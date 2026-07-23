from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from services.mode_service import WorkMode


class ModesScreen(Vertical):
    """CyberDeck work mode selection and activation screen."""

    def __init__(
        self,
        modes: tuple[WorkMode, ...],
        active_mode_id: str,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.modes = modes
        self.mode_map = {
            mode.mode_id: mode
            for mode in modes
        }

        self.active_mode_id = active_mode_id
        self.selected_mode_id = (
            active_mode_id
            if active_mode_id in self.mode_map
            else modes[0].mode_id
        )

    def compose(self) -> ComposeResult:
        with Horizontal(id="modes-summary"):
            yield Static(
                "--",
                id="mode-active-summary",
                classes="mode-summary-card",
            )
            yield Static(
                "--",
                id="mode-power-summary",
                classes="mode-summary-card",
            )
            yield Static(
                "--",
                id="mode-refresh-summary",
                classes="mode-summary-card",
            )
            yield Static(
                "--",
                id="mode-target-summary",
                classes="mode-summary-card",
            )

        yield Static(
            "[b cyan]● WORK MODE ENGINE ONLINE[/b cyan]"
            "    //    SELECT AN OPERATION PROFILE",
            id="mode-status",
        )

        with Horizontal(id="mode-selector"):
            for mode in self.modes:
                yield Button(
                    mode.name,
                    id=f"mode-select-{mode.mode_id}",
                    classes="mode-choice",
                )

        yield Static(
            "SELECT A MODE",
            id="mode-details",
        )

        with Horizontal(id="mode-actions"):
            yield Button(
                "ACTIVATE SELECTED MODE",
                id="mode-activate",
                variant="primary",
            )

        yield Static(
            "Work profiles: config/modes.json",
            id="mode-config-path",
        )

    def on_mount(self) -> None:
        self.select_mode(self.selected_mode_id)
        self.update_active_mode(
            self.active_mode_id,
            "CHECKING",
        )

    def select_mode(self, mode_id: str) -> None:
        mode = self.mode_map.get(mode_id)

        if mode is None:
            return

        self.selected_mode_id = mode_id

        for known_mode in self.modes:
            button = self.query_one(
                f"#mode-select-{known_mode.mode_id}",
                Button,
            )
            button.remove_class("selected-mode")

        self.query_one(
            f"#mode-select-{mode_id}",
            Button,
        ).add_class("selected-mode")

        features = "\n".join(
            f"  • {feature}"
            for feature in mode.features
        )

        self.query_one("#mode-details", Static).update(
            f"[b cyan]{mode.name} MODE[/b cyan]\n\n"
            f"{mode.description}\n\n"
            f"[b]PRIMARY OBJECTIVE[/b]\n"
            f"{mode.objective}\n\n"
            f"[b]MODE PARAMETERS[/b]\n"
            f"  TELEMETRY       {mode.telemetry_interval:g} seconds\n"
            f"  TARGET SCREEN   {mode.target_screen.upper()}\n"
            f"  POWER PROFILE   {mode.power_profile.upper()}\n"
            f"  NAVIGATION LOG  "
            f"{'ENABLED' if mode.navigation_logging else 'DISABLED'}\n\n"
            f"[b]CAPABILITIES[/b]\n"
            f"{features}"
        )

    def update_active_mode(
        self,
        mode_id: str,
        power_profile: str,
        message: str | None = None,
    ) -> None:
        self.active_mode_id = mode_id
        active_mode = self.mode_map.get(mode_id)

        for mode in self.modes:
            button = self.query_one(
                f"#mode-select-{mode.mode_id}",
                Button,
            )
            button.remove_class("active-mode")

        if active_mode is not None:
            self.query_one(
                f"#mode-select-{mode_id}",
                Button,
            ).add_class("active-mode")

            mode_name = active_mode.name
            refresh = f"{active_mode.telemetry_interval:g}s"
            target = active_mode.target_screen.upper()
        else:
            mode_name = "CUSTOM"
            refresh = "CUSTOM"
            target = "CUSTOM"

        self.query_one(
            "#mode-active-summary",
            Static,
        ).update(
            "[b]ACTIVE MODE[/b]\n\n"
            f"[b cyan]{mode_name}[/b cyan]"
        )

        self.query_one(
            "#mode-power-summary",
            Static,
        ).update(
            "[b]POWER PROFILE[/b]\n\n"
            f"[b]{power_profile.upper()}[/b]"
        )

        self.query_one(
            "#mode-refresh-summary",
            Static,
        ).update(
            "[b]TELEMETRY[/b]\n\n"
            f"[b]{refresh}[/b]"
        )

        self.query_one(
            "#mode-target-summary",
            Static,
        ).update(
            "[b]TARGET SCREEN[/b]\n\n"
            f"[b]{target}[/b]"
        )

        if message:
            self.query_one("#mode-status", Static).update(
                "[b cyan]● MODE ENGINE READY[/b cyan]"
                f"    //    {message}"
            )

    def show_activation(
        self,
        mode: WorkMode,
        power_profile: str,
    ) -> None:
        self.update_active_mode(
            mode.mode_id,
            power_profile,
            (
                f"{mode.name} MODE ACTIVATED"
                f"    //    POWER {power_profile}"
            ),
        )
