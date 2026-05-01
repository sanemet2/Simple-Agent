from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_DOCKER_IMAGE = "python:3.12-slim"


@dataclass(frozen=True)
class AgentConfig:
    api_key: str
    model: str
    workspace: Path
    max_steps: int
    docker_image: str
    docker_network: bool
    allow_bash: bool
    auto_yes: bool
    session_file: Path | None


def parse_args(argv: list[str] | None = None) -> tuple[AgentConfig, str | None]:
    parser = argparse.ArgumentParser(
        description="Tiny OpenRouter coding agent with guarded file tools and Docker bash."
    )
    parser.add_argument("prompt", nargs="*", help="Prompt to run once. Omit for REPL.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace folder the agent may read/write. Defaults to current folder.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="OpenRouter model id. Can also set OPENROUTER_MODEL.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum model/tool iterations per prompt.",
    )
    parser.add_argument(
        "--docker-image",
        default=os.environ.get("AGENT_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE),
        help="Docker image used for bash tool.",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="Allow network inside Docker bash. Default is disabled.",
    )
    parser.add_argument(
        "--no-bash",
        action="store_true",
        help="Disable the bash tool entirely.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-approve write/edit/bash tool calls. Use only in a sandbox.",
    )
    parser.add_argument(
        "--session",
        help="Optional JSONL file to append conversation messages to.",
    )
    parser.add_argument(
        "--env-file",
        default=".env.local",
        help=(
            "Env file loaded before reading OPENROUTER_API_KEY. "
            "Defaults to .env.local if present."
        ),
    )
    args = parser.parse_args(argv)

    _load_env_file(Path(args.env_file).expanduser())

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        parser.error("OPENROUTER_API_KEY is required.")

    model = args.model or os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)

    workspace = Path(args.workspace).expanduser().resolve()
    prompt = " ".join(args.prompt).strip() or None
    session_file = Path(args.session).expanduser().resolve() if args.session else None

    return (
        AgentConfig(
            api_key=api_key,
            model=model,
            workspace=workspace,
            max_steps=args.max_steps,
            docker_image=args.docker_image,
            docker_network=args.network,
            allow_bash=not args.no_bash,
            auto_yes=args.yes,
            session_file=session_file,
        ),
        prompt,
    )


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
