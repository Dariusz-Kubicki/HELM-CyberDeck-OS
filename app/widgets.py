from textual.widgets import Static


class InfoBox(Static):
    def __init__(self, title: str):
        super().__init__()
        self.title = title

    def update_value(self, value):
        self.update(
            f"[b cyan]{self.title}[/]\n\n"
            f"[bold white]{value}[/]"
        )
