from __future__ import annotations

from dataclasses import dataclass

from services.data_service import SystemSnapshot


@dataclass(frozen=True, slots=True)
class SystemAlert:
    code: str
    severity: str
    title: str
    message: str
    value: str


class AlertService:
    """Analyzes live telemetry and detects unhealthy conditions."""

    def analyze(
        self,
        snapshot: SystemSnapshot,
    ) -> tuple[SystemAlert, ...]:
        alerts: list[SystemAlert] = []

        self._check_metric(
            alerts,
            code="cpu-temperature",
            title="CPU TEMPERATURE",
            value=snapshot.cpu_temp,
            warning=75.0,
            critical=85.0,
            suffix="°C",
        )

        self._check_metric(
            alerts,
            code="gpu-temperature",
            title="GPU TEMPERATURE",
            value=snapshot.gpu_temp,
            warning=75.0,
            critical=85.0,
            suffix="°C",
        )

        self._check_metric(
            alerts,
            code="memory-usage",
            title="MEMORY PRESSURE",
            value=snapshot.resources.memory_percent,
            warning=80.0,
            critical=92.0,
            suffix="%",
        )

        self._check_metric(
            alerts,
            code="root-usage",
            title="ROOT FILESYSTEM",
            value=snapshot.storage.root_percent,
            warning=85.0,
            critical=95.0,
            suffix="%",
        )

        if snapshot.resources.swap_total > 0:
            self._check_metric(
                alerts,
                code="swap-usage",
                title="SWAP PRESSURE",
                value=snapshot.resources.swap_percent,
                warning=70.0,
                critical=90.0,
                suffix="%",
            )

        logical_cores = max(
            snapshot.resources.logical_cores,
            1,
        )

        load_percent = (
            snapshot.resources.load_1
            / logical_cores
            * 100.0
        )

        self._check_metric(
            alerts,
            code="system-load",
            title="SYSTEM LOAD",
            value=load_percent,
            warning=100.0,
            critical=150.0,
            suffix="% capacity",
        )

        if not snapshot.network_online:
            alerts.append(
                SystemAlert(
                    code="network-offline",
                    severity="WARNING",
                    title="NETWORK OFFLINE",
                    message=(
                        "Primary network interface "
                        f"{snapshot.network_interface} is down."
                    ),
                    value=snapshot.network_interface,
                )
            )

        for device in snapshot.storage.devices:
            if device.smart_status != "FAILED":
                continue

            alerts.append(
                SystemAlert(
                    code=f"smart-failure-{device.name}",
                    severity="CRITICAL",
                    title="SMART FAILURE",
                    message=(
                        f"/dev/{device.name} reported "
                        "a failed SMART health test."
                    ),
                    value=device.model,
                )
            )

        alerts.sort(
            key=lambda alert: (
                0 if alert.severity == "CRITICAL" else 1,
                alert.title,
            )
        )

        return tuple(alerts)

    @staticmethod
    def _check_metric(
        alerts: list[SystemAlert],
        *,
        code: str,
        title: str,
        value: float | None,
        warning: float,
        critical: float,
        suffix: str,
    ) -> None:
        if value is None:
            return

        if value >= critical:
            severity = "CRITICAL"
            threshold = critical
        elif value >= warning:
            severity = "WARNING"
            threshold = warning
        else:
            return

        alerts.append(
            SystemAlert(
                code=code,
                severity=severity,
                title=title,
                message=(
                    f"Measured value exceeded the "
                    f"{threshold:g}{suffix} threshold."
                ),
                value=f"{value:.1f}{suffix}",
            )
        )
