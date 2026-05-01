from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .sessions import append_messages, load_messages
from .tools import ToolRegistry, tool_schemas


BASE_SYSTEM_PROMPT = """You are a minimal coding agent running in a guarded harness.

Use tools when you need local context. File tools are restricted to the workspace.
The bash tool, when enabled, runs inside Docker at /workspace and may require user
approval. Prefer read/search before editing. Keep final answers concise and include
what changed or what you verified.
"""


class ChatClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return one model response for the current message/tool state."""
        ...


def build_initial_messages(workspace: Path) -> list[dict[str, Any]]:
    system = BASE_SYSTEM_PROMPT
    context_chunks: list[str] = []
    for filename in ("AGENTS.md", "CLAUDE.md"):
        path = workspace / filename
        if path.exists() and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            context_chunks.append(f"# {filename}\n{text}")
    if context_chunks:
        system += "\n\nWorkspace context files:\n\n" + "\n\n".join(context_chunks)
    return [{"role": "system", "content": system}]


class AgentLoop:
    def __init__(
        self,
        client: ChatClient,
        registry: ToolRegistry,
        workspace: Path,
        max_steps: int,
        session_file: Path | None,
        allow_bash: bool,
    ) -> None:
        self.client = client
        self.registry = registry
        self.max_steps = max_steps
        self.session_file = session_file
        self.messages = build_initial_messages(workspace)
        self.messages.extend(load_messages(session_file))
        self.tools = tool_schemas(allow_bash)

    def run_prompt(self, prompt: str) -> str:
        new_messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        self.messages.extend(new_messages)

        for _ in range(self.max_steps):
            response = self.client.chat(self.messages, self.tools)
            message = response["choices"][0]["message"]
            assistant_message = _normalize_assistant_message(message)
            self.messages.append(assistant_message)
            new_messages.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls") or []
            if not tool_calls:
                append_messages(self.session_file, new_messages)
                return assistant_message.get("content") or ""

            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", "{}")
                result = self.registry.execute(name, arguments)
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": name,
                    "content": result,
                }
                self.messages.append(tool_message)
                new_messages.append(tool_message)

        final = f"Stopped after max_steps={self.max_steps}."
        append_messages(self.session_file, new_messages)
        return final


def _normalize_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "role": "assistant",
        "content": message.get("content"),
    }
    if message.get("tool_calls"):
        normalized["tool_calls"] = message["tool_calls"]
    return normalized
