from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

import psutil


@dataclass(frozen=True, slots=True)
class ProcessSample:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    status: str


@dataclass(frozen=True, slots=True)
class ResourceSample:
    physical_cores: int
    logical_cores: int

    cpu_frequency_mhz: float | None
    cpu_max_frequency_mhz: float | None
    per_core_usage: tuple[float, ...]

    load_1: float
    load_5: float
    load_15: float

    memory_total: int
    memory_used: int
    memory_available: int
    memory_percent: float

    swap_total: int
    swap_used: int
    swap_free: int
    swap_percent: float

    top_processes: tuple[ProcessSample, ...]


class ResourceMonitor:
    """Collects detailed CPU, memory and process telemetry."""

    PROCESS_REFRESH_SECONDS = 2.0
    PROCESS_LIMIT = 12

    def __init__(self) -> None:
        self._cached_processes: tuple[ProcessSample, ...] = ()
        self._next_process_refresh = 0.0

        # Prime psutil's non-blocking CPU counters.
        psutil.cpu_percent(interval=None, percpu=True)

        for process in psutil.process_iter():
            try:
                process.cpu_percent(interval=None)
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

    def sample(self) -> ResourceSample:
        now = monotonic()

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        frequency = psutil.cpu_freq()
        load_1, load_5, load_15 = psutil.getloadavg()

        if now >= self._next_process_refresh:
            self._cached_processes = self._read_processes()
            self._next_process_refresh = (
                now + self.PROCESS_REFRESH_SECONDS
            )

        return ResourceSample(
            physical_cores=psutil.cpu_count(logical=False) or 0,
            logical_cores=psutil.cpu_count(logical=True) or 0,

            cpu_frequency_mhz=(
                float(frequency.current)
                if frequency is not None
                else None
            ),
            cpu_max_frequency_mhz=(
                float(frequency.max)
                if frequency is not None and frequency.max > 0
                else None
            ),
            per_core_usage=tuple(
                float(value)
                for value in psutil.cpu_percent(
                    interval=None,
                    percpu=True,
                )
            ),

            load_1=float(load_1),
            load_5=float(load_5),
            load_15=float(load_15),

            memory_total=int(memory.total),
            memory_used=int(memory.used),
            memory_available=int(memory.available),
            memory_percent=float(memory.percent),

            swap_total=int(swap.total),
            swap_used=int(swap.used),
            swap_free=int(swap.free),
            swap_percent=float(swap.percent),

            top_processes=self._cached_processes,
        )

    def _read_processes(self) -> tuple[ProcessSample, ...]:
        processes: list[ProcessSample] = []

        for process in psutil.process_iter(
            [
                "pid",
                "name",
                "status",
                "memory_info",
                "memory_percent",
            ]
        ):
            try:
                info = process.info
                memory_info = info.get("memory_info")

                processes.append(
                    ProcessSample(
                        pid=int(info["pid"]),
                        name=str(
                            info.get("name") or "unknown"
                        )[:40],
                        cpu_percent=max(
                            0.0,
                            float(
                                process.cpu_percent(
                                    interval=None
                                )
                            ),
                        ),
                        memory_percent=max(
                            0.0,
                            float(
                                info.get("memory_percent")
                                or 0.0
                            ),
                        ),
                        memory_rss=(
                            int(memory_info.rss)
                            if memory_info is not None
                            else 0
                        ),
                        status=str(
                            info.get("status") or "unknown"
                        ).upper(),
                    )
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
                TypeError,
                ValueError,
            ):
                continue

        processes.sort(
            key=lambda item: (
                item.cpu_percent,
                item.memory_percent,
                item.memory_rss,
            ),
            reverse=True,
        )

        return tuple(
            processes[:self.PROCESS_LIMIT]
        )
