from __future__ import annotations

import glob
import grp
import os
import pwd
import stat
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic


@dataclass(frozen=True, slots=True)
class UsbDevice:
    sysfs_id: str
    bus: str
    device: str
    vendor_id: str
    product_id: str
    manufacturer: str
    product: str
    serial: str
    speed_mbps: str


@dataclass(frozen=True, slots=True)
class SerialDevice:
    path: str
    driver: str

    usb_product: str
    usb_manufacturer: str
    usb_vendor_id: str
    usb_product_id: str
    usb_serial: str

    accessible: bool
    permissions: str
    owner: str
    group: str


@dataclass(frozen=True, slots=True)
class DeviceEvent:
    sequence: int
    timestamp: str
    action: str
    category: str
    identifier: str
    description: str


@dataclass(frozen=True, slots=True)
class DeviceSample:
    usb_devices: tuple[UsbDevice, ...]
    serial_devices: tuple[SerialDevice, ...]
    events: tuple[DeviceEvent, ...]


class DeviceMonitor:
    """Collects USB/serial inventory and connection events."""

    REFRESH_SECONDS = 2.0
    EVENT_LIMIT = 100

    def __init__(self) -> None:
        self._cached_sample = DeviceSample((), (), ())
        self._next_refresh = 0.0

        self._initialized = False
        self._previous_usb: dict[str, UsbDevice] = {}
        self._previous_serial: dict[str, SerialDevice] = {}

        self._events: deque[DeviceEvent] = deque(
            maxlen=self.EVENT_LIMIT
        )
        self._event_sequence = 0

    def sample(self) -> DeviceSample:
        now = monotonic()

        if now < self._next_refresh:
            return self._cached_sample

        usb_devices = self._read_usb_devices()
        serial_devices = self._read_serial_devices()

        self._record_changes(
            usb_devices,
            serial_devices,
        )

        self._cached_sample = DeviceSample(
            usb_devices=usb_devices,
            serial_devices=serial_devices,
            events=tuple(self._events),
        )

        self._next_refresh = now + self.REFRESH_SECONDS
        return self._cached_sample

    def _record_changes(
        self,
        usb_devices: tuple[UsbDevice, ...],
        serial_devices: tuple[SerialDevice, ...],
    ) -> None:
        current_usb = {
            device.sysfs_id: device
            for device in usb_devices
        }
        current_serial = {
            device.path: device
            for device in serial_devices
        }

        if not self._initialized:
            self._previous_usb = current_usb
            self._previous_serial = current_serial
            self._initialized = True
            return

        for key in sorted(
            current_usb.keys() - self._previous_usb.keys()
        ):
            device = current_usb[key]

            self._add_event(
                action="CONNECTED",
                category="USB",
                identifier=(
                    f"{device.vendor_id}:{device.product_id}"
                ),
                description=(
                    f"{device.manufacturer} {device.product}"
                ),
            )

        for key in sorted(
            self._previous_usb.keys() - current_usb.keys()
        ):
            device = self._previous_usb[key]

            self._add_event(
                action="DISCONNECTED",
                category="USB",
                identifier=(
                    f"{device.vendor_id}:{device.product_id}"
                ),
                description=(
                    f"{device.manufacturer} {device.product}"
                ),
            )

        for path in sorted(
            current_serial.keys()
            - self._previous_serial.keys()
        ):
            device = current_serial[path]

            self._add_event(
                action="CONNECTED",
                category="SERIAL",
                identifier=device.path,
                description=(
                    f"{device.usb_manufacturer} "
                    f"{device.usb_product}"
                ),
            )

        for path in sorted(
            self._previous_serial.keys()
            - current_serial.keys()
        ):
            device = self._previous_serial[path]

            self._add_event(
                action="DISCONNECTED",
                category="SERIAL",
                identifier=device.path,
                description=(
                    f"{device.usb_manufacturer} "
                    f"{device.usb_product}"
                ),
            )

        self._previous_usb = current_usb
        self._previous_serial = current_serial

    def _add_event(
        self,
        *,
        action: str,
        category: str,
        identifier: str,
        description: str,
    ) -> None:
        self._event_sequence += 1

        self._events.append(
            DeviceEvent(
                sequence=self._event_sequence,
                timestamp=datetime.now().strftime("%H:%M:%S"),
                action=action,
                category=category,
                identifier=identifier,
                description=description,
            )
        )

    def _read_usb_devices(
        self,
    ) -> tuple[UsbDevice, ...]:
        devices: list[UsbDevice] = []

        for device_path in sorted(
            Path("/sys/bus/usb/devices").glob("*")
        ):
            vendor_id = self._read_text(
                device_path / "idVendor"
            )
            product_id = self._read_text(
                device_path / "idProduct"
            )

            if not vendor_id or not product_id:
                continue

            product = self._read_text(
                device_path / "product",
                default="USB DEVICE",
            )

            # Hide Linux root hubs and USB host controllers.
            if (
                vendor_id.lower() == "1d6b"
                or "host controller" in product.lower()
            ):
                continue

            devices.append(
                UsbDevice(
                    sysfs_id=device_path.name,
                    bus=self._read_text(
                        device_path / "busnum",
                        default="—",
                    ),
                    device=self._read_text(
                        device_path / "devnum",
                        default="—",
                    ),
                    vendor_id=vendor_id.upper(),
                    product_id=product_id.upper(),
                    manufacturer=self._read_text(
                        device_path / "manufacturer",
                        default="UNKNOWN",
                    ),
                    product=product,
                    serial=self._read_text(
                        device_path / "serial",
                        default="—",
                    ),
                    speed_mbps=self._format_speed(
                        self._read_text(
                            device_path / "speed",
                            default="—",
                        )
                    ),
                )
            )

        return tuple(devices)

    def _read_serial_devices(
        self,
    ) -> tuple[SerialDevice, ...]:
        paths = sorted(
            set(glob.glob("/dev/ttyUSB*"))
            | set(glob.glob("/dev/ttyACM*"))
        )

        devices: list[SerialDevice] = []

        for serial_path in paths:
            tty_name = os.path.basename(serial_path)
            sys_path = (
                Path("/sys/class/tty")
                / tty_name
                / "device"
            )

            try:
                resolved = sys_path.resolve()
            except OSError:
                resolved = sys_path

            driver = self._read_driver(resolved)
            usb_root = self._find_usb_parent(resolved)

            (
                permissions,
                owner,
                group,
            ) = self._read_permissions(serial_path)

            devices.append(
                SerialDevice(
                    path=serial_path,
                    driver=driver,

                    usb_product=(
                        self._read_text(
                            usb_root / "product",
                            default="SERIAL DEVICE",
                        )
                        if usb_root
                        else "SERIAL DEVICE"
                    ),
                    usb_manufacturer=(
                        self._read_text(
                            usb_root / "manufacturer",
                            default="UNKNOWN",
                        )
                        if usb_root
                        else "UNKNOWN"
                    ),
                    usb_vendor_id=(
                        self._read_text(
                            usb_root / "idVendor",
                            default="—",
                        ).upper()
                        if usb_root
                        else "—"
                    ),
                    usb_product_id=(
                        self._read_text(
                            usb_root / "idProduct",
                            default="—",
                        ).upper()
                        if usb_root
                        else "—"
                    ),
                    usb_serial=(
                        self._read_text(
                            usb_root / "serial",
                            default="—",
                        )
                        if usb_root
                        else "—"
                    ),

                    accessible=os.access(
                        serial_path,
                        os.R_OK | os.W_OK,
                    ),
                    permissions=permissions,
                    owner=owner,
                    group=group,
                )
            )

        return tuple(devices)

    @staticmethod
    def _read_permissions(
        path: str,
    ) -> tuple[str, str, str]:
        try:
            file_stat = os.stat(path)

            permissions = stat.filemode(
                file_stat.st_mode
            )

            try:
                owner = pwd.getpwuid(
                    file_stat.st_uid
                ).pw_name
            except KeyError:
                owner = str(file_stat.st_uid)

            try:
                group = grp.getgrgid(
                    file_stat.st_gid
                ).gr_name
            except KeyError:
                group = str(file_stat.st_gid)

            return permissions, owner, group

        except OSError:
            return "UNKNOWN", "UNKNOWN", "UNKNOWN"

    @staticmethod
    def _find_usb_parent(
        path: Path,
    ) -> Path | None:
        current = path

        for parent in (
            current,
            *current.parents,
        ):
            if (
                (parent / "idVendor").exists()
                and (parent / "idProduct").exists()
            ):
                return parent

        return None

    @staticmethod
    def _read_driver(path: Path) -> str:
        driver_link = path / "driver"

        try:
            return driver_link.resolve().name
        except OSError:
            return "UNKNOWN"

    @staticmethod
    def _read_text(
        path: Path,
        default: str = "",
    ) -> str:
        try:
            value = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()

            return value or default

        except OSError:
            return default

    @staticmethod
    def _format_speed(value: str) -> str:
        if not value or value == "—":
            return "—"

        try:
            speed = float(value)
        except ValueError:
            return value

        if speed >= 1000:
            return f"{speed / 1000:.1f} Gbps"

        return f"{speed:.0f} Mbps"
