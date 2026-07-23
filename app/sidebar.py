from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button


class Sidebar(Vertical):
    def compose(self) -> ComposeResult:
        yield Button("SYSTEM", id="system")
        yield Button("NETWORK", id="network")
        yield Button("DEVICES", id="devices")
        yield Button("PROJECTS", id="projects")
        yield Button("AI", id="ai")
        yield Button("LOGS", id="logs")
        yield Button("SETTINGS", id="settings")
