from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from services.data_service import SystemSnapshot


class MetricBox(Static):
    """Single telemetry tile."""

    def __init__(self, title: str, widget_id: str) -> None:
        super().__init__(id=widget_id)
        self.title = title

    def set_value(self, value: str) -> None:
        self.update(f"[b]{self.title}[/b]\n\n{value}")


class Dashboard(Horizontal):
    """Displays hardware telemetry without collecting data itself."""

    def compose(self) -> ComposeResult:
        yield MetricBox("CPU", "cpu-box")
        yield MetricBox("GPU", "gpu-box")
        yield MetricBox("RAM", "ram-box")
        yield MetricBox("STORAGE", "storage-box")

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        cpu_temp = self._format_value(snapshot.cpu_temp, "°C")
        gpu_usage = self._format_value(snapshot.gpu_usage, "%")
        gpu_temp = self._format_value(snapshot.gpu_temp, "°C")
        gpu_power = self._format_value(snapshot.gpu_power, " W")

        self.query_one("#cpu-box", MetricBox).set_value(
            f"{snapshot.cpu_usage:.1f}%\n{cpu_temp}"
        )

        self.query_one("#gpu-box", MetricBox).set_value(
            f"{gpu_usage}\n{gpu_temp}\n{gpu_power}"
        )

        self.query_one("#ram-box", MetricBox).set_value(
            f"{snapshot.ram_usage:.1f}%"
        )

        self.query_one("#storage-box", MetricBox).set_value(
            f"{snapshot.disk_usage:.1f}%"
        )

    @staticmethod
    def _format_value(value: float | None, suffix: str) -> str:
        if value is None:
            return "N/A"

        return f"{value:.1f}{suffix}"
