from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, ContentSwitcher, Footer, Header, Static

from app.screens.devices import DevicesScreen
from app.screens.logs import LogsScreen
from app.screens.network import NetworkScreen
from app.screens.projects import ProjectsScreen
from app.screens.storage import StorageScreen
from app.screens.system import SystemScreen
from app.sidebar import Sidebar
from services.data_service import DataService
from services.log_service import LogService


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
    }

    def __init__(self) -> None:
        super().__init__()
        self.data_service = DataService()
        self.log_service = LogService()

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

        yield Footer()

    def on_mount(self) -> None:
        self.log_service.info(
            "HELM",
            "CyberDeck control interface started",
        )

        self.refresh_snapshot()
        self.set_interval(1.0, self.refresh_snapshot)

    def on_unmount(self) -> None:
        self.log_service.info(
            "HELM",
            "CyberDeck control interface stopped",
        )

    def refresh_snapshot(self) -> None:
        try:
            snapshot = self.data_service.collect()

            self.query_one(SystemScreen).update_snapshot(snapshot)
            self.query_one(NetworkScreen).update_snapshot(snapshot)
            self.query_one(StorageScreen).update_snapshot(snapshot)
            self.query_one(DevicesScreen).update_snapshot(snapshot)
            self.query_one(ProjectsScreen).update_snapshot(snapshot)

        except Exception as error:
            self.query_one(SystemScreen).show_error(error)
            self.query_one(StorageScreen).show_error(error)

            self.log_service.error(
                "TELEMETRY",
                f"{type(error).__name__}: {error}",
            )

        self.query_one(LogsScreen).update_entries(
            self.log_service.tail(limit=200)
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id not in self.NAVIGATION:
            return

        screen_id, title = self.NAVIGATION[button_id]

        self.query_one("#screen-switcher", ContentSwitcher).current = screen_id
        self.query_one("#screen-title", Static).update(title)

        for navigation_id in self.NAVIGATION:
            self.query_one(
                f"#{navigation_id}",
                Button,
            ).remove_class("selected")

        event.button.add_class("selected")

        self.log_service.info(
            "NAVIGATION",
            f"Opened {button_id.upper()} screen",
        )


if __name__ == "__main__":
    Helm().run()
