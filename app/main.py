from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

from app.dashboard import Dashboard


class Helm(App):
    CSS_PATH = "theme.tcss"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Dashboard()
        yield Footer()


if __name__ == "__main__":
    Helm().run()
