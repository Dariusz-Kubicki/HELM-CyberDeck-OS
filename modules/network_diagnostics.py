from __future__ import annotations

import ipaddress
import os
import re
import shutil
import socket
import struct
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psutil


@dataclass(frozen=True, slots=True)
class SocketRecord:
    protocol: str
    local_address: str
    remote_address: str
    status: str
    pid: int | None
    process_name: str
    non_loopback: bool


@dataclass(frozen=True, slots=True)
class NetworkDiagnosticsSample:
    interface: str
    gateway: str
    dns_servers: tuple[str, ...]

    gateway_latency_ms: float | None
    gateway_packet_loss: float | None

    internet_latency_ms: float | None
    internet_packet_loss: float | None

    active_connections: int
    established_connections: int
    listening_sockets: int
    non_loopback_listeners: int

    errors_in: int
    errors_out: int
    drops_in: int
    drops_out: int

    connections: tuple[SocketRecord, ...]
    listeners: tuple[SocketRecord, ...]

    socket_access_limited: bool
    updated_at: str


class NetworkDiagnosticsMonitor:
    """Collects slower network diagnostics outside the UI thread."""

    INTERNET_PROBE = "1.1.1.1"
    CONNECTION_LIMIT = 18
    LISTENER_LIMIT = 18

    def collect(
        self,
        interface: str,
    ) -> NetworkDiagnosticsSample:
        gateway = self._read_default_gateway(interface)
        dns_servers = self._read_dns_servers(interface)

        gateway_latency, gateway_loss = self._ping(gateway)
        internet_latency, internet_loss = self._ping(
            self.INTERNET_PROBE
        )

        (
            connections,
            listeners,
            access_limited,
        ) = self._read_connections()

        counters = (
            psutil.net_io_counters(
                pernic=True,
                nowrap=True,
            )
            or {}
        ).get(interface)

        return NetworkDiagnosticsSample(
            interface=interface,
            gateway=gateway,
            dns_servers=dns_servers,

            gateway_latency_ms=gateway_latency,
            gateway_packet_loss=gateway_loss,

            internet_latency_ms=internet_latency,
            internet_packet_loss=internet_loss,

            active_connections=len(connections),
            established_connections=sum(
                connection.status == "ESTABLISHED"
                for connection in connections
            ),
            listening_sockets=len(listeners),
            non_loopback_listeners=sum(
                listener.non_loopback
                for listener in listeners
            ),

            errors_in=(
                int(counters.errin)
                if counters is not None
                else 0
            ),
            errors_out=(
                int(counters.errout)
                if counters is not None
                else 0
            ),
            drops_in=(
                int(counters.dropin)
                if counters is not None
                else 0
            ),
            drops_out=(
                int(counters.dropout)
                if counters is not None
                else 0
            ),

            connections=tuple(
                connections[:self.CONNECTION_LIMIT]
            ),
            listeners=tuple(
                listeners[:self.LISTENER_LIMIT]
            ),

            socket_access_limited=access_limited,
            updated_at=datetime.now().strftime("%H:%M:%S"),
        )

    @staticmethod
    def _read_default_gateway(
        preferred_interface: str,
    ) -> str:
        fallback_gateway = "N/A"

        try:
            with Path("/proc/net/route").open(
                encoding="utf-8"
            ) as route_file:
                next(route_file, None)

                for line in route_file:
                    fields = line.split()

                    if len(fields) < 4:
                        continue

                    interface = fields[0]
                    destination = fields[1]
                    gateway_hex = fields[2]

                    try:
                        flags = int(fields[3], 16)
                    except ValueError:
                        continue

                    if (
                        destination != "00000000"
                        or not flags & 0x2
                    ):
                        continue

                    try:
                        gateway = socket.inet_ntoa(
                            struct.pack(
                                "<L",
                                int(gateway_hex, 16),
                            )
                        )
                    except (ValueError, OSError):
                        continue

                    if interface == preferred_interface:
                        return gateway

                    fallback_gateway = gateway

        except OSError:
            return "N/A"

        return fallback_gateway

    def _read_dns_servers(
        self,
        interface: str,
    ) -> tuple[str, ...]:
        servers: list[str] = []

        if (
            interface
            and interface != "unknown"
            and shutil.which("resolvectl")
        ):
            try:
                result = subprocess.run(
                    ["resolvectl", "dns", interface],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                    env={
                        **os.environ,
                        "LC_ALL": "C",
                    },
                )

                if result.returncode == 0:
                    for token in result.stdout.split():
                        candidate = token.strip(
                            "[](),:"
                        )

                        if self._is_ip_address(candidate):
                            servers.append(candidate)

            except (
                OSError,
                subprocess.SubprocessError,
            ):
                pass

        try:
            resolv_conf = Path(
                "/etc/resolv.conf"
            ).read_text(
                encoding="utf-8",
                errors="replace",
            )

            for line in resolv_conf.splitlines():
                fields = line.split()

                if (
                    len(fields) >= 2
                    and fields[0] == "nameserver"
                    and self._is_ip_address(fields[1])
                ):
                    servers.append(fields[1])

        except OSError:
            pass

        return tuple(dict.fromkeys(servers))

    @staticmethod
    def _is_ip_address(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
        except ValueError:
            return False

        return True

    @staticmethod
    def _ping(
        host: str,
    ) -> tuple[float | None, float | None]:
        if (
            not host
            or host == "N/A"
            or shutil.which("ping") is None
        ):
            return None, None

        try:
            result = subprocess.run(
                [
                    "ping",
                    "-n",
                    "-c",
                    "2",
                    "-W",
                    "1",
                    host,
                ],
                capture_output=True,
                text=True,
                timeout=4.0,
                check=False,
                env={
                    **os.environ,
                    "LC_ALL": "C",
                },
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return None, None

        output = result.stdout + result.stderr

        loss_match = re.search(
            r"([\d.]+)% packet loss",
            output,
        )

        packet_loss = (
            float(loss_match.group(1))
            if loss_match
            else None
        )

        latency_match = re.search(
            r"(?:rtt|round-trip).*?="
            r"\s*[\d.]+/([\d.]+)/",
            output,
        )

        latency = (
            float(latency_match.group(1))
            if latency_match
            else None
        )

        return latency, packet_loss

    def _read_connections(
        self,
    ) -> tuple[
        list[SocketRecord],
        list[SocketRecord],
        bool,
    ]:
        try:
            raw_connections = psutil.net_connections(
                kind="inet"
            )
            access_limited = False

        except (
            psutil.AccessDenied,
            PermissionError,
            OSError,
        ):
            raw_connections = []
            access_limited = True

        process_cache: dict[int, str] = {}
        connections: list[SocketRecord] = []
        listeners: list[SocketRecord] = []

        for connection in raw_connections:
            protocol = (
                "TCP"
                if connection.type == socket.SOCK_STREAM
                else "UDP"
            )

            local_address = self._format_address(
                connection.laddr
            )
            remote_address = self._format_address(
                connection.raddr
            )

            raw_status = connection.status
            status = str(
                getattr(
                    raw_status,
                    "value",
                    raw_status,
                )
            ).upper()

            if not status or status == "NONE":
                status = (
                    "BOUND"
                    if not connection.raddr
                    else "ACTIVE"
                )

            process_name = self._get_process_name(
                connection.pid,
                process_cache,
            )

            local_ip = self._extract_ip(
                connection.laddr
            )

            record = SocketRecord(
                protocol=protocol,
                local_address=local_address,
                remote_address=remote_address,
                status=status,
                pid=connection.pid,
                process_name=process_name,
                non_loopback=self._is_non_loopback(
                    local_ip
                ),
            )

            is_listener = (
                status == "LISTEN"
                or not connection.raddr
            )

            if is_listener:
                listeners.append(record)
            else:
                connections.append(record)

        connections.sort(
            key=lambda record: (
                record.status != "ESTABLISHED",
                record.process_name.lower(),
                record.remote_address,
            )
        )

        listeners.sort(
            key=lambda record: (
                not record.non_loopback,
                record.protocol,
                record.local_address,
            )
        )

        return connections, listeners, access_limited

    @staticmethod
    def _get_process_name(
        pid: int | None,
        cache: dict[int, str],
    ) -> str:
        if pid is None:
            return "kernel/unknown"

        if pid in cache:
            return cache[pid]

        try:
            name = psutil.Process(pid).name()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            name = "restricted"

        cache[pid] = name
        return name

    @staticmethod
    def _format_address(address: object) -> str:
        if not address:
            return "—"

        ip_value = getattr(address, "ip", None)
        port_value = getattr(address, "port", None)

        if ip_value is None:
            try:
                ip_value = address[0]
                port_value = address[1]
            except (
                IndexError,
                TypeError,
            ):
                return str(address)

        ip_text = str(ip_value)

        if ":" in ip_text:
            return f"[{ip_text}]:{port_value}"

        return f"{ip_text}:{port_value}"

    @staticmethod
    def _extract_ip(address: object) -> str:
        if not address:
            return ""

        ip_value = getattr(address, "ip", None)

        if ip_value is not None:
            return str(ip_value)

        try:
            return str(address[0])
        except (
            IndexError,
            TypeError,
        ):
            return ""

    @staticmethod
    def _is_non_loopback(ip_value: str) -> bool:
        if not ip_value:
            return False

        try:
            address = ipaddress.ip_address(ip_value)
        except ValueError:
            return False

        return not address.is_loopback
