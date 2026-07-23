from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static


class Sidebar(Vertical):
    def compose(self) -> ComposeResult:
        yield Static("HELM // NAVIGATION", id="sidebar-title")

        yield Button(
            "SYSTEM",
            id="system",
            classes="nav-button selected",
        )
        yield Button(
            "NETWORK",
            id="network",
            classes="nav-button",
        )
        yield Button(
            "STORAGE",
            id="storage",
            classes="nav-button",
        )
        yield Button(
            "DEVICES",
            id="devices",
            classes="nav-button",
        )

        yield Static("COMING ONLINE", classes="sidebar-section")

        yield Button("PROJECTS", id="projects", disabled=True)
        yield Button("AI", id="ai", disabled=True)
        yield Button("LOGS", id="logs", disabled=True)
        yield Button("SETTINGS", id="settings", disabled=True)
