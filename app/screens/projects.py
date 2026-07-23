from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from services.data_service import SystemSnapshot


class ProjectsScreen(Vertical):
    """Project command and progress overview."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_rows: tuple[tuple[str, ...], ...] = ()

    def compose(self) -> ComposeResult:
        with Horizontal(id="projects-summary"):
            yield Static("--", id="project-total", classes="project-card")
            yield Static("--", id="project-active", classes="project-card")
            yield Static("--", id="project-progress", classes="project-card")
            yield Static("--", id="project-blocked", classes="project-card")

        yield Static(
            "PRIMARY OBJECTIVE // WAITING FOR DATABASE",
            id="project-focus",
        )

        yield Static(
            "PROJECT DATABASE",
            classes="projects-section-title",
        )

        yield DataTable(id="projects-table")

        yield Static(
            "Edit config/projects.json to update project data.",
            id="projects-hint",
        )

    def on_mount(self) -> None:
        table = self.query_one("#projects-table", DataTable)
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

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        sample = snapshot.projects

        self.query_one("#project-total", Static).update(
            "[b]TOTAL PROJECTS[/b]\n\n"
            f"[b]{len(sample.projects)}[/b]"
        )

        self.query_one("#project-active", Static).update(
            "[b]ACTIVE[/b]\n\n"
            f"[b cyan]{sample.active_count}[/b cyan]"
        )

        self.query_one("#project-progress", Static).update(
            "[b]AVERAGE PROGRESS[/b]\n\n"
            f"[b]{sample.average_progress:.1f}%[/b]"
        )

        blocked_color = "red" if sample.blocked_count else "cyan"

        self.query_one("#project-blocked", Static).update(
            "[b]BLOCKED[/b]\n\n"
            f"[b {blocked_color}]"
            f"{sample.blocked_count}"
            f"[/b {blocked_color}]"
        )

        if sample.error:
            self.query_one("#project-focus", Static).update(
                "[b red]● PROJECT DATABASE ERROR[/b red]\n"
                f"{sample.error}"
            )
        elif sample.focus_project is not None:
            project = sample.focus_project

            self.query_one("#project-focus", Static).update(
                "[b cyan]● PRIMARY OBJECTIVE[/b cyan]"
                f"    //    [b]{project.name}[/b]"
                f"    //    PRIORITY {project.priority}/5"
                f"    //    PROGRESS {project.progress}%\n"
                f"[b]NEXT ACTION[/b]  {project.next_action}\n"
                f"{project.description}"
            )
        else:
            self.query_one("#project-focus", Static).update(
                "[b]NO PROJECTS REGISTERED[/b]"
            )

        rows = tuple(
            (
                str(project.priority),
                project.name,
                project.category,
                project.status,
                self._progress_bar(project.progress),
                ", ".join(project.tech) or "—",
                project.next_action,
            )
            for project in sorted(
                sample.projects,
                key=lambda project: (
                    -project.priority,
                    project.name.lower(),
                ),
            )
        )

        if rows == self._last_rows:
            return

        table = self.query_one("#projects-table", DataTable)
        table.clear()

        if rows:
            table.add_rows(rows)
        else:
            table.add_row(
                "—",
                "NO PROJECTS REGISTERED",
                "—",
                "—",
                "—",
                "—",
                "—",
            )

        self._last_rows = rows

    @staticmethod
    def _progress_bar(progress: int) -> str:
        width = 12
        filled = round(progress / 100 * width)
        empty = width - filled

        return (
            f"{'█' * filled}"
            f"{'░' * empty}"
            f" {progress:3d}%"
        )
