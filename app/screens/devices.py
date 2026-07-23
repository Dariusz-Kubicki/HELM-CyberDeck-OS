from __future__ import annotations

from queue import Empty, Queue

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Input,
    RichLog,
    Static,
)
from textual.worker import Worker, get_current_worker

from modules.devices import (
    DeviceEvent,
    SerialDevice,
)
from services.data_service import SystemSnapshot
from services.device_action_service import (
    DeviceActionResult,
    DeviceActionService,
)


class DevicesScreen(Vertical):
    """USB inventory and interactive serial laboratory."""

    BAUD_RATES = (
        9600,
        19200,
        38400,
        57600,
        115200,
        230400,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.action_service = DeviceActionService()

        self.serial_devices: tuple[
            SerialDevice,
            ...,
        ] = ()

        self.baud_rate = 115200

        self._last_usb_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

        self._last_serial_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

        self._last_event_sequence = 0

        self._serial_worker: Worker[None] | None = None
        self._serial_port: str | None = None
        self._serial_connected = False

        self._serial_tx_queue: Queue[bytes] = Queue()

    def compose(self) -> ComposeResult:
        with Horizontal(id="devices-summary"):
            yield Static(
                "--",
                id="usb-count",
                classes="devices-card",
            )
            yield Static(
                "--",
                id="serial-count",
                classes="devices-card",
            )
            yield Static(
                "--",
                id="serial-access-count",
                classes="devices-card",
            )
            yield Static(
                "--",
                id="device-status",
                classes="devices-card",
            )

        yield Static(
            "[b cyan]● DEVICE ENGINE ONLINE[/b cyan]"
            "    //    WAITING FOR HARDWARE EVENTS",
            id="device-health",
        )

        with Horizontal(id="device-action-buttons"):
            yield Button(
                "ARDUINO IDE",
                id="device-action-arduino",
                classes="device-action-button",
            )
            yield Button(
                "CONNECT UART",
                id="device-action-connect",
                classes="device-action-button",
            )
            yield Button(
                "DISCONNECT",
                id="device-action-disconnect",
                classes="device-action-button",
            )
            yield Button(
                "PORT INFO",
                id="device-action-info",
                classes="device-action-button",
            )
            yield Button(
                "REFRESH",
                id="device-action-refresh",
                classes="device-action-button",
            )
            yield Button(
                "CLEAR CONSOLE",
                id="device-action-clear",
                classes="device-action-button",
            )

        yield Static(
            "SELECT A SERIAL INTERFACE",
            id="selected-device-details",
        )

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

        with Horizontal(id="serial-console-header"):
            yield Static(
                "[b cyan]UART CONSOLE[/b cyan]"
                "    //    BIDIRECTIONAL SERIAL LINK",
                id="serial-console-title",
            )

            with Horizontal(id="serial-baud-control"):
                yield Button(
                    "◀",
                    id="device-baud-prev",
                    classes="serial-baud-arrow",
                )
                yield Static(
                    self._baud_label(),
                    id="serial-baud-value",
                )
                yield Button(
                    "▶",
                    id="device-baud-next",
                    classes="serial-baud-arrow",
                )

        with Horizontal(id="device-console-grid"):
            with Vertical(classes="device-console-panel"):
                yield Static(
                    "SERIAL DATA STREAM",
                    classes="device-console-panel-title",
                )
                yield RichLog(
                    id="serial-console",
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                    max_lines=2000,
                )

            with Vertical(classes="device-console-panel"):
                yield Static(
                    "USB / SERIAL EVENT TIMELINE",
                    classes="device-console-panel-title",
                )
                yield RichLog(
                    id="device-event-log",
                    markup=True,
                    wrap=True,
                    auto_scroll=True,
                    max_lines=500,
                )

        with Horizontal(id="serial-command-row"):
            yield Input(
                placeholder=(
                    "Send text to the connected Arduino/ESP32..."
                ),
                id="serial-command-input",
            )
            yield Button(
                "SEND",
                id="device-action-send",
                variant="primary",
            )

        yield Static(
            "[b #6a8790]● UART DISCONNECTED[/b #6a8790]"
            "    //    SELECT A SERIAL PORT",
            id="device-action-status",
        )

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
            "VID:PID",
            "DRIVER",
            "ACCESS",
            "GROUP",
            "MANUFACTURER",
            "DEVICE",
            "SERIAL",
        )

        self.query_one(
            "#serial-console",
            RichLog,
        ).write(
            "[b cyan]HELM UART CONSOLE[/b cyan]\n"
            "Select a serial interface and press CONNECT UART."
        )

        self.query_one(
            "#device-event-log",
            RichLog,
        ).write(
            "[b cyan]DEVICE EVENT ENGINE READY[/b cyan]\n"
            "New USB and serial events will appear here."
        )

    def on_unmount(self) -> None:
        self._disconnect_serial(silent=True)

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        devices = snapshot.devices
        self.serial_devices = devices.serial_devices

        accessible_count = sum(
            device.accessible
            for device in devices.serial_devices
        )

        blocked_count = (
            len(devices.serial_devices)
            - accessible_count
        )

        self.query_one(
            "#usb-count",
            Static,
        ).update(
            "[b]USB DEVICES[/b]\n\n"
            f"[b]{len(devices.usb_devices)}[/b]"
        )

        self.query_one(
            "#serial-count",
            Static,
        ).update(
            "[b]SERIAL PORTS[/b]\n\n"
            f"[b]{len(devices.serial_devices)}[/b]"
        )

        self.query_one(
            "#serial-access-count",
            Static,
        ).update(
            "[b]UART ACCESS[/b]\n\n"
            f"[b]{accessible_count} READY[/b]\n"
            f"{blocked_count} BLOCKED"
        )

        if self._serial_connected:
            link_status = (
                "[b cyan]● UART CONNECTED[/b cyan]"
            )
        elif devices.serial_devices:
            link_status = (
                "[b #70a9b8]● UART AVAILABLE[/b #70a9b8]"
            )
        else:
            link_status = (
                "[b #6a8790]● NO SERIAL LINK[/b #6a8790]"
            )

        self.query_one(
            "#device-status",
            Static,
        ).update(
            "[b]DEVICE LINK[/b]\n\n"
            f"{link_status}\n"
            f"UPDATED {snapshot.timestamp}"
        )

        health = self.query_one(
            "#device-health",
            Static,
        )

        health.remove_class("warning")
        health.remove_class("critical")

        if blocked_count:
            health.add_class("warning")
            health.update(
                "[b yellow]● DEVICE ACCESS WARNING[/b yellow]"
                f"    //    BLOCKED SERIAL PORTS {blocked_count}"
                "    //    CHECK PORT PERMISSIONS"
            )
        else:
            health.update(
                "[b cyan]● DEVICE BUS NOMINAL[/b cyan]"
                f"    //    USB {len(devices.usb_devices)}"
                f"    //    SERIAL {len(devices.serial_devices)}"
                "    //    ACCESS READY"
            )

        usb_rows = tuple(
            (
                device.bus,
                device.device,
                (
                    f"{device.vendor_id}:"
                    f"{device.product_id}"
                ),
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
                (
                    f"{device.usb_vendor_id}:"
                    f"{device.usb_product_id}"
                ),
                device.driver,
                (
                    "READY"
                    if device.accessible
                    else "BLOCKED"
                ),
                device.group,
                device.usb_manufacturer,
                device.usb_product,
                device.usb_serial,
            )
            for device in devices.serial_devices
        )

        if usb_rows != self._last_usb_rows:
            self._replace_usb_rows(usb_rows)
            self._last_usb_rows = usb_rows

        if serial_rows != self._last_serial_rows:
            self._replace_serial_rows(serial_rows)
            self._last_serial_rows = serial_rows

        self._update_selected_device()
        self._append_device_events(devices.events)

        active_paths = {
            device.path
            for device in devices.serial_devices
        }

        if (
            self._serial_port
            and self._serial_port not in active_paths
        ):
            self._disconnect_serial()

            self._set_action_status(
                "PORT REMOVED",
                (
                    f"{self._serial_port or 'serial port'} "
                    "was disconnected"
                ),
                color="yellow",
            )

    def _replace_usb_rows(
        self,
        rows: tuple[tuple[str, ...], ...],
    ) -> None:
        table = self.query_one(
            "#usb-devices-table",
            DataTable,
        )
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
        table = self.query_one(
            "#serial-devices-table",
            DataTable,
        )
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "—",
                "—",
                "NO SERIAL DEVICES CONNECTED",
                "—",
                "—",
                "—",
                "—",
            )

    def on_data_table_row_highlighted(
        self,
        event: DataTable.RowHighlighted,
    ) -> None:
        if event.control.id == "serial-devices-table":
            self._update_selected_device()

    def _update_selected_device(self) -> None:
        device = self._selected_serial_device()
        panel = self.query_one(
            "#selected-device-details",
            Static,
        )

        if device is None:
            panel.update(
                "[b]SELECTED SERIAL INTERFACE[/b]\n\n"
                "No serial device selected."
            )
            return

        access_color = (
            "cyan"
            if device.accessible
            else "yellow"
        )
        access_text = (
            "READY"
            if device.accessible
            else "BLOCKED"
        )

        panel.update(
            "[b cyan]SELECTED SERIAL INTERFACE[/b cyan]\n\n"
            f"[b]PORT[/b]          {device.path}\n"
            f"[b]DEVICE[/b]        "
            f"{device.usb_manufacturer} "
            f"{device.usb_product}\n"
            f"[b]VID:PID[/b]       "
            f"{device.usb_vendor_id}:"
            f"{device.usb_product_id}\n"
            f"[b]SERIAL[/b]        {device.usb_serial}\n"
            f"[b]DRIVER[/b]        {device.driver}\n"
            f"[b]PERMISSIONS[/b]   {device.permissions}\n"
            f"[b]OWNER:GROUP[/b]   "
            f"{device.owner}:{device.group}\n"
            f"[b]ACCESS[/b]        "
            f"[b {access_color}]"
            f"{access_text}"
            f"[/b {access_color}]"
        )

    def _append_device_events(
        self,
        events: tuple[DeviceEvent, ...],
    ) -> None:
        event_log = self.query_one(
            "#device-event-log",
            RichLog,
        )

        new_events = tuple(
            event
            for event in events
            if event.sequence > self._last_event_sequence
        )

        for event in new_events:
            if event.action == "CONNECTED":
                color = "cyan"
                symbol = "+"
            else:
                color = "yellow"
                symbol = "-"

            event_log.write(
                f"[b {color}]"
                f"{event.timestamp}  {symbol} "
                f"{escape(event.action)}"
                f"[/b {color}]\n"
                f"{escape(event.category):<8} "
                f"{escape(event.identifier)}\n"
                f"{escape(event.description)}"
            )

            self._log_device_event(event)

            self._last_event_sequence = max(
                self._last_event_sequence,
                event.sequence,
            )

    def _log_device_event(
        self,
        event: DeviceEvent,
    ) -> None:
        log_service = getattr(
            self.app,
            "log_service",
            None,
        )

        if log_service is None:
            return

        message = (
            f"{event.action} {event.category}; "
            f"id={event.identifier}; "
            f"device={event.description}"
        )

        if event.action == "CONNECTED":
            log_service.info(
                "DEVICE EVENT",
                message,
            )
        else:
            log_service.warning(
                "DEVICE EVENT",
                message,
            )

    def on_button_pressed(
        self,
        event: Button.Pressed,
    ) -> None:
        button_id = event.button.id

        if button_id == "device-baud-prev":
            self._cycle_baud(-1)
            event.stop()
            return

        if button_id == "device-baud-next":
            self._cycle_baud(1)
            event.stop()
            return

        if button_id == "device-action-connect":
            self._connect_selected_serial()
            event.stop()
            return

        if button_id == "device-action-disconnect":
            self._disconnect_serial()
            event.stop()
            return

        if button_id == "device-action-clear":
            self.query_one(
                "#serial-console",
                RichLog,
            ).clear()

            self.query_one(
                "#serial-console",
                RichLog,
            ).write(
                "[b cyan]UART CONSOLE CLEARED[/b cyan]"
            )

            event.stop()
            return

        if button_id == "device-action-send":
            command_input = self.query_one(
                "#serial-command-input",
                Input,
            )

            self._send_serial(command_input.value)
            command_input.value = ""
            command_input.focus()

            event.stop()
            return

        if button_id == "device-action-refresh":
            refresh = getattr(
                self.app,
                "refresh_snapshot",
                None,
            )

            if callable(refresh):
                refresh()

            self._set_action_status(
                "REFRESH REQUESTED",
                "USB and serial inventory updated",
                color="cyan",
            )

            event.stop()
            return

        if button_id == "device-action-arduino":
            self._disconnect_serial(silent=True)

            result = self.action_service.launch(
                "arduino"
            )

            self._show_action_result(result)
            self._log_action(result)
            event.stop()
            return

        if button_id == "device-action-info":
            selected = self._selected_serial_device()

            result = self.action_service.launch(
                "port-info",
                serial_port=(
                    selected.path
                    if selected
                    else None
                ),
            )

            self._show_action_result(result)
            self._log_action(result)
            event.stop()

    def on_input_submitted(
        self,
        event: Input.Submitted,
    ) -> None:
        if event.input.id != "serial-command-input":
            return

        self._send_serial(event.value)
        event.input.value = ""
        event.stop()

    def _cycle_baud(self, direction: int) -> None:
        try:
            index = self.BAUD_RATES.index(
                self.baud_rate
            )
        except ValueError:
            index = 0

        index = (
            index + direction
        ) % len(self.BAUD_RATES)

        self.baud_rate = self.BAUD_RATES[index]

        self.query_one(
            "#serial-baud-value",
            Static,
        ).update(self._baud_label())

        if self._serial_worker is not None:
            self._set_action_status(
                "BAUD CHANGED",
                (
                    f"{self.baud_rate} requires "
                    "reconnecting the UART console"
                ),
                color="yellow",
            )

    def _baud_label(self) -> str:
        return f"{self.baud_rate} BAUD"

    def _selected_serial_device(
        self,
    ) -> SerialDevice | None:
        if not self.serial_devices:
            return None

        row = self.query_one(
            "#serial-devices-table",
            DataTable,
        ).cursor_row

        if not 0 <= row < len(self.serial_devices):
            return None

        return self.serial_devices[row]

    def _connect_selected_serial(self) -> None:
        selected = self._selected_serial_device()

        if selected is None:
            self._set_action_status(
                "NO PORT SELECTED",
                "Select a serial interface in the table",
                color="yellow",
            )
            return

        if not selected.accessible:
            self._set_action_status(
                "ACCESS BLOCKED",
                (
                    f"{selected.path} permissions "
                    f"{selected.permissions}; "
                    f"group {selected.group}"
                ),
                color="yellow",
            )
            return

        if (
            self._serial_worker is not None
            and not self._serial_worker.is_finished
        ):
            self._set_action_status(
                "UART ALREADY ACTIVE",
                "Disconnect the current session first",
                color="yellow",
            )
            return

        self._clear_tx_queue()

        self._serial_port = selected.path
        self._serial_connected = False

        self.query_one(
            "#serial-console",
            RichLog,
        ).write(
            "[b cyan]CONNECTING[/b cyan]"
            f"  {escape(selected.path)}"
            f"  //  {self.baud_rate} BAUD"
        )

        self._set_action_status(
            "CONNECTING",
            (
                f"{selected.path} at "
                f"{self.baud_rate} baud"
            ),
            color="cyan",
        )

        self._serial_worker = self._read_serial(
            selected.path,
            self.baud_rate,
        )

    def _disconnect_serial(
        self,
        *,
        silent: bool = False,
    ) -> None:
        if (
            self._serial_worker is not None
            and not self._serial_worker.is_finished
        ):
            self._serial_worker.cancel()

        if not silent:
            self._set_action_status(
                "DISCONNECTING",
                self._serial_port or "UART console",
                color="#70a9b8",
            )

    @work(
        thread=True,
        group="device-serial-console",
        exclusive=True,
        exit_on_error=False,
    )
    def _read_serial(
        self,
        port: str,
        baud_rate: int,
    ) -> None:
        worker = get_current_worker()
        serial_port = None
        failure: str | None = None
        receive_buffer = bytearray()

        try:
            import serial

            serial_port = serial.Serial(
                port=port,
                baudrate=baud_rate,
                timeout=0.2,
                write_timeout=0.5,
            )

            self.app.call_from_thread(
                self._serial_opened,
                port,
                baud_rate,
            )

            while not worker.is_cancelled:
                while not worker.is_cancelled:
                    try:
                        payload = (
                            self._serial_tx_queue
                            .get_nowait()
                        )
                    except Empty:
                        break

                    serial_port.write(payload)
                    serial_port.flush()

                    self.app.call_from_thread(
                        self._append_serial_tx,
                        payload,
                    )

                chunk = serial_port.read(
                    serial_port.in_waiting or 1
                )

                if not chunk:
                    continue

                receive_buffer.extend(chunk)

                while b"\n" in receive_buffer:
                    newline_index = (
                        receive_buffer.index(b"\n")
                    )

                    raw_line = bytes(
                        receive_buffer[:newline_index]
                    )

                    del receive_buffer[
                        :newline_index + 1
                    ]

                    text = raw_line.rstrip(
                        b"\r"
                    ).decode(
                        "utf-8",
                        errors="replace",
                    )

                    self.app.call_from_thread(
                        self._append_serial_rx,
                        text,
                    )

                if len(receive_buffer) >= 4096:
                    text = bytes(
                        receive_buffer
                    ).decode(
                        "utf-8",
                        errors="replace",
                    )

                    receive_buffer.clear()

                    self.app.call_from_thread(
                        self._append_serial_rx,
                        text,
                    )

        except ImportError:
            failure = (
                "pyserial is not installed in the HELM venv"
            )

        except Exception as error:
            failure = (
                f"{type(error).__name__}: {error}"
            )

        finally:
            if receive_buffer:
                text = bytes(
                    receive_buffer
                ).decode(
                    "utf-8",
                    errors="replace",
                )

                try:
                    self.app.call_from_thread(
                        self._append_serial_rx,
                        text,
                    )
                except RuntimeError:
                    pass

            if serial_port is not None:
                try:
                    serial_port.close()
                except Exception:
                    pass

            try:
                self.app.call_from_thread(
                    self._serial_closed,
                    port,
                    failure,
                )
            except RuntimeError:
                pass

    def _serial_opened(
        self,
        port: str,
        baud_rate: int,
    ) -> None:
        self._serial_connected = True
        self._serial_port = port

        self.query_one(
            "#serial-console",
            RichLog,
        ).write(
            "[b cyan]UART LINK ESTABLISHED[/b cyan]"
            f"  {escape(port)}"
            f"  //  {baud_rate} BAUD"
        )

        self._set_action_status(
            "UART CONNECTED",
            f"{port} at {baud_rate} baud",
            color="cyan",
        )

    def _serial_closed(
        self,
        port: str,
        failure: str | None,
    ) -> None:
        self._serial_connected = False
        self._serial_worker = None

        if self._serial_port == port:
            self._serial_port = None

        if failure:
            self.query_one(
                "#serial-console",
                RichLog,
            ).write(
                "[b red]UART ERROR[/b red]\n"
                f"{escape(failure)}"
            )

            self._set_action_status(
                "UART ERROR",
                failure,
                color="red",
            )
        else:
            self.query_one(
                "#serial-console",
                RichLog,
            ).write(
                "[b #70a9b8]"
                "UART LINK CLOSED"
                "[/b #70a9b8]"
                f"  {escape(port)}"
            )

            self._set_action_status(
                "UART DISCONNECTED",
                port,
                color="#70a9b8",
            )

    def _send_serial(self, text: str) -> None:
        command = text.rstrip("\r\n")

        if not command:
            return

        if not self._serial_connected:
            self._set_action_status(
                "UART DISCONNECTED",
                "Connect a serial interface before sending",
                color="yellow",
            )
            return

        payload = (
            command + "\n"
        ).encode(
            "utf-8",
            errors="replace",
        )

        self._serial_tx_queue.put(payload)

    def _append_serial_rx(self, text: str) -> None:
        if not text:
            return

        self.query_one(
            "#serial-console",
            RichLog,
        ).write(
            "[b cyan]RX[/b cyan]  "
            f"{escape(text)}"
        )

    def _append_serial_tx(self, payload: bytes) -> None:
        text = payload.decode(
            "utf-8",
            errors="replace",
        ).rstrip("\r\n")

        self.query_one(
            "#serial-console",
            RichLog,
        ).write(
            "[b yellow]TX[/b yellow]  "
            f"{escape(text)}"
        )

    def _clear_tx_queue(self) -> None:
        while True:
            try:
                self._serial_tx_queue.get_nowait()
            except Empty:
                break

    def _show_action_result(
        self,
        result: DeviceActionResult,
    ) -> None:
        color = {
            "LAUNCHED": "cyan",
            "UNAVAILABLE": "yellow",
            "FAILED": "red",
            "UNKNOWN ACTION": "red",
        }.get(result.status, "white")

        self._set_action_status(
            result.status,
            f"{result.title} // {result.detail}",
            color=color,
        )

    def _set_action_status(
        self,
        state: str,
        detail: str,
        *,
        color: str,
    ) -> None:
        self.query_one(
            "#device-action-status",
            Static,
        ).update(
            f"[b {color}]● {escape(state)}[/b {color}]"
            f"    //    {escape(detail)}"
        )

    def _log_action(
        self,
        result: DeviceActionResult,
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
                "DEVICE ACTION",
                message,
            )
        elif result.status == "UNAVAILABLE":
            log_service.warning(
                "DEVICE ACTION",
                message,
            )
        else:
            log_service.error(
                "DEVICE ACTION",
                message,
            )
