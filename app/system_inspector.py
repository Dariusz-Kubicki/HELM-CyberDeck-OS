from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from services.data_service import SystemSnapshot


class SystemInspector(Vertical):
    """Detailed processor, memory and process inspector."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_process_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

    def compose(self) -> ComposeResult:
        with Horizontal(id="system-detail-summary"):
            yield Static(
                "--",
                id="cpu-topology",
                classes="system-detail-card",
            )
            yield Static(
                "--",
                id="cpu-clock",
                classes="system-detail-card",
            )
            yield Static(
                "--",
                id="memory-detail",
                classes="system-detail-card",
            )
            yield Static(
                "--",
                id="load-detail",
                classes="system-detail-card",
            )

        yield Static(
            "PER-CORE LOAD // WAITING FOR TELEMETRY",
            id="cpu-core-grid",
        )

        yield Static(
            "PROCESS INSPECTOR // TOP RESOURCE CONSUMERS",
            id="process-section-title",
        )

        yield DataTable(id="top-processes-table")

    def on_mount(self) -> None:
        table = self.query_one(
            "#top-processes-table",
            DataTable,
        )

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "PID",
            "PROCESS",
            "CPU",
            "RAM",
            "RSS",
            "STATE",
        )

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        resources = snapshot.resources

        self.query_one(
            "#cpu-topology",
            Static,
        ).update(
            "[b]CPU TOPOLOGY[/b]\n\n"
            f"[b]{resources.physical_cores}[/b] PHYSICAL\n"
            f"[b]{resources.logical_cores}[/b] LOGICAL"
        )

        current_frequency = self._format_frequency(
            resources.cpu_frequency_mhz
        )
        maximum_frequency = self._format_frequency(
            resources.cpu_max_frequency_mhz
        )

        self.query_one(
            "#cpu-clock",
            Static,
        ).update(
            "[b]CPU CLOCK[/b]\n\n"
            f"[b]{current_frequency}[/b]\n"
            f"MAX {maximum_frequency}"
        )

        self.query_one(
            "#memory-detail",
            Static,
        ).update(
            "[b]SYSTEM MEMORY[/b]\n\n"
            f"[b]{self._format_bytes(resources.memory_used)}[/b]"
            f" / {self._format_bytes(resources.memory_total)}\n"
            f"AVAILABLE "
            f"{self._format_bytes(resources.memory_available)}"
        )

        swap_text = (
            f"{resources.swap_percent:.1f}%"
            if resources.swap_total > 0
            else "DISABLED"
        )

        self.query_one(
            "#load-detail",
            Static,
        ).update(
            "[b]SYSTEM LOAD[/b]\n\n"
            f"{resources.load_1:.2f} / "
            f"{resources.load_5:.2f} / "
            f"{resources.load_15:.2f}\n"
            f"SWAP {swap_text}"
        )

        self.query_one(
            "#cpu-core-grid",
            Static,
        ).update(
            self._build_core_grid(
                resources.per_core_usage
            )
        )

        rows = tuple(
            (
                str(process.pid),
                process.name,
                f"{process.cpu_percent:6.1f}%",
                f"{process.memory_percent:5.1f}%",
                self._format_bytes(
                    process.memory_rss
                ),
                process.status,
            )
            for process in resources.top_processes
        )

        if rows == self._last_process_rows:
            return

        table = self.query_one(
            "#top-processes-table",
            DataTable,
        )
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "NO PROCESS DATA",
                "—",
                "—",
                "—",
                "—",
            )

        self._last_process_rows = rows

    @classmethod
    def _build_core_grid(
        cls,
        values: tuple[float, ...],
    ) -> str:
        if not values:
            return (
                "[b]PER-CORE LOAD[/b]\n\n"
                "No logical CPU data available."
            )

        cells = [
            cls._format_core(index, value)
            for index, value in enumerate(values)
        ]

        lines = [
            "    ".join(cells[index:index + 3])
            for index in range(0, len(cells), 3)
        ]

        return (
            "[b cyan]PER-CORE LOAD[/b cyan]"
            "    //    LOGICAL PROCESSORS\n\n"
            + "\n".join(lines)
        )

    @staticmethod
    def _format_core(
        index: int,
        value: float,
    ) -> str:
        safe_value = max(
            0.0,
            min(float(value), 100.0),
        )

        width = 8
        filled = round(
            safe_value / 100 * width
        )
        empty = width - filled

        return (
            f"C{index:02d} "
            f"[#36d7ff]{'█' * filled}[/#36d7ff]"
            f"[#12313a]{'░' * empty}[/#12313a] "
            f"{safe_value:5.1f}%"
        )

    @staticmethod
    def _format_frequency(
        value: float | None,
    ) -> str:
        if value is None or value <= 0:
            return "N/A"

        if value >= 1000:
            return f"{value / 1000:.2f} GHz"

        return f"{value:.0f} MHz"

    @staticmethod
    def _format_bytes(
        value: float,
    ) -> str:
        size = float(value)

        for unit in (
            "B",
            "KiB",
            "MiB",
            "GiB",
            "TiB",
        ):
            if size < 1024 or unit == "TiB":
                return f"{size:.1f} {unit}"

            size /= 1024

        return "0 B"
