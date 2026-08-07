from functools import partial
from rich.markup import escape
from typing import Iterable
from textual import work
from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.worker import Worker, get_current_worker
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Static,
)

from app.screens.ai import AIScreen
from app.screens.boot import BootScreen
from app.screens.devices import DevicesScreen
from app.screens.logs import LogsScreen
from app.screens.modes import ModesScreen
from app.screens.network import NetworkScreen
from app.screens.projects import ProjectsScreen
from app.screens.settings import SettingsScreen
from app.screens.storage import StorageScreen
from app.screens.system import SystemScreen
from app.sidebar import Sidebar
from app.signature_rail import SignatureRail
from app.system_actions import SystemActions
from services.alert_service import AlertService, SystemAlert
from services.data_service import (
    DataService,
    SystemSnapshot,
    TelemetryIssue,
    TelemetryResult,
)
from services.health_service import HealthReport, HealthService
from services.log_service import LogService
from services.mode_service import ModeService
from services.mobile_power_policy import MobilePowerPolicyService
from services.settings_service import HelmSettings, SettingsService
from services.workspace_service import WorkspaceService
from services.system_action_service import SystemActionService


class Helm(App):
    CSS_PATH = "theme.tcss"
    TITLE = "HELM"
    SUB_TITLE = "CyberDeck Control Interface"

    COMMAND_PALETTE_BINDING = "ctrl+k"
    COMMAND_PALETTE_DISPLAY = "CTRL+K"

    NAVIGATION = {
        "system": (
            "system-screen",
            "HELM // SYSTEM OVERVIEW",
        ),
        "network": (
            "network-screen",
            "HELM // NETWORK TELEMETRY",
        ),
        "storage": (
            "storage-screen",
            "HELM // STORAGE ARRAY",
        ),
        "devices": (
            "devices-screen",
            "HELM // CONNECTED DEVICES",
        ),
        "modes": (
            "modes-screen",
            "HELM // OPERATION MODES",
        ),
        "projects": (
            "projects-screen",
            "HELM // PROJECT COMMAND",
        ),
        "logs": (
            "logs-screen",
            "HELM // EVENT LOG",
        ),
        "ai": (
            "ai-screen",
            "HELM // DIAGNOSTIC CORE",
        ),
        "settings": (
            "settings-screen",
            "HELM // SYSTEM CONFIGURATION",
        ),
    }

    SCREEN_CODES = {
        "system": "01",
        "network": "02",
        "storage": "03",
        "devices": "04",
        "modes": "05",
        "projects": "06",
        "logs": "07",
        "ai": "08",
        "settings": "09",
    }

    SCREEN_CONTEXT = {
        "system": "CORE TELEMETRY",
        "network": "NETWORK FABRIC",
        "storage": "DATA VAULT",
        "devices": "HARDWARE MATRIX",
        "modes": "WORKSPACE ENGINE",
        "projects": "MISSION CONTROL",
        "logs": "EVENT ARCHIVE",
        "ai": "LOCAL INTELLIGENCE",
        "settings": "SYSTEM CONTROL",
    }

    def __init__(self) -> None:
        super().__init__()

        self.data_service = DataService()
        self.log_service = LogService()
        self.settings_service = SettingsService()
        self.mode_service = ModeService()
        self.mobile_power_policy = MobilePowerPolicyService()
        self.workspace_service = WorkspaceService()
        self.system_action_service = SystemActionService()
        self.alert_service = AlertService()

        self.health_service = HealthService(
            settings_service=self.settings_service,
            mode_service=self.mode_service,
            log_service=self.log_service,
        )

        self.settings = self.settings_service.load()
        self.modes = self.mode_service.load_modes()
        self.active_mode_id = self.mode_service.load_active_mode()

        self._active_navigation_id = (
            self.settings.start_screen
            if self.settings.start_screen in self.NAVIGATION
            else "system"
        )

        self.refresh_timer: Timer | None = None
        self._active_system_alerts: dict[str, str] = {}

        self._telemetry_sequence = 0
        self._telemetry_last_applied = 0
        self._telemetry_in_flight = False
        self._telemetry_shutdown = False
        self._telemetry_skipped_cycles = 0
        self._telemetry_last_duration_ms = 0.0

        self._telemetry_worker: Worker[None] | None = None
        self._last_snapshot: SystemSnapshot | None = None

        self._telemetry_issue_state: dict[str, str] = {}

        self._telemetry_state = "STARTING"
        self._health_state = "STARTING"
        self._startup_health_requested = False

        self._health_worker: Worker[None] | None = None
        self._last_health_report: HealthReport | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar")

            with Vertical(id="content-area"):
                with Horizontal(id="screen-header"):
                    yield Static(
                        "[b #42e8ff]01[/b #42e8ff]"
                        " [#315965]//[/] "
                        "[b]HELM // SYSTEM OVERVIEW[/b]",
                        id="screen-title",
                    )

                    yield Static(
                        "[b #6feeff]CORE TELEMETRY[/b #6feeff]\n"
                        "[#456d78]MODE CUSTOM[/]",
                        id="screen-context",
                    )

                yield SignatureRail(
                    id="signature-rail",
                )

                with ContentSwitcher(
                    initial="system-screen",
                    id="screen-switcher",
                ):
                    yield SystemScreen(id="system-screen")
                    yield NetworkScreen(id="network-screen")
                    yield StorageScreen(id="storage-screen")
                    yield DevicesScreen(id="devices-screen")
                    yield ModesScreen(
                        self.modes,
                        self.active_mode_id,
                        id="modes-screen",
                    )
                    yield ProjectsScreen(id="projects-screen")
                    yield LogsScreen(id="logs-screen")
                    yield AIScreen(
                        self.settings,
                        id="ai-screen",
                    )
                    yield SettingsScreen(
                        self.settings,
                        id="settings-screen",
                    )

        yield Footer()

    def get_system_commands(
        self,
        screen: Screen,
    ) -> Iterable[SystemCommand]:
        """Expose HELM actions through the global command palette."""

        yield from super().get_system_commands(screen)

        for navigation_id, (_, title) in self.NAVIGATION.items():
            yield SystemCommand(
                f"Open {navigation_id.upper()}",
                title,
                partial(
                    self._open_screen,
                    navigation_id,
                ),
            )

        for mode in self.modes:
            yield SystemCommand(
                f"Activate {mode.name} workspace",
                mode.description,
                partial(
                    self._activate_workspace_from_palette,
                    mode.mode_id,
                ),
            )

        yield SystemCommand(
            "Run full CyberDeck diagnostic",
            "Open the AI core and analyze live system telemetry.",
            partial(
                self._run_ai_command,
                "diagnostic",
            ),
        )

        yield SystemCommand(
            "Show AI command help",
            "Open the diagnostic core command reference.",
            partial(
                self._run_ai_command,
                "help",
            ),
        )

        yield SystemCommand(
            "Run HELM health diagnostic",
            (
                "Check telemetry, configuration, tools, "
                "Ollama, Git and the previous session."
            ),
            self._run_health_check,
        )

        yield SystemCommand(
            "Show last HELM health report",
            "Open the most recent core health report.",
            self._show_last_health_report,
        )

        yield SystemCommand(
            "Export last HELM health report",
            "Save the current health report as Markdown.",
            self._export_last_health_report,
        )

    def on_mount(self) -> None:
        self.push_screen(BootScreen())

        self.log_service.info(
            "HELM",
            "CyberDeck control interface started",
        )

        active_mode = self.mode_service.get_mode(
            self.active_mode_id
        )

        if active_mode is not None:
            self.query_one(
                SystemScreen
            ).update_mode_context(
                active_mode.mode_id,
                active_mode.power_profile,
            )

            power_policy = self.mobile_power_policy.apply(
                self.mode_service,
                active_mode.mode_id,
                active_mode.power_profile,
            )

            self.query_one(ModesScreen).update_active_mode(
                active_mode.mode_id,
                power_policy.applied_profile,
                f"{active_mode.name} MODE RESTORED",
            )

            self.log_service.info(
                "POWER",
                (
                    f"{active_mode.name}: "
                    f"source={power_policy.power_source}; "
                    f"policy={power_policy.policy_profile}; "
                    f"resolved={power_policy.resolved_profile}; "
                    f"applied={power_policy.applied_profile}; "
                    f"status={power_policy.status}"
                ),
            )
        else:
            self.query_one(
                SystemScreen
            ).update_mode_context(
                "custom",
                "unchanged",
            )

            self.query_one(ModesScreen).update_active_mode(
                "custom",
                self.mode_service.get_current_power_profile(),
                "CUSTOM RUNTIME CONFIGURATION",
            )

        sidebar = self.query_one(
            Sidebar
        )

        if active_mode is not None:
            sidebar.update_mode(
                active_mode.name,
                active_mode.mode_id,
            )
        else:
            sidebar.update_mode(
                "CUSTOM RUNTIME",
                "custom",
            )

        self._open_screen(
            self.settings.start_screen,
            log_event=False,
        )

        self._prime_interface_labels()

        self.refresh_snapshot()
        self._restart_refresh_timer()

    def _prime_interface_labels(self) -> None:
        """Fill status surfaces before the first user action."""
        try:
            self.query_one(
                "#mode-status",
                Static,
            ).update(
                "[b #58f6d0]"
                "● WORKSPACE ENGINE ONLINE"
                "[/]    //    "
                "SELECT, EDIT OR ACTIVATE A PROFILE"
            )
        except Exception:
            pass

        try:
            section_titles = list(
                self.query(
                    ".modes-section-title"
                )
            )

            if section_titles:
                section_titles[0].update(
                    "[b #42e8ff]"
                    "WORKSPACE DATABASE"
                    "[/]    //    "
                    "AVAILABLE OPERATION PROFILES"
                )
        except Exception:
            pass

    def on_unmount(self) -> None:
        self._telemetry_shutdown = True

        if self.refresh_timer is not None:
            self.refresh_timer.stop()

        for worker in (
            self._telemetry_worker,
            self._health_worker,
        ):
            if (
                worker is not None
                and not worker.is_finished
            ):
                worker.cancel()

        self.log_service.info(
            "HELM",
            "CyberDeck control interface stopped",
        )

    def _restart_refresh_timer(self) -> None:
        if self.refresh_timer is not None:
            self.refresh_timer.stop()

        self.refresh_timer = self.set_interval(
            self.settings.telemetry_interval,
            self.refresh_snapshot,
        )

    def refresh_snapshot(self) -> None:
        """Request a telemetry cycle without blocking the UI."""
        if self._telemetry_shutdown:
            return

        if self._telemetry_in_flight:
            self._telemetry_skipped_cycles += 1
            self._update_telemetry_subtitle(
                "BUSY"
            )
            return

        self._telemetry_sequence += 1
        sequence = self._telemetry_sequence

        self._telemetry_in_flight = True

        self._telemetry_worker = (
            self._collect_snapshot_worker(
                sequence,
                self._last_snapshot,
            )
        )

    @work(
        name="telemetry-collector",
        group="telemetry",
        thread=True,
        exit_on_error=False,
    )
    def _collect_snapshot_worker(
        self,
        sequence: int,
        previous_snapshot: SystemSnapshot | None,
    ) -> None:
        worker = get_current_worker()

        if (
            worker.is_cancelled
            or self._telemetry_shutdown
        ):
            return

        result = self.data_service.collect_result(
            sequence=sequence,
            previous_snapshot=previous_snapshot,
        )

        if (
            worker.is_cancelled
            or self._telemetry_shutdown
        ):
            return

        try:
            self.call_from_thread(
                self._apply_telemetry_result,
                result,
            )
        except RuntimeError:
            # App is already shutting down.
            return

    def _apply_telemetry_result(
        self,
        result: TelemetryResult,
    ) -> None:
        if self._telemetry_shutdown:
            return

        ui_issues: list[TelemetryIssue] = []

        try:
            if (
                result.sequence
                <= self._telemetry_last_applied
            ):
                return

            self._telemetry_last_applied = (
                result.sequence
            )

            self._telemetry_last_duration_ms = (
                result.duration_ms
            )

            snapshot = result.snapshot

            if snapshot is not None:
                self._last_snapshot = snapshot

                try:
                    if (
                        self._active_navigation_id
                        == "system"
                    ):
                        system_alerts = self.query_one(
                            SystemScreen
                        ).update_snapshot(
                            snapshot
                        )
                    else:
                        system_alerts = (
                            self.alert_service.analyze(
                                snapshot
                            )
                        )

                    self._process_system_alerts(
                        system_alerts
                    )

                except Exception as error:
                    ui_issues.append(
                        self._make_ui_issue(
                            "UI SYSTEM",
                            error,
                        )
                    )

                if (
                    self._active_navigation_id
                    != "system"
                ):
                    try:
                        self._update_active_snapshot_screen(
                            snapshot
                        )

                    except Exception as error:
                        ui_issues.append(
                            self._make_ui_issue(
                                (
                                    "UI "
                                    + self._active_navigation_id.upper()
                                ),
                                error,
                            )
                        )

            all_issues = (
                *result.issues,
                *ui_issues,
            )

            self._synchronize_telemetry_issues(
                all_issues
            )

            if result.snapshot is None:
                engine_state = "FAILED"
            elif all_issues:
                engine_state = "DEGRADED"
            else:
                engine_state = "NOMINAL"

            self._update_telemetry_subtitle(
                engine_state
            )

            if not self._startup_health_requested:
                self._startup_health_requested = True

                self._request_health_check(
                    display=False,
                    export=True,
                )

        finally:
            self._telemetry_in_flight = False
            self._refresh_log_screen()

    def _synchronize_telemetry_issues(
        self,
        issues: tuple[TelemetryIssue, ...],
    ) -> None:
        current_state = {
            issue.source: issue.signature
            for issue in issues
        }

        for issue in issues:
            previous_signature = (
                self._telemetry_issue_state.get(
                    issue.source
                )
            )

            if (
                previous_signature
                == issue.signature
            ):
                continue

            message = (
                f"{issue.source}: "
                f"{issue.error_type}: "
                f"{issue.message}; "
                f"fallback="
                f"{'USED' if issue.fallback_used else 'UNAVAILABLE'}"
            )

            if issue.fallback_used:
                self.log_service.warning(
                    "TELEMETRY",
                    message,
                )
            else:
                self.log_service.error(
                    "TELEMETRY",
                    message,
                )

        recovered_sources = (
            set(self._telemetry_issue_state)
            - set(current_state)
        )

        for source in sorted(
            recovered_sources
        ):
            self.log_service.info(
                "TELEMETRY",
                (
                    f"{source}: telemetry "
                    "source recovered"
                ),
            )

        self._telemetry_issue_state = (
            current_state
        )

    def _update_active_snapshot_screen(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        screen_type = {
            "network": NetworkScreen,
            "storage": StorageScreen,
            "devices": DevicesScreen,
            "projects": ProjectsScreen,
            "ai": AIScreen,
        }.get(
            self._active_navigation_id
        )

        if screen_type is None:
            return

        self.query_one(
            screen_type
        ).update_snapshot(
            snapshot
        )

    def _refresh_active_screen_from_cache(
        self,
    ) -> None:
        if self._active_navigation_id == "logs":
            self._refresh_log_screen(
                force=True
            )
            return

        snapshot = self._last_snapshot

        if snapshot is None:
            return

        if self._active_navigation_id == "system":
            self.query_one(
                SystemScreen
            ).update_snapshot(
                snapshot
            )
            return

        self._update_active_snapshot_screen(
            snapshot
        )

    def _refresh_log_screen(
        self,
        *,
        force: bool = False,
    ) -> None:
        if (
            not force
            and self._active_navigation_id
            != "logs"
        ):
            return

        try:
            self.query_one(
                LogsScreen
            ).update_entries(
                self.log_service.tail(
                    limit=self.settings.log_rows,
                )
            )
        except Exception:
            # LOGS failure must not stop telemetry.
            pass

    def _update_telemetry_subtitle(
        self,
        state: str,
    ) -> None:
        self._telemetry_state = state
        self._refresh_core_subtitle()

    def _refresh_core_subtitle(self) -> None:
        self.sub_title = (
            f"HEALTH {self._health_state}"
            f"  //  TELEMETRY "
            f"{self._telemetry_state}"
            f"  //  "
            f"{self._telemetry_last_duration_ms:.0f} ms"
            f"  //  SKIPPED "
            f"{self._telemetry_skipped_cycles}"
        )

        try:
            self.query_one(
                Sidebar
            ).update_core_state(
                self._health_state,
                self._telemetry_state,
                self._telemetry_last_duration_ms,
                self._telemetry_skipped_cycles,
            )
        except Exception:
            pass

        try:
            self.query_one(
                SignatureRail
            ).update_state(
                self._health_state,
                self._telemetry_state,
                self._telemetry_last_duration_ms,
                self._telemetry_skipped_cycles,
                self.active_mode_id,
            )
        except Exception:
            pass

        try:
            self._apply_core_visual_state()
        except Exception:
            pass

    def _apply_core_visual_state(self) -> None:
        health = self._health_state.upper()
        telemetry = self._telemetry_state.upper()

        states = {
            health,
            telemetry,
        }

        critical_states = {
            "CRITICAL",
            "FAILED",
            "OFFLINE",
        }

        warning_states = {
            "DEGRADED",
            "WARNING",
            "SCANNING",
            "STARTING",
        }

        if states & critical_states:
            visual_state = "critical"
        elif states & warning_states:
            visual_state = "degraded"
        elif "BUSY" in states:
            visual_state = "processing"
        else:
            visual_state = "nominal"

        # Najważniejsza optymalizacja:
        # nie dotykaj klas CSS, dopóki stan się nie zmieni.
        if (
            getattr(
                self,
                "_core_visual_state",
                None,
            )
            == visual_state
        ):
            return

        layout = self.query_one(
            "#main-layout"
        )

        target_class = (
            f"core-{visual_state}"
        )

        # Chroni także przed stanem, w którym klasa
        # została już ustawiona przed zapisaniem cache.
        if layout.has_class(target_class):
            self._core_visual_state = visual_state
            return

        for class_name in (
            "core-nominal",
            "core-degraded",
            "core-processing",
            "core-critical",
        ):
            if layout.has_class(class_name):
                layout.remove_class(
                    class_name
                )

        layout.add_class(
            target_class
        )

        self._core_visual_state = visual_state


    @staticmethod
    def _make_ui_issue(
        source: str,
        error: Exception,
    ) -> TelemetryIssue:
        message = " ".join(
            str(error).split()
        )

        return TelemetryIssue(
            source=source,
            error_type=type(error).__name__,
            message=(
                message[:300]
                or "No error detail provided."
            ),
            fallback_used=True,
        )

    def _run_health_check(self) -> None:
        self._request_health_check(
            display=True,
            export=True,
        )

    def _show_last_health_report(self) -> None:
        if self._last_health_report is None:
            self._request_health_check(
                display=True,
                export=False,
            )
            return

        self._display_health_report(
            self._last_health_report,
            export_path=None,
        )

    def _export_last_health_report(self) -> None:
        report = self._last_health_report

        if report is None:
            self._request_health_check(
                display=True,
                export=True,
            )
            return

        try:
            export_path = (
                self.health_service
                .export_report(report)
            )

            self.log_service.info(
                "HEALTH",
                f"Health report exported: {export_path}",
            )

            self._open_screen(
                "ai",
                log_event=False,
            )

            self.query_one(
                AIScreen
            ).display_system_report(
                "HELM HEALTH EXPORT",
                f"Report exported to:\n{export_path}",
            )

        except OSError as error:
            self.log_service.error(
                "HEALTH",
                (
                    f"Export failed: "
                    f"{type(error).__name__}: {error}"
                ),
            )

    def _request_health_check(
        self,
        *,
        display: bool,
        export: bool,
    ) -> None:
        if self._telemetry_shutdown:
            return

        current_worker = self._health_worker

        if (
            current_worker is not None
            and not current_worker.is_finished
        ):
            current_worker.cancel()

        self._health_state = "SCANNING"
        self._refresh_core_subtitle()

        self._health_worker = (
            self._collect_health_worker(
                self.settings,
                self.active_mode_id,
                self._telemetry_state,
                self._telemetry_last_duration_ms,
                self._telemetry_skipped_cycles,
                display,
                export,
            )
        )

    @work(
        name="health-check",
        group="health",
        thread=True,
        exclusive=True,
        exit_on_error=False,
    )
    def _collect_health_worker(
        self,
        settings: HelmSettings,
        active_mode_id: str,
        telemetry_state: str,
        telemetry_duration_ms: float,
        telemetry_skipped_cycles: int,
        display: bool,
        export: bool,
    ) -> None:
        worker = get_current_worker()

        if (
            worker.is_cancelled
            or self._telemetry_shutdown
        ):
            return

        try:
            report = self.health_service.collect(
                settings=settings,
                active_mode_id=active_mode_id,
                telemetry_state=telemetry_state,
                telemetry_duration_ms=(
                    telemetry_duration_ms
                ),
                telemetry_skipped_cycles=(
                    telemetry_skipped_cycles
                ),
            )

            export_path: str | None = None

            if export:
                export_path = str(
                    self.health_service
                    .export_report(report)
                )

            if (
                worker.is_cancelled
                or self._telemetry_shutdown
            ):
                return

            self.call_from_thread(
                self._apply_health_report,
                report,
                display,
                export_path,
            )

        except Exception as error:
            if (
                worker.is_cancelled
                or self._telemetry_shutdown
            ):
                return

            try:
                self.call_from_thread(
                    self._apply_health_failure,
                    display,
                    (
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            except RuntimeError:
                return

    def _apply_health_report(
        self,
        report: HealthReport,
        display: bool,
        export_path: str | None,
    ) -> None:
        self._last_health_report = report
        self._health_state = report.state
        self._health_worker = None

        self._refresh_core_subtitle()
        self._log_health_report(report)

        if display:
            self._display_health_report(
                report,
                export_path=export_path,
            )

    def _apply_health_failure(
        self,
        display: bool,
        detail: str,
    ) -> None:
        self._health_state = "DEGRADED"
        self._health_worker = None

        self._refresh_core_subtitle()

        self.log_service.error(
            "HEALTH",
            f"Health check failed: {detail}",
        )

        if display:
            self._open_screen(
                "ai",
                log_event=False,
            )

            self.query_one(
                AIScreen
            ).display_system_report(
                "HELM HEALTH CHECK ERROR",
                detail,
            )

    def _display_health_report(
        self,
        report: HealthReport,
        *,
        export_path: str | None,
    ) -> None:
        content = report.to_text()

        if export_path:
            content += (
                "\n\nEXPORTED REPORT\n"
                f"{export_path}"
            )

        self._open_screen(
            "ai",
            log_event=False,
        )

        self.query_one(
            AIScreen
        ).display_system_report(
            "HELM CORE HEALTH REPORT",
            content,
        )

    def _log_health_report(
        self,
        report: HealthReport,
    ) -> None:
        summary = (
            f"state={report.state}; "
            f"checks={len(report.checks)}; "
            f"warnings={report.warning_count}; "
            f"critical={report.critical_count}; "
            f"duration={report.duration_ms:.1f}ms"
        )

        if report.state == "CRITICAL":
            self.log_service.critical(
                "HEALTH",
                summary,
            )
        elif report.state == "DEGRADED":
            self.log_service.warning(
                "HEALTH",
                summary,
            )
        else:
            self.log_service.info(
                "HEALTH",
                summary,
            )

        for check in report.problem_checks:
            message = (
                f"{check.code}: "
                f"{check.title}; "
                f"{check.detail}"
            )

            if check.status == "CRITICAL":
                self.log_service.critical(
                    "HEALTH",
                    message,
                )
            else:
                self.log_service.warning(
                    "HEALTH",
                    message,
                )

        self._refresh_log_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id is None:
            return

        system_actions = {
            "system-action-btop": "btop",
            "system-action-sensors": "sensors",
            "system-action-gpu": "gpu",
            "system-action-diagnostic": "diagnostic",
        }

        if button_id in system_actions:
            self._launch_system_action(
                system_actions[button_id]
            )
            event.stop()
            return

        if button_id.startswith("mode-select-"):
            mode_id = button_id.removeprefix("mode-select-")

            self.query_one(ModesScreen).select_mode(mode_id)
            event.stop()
            return

        if button_id == "mode-activate":
            self._activate_selected_mode()
            event.stop()
            return

        if button_id == "settings-save":
            self._save_settings()
            event.stop()
            return

        if button_id == "settings-backup":
            self._backup_settings()
            event.stop()
            return

        if button_id == "settings-export":
            self._export_settings()
            event.stop()
            return

        if button_id == "settings-restore":
            self._restore_settings_backup()
            event.stop()
            return

        if button_id == "settings-reset":
            self._reset_settings()
            event.stop()
            return

        if button_id in self.NAVIGATION:
            self._open_screen(button_id)

    def _launch_system_action(
        self,
        action_id: str,
    ) -> None:
        result = self.system_action_service.launch(
            action_id
        )

        self.query_one(
            SystemActions
        ).show_result(result)

        message = (
            f"{result.title}; "
            f"status={result.status}; "
            f"detail={result.detail}"
        )

        if result.status == "LAUNCHED":
            self.log_service.info(
                "SYSTEM ACTION",
                message,
            )
        elif result.status == "NOT INSTALLED":
            self.log_service.warning(
                "SYSTEM ACTION",
                message,
            )
        else:
            self.log_service.error(
                "SYSTEM ACTION",
                message,
            )

    def _process_system_alerts(
        self,
        alerts: tuple[SystemAlert, ...],
    ) -> None:
        current_alerts = {
            alert.code: alert
            for alert in alerts
        }

        previous_codes = set(
            self._active_system_alerts
        )
        current_codes = set(current_alerts)

        for code in sorted(
            current_codes - previous_codes
        ):
            alert = current_alerts[code]

            message = (
                f"{alert.title}: "
                f"{alert.value}; "
                f"{alert.message}"
            )

            if alert.severity == "CRITICAL":
                self.log_service.critical(
                    "SYSTEM ALERT",
                    message,
                )
            else:
                self.log_service.warning(
                    "SYSTEM ALERT",
                    message,
                )

        for code in sorted(
            previous_codes - current_codes
        ):
            self.log_service.info(
                "SYSTEM ALERT",
                f"Condition cleared: {code}",
            )

        self._active_system_alerts = {
            code: alert.severity
            for code, alert in current_alerts.items()
        }

    def _activate_workspace_from_palette(
        self,
        mode_id: str,
    ) -> None:
        """Select and activate a workspace from the command palette."""

        modes_screen = self.query_one(ModesScreen)
        modes_screen.select_mode(mode_id)

        self._activate_selected_mode()

    def _run_ai_command(self, command: str) -> None:
        """Open the AI screen and execute a diagnostic command."""

        self._open_screen(
            "ai",
            log_event=False,
        )

        self.query_one(AIScreen).execute_command(command)

        self.log_service.info(
            "COMMAND",
            f"Executed AI command: {command}",
        )

    def _activate_selected_mode(self) -> None:
        screen = self.query_one(ModesScreen)
        mode = self.mode_service.get_mode(
            screen.selected_mode_id
        )

        if mode is None:
            self.log_service.error(
                "WORKSPACE",
                "Selected workspace does not exist",
            )
            return

        settings = HelmSettings(
            telemetry_interval=mode.telemetry_interval,
            start_screen=mode.target_screen,
            navigation_logging=mode.navigation_logging,
            log_rows=self.settings.log_rows,
            ai_model=self.settings.ai_model,
            ai_context_window=(
                self.settings.ai_context_window
            ),
            ai_keep_alive=(
                self.settings.ai_keep_alive
            ),
        )

        try:
            self.settings_service.save(settings)
            self.mode_service.save_active_mode(mode.mode_id)

            self.settings = settings
            self.active_mode_id = mode.mode_id

            self.query_one(
                SystemScreen
            ).update_mode_context(
                mode.mode_id,
                mode.power_profile,
            )

            self.query_one(
                Sidebar
            ).update_mode(
                mode.name,
                mode.mode_id,
            )

            self.query_one(SettingsScreen).load_settings(settings)
            self._restart_refresh_timer()

            power_policy = self.mobile_power_policy.apply(
                self.mode_service,
                mode.mode_id,
                mode.power_profile,
            )

            launch_results = self.workspace_service.launch_mode(mode)

            screen.show_activation(
                mode,
                power_policy.applied_profile,
                launch_results,
            )

            for result in launch_results:
                self.log_service.info(
                    "WORKSPACE",
                    (
                        f"{mode.name}: {result.application}; "
                        f"status={result.status}; "
                        f"detail={result.detail}"
                    ),
                )

            self.log_service.info(
                "POWER",
                (
                    f"{mode.name}: "
                    f"source={power_policy.power_source}; "
                    f"policy={power_policy.policy_profile}; "
                    f"resolved={power_policy.resolved_profile}; "
                    f"applied={power_policy.applied_profile}; "
                    f"status={power_policy.status}; "
                    f"fallback={power_policy.fallback_reason or 'none'}"
                ),
            )

            self.log_service.info(
                "MODE",
                (
                    f"Activated {mode.name} workspace; "
                    f"telemetry={mode.telemetry_interval}s; "
                    f"target={mode.target_screen}; "
                    f"applications={len(launch_results)}"
                ),
            )

            self._open_screen(
                mode.target_screen,
                log_event=False,
            )

        except Exception as error:
            self.log_service.error(
                "WORKSPACE",
                f"{type(error).__name__}: {error}",
            )

            screen.update_active_mode(
                self.active_mode_id,
                self.mode_service.get_current_power_profile(),
                f"ACTIVATION ERROR: {error}",
            )

    def _open_screen(
        self,
        navigation_id: str,
        *,
        log_event: bool = True,
    ) -> None:
        if navigation_id not in self.NAVIGATION:
            navigation_id = "system"

        self._active_navigation_id = navigation_id

        screen_id, title = self.NAVIGATION[navigation_id]

        self.query_one(
            "#screen-switcher",
            ContentSwitcher,
        ).current = screen_id

        try:
            self._refresh_active_screen_from_cache()
        except Exception:
            # Cached refresh must never break navigation.
            pass

        screen_code = self.SCREEN_CODES.get(
            navigation_id,
            "00",
        )

        screen_context = self.SCREEN_CONTEXT.get(
            navigation_id,
            "SYSTEM MODULE",
        )

        self.query_one(
            "#screen-title",
            Static,
        ).update(
            f"[b #42e8ff]{screen_code}[/b #42e8ff]"
            " [#315965]//[/] "
            f"[b]{escape(title)}[/b]"
        )

        self.query_one(
            "#screen-context",
            Static,
        ).update(
            f"[b #6feeff]"
            f"{escape(screen_context)}"
            f"[/b #6feeff]\n"
            f"[#456d78]MODE "
            f"{escape(self.active_mode_id.upper())}"
            f"[/]"
        )

        try:
            self.query_one(
                SignatureRail
            ).update_module(
                screen_code,
                title,
                screen_context,
            )
        except Exception:
            pass

        try:
            content_area = self.query_one(
                "#content-area"
            )

            for module_name in self.NAVIGATION:
                content_area.remove_class(
                    f"module-{module_name}"
                )

            content_area.add_class(
                f"module-{navigation_id}"
            )

        except Exception:
            pass

        for button_name in self.NAVIGATION:
            self.query_one(
                f"#{button_name}",
                Button,
            ).remove_class("selected")

        active_button = self.query_one(
            f"#{navigation_id}",
            Button,
        )
        active_button.add_class("selected")
        active_button.focus()

        if log_event and self.settings.navigation_logging:
            self.log_service.info(
                "NAVIGATION",
                f"Opened {navigation_id.upper()} screen",
            )

    def _set_custom_mode(self) -> None:
        self.active_mode_id = "custom"
        self.mode_service.save_active_mode("custom")

        self.query_one(
            SystemScreen
        ).update_mode_context(
            "custom",
            "unchanged",
        )

        self.query_one(ModesScreen).update_active_mode(
            "custom",
            self.mode_service.get_current_power_profile(),
            "CUSTOM SETTINGS ACTIVE",
        )

        self.query_one(
            Sidebar
        ).update_mode(
            "CUSTOM RUNTIME",
            "custom",
        )

    def _apply_settings_runtime(
        self,
        settings: HelmSettings,
        *,
        mark_custom: bool = True,
    ) -> None:
        self.settings = settings

        settings_screen = self.query_one(
            SettingsScreen
        )

        settings_screen.load_settings(
            settings
        )

        self.query_one(
            AIScreen
        ).apply_settings(
            settings
        )

        self._restart_refresh_timer()

        if mark_custom:
            self._set_custom_mode()

        settings_screen.refresh_diagnostics()

    def _save_settings(self) -> None:
        screen = self.query_one(
            SettingsScreen
        )

        screen.clear_confirmation()

        try:
            settings = (
                self.settings_service.validate(
                    screen.read_settings()
                )
            )

            # Kopia zawiera ustawienia sprzed zapisu.
            self.settings_service.create_backup()
            self.settings_service.save(settings)

            self._apply_settings_runtime(
                settings
            )

            screen.show_status(
                (
                    "Runtime and local AI configuration "
                    "saved successfully."
                )
            )

            self.log_service.info(
                "SETTINGS",
                (
                    "Runtime configuration updated; "
                    f"model={settings.ai_model}; "
                    f"context={settings.ai_context_window}; "
                    f"keep_alive={settings.ai_keep_alive}"
                ),
            )

        except Exception as error:
            screen.show_status(
                f"{type(error).__name__}: {error}",
                error=True,
            )

            self.log_service.error(
                "SETTINGS",
                f"{type(error).__name__}: {error}",
            )

    def _backup_settings(self) -> None:
        screen = self.query_one(
            SettingsScreen
        )

        screen.clear_confirmation()

        try:
            backup_path = (
                self.settings_service
                .create_backup()
            )

            screen.refresh_diagnostics()

            screen.show_status(
                str(backup_path),
                state="BACKUP CREATED",
            )

            self.log_service.info(
                "SETTINGS",
                f"Created backup: {backup_path}",
            )

        except Exception as error:
            screen.show_status(
                f"{type(error).__name__}: {error}",
                error=True,
            )

            self.log_service.error(
                "SETTINGS",
                f"Backup failed: {error}",
            )

    def _export_settings(self) -> None:
        screen = self.query_one(
            SettingsScreen
        )

        screen.clear_confirmation()

        try:
            settings = (
                self.settings_service.validate(
                    screen.read_settings()
                )
            )

            export_path = (
                self.settings_service
                .export_profile(settings)
            )

            screen.refresh_diagnostics()

            screen.show_status(
                str(export_path),
                state="PROFILE EXPORTED",
            )

            self.log_service.info(
                "SETTINGS",
                f"Exported profile: {export_path}",
            )

        except Exception as error:
            screen.show_status(
                f"{type(error).__name__}: {error}",
                error=True,
            )

            self.log_service.error(
                "SETTINGS",
                f"Export failed: {error}",
            )

    def _restore_settings_backup(self) -> None:
        screen = self.query_one(
            SettingsScreen
        )

        if not screen.confirm_action(
            "restore"
        ):
            return

        try:
            # Najpierw wybieramy starą kopię.
            source = (
                self.settings_service
                .latest_backup_path()
            )

            # Dopiero potem zabezpieczamy obecny stan.
            # Dzięki temu nowy rollback nie zostanie
            # omyłkowo wybrany do przywrócenia.
            rollback_backup = (
                self.settings_service
                .create_backup()
            )

            settings = (
                self.settings_service
                .restore_backup(source)
            )

            self._apply_settings_runtime(
                settings
            )

            screen.show_status(
                (
                    f"Restored {source.name}; "
                    f"previous state saved as "
                    f"{rollback_backup.name}"
                ),
                warning=True,
                state="BACKUP RESTORED",
            )

            self.log_service.warning(
                "SETTINGS",
                (
                    f"Restored settings backup: {source}; "
                    f"rollback backup: {rollback_backup}"
                ),
            )

        except Exception as error:
            screen.show_status(
                f"{type(error).__name__}: {error}",
                error=True,
            )

            self.log_service.error(
                "SETTINGS",
                f"Restore failed: {error}",
            )

    def _reset_settings(self) -> None:
        screen = self.query_one(
            SettingsScreen
        )

        if not screen.confirm_action(
            "reset"
        ):
            return

        try:
            backup_path = (
                self.settings_service
                .create_backup()
            )

            settings = (
                self.settings_service.defaults()
            )

            self.settings_service.save(
                settings
            )

            self._apply_settings_runtime(
                settings
            )

            screen.show_status(
                (
                    "Default configuration restored; "
                    f"previous state saved as "
                    f"{backup_path.name}."
                ),
                warning=True,
                state="DEFAULTS RESTORED",
            )

            self.log_service.warning(
                "SETTINGS",
                (
                    "Default configuration restored; "
                    f"backup={backup_path}"
                ),
            )

        except Exception as error:
            screen.show_status(
                f"{type(error).__name__}: {error}",
                error=True,
            )

            self.log_service.error(
                "SETTINGS",
                f"{type(error).__name__}: {error}",
            )


if __name__ == "__main__":
    Helm().run()
