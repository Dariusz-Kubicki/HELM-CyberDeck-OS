from textual.app import ComposeResult
from textual.containers import Vertical

from app.cpu_history import CpuHistory
from app.dashboard import Dashboard
from app.system_inspector import SystemInspector
from app.system_panel import SystemPanel
from services.data_service import SystemSnapshot


class SystemScreen(Vertical):
    """Main system monitoring and diagnostic screen."""

    def compose(self) -> ComposeResult:
        yield SystemPanel(id="system-panel")
        yield Dashboard(id="dashboard")
        yield CpuHistory(id="cpu-history")
        yield SystemInspector(id="system-inspector")

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        self.query_one(
            SystemPanel
        ).update_snapshot(snapshot)

        self.query_one(
            Dashboard
        ).update_snapshot(snapshot)

        self.query_one(
            CpuHistory
        ).add_sample(snapshot.cpu_usage)

        self.query_one(
            SystemInspector
        ).update_snapshot(snapshot)

    def show_error(
        self,
        error: Exception,
    ) -> None:
        self.query_one(SystemPanel).update(
            "[b red]● TELEMETRY ERROR[/b red]\n\n"
            f"{type(error).__name__}: {error}"
        )
