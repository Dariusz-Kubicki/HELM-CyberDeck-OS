from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from app.screens.system import SystemScreen
from app.sidebar import Sidebar


class Helm(App):
    CSS_PATH = "theme.tcss"
    TITLE = "HELM"
    SUB_TITLE = "CyberDeck Control Interface"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar")

            with Vertical(id="content-area"):
                yield Static(
                    "HELM // SYSTEM OVERVIEW",
                    id="screen-title",
                )
                yield SystemScreen(id="system-screen")

        yield Footer()


if __name__ == "__main__":
    Helm().run()
