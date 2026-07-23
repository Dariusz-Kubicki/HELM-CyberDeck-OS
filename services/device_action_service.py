from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceActionResult:
    action_id: str
    title: str
    status: str
    detail: str


class DeviceActionService:
    """Launches approved hardware-development actions."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.home = Path.home()

    def launch(
        self,
        action_id: str,
        *,
        serial_port: str | None = None,
    ) -> DeviceActionResult:
        if action_id == "arduino":
            return self._launch_arduino()

        if action_id == "port-info":
            return self._launch_port_info(serial_port)

        return DeviceActionResult(
            action_id=action_id,
            title=action_id.upper(),
            status="UNKNOWN ACTION",
            detail="The requested action is not registered.",
        )

    def _launch_arduino(self) -> DeviceActionResult:
        alternatives = (
            ("arduino-ide",),
            ("arduino",),
            (
                "flatpak",
                "run",
                "cc.arduino.IDE2",
            ),
        )

        command: tuple[str, ...] | None = None

        for candidate in alternatives:
            if shutil.which(candidate[0]) is None:
                continue

            if (
                candidate[0] == "flatpak"
                and not self._flatpak_exists(
                    "cc.arduino.IDE2"
                )
            ):
                continue

            command = candidate
            break

        if command is None:
            return DeviceActionResult(
                action_id="arduino",
                title="ARDUINO IDE",
                status="UNAVAILABLE",
                detail="Arduino IDE was not detected.",
            )

        try:
            subprocess.Popen(
                command,
                cwd=str(self.home),
                env=os.environ.copy(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )

        except OSError as error:
            return DeviceActionResult(
                action_id="arduino",
                title="ARDUINO IDE",
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return DeviceActionResult(
            action_id="arduino",
            title="ARDUINO IDE",
            status="LAUNCHED",
            detail=" ".join(command),
        )

    def _launch_port_info(
        self,
        serial_port: str | None,
    ) -> DeviceActionResult:
        if not serial_port:
            return DeviceActionResult(
                action_id="port-info",
                title="PORT INFORMATION",
                status="UNAVAILABLE",
                detail="No serial interface selected.",
            )

        if not re.fullmatch(
            r"/dev/tty(?:USB|ACM)\d+",
            serial_port,
        ):
            return DeviceActionResult(
                action_id="port-info",
                title="PORT INFORMATION",
                status="UNAVAILABLE",
                detail="Invalid serial interface.",
            )

        if shutil.which("udevadm") is None:
            return DeviceActionResult(
                action_id="port-info",
                title="PORT INFORMATION",
                status="UNAVAILABLE",
                detail="udevadm is not installed.",
            )

        command = (
            "udevadm",
            "info",
            "--query=property",
            "--name",
            serial_port,
        )

        terminal_command = self._terminal_command(
            command
        )

        if terminal_command is None:
            return DeviceActionResult(
                action_id="port-info",
                title="PORT INFORMATION",
                status="UNAVAILABLE",
                detail="No supported terminal emulator found.",
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

        except OSError as error:
            return DeviceActionResult(
                action_id="port-info",
                title="PORT INFORMATION",
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return DeviceActionResult(
            action_id="port-info",
            title="PORT INFORMATION",
            status="LAUNCHED",
            detail=serial_port,
        )

    @staticmethod
    def _flatpak_exists(application_id: str) -> bool:
        try:
            result = subprocess.run(
                [
                    "flatpak",
                    "info",
                    application_id,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3.0,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return False

        return result.returncode == 0

    def _terminal_command(
        self,
        command: tuple[str, ...],
    ) -> tuple[str, ...] | None:
        shell_command = (
            f"{shlex.join(command)}; "
            "status=$?; "
            "printf "
            "'\\n[HELM] Command finished with status %s.\\n' "
            "\"$status\"; "
            "printf "
            "'[HELM] Press Enter to close this window...'; "
            "read -r _"
        )

        project_root = str(self.project_root)

        if shutil.which("konsole"):
            return (
                "konsole",
                "--workdir",
                project_root,
                "-e",
                "bash",
                "-c",
                shell_command,
            )

        if shutil.which("kitty"):
            return (
                "kitty",
                "--directory",
                project_root,
                "bash",
                "-c",
                shell_command,
            )

        if shutil.which("alacritty"):
            return (
                "alacritty",
                "--working-directory",
                project_root,
                "-e",
                "bash",
                "-c",
                shell_command,
            )

        if shutil.which("xterm"):
            return (
                "xterm",
                "-e",
                "bash",
                "-c",
                shell_command,
            )

        return None
