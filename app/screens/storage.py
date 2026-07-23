from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from services.data_service import SystemSnapshot


class StorageScreen(Vertical):
    """Filesystem and physical drive telemetry."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_rows: tuple[tuple[str, ...], ...] = ()

    def compose(self) -> ComposeResult:
        with Horizontal(id="storage-summary"):
            yield Static("--", id="root-usage", classes="storage-card")
            yield Static("--", id="root-free", classes="storage-card")
            yield Static("--", id="disk-read-rate", classes="storage-card")
            yield Static("--", id="disk-write-rate", classes="storage-card")

        yield Static(
            "DRIVE HEALTH // WAITING FOR TELEMETRY",
            id="storage-health",
        )

        yield DataTable(id="storage-devices")

    def on_mount(self) -> None:
        table = self.query_one("#storage-devices", DataTable)

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "DEVICE",
            "MODEL",
            "SIZE",
            "BUS",
            "TEMP",
            "SMART",
            "MOUNTS",
        )

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        storage = snapshot.storage

        self.query_one("#root-usage", Static).update(
            "[b]ROOT USAGE[/b]\n\n"
            f"[b]{storage.root_percent:.1f}%[/b]\n"
            f"{self._format_bytes(storage.root_used)} USED"
        )

        self.query_one("#root-free", Static).update(
            "[b]AVAILABLE[/b]\n\n"
            f"[b]{self._format_bytes(storage.root_free)}[/b]\n"
            f"OF {self._format_bytes(storage.root_total)}"
        )

        self.query_one("#disk-read-rate", Static).update(
            "[b]READ RATE[/b]\n\n"
            f"[b]{self._format_rate(storage.read_bps)}[/b]"
        )

        self.query_one("#disk-write-rate", Static).update(
            "[b]WRITE RATE[/b]\n\n"
            f"[b]{self._format_rate(storage.write_bps)}[/b]"
        )

        passed = sum(
            device.smart_status == "PASSED"
            for device in storage.devices
        )
        failed = sum(
            device.smart_status == "FAILED"
            for device in storage.devices
        )

        health_color = "red" if failed else "cyan"

        self.query_one("#storage-health", Static).update(
            f"[b {health_color}]● STORAGE ARRAY ACTIVE[/b {health_color}]"
            f"    //    DRIVES {len(storage.devices)}"
            f"    //    SMART PASSED {passed}"
            f"    //    FAILED {failed}"
            f"    //    UPDATED {snapshot.timestamp}"
        )

        rows = tuple(
            (
                f"/dev/{device.name}",
                device.model,
                self._format_bytes(device.size_bytes),
                device.transport,
                (
                    f"{device.temperature_c:.1f}°C"
                    if device.temperature_c is not None
                    else "N/A"
                ),
                device.smart_status,
                ", ".join(device.mountpoints) or "—",
            )
            for device in storage.devices
        )

        if rows == self._last_rows:
            return

        table = self.query_one("#storage-devices", DataTable)
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "NO PHYSICAL DRIVES DETECTED",
                "—",
                "—",
                "—",
                "—",
                "—",
            )

        self._last_rows = rows

    def show_error(self, error: Exception) -> None:
        self.query_one("#storage-health", Static).update(
            "[b red]● STORAGE TELEMETRY ERROR[/b red]"
            f"    //    {type(error).__name__}: {error}"
        )

    @staticmethod
    def _format_rate(value: float) -> str:
        return f"{StorageScreen._format_bytes(value)}/s"

    @staticmethod
    def _format_bytes(value: float) -> str:
        size = float(value)

        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if size < 1024 or unit == "TiB":
                return f"{size:.1f} {unit}"

            size /= 1024

        return "0 B"
