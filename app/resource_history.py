from collections import deque
from statistics import mean

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Sparkline, Static

from services.data_service import SystemSnapshot


class ResourceHistory(Vertical):
    """Displays the latest 60 RAM and GPU usage samples."""

    HISTORY_SIZE = 60

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.ram_history: deque[float] = deque(
            [0.0],
            maxlen=self.HISTORY_SIZE,
        )
        self.gpu_history: deque[float] = deque(
            [0.0],
            maxlen=self.HISTORY_SIZE,
        )

    def compose(self) -> ComposeResult:
        with Horizontal(id="resource-history-graphs"):
            with Vertical(classes="resource-history-graph"):
                yield Static(
                    "[b]MEMORY LOAD // 60 SAMPLES[/b]",
                    classes="resource-history-title",
                )

                yield Static(
                    "WAITING FOR TELEMETRY",
                    id="ram-history-stats",
                    classes="resource-history-stats",
                )

                yield Sparkline(
                    [0.0],
                    min_color="#164657",
                    max_color="#36d7ff",
                    summary_function=max,
                    id="ram-history-sparkline",
                )

            with Vertical(classes="resource-history-graph"):
                yield Static(
                    "[b]GPU LOAD // 60 SAMPLES[/b]",
                    classes="resource-history-title",
                )

                yield Static(
                    "WAITING FOR TELEMETRY",
                    id="gpu-history-stats",
                    classes="resource-history-stats",
                )

                yield Sparkline(
                    [0.0],
                    min_color="#164657",
                    max_color="#36d7ff",
                    summary_function=max,
                    id="gpu-history-sparkline",
                )

    def add_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        ram_usage = self._safe_percent(
            snapshot.resources.memory_percent
        )
        gpu_usage = self._safe_percent(
            snapshot.gpu_usage or 0.0
        )

        self.ram_history.append(ram_usage)
        self.gpu_history.append(gpu_usage)

        ram_values = list(self.ram_history)
        gpu_values = list(self.gpu_history)

        self.query_one(
            "#ram-history-sparkline",
            Sparkline,
        ).data = ram_values

        self.query_one(
            "#gpu-history-sparkline",
            Sparkline,
        ).data = gpu_values

        self.query_one(
            "#ram-history-stats",
            Static,
        ).update(
            self._stats_text(ram_values)
        )

        if snapshot.gpu_usage is None:
            gpu_stats = "GPU TELEMETRY UNAVAILABLE"
        else:
            gpu_stats = self._stats_text(gpu_values)

        self.query_one(
            "#gpu-history-stats",
            Static,
        ).update(gpu_stats)

    @staticmethod
    def _stats_text(values: list[float]) -> str:
        return (
            f"NOW {values[-1]:5.1f}%"
            f"  //  AVG {mean(values):5.1f}%"
            f"  //  MAX {max(values):5.1f}%"
        )

    @staticmethod
    def _safe_percent(value: float) -> float:
        return max(
            0.0,
            min(float(value), 100.0),
        )
