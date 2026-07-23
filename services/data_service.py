from dataclasses import dataclass
from datetime import datetime

from modules.devices import DeviceMonitor, DeviceSample
from modules.gpu import get_gpu_info
from modules.hardware import (
    get_cpu_temp,
    get_cpu_usage,
    get_ram_usage,
)
from modules.network import NetworkMonitor
from modules.projects import ProjectMonitor, ProjectSample
from modules.storage import StorageMonitor, StorageSample
from modules.system import get_system_info


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


class DataService:
    """Collects all HELM telemetry and operational data."""

    def __init__(self) -> None:
        self.network_monitor = NetworkMonitor()
        self.storage_monitor = StorageMonitor()
        self.device_monitor = DeviceMonitor()
        self.project_monitor = ProjectMonitor()

    def collect(self) -> SystemSnapshot:
        system_info = get_system_info()
        gpu_info = get_gpu_info()
        network = self.network_monitor.sample()
        storage = self.storage_monitor.sample()
        devices = self.device_monitor.sample()
        projects = self.project_monitor.sample()

        return SystemSnapshot(
            timestamp=datetime.now().strftime("%H:%M:%S"),

            cpu_usage=self._to_float(get_cpu_usage(), default=0.0),
            cpu_temp=self._to_optional_float(get_cpu_temp()),
            ram_usage=self._to_float(get_ram_usage(), default=0.0),
            disk_usage=storage.root_percent,

            gpu_usage=self._to_optional_float(gpu_info.get("usage")),
            gpu_temp=self._to_optional_float(gpu_info.get("temp")),
            gpu_memory=self._to_optional_float(gpu_info.get("memory")),
            gpu_power=self._to_optional_float(gpu_info.get("power")),

            host=str(system_info.get("host", "unknown")),
            user=str(system_info.get("user", "unknown")),
            os_name=str(system_info.get("os", "unknown")),
            kernel=str(system_info.get("kernel", "unknown")),
            uptime=str(system_info.get("uptime", "unknown")),

            network_interface=network.interface,
            network_ip=network.ip_address,
            network_link_speed=network.link_speed_mbps,
            network_online=network.is_up,
            network_download_bps=network.download_bps,
            network_upload_bps=network.upload_bps,
            network_bytes_received=network.bytes_received,
            network_bytes_sent=network.bytes_sent,

            storage=storage,
            devices=devices,
            projects=projects,
        )

    @staticmethod
    def _to_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_optional_float(value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
