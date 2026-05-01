from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .docker_bash import DockerBash
from .safety import (
    SafetyError,
    check_not_sensitive,
    confirm,
    resolve_in_workspace,
    truncate_text,
)


ToolFn = Callable[[dict[str, Any]], str]


def create_tool_registry(
    workspace: Path,
    allow_bash: bool,
    docker_image: str,
    docker_network: bool,
    auto_yes: bool,
) -> "ToolRegistry":
    docker = None
    if allow_bash:
        docker = DockerBash(
            workspace=workspace,
            image=docker_image,
            network=docker_network,
            auto_yes=auto_yes,
        )
    return ToolRegistry(
        workspace=workspace,
        docker_bash=docker,
        auto_yes=auto_yes,
    )


def tool_schemas(allow_bash: bool) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and folders inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                        "max_entries": {"type": "integer", "default": 200},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file inside the workspace.",
                "parameters": {
                    "type": "object",
                    "required": ["path"],
                    "properties": {
                        "path": {"type": "string"},
                        "max_chars": {"type": "integer", "default": 12000},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search text files inside the workspace for a query.",
                "parameters": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string"},
                        "path": {"type": "string", "default": "."},
                        "case_sensitive": {"type": "boolean", "default": False},
                        "max_matches": {"type": "integer", "default": 50},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create or replace a UTF-8 text file inside the workspace.",
                "parameters": {
                    "type": "object",
                    "required": ["path", "content"],
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Replace one exact text span in a file inside the workspace.",
                "parameters": {
                    "type": "object",
                    "required": ["path", "old_text", "new_text"],
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                },
            },
        },
    ]
    if allow_bash:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": (
                        "Run a bash command in Docker at /workspace. Network is disabled "
                        "unless the user started the agent with --network."
                    ),
                    "parameters": {
                        "type": "object",
                        "required": ["command"],
                        "properties": {"command": {"type": "string"}},
                    },
                },
            }
        )
    return tools


@dataclass
class ToolRegistry:
    workspace: Path
    docker_bash: DockerBash | None
    auto_yes: bool

    def execute(self, name: str, arguments_json: str) -> str:
        try:
            args = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as exc:
            return f"Invalid JSON arguments: {exc}"

        handlers: dict[str, ToolFn] = {
            "list_files": self._list_files,
            "read_file": self._read_file,
            "search_files": self._search_files,
            "write_file": self._write_file,
            "edit_file": self._edit_file,
        }
        if self.docker_bash is not None:
            handlers["bash"] = self._bash

        handler = handlers.get(name)
        if handler is None:
            return f"Unknown or disabled tool: {name}"

        try:
            return handler(args)
        except SafetyError as exc:
            return f"SafetyError: {exc}"
        except Exception as exc:  # Keep the loop recoverable.
            return f"{type(exc).__name__}: {exc}"

    def _safe_path(self, requested: str) -> Path:
        path = resolve_in_workspace(self.workspace, requested)
        check_not_sensitive(path)
        return path

    def _list_files(self, args: dict[str, Any]) -> str:
        root = self._safe_path(str(args.get("path", ".")))
        max_entries = int(args.get("max_entries", 200))
        if not root.exists():
            return f"Path does not exist: {root}"
        if root.is_file():
            return str(root.relative_to(self.workspace))

        rows: list[str] = []
        for index, child in enumerate(sorted(root.iterdir(), key=lambda p: p.name.lower())):
            if index >= max_entries:
                rows.append(f"... truncated after {max_entries} entries")
                break
            suffix = "/" if child.is_dir() else ""
            rows.append(f"{child.relative_to(self.workspace)}{suffix}")
        return "\n".join(rows) or "(empty)"

    def _read_file(self, args: dict[str, Any]) -> str:
        path = self._safe_path(str(args["path"]))
        max_chars = int(args.get("max_chars", 12000))
        if not path.exists():
            return f"File does not exist: {path.relative_to(self.workspace)}"
        if not path.is_file():
            return f"Not a file: {path.relative_to(self.workspace)}"
        content = path.read_text(encoding="utf-8", errors="replace")
        return truncate_text(content, max_chars)

    def _search_files(self, args: dict[str, Any]) -> str:
        query = str(args["query"])
        root = self._safe_path(str(args.get("path", ".")))
        case_sensitive = bool(args.get("case_sensitive", False))
        max_matches = int(args.get("max_matches", 50))
        needle = query if case_sensitive else query.lower()
        matches: list[str] = []

        if not root.exists():
            return f"Path does not exist: {root.relative_to(self.workspace)}"

        files = [root] if root.is_file() else _walk_text_candidates(root)
        for path in files:
            try:
                check_not_sensitive(path)
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            haystack = text if case_sensitive else text.lower()
            if needle not in haystack:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                compare = line if case_sensitive else line.lower()
                if needle in compare:
                    rel = path.relative_to(self.workspace)
                    matches.append(f"{rel}:{line_no}: {line}")
                    if len(matches) >= max_matches:
                        return "\n".join(matches)
        return "\n".join(matches) if matches else "No matches."

    def _write_file(self, args: dict[str, Any]) -> str:
        path = self._safe_path(str(args["path"]))
        rel = path.relative_to(self.workspace)
        content = str(args["content"])
        action = f"Write requested: {rel} ({len(content)} chars)"
        if not confirm(action, self.auto_yes):
            return "User denied write."
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {rel} ({len(content)} chars)."

    def _edit_file(self, args: dict[str, Any]) -> str:
        path = self._safe_path(str(args["path"]))
        rel = path.relative_to(self.workspace)
        old_text = str(args["old_text"])
        new_text = str(args["new_text"])
        if not path.exists():
            return f"File does not exist: {rel}"
        content = path.read_text(encoding="utf-8", errors="replace")
        count = content.count(old_text)
        if count == 0:
            return f"old_text not found in {rel}."
        if count > 1:
            return f"old_text appears {count} times in {rel}; refusing ambiguous edit."

        action = (
            f"Edit requested: {rel}\n"
            f"  replace {len(old_text)} chars with {len(new_text)} chars"
        )
        if not confirm(action, self.auto_yes):
            return "User denied edit."
        path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {rel}."

    def _bash(self, args: dict[str, Any]) -> str:
        if self.docker_bash is None:
            return "bash tool is disabled."
        return self.docker_bash.run(str(args["command"]))


def _walk_text_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    skipped_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache"}
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in skipped_dirs]
        current = Path(current_root)
        for filename in files:
            path = current / filename
            if path.stat().st_size > 1_000_000:
                continue
            candidates.append(path)
    return candidates
