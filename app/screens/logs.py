from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from services.log_service import LogEntry


class LogsScreen(Vertical):
    """Displays HELM runtime and diagnostic events."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_rows: tuple[tuple[str, ...], ...] = ()

    def compose(self) -> ComposeResult:
        with Horizontal(id="logs-summary"):
            yield Static("--", id="logs-total", classes="logs-card")
            yield Static("--", id="logs-info", classes="logs-card")
            yield Static("--", id="logs-warning", classes="logs-card")
            yield Static("--", id="logs-errors", classes="logs-card")

        yield Static(
            "[b cyan]● EVENT STREAM ONLINE[/b cyan]",
            id="logs-status",
        )

        yield DataTable(id="logs-table")

        yield Static(
            "Runtime file: logs/helm.log",
            id="logs-path",
        )

    def on_mount(self) -> None:
        table = self.query_one("#logs-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "TIME",
            "LEVEL",
            "SOURCE",
            "MESSAGE",
        )

    def update_entries(
        self,
        entries: tuple[LogEntry, ...],
    ) -> None:
        info_count = sum(
            entry.level in {"DEBUG", "INFO"}
            for entry in entries
        )
        warning_count = sum(
            entry.level == "WARNING"
            for entry in entries
        )
        error_count = sum(
            entry.level in {"ERROR", "CRITICAL"}
            for entry in entries
        )

        self.query_one("#logs-total", Static).update(
            "[b]EVENTS LOADED[/b]\n\n"
            f"[b]{len(entries)}[/b]"
        )

        self.query_one("#logs-info", Static).update(
            "[b]INFORMATION[/b]\n\n"
            f"[b cyan]{info_count}[/b cyan]"
        )

        warning_color = "yellow" if warning_count else "cyan"

        self.query_one("#logs-warning", Static).update(
            "[b]WARNINGS[/b]\n\n"
            f"[b {warning_color}]"
            f"{warning_count}"
            f"[/b {warning_color}]"
        )

        error_color = "red" if error_count else "cyan"

        self.query_one("#logs-errors", Static).update(
            "[b]ERRORS[/b]\n\n"
            f"[b {error_color}]"
            f"{error_count}"
            f"[/b {error_color}]"
        )

        if error_count:
            status = (
                "[b red]● ERRORS DETECTED[/b red]"
                f"    //    {error_count} EVENT(S) REQUIRE ATTENTION"
            )
        elif warning_count:
            status = (
                "[b yellow]● SYSTEM WARNINGS[/b yellow]"
                f"    //    {warning_count} EVENT(S)"
            )
        else:
            status = (
                "[b cyan]● EVENT STREAM NOMINAL[/b cyan]"
                "    //    NO ACTIVE ERRORS"
            )

        self.query_one("#logs-status", Static).update(status)

        rows = tuple(
            (
                entry.timestamp,
                self._format_level(entry.level),
                entry.source,
                entry.message,
            )
            for entry in reversed(entries)
        )

        if rows == self._last_rows:
            return

        table = self.query_one("#logs-table", DataTable)
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "—",
                "HELM",
                "NO EVENTS REGISTERED",
            )

        self._last_rows = rows

    @staticmethod
    def _format_level(level: str) -> str:
        colors = {
            "DEBUG": "#6a8790",
            "INFO": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red",
        }

        color = colors.get(level, "white")
        return f"[b {color}]{level}[/b {color}]"
