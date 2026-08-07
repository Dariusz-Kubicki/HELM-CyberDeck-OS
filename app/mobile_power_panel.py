from __future__ import annotations

from rich.markup import escape
from textual.widgets import Static

from modules.power import PowerSample
from services.data_service import SystemSnapshot
from services.mobile_power_policy import MobilePowerPolicyService


class MobilePowerPanel(Static):
    # Compact Stage 5C laptop energy telemetry surface.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._policy = MobilePowerPolicyService()

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
        mode_id: str,
        explicit_profile: str,
    ) -> None:
        target = self._policy.policy_target_for_source(
            mode_id,
            explicit_profile,
            snapshot.power.external_power_online,
        )

        self.update(
            self.build_markup(
                snapshot.power,
                mode_id,
                target,
            )
        )

    @classmethod
    def build_markup(
        cls,
        power: PowerSample,
        mode_id: str,
        policy_target: str,
    ) -> str:
        source = cls._power_source(
            power.external_power_online
        )

        battery = cls._format_percent(
            power.battery_percent
        )
        remaining = cls._format_duration(
            power.battery_time_remaining_s
        )
        draw = cls._format_number(
            power.battery_power_w,
            " W",
            digits=1,
        )
        health = cls._format_percent(
            power.battery_health_percent
        )
        energy = cls._format_energy(
            power.battery_energy_wh,
            power.battery_energy_full_wh,
        )

        state = escape(
            power.battery_state.upper()
            if power.battery_state
            else "UNKNOWN"
        )
        profile = escape(
            power.power_profile.upper()
            if power.power_profile
            else "UNKNOWN"
        )
        mode = escape(
            str(mode_id or "custom").upper()
        )
        target = escape(
            str(policy_target or "unchanged").upper()
        )

        return "\n".join(
            [
                (
                    "[b #42e8ff]"
                    "MOBILE POWER // FIELD ENERGY STATUS"
                    "[/b #42e8ff]"
                ),
                (
                    f"[b]BATTERY[/b] {battery} {state}"
                    f"    //    [b]REMAINING[/b] {remaining}"
                    f"    //    [b]DRAW[/b] {draw}"
                ),
                (
                    f"[b]ENERGY[/b] {energy}"
                    f"    //    [b]HEALTH[/b] {health}"
                    f"    //    [b]SOURCE[/b] {source}"
                ),
                (
                    f"[b]PROFILE[/b] {profile}"
                    f"    //    [b]MODE POLICY[/b] "
                    f"{mode} -> {target}"
                ),
            ]
        )

    @staticmethod
    def _power_source(
        external_power_online: bool | None,
    ) -> str:
        if external_power_online is True:
            return "AC"

        if external_power_online is False:
            return "BATTERY"

        return "UNKNOWN"

    @staticmethod
    def _format_percent(
        value: float | None,
    ) -> str:
        if value is None:
            return "N/A"

        return f"{value:.1f}%"

    @staticmethod
    def _format_number(
        value: float | None,
        suffix: str,
        *,
        digits: int,
    ) -> str:
        if value is None:
            return "N/A"

        return f"{value:.{digits}f}{suffix}"

    @staticmethod
    def _format_energy(
        current: float | None,
        full: float | None,
    ) -> str:
        if current is None and full is None:
            return "N/A"

        current_text = (
            f"{current:.2f}"
            if current is not None
            else "N/A"
        )
        full_text = (
            f"{full:.2f}"
            if full is not None
            else "N/A"
        )

        return f"{current_text} / {full_text} Wh"

    @staticmethod
    def _format_duration(
        seconds: int | None,
    ) -> str:
        if seconds is None or seconds < 0:
            return "N/A"

        total_minutes = int(seconds) // 60
        hours, minutes = divmod(
            total_minutes,
            60,
        )

        if hours:
            return f"{hours}h {minutes:02d}m"

        return f"{minutes}m"
