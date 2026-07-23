from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static, Switch

from services.settings_service import HelmSettings


class SettingsScreen(Vertical):
    """HELM runtime configuration screen."""

    INTERVAL_VALUES = (0.5, 1.0, 2.0, 5.0)

    START_SCREEN_VALUES = (
        "system",
        "network",
        "storage",
        "devices",
        "projects",
        "logs",
        "ai",
        "settings",
    )

    LOG_ROW_VALUES = (50, 100, 200, 500)

    def __init__(
        self,
        settings: HelmSettings,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.settings = settings
        self.telemetry_interval = settings.telemetry_interval
        self.start_screen = settings.start_screen
        self.log_rows = settings.log_rows

    def compose(self) -> ComposeResult:
        with Horizontal(id="settings-summary"):
            yield Static(
                "--",
                id="setting-refresh-summary",
                classes="settings-card",
            )
            yield Static(
                "--",
                id="setting-start-summary",
                classes="settings-card",
            )
            yield Static(
                "--",
                id="setting-log-summary",
                classes="settings-card",
            )
            yield Static(
                "--",
                id="setting-nav-summary",
                classes="settings-card",
            )

        yield Static(
            "[b cyan]● CONFIGURATION SERVICE ONLINE[/b cyan]"
            "    //    RUNTIME SETTINGS READY",
            id="settings-status",
        )

        with Vertical(id="settings-form"):
            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]TELEMETRY INTERVAL[/b]\n"
                    "Time between hardware and system measurements.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="interval-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        self._interval_label(),
                        id="telemetry-interval-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="interval-next",
                        classes="cycle-arrow",
                    )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]START SCREEN[/b]\n"
                    "Screen opened automatically when HELM starts.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="start-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        self.start_screen.upper(),
                        id="start-screen-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="start-next",
                        classes="cycle-arrow",
                    )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]EVENT LOG LIMIT[/b]\n"
                    "Maximum number of recent events displayed.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="logs-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        f"{self.log_rows} EVENTS",
                        id="log-rows-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="logs-next",
                        classes="cycle-arrow",
                    )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]NAVIGATION LOGGING[/b]\n"
                    "Record every opened HELM screen in the event log.",
                    classes="setting-label",
                )

                yield Switch(
                    value=self.settings.navigation_logging,
                    id="navigation-logging",
                    classes="setting-switch",
                )

        with Horizontal(id="settings-actions"):
            yield Button(
                "SAVE AND APPLY",
                id="settings-save",
                variant="primary",
            )
            yield Button(
                "RESET DEFAULTS",
                id="settings-reset",
                variant="warning",
            )

        yield Static(
            "Runtime configuration: config/settings.json",
            id="settings-path",
        )

    def on_mount(self) -> None:
        self._refresh_controls()
        self.update_summary(self.settings)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "interval-prev":
            self.telemetry_interval = self._cycle(
                self.INTERVAL_VALUES,
                self.telemetry_interval,
                -1,
            )
        elif button_id == "interval-next":
            self.telemetry_interval = self._cycle(
                self.INTERVAL_VALUES,
                self.telemetry_interval,
                1,
            )
        elif button_id == "start-prev":
            self.start_screen = self._cycle(
                self.START_SCREEN_VALUES,
                self.start_screen,
                -1,
            )
        elif button_id == "start-next":
            self.start_screen = self._cycle(
                self.START_SCREEN_VALUES,
                self.start_screen,
                1,
            )
        elif button_id == "logs-prev":
            self.log_rows = self._cycle(
                self.LOG_ROW_VALUES,
                self.log_rows,
                -1,
            )
        elif button_id == "logs-next":
            self.log_rows = self._cycle(
                self.LOG_ROW_VALUES,
                self.log_rows,
                1,
            )
        else:
            return

        event.stop()
        self._refresh_controls()

    def read_settings(self) -> HelmSettings:
        navigation_logging = self.query_one(
            "#navigation-logging",
            Switch,
        ).value

        return HelmSettings(
            telemetry_interval=float(self.telemetry_interval),
            start_screen=str(self.start_screen),
            navigation_logging=bool(navigation_logging),
            log_rows=int(self.log_rows),
        )

    def load_settings(self, settings: HelmSettings) -> None:
        self.settings = settings
        self.telemetry_interval = settings.telemetry_interval
        self.start_screen = settings.start_screen
        self.log_rows = settings.log_rows

        self.query_one(
            "#navigation-logging",
            Switch,
        ).value = settings.navigation_logging

        self._refresh_controls()
        self.update_summary(settings)

    def _refresh_controls(self) -> None:
        self.query_one(
            "#telemetry-interval-value",
            Static,
        ).update(self._interval_label())

        self.query_one(
            "#start-screen-value",
            Static,
        ).update(self.start_screen.upper())

        self.query_one(
            "#log-rows-value",
            Static,
        ).update(f"{self.log_rows} EVENTS")

    def update_summary(self, settings: HelmSettings) -> None:
        self.query_one(
            "#setting-refresh-summary",
            Static,
        ).update(
            "[b]REFRESH RATE[/b]\n\n"
            f"[b]{settings.telemetry_interval:.1f}s[/b]"
        )

        self.query_one(
            "#setting-start-summary",
            Static,
        ).update(
            "[b]START SCREEN[/b]\n\n"
            f"[b]{settings.start_screen.upper()}[/b]"
        )

        self.query_one(
            "#setting-log-summary",
            Static,
        ).update(
            "[b]LOG CAPACITY[/b]\n\n"
            f"[b]{settings.log_rows} EVENTS[/b]"
        )

        navigation_status = (
            "[b cyan]ENABLED[/b cyan]"
            if settings.navigation_logging
            else "[b #6a8790]DISABLED[/b #6a8790]"
        )

        self.query_one(
            "#setting-nav-summary",
            Static,
        ).update(
            "[b]NAVIGATION LOG[/b]\n\n"
            f"{navigation_status}"
        )

    def show_status(
        self,
        message: str,
        *,
        error: bool = False,
    ) -> None:
        if error:
            content = (
                "[b red]● CONFIGURATION ERROR[/b red]"
                f"    //    {message}"
            )
        else:
            content = (
                "[b cyan]● SETTINGS APPLIED[/b cyan]"
                f"    //    {message}"
            )

        self.query_one("#settings-status", Static).update(content)

    def _interval_label(self) -> str:
        if self.telemetry_interval == 1.0:
            return "1 SECOND"

        return f"{self.telemetry_interval:g} SECONDS"

    @staticmethod
    def _cycle(
        values: tuple,
        current: object,
        direction: int,
    ):
        try:
            current_index = values.index(current)
        except ValueError:
            current_index = 0

        new_index = (current_index + direction) % len(values)
        return values[new_index]
