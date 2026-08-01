from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from services.system_action_service import SystemActionResult


class SystemActions(Vertical):
    """Quick launch controls for system diagnostic tools."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[b cyan]DIAGNOSTIC ACTIONS[/b cyan]"
            "    //    OPEN TOOLS IN A SEPARATE TERMINAL",
            id="system-actions-title",
        )

        with Horizontal(id="system-action-buttons"):
            yield Button(
                "BTOP MONITOR",
                id="system-action-btop",
                classes="system-action-button",
                flat=True,
            )
            yield Button(
                "TEMPERATURES",
                id="system-action-sensors",
                classes="system-action-button",
                flat=True,
            )
            yield Button(
                "NVIDIA MONITOR",
                id="system-action-gpu",
                classes="system-action-button",
                flat=True,
            )
            yield Button(
                "FULL DIAGNOSTIC",
                id="system-action-diagnostic",
                classes="system-action-button",
                flat=True,
            )

        yield Static(
            "ACTION ENGINE READY",
            id="system-action-status",
        )

    def show_result(
        self,
        result: SystemActionResult,
    ) -> None:
        color = {
            "LAUNCHED": "cyan",
            "NOT INSTALLED": "yellow",
            "FAILED": "red",
            "UNKNOWN ACTION": "red",
        }.get(result.status, "white")

        self.query_one(
            "#system-action-status",
            Static,
        ).update(
            f"[b {color}]● {result.status}[/b {color}]"
            f"    //    {result.title}"
            f"    //    {result.detail}"
        )
