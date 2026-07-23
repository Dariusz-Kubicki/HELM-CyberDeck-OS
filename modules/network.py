from __future__ import annotations

import socket
from dataclasses import dataclass
from time import monotonic

import psutil


@dataclass(slots=True)
class NetworkSample:
    interface: str
    ip_address: str
    link_speed_mbps: int
    is_up: bool
    download_bps: float
    upload_bps: float
    bytes_received: int
    bytes_sent: int


class NetworkMonitor:
    """Collects telemetry for the active Linux network interface."""

    def __init__(self) -> None:
        self._last_interface: str | None = None
        self._last_received: int | None = None
        self._last_sent: int | None = None
        self._last_time = monotonic()

    def sample(self) -> NetworkSample:
        now = monotonic()
        interface = self._find_active_interface()

        stats_by_interface = psutil.net_if_stats()
        counters_by_interface = (
            psutil.net_io_counters(pernic=True, nowrap=True) or {}
        )

        stats = stats_by_interface.get(interface)
        counters = counters_by_interface.get(interface)

        is_up = bool(stats and stats.isup)
        link_speed = int(stats.speed) if stats and stats.speed > 0 else 0
        ip_address = self._get_ipv4_address(interface)

        download_bps = 0.0
        upload_bps = 0.0

        if counters is not None:
            elapsed = max(now - self._last_time, 0.001)

            if (
                self._last_interface == interface
                and self._last_received is not None
                and self._last_sent is not None
            ):
                download_bps = max(
                    0.0,
                    (counters.bytes_recv - self._last_received) / elapsed,
                )
                upload_bps = max(
                    0.0,
                    (counters.bytes_sent - self._last_sent) / elapsed,
                )

            self._last_received = counters.bytes_recv
            self._last_sent = counters.bytes_sent
            bytes_received = counters.bytes_recv
            bytes_sent = counters.bytes_sent
        else:
            self._last_received = None
            self._last_sent = None
            bytes_received = 0
            bytes_sent = 0

        self._last_interface = interface
        self._last_time = now

        return NetworkSample(
            interface=interface,
            ip_address=ip_address,
            link_speed_mbps=link_speed,
            is_up=is_up,
            download_bps=download_bps,
            upload_bps=upload_bps,
            bytes_received=bytes_received,
            bytes_sent=bytes_sent,
        )

    def _find_active_interface(self) -> str:
        default_interface = self._read_default_route()

        if default_interface:
            return default_interface

        for name, stats in psutil.net_if_stats().items():
            if name != "lo" and stats.isup:
                return name

        return "unknown"

    @staticmethod
    def _read_default_route() -> str | None:
        try:
            with open("/proc/net/route", encoding="utf-8") as route_file:
                next(route_file, None)

                for line in route_file:
                    fields = line.split()

                    if len(fields) < 4:
                        continue

                    destination = fields[1]
                    flags = int(fields[3], 16)

                    if destination == "00000000" and flags & 0x2:
                        return fields[0]

        except (OSError, ValueError):
            return None

        return None

    @staticmethod
    def _get_ipv4_address(interface: str) -> str:
        addresses = psutil.net_if_addrs().get(interface, [])

        for address in addresses:
            if address.family == socket.AF_INET:
                return address.address

        return "N/A"
