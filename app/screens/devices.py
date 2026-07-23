from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from services.data_service import SystemSnapshot


class DevicesScreen(Vertical):
    """Connected USB and serial device inventory."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_usb_rows: tuple[tuple[str, ...], ...] = ()
        self._last_serial_rows: tuple[tuple[str, ...], ...] = ()

    def compose(self) -> ComposeResult:
        with Horizontal(id="devices-summary"):
            yield Static("--", id="usb-count", classes="devices-card")
            yield Static("--", id="serial-count", classes="devices-card")
            yield Static("--", id="device-status", classes="devices-card")

        yield Static(
            "USB DEVICE BUS",
            classes="devices-section-title",
        )
        yield DataTable(id="usb-devices-table")

        yield Static(
            "SERIAL INTERFACES",
            classes="devices-section-title",
        )
        yield DataTable(id="serial-devices-table")

    def on_mount(self) -> None:
        usb_table = self.query_one(
            "#usb-devices-table",
            DataTable,
        )
        usb_table.cursor_type = "row"
        usb_table.zebra_stripes = True
        usb_table.add_columns(
            "BUS",
            "DEVICE",
            "VID:PID",
            "MANUFACTURER",
            "PRODUCT",
            "SERIAL",
            "SPEED",
        )

        serial_table = self.query_one(
            "#serial-devices-table",
            DataTable,
        )
        serial_table.cursor_type = "row"
        serial_table.zebra_stripes = True
        serial_table.add_columns(
            "PORT",
            "DRIVER",
            "MANUFACTURER",
            "DEVICE",
        )

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        devices = snapshot.devices

        self.query_one("#usb-count", Static).update(
            "[b]USB DEVICES[/b]\n\n"
            f"[b]{len(devices.usb_devices)}[/b]"
        )

        self.query_one("#serial-count", Static).update(
            "[b]SERIAL PORTS[/b]\n\n"
            f"[b]{len(devices.serial_devices)}[/b]"
        )

        serial_status = (
            "[b cyan]● SERIAL READY[/b cyan]"
            if devices.serial_devices
            else "[b #6a8790]● NO SERIAL LINK[/b #6a8790]"
        )

        self.query_one("#device-status", Static).update(
            "[b]DEVICE LINK[/b]\n\n"
            f"{serial_status}\n"
            f"UPDATED {snapshot.timestamp}"
        )

        usb_rows = tuple(
            (
                device.bus,
                device.device,
                f"{device.vendor_id}:{device.product_id}",
                device.manufacturer,
                device.product,
                device.serial,
                device.speed_mbps,
            )
            for device in devices.usb_devices
        )

        serial_rows = tuple(
            (
                device.path,
                device.driver,
                device.usb_manufacturer,
                device.usb_product,
            )
            for device in devices.serial_devices
        )

        if usb_rows != self._last_usb_rows:
            self._replace_usb_rows(usb_rows)
            self._last_usb_rows = usb_rows

        if serial_rows != self._last_serial_rows:
            self._replace_serial_rows(serial_rows)
            self._last_serial_rows = serial_rows

    def _replace_usb_rows(
        self,
        rows: tuple[tuple[str, ...], ...],
    ) -> None:
        table = self.query_one("#usb-devices-table", DataTable)
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "—",
                "—",
                "NO USB DEVICES DETECTED",
                "—",
                "—",
                "—",
            )

    def _replace_serial_rows(
        self,
        rows: tuple[tuple[str, ...], ...],
    ) -> None:
        table = self.query_one("#serial-devices-table", DataTable)
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "—",
                "NO SERIAL DEVICES CONNECTED",
                "—",
            )
