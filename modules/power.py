from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True, slots=True)
class PowerSample:
    battery_present: bool
    battery_percent: float | None
    battery_state: str
    battery_power_w: float | None
    battery_energy_wh: float | None
    battery_energy_full_wh: float | None
    battery_energy_full_design_wh: float | None
    battery_health_percent: float | None
    battery_time_remaining_s: int | None
    external_power_online: bool | None
    power_profile: str

    @classmethod
    def unavailable(cls) -> "PowerSample":
        return cls(
            battery_present=False,
            battery_percent=None,
            battery_state="UNKNOWN",
            battery_power_w=None,
            battery_energy_wh=None,
            battery_energy_full_wh=None,
            battery_energy_full_design_wh=None,
            battery_health_percent=None,
            battery_time_remaining_s=None,
            external_power_online=None,
            power_profile="UNKNOWN",
        )


class PowerMonitor:
    """Read-only laptop battery and platform power telemetry."""

    def __init__(
        self,
        power_supply_root: Path | None = None,
        profile_reader: Callable[[], str] | None = None,
    ) -> None:
        self.power_supply_root = (
            Path(power_supply_root)
            if power_supply_root is not None
            else Path("/sys/class/power_supply")
        )
        self._profile_reader = (
            profile_reader
            if profile_reader is not None
            else self._read_power_profile
        )

    def sample(self) -> PowerSample:
        battery = self._find_battery()
        external_power = self._external_power_online()

        try:
            power_profile = self._profile_reader().strip().lower()
        except Exception:
            power_profile = "unknown"

        if not power_profile:
            power_profile = "unknown"

        if battery is None:
            return PowerSample(
                battery_present=False,
                battery_percent=None,
                battery_state="NOT PRESENT",
                battery_power_w=None,
                battery_energy_wh=None,
                battery_energy_full_wh=None,
                battery_energy_full_design_wh=None,
                battery_health_percent=None,
                battery_time_remaining_s=None,
                external_power_online=external_power,
                power_profile=power_profile,
            )

        present_raw = self._read_text(battery / "present")
        if present_raw == "0":
            return PowerSample(
                battery_present=False,
                battery_percent=None,
                battery_state="NOT PRESENT",
                battery_power_w=None,
                battery_energy_wh=None,
                battery_energy_full_wh=None,
                battery_energy_full_design_wh=None,
                battery_health_percent=None,
                battery_time_remaining_s=None,
                external_power_online=external_power,
                power_profile=power_profile,
            )

        percent = self._read_number(battery / "capacity")
        if percent is not None:
            percent = max(0.0, min(percent, 100.0))

        state = (
            self._read_text(battery / "status")
            or "UNKNOWN"
        ).upper()

        energy_now = self._read_energy_wh(
            battery,
            "energy_now",
            "charge_now",
        )
        energy_full = self._read_energy_wh(
            battery,
            "energy_full",
            "charge_full",
        )
        energy_design = self._read_energy_wh(
            battery,
            "energy_full_design",
            "charge_full_design",
        )
        power_w = self._read_power_w(battery)

        health = None
        if (
            energy_full is not None
            and energy_design is not None
            and energy_design > 0
        ):
            health = round(
                (energy_full / energy_design) * 100.0,
                1,
            )

        remaining = self._estimate_remaining_seconds(
            state=state,
            energy_now=energy_now,
            energy_full=energy_full,
            power_w=power_w,
        )

        return PowerSample(
            battery_present=True,
            battery_percent=(
                round(percent, 1)
                if percent is not None
                else None
            ),
            battery_state=state,
            battery_power_w=(
                round(power_w, 2)
                if power_w is not None
                else None
            ),
            battery_energy_wh=(
                round(energy_now, 2)
                if energy_now is not None
                else None
            ),
            battery_energy_full_wh=(
                round(energy_full, 2)
                if energy_full is not None
                else None
            ),
            battery_energy_full_design_wh=(
                round(energy_design, 2)
                if energy_design is not None
                else None
            ),
            battery_health_percent=health,
            battery_time_remaining_s=remaining,
            external_power_online=external_power,
            power_profile=power_profile,
        )

    def _find_battery(self) -> Path | None:
        if not self.power_supply_root.is_dir():
            return None

        for candidate in sorted(self.power_supply_root.iterdir()):
            if not candidate.is_dir():
                continue

            supply_type = self._read_text(candidate / "type")
            if supply_type.lower() == "battery":
                return candidate

        return None

    def _external_power_online(self) -> bool | None:
        if not self.power_supply_root.is_dir():
            return None

        online_values: list[bool] = []

        for candidate in sorted(self.power_supply_root.iterdir()):
            if not candidate.is_dir():
                continue

            supply_type = self._read_text(candidate / "type").lower()
            if supply_type == "battery":
                continue

            raw = self._read_text(candidate / "online")
            if raw in {"0", "1"}:
                online_values.append(raw == "1")

        if not online_values:
            return None

        return any(online_values)

    def _read_energy_wh(
        self,
        battery: Path,
        energy_name: str,
        charge_name: str,
    ) -> float | None:
        energy = self._read_number(battery / energy_name)
        if energy is not None:
            return energy / 1_000_000.0

        charge = self._read_number(battery / charge_name)
        voltage = self._read_number(battery / "voltage_now")

        if charge is None or voltage is None:
            return None

        return (charge * voltage) / 1_000_000_000_000.0

    def _read_power_w(self, battery: Path) -> float | None:
        power = self._read_number(battery / "power_now")
        if power is not None:
            return abs(power) / 1_000_000.0

        current = self._read_number(battery / "current_now")
        voltage = self._read_number(battery / "voltage_now")

        if current is None or voltage is None:
            return None

        return abs(current * voltage) / 1_000_000_000_000.0

    @staticmethod
    def _estimate_remaining_seconds(
        *,
        state: str,
        energy_now: float | None,
        energy_full: float | None,
        power_w: float | None,
    ) -> int | None:
        if power_w is None or power_w <= 0.05:
            return None

        hours: float | None = None

        if state == "DISCHARGING" and energy_now is not None:
            hours = energy_now / power_w

        elif (
            state == "CHARGING"
            and energy_now is not None
            and energy_full is not None
        ):
            hours = max(0.0, energy_full - energy_now) / power_w

        if hours is None:
            return None

        seconds = int(hours * 3600.0)
        return max(0, seconds)

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()
        except OSError:
            return ""

    @classmethod
    def _read_number(cls, path: Path) -> float | None:
        raw = cls._read_text(path)
        if not raw:
            return None

        try:
            return float(raw)
        except ValueError:
            return None

    @staticmethod
    def _read_power_profile() -> str:
        if shutil.which("powerprofilesctl") is None:
            return "not-managed"

        try:
            result = subprocess.run(
                ["powerprofilesctl", "get"],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "not-managed"

        if result.returncode != 0:
            return "not-managed"

        return result.stdout.strip() or "not-managed"
