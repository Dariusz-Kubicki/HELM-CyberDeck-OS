from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class SignatureRail(Horizontal):
    """Distinctive HELM identity and live system-state rail."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[b #42e8ff]◈ HELM // SIG[/]",
            id="signature-mark",
        )

        yield Static(
            "[b]01 SYSTEM OVERVIEW[/b]"
            " [#315965]//[/] "
            "[#6f9da8]CORE TELEMETRY[/]",
            id="signature-module",
        )

        yield Static(
            "[b #ffbd59]HEALTH STARTING[/]"
            " [#315965]//[/] "
            "[#6f9da8]LINK --ms // CUSTOM[/]",
            id="signature-state",
        )

    def update_module(
        self,
        code: str,
        title: str,
        context: str,
    ) -> None:
        clean_title = (
            title.replace(
                "HELM // ",
                "",
            )
            .strip()
            .upper()
        )

        self.query_one(
            "#signature-module",
            Static,
        ).update(
            f"[b]{escape(code)} "
            f"{escape(clean_title)}[/b]"
            " [#315965]//[/] "
            f"[#6f9da8]"
            f"{escape(context.upper())}"
            "[/]"
        )

    def update_state(
        self,
        health: str,
        telemetry: str,
        duration_ms: float,
        skipped_cycles: int,
        mode_id: str,
    ) -> None:
        color = self._state_color(
            health,
            telemetry,
        )

        state_label = self._combined_state(
            health,
            telemetry,
        )

        clean_mode = (
            mode_id.strip().upper()
            or "CUSTOM"
        )

        self.query_one(
            "#signature-state",
            Static,
        ).update(
            f"[b {color}]"
            f"CORE {escape(state_label)}"
            "[/] "
            "[#315965]//[/] "
            f"[#6f9da8]"
            f"LINK {duration_ms:.0f}ms"
            f" // S{skipped_cycles}"
            f" // {escape(clean_mode)}"
            "[/]"
        )

    @staticmethod
    def _combined_state(
        health: str,
        telemetry: str,
    ) -> str:
        critical_states = {
            "CRITICAL",
            "FAILED",
            "OFFLINE",
        }

        warning_states = {
            "DEGRADED",
            "WARNING",
            "SCANNING",
            "STARTING",
        }

        states = {
            health.upper(),
            telemetry.upper(),
        }

        if states & critical_states:
            return "CRITICAL"

        if states & warning_states:
            return "DEGRADED"

        if "BUSY" in states:
            return "PROCESSING"

        return "NOMINAL"

    @classmethod
    def _state_color(
        cls,
        health: str,
        telemetry: str,
    ) -> str:
        state = cls._combined_state(
            health,
            telemetry,
        )

        if state == "CRITICAL":
            return "#ff4365"

        if state in {
            "DEGRADED",
            "PROCESSING",
        }:
            return "#ffbd59"

        return "#58f6d0"
