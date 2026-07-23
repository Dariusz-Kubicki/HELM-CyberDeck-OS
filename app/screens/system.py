from textual.app import ComposeResult
from textual.containers import Vertical

from app.cpu_history import CpuHistory
from app.dashboard import Dashboard
from app.system_panel import SystemPanel
from services.data_service import SystemSnapshot


class SystemScreen(Vertical):
    """Main system monitoring screen."""

    def compose(self) -> ComposeResult:
        yield SystemPanel(id="system-panel")
        yield Dashboard(id="dashboard")
        yield CpuHistory(id="cpu-history")

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        self.query_one(SystemPanel).update_snapshot(snapshot)
        self.query_one(Dashboard).update_snapshot(snapshot)
        self.query_one(CpuHistory).add_sample(snapshot.cpu_usage)

    def show_error(self, error: Exception) -> None:
        self.query_one(SystemPanel).update(
            "[b red]● TELEMETRY ERROR[/b red]\n\n"
            f"{type(error).__name__}: {error}"
        )
