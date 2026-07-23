from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Callable

from modules.devices import DeviceMonitor, DeviceSample
from modules.gpu import get_gpu_info
from modules.hardware import (
    get_cpu_temp,
    get_cpu_usage,
    get_ram_usage,
)
from modules.network import NetworkMonitor
from modules.projects import ProjectMonitor, ProjectSample
from modules.resources import ResourceMonitor, ResourceSample
from modules.storage import StorageMonitor, StorageSample
from modules.system import get_system_info


_MISSING = object()


@dataclass(slots=True)
class SystemSnapshot:
    timestamp: str

    cpu_usage: float
    cpu_temp: float | None
    ram_usage: float
    disk_usage: float

    gpu_usage: float | None
    gpu_temp: float | None
    gpu_memory: float | None
    gpu_power: float | None

    host: str
    user: str
    os_name: str
    kernel: str
    uptime: str

    network_interface: str
    network_ip: str
    network_link_speed: int
    network_online: bool
    network_download_bps: float
    network_upload_bps: float
    network_bytes_received: int
    network_bytes_sent: int

    storage: StorageSample
    devices: DeviceSample
    projects: ProjectSample
    resources: ResourceSample


@dataclass(frozen=True, slots=True)
class TelemetryIssue:
    source: str
    error_type: str
    message: str
    fallback_used: bool

    @property
    def signature(self) -> str:
        return (
            f"{self.error_type}: {self.message}; "
            f"fallback={self.fallback_used}"
        )


@dataclass(frozen=True, slots=True)
class TelemetryResult:
    sequence: int
    started_at: str
    finished_at: str
    duration_ms: float
    snapshot: SystemSnapshot | None
    issues: tuple[TelemetryIssue, ...]

    @property
    def state(self) -> str:
        if self.snapshot is None:
            return "FAILED"

        if self.issues:
            return "DEGRADED"

        return "NOMINAL"


