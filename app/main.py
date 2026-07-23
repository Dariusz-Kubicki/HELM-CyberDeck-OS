from functools import partial
from typing import Iterable
from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Static,
)

from app.screens.ai import AIScreen
from app.screens.devices import DevicesScreen
from app.screens.logs import LogsScreen
from app.screens.modes import ModesScreen
from app.screens.network import NetworkScreen
from app.screens.projects import ProjectsScreen
from app.screens.settings import SettingsScreen
from app.screens.storage import StorageScreen
from app.screens.system import SystemScreen
from app.sidebar import Sidebar
from app.system_actions import SystemActions
from services.alert_service import SystemAlert
from services.data_service import DataService
from services.log_service import LogService
from services.mode_service import ModeService
from services.settings_service import HelmSettings, SettingsService
from services.workspace_service import WorkspaceService
from services.system_action_service import SystemActionService


class Helm(App):
    CSS_PATH = "theme.tcss"
    TITLE = "HELM"
    SUB_TITLE = "CyberDeck Control Interface"

    COMMAND_PALETTE_BINDING = "ctrl+k"
    COMMAND_PALETTE_DISPLAY = "CTRL+K"

    NAVIGATION = {
        "system": (
            "system-screen",
            "HELM // SYSTEM OVERVIEW",
        ),
        "network": (
            "network-screen",
            "HELM // NETWORK TELEMETRY",
        ),
        "storage": (
            "storage-screen",
            "HELM // STORAGE ARRAY",
        ),
        "devices": (
            "devices-screen",
            "HELM // CONNECTED DEVICES",
        ),
        "modes": (
            "modes-screen",
            "HELM // OPERATION MODES",
        ),
        "projects": (
            "projects-screen",
            "HELM // PROJECT COMMAND",
        ),
        "logs": (
            "logs-screen",
            "HELM // EVENT LOG",
        ),
        "ai": (
            "ai-screen",
            "HELM // DIAGNOSTIC CORE",
        ),
        "settings": (
            "settings-screen",
            "HELM // SYSTEM CONFIGURATION",
        ),
    }

    def __init__(self) -> None:
        super().__init__()

        self.data_service = DataService()
        self.log_service = LogService()
        self.settings_service = SettingsService()
        self.mode_service = ModeService()
        self.workspace_service = WorkspaceService()
        self.system_action_service = SystemActionService()

        self.settings = self.settings_service.load()
        self.modes = self.mode_service.load_modes()
        self.active_mode_id = self.mode_service.load_active_mode()

        self.refresh_timer: Timer | None = None
        self._active_system_alerts: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar")

            with Vertical(id="content-area"):
                yield Static(
                    "HELM // SYSTEM OVERVIEW",
                    id="screen-title",
                )

                with ContentSwitcher(
                    initial="system-screen",
                    id="screen-switcher",
                ):
                    yield SystemScreen(id="system-screen")
                    yield NetworkScreen(id="network-screen")
                    yield StorageScreen(id="storage-screen")
                    yield DevicesScreen(id="devices-screen")
                    yield ModesScreen(
                        self.modes,
                        self.active_mode_id,
                        id="modes-screen",
                    )
                    yield ProjectsScreen(id="projects-screen")
                    yield LogsScreen(id="logs-screen")
                    yield AIScreen(id="ai-screen")
                    yield SettingsScreen(
                        self.settings,
                        id="settings-screen",
                    )

        yield Footer()

    def get_system_commands(
        self,
        screen: Screen,
    ) -> Iterable[SystemCommand]:
        """Expose HELM actions through the global command palette."""

        yield from super().get_system_commands(screen)

        for navigation_id, (_, title) in self.NAVIGATION.items():
            yield SystemCommand(
                f"Open {navigation_id.upper()}",
                title,
                partial(
                    self._open_screen,
                    navigation_id,
                ),
            )

        for mode in self.modes:
            yield SystemCommand(
                f"Activate {mode.name} workspace",
                mode.description,
                partial(
                    self._activate_workspace_from_palette,
                    mode.mode_id,
                ),
            )

        yield SystemCommand(
            "Run full CyberDeck diagnostic",
            "Open the AI core and analyze live system telemetry.",
            partial(
                self._run_ai_command,
                "diagnostic",
            ),
        )

        yield SystemCommand(
            "Show AI command help",
            "Open the diagnostic core command reference.",
            partial(
                self._run_ai_command,
                "help",
            ),
        )

    def on_mount(self) -> None:
        self.log_service.info(
            "HELM",
            "CyberDeck control interface started",
        )

        active_mode = self.mode_service.get_mode(
            self.active_mode_id
        )

        if active_mode is not None:
            power_profile = self.mode_service.apply_power_profile(
                active_mode.power_profile
            )

            self.query_one(ModesScreen).update_active_mode(
                active_mode.mode_id,
                power_profile,
                f"{active_mode.name} MODE RESTORED",
            )
        else:
            self.query_one(ModesScreen).update_active_mode(
                "custom",
                self.mode_service.get_current_power_profile(),
                "CUSTOM RUNTIME CONFIGURATION",
            )

        self._open_screen(
            self.settings.start_screen,
            log_event=False,
        )

        self.refresh_snapshot()
        self._restart_refresh_timer()

    def on_unmount(self) -> None:
        if self.refresh_timer is not None:
            self.refresh_timer.stop()

        self.log_service.info(
            "HELM",
            "CyberDeck control interface stopped",
        )

    def _restart_refresh_timer(self) -> None:
        if self.refresh_timer is not None:
            self.refresh_timer.stop()

        self.refresh_timer = self.set_interval(
            self.settings.telemetry_interval,
            self.refresh_snapshot,
        )

    def refresh_snapshot(self) -> None:
        try:
            snapshot = self.data_service.collect()

            system_alerts = self.query_one(SystemScreen).update_snapshot(snapshot)
            self._process_system_alerts(system_alerts)
            self.query_one(NetworkScreen).update_snapshot(snapshot)
            self.query_one(StorageScreen).update_snapshot(snapshot)
            self.query_one(DevicesScreen).update_snapshot(snapshot)
            self.query_one(ProjectsScreen).update_snapshot(snapshot)
            self.query_one(AIScreen).update_snapshot(snapshot)

        except Exception as error:
            self.query_one(SystemScreen).show_error(error)
            self.query_one(StorageScreen).show_error(error)

            self.log_service.error(
                "TELEMETRY",
                f"{type(error).__name__}: {error}",
            )

        self.query_one(LogsScreen).update_entries(
            self.log_service.tail(
                limit=self.settings.log_rows,
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id is None:
            return

        system_actions = {
            "system-action-btop": "btop",
            "system-action-sensors": "sensors",
            "system-action-gpu": "gpu",
            "system-action-diagnostic": "diagnostic",
        }

        if button_id in system_actions:
            self._launch_system_action(
                system_actions[button_id]
            )
            event.stop()
            return

        if button_id.startswith("mode-select-"):
            mode_id = button_id.removeprefix("mode-select-")

            self.query_one(ModesScreen).select_mode(mode_id)
            event.stop()
            return

        if button_id == "mode-activate":
            self._activate_selected_mode()
            event.stop()
            return

        if button_id == "settings-save":
            self._save_settings()
            return

        if button_id == "settings-reset":
            self._reset_settings()
            return

        if button_id in self.NAVIGATION:
            self._open_screen(button_id)

    def _launch_system_action(
        self,
        action_id: str,
    ) -> None:
        result = self.system_action_service.launch(
            action_id
        )

        self.query_one(
            SystemActions
        ).show_result(result)

        message = (
            f"{result.title}; "
            f"status={result.status}; "
            f"detail={result.detail}"
        )

        if result.status == "LAUNCHED":
            self.log_service.info(
                "SYSTEM ACTION",
                message,
            )
        elif result.status == "NOT INSTALLED":
            self.log_service.warning(
                "SYSTEM ACTION",
                message,
            )
        else:
            self.log_service.error(
                "SYSTEM ACTION",
                message,
            )

    def _process_system_alerts(
        self,
        alerts: tuple[SystemAlert, ...],
    ) -> None:
        current_alerts = {
            alert.code: alert
            for alert in alerts
        }

        previous_codes = set(
            self._active_system_alerts
        )
        current_codes = set(current_alerts)

        for code in sorted(
            current_codes - previous_codes
        ):
            alert = current_alerts[code]

            message = (
                f"{alert.title}: "
                f"{alert.value}; "
                f"{alert.message}"
            )

            if alert.severity == "CRITICAL":
                self.log_service.critical(
                    "SYSTEM ALERT",
                    message,
                )
            else:
                self.log_service.warning(
                    "SYSTEM ALERT",
                    message,
                )

        for code in sorted(
            previous_codes - current_codes
        ):
            self.log_service.info(
                "SYSTEM ALERT",
                f"Condition cleared: {code}",
            )

        self._active_system_alerts = {
            code: alert.severity
            for code, alert in current_alerts.items()
        }

    def _activate_workspace_from_palette(
        self,
        mode_id: str,
    ) -> None:
        """Select and activate a workspace from the command palette."""

        modes_screen = self.query_one(ModesScreen)
        modes_screen.select_mode(mode_id)

        self._activate_selected_mode()

    def _run_ai_command(self, command: str) -> None:
        """Open the AI screen and execute a diagnostic command."""

        self._open_screen(
            "ai",
            log_event=False,
        )

        self.query_one(AIScreen).execute_command(command)

        self.log_service.info(
            "COMMAND",
            f"Executed AI command: {command}",
        )

    def _activate_selected_mode(self) -> None:
        screen = self.query_one(ModesScreen)
        mode = self.mode_service.get_mode(
            screen.selected_mode_id
        )

        if mode is None:
            self.log_service.error(
                "WORKSPACE",
                "Selected workspace does not exist",
            )
            return

        settings = HelmSettings(
            telemetry_interval=mode.telemetry_interval,
            start_screen=mode.target_screen,
            navigation_logging=mode.navigation_logging,
            log_rows=self.settings.log_rows,
        )

        try:
            self.settings_service.save(settings)
            self.mode_service.save_active_mode(mode.mode_id)

            self.settings = settings
            self.active_mode_id = mode.mode_id

            self.query_one(SettingsScreen).load_settings(settings)
            self._restart_refresh_timer()

            power_profile = self.mode_service.apply_power_profile(
                mode.power_profile
            )

            launch_results = self.workspace_service.launch_mode(mode)

            screen.show_activation(
                mode,
                power_profile,
                launch_results,
            )

            for result in launch_results:
                self.log_service.info(
                    "WORKSPACE",
                    (
                        f"{mode.name}: {result.application}; "
                        f"status={result.status}; "
                        f"detail={result.detail}"
                    ),
                )

            self.log_service.info(
                "MODE",
                (
                    f"Activated {mode.name} workspace; "
                    f"telemetry={mode.telemetry_interval}s; "
                    f"target={mode.target_screen}; "
                    f"applications={len(launch_results)}"
                ),
            )

            self._open_screen(
                mode.target_screen,
                log_event=False,
            )

        except Exception as error:
            self.log_service.error(
                "WORKSPACE",
                f"{type(error).__name__}: {error}",
            )

            screen.update_active_mode(
                self.active_mode_id,
                self.mode_service.get_current_power_profile(),
                f"ACTIVATION ERROR: {error}",
            )

    def _open_screen(
        self,
        navigation_id: str,
        *,
        log_event: bool = True,
    ) -> None:
        if navigation_id not in self.NAVIGATION:
            navigation_id = "system"

        screen_id, title = self.NAVIGATION[navigation_id]

        self.query_one(
            "#screen-switcher",
            ContentSwitcher,
        ).current = screen_id

        self.query_one("#screen-title", Static).update(title)

        for button_name in self.NAVIGATION:
            self.query_one(
                f"#{button_name}",
                Button,
            ).remove_class("selected")

        active_button = self.query_one(
            f"#{navigation_id}",
            Button,
        )
        active_button.add_class("selected")
        active_button.focus()

        if log_event and self.settings.navigation_logging:
            self.log_service.info(
                "NAVIGATION",
                f"Opened {navigation_id.upper()} screen",
            )

    def _set_custom_mode(self) -> None:
        self.active_mode_id = "custom"
        self.mode_service.save_active_mode("custom")

        self.query_one(ModesScreen).update_active_mode(
            "custom",
            self.mode_service.get_current_power_profile(),
            "CUSTOM SETTINGS ACTIVE",
        )

    def _save_settings(self) -> None:
        screen = self.query_one(SettingsScreen)

        try:
            settings = screen.read_settings()
            self.settings_service.save(settings)

            self.settings = settings
            screen.load_settings(settings)
            self._restart_refresh_timer()
            self._set_custom_mode()

            screen.show_status(
                "Runtime configuration saved successfully."
            )

            self.log_service.info(
                "SETTINGS",
                "Runtime configuration updated",
            )

        except Exception as error:
            screen.show_status(
                f"{type(error).__name__}: {error}",
                error=True,
            )

            self.log_service.error(
                "SETTINGS",
                f"{type(error).__name__}: {error}",
            )

    def _reset_settings(self) -> None:
        screen = self.query_one(SettingsScreen)

        try:
            settings = HelmSettings()
            self.settings_service.save(settings)

            self.settings = settings
            screen.load_settings(settings)
            self._restart_refresh_timer()
            self._set_custom_mode()

            screen.show_status(
                "Default configuration restored."
            )

            self.log_service.warning(
                "SETTINGS",
                "Default runtime configuration restored",
            )

        except Exception as error:
            screen.show_status(
                f"{type(error).__name__}: {error}",
                error=True,
            )


if __name__ == "__main__":
    Helm().run()
