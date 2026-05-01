from __future__ import annotations

from pathlib import Path


class SafetyError(Exception):
    """Raised when a requested tool action violates local safety policy."""


SENSITIVE_PARTS = {
    ".ssh",
    ".aws",
    ".azure",
    ".gnupg",
    ".kube",
}

SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SENSITIVE_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


def resolve_in_workspace(workspace: Path, requested: str) -> Path:
    if not requested:
        requested = "."
    raw = Path(requested).expanduser()
    target = raw.resolve() if raw.is_absolute() else (workspace / raw).resolve()

    workspace = workspace.resolve()
    if target != workspace and workspace not in target.parents:
        raise SafetyError(f"path is outside workspace: {requested}")
    return target


def check_not_sensitive(path: Path) -> None:
    parts = {part.lower() for part in path.parts}
    if parts & SENSITIVE_PARTS:
        raise SafetyError(f"refusing to access sensitive path: {path}")

    name = path.name.lower()
    if name in SENSITIVE_NAMES or name.startswith(".env."):
        raise SafetyError(f"refusing to access sensitive file: {path.name}")

    if any(name.endswith(suffix) for suffix in SENSITIVE_SUFFIXES):
        raise SafetyError(f"refusing to access key/certificate-like file: {path.name}")


def confirm(action: str, auto_yes: bool) -> bool:
    if auto_yes:
        return True
    print()
    print(action)
    answer = input("Allow? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"{text[:max_chars]}\n\n[truncated {omitted} chars]"
