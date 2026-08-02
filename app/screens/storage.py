from __future__ import annotations

from collections import deque
from statistics import mean

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Sparkline,
    Static,
)

from services.data_service import SystemSnapshot
from services.storage_action_service import (
    StorageActionResult,
    StorageActionService,
)


class StorageScreen(Vertical):
    """Filesystem, partition and physical drive control center."""

    HISTORY_SIZE = 60

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.read_history: deque[float] = deque(
            [0.0],
            maxlen=self.HISTORY_SIZE,
        )
        self.write_history: deque[float] = deque(
            [0.0],
            maxlen=self.HISTORY_SIZE,
        )

        self.action_service = StorageActionService()

        self._device_names: tuple[str, ...] = ()
        self._partition_mounts: tuple[str, ...] = ()

        self._last_device_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

        self._last_partition_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

    def compose(self) -> ComposeResult:
        with Horizontal(id="storage-summary"):
            yield Static(
                "--",
                id="root-usage",
                classes="storage-card",
            )
            yield Static(
                "--",
                id="root-free",
                classes="storage-card",
            )
            yield Static(
                "--",
                id="disk-read-rate",
                classes="storage-card",
            )
            yield Static(
                "--",
                id="disk-write-rate",
                classes="storage-card",
            )

        with Horizontal(id="storage-history"):
            with Vertical(classes="storage-graph"):
                yield Static(
                    "[b]DISK READ // 60 SAMPLES[/b]",
                    classes="storage-graph-title",
                )
                yield Static(
                    "WAITING FOR TELEMETRY",
                    id="storage-read-stats",
                    classes="storage-graph-stats",
                )
                yield Sparkline(
                    [0.0],
                    min_color="#164657",
                    max_color="#36d7ff",
                    summary_function=max,
                    id="storage-read-history",
                )

            with Vertical(classes="storage-graph"):
                yield Static(
                    "[b]DISK WRITE // 60 SAMPLES[/b]",
                    classes="storage-graph-title",
                )
                yield Static(
                    "WAITING FOR TELEMETRY",
                    id="storage-write-stats",
                    classes="storage-graph-stats",
                )
                yield Sparkline(
                    [0.0],
                    min_color="#164657",
                    max_color="#36d7ff",
                    summary_function=max,
                    id="storage-write-history",
                )

        yield Static(
            "DRIVE HEALTH // WAITING FOR TELEMETRY",
            id="storage-health",
        )

        with Horizontal(id="storage-action-buttons"):
            yield Button(
                "SMART SELECTED",
                id="storage-action-smart",
                classes="storage-action-button",
                flat=True,
            )
            yield Button(
                "DRIVE MAP",
                id="storage-action-map",
                classes="storage-action-button",
                flat=True,
            )
            yield Button(
                "HOME USAGE",
                id="storage-action-home",
                classes="storage-action-button",
                flat=True,
            )
            yield Button(
                "OPEN LOCATION",
                id="storage-action-open",
                classes="storage-action-button",
                flat=True,
            )
            yield Button(
                "REFRESH",
                id="storage-action-refresh",
                classes="storage-action-button",
                flat=True,
            )

        yield Static(
            "PHYSICAL DRIVES // SELECT A ROW FOR SMART",
            id="storage-devices-title",
            classes="storage-table-title",
        )
        yield DataTable(id="storage-devices")

        yield Static(
            "PARTITIONS AND MOUNTS // SELECT A ROW TO OPEN",
            id="storage-partitions-title",
            classes="storage-table-title",
        )
        yield DataTable(id="storage-partitions")

        yield Static(
            "STORAGE ACTION ENGINE READY",
            id="storage-action-status",
        )

    def on_mount(self) -> None:
        device_table = self.query_one(
            "#storage-devices",
            DataTable,
        )
        device_table.cursor_type = "row"
        device_table.zebra_stripes = True
        device_table.add_columns(
            "DEVICE",
            "MODEL",
            "SIZE",
            "BUS",
            "TEMP",
            "SMART",
            "MOUNTS",
        )

        partition_table = self.query_one(
            "#storage-partitions",
            DataTable,
        )
        partition_table.cursor_type = "row"
        partition_table.zebra_stripes = True
        partition_table.add_columns(
            "PARTITION",
            "PARENT",
            "SIZE",
            "FILESYSTEM",
            "LABEL",
            "USED",
            "FREE",
            "MOUNTPOINT",
        )

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        storage = snapshot.storage

        self.read_history.append(
            storage.read_bps / 1024**2
        )
        self.write_history.append(
            storage.write_bps / 1024**2
        )

        self.query_one(
            "#root-usage",
            Static,
        ).update(
            "[b]ROOT USAGE[/b]\n\n"
            f"[b]{storage.root_percent:.1f}%[/b]\n"
            f"{self._format_bytes(storage.root_used)} USED"
        )

        self.query_one(
            "#root-free",
            Static,
        ).update(
            "[b]AVAILABLE[/b]\n\n"
            f"[b]{self._format_bytes(storage.root_free)}[/b]\n"
            f"OF {self._format_bytes(storage.root_total)}"
        )

        self.query_one(
            "#disk-read-rate",
            Static,
        ).update(
            "[b]READ RATE[/b]\n\n"
            f"[b]{self._format_rate(storage.read_bps)}[/b]"
        )

        self.query_one(
            "#disk-write-rate",
            Static,
        ).update(
            "[b]WRITE RATE[/b]\n\n"
            f"[b]{self._format_rate(storage.write_bps)}[/b]"
        )

        self._update_history()
        self._update_health(snapshot)
        self._update_device_table(snapshot)
        self._update_partition_table(snapshot)

    def _update_history(self) -> None:
        read_values = list(self.read_history)
        write_values = list(self.write_history)

        self.query_one(
            "#storage-read-history",
            Sparkline,
        ).data = read_values

        self.query_one(
            "#storage-write-history",
            Sparkline,
        ).data = write_values

        self.query_one(
            "#storage-read-stats",
            Static,
        ).update(
            self._history_stats(read_values)
        )

        self.query_one(
            "#storage-write-stats",
            Static,
        ).update(
            self._history_stats(write_values)
        )

    def _update_health(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        storage = snapshot.storage

        passed = sum(
            device.smart_status == "PASSED"
            for device in storage.devices
        )
        failed = sum(
            device.smart_status == "FAILED"
            for device in storage.devices
        )
        restricted = sum(
            device.smart_status
            in {"RESTRICTED", "UNAVAILABLE"}
            for device in storage.devices
        )

        hot_drives = tuple(
            device
            for device in storage.devices
            if (
                device.temperature_c is not None
                and device.temperature_c >= 70.0
            )
        )

        issues: list[str] = []
        state = "NOMINAL"
        color = "cyan"

        if failed:
            state = "CRITICAL"
            color = "red"
            issues.append(
                f"SMART FAILED {failed}"
            )

        if storage.root_percent >= 95:
            state = "CRITICAL"
            color = "red"
            issues.append(
                f"ROOT {storage.root_percent:.1f}%"
            )

        elif storage.root_percent >= 85:
            if state != "CRITICAL":
                state = "WARNING"
                color = "yellow"

            issues.append(
                f"ROOT {storage.root_percent:.1f}%"
            )

        if hot_drives:
            if state != "CRITICAL":
                state = "WARNING"
                color = "yellow"

            issues.append(
                f"HOT DRIVES {len(hot_drives)}"
            )

        details = (
            "    //    " + "    //    ".join(issues)
            if issues
            else "    //    ARRAY HEALTHY"
        )

        health = self.query_one(
            "#storage-health",
            Static,
        )
        health.remove_class("warning")
        health.remove_class("critical")

        if state == "WARNING":
            health.add_class("warning")

        if state == "CRITICAL":
            health.add_class("critical")

        health.update(
            f"[b {color}]● STORAGE {state}[/b {color}]"
            f"    //    DRIVES {len(storage.devices)}"
            f"    //    SMART PASSED {passed}"
            f"    //    LIMITED {restricted}"
            f"{details}"
            f"    //    UPDATED {snapshot.timestamp}"
        )

    def _update_device_table(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        rows = tuple(
            (
                f"/dev/{device.name}",
                device.model,
                self._format_bytes(
                    device.size_bytes
                ),
                device.transport,
                (
                    f"{device.temperature_c:.1f}°C"
                    if device.temperature_c is not None
                    else "N/A"
                ),
                device.smart_status,
                ", ".join(
                    device.mountpoints
                ) or "—",
            )
            for device in snapshot.storage.devices
        )

        self._device_names = tuple(
            device.name
            for device in snapshot.storage.devices
        )

        self.query_one(
            "#storage-devices-title",
            Static,
        ).update(
            "[b cyan]PHYSICAL DRIVES[/b cyan]"
            f"    //    TOTAL {len(rows)}"
            "    //    SELECT A ROW FOR SMART"
        )

        if rows == self._last_device_rows:
            return

        table = self.query_one(
            "#storage-devices",
            DataTable,
        )
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

        self._last_device_rows = rows

    def _update_partition_table(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        rows = tuple(
            (
                f"/dev/{partition.name}",
                f"/dev/{partition.parent}",
                self._format_bytes(
                    partition.size_bytes
                ),
                partition.filesystem,
                partition.label,
                (
                    f"{partition.used_percent:.1f}%"
                    if partition.used_percent is not None
                    else "N/A"
                ),
                (
                    self._format_bytes(
                        partition.free_bytes
                    )
                    if partition.free_bytes is not None
                    else "N/A"
                ),
                partition.mountpoint,
            )
            for partition in snapshot.storage.partitions
        )

        self._partition_mounts = tuple(
            partition.mountpoint
            for partition in snapshot.storage.partitions
        )

        mounted_count = sum(
            mountpoint not in {"", "—"}
            for mountpoint in self._partition_mounts
        )

        self.query_one(
            "#storage-partitions-title",
            Static,
        ).update(
            "[b cyan]PARTITIONS AND MOUNTS[/b cyan]"
            f"    //    TOTAL {len(rows)}"
            f"    //    MOUNTED {mounted_count}"
        )

        if rows == self._last_partition_rows:
            return

        table = self.query_one(
            "#storage-partitions",
            DataTable,
        )
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "—",
                "NO PARTITIONS DETECTED",
                "—",
                "—",
                "—",
                "—",
                "—",
            )

        self._last_partition_rows = rows

    def on_button_pressed(
        self,
        event: Button.Pressed,
    ) -> None:
        button_id = event.button.id

        if button_id == "storage-action-refresh":
            refresh = getattr(
                self.app,
                "refresh_snapshot",
                None,
            )

            if callable(refresh):
                refresh()

            self.query_one(
                "#storage-action-status",
                Static,
            ).update(
                "[b cyan]● REFRESH REQUESTED[/b cyan]"
                "    //    STORAGE TELEMETRY UPDATED"
            )

            event.stop()
            return

        actions = {
            "storage-action-smart": "smart",
            "storage-action-map": "drive-map",
            "storage-action-home": "home-usage",
            "storage-action-open": "open-location",
        }

        action_id = actions.get(button_id)

        if action_id is None:
            return

        result = self.action_service.launch(
            action_id,
            device_name=self._selected_device(),
            mountpoint=self._selected_mountpoint(),
        )

        self._show_action_result(result)
        self._log_action(result)
        event.stop()

    def _selected_device(self) -> str | None:
        if not self._device_names:
            return None

        row = self.query_one(
            "#storage-devices",
            DataTable,
        ).cursor_row

        if not 0 <= row < len(self._device_names):
            return None

        return self._device_names[row]

    def _selected_mountpoint(self) -> str:
        if not self._partition_mounts:
            return "/"

        row = self.query_one(
            "#storage-partitions",
            DataTable,
        ).cursor_row

        if not 0 <= row < len(
            self._partition_mounts
        ):
            return "/"

        mountpoint = self._partition_mounts[row]

        return (
            mountpoint
            if mountpoint not in {"", "—"}
            else "/"
        )

    def _show_action_result(
        self,
        result: StorageActionResult,
    ) -> None:
        color = {
            "LAUNCHED": "cyan",
            "UNAVAILABLE": "yellow",
            "FAILED": "red",
        }.get(result.status, "white")

        self.query_one(
            "#storage-action-status",
            Static,
        ).update(
            f"[b {color}]● {result.status}[/b {color}]"
            f"    //    {result.title}"
            f"    //    {result.detail}"
        )

    def _log_action(
        self,
        result: StorageActionResult,
    ) -> None:
        log_service = getattr(
            self.app,
            "log_service",
            None,
        )

        if log_service is None:
            return

        message = (
            f"{result.title}; "
            f"status={result.status}; "
            f"detail={result.detail}"
        )

        if result.status == "LAUNCHED":
            log_service.info(
                "STORAGE ACTION",
                message,
            )
        elif result.status == "UNAVAILABLE":
            log_service.warning(
                "STORAGE ACTION",
                message,
            )
        else:
            log_service.error(
                "STORAGE ACTION",
                message,
            )

    def show_error(
        self,
        error: Exception,
    ) -> None:
        self.query_one(
            "#storage-health",
            Static,
        ).update(
            "[b red]● STORAGE TELEMETRY ERROR[/b red]"
            f"    //    {type(error).__name__}: {error}"
        )

    @staticmethod
    def _history_stats(
        values: list[float],
    ) -> str:
        return (
            f"NOW {values[-1]:7.2f} MiB/s"
            f"  //  AVG {mean(values):7.2f}"
            f"  //  MAX {max(values):7.2f}"
        )

    @staticmethod
    def _format_rate(
        value: float,
    ) -> str:
        return (
            f"{StorageScreen._format_bytes(value)}/s"
        )

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
