from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StorageActionResult:
    action_id: str
    title: str
    status: str
    detail: str


class StorageActionService:
    """Launches approved storage diagnostics and locations."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.home = Path.home()
        self.smart_helper = Path(
            "/usr/local/lib/helm/helm-smart-status"
        )

    def launch(
        self,
        action_id: str,
        *,
        device_name: str | None = None,
        mountpoint: str | None = None,
    ) -> StorageActionResult:
        if action_id == "open-location":
            return self._open_location(
                mountpoint or "/"
            )

        title, command, missing = self._resolve_terminal_action(
            action_id,
            device_name=device_name,
        )

        if command is None:
            return StorageActionResult(
                action_id=action_id,
                title=title,
                status="UNAVAILABLE",
                detail=missing,
            )

        terminal_command = self._terminal_command(
            command
        )

        if terminal_command is None:
            return StorageActionResult(
                action_id=action_id,
                title=title,
                status="UNAVAILABLE",
                detail="No supported terminal emulator found",
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
            return StorageActionResult(
                action_id=action_id,
                title=title,
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return StorageActionResult(
            action_id=action_id,
            title=title,
            status="LAUNCHED",
            detail=terminal_command[0],
        )

    def _resolve_terminal_action(
        self,
        action_id: str,
        *,
        device_name: str | None,
    ) -> tuple[
        str,
        tuple[str, ...] | None,
        str,
    ]:
        if action_id == "smart":
            if not device_name:
                return (
                    "SMART SELECTED",
                    None,
                    "No physical drive selected",
                )

            if not re.fullmatch(
                r"[A-Za-z0-9._+-]+",
                device_name,
            ):
                return (
                    "SMART SELECTED",
                    None,
                    "Invalid device name",
                )

            device = f"/dev/{device_name}"

            if (
                re.fullmatch(
                    r"nvme\d+n\d+",
                    device_name,
                )
                and self.smart_helper.is_file()
            ):
                return (
                    "SMART SELECTED",
                    (
                        "sudo",
                        "-n",
                        str(self.smart_helper),
                        device,
                        "report",
                    ),
                    "",
                )

            if shutil.which("smartctl"):
                return (
                    "SMART SELECTED",
                    (
                        "smartctl",
                        "-a",
                        device,
                    ),
                    "",
                )

            return (
                "SMART SELECTED",
                None,
                "smartctl is not installed",
            )

        if action_id == "drive-map":
            if shutil.which("lsblk") is None:
                return (
                    "DRIVE MAP",
                    None,
                    "lsblk is not installed",
                )

            return (
                "DRIVE MAP",
                (
                    "lsblk",
                    "-o",
                    (
                        "NAME,MODEL,SIZE,TYPE,FSTYPE,"
                        "LABEL,TRAN,MOUNTPOINTS"
                    ),
                ),
                "",
            )

        if action_id == "home-usage":
            if shutil.which("ncdu"):
                return (
                    "HOME USAGE",
                    (
                        "ncdu",
                        "-x",
                        str(self.home),
                    ),
                    "",
                )

            if shutil.which("du"):
                shell_command = (
                    f"du -xhd1 "
                    f"{shlex.quote(str(self.home))} "
                    "2>/dev/null | sort -h"
                )

                return (
                    "HOME USAGE",
                    (
                        "bash",
                        "-lc",
                        shell_command,
                    ),
                    "",
                )

            return (
                "HOME USAGE",
                None,
                "ncdu and du are unavailable",
            )

        return (
            action_id.upper(),
            None,
            "Unknown storage action",
        )

    def _open_location(
        self,
        mountpoint: str,
    ) -> StorageActionResult:
        target = Path(
            mountpoint
            if mountpoint not in {"", "—"}
            else "/"
        )

        if not target.exists():
            return StorageActionResult(
                action_id="open-location",
                title="OPEN LOCATION",
                status="UNAVAILABLE",
                detail=f"Path does not exist: {target}",
            )

        if shutil.which("dolphin"):
            command = (
                "dolphin",
                str(target),
            )

        elif shutil.which("xdg-open"):
            command = (
                "xdg-open",
                str(target),
            )

        else:
            return StorageActionResult(
                action_id="open-location",
                title="OPEN LOCATION",
                status="UNAVAILABLE",
                detail="Dolphin and xdg-open are unavailable",
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
            return StorageActionResult(
                action_id="open-location",
                title="OPEN LOCATION",
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return StorageActionResult(
            action_id="open-location",
            title="OPEN LOCATION",
            status="LAUNCHED",
            detail=str(target),
        )

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
            "printf '\\n[HELM] Press Enter to close this window...'; read -r _"
        )

        project_root = str(self.project_root)

        if shutil.which("konsole"):
            return (
                "konsole",
                "--workdir",
                project_root,
                "-e",
                "bash",
                "-lc",
                shell_command,
            )

        if shutil.which("kitty"):
            return (
                "kitty",
                "--directory",
                project_root,
                "bash",
                "-lc",
                shell_command,
            )

        if shutil.which("alacritty"):
            return (
                "alacritty",
                "--working-directory",
                project_root,
                "-e",
                "bash",
                "-lc",
                shell_command,
            )

        if shutil.which("xterm"):
            return (
                "xterm",
                "-e",
                "bash",
                "-lc",
                shell_command,
            )

        return None
