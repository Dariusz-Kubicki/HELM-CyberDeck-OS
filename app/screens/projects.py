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

from modules.projects import Project
from services.data_service import SystemSnapshot
from services.project_action_service import (
    ProjectActionResult,
    ProjectActionService,
)
from services.project_service import (
    ProjectMutationResult,
    ProjectService,
)


class ProjectsScreen(Vertical):
    """Editable HELM project mission control."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.project_service = ProjectService()
        self.action_service = ProjectActionService()

        self.projects: tuple[Project, ...] = ()
        self.active_projects: tuple[Project, ...] = ()
        self.completed_projects: tuple[Project, ...] = ()

        self.selected_project_id: str | None = None
        self.pending_selected_project_id: str | None = None

        self.editing_project_id: str | None = None
        self.creating_project = False

        self.editor_status = "CONCEPT"
        self.editor_priority = 1
        self.editor_progress = 0

        self.pending_delete_project_id: str | None = None

        self._last_active_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

        self._last_completed_rows: tuple[
            tuple[str, ...],
            ...,
        ] = ()

    def compose(self) -> ComposeResult:
        with Horizontal(id="projects-summary"):
            yield Static(
                "--",
                id="project-total",
                classes="project-card",
            )
            yield Static(
                "--",
                id="project-active",
                classes="project-card",
            )
            yield Static(
                "--",
                id="project-progress",
                classes="project-card",
            )
            yield Static(
                "--",
                id="project-blocked",
                classes="project-card",
            )

        yield Static(
            "PRIMARY OBJECTIVE // WAITING FOR DATABASE",
            id="project-focus",
        )

        yield Static(
            "[b cyan]ACTIVE / PLANNED PROJECTS[/b cyan]"
            "    //    CURRENT MISSION QUEUE",
            id="projects-active-title",
            classes="projects-section-title",
        )

        yield DataTable(id="projects-active-table")

        yield Static(
            "[b green]COMPLETED / STABLE PROJECTS[/b green]"
            "    //    FINISHED OR READY FOR EXPANSION",
            id="projects-completed-title",
            classes="projects-section-title",
        )

        yield DataTable(id="projects-completed-table")

        with Horizontal(id="project-quick-actions"):
            yield Button(
                "EDIT SELECTED",
                id="project-edit",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "NEW PROJECT",
                id="project-new",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "STATUS ◀",
                id="project-status-prev-quick",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "STATUS ▶",
                id="project-status-next-quick",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "PROGRESS -5%",
                id="project-progress-minus-quick",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "PROGRESS +5%",
                id="project-progress-plus-quick",
                classes="project-control-button",
                flat=True,
            )

        with Horizontal(id="project-workspace-actions"):
            yield Button(
                "OPEN FOLDER",
                id="project-open-folder",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "OPEN TERMINAL",
                id="project-open-terminal",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "OPEN EDITOR",
                id="project-open-editor",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "OPEN GITHUB",
                id="project-open-github",
                classes="project-control-button",
                flat=True,
            )
            yield Button(
                "DELETE PROJECT",
                id="project-delete",
                classes="project-delete-button",
            )

        yield Static(
            "[b cyan]PROJECT EDITOR[/b cyan]"
            "    //    SELECT EDIT OR CREATE A NEW PROJECT",
            id="project-editor-title",
        )

        with Horizontal(id="project-editor-grid"):
            with Vertical(classes="project-editor-column"):
                yield Static(
                    "PROJECT NAME",
                    classes="project-field-label",
                )
                yield Input(
                    placeholder="Project name",
                    id="project-name-input",
                    disabled=True,
                )

                yield Static(
                    "CATEGORY",
                    classes="project-field-label",
                )
                yield Input(
                    placeholder="SOFTWARE / EMBEDDED / ROBOTICS",
                    id="project-category-input",
                    disabled=True,
                )

                yield Static(
                    "TECH STACK",
                    classes="project-field-label",
                )
                yield Input(
                    placeholder="Python, Textual, Arch Linux",
                    id="project-tech-input",
                    disabled=True,
                )

            with Vertical(classes="project-editor-column"):
                yield Static(
                    "PROJECT DIRECTORY",
                    classes="project-field-label",
                )
                yield Input(
                    placeholder="~/Projects/project-name",
                    id="project-path-input",
                    disabled=True,
                )

                yield Static(
                    "NEXT ACTION",
                    classes="project-field-label",
                )
                yield Input(
                    placeholder="What should be done next?",
                    id="project-next-action-input",
                    disabled=True,
                )

                yield Static(
                    "GITHUB REPOSITORY",
                    classes="project-field-label",
                )
                yield Input(
                    placeholder=(
                        "https://github.com/user/repository"
                    ),
                    id="project-github-input",
                    disabled=True,
                )

        yield Static(
            "DESCRIPTION",
            id="project-description-label",
            classes="project-field-label",
        )
        yield TextArea(
            "",
            placeholder=(
                "Describe the project, its purpose "
                "and important technical details..."
            ),
            id="project-description-input",
            disabled=True,
        )

        with Horizontal(id="project-editor-controls"):
            with Horizontal(classes="project-cycle-control"):
                yield Button(
                    "◀",
                    id="project-editor-status-prev",
                    classes="project-cycle-arrow",
                    disabled=True,
                )
                yield Static(
                    "STATUS: CONCEPT",
                    id="project-editor-status",
                    classes="project-cycle-value",
                )
                yield Button(
                    "▶",
                    id="project-editor-status-next",
                    classes="project-cycle-arrow",
                    disabled=True,
                )

            with Horizontal(classes="project-cycle-control"):
                yield Button(
                    "◀",
                    id="project-editor-priority-prev",
                    classes="project-cycle-arrow",
                    disabled=True,
                )
                yield Static(
                    "PRIORITY: 1/5",
                    id="project-editor-priority",
                    classes="project-cycle-value",
                )
                yield Button(
                    "▶",
                    id="project-editor-priority-next",
                    classes="project-cycle-arrow",
                    disabled=True,
                )

            with Horizontal(classes="project-cycle-control"):
                yield Button(
                    "-5",
                    id="project-editor-progress-prev",
                    classes="project-cycle-arrow",
                    disabled=True,
                )
                yield Static(
                    "PROGRESS: 0%",
                    id="project-editor-progress",
                    classes="project-cycle-value",
                )
                yield Button(
                    "+5",
                    id="project-editor-progress-next",
                    classes="project-cycle-arrow",
                    disabled=True,
                )

        with Horizontal(id="project-editor-actions"):
            yield Button(
                "SAVE CHANGES",
                id="project-save",
                variant="primary",
                disabled=True,
                flat=True,
            )
            yield Button(
                "CANCEL",
                id="project-cancel",
                disabled=True,
            )

        yield Static(
            "[b #6a8790]● PROJECT EDITOR STANDBY[/b #6a8790]"
            "    //    SELECT A PROJECT",
            id="project-action-status",
        )

    def on_mount(self) -> None:
        for table_id in (
            "#projects-active-table",
            "#projects-completed-table",
        ):
            table = self.query_one(
                table_id,
                DataTable,
            )

            table.cursor_type = "row"
            table.zebra_stripes = True

            table.add_columns(
                "PRI",
                "PROJECT",
                "CATEGORY",
                "STATUS",
                "PROGRESS",
                "TECH STACK",
                "NEXT ACTION",
            )

        self._set_editor_enabled(False)

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        sample = snapshot.projects

        self.query_one(
            "#project-total",
            Static,
        ).update(
            "[b]TOTAL PROJECTS[/b]\n\n"
            f"[b]{len(sample.projects)}[/b]"
        )

        self.query_one(
            "#project-active",
            Static,
        ).update(
            "[b]ACTIVE[/b]\n\n"
            f"[b cyan]{sample.active_count}[/b cyan]"
        )

        self.query_one(
            "#project-progress",
            Static,
        ).update(
            "[b]AVERAGE PROGRESS[/b]\n\n"
            f"[b]{sample.average_progress:.1f}%[/b]"
        )

        blocked_color = (
            "red"
            if sample.blocked_count
            else "cyan"
        )

        self.query_one(
            "#project-blocked",
            Static,
        ).update(
            "[b]BLOCKED[/b]\n\n"
            f"[b {blocked_color}]"
            f"{sample.blocked_count}"
            f"[/b {blocked_color}]"
        )

        self._update_focus(sample)

        archived_statuses = {
            "STABLE",
            "DONE",
            "COMPLETED",
        }

        self.active_projects = tuple(
            sorted(
                (
                    project
                    for project in sample.projects
                    if project.status
                    not in archived_statuses
                ),
                key=lambda project: (
                    -project.priority,
                    project.name.lower(),
                ),
            )
        )

        self.completed_projects = tuple(
            sorted(
                (
                    project
                    for project in sample.projects
                    if project.status
                    in archived_statuses
                ),
                key=lambda project: (
                    project.status != "STABLE",
                    project.name.lower(),
                ),
            )
        )

        self.projects = (
            self.active_projects
            + self.completed_projects
        )

        project_ids = {
            project.project_id
            for project in self.projects
        }

        if (
            self.pending_selected_project_id
            in project_ids
        ):
            self.selected_project_id = (
                self.pending_selected_project_id
            )
            self.pending_selected_project_id = None

        elif self.selected_project_id not in project_ids:
            self.selected_project_id = (
                self.projects[0].project_id
                if self.projects
                else None
            )

        active_rows = self._project_rows(
            self.active_projects
        )

        completed_rows = self._project_rows(
            self.completed_projects
        )

        if active_rows != self._last_active_rows:
            self._replace_project_rows(
                "#projects-active-table",
                active_rows,
                "NO ACTIVE OR PLANNED PROJECTS",
            )
            self._last_active_rows = active_rows

        if completed_rows != self._last_completed_rows:
            self._replace_project_rows(
                "#projects-completed-table",
                completed_rows,
                "NO COMPLETED OR STABLE PROJECTS",
            )
            self._last_completed_rows = completed_rows

        self.query_one(
            "#projects-active-title",
            Static,
        ).update(
            "[b cyan]ACTIVE / PLANNED PROJECTS[/b cyan]"
            f"    //    TOTAL {len(self.active_projects)}"
            "    //    CURRENT MISSION QUEUE"
        )

        stable_count = sum(
            project.status == "STABLE"
            for project in self.completed_projects
        )

        done_count = sum(
            project.status in {
                "DONE",
                "COMPLETED",
            }
            for project in self.completed_projects
        )

        self.query_one(
            "#projects-completed-title",
            Static,
        ).update(
            "[b green]COMPLETED / STABLE PROJECTS[/b green]"
            f"    //    STABLE {stable_count}"
            f"    //    DONE {done_count}"
        )

        self._restore_selected_row()

        if not self._editor_active:
            self._load_selected_project()

    def _update_focus(self, sample) -> None:
        panel = self.query_one(
            "#project-focus",
            Static,
        )

        if sample.error:
            panel.update(
                "[b red]● PROJECT DATABASE ERROR[/b red]\n"
                f"{escape(sample.error)}"
            )
            return

        project = sample.focus_project

        if project is None:
            panel.update(
                "[b]NO PROJECTS REGISTERED[/b]"
            )
            return

        status_color = self._status_color(
            project.status
        )

        panel.update(
            "[b cyan]● PRIMARY OBJECTIVE[/b cyan]"
            f"    //    [b]{escape(project.name)}[/b]"
            f"    //    "
            f"[b {status_color}]"
            f"{escape(project.status)}"
            f"[/b {status_color}]"
            f"    //    PRIORITY {project.priority}/5"
            f"    //    PROGRESS {project.progress}%\n"
            f"[b]NEXT ACTION[/b]  "
            f"{escape(project.next_action)}\n"
            f"{escape(project.description)}"
        )

    @staticmethod
    def _project_rows(
        projects: tuple[Project, ...],
    ) -> tuple[tuple[str, ...], ...]:
        return tuple(
            (
                str(project.priority),
                project.name,
                project.category,
                project.status,
                ProjectsScreen._progress_bar(
                    project.progress
                ),
                ", ".join(project.tech) or "—",
                project.next_action,
            )
            for project in projects
        )

    def _replace_project_rows(
        self,
        table_id: str,
        rows: tuple[tuple[str, ...], ...],
        empty_message: str,
    ) -> None:
        table = self.query_one(
            table_id,
            DataTable,
        )

        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                empty_message,
                "—",
                "—",
                "—",
                "—",
                "—",
            )

    def _restore_selected_row(self) -> None:
        if self.selected_project_id is None:
            return

        groups = (
            (
                "#projects-active-table",
                self.active_projects,
            ),
            (
                "#projects-completed-table",
                self.completed_projects,
            ),
        )

        for table_id, projects in groups:
            for index, project in enumerate(projects):
                if (
                    project.project_id
                    != self.selected_project_id
                ):
                    continue

                self.query_one(
                    table_id,
                    DataTable,
                ).move_cursor(
                    row=index,
                    column=0,
                    scroll=False,
                )
                return

    def on_data_table_row_highlighted(
        self,
        event: DataTable.RowHighlighted,
    ) -> None:
        if self._editor_active:
            return

        if event.control.id == "projects-active-table":
            source = self.active_projects

        elif event.control.id == "projects-completed-table":
            source = self.completed_projects

        else:
            return

        row = event.cursor_row

        if not 0 <= row < len(source):
            return

        self.selected_project_id = (
            source[row].project_id
        )

        self._reset_delete_confirmation()
        self._load_selected_project()

    @property
    def _editor_active(self) -> bool:
        return (
            self.editing_project_id is not None
            or self.creating_project
        )

    def _selected_project(self) -> Project | None:
        if self.selected_project_id is None:
            return None

        return next(
            (
                project
                for project in self.projects
                if (
                    project.project_id
                    == self.selected_project_id
                )
            ),
            None,
        )

    def _load_selected_project(self) -> None:
        project = self._selected_project()

        if project is None:
            self._clear_editor()
            return

        self._load_project_into_editor(project)

    def _load_project_into_editor(
        self,
        project: Project,
    ) -> None:
        self.query_one(
            "#project-name-input",
            Input,
        ).value = project.name

        self.query_one(
            "#project-category-input",
            Input,
        ).value = project.category

        self.query_one(
            "#project-tech-input",
            Input,
        ).value = ", ".join(project.tech)

        self.query_one(
            "#project-path-input",
            Input,
        ).value = project.path

        self.query_one(
            "#project-github-input",
            Input,
        ).value = project.github_url

        self.query_one(
            "#project-next-action-input",
            Input,
        ).value = project.next_action

        self.query_one(
            "#project-description-input",
            TextArea,
        ).text = project.description

        self.editor_status = project.status
        self.editor_priority = project.priority
        self.editor_progress = project.progress

        self._update_editor_control_labels()

        self.query_one(
            "#project-editor-title",
            Static,
        ).update(
            "[b cyan]SELECTED PROJECT[/b cyan]"
            f"    //    {escape(project.name)}"
            f"    //    ID {escape(project.project_id)}"
        )

    def _clear_editor(self) -> None:
        for input_id in (
            "#project-name-input",
            "#project-category-input",
            "#project-tech-input",
            "#project-path-input",
            "#project-github-input",
            "#project-next-action-input",
        ):
            self.query_one(
                input_id,
                Input,
            ).value = ""

        self.query_one(
            "#project-description-input",
            TextArea,
        ).text = ""

        self.editor_status = "CONCEPT"
        self.editor_priority = 1
        self.editor_progress = 0
        self._update_editor_control_labels()

    def _begin_edit(self) -> None:
        project = self._selected_project()

        if project is None:
            self._set_status(
                "NO PROJECT SELECTED",
                "Select a project in the table.",
                "yellow",
            )
            return

        self.editing_project_id = project.project_id
        self.creating_project = False

        self._load_project_into_editor(project)
        self._set_editor_enabled(True)

        self.query_one(
            "#project-editor-title",
            Static,
        ).update(
            "[b cyan]EDITING PROJECT[/b cyan]"
            f"    //    {escape(project.name)}"
        )

        self._set_status(
            "EDIT MODE ACTIVE",
            "Change fields and press SAVE CHANGES.",
            "cyan",
        )

    def _begin_new_project(self) -> None:
        self.editing_project_id = None
        self.creating_project = True

        self._clear_editor()

        self.query_one(
            "#project-name-input",
            Input,
        ).value = "New Project"

        self.query_one(
            "#project-category-input",
            Input,
        ).value = "GENERAL"

        self.query_one(
            "#project-next-action-input",
            Input,
        ).value = "Define first action"

        self._set_editor_enabled(True)

        self.query_one(
            "#project-editor-title",
            Static,
        ).update(
            "[b cyan]CREATING NEW PROJECT[/b cyan]"
            "    //    ENTER PROJECT DATA"
        )

        self.query_one(
            "#project-name-input",
            Input,
        ).focus()

        self._set_status(
            "NEW PROJECT",
            "Complete the form and save it.",
            "cyan",
        )

    def _save_editor(self) -> None:
        name = self.query_one(
            "#project-name-input",
            Input,
        ).value.strip()

        if not name:
            self._set_status(
                "VALIDATION ERROR",
                "Project name cannot be empty.",
                "red",
            )
            return

        fields = {
            "name": name,
            "category": self.query_one(
                "#project-category-input",
                Input,
            ).value.strip(),
            "tech": self.query_one(
                "#project-tech-input",
                Input,
            ).value,
            "path": self.query_one(
                "#project-path-input",
                Input,
            ).value.strip(),
            "github_url": self.query_one(
                "#project-github-input",
                Input,
            ).value.strip(),
            "next_action": self.query_one(
                "#project-next-action-input",
                Input,
            ).value.strip(),
            "description": self.query_one(
                "#project-description-input",
                TextArea,
            ).text.strip(),
            "status": self.editor_status,
            "priority": self.editor_priority,
            "progress": self.editor_progress,
        }

        if self.creating_project:
            result = self.project_service.create_project(
                fields
            )

        elif self.editing_project_id is not None:
            result = self.project_service.update_project(
                self.editing_project_id,
                fields,
            )

        else:
            return

        if result.status in {"SAVED", "CREATED"}:
            self.pending_selected_project_id = (
                result.project_id
            )

            self.editing_project_id = None
            self.creating_project = False
            self._set_editor_enabled(False)

        self._handle_mutation(result)

    def _cancel_editor(self) -> None:
        self.editing_project_id = None
        self.creating_project = False

        self._set_editor_enabled(False)
        self._load_selected_project()

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
            "#project-name-input",
            "#project-category-input",
            "#project-tech-input",
            "#project-path-input",
            "#project-github-input",
            "#project-next-action-input",
        ):
            self.query_one(
                input_id,
                Input,
            ).disabled = not enabled

        self.query_one(
            "#project-description-input",
            TextArea,
        ).disabled = not enabled

        for button_id in (
            "#project-editor-status-prev",
            "#project-editor-status-next",
            "#project-editor-priority-prev",
            "#project-editor-priority-next",
            "#project-editor-progress-prev",
            "#project-editor-progress-next",
            "#project-save",
            "#project-cancel",
        ):
            self.query_one(
                button_id,
                Button,
            ).disabled = not enabled

        for button_id in (
            "#project-edit",
            "#project-new",
            "#project-status-prev-quick",
            "#project-status-next-quick",
            "#project-progress-minus-quick",
            "#project-progress-plus-quick",
            "#project-delete",
        ):
            self.query_one(
                button_id,
                Button,
            ).disabled = enabled

        for table_id in (
            "#projects-active-table",
            "#projects-completed-table",
        ):
            self.query_one(
                table_id,
                DataTable,
            ).disabled = enabled

    def on_button_pressed(
        self,
        event: Button.Pressed,
    ) -> None:
        button_id = event.button.id

        if button_id is None:
            return

        if button_id != "project-delete":
            self._reset_delete_confirmation()

        actions = {
            "project-edit": self._begin_edit,
            "project-new": self._begin_new_project,
            "project-save": self._save_editor,
            "project-cancel": self._cancel_editor,
            "project-status-prev-quick":
                lambda: self._quick_status(-1),
            "project-status-next-quick":
                lambda: self._quick_status(1),
            "project-progress-minus-quick":
                lambda: self._quick_progress(-5),
            "project-progress-plus-quick":
                lambda: self._quick_progress(5),
            "project-delete": self._delete_selected,
            "project-open-folder":
                lambda: self._launch_action("folder"),
            "project-open-terminal":
                lambda: self._launch_action("terminal"),
            "project-open-editor":
                lambda: self._launch_action("editor"),
            "project-open-github":
                lambda: self._launch_action("github"),
            "project-editor-status-prev":
                lambda: self._cycle_editor_status(-1),
            "project-editor-status-next":
                lambda: self._cycle_editor_status(1),
            "project-editor-priority-prev":
                lambda: self._cycle_editor_priority(-1),
            "project-editor-priority-next":
                lambda: self._cycle_editor_priority(1),
            "project-editor-progress-prev":
                lambda: self._adjust_editor_progress(-5),
            "project-editor-progress-next":
                lambda: self._adjust_editor_progress(5),
        }

        action = actions.get(button_id)

        if action is None:
            return

        action()
        event.stop()

    def _quick_status(
        self,
        direction: int,
    ) -> None:
        project = self._selected_project()

        if project is None:
            self._set_status(
                "NO PROJECT SELECTED",
                "Select a project first.",
                "yellow",
            )
            return

        result = self.project_service.cycle_status(
            project.project_id,
            direction,
        )

        self.pending_selected_project_id = (
            project.project_id
        )
        self._handle_mutation(result)

    def _quick_progress(
        self,
        delta: int,
    ) -> None:
        project = self._selected_project()

        if project is None:
            self._set_status(
                "NO PROJECT SELECTED",
                "Select a project first.",
                "yellow",
            )
            return

        result = self.project_service.adjust_progress(
            project.project_id,
            delta,
        )

        self.pending_selected_project_id = (
            project.project_id
        )
        self._handle_mutation(result)

    def _cycle_editor_status(
        self,
        direction: int,
    ) -> None:
        statuses = self.project_service.STATUS_ORDER

        try:
            index = statuses.index(
                self.editor_status
            )
        except ValueError:
            index = 0

        self.editor_status = statuses[
            (index + direction) % len(statuses)
        ]

        self._update_editor_control_labels()

    def _cycle_editor_priority(
        self,
        direction: int,
    ) -> None:
        self.editor_priority = (
            (self.editor_priority - 1 + direction)
            % 5
        ) + 1

        self._update_editor_control_labels()

    def _adjust_editor_progress(
        self,
        delta: int,
    ) -> None:
        self.editor_progress = max(
            0,
            min(
                self.editor_progress + delta,
                100,
            ),
        )

        self._update_editor_control_labels()

    def _update_editor_control_labels(self) -> None:
        self.query_one(
            "#project-editor-status",
            Static,
        ).update(
            f"STATUS: {self.editor_status}"
        )

        self.query_one(
            "#project-editor-priority",
            Static,
        ).update(
            f"PRIORITY: {self.editor_priority}/5"
        )

        self.query_one(
            "#project-editor-progress",
            Static,
        ).update(
            f"PROGRESS: {self.editor_progress}%"
        )

    def _delete_selected(self) -> None:
        project = self._selected_project()

        if project is None:
            self._set_status(
                "NO PROJECT SELECTED",
                "Select a project first.",
                "yellow",
            )
            return

        delete_button = self.query_one(
            "#project-delete",
            Button,
        )

        if (
            self.pending_delete_project_id
            != project.project_id
        ):
            self.pending_delete_project_id = (
                project.project_id
            )

            delete_button.label = "CONFIRM DELETE"

            self._set_status(
                "DELETE CONFIRMATION",
                (
                    f"Press CONFIRM DELETE to remove "
                    f"{project.name}."
                ),
                "yellow",
            )
            return

        result = self.project_service.delete_project(
            project.project_id
        )

        self.pending_delete_project_id = None
        delete_button.label = "DELETE PROJECT"

        self.selected_project_id = None
        self._handle_mutation(result)

    def _reset_delete_confirmation(self) -> None:
        if self.pending_delete_project_id is None:
            return

        self.pending_delete_project_id = None

        self.query_one(
            "#project-delete",
            Button,
        ).label = "DELETE PROJECT"

    def _launch_action(
        self,
        action_id: str,
    ) -> None:
        project = self._selected_project()

        if project is None:
            self._set_status(
                "NO PROJECT SELECTED",
                "Select a project first.",
                "yellow",
            )
            return

        result = self.action_service.launch(
            action_id,
            project.path,
            github_url=project.github_url,
        )

        self._handle_action(result)

    def _handle_mutation(
        self,
        result: ProjectMutationResult,
    ) -> None:
        color = {
            "SAVED": "cyan",
            "CREATED": "cyan",
            "DELETED": "yellow",
            "NOT FOUND": "yellow",
            "FAILED": "red",
        }.get(result.status, "white")

        self._set_status(
            result.status,
            result.detail,
            color,
        )

        self._log_result(
            category="PROJECT DATABASE",
            status=result.status,
            detail=(
                f"{result.action}; "
                f"id={result.project_id}; "
                f"{result.detail}"
            ),
        )

        if result.status in {
            "SAVED",
            "CREATED",
            "DELETED",
        }:
            self._request_refresh()

    def _handle_action(
        self,
        result: ProjectActionResult,
    ) -> None:
        color = {
            "LAUNCHED": "cyan",
            "UNAVAILABLE": "yellow",
            "FAILED": "red",
        }.get(result.status, "white")

        self._set_status(
            result.status,
            f"{result.title} // {result.detail}",
            color,
        )

        self._log_result(
            category="PROJECT ACTION",
            status=result.status,
            detail=(
                f"{result.title}; "
                f"{result.detail}"
            ),
        )

    def _request_refresh(self) -> None:
        refresh = getattr(
            self.app,
            "refresh_snapshot",
            None,
        )

        if not callable(refresh):
            return

        self.set_timer(
            0.35,
            refresh,
        )

    def _set_status(
        self,
        state: str,
        detail: str,
        color: str,
    ) -> None:
        self.query_one(
            "#project-action-status",
            Static,
        ).update(
            f"[b {color}]"
            f"● {escape(state)}"
            f"[/b {color}]"
            f"    //    {escape(detail)}"
        )

    def _log_result(
        self,
        *,
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
        }:
            log_service.info(
                category,
                detail,
            )

        elif status in {
            "DELETED",
            "UNAVAILABLE",
            "NOT FOUND",
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

    @staticmethod
    def _status_color(status: str) -> str:
        return {
            "ACTIVE": "cyan",
            "BUILDING": "cyan",
            "TESTING": "cyan",
            "STABLE": "green",
            "DONE": "green",
            "COMPLETED": "green",
            "BLOCKED": "red",
            "PAUSED": "yellow",
            "PLANNING": "#70a9b8",
            "CONCEPT": "#6a8790",
        }.get(status, "white")

    @staticmethod
    def _progress_bar(progress: int) -> str:
        width = 12
        filled = round(
            progress / 100 * width
        )

        return (
            f"{'█' * filled}"
            f"{'░' * (width - filled)}"
            f" {progress:3d}%"
        )
