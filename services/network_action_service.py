from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class NetworkActionResult:
    action_id: str
    title: str
    status: str
    detail: str


class NetworkActionService:
    """Launches approved network diagnostics in Konsole."""

    INTERNET_TARGET = "1.1.1.1"
    DNS_TARGET = "chatgpt.com"

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]

    def launch(
        self,
        action_id: str,
        gateway: str,
    ) -> NetworkActionResult:
        title, command, missing = self._resolve_action(
            action_id,
            gateway,
        )

        if command is None:
            return NetworkActionResult(
                action_id=action_id,
                title=title,
                status="UNAVAILABLE",
                detail=missing,
            )

        terminal_command = self._terminal_command(command)

        if terminal_command is None:
            return NetworkActionResult(
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
            return NetworkActionResult(
                action_id=action_id,
                title=title,
                status="FAILED",
                detail=f"{type(error).__name__}: {error}",
            )

        return NetworkActionResult(
            action_id=action_id,
            title=title,
            status="LAUNCHED",
            detail=terminal_command[0],
        )

    def _resolve_action(
        self,
        action_id: str,
        gateway: str,
    ) -> tuple[
        str,
        tuple[str, ...] | None,
        str,
    ]:
        if action_id == "ping-gateway":
            if gateway in {"", "N/A", "unknown"}:
                return (
                    "PING GATEWAY",
                    None,
                    "Default gateway was not detected",
                )

            if shutil.which("ping") is None:
                return "PING GATEWAY", None, "ping not installed"

            return (
                "PING GATEWAY",
                ("ping", gateway),
                "",
            )

        if action_id == "ping-internet":
            if shutil.which("ping") is None:
                return "PING INTERNET", None, "ping not installed"

            return (
                "PING INTERNET",
                ("ping", self.INTERNET_TARGET),
                "",
            )

        if action_id == "trace-route":
            if shutil.which("tracepath"):
                return (
                    "TRACE ROUTE",
                    (
                        "tracepath",
                        self.INTERNET_TARGET,
                    ),
                    "",
                )

            if shutil.which("traceroute"):
                return (
                    "TRACE ROUTE",
                    (
                        "traceroute",
                        "-n",
                        self.INTERNET_TARGET,
                    ),
                    "",
                )

            return (
                "TRACE ROUTE",
                None,
                "tracepath or traceroute not installed",
            )

        if action_id == "dns-query":
            # getent uses the system NSS resolver and does not require
            # the optional systemd-resolved service.
            if shutil.which("getent"):
                return (
                    "DNS QUERY",
                    (
                        "getent",
                        "ahosts",
                        self.DNS_TARGET,
                    ),
                    "",
                )

            if shutil.which("dig"):
                return (
                    "DNS QUERY",
                    (
                        "dig",
                        self.DNS_TARGET,
                    ),
                    "",
                )

            if shutil.which("resolvectl"):
                return (
                    "DNS QUERY",
                    (
                        "resolvectl",
                        "query",
                        self.DNS_TARGET,
                    ),
                    "",
                )

            return (
                "DNS QUERY",
                None,
                "getent, dig or resolvectl not available",
            )

        if action_id == "socket-monitor":
            if shutil.which("ss") is None:
                return (
                    "SOCKET MONITOR",
                    None,
                    "ss not installed",
                )

            if shutil.which("watch"):
                command = (
                    "watch",
                    "--interval",
                    "2",
                    "ss",
                    "-tupan",
                )
            else:
                command = ("ss", "-tupan")

            return "SOCKET MONITOR", command, ""

        return (
            action_id.upper(),
            None,
            "Unknown network action",
        )

    def _terminal_command(
        self,
        command: tuple[str, ...],
    ) -> tuple[str, ...] | None:
        shell_command = (
            f"{shlex.join(command)}; "
            "status=$?; "
            "printf '\\n[HELM] Command finished with status %s.\\n' "
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
