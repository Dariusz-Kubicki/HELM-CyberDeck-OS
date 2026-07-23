from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Static,
    TextArea,
)

from services.mode_service import (
    ModeMutationResult,
    ModeService,
    WorkMode,
)
from services.workspace_service import (
    LaunchResult,
    WorkspaceService,
)


class ModesScreen(Vertical):
    """Editable CyberDeck workspace control center."""

    TELEMETRY_OPTIONS = (
        0.5,
        1.0,
        2.0,
        5.0,
        10.0,
    )

    SCREEN_OPTIONS = (
        "system",
        "network",
        "storage",
        "devices",
        "modes",
        "projects",
        "logs",
        "ai",
        "settings",
    )

    POWER_OPTIONS = (
        "unchanged",
        "balanced",
        "performance",
        "power-saver",
    )

    def __init__(
        self,
        modes: tuple[WorkMode, ...],
        active_mode_id: str,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.mode_service = ModeService()
        self.workspace_service = WorkspaceService()

        self.modes = modes
        self.mode_map = {
            mode.mode_id: mode
            for mode in modes
        }

        self.active_mode_id = active_mode_id
        self.selected_mode_id = (
            active_mode_id
            if active_mode_id in self.mode_map
            else modes[0].mode_id
        )

        self.selected_application_index = 0

        self.editing_mode_id: str | None = None
        self.creating_mode = False

        self.editor_telemetry = 1.0
        self.editor_target_screen = "system"
        self.editor_navigation_logging = True
        self.editor_power_profile = "unchanged"

        self.pending_delete_mode_id: str | None = None
        self.pending_remove_application: (
            tuple[str, int] | None
        ) = None

        self._last_mode_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

        self._last_application_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

        self._synchronising_tables = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="modes-summary"):
            yield Static(
                "--",
                id="mode-active-summary",
                classes="mode-summary-card",
            )
            yield Static(
                "--",
                id="mode-workload-summary",
                classes="mode-summary-card",
            )
            yield Static(
                "--",
                id="mode-refresh-summary",
                classes="mode-summary-card",
            )
            yield Static(
                "--",
                id="mode-target-summary",
                classes="mode-summary-card",
            )

        yield Static(
            "[b cyan]● WORKSPACE ENGINE ONLINE[/b cyan]"
            "    //    SELECT AN OPERATION ENVIRONMENT",
            id="mode-status",
        )

        yield Static(
            "[b cyan]WORKSPACE DATABASE[/b cyan]"
            "    //    SELECT A PROFILE",
            classes="modes-section-title",
        )

        yield DataTable(id="modes-table")

        with Horizontal(id="mode-database-actions"):
            yield Button(
                "EDIT MODE",
                id="mode-edit",
                classes="mode-control-button",
            )
            yield Button(
                "NEW MODE",
                id="mode-new",
                classes="mode-control-button",
            )
            yield Button(
                "CLONE MODE",
                id="mode-clone",
                classes="mode-control-button",
            )
            yield Button(
                "DELETE MODE",
                id="mode-delete",
                classes="mode-delete-button",
            )

        yield Static(
            "SELECT A WORKSPACE",
            id="mode-details",
        )

        yield Static(
            "[b cyan]APPLICATION MANIFEST[/b cyan]"
            "    //    APPLICATIONS AND WEB WORKSPACES",
            id="mode-applications-title",
            classes="modes-section-title",
        )

        yield DataTable(id="mode-applications-table")

        with Horizontal(id="mode-application-actions"):
            yield Button(
                "ENABLE / DISABLE",
                id="mode-app-toggle",
                classes="mode-control-button",
            )
            yield Button(
                "LAUNCH SELECTED",
                id="mode-app-launch",
                classes="mode-control-button",
            )
            yield Button(
                "REMOVE SELECTED",
                id="mode-app-remove",
                classes="mode-delete-button",
            )

        with Horizontal(id="mode-web-app-editor"):
            yield Input(
                placeholder="Web application name",
                id="mode-web-app-name",
            )
            yield Input(
                placeholder=(
                    "URLs separated with commas, "
                    "for example chatgpt.com, github.com"
                ),
                id="mode-web-app-urls",
            )
            yield Button(
                "ADD WEB APP",
                id="mode-web-app-add",
                classes="mode-control-button",
            )

        yield Static(
            "No workspace has been launched during this session.",
            id="mode-launch-report",
        )

        with Horizontal(id="mode-actions"):
            yield Button(
                "ACTIVATE WORKSPACE",
                id="mode-activate",
                variant="primary",
            )

        yield Static(
            "[b cyan]WORKSPACE EDITOR[/b cyan]"
            "    //    EDIT OR CREATE A PROFILE",
            id="mode-editor-title",
        )

        with Horizontal(id="mode-editor-basic"):
            with Vertical(classes="mode-editor-column"):
                yield Static(
                    "WORKSPACE NAME",
                    classes="mode-field-label",
                )
                yield Input(
                    placeholder="WORKSPACE NAME",
                    id="mode-name-input",
                    disabled=True,
                )

                yield Static(
                    "WORKLOAD PROFILE",
                    classes="mode-field-label",
                )
                yield Input(
                    placeholder="BALANCED / DEVELOPER / HARDWARE LAB",
                    id="mode-workload-input",
                    disabled=True,
                )

            with Vertical(classes="mode-editor-column"):
                yield Static(
                    "DESCRIPTION",
                    classes="mode-field-label",
                )
                yield TextArea(
                    "",
                    placeholder="Describe the workspace...",
                    id="mode-description-input",
                    disabled=True,
                )

        with Horizontal(id="mode-editor-controls"):
            with Horizontal(classes="mode-cycle-control"):
                yield Button(
                    "◀",
                    id="mode-telemetry-prev",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )
                yield Static(
                    "TELEMETRY: 1s",
                    id="mode-telemetry-value",
                    classes="mode-cycle-value",
                )
                yield Button(
                    "▶",
                    id="mode-telemetry-next",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )

            with Horizontal(classes="mode-cycle-control"):
                yield Button(
                    "◀",
                    id="mode-target-prev",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )
                yield Static(
                    "TARGET: SYSTEM",
                    id="mode-target-value",
                    classes="mode-cycle-value",
                )
                yield Button(
                    "▶",
                    id="mode-target-next",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )

            with Horizontal(classes="mode-cycle-control"):
                yield Button(
                    "◀",
                    id="mode-navigation-toggle",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )
                yield Static(
                    "NAV LOG: ENABLED",
                    id="mode-navigation-value",
                    classes="mode-cycle-value",
                )
                yield Button(
                    "▶",
                    id="mode-navigation-toggle-right",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )

            with Horizontal(classes="mode-cycle-control"):
                yield Button(
                    "◀",
                    id="mode-power-prev",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )
                yield Static(
                    "POWER: UNCHANGED",
                    id="mode-power-value",
                    classes="mode-cycle-value",
                )
                yield Button(
                    "▶",
                    id="mode-power-next",
                    classes="mode-cycle-arrow",
                    disabled=True,
                )

        yield Static(
            "PRIMARY OBJECTIVE",
            classes="mode-field-label standalone",
        )
        yield TextArea(
            "",
            placeholder="What should this workspace accomplish?",
            id="mode-objective-input",
            disabled=True,
        )

        yield Static(
            "CAPABILITIES // ONE ENTRY PER LINE",
            classes="mode-field-label standalone",
        )
        yield TextArea(
            "",
            placeholder=(
                "Open project editor\n"
                "Launch browser workspace\n"
                "Switch HELM to AI"
            ),
            id="mode-features-input",
            disabled=True,
        )

        with Horizontal(id="mode-editor-actions"):
            yield Button(
                "SAVE MODE",
                id="mode-save",
                variant="primary",
                disabled=True,
            )
            yield Button(
                "CANCEL",
                id="mode-cancel",
                disabled=True,
            )

        yield Static(
            "Workspace database: config/modes.json",
            id="mode-config-path",
        )

    def on_mount(self) -> None:
        modes_table = self.query_one(
            "#modes-table",
            DataTable,
        )

        modes_table.cursor_type = "row"
        modes_table.zebra_stripes = True
        modes_table.add_columns(
            "ACTIVE",
            "MODE",
            "WORKLOAD",
            "TARGET",
            "TELEMETRY",
            "APPS",
        )

        applications_table = self.query_one(
            "#mode-applications-table",
            DataTable,
        )

        applications_table.cursor_type = "row"
        applications_table.zebra_stripes = True
        applications_table.add_columns(
            "STATE",
            "TYPE",
            "APPLICATION",
            "TARGET / COMMAND",
            "POLICY",
        )

        self._set_editor_enabled(False)
        self._reload_modes(
            preferred_mode_id=self.selected_mode_id
        )

        self.update_active_mode(
            self.active_mode_id,
            "UNCHANGED",
        )

    def _reload_modes(
        self,
        *,
        preferred_mode_id: str | None = None,
    ) -> None:
        try:
            modes = self.mode_service.load_modes()
        except RuntimeError as error:
            self._set_status(
                "WORKSPACE DATABASE ERROR",
                str(error),
                "red",
            )
            return

        self.modes = modes
        self.mode_map = {
            mode.mode_id: mode
            for mode in modes
        }

        candidate = (
            preferred_mode_id
            or self.selected_mode_id
            or self.active_mode_id
        )

        self.selected_mode_id = (
            candidate
            if candidate in self.mode_map
            else modes[0].mode_id
        )

        self._refresh_mode_table()
        self.select_mode(
            self.selected_mode_id
        )
        self._update_active_summary()

    def _refresh_mode_table(self) -> None:
        rows = tuple(
            (
                (
                    "● ACTIVE"
                    if mode.mode_id
                    == self.active_mode_id
                    else "—"
                ),
                mode.name,
                mode.workload_profile,
                mode.target_screen.upper(),
                f"{mode.telemetry_interval:g}s",
                str(len(mode.applications)),
            )
            for mode in self.modes
        )

        if rows == self._last_mode_rows:
            return

        table = self.query_one(
            "#modes-table",
            DataTable,
        )

        self._synchronising_tables = True

        try:
            table.clear()
            table.add_rows(rows)
        finally:
            self._synchronising_tables = False

        self._last_mode_rows = rows

    def select_mode(
        self,
        mode_id: str,
    ) -> None:
        mode = self.mode_map.get(mode_id)

        if mode is None:
            return

        self.selected_mode_id = mode_id
        self.selected_application_index = 0

        for index, known_mode in enumerate(self.modes):
            if known_mode.mode_id != mode_id:
                continue

            self.query_one(
                "#modes-table",
                DataTable,
            ).move_cursor(
                row=index,
                column=0,
                scroll=False,
            )
            break

        self._update_mode_details(mode)
        self._refresh_application_table(mode)

        if not self._editor_active:
            self._load_mode_into_editor(mode)

    def _update_mode_details(
        self,
        mode: WorkMode,
    ) -> None:
        enabled_apps = sum(
            application.enabled
            for application in mode.applications
        )

        features = (
            "\n".join(
                f"  • {escape(feature)}"
                for feature in mode.features
            )
            if mode.features
            else "  • No capabilities registered"
        )

        self.query_one(
            "#mode-details",
            Static,
        ).update(
            f"[b cyan]{escape(mode.name)} WORKSPACE[/b cyan]\n\n"
            f"{escape(mode.description)}\n\n"
            f"[b]PRIMARY OBJECTIVE[/b]\n"
            f"{escape(mode.objective)}\n\n"
            f"[b]WORKSPACE PARAMETERS[/b]\n"
            f"  WORKLOAD         "
            f"{escape(mode.workload_profile)}\n"
            f"  TELEMETRY        "
            f"{mode.telemetry_interval:g} seconds\n"
            f"  TARGET SCREEN    "
            f"{mode.target_screen.upper()}\n"
            f"  NAVIGATION LOG   "
            f"{'ENABLED' if mode.navigation_logging else 'DISABLED'}\n"
            f"  POWER PROFILE    "
            f"{mode.power_profile.upper()}\n"
            f"  APPLICATIONS     "
            f"{enabled_apps}/{len(mode.applications)} ENABLED\n\n"
            f"[b]CAPABILITIES[/b]\n"
            f"{features}"
        )

    def _refresh_application_table(
        self,
        mode: WorkMode,
    ) -> None:
        rows = tuple(
            (
                (
                    "ENABLED"
                    if application.enabled
                    else "DISABLED"
                ),
                application.kind.upper(),
                application.name,
                self._application_target(
                    application
                ),
                (
                    "SKIP IF RUNNING"
                    if application.skip_if_running
                    else "ALWAYS LAUNCH"
                ),
            )
            for application in mode.applications
        )

        table = self.query_one(
            "#mode-applications-table",
            DataTable,
        )

        self._synchronising_tables = True

        try:
            table.clear()

            if rows:
                table.add_rows(rows)
            else:
                table.add_row(
                    "—",
                    "—",
                    "NO APPLICATIONS CONFIGURED",
                    "—",
                    "—",
                )
        finally:
            self._synchronising_tables = False

        self._last_application_rows = rows

        enabled_count = sum(
            application.enabled
            for application in mode.applications
        )

        self.query_one(
            "#mode-applications-title",
            Static,
        ).update(
            "[b cyan]APPLICATION MANIFEST[/b cyan]"
            f"    //    TOTAL {len(mode.applications)}"
            f"    //    ENABLED {enabled_count}"
        )

    @staticmethod
    def _application_target(
        application,
    ) -> str:
        if application.kind == "browser":
            return (
                ", ".join(application.urls)
                or "NO URLS"
            )

        if application.alternatives:
            return " | ".join(
                " ".join(command)
                for command
                in application.alternatives
            )

        return "NO COMMAND"

    def on_data_table_row_highlighted(
        self,
        event: DataTable.RowHighlighted,
    ) -> None:
        if self._synchronising_tables:
            return

        if event.control.id == "modes-table":
            row = event.cursor_row

            if 0 <= row < len(self.modes):
                self._reset_confirmations()
                self.select_mode(
                    self.modes[row].mode_id
                )

            return

        if (
            event.control.id
            == "mode-applications-table"
        ):
            mode = self._selected_mode()

            if mode is None:
                return

            row = event.cursor_row

            if 0 <= row < len(mode.applications):
                self.selected_application_index = row
                self._reset_application_confirmation()

    @property
    def _editor_active(self) -> bool:
        return (
            self.editing_mode_id is not None
            or self.creating_mode
        )

    def _selected_mode(
        self,
    ) -> WorkMode | None:
        return self.mode_map.get(
            self.selected_mode_id
        )

    def _selected_application(self):
        mode = self._selected_mode()

        if (
            mode is None
            or not 0 <= self.selected_application_index
            < len(mode.applications)
        ):
            return None

        return mode.applications[
            self.selected_application_index
        ]

    def _load_mode_into_editor(
        self,
        mode: WorkMode,
    ) -> None:
        self.query_one(
            "#mode-name-input",
            Input,
        ).value = mode.name

        self.query_one(
            "#mode-workload-input",
            Input,
        ).value = mode.workload_profile

        self.query_one(
            "#mode-description-input",
            TextArea,
        ).text = mode.description

        self.query_one(
            "#mode-objective-input",
            TextArea,
        ).text = mode.objective

        self.query_one(
            "#mode-features-input",
            TextArea,
        ).text = "\n".join(
            mode.features
        )

        self.editor_telemetry = (
            mode.telemetry_interval
        )
        self.editor_target_screen = (
            mode.target_screen
        )
        self.editor_navigation_logging = (
            mode.navigation_logging
        )
        self.editor_power_profile = (
            mode.power_profile
        )

        self._update_editor_labels()

        self.query_one(
            "#mode-editor-title",
            Static,
        ).update(
            "[b cyan]SELECTED WORKSPACE[/b cyan]"
            f"    //    {escape(mode.name)}"
            f"    //    ID {escape(mode.mode_id)}"
        )

    def _clear_editor(self) -> None:
        self.query_one(
            "#mode-name-input",
            Input,
        ).value = ""

        self.query_one(
            "#mode-workload-input",
            Input,
        ).value = ""

        self.query_one(
            "#mode-description-input",
            TextArea,
        ).text = ""

        self.query_one(
            "#mode-objective-input",
            TextArea,
        ).text = ""

        self.query_one(
            "#mode-features-input",
            TextArea,
        ).text = ""

        self.editor_telemetry = 1.0
        self.editor_target_screen = "system"
        self.editor_navigation_logging = True
        self.editor_power_profile = "unchanged"

        self._update_editor_labels()

    def _begin_edit(self) -> None:
        mode = self._selected_mode()

        if mode is None:
            self._set_status(
                "NO WORKSPACE SELECTED",
                "Select a workspace first.",
                "yellow",
            )
            return

        self.editing_mode_id = mode.mode_id
        self.creating_mode = False

        self._load_mode_into_editor(mode)
        self._set_editor_enabled(True)

        self.query_one(
            "#mode-editor-title",
            Static,
        ).update(
            "[b cyan]EDITING WORKSPACE[/b cyan]"
            f"    //    {escape(mode.name)}"
        )

        self._set_status(
            "EDIT MODE ACTIVE",
            "Change the profile and press SAVE MODE.",
            "cyan",
        )

    def _begin_new(self) -> None:
        self.editing_mode_id = None
        self.creating_mode = True

        self._clear_editor()

        self.query_one(
            "#mode-name-input",
            Input,
        ).value = "NEW WORKSPACE"

        self.query_one(
            "#mode-workload-input",
            Input,
        ).value = "BALANCED"

        self.query_one(
            "#mode-description-input",
            TextArea,
        ).text = (
            "Custom CyberDeck operating environment."
        )

        self.query_one(
            "#mode-objective-input",
            TextArea,
        ).text = (
            "Define the primary workspace objective."
        )

        self._set_editor_enabled(True)

        self.query_one(
            "#mode-name-input",
            Input,
        ).focus()

        self.query_one(
            "#mode-editor-title",
            Static,
        ).update(
            "[b cyan]CREATING WORKSPACE[/b cyan]"
            "    //    ENTER PROFILE PARAMETERS"
        )

        self._set_status(
            "NEW WORKSPACE",
            "Complete the editor and save.",
            "cyan",
        )

    def _save_editor(self) -> None:
        name = self.query_one(
            "#mode-name-input",
            Input,
        ).value.strip()

        if not name:
            self._set_status(
                "VALIDATION ERROR",
                "Workspace name cannot be empty.",
                "red",
            )
            return

        fields = {
            "name": name,
            "workload_profile": self.query_one(
                "#mode-workload-input",
                Input,
            ).value.strip(),
            "description": self.query_one(
                "#mode-description-input",
                TextArea,
            ).text.strip(),
            "objective": self.query_one(
                "#mode-objective-input",
                TextArea,
            ).text.strip(),
            "features": self.query_one(
                "#mode-features-input",
                TextArea,
            ).text,
            "telemetry_interval": (
                self.editor_telemetry
            ),
            "target_screen": (
                self.editor_target_screen
            ),
            "navigation_logging": (
                self.editor_navigation_logging
            ),
            "power_profile": (
                self.editor_power_profile
            ),
        }

        if self.creating_mode:
            result = self.mode_service.create_mode(
                fields
            )

        elif self.editing_mode_id is not None:
            result = self.mode_service.update_mode(
                self.editing_mode_id,
                fields,
            )

        else:
            return

        if result.status in {
            "SAVED",
            "CREATED",
        }:
            self.editing_mode_id = None
            self.creating_mode = False
            self._set_editor_enabled(False)

            self._reload_modes(
                preferred_mode_id=result.mode_id
            )

        self._handle_mutation(result)

    def _cancel_editor(self) -> None:
        self.editing_mode_id = None
        self.creating_mode = False
        self._set_editor_enabled(False)

        mode = self._selected_mode()

        if mode is not None:
            self._load_mode_into_editor(mode)

        self._set_status(
            "EDIT CANCELLED",
            "No changes were written.",
            "#70a9b8",
        )

    def _set_editor_enabled(
        self,
        enabled: bool,
    ) -> None:
        for input_id in (
            "#mode-name-input",
            "#mode-workload-input",
        ):
            self.query_one(
                input_id,
                Input,
            ).disabled = not enabled

        for text_area_id in (
            "#mode-description-input",
            "#mode-objective-input",
            "#mode-features-input",
        ):
            self.query_one(
                text_area_id,
                TextArea,
            ).disabled = not enabled

        for button_id in (
            "#mode-telemetry-prev",
            "#mode-telemetry-next",
            "#mode-target-prev",
            "#mode-target-next",
            "#mode-navigation-toggle",
            "#mode-navigation-toggle-right",
            "#mode-power-prev",
            "#mode-power-next",
            "#mode-save",
            "#mode-cancel",
        ):
            self.query_one(
                button_id,
                Button,
            ).disabled = not enabled

        for button_id in (
            "#mode-edit",
            "#mode-new",
            "#mode-clone",
            "#mode-delete",
        ):
            self.query_one(
                button_id,
                Button,
            ).disabled = enabled

        self.query_one(
            "#modes-table",
            DataTable,
        ).disabled = enabled

    def _cycle_telemetry(
        self,
        direction: int,
    ) -> None:
        index = min(
            range(len(self.TELEMETRY_OPTIONS)),
            key=lambda candidate: abs(
                self.TELEMETRY_OPTIONS[candidate]
                - self.editor_telemetry
            ),
        )

        self.editor_telemetry = (
            self.TELEMETRY_OPTIONS[
                (
                    index + direction
                ) % len(self.TELEMETRY_OPTIONS)
            ]
        )

        self._update_editor_labels()

    def _cycle_target(
        self,
        direction: int,
    ) -> None:
        try:
            index = self.SCREEN_OPTIONS.index(
                self.editor_target_screen
            )
        except ValueError:
            index = 0

        self.editor_target_screen = (
            self.SCREEN_OPTIONS[
                (
                    index + direction
                ) % len(self.SCREEN_OPTIONS)
            ]
        )

        self._update_editor_labels()

    def _toggle_navigation(self) -> None:
        self.editor_navigation_logging = (
            not self.editor_navigation_logging
        )
        self._update_editor_labels()

    def _cycle_power(
        self,
        direction: int,
    ) -> None:
        try:
            index = self.POWER_OPTIONS.index(
                self.editor_power_profile
            )
        except ValueError:
            index = 0

        self.editor_power_profile = (
            self.POWER_OPTIONS[
                (
                    index + direction
                ) % len(self.POWER_OPTIONS)
            ]
        )

        self._update_editor_labels()

    def _update_editor_labels(self) -> None:
        self.query_one(
            "#mode-telemetry-value",
            Static,
        ).update(
            f"TELEMETRY: "
            f"{self.editor_telemetry:g}s"
        )

        self.query_one(
            "#mode-target-value",
            Static,
        ).update(
            f"TARGET: "
            f"{self.editor_target_screen.upper()}"
        )

        self.query_one(
            "#mode-navigation-value",
            Static,
        ).update(
            "NAV LOG: "
            + (
                "ENABLED"
                if self.editor_navigation_logging
                else "DISABLED"
            )
        )

        self.query_one(
            "#mode-power-value",
            Static,
        ).update(
            f"POWER: "
            f"{self.editor_power_profile.upper()}"
        )

    def _clone_selected(self) -> None:
        mode = self._selected_mode()

        if mode is None:
            return

        result = self.mode_service.clone_mode(
            mode.mode_id
        )

        if result.status == "CREATED":
            self._reload_modes(
                preferred_mode_id=result.mode_id
            )

        self._handle_mutation(result)

    def _delete_selected(self) -> None:
        mode = self._selected_mode()

        if mode is None:
            return

        button = self.query_one(
            "#mode-delete",
            Button,
        )

        if (
            self.pending_delete_mode_id
            != mode.mode_id
        ):
            self.pending_delete_mode_id = (
                mode.mode_id
            )
            button.label = "CONFIRM DELETE"

            self._set_status(
                "DELETE CONFIRMATION",
                (
                    f"Press CONFIRM DELETE to remove "
                    f"{mode.name}."
                ),
                "yellow",
            )
            return

        result = self.mode_service.delete_mode(
            mode.mode_id,
            protected_mode_id=self.active_mode_id,
        )

        self.pending_delete_mode_id = None
        button.label = "DELETE MODE"

        if result.status == "DELETED":
            self._reload_modes()

        self._handle_mutation(result)

    def _toggle_application(self) -> None:
        mode = self._selected_mode()

        if (
            mode is None
            or self._selected_application() is None
        ):
            self._set_status(
                "NO APPLICATION SELECTED",
                "Select an application first.",
                "yellow",
            )
            return

        result = self.mode_service.toggle_application(
            mode.mode_id,
            self.selected_application_index,
        )

        if result.status == "SAVED":
            self._reload_modes(
                preferred_mode_id=mode.mode_id
            )

        self._handle_mutation(result)

    def _launch_application(self) -> None:
        application = self._selected_application()

        if application is None:
            self._set_status(
                "NO APPLICATION SELECTED",
                "Select an application first.",
                "yellow",
            )
            return

        result = (
            self.workspace_service
            .launch_application(application)
        )

        self._show_single_launch(result)
        self._log_result(
            "MODE APPLICATION",
            result.status,
            (
                f"{result.application}; "
                f"{result.detail}"
            ),
        )

    def _add_web_application(self) -> None:
        mode = self._selected_mode()

        if mode is None:
            return

        name_input = self.query_one(
            "#mode-web-app-name",
            Input,
        )

        urls_input = self.query_one(
            "#mode-web-app-urls",
            Input,
        )

        result = (
            self.mode_service
            .add_browser_application(
                mode.mode_id,
                name_input.value,
                urls_input.value,
            )
        )

        if result.status == "CREATED":
            name_input.value = ""
            urls_input.value = ""

            self._reload_modes(
                preferred_mode_id=mode.mode_id
            )

        self._handle_mutation(result)

    def _remove_application(self) -> None:
        mode = self._selected_mode()
        application = self._selected_application()

        if mode is None or application is None:
            self._set_status(
                "NO APPLICATION SELECTED",
                "Select an application first.",
                "yellow",
            )
            return

        key = (
            mode.mode_id,
            self.selected_application_index,
        )

        button = self.query_one(
            "#mode-app-remove",
            Button,
        )

        if self.pending_remove_application != key:
            self.pending_remove_application = key
            button.label = "CONFIRM REMOVE"

            self._set_status(
                "REMOVE CONFIRMATION",
                (
                    f"Press CONFIRM REMOVE to delete "
                    f"{application.name} from the manifest."
                ),
                "yellow",
            )
            return

        result = self.mode_service.remove_application(
            mode.mode_id,
            self.selected_application_index,
        )

        self.pending_remove_application = None
        button.label = "REMOVE SELECTED"

        if result.status == "DELETED":
            self.selected_application_index = 0
            self._reload_modes(
                preferred_mode_id=mode.mode_id
            )

        self._handle_mutation(result)

    def on_button_pressed(
        self,
        event: Button.Pressed,
    ) -> None:
        button_id = event.button.id

        # Activation remains handled by HELM main.py.
        if button_id == "mode-activate":
            return

        if button_id is None:
            return

        if button_id != "mode-delete":
            self._reset_mode_confirmation()

        if button_id != "mode-app-remove":
            self._reset_application_confirmation()

        actions = {
            "mode-edit": self._begin_edit,
            "mode-new": self._begin_new,
            "mode-clone": self._clone_selected,
            "mode-delete": self._delete_selected,
            "mode-save": self._save_editor,
            "mode-cancel": self._cancel_editor,
            "mode-telemetry-prev":
                lambda: self._cycle_telemetry(-1),
            "mode-telemetry-next":
                lambda: self._cycle_telemetry(1),
            "mode-target-prev":
                lambda: self._cycle_target(-1),
            "mode-target-next":
                lambda: self._cycle_target(1),
            "mode-navigation-toggle":
                self._toggle_navigation,
            "mode-navigation-toggle-right":
                self._toggle_navigation,
            "mode-power-prev":
                lambda: self._cycle_power(-1),
            "mode-power-next":
                lambda: self._cycle_power(1),
            "mode-app-toggle":
                self._toggle_application,
            "mode-app-launch":
                self._launch_application,
            "mode-app-remove":
                self._remove_application,
            "mode-web-app-add":
                self._add_web_application,
        }

        action = actions.get(button_id)

        if action is None:
            return

        action()
        event.stop()

    def _reset_confirmations(self) -> None:
        self._reset_mode_confirmation()
        self._reset_application_confirmation()

    def _reset_mode_confirmation(self) -> None:
        if self.pending_delete_mode_id is None:
            return

        self.pending_delete_mode_id = None
        self.query_one(
            "#mode-delete",
            Button,
        ).label = "DELETE MODE"

    def _reset_application_confirmation(self) -> None:
        if self.pending_remove_application is None:
            return

        self.pending_remove_application = None
        self.query_one(
            "#mode-app-remove",
            Button,
        ).label = "REMOVE SELECTED"

    def update_active_mode(
        self,
        mode_id: str,
        power_profile: str,
        message: str | None = None,
    ) -> None:
        self.active_mode_id = mode_id
        self._last_mode_rows = ()
        self._refresh_mode_table()
        self._update_active_summary()

        if message:
            self.query_one(
                "#mode-status",
                Static,
            ).update(
                "[b cyan]● WORKSPACE ENGINE READY[/b cyan]"
                f"    //    {escape(message)}"
                f"    //    SYSTEM POWER "
                f"{escape(power_profile)}"
            )

    def _update_active_summary(self) -> None:
        active_mode = self.mode_map.get(
            self.active_mode_id
        )

        if active_mode is None:
            mode_name = "CUSTOM"
            workload = "CUSTOM"
            refresh = "CUSTOM"
            target = "CUSTOM"
        else:
            mode_name = active_mode.name
            workload = active_mode.workload_profile
            refresh = (
                f"{active_mode.telemetry_interval:g}s"
            )
            target = (
                active_mode.target_screen.upper()
            )

        self.query_one(
            "#mode-active-summary",
            Static,
        ).update(
            "[b]ACTIVE WORKSPACE[/b]\n\n"
            f"[b cyan]{escape(mode_name)}[/b cyan]"
        )

        self.query_one(
            "#mode-workload-summary",
            Static,
        ).update(
            "[b]WORKLOAD[/b]\n\n"
            f"[b]{escape(workload)}[/b]"
        )

        self.query_one(
            "#mode-refresh-summary",
            Static,
        ).update(
            "[b]TELEMETRY[/b]\n\n"
            f"[b]{escape(refresh)}[/b]"
        )

        self.query_one(
            "#mode-target-summary",
            Static,
        ).update(
            "[b]TARGET SCREEN[/b]\n\n"
            f"[b]{escape(target)}[/b]"
        )

    def show_activation(
        self,
        mode: WorkMode,
        power_profile: str,
        launch_results: tuple[LaunchResult, ...],
    ) -> None:
        self._reload_modes(
            preferred_mode_id=mode.mode_id
        )

        self.update_active_mode(
            mode.mode_id,
            power_profile,
            f"{mode.name} WORKSPACE ACTIVATED",
        )

        if not launch_results:
            report = (
                "[b cyan]WORKSPACE ACTIVATION COMPLETE[/b cyan]\n\n"
                "No external applications were configured."
            )
        else:
            lines = [
                "[b cyan]APPLICATION LAUNCH REPORT[/b cyan]",
                "",
            ]

            for result in launch_results:
                color = self._launch_color(
                    result.status
                )

                lines.append(
                    f"[b {color}]"
                    f"{result.status:<16}"
                    f"[/b {color}] "
                    f"{escape(result.application)}"
                )
                lines.append(
                    f"                 "
                    f"{escape(result.detail)}"
                )

            report = "\n".join(lines)

        self.query_one(
            "#mode-launch-report",
            Static,
        ).update(report)

    def _show_single_launch(
        self,
        result: LaunchResult,
    ) -> None:
        color = self._launch_color(
            result.status
        )

        self.query_one(
            "#mode-launch-report",
            Static,
        ).update(
            "[b cyan]APPLICATION ACTION[/b cyan]\n\n"
            f"[b {color}]"
            f"{escape(result.status)}"
            f"[/b {color}]"
            f"    {escape(result.application)}\n"
            f"{escape(result.detail)}"
        )

        self._set_status(
            result.status,
            (
                f"{result.application} // "
                f"{result.detail}"
            ),
            color,
        )

    @staticmethod
    def _launch_color(
        status: str,
    ) -> str:
        return {
            "LAUNCHED": "cyan",
            "ALREADY RUNNING": "#70a9b8",
            "SKIPPED": "#70a9b8",
            "DISABLED": "yellow",
            "NOT INSTALLED": "yellow",
            "FAILED": "red",
        }.get(status, "white")

    def _handle_mutation(
        self,
        result: ModeMutationResult,
    ) -> None:
        color = {
            "SAVED": "cyan",
            "CREATED": "cyan",
            "DELETED": "yellow",
            "BLOCKED": "yellow",
            "NOT FOUND": "yellow",
            "FAILED": "red",
        }.get(result.status, "white")

        self._set_status(
            result.status,
            result.detail,
            color,
        )

        self._log_result(
            "MODE DATABASE",
            result.status,
            (
                f"{result.action}; "
                f"id={result.mode_id}; "
                f"{result.detail}"
            ),
        )

    def _set_status(
        self,
        state: str,
        detail: str,
        color: str,
    ) -> None:
        self.query_one(
            "#mode-status",
            Static,
        ).update(
            f"[b {color}]"
            f"● {escape(state)}"
            f"[/b {color}]"
            f"    //    {escape(detail)}"
        )

    def _log_result(
        self,
        category: str,
        status: str,
        detail: str,
    ) -> None:
        log_service = getattr(
            self.app,
            "log_service",
            None,
        )

        if log_service is None:
            return

        if status in {
            "SAVED",
            "CREATED",
            "LAUNCHED",
            "ALREADY RUNNING",
        }:
            log_service.info(
                category,
                detail,
            )

        elif status in {
            "DELETED",
            "BLOCKED",
            "NOT FOUND",
            "DISABLED",
            "NOT INSTALLED",
        }:
            log_service.warning(
                category,
                detail,
            )

        else:
            log_service.error(
                category,
                detail,
            )
