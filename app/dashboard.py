from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import ProgressBar, Static

from services.data_service import SystemSnapshot


class MetricCard(Vertical):
    """Reusable telemetry card with a progress bar."""

    def __init__(self, title: str, metric_id: str) -> None:
        super().__init__(id=f"{metric_id}-card")
        self.title = title
        self.metric_id = metric_id

    def compose(self) -> ComposeResult:
        yield Static(
            f"[b]{self.title}[/b]",
            classes="metric-title",
        )

        yield Static(
            "--",
            id=f"{self.metric_id}-value",
            classes="metric-value",
        )

        yield ProgressBar(
            total=100,
            show_eta=False,
            show_percentage=False,
            id=f"{self.metric_id}-bar",
        )

        yield Static(
            "WAITING FOR TELEMETRY",
            id=f"{self.metric_id}-detail",
            classes="metric-detail",
        )

    def set_metric(
        self,
        progress: float,
        value: str,
        detail: str,
    ) -> None:
        safe_progress = max(0.0, min(float(progress), 100.0))

        self.query_one(
            f"#{self.metric_id}-value",
            Static,
        ).update(value)

        self.query_one(
            f"#{self.metric_id}-bar",
            ProgressBar,
        ).update(progress=safe_progress)

        self.query_one(
            f"#{self.metric_id}-detail",
            Static,
        ).update(detail)


class Dashboard(Horizontal):
    """Hardware telemetry dashboard."""

    def compose(self) -> ComposeResult:
        yield MetricCard("CPU CORE", "cpu")
        yield MetricCard("GPU CORE", "gpu")
        yield MetricCard("MEMORY", "ram")
        yield MetricCard("STORAGE", "storage")

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        cpu_temp = self._format_optional(snapshot.cpu_temp, "°C")

        self.query_one("#cpu-card", MetricCard).set_metric(
            progress=snapshot.cpu_usage,
            value=f"{snapshot.cpu_usage:.1f}%",
            detail=f"TEMP  {cpu_temp}",
        )

        gpu_usage = snapshot.gpu_usage or 0.0
        gpu_temp = self._format_optional(snapshot.gpu_temp, "°C")
        gpu_power = self._format_optional(snapshot.gpu_power, " W")

        self.query_one("#gpu-card", MetricCard).set_metric(
            progress=gpu_usage,
            value=self._format_optional(snapshot.gpu_usage, "%"),
            detail=f"TEMP {gpu_temp}  //  PWR {gpu_power}",
        )

        self.query_one("#ram-card", MetricCard).set_metric(
            progress=snapshot.ram_usage,
            value=f"{snapshot.ram_usage:.1f}%",
            detail="SYSTEM MEMORY LOAD",
        )

        self.query_one("#storage-card", MetricCard).set_metric(
            progress=snapshot.disk_usage,
            value=f"{snapshot.disk_usage:.1f}%",
            detail="ROOT PARTITION USED",
        )

    @staticmethod
    def _format_optional(
        value: float | None,
        suffix: str,
    ) -> str:
        if value is None:
            return "N/A"

        return f"{value:.1f}{suffix}"
