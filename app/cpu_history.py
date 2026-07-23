from collections import deque
from statistics import mean

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Sparkline, Static


class CpuHistory(Vertical):
    """Displays CPU load history from the latest 60 samples."""

    HISTORY_SIZE = 60

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.samples: deque[float] = deque(maxlen=self.HISTORY_SIZE)

    def compose(self) -> ComposeResult:
        with Horizontal(id="cpu-history-header"):
            yield Static(
                "[b]CPU LOAD HISTORY[/b]",
                id="cpu-history-title",
            )
            yield Static(
                "60 SEC // WAITING FOR DATA",
                id="cpu-history-stats",
            )

        yield Sparkline(
            [0.0],
            min_color="#164657",
            max_color="#36d7ff",
            summary_function=max,
            id="cpu-sparkline",
        )

    def add_sample(self, usage: float) -> None:
        safe_usage = max(0.0, min(float(usage), 100.0))
        self.samples.append(safe_usage)

        values = list(self.samples)

        self.query_one("#cpu-sparkline", Sparkline).data = values

        self.query_one("#cpu-history-stats", Static).update(
            f"NOW {safe_usage:5.1f}%  //  "
            f"AVG {mean(values):5.1f}%  //  "
            f"MAX {max(values):5.1f}%"
        )
