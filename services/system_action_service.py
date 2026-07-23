from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SystemActionResult:
    action_id: str
    title: str
    status: str
    detail: str


class SystemActionService:
    """Launches approved system tools in a separate terminal."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.diagnostic_script = (
            self.project_root
            / "scripts"
            / "helm-system-diagnostic.sh"
        )

    def launch(
        self,
        action_id: str,
    ) -> SystemActionResult:
        actions = {
            "btop": self._btop_command,
            "sensors": self._sensors_command,
            "gpu": self._gpu_command,
            "diagnostic": self._diagnostic_command,
        }

        titles = {
            "btop": "BTOP SYSTEM MONITOR",
            "sensors": "LIVE TEMPERATURE MONITOR",
            "gpu": "NVIDIA GPU MONITOR",
            "diagnostic": "FULL SYSTEM DIAGNOSTIC",
        }

        command_builder = actions.get(action_id)
        title = titles.get(action_id, action_id.upper())

        if command_builder is None:
            return SystemActionResult(
                action_id=action_id,
                title=title,
                status="UNKNOWN ACTION",
                detail="The requested action is not registered.",
            )

        command, missing_program = command_builder()

        if command is None:
            return SystemActionResult(
                action_id=action_id,
                title=title,
                status="NOT INSTALLED",
                detail=(
                    f"Required program not found: "
                    f"{missing_program}"
                ),
            )

        terminal_command = self._build_terminal_command(
            command
        )

        if terminal_command is None:
            return SystemActionResult(
                action_id=action_id,
                title=title,
                status="NOT INSTALLED",
                detail=(
                    "No supported terminal emulator found "
                    "(Konsole, Kitty, Alacritty or xterm)."
                ),
            )

        try:
            subprocess.Popen(
                terminal_command,
                cwd=str(self.project_root),
                env=os.environ.copy(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        except (OSError, ValueError) as error:
            return SystemActionResult(
                action_id=action_id,
                title=title,
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return SystemActionResult(
            action_id=action_id,
            title=title,
            status="LAUNCHED",
            detail=terminal_command[0],
        )

    @staticmethod
    def _btop_command(
    ) -> tuple[tuple[str, ...] | None, str]:
        if shutil.which("btop") is None:
            return None, "btop"

        return ("btop",), ""

    @staticmethod
    def _sensors_command(
    ) -> tuple[tuple[str, ...] | None, str]:
        if shutil.which("sensors") is None:
            return None, "sensors"

        if shutil.which("watch") is not None:
            return (
                "watch",
                "--color",
                "--interval",
                "1",
                "sensors",
            ), ""

        return ("sensors",), ""

    @staticmethod
    def _gpu_command(
    ) -> tuple[tuple[str, ...] | None, str]:
        if shutil.which("nvidia-smi") is None:
            return None, "nvidia-smi"

        if shutil.which("watch") is not None:
            return (
                "watch",
                "--color",
                "--interval",
                "1",
                "nvidia-smi",
            ), ""

        return ("nvidia-smi",), ""

    def _diagnostic_command(
        self,
    ) -> tuple[tuple[str, ...] | None, str]:
        if not self.diagnostic_script.exists():
            return None, str(self.diagnostic_script)

        return (
            "bash",
            str(self.diagnostic_script),
        ), ""

    def _build_terminal_command(
        self,
        command: tuple[str, ...],
    ) -> tuple[str, ...] | None:
        shell_command = (
            f"{shlex.join(command)}; "
            "result=$?; "
            "printf '\\n[HELM] Process finished with status %s.\\n' "
            "\"$result\"; "
            "printf '\\n[HELM] Press Enter to close this window...'; read -r _"
        )

        project_root = str(self.project_root)

        if shutil.which("konsole") is not None:
            return (
                "konsole",
                "--workdir",
                project_root,
                "-e",
                "bash",
                "-lc",
                shell_command,
            )

        if shutil.which("kitty") is not None:
            return (
                "kitty",
                "--directory",
                project_root,
                "bash",
                "-lc",
                shell_command,
            )

        if shutil.which("alacritty") is not None:
            return (
                "alacritty",
                "--working-directory",
                project_root,
                "-e",
                "bash",
                "-lc",
                shell_command,
            )

        if shutil.which("xterm") is not None:
            return (
                "xterm",
                "-e",
                "bash",
                "-lc",
                shell_command,
            )

        return None
