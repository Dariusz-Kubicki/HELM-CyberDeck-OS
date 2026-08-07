from textual.app import ComposeResult
from textual.containers import Vertical

from app.cpu_history import CpuHistory
from app.dashboard import Dashboard
from app.mobile_power_panel import MobilePowerPanel
from app.resource_history import ResourceHistory
from app.system_actions import SystemActions
from app.system_alerts import SystemAlerts
from app.system_inspector import SystemInspector
from app.system_panel import SystemPanel
from services.alert_service import AlertService, SystemAlert
from services.data_service import SystemSnapshot


class SystemScreen(Vertical):
    # Main system monitoring and diagnostic control center.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.alert_service = AlertService()
        self._mode_id = "custom"
        self._mode_power_profile = "unchanged"

    def compose(self) -> ComposeResult:
        yield SystemPanel(id="system-panel")
        yield MobilePowerPanel(id="mobile-power-panel")
        yield Dashboard(id="dashboard")
        yield CpuHistory(id="cpu-history")
        yield ResourceHistory(id="resource-history")
        yield SystemAlerts(id="system-alerts")
        yield SystemActions(id="system-actions")
        yield SystemInspector(id="system-inspector")

    def update_mode_context(
        self,
        mode_id: str,
        explicit_profile: str,
    ) -> None:
        self._mode_id = (
            str(mode_id).strip().lower()
            or "custom"
        )
        self._mode_power_profile = (
            str(explicit_profile).strip().lower()
            or "unchanged"
        )

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> tuple[SystemAlert, ...]:
        self.query_one(
            SystemPanel
        ).update_snapshot(snapshot)

        self.query_one(
            MobilePowerPanel
        ).update_snapshot(
            snapshot,
            self._mode_id,
            self._mode_power_profile,
        )

        self.query_one(
            Dashboard
        ).update_snapshot(snapshot)

        self.query_one(
            CpuHistory
        ).add_sample(snapshot.cpu_usage)

        self.query_one(
            ResourceHistory
        ).add_snapshot(snapshot)

        alerts = self.alert_service.analyze(snapshot)

        self.query_one(
            SystemAlerts
        ).update_alerts(alerts)

        self.query_one(
            SystemInspector
        ).update_snapshot(snapshot)

        return alerts

    def show_error(
        self,
        error: Exception,
    ) -> None:
        self.query_one(SystemPanel).update(
            "[b red]● TELEMETRY ERROR[/b red]\n\n"
            f"{type(error).__name__}: {error}"
        )
