from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from pathlib import Path
from time import monotonic


@dataclass(frozen=True, slots=True)
class UsbDevice:
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


@dataclass(frozen=True, slots=True)
class DeviceSample:
    usb_devices: tuple[UsbDevice, ...]
    serial_devices: tuple[SerialDevice, ...]


class DeviceMonitor:
    """Collects connected USB and serial device inventory."""

    REFRESH_SECONDS = 3.0

    def __init__(self) -> None:
        self._cached_sample = DeviceSample((), ())
        self._next_refresh = 0.0

    def sample(self) -> DeviceSample:
        now = monotonic()

        if now < self._next_refresh:
            return self._cached_sample

        self._cached_sample = DeviceSample(
            usb_devices=self._read_usb_devices(),
            serial_devices=self._read_serial_devices(),
        )
        self._next_refresh = now + self.REFRESH_SECONDS

        return self._cached_sample

    def _read_usb_devices(self) -> tuple[UsbDevice, ...]:
        devices: list[UsbDevice] = []

        for device_path in sorted(
            Path("/sys/bus/usb/devices").glob("*")
        ):
            vendor_id = self._read_text(device_path / "idVendor")
            product_id = self._read_text(device_path / "idProduct")

            if not vendor_id or not product_id:
                continue

            product = self._read_text(
                device_path / "product",
                default="USB DEVICE",
            )

            # Hide Linux root hubs and host controllers.
            if (
                vendor_id.lower() == "1d6b"
                or "host controller" in product.lower()
            ):
                continue

            devices.append(
                UsbDevice(
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

    def _read_serial_devices(self) -> tuple[SerialDevice, ...]:
        paths = sorted(
            set(glob.glob("/dev/ttyUSB*"))
            | set(glob.glob("/dev/ttyACM*"))
        )

        devices: list[SerialDevice] = []

        for serial_path in paths:
            tty_name = os.path.basename(serial_path)
            sys_path = Path("/sys/class/tty") / tty_name / "device"

            try:
                resolved = sys_path.resolve()
            except OSError:
                resolved = sys_path

            driver = self._read_driver(resolved)
            usb_root = self._find_usb_parent(resolved)

            devices.append(
                SerialDevice(
                    path=serial_path,
                    driver=driver,
                    usb_product=self._read_text(
                        usb_root / "product",
                        default="SERIAL DEVICE",
                    )
                    if usb_root
                    else "SERIAL DEVICE",
                    usb_manufacturer=self._read_text(
                        usb_root / "manufacturer",
                        default="UNKNOWN",
                    )
                    if usb_root
                    else "UNKNOWN",
                )
            )

        return tuple(devices)

    @staticmethod
    def _find_usb_parent(path: Path) -> Path | None:
        current = path

        for parent in (current, *current.parents):
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
