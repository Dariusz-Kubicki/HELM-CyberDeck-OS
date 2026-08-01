from __future__ import annotations

from collections import Counter

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Static,
)

from services.log_service import (
    LogEntry,
    LogService,
)


class LogsScreen(Vertical):
    """Searchable and controllable HELM event stream."""

    LEVEL_FILTERS = (
        "ALL",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
        "DEBUG",
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.level_filter = "ALL"
        self.source_filter = "ALL"
        self.search_text = ""

        self.paused = False
        self.pending_count = 0

        self._latest_entries: tuple[
            LogEntry,
            ...,
        ] = ()

        self._frozen_entries: tuple[
            LogEntry,
            ...,
        ] = ()

        self._visible_entries: tuple[
            LogEntry,
            ...,
        ] = ()

        self._pause_keys: Counter[
            tuple[str, str, str, str]
        ] = Counter()

        self._sources: tuple[str, ...] = (
            "ALL",
        )

        self._last_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

        self._synchronising_table = False
        self._clear_confirmation = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="logs-summary"):
            yield Static(
                "--",
                id="logs-total",
                classes="logs-card",
            )
            yield Static(
                "--",
                id="logs-info",
                classes="logs-card",
            )
            yield Static(
                "--",
                id="logs-warning",
                classes="logs-card",
            )
            yield Static(
                "--",
                id="logs-errors",
                classes="logs-card",
            )

        yield Static(
            "[b cyan]● EVENT STREAM ONLINE[/b cyan]",
            id="logs-status",
        )

        with Horizontal(id="logs-filter-row"):
            with Horizontal(
                classes="logs-cycle-control"
            ):
                yield Button(
                    "◀",
                    id="logs-level-prev",
                    classes="logs-cycle-arrow",
                )
                yield Static(
                    "LEVEL: ALL",
                    id="logs-level-value",
                    classes="logs-cycle-value",
                )
                yield Button(
                    "▶",
                    id="logs-level-next",
                    classes="logs-cycle-arrow",
                )

            with Horizontal(
                classes="logs-cycle-control"
            ):
                yield Button(
                    "◀",
                    id="logs-source-prev",
                    classes="logs-cycle-arrow",
                )
                yield Static(
                    "SOURCE: ALL",
                    id="logs-source-value",
                    classes="logs-cycle-value",
                )
                yield Button(
                    "▶",
                    id="logs-source-next",
                    classes="logs-cycle-arrow",
                )

            yield Input(
                placeholder=(
                    "Search source, message, level or time..."
                ),
                id="logs-search-input",
            )

            yield Button(
                "PAUSE STREAM",
                id="logs-pause",
                classes="logs-control-button",
                flat=True,
            )

        with Horizontal(id="logs-actions"):
            yield Button(
                "RESET FILTERS",
                id="logs-reset-filters",
                classes="logs-control-button",
                flat=True,
            )
            yield Button(
                "JUMP TO NEWEST",
                id="logs-jump-newest",
                classes="logs-control-button",
                flat=True,
            )
            yield Button(
                "CLEAR VIEW",
                id="logs-clear-view",
                classes="logs-control-button",
                flat=True,
            )
            yield Button(
                "EXPORT FILTERED",
                id="logs-export",
                classes="logs-control-button",
                flat=True,
            )
            yield Button(
                "CLEAR LOG FILE",
                id="logs-clear-file",
                classes="logs-delete-button",
            )

        yield Static(
            "[b cyan]EVENT DATABASE[/b cyan]"
            "    //    NEWEST EVENTS FIRST",
            id="logs-table-title",
        )

        yield DataTable(id="logs-table")

        yield Static(
            "[b cyan]EVENT INSPECTOR[/b cyan]"
            "    //    SELECT AN EVENT",
            id="logs-details",
        )

        yield Static(
            "Runtime file: logs/helm.log"
            "    //    Exports: logs/exports/",
            id="logs-path",
        )

    def on_mount(self) -> None:
        table = self.query_one(
            "#logs-table",
            DataTable,
        )

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "TIME",
            "LEVEL",
            "SOURCE",
            "MESSAGE",
        )

        self._update_filter_labels()
        self._update_summary(())
        self._render_table(
            empty_message="NO EVENTS REGISTERED"
        )

    def update_entries(
        self,
        entries: tuple[LogEntry, ...],
    ) -> None:
        self._latest_entries = entries
        self._refresh_sources(entries)

        if self.paused:
            current_keys = Counter(
                self._entry_key(entry)
                for entry in entries
            )

            self.pending_count = sum(
                max(
                    0,
                    count
                    - self._pause_keys.get(
                        key,
                        0,
                    ),
                )
                for key, count
                in current_keys.items()
            )

            self._update_status()
            return

        self._apply_filters()

    def _apply_filters(self) -> None:
        source_entries = (
            self._frozen_entries
            if self.paused
            else self._latest_entries
        )

        query = self.search_text.casefold()

        visible: list[LogEntry] = []

        for entry in reversed(source_entries):
            if (
                self.level_filter != "ALL"
                and entry.level
                != self.level_filter
            ):
                continue

            if (
                self.source_filter != "ALL"
                and entry.source
                != self.source_filter
            ):
                continue

            if query:
                searchable = " ".join(
                    (
                        entry.timestamp,
                        entry.level,
                        entry.source,
                        entry.message,
                    )
                ).casefold()

                if query not in searchable:
                    continue

            visible.append(entry)

        self._visible_entries = tuple(visible)

        self._update_summary(source_entries)
        self._render_table()
        self._update_status()

    def _refresh_sources(
        self,
        entries: tuple[LogEntry, ...],
    ) -> None:
        sources = tuple(
            sorted(
                {
                    entry.source
                    for entry in entries
                    if entry.source
                },
                key=str.casefold,
            )
        )

        self._sources = (
            "ALL",
            *sources,
        )

        if (
            self.source_filter
            not in self._sources
        ):
            self.source_filter = "ALL"

        self._update_filter_labels()

    def _update_summary(
        self,
        entries: tuple[LogEntry, ...],
    ) -> None:
        info_count = sum(
            entry.level in {
                "DEBUG",
                "INFO",
            }
            for entry in entries
        )

        warning_count = sum(
            entry.level == "WARNING"
            for entry in entries
        )

        error_count = sum(
            entry.level in {
                "ERROR",
                "CRITICAL",
            }
            for entry in entries
        )

        self.query_one(
            "#logs-total",
            Static,
        ).update(
            "[b]EVENTS LOADED[/b]\n\n"
            f"[b]{len(entries)}[/b]\n"
            f"{len(self._visible_entries)} VISIBLE"
        )

        self.query_one(
            "#logs-info",
            Static,
        ).update(
            "[b]INFORMATION[/b]\n\n"
            f"[b cyan]{info_count}[/b cyan]"
        )

        warning_color = (
            "yellow"
            if warning_count
            else "cyan"
        )

        self.query_one(
            "#logs-warning",
            Static,
        ).update(
            "[b]WARNINGS[/b]\n\n"
            f"[b {warning_color}]"
            f"{warning_count}"
            f"[/b {warning_color}]"
        )

        error_color = (
            "red"
            if error_count
            else "cyan"
        )

        self.query_one(
            "#logs-errors",
            Static,
        ).update(
            "[b]ERRORS[/b]\n\n"
            f"[b {error_color}]"
            f"{error_count}"
            f"[/b {error_color}]"
        )

    def _update_status(self) -> None:
        filter_description = (
            f"LEVEL {self.level_filter}"
            f"    //    SOURCE {self.source_filter}"
        )

        if self.search_text:
            filter_description += (
                f"    //    SEARCH {self.search_text}"
            )

        if self.paused:
            self.query_one(
                "#logs-status",
                Static,
            ).update(
                "[b yellow]● EVENT STREAM PAUSED[/b yellow]"
                f"    //    PENDING {self.pending_count}"
                f"    //    VISIBLE {len(self._visible_entries)}"
                f"    //    {escape(filter_description)}"
            )
            return

        visible_errors = sum(
            entry.level in {
                "ERROR",
                "CRITICAL",
            }
            for entry in self._visible_entries
        )

        visible_warnings = sum(
            entry.level == "WARNING"
            for entry in self._visible_entries
        )

        if visible_errors:
            state = (
                "[b red]● ERRORS IN CURRENT VIEW[/b red]"
                f"    //    {visible_errors} EVENT(S)"
            )

        elif visible_warnings:
            state = (
                "[b yellow]● WARNINGS IN CURRENT VIEW[/b yellow]"
                f"    //    {visible_warnings} EVENT(S)"
            )

        else:
            state = (
                "[b cyan]● EVENT STREAM NOMINAL[/b cyan]"
                f"    //    {len(self._visible_entries)} EVENT(S)"
            )

        final_status = (
            state
            + f"    //    {escape(filter_description)}"
        )

        self.query_one(
            "#logs-status",
            Static,
        ).update(final_status)

    def _render_table(
        self,
        *,
        empty_message: str = (
            "NO EVENTS MATCH CURRENT FILTERS"
        ),
        force: bool = False,
    ) -> None:
        rows = tuple(
            (
                entry.timestamp,
                self._format_level(
                    entry.level
                ),
                escape(entry.source),
                escape(entry.message),
            )
            for entry in self._visible_entries
        )

        if (
            rows == self._last_rows
            and not force
        ):
            return

        table = self.query_one(
            "#logs-table",
            DataTable,
        )

        self._synchronising_table = True

        try:
            table.clear()

            if rows:
                table.add_rows(rows)
                table.move_cursor(
                    row=0,
                    column=0,
                    scroll=False,
                )

            else:
                table.add_row(
                    "—",
                    "—",
                    "HELM",
                    empty_message,
                )

        finally:
            self._synchronising_table = False

        self._last_rows = rows

        if self._visible_entries:
            self._update_details(
                self._visible_entries[0]
            )
        else:
            self.query_one(
                "#logs-details",
                Static,
            ).update(
                "[b cyan]EVENT INSPECTOR[/b cyan]"
                "    //    NO EVENT SELECTED"
            )

    def on_data_table_row_highlighted(
        self,
        event: DataTable.RowHighlighted,
    ) -> None:
        if (
            self._synchronising_table
            or event.control.id != "logs-table"
        ):
            return

        row = event.cursor_row

        if not 0 <= row < len(
            self._visible_entries
        ):
            return

        self._update_details(
            self._visible_entries[row]
        )

    def _update_details(
        self,
        entry: LogEntry,
    ) -> None:
        color = self._level_color(
            entry.level
        )

        self.query_one(
            "#logs-details",
            Static,
        ).update(
            "[b cyan]EVENT INSPECTOR[/b cyan]\n\n"
            f"[b]TIME[/b]      "
            f"{escape(entry.timestamp)}\n"
            f"[b]LEVEL[/b]     "
            f"[b {color}]"
            f"{escape(entry.level)}"
            f"[/b {color}]\n"
            f"[b]SOURCE[/b]    "
            f"{escape(entry.source)}\n"
            f"[b]MESSAGE[/b]   "
            f"{escape(entry.message)}"
        )

    def on_input_changed(
        self,
        event: Input.Changed,
    ) -> None:
        if (
            event.input.id
            != "logs-search-input"
        ):
            return

        self.search_text = event.value.strip()
        self._apply_filters()

    def on_button_pressed(
        self,
        event: Button.Pressed,
    ) -> None:
        button_id = event.button.id

        if button_id is None:
            return

        if button_id != "logs-clear-file":
            self._reset_clear_confirmation()

        actions = {
            "logs-level-prev":
                lambda: self._cycle_level(-1),
            "logs-level-next":
                lambda: self._cycle_level(1),
            "logs-source-prev":
                lambda: self._cycle_source(-1),
            "logs-source-next":
                lambda: self._cycle_source(1),
            "logs-pause":
                self._toggle_pause,
            "logs-reset-filters":
                self._reset_filters,
            "logs-jump-newest":
                self._jump_to_newest,
            "logs-clear-view":
                self._clear_view,
            "logs-export":
                self._export_filtered,
            "logs-clear-file":
                self._clear_log_file,
        }

        action = actions.get(button_id)

        if action is None:
            return

        action()
        event.stop()

    def _cycle_level(
        self,
        direction: int,
    ) -> None:
        index = self.LEVEL_FILTERS.index(
            self.level_filter
        )

        self.level_filter = (
            self.LEVEL_FILTERS[
                (
                    index + direction
                ) % len(self.LEVEL_FILTERS)
            ]
        )

        self._update_filter_labels()
        self._apply_filters()

    def _cycle_source(
        self,
        direction: int,
    ) -> None:
        try:
            index = self._sources.index(
                self.source_filter
            )
        except ValueError:
            index = 0

        self.source_filter = self._sources[
            (
                index + direction
            ) % len(self._sources)
        ]

        self._update_filter_labels()
        self._apply_filters()

    def _update_filter_labels(self) -> None:
        self.query_one(
            "#logs-level-value",
            Static,
        ).update(
            f"LEVEL: {self.level_filter}"
        )

        source_label = self.source_filter

        if len(source_label) > 20:
            source_label = (
                source_label[:17] + "..."
            )

        self.query_one(
            "#logs-source-value",
            Static,
        ).update(
            f"SOURCE: {source_label}"
        )

    def _toggle_pause(self) -> None:
        button = self.query_one(
            "#logs-pause",
            Button,
        )

        if not self.paused:
            self.paused = True
            self.pending_count = 0
            self._frozen_entries = (
                self._latest_entries
            )

            self._pause_keys = Counter(
                self._entry_key(entry)
                for entry
                in self._latest_entries
            )

            button.label = "RESUME STREAM"

        else:
            self.paused = False
            self.pending_count = 0
            self._frozen_entries = ()
            self._pause_keys.clear()

            button.label = "PAUSE STREAM"

        self._apply_filters()

    def _reset_filters(self) -> None:
        self.level_filter = "ALL"
        self.source_filter = "ALL"
        self.search_text = ""

        self.query_one(
            "#logs-search-input",
            Input,
        ).value = ""

        self._update_filter_labels()
        self._apply_filters()

    def _jump_to_newest(self) -> None:
        if not self._visible_entries:
            self._set_status(
                "NO VISIBLE EVENTS",
                "Current filters returned no events.",
                "yellow",
            )
            return

        table = self.query_one(
            "#logs-table",
            DataTable,
        )

        table.move_cursor(
            row=0,
            column=0,
            scroll=True,
        )

        self._update_details(
            self._visible_entries[0]
        )

        self._set_status(
            "NEWEST EVENT SELECTED",
            self._visible_entries[0].timestamp,
            "cyan",
        )

    def _clear_view(self) -> None:
        self.paused = True
        self.pending_count = 0
        self._frozen_entries = ()
        self._visible_entries = ()

        self._pause_keys = Counter(
            self._entry_key(entry)
            for entry in self._latest_entries
        )

        self.query_one(
            "#logs-pause",
            Button,
        ).label = "RESUME STREAM"

        self._update_summary(())
        self._render_table(
            empty_message=(
                "VIEW CLEARED — RESUME STREAM TO RELOAD"
            ),
            force=True,
        )

        self._set_status(
            "VIEW CLEARED",
            (
                "Log file was not modified; "
                "event stream is paused."
            ),
            "#70a9b8",
        )

    def _export_filtered(self) -> None:
        if not self._visible_entries:
            self._set_status(
                "EXPORT SKIPPED",
                "No visible events to export.",
                "yellow",
            )
            return

        service = self._log_service()

        if service is None:
            self._set_status(
                "EXPORT FAILED",
                "LogService is unavailable.",
                "red",
            )
            return

        try:
            export_path = service.export_entries(
                reversed(
                    self._visible_entries
                )
            )

        except OSError as error:
            self._set_status(
                "EXPORT FAILED",
                f"{type(error).__name__}: {error}",
                "red",
            )
            return

        service.info(
            "LOGS",
            (
                f"Exported "
                f"{len(self._visible_entries)} "
                f"filtered event(s) to "
                f"{export_path}"
            ),
        )

        self._set_status(
            "EXPORT COMPLETE",
            str(export_path),
            "cyan",
        )

    def _clear_log_file(self) -> None:
        button = self.query_one(
            "#logs-clear-file",
            Button,
        )

        if not self._clear_confirmation:
            self._clear_confirmation = True
            button.label = "CONFIRM CLEAR LOG"

            self._set_status(
                "CLEAR CONFIRMATION",
                (
                    "Press CONFIRM CLEAR LOG "
                    "to erase logs/helm.log."
                ),
                "yellow",
            )
            return

        service = self._log_service()

        if service is None:
            self._set_status(
                "CLEAR FAILED",
                "LogService is unavailable.",
                "red",
            )
            return

        try:
            service.clear()
        except OSError as error:
            self._set_status(
                "CLEAR FAILED",
                f"{type(error).__name__}: {error}",
                "red",
            )
            return

        self._reset_clear_confirmation()

        self.paused = False
        self.pending_count = 0

        self._latest_entries = ()
        self._frozen_entries = ()
        self._visible_entries = ()
        self._pause_keys.clear()

        self.query_one(
            "#logs-pause",
            Button,
        ).label = "PAUSE STREAM"

        self._refresh_sources(())
        self._update_summary(())
        self._render_table(
            empty_message="LOG FILE CLEARED",
            force=True,
        )

        self._set_status(
            "LOG FILE CLEARED",
            "logs/helm.log now contains no events.",
            "yellow",
        )

    def _reset_clear_confirmation(self) -> None:
        if not self._clear_confirmation:
            return

        self._clear_confirmation = False

        self.query_one(
            "#logs-clear-file",
            Button,
        ).label = "CLEAR LOG FILE"

    def _log_service(
        self,
    ) -> LogService | None:
        service = getattr(
            self.app,
            "log_service",
            None,
        )

        return (
            service
            if isinstance(service, LogService)
            else None
        )

    def _set_status(
        self,
        state: str,
        detail: str,
        color: str,
    ) -> None:
        self.query_one(
            "#logs-status",
            Static,
        ).update(
            f"[b {color}]"
            f"● {escape(state)}"
            f"[/b {color}]"
            f"    //    {escape(detail)}"
        )

    @staticmethod
    def _entry_key(
        entry: LogEntry,
    ) -> tuple[str, str, str, str]:
        return (
            entry.timestamp,
            entry.level,
            entry.source,
            entry.message,
        )

    @staticmethod
    def _level_color(
        level: str,
    ) -> str:
        return {
            "DEBUG": "#6a8790",
            "INFO": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red",
        }.get(level, "white")

    @classmethod
    def _format_level(
        cls,
        level: str,
    ) -> str:
        color = cls._level_color(level)

        return (
            f"[b {color}]"
            f"{level}"
            f"[/b {color}]"
        )
