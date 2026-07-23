from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from time import monotonic

import psutil


@dataclass(frozen=True, slots=True)
class DiskDevice:
    name: str
    model: str
    size_bytes: int
    transport: str
    mountpoints: tuple[str, ...]
    temperature_c: float | None
    smart_status: str


@dataclass(frozen=True, slots=True)
class StorageSample:
    root_total: int
    root_used: int
    root_free: int
    root_percent: float

    read_bps: float
    write_bps: float
    total_read_bytes: int
    total_write_bytes: int

    devices: tuple[DiskDevice, ...]


class StorageMonitor:
    """Collects filesystem, disk I/O and physical drive telemetry."""

    INVENTORY_REFRESH_SECONDS = 5.0
    SMART_REFRESH_SECONDS = 60.0

    def __init__(self) -> None:
        self._previous_io = None
        self._previous_time = monotonic()

        self._devices: tuple[DiskDevice, ...] = ()
        self._next_inventory_refresh = 0.0

        self._smart_cache: dict[str, str] = {}
        self._smart_checked_at: dict[str, float] = {}

    def sample(self) -> StorageSample:
        now = monotonic()
        root = psutil.disk_usage("/")
        current_io = psutil.disk_io_counters(nowrap=True)

        read_bps = 0.0
        write_bps = 0.0
        total_read_bytes = 0
        total_write_bytes = 0

        if current_io is not None:
            total_read_bytes = int(current_io.read_bytes)
            total_write_bytes = int(current_io.write_bytes)

            if self._previous_io is not None:
                elapsed = max(now - self._previous_time, 0.001)

                read_bps = max(
                    0.0,
                    (current_io.read_bytes - self._previous_io.read_bytes)
                    / elapsed,
                )
                write_bps = max(
                    0.0,
                    (current_io.write_bytes - self._previous_io.write_bytes)
                    / elapsed,
                )

            self._previous_io = current_io

        self._previous_time = now

        if now >= self._next_inventory_refresh:
            self._devices = self._read_devices(now)
            self._next_inventory_refresh = (
                now + self.INVENTORY_REFRESH_SECONDS
            )

        return StorageSample(
            root_total=int(root.total),
            root_used=int(root.used),
            root_free=int(root.free),
            root_percent=float(root.percent),
            read_bps=read_bps,
            write_bps=write_bps,
            total_read_bytes=total_read_bytes,
            total_write_bytes=total_write_bytes,
            devices=self._devices,
        )

    def _read_devices(self, now: float) -> tuple[DiskDevice, ...]:
        try:
            output = subprocess.check_output(
                [
                    "lsblk",
                    "--json",
                    "--bytes",
                    "--output",
                    "NAME,TYPE,SIZE,MODEL,TRAN,MOUNTPOINTS",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            )
            payload = json.loads(output)

        except (
            OSError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ):
            return ()

        devices: list[DiskDevice] = []

        for item in payload.get("blockdevices", []):
            if item.get("type") != "disk":
                continue

            name = str(item.get("name") or "unknown")

            if name.startswith(("loop", "zram", "ram")):
                continue

            devices.append(
                DiskDevice(
                    name=name,
                    model=str(item.get("model") or "UNKNOWN").strip(),
                    size_bytes=self._to_int(item.get("size")),
                    transport=str(item.get("tran") or "UNKNOWN").upper(),
                    mountpoints=self._collect_mountpoints(item),
                    temperature_c=self._read_temperature(name),
                    smart_status=self._get_smart_status(name, now),
                )
            )

        return tuple(devices)

    def _get_smart_status(self, name: str, now: float) -> str:
        last_check = self._smart_checked_at.get(name, 0.0)

        if (
            name in self._smart_cache
            and now - last_check < self.SMART_REFRESH_SECONDS
        ):
            return self._smart_cache[name]

        status = self._read_smart_status(name)

        self._smart_cache[name] = status
        self._smart_checked_at[name] = now

        return status

    @staticmethod
    def _read_smart_status(name: str) -> str:
        helper = "/usr/local/lib/helm/helm-smart-status"
        device = f"/dev/{name}"

        if os.path.isfile(helper):
            command = [
                "sudo",
                "-n",
                helper,
                device,
            ]
        elif shutil.which("smartctl") is not None:
            command = [
                "smartctl",
                "-H",
                "-j",
                device,
            ]
        else:
            return "NOT INSTALLED"

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )

            combined_output = (
                f"{result.stdout}\n{result.stderr}"
            ).lower()

            if (
                "permission denied" in combined_output
                or "operation not permitted" in combined_output
                or "a password is required" in combined_output
            ):
                return "RESTRICTED"

            payload = json.loads(result.stdout or "{}")
            passed = payload.get("smart_status", {}).get("passed")

            if passed is True:
                return "PASSED"

            if passed is False:
                return "FAILED"

            return "UNKNOWN"

        except subprocess.TimeoutExpired:
            return "TIMEOUT"
        except (
            OSError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ):
            return "UNAVAILABLE"

    @staticmethod
    def _read_temperature(name: str) -> float | None:
        match = re.match(r"^(nvme\d+)(?:n\d+)?$", name)

        if match is None:
            return None

        controller = match.group(1)
        matching_hwmon: list[str] = []
        fallback_hwmon: list[str] = []

        for hwmon_dir in glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                with open(
                    os.path.join(hwmon_dir, "name"),
                    encoding="utf-8",
                ) as file:
                    sensor_name = file.read().strip().lower()
            except OSError:
                continue

            if "nvme" not in sensor_name:
                continue

            device_path = os.path.realpath(
                os.path.join(hwmon_dir, "device")
            )

            if controller in device_path:
                matching_hwmon.append(hwmon_dir)
            else:
                fallback_hwmon.append(hwmon_dir)

        candidates = matching_hwmon or fallback_hwmon

        def temperature_priority(path: str) -> tuple[int, str]:
            label_path = path.replace("_input", "_label")

            try:
                with open(label_path, encoding="utf-8") as file:
                    label = file.read().strip().lower()
            except OSError:
                label = ""

            return (
                0 if label == "composite" else 1,
                path,
            )

        for hwmon_dir in candidates:
            temperature_files = glob.glob(
                os.path.join(hwmon_dir, "temp*_input")
            )
            temperature_files.sort(key=temperature_priority)

            for temperature_file in temperature_files:
                try:
                    with open(
                        temperature_file,
                        encoding="utf-8",
                    ) as file:
                        temperature = (
                            float(file.read().strip()) / 1000.0
                        )

                    if -20.0 <= temperature <= 200.0:
                        return temperature

                except (OSError, ValueError):
                    continue

        return None

    @classmethod
    def _collect_mountpoints(
        cls,
        device: dict,
    ) -> tuple[str, ...]:
        mountpoints: set[str] = set()

        raw_mountpoints = device.get("mountpoints")

        if isinstance(raw_mountpoints, list):
            mountpoints.update(
                str(value)
                for value in raw_mountpoints
                if value
            )
        elif raw_mountpoints:
            mountpoints.add(str(raw_mountpoints))

        for child in device.get("children") or []:
            mountpoints.update(cls._collect_mountpoints(child))

        return tuple(sorted(mountpoints))

    @staticmethod
    def _to_int(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
