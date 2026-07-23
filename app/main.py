from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
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
from app.screens.network import NetworkScreen
from app.screens.projects import ProjectsScreen
from app.screens.settings import SettingsScreen
from app.screens.storage import StorageScreen
from app.screens.system import SystemScreen
from app.sidebar import Sidebar
from services.data_service import DataService
from services.log_service import LogService
from services.settings_service import HelmSettings, SettingsService


class Helm(App):
    CSS_PATH = "theme.tcss"
    TITLE = "HELM"
    SUB_TITLE = "CyberDeck Control Interface"

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

        self.settings = self.settings_service.load()
        self.refresh_timer: Timer | None = None

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
                    yield ProjectsScreen(id="projects-screen")
                    yield LogsScreen(id="logs-screen")
                    yield AIScreen(id="ai-screen")
                    yield SettingsScreen(
                        self.settings,
                        id="settings-screen",
                    )

        yield Footer()

    def on_mount(self) -> None:
        self.log_service.info(
            "HELM",
            "CyberDeck control interface started",
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

            self.query_one(SystemScreen).update_snapshot(snapshot)
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

        if button_id == "settings-save":
            self._save_settings()
            return

        if button_id == "settings-reset":
            self._reset_settings()
            return

        if button_id in self.NAVIGATION:
            self._open_screen(button_id)

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

        self.query_one(
            f"#{navigation_id}",
            Button,
        ).add_class("selected")

        if log_event and self.settings.navigation_logging:
            self.log_service.info(
                "NAVIGATION",
                f"Opened {navigation_id.upper()} screen",
            )

    def _save_settings(self) -> None:
        screen = self.query_one(SettingsScreen)

        try:
            settings = screen.read_settings()
            self.settings_service.save(settings)

            self.settings = settings
            screen.load_settings(settings)
            self._restart_refresh_timer()

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