class DataService:
    """Fault-tolerant HELM telemetry collection engine."""

    def __init__(self) -> None:
        self.network_monitor = NetworkMonitor()
        self.storage_monitor = StorageMonitor()
        self.device_monitor = DeviceMonitor()
        self.project_monitor = ProjectMonitor()
        self.resource_monitor = ResourceMonitor()

        self._last_snapshot: SystemSnapshot | None = None

    def collect(self) -> SystemSnapshot:
        """Compatibility wrapper returning only the snapshot."""
        result = self.collect_result(
            sequence=0,
            previous_snapshot=self._last_snapshot,
        )

        if result.snapshot is None:
            details = "; ".join(
                (
                    f"{issue.source}: "
                    f"{issue.error_type}: "
                    f"{issue.message}"
                )
                for issue in result.issues
            )

            raise RuntimeError(
                details
                or "Telemetry collection failed."
            )

        return result.snapshot

    def collect_result(
        self,
        sequence: int,
        previous_snapshot: SystemSnapshot | None = None,
    ) -> TelemetryResult:
        started_at = datetime.now()
        started_clock = perf_counter()

        previous = (
            previous_snapshot
            or self._last_snapshot
        )

        issues: list[TelemetryIssue] = []

        def capture(
            source: str,
            operation: Callable[[], object],
            fallback: object = _MISSING,
        ) -> object:
            try:
                return operation()

            except Exception as error:
                issues.append(
                    TelemetryIssue(
                        source=source,
                        error_type=type(error).__name__,
                        message=self._error_message(error),
                        fallback_used=(
                            fallback is not _MISSING
                        ),
                    )
                )

                return fallback

        system_fallback = {
            "host": (
                previous.host
                if previous is not None
                else "unknown"
            ),
            "user": (
                previous.user
                if previous is not None
                else "unknown"
            ),
            "os": (
                previous.os_name
                if previous is not None
                else "unknown"
            ),
            "kernel": (
                previous.kernel
                if previous is not None
                else "unknown"
            ),
            "uptime": (
                previous.uptime
                if previous is not None
                else "unknown"
            ),
        }

        def read_system() -> dict:
            value = get_system_info()

            if not isinstance(value, dict):
                raise TypeError(
                    "System information is not a dictionary."
                )

            return value

        system_info = capture(
            "SYSTEM",
            read_system,
            system_fallback,
        )

        gpu_fallback = {
            "usage": (
                previous.gpu_usage
                if previous is not None
                else None
            ),
            "temp": (
                previous.gpu_temp
                if previous is not None
                else None
            ),
            "memory": (
                previous.gpu_memory
                if previous is not None
                else None
            ),
            "power": (
                previous.gpu_power
                if previous is not None
                else None
            ),
        }

        def read_gpu() -> dict:
            value = get_gpu_info()

            if not isinstance(value, dict):
                raise TypeError(
                    "GPU information is not a dictionary."
                )

            return value

        gpu_info = capture(
            "GPU",
            read_gpu,
            gpu_fallback,
        )

        cpu_usage = capture(
            "CPU LOAD",
            get_cpu_usage,
            (
                previous.cpu_usage
                if previous is not None
                else 0.0
            ),
        )

        cpu_temp = capture(
            "CPU TEMPERATURE",
            get_cpu_temp,
            (
                previous.cpu_temp
                if previous is not None
                else None
            ),
        )

        ram_usage = capture(
            "RAM",
            get_ram_usage,
            (
                previous.ram_usage
                if previous is not None
                else 0.0
            ),
        )

        network_fallback = {
            "interface": (
                previous.network_interface
                if previous is not None
                else "unknown"
            ),
            "ip": (
                previous.network_ip
                if previous is not None
                else "N/A"
            ),
            "link_speed": (
                previous.network_link_speed
                if previous is not None
                else 0
            ),
            "online": (
                previous.network_online
                if previous is not None
                else False
            ),
            "download_bps": (
                previous.network_download_bps
                if previous is not None
                else 0.0
            ),
            "upload_bps": (
                previous.network_upload_bps
                if previous is not None
                else 0.0
            ),
            "received": (
                previous.network_bytes_received
                if previous is not None
                else 0
            ),
            "sent": (
                previous.network_bytes_sent
                if previous is not None
                else 0
            ),
        }

        def read_network() -> dict:
            network = self.network_monitor.sample()

            return {
                "interface": network.interface,
                "ip": network.ip_address,
                "link_speed": network.link_speed_mbps,
                "online": network.is_up,
                "download_bps": network.download_bps,
                "upload_bps": network.upload_bps,
                "received": network.bytes_received,
                "sent": network.bytes_sent,
            }

        network = capture(
            "NETWORK",
            read_network,
            network_fallback,
        )

        storage = capture(
            "STORAGE",
            self.storage_monitor.sample,
            (
                previous.storage
                if previous is not None
                else _MISSING
            ),
        )

        devices = capture(
            "DEVICES",
            self.device_monitor.sample,
            (
                previous.devices
                if previous is not None
                else _MISSING
            ),
        )

        projects = capture(
            "PROJECTS",
            self.project_monitor.sample,
            (
                previous.projects
                if previous is not None
                else _MISSING
            ),
        )

        resources = capture(
            "RESOURCES",
            self.resource_monitor.sample,
            (
                previous.resources
                if previous is not None
                else _MISSING
            ),
        )

        required_components = {
            "STORAGE": storage,
            "DEVICES": devices,
            "PROJECTS": projects,
            "RESOURCES": resources,
        }

        missing_components = [
            source
            for source, value
            in required_components.items()
            if value is _MISSING
        ]

        snapshot: SystemSnapshot | None

        if missing_components:
            snapshot = None

        else:
            assert isinstance(system_info, dict)
            assert isinstance(gpu_info, dict)
            assert isinstance(network, dict)

            snapshot = SystemSnapshot(
                timestamp=datetime.now().strftime(
                    "%H:%M:%S"
                ),

                cpu_usage=self._to_float(
                    cpu_usage,
                    default=(
                        previous.cpu_usage
                        if previous is not None
                        else 0.0
                    ),
                ),
                cpu_temp=self._to_optional_float(
                    cpu_temp
                ),
                ram_usage=self._to_float(
                    ram_usage,
                    default=(
                        previous.ram_usage
                        if previous is not None
                        else 0.0
                    ),
                ),
                disk_usage=storage.root_percent,

                gpu_usage=self._to_optional_float(
                    gpu_info.get("usage")
                ),
                gpu_temp=self._to_optional_float(
                    gpu_info.get("temp")
                ),
                gpu_memory=self._to_optional_float(
                    gpu_info.get("memory")
                ),
                gpu_power=self._to_optional_float(
                    gpu_info.get("power")
                ),

                host=str(
                    system_info.get(
                        "host",
                        "unknown",
                    )
                ),
                user=str(
                    system_info.get(
                        "user",
                        "unknown",
                    )
                ),
                os_name=str(
                    system_info.get(
                        "os",
                        "unknown",
                    )
                ),
                kernel=str(
                    system_info.get(
                        "kernel",
                        "unknown",
                    )
                ),
                uptime=str(
                    system_info.get(
                        "uptime",
                        "unknown",
                    )
                ),

                network_interface=str(
                    network["interface"]
                ),
                network_ip=str(
                    network["ip"]
                ),
                network_link_speed=int(
                    network["link_speed"]
                ),
                network_online=bool(
                    network["online"]
                ),
                network_download_bps=float(
                    network["download_bps"]
                ),
                network_upload_bps=float(
                    network["upload_bps"]
                ),
                network_bytes_received=int(
                    network["received"]
                ),
                network_bytes_sent=int(
                    network["sent"]
                ),

                storage=storage,
                devices=devices,
                projects=projects,
                resources=resources,
            )

            self._last_snapshot = snapshot

        finished_at = datetime.now()

        return TelemetryResult(
            sequence=int(sequence),
            started_at=started_at.isoformat(
                timespec="milliseconds"
            ),
            finished_at=finished_at.isoformat(
                timespec="milliseconds"
            ),
            duration_ms=(
                perf_counter() - started_clock
            ) * 1000.0,
            snapshot=snapshot,
            issues=tuple(issues),
        )

    @staticmethod
    def _error_message(
        error: Exception,
    ) -> str:
        message = " ".join(
            str(error).split()
        )

        if not message:
            message = "No error detail provided."

        return message[:300]

    @staticmethod
    def _to_float(
        value: object,
        default: float = 0.0,
    ) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_optional_float(
        value: object,
    ) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
