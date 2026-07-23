from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from services.alert_service import SystemAlert


class SystemAlerts(Vertical):
    """Displays current system health alerts."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[b cyan]● SYSTEM NOMINAL[/b cyan]"
            "    //    NO ACTIVE ALERTS",
            id="system-alert-banner",
        )

    def update_alerts(
        self,
        alerts: tuple[SystemAlert, ...],
    ) -> None:
        banner = self.query_one(
            "#system-alert-banner",
            Static,
        )

        if not alerts:
            banner.update(
                "[b cyan]● SYSTEM NOMINAL[/b cyan]"
                "    //    NO ACTIVE ALERTS"
            )
            self.remove_class("has-warning")
            self.remove_class("has-critical")
            return

        critical_count = sum(
            alert.severity == "CRITICAL"
            for alert in alerts
        )
        warning_count = sum(
            alert.severity == "WARNING"
            for alert in alerts
        )

        if critical_count:
            state = (
                "[b red]● CRITICAL CONDITION[/b red]"
            )
            self.add_class("has-critical")
            self.remove_class("has-warning")
        else:
            state = (
                "[b yellow]● SYSTEM WARNING[/b yellow]"
            )
            self.add_class("has-warning")
            self.remove_class("has-critical")

        lines = [
            (
                f"{state}"
                f"    //    CRITICAL {critical_count}"
                f"    //    WARNING {warning_count}"
            ),
            "",
        ]

        for alert in alerts[:5]:
            color = (
                "red"
                if alert.severity == "CRITICAL"
                else "yellow"
            )

            lines.append(
                f"[b {color}]"
                f"{alert.severity:<8}"
                f"[/b {color}]"
                f"  {alert.title:<20}"
                f"  {alert.value}"
            )
            lines.append(
                f"          {alert.message}"
            )

        if len(alerts) > 5:
            lines.append(
                f"\n...and {len(alerts) - 5} more alert(s)."
            )

        banner.update("\n".join(lines))
