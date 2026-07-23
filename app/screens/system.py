from textual.app import ComposeResult
from textual.containers import Vertical

from app.cpu_history import CpuHistory
from app.dashboard import Dashboard
from app.system_panel import SystemPanel
from services.data_service import DataService


class SystemScreen(Vertical):
    """Main system monitoring screen."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.data_service = DataService()

    def compose(self) -> ComposeResult:
        yield SystemPanel(id="system-panel")
        yield Dashboard(id="dashboard")
        yield CpuHistory(id="cpu-history")

    def on_mount(self) -> None:
        self.refresh_snapshot()
        self.set_interval(1.0, self.refresh_snapshot)

    def refresh_snapshot(self) -> None:
        try:
            snapshot = self.data_service.collect()

            self.query_one(SystemPanel).update_snapshot(snapshot)
            self.query_one(Dashboard).update_snapshot(snapshot)
            self.query_one(CpuHistory).add_sample(snapshot.cpu_usage)

        except Exception as error:
            self.query_one(SystemPanel).update(
                "[b red]● TELEMETRY ERROR[/b red]\n\n"
                f"{type(error).__name__}: {error}"
            )
