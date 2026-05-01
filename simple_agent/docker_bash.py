from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .safety import confirm, truncate_text


@dataclass
class DockerBash:
    workspace: Path
    image: str
    network: bool
    auto_yes: bool
    timeout_seconds: int = 60
    max_output_chars: int = 12000

    def run(self, command: str) -> str:
        network_mode = "enabled" if self.network else "disabled"
        action = (
            "Docker bash requested:\n"
            f"  image: {self.image}\n"
            f"  workspace mount: {self.workspace} -> /workspace\n"
            f"  network: {network_mode}\n"
            f"  command: {command}"
        )
        if not confirm(action, self.auto_yes):
            return "User denied bash command."

        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "-v",
            f"{self.workspace}:/workspace",
            "-w",
            "/workspace",
        ]
        if not self.network:
            docker_cmd.extend(["--network", "none"])
        docker_cmd.extend([self.image, "bash", "-lc", command])

        try:
            completed = subprocess.run(
                docker_cmd,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return "Docker is not installed or is not on PATH."
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            return truncate_text(
                "Command timed out.\n"
                f"stdout:\n{stdout}\n\nstderr:\n{stderr}",
                self.max_output_chars,
            )

        output = (
            f"exit_code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n\n"
            f"stderr:\n{completed.stderr}"
        )
        return truncate_text(output, self.max_output_chars)
