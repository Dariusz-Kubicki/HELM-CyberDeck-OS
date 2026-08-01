from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Input,
    Static,
    Switch,
)

from services.settings_service import (
    HelmSettings,
    SettingsDiagnostics,
    SettingsService,
)


class SettingsScreen(Vertical):
    """Complete HELM runtime and local AI configuration center."""

    INTERVAL_VALUES = (
        0.5,
        1.0,
        2.0,
        5.0,
        10.0,
    )

    START_SCREEN_VALUES = (
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

    LOG_ROW_VALUES = (
        50,
        100,
        200,
        500,
        1000,
    )

    AI_CONTEXT_VALUES = (
        2048,
        4096,
        8192,
        16384,
    )

    AI_KEEP_ALIVE_VALUES = (
        "0",
        "5m",
        "10m",
        "30m",
        "1h",
    )

    def __init__(
        self,
        settings: HelmSettings,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.settings = settings

        self.telemetry_interval = (
            settings.telemetry_interval
        )
        self.start_screen = settings.start_screen
        self.log_rows = settings.log_rows

        self.ai_context_window = (
            settings.ai_context_window
        )
        self.ai_keep_alive = (
            settings.ai_keep_alive
        )

        self.pending_confirmation: (
            str | None
        ) = None

        self._loading = False
        self._dirty = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="settings-summary"):
            yield Static(
                "--",
                id="setting-refresh-summary",
                classes="settings-card",
            )
            yield Static(
                "--",
                id="setting-start-summary",
                classes="settings-card",
            )
            yield Static(
                "--",
                id="setting-log-summary",
                classes="settings-card",
            )
            yield Static(
                "--",
                id="setting-ai-summary",
                classes="settings-card",
            )

        yield Static(
            "[b cyan]● CONFIGURATION SERVICE ONLINE[/b cyan]"
            "    //    RUNTIME SETTINGS READY",
            id="settings-status",
        )

        yield Static(
            "[b cyan]RUNTIME CONFIGURATION[/b cyan]"
            "    //    HELM BEHAVIOUR",
            classes="settings-section-title",
        )

        with Vertical(
            id="settings-runtime-form",
            classes="settings-panel",
        ):
            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]TELEMETRY INTERVAL[/b]\n"
                    "Time between hardware and system measurements.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="interval-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        "--",
                        id="telemetry-interval-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="interval-next",
                        classes="cycle-arrow",
                    )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]START SCREEN[/b]\n"
                    "Screen opened automatically when HELM starts.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="start-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        "--",
                        id="start-screen-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="start-next",
                        classes="cycle-arrow",
                    )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]EVENT LOG LIMIT[/b]\n"
                    "Maximum number of recent events loaded into LOGS.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="logs-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        "--",
                        id="log-rows-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="logs-next",
                        classes="cycle-arrow",
                    )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]NAVIGATION LOGGING[/b]\n"
                    "Record every opened HELM screen in the event log.",
                    classes="setting-label",
                )

                yield Switch(
                    value=self.settings.navigation_logging,
                    id="navigation-logging",
                    classes="setting-switch",
                )

        yield Static(
            "[b cyan]LOCAL AI CONFIGURATION[/b cyan]"
            "    //    OLLAMA PROVIDER",
            classes="settings-section-title",
        )

        with Vertical(
            id="settings-ai-form",
            classes="settings-panel",
        ):
            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]LOCAL MODEL[/b]\n"
                    "Ollama model used by HELM AI.",
                    classes="setting-label",
                )

                yield Input(
                    value=self.settings.ai_model,
                    placeholder="qwen3:8b",
                    id="ai-model-input",
                    classes="setting-input",
                )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]CONTEXT WINDOW[/b]\n"
                    "Maximum conversation and telemetry context.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="ai-context-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        "--",
                        id="ai-context-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="ai-context-next",
                        classes="cycle-arrow",
                    )

            with Horizontal(classes="setting-row"):
                yield Static(
                    "[b]MODEL KEEP-ALIVE[/b]\n"
                    "How long Ollama keeps the model loaded in VRAM.",
                    classes="setting-label",
                )

                with Horizontal(classes="cycle-control"):
                    yield Button(
                        "◀",
                        id="ai-keep-alive-prev",
                        classes="cycle-arrow",
                    )
                    yield Static(
                        "--",
                        id="ai-keep-alive-value",
                        classes="cycle-value",
                    )
                    yield Button(
                        "▶",
                        id="ai-keep-alive-next",
                        classes="cycle-arrow",
                    )

        yield Static(
            "[b cyan]CONFIGURATION DIAGNOSTICS[/b cyan]"
            "    //    COLLECTING STATE",
            id="settings-diagnostics",
        )

        with Horizontal(id="settings-primary-actions"):
            yield Button(
                "SAVE AND APPLY",
                id="settings-save",
                variant="primary",
                flat=True,
            )
            yield Button(
                "CREATE BACKUP",
                id="settings-backup",
                classes="settings-control-button",
                flat=True,
            )
            yield Button(
                "EXPORT PROFILE",
                id="settings-export",
                classes="settings-control-button",
                flat=True,
            )

        with Horizontal(id="settings-danger-actions"):
            yield Button(
                "RESTORE LATEST BACKUP",
                id="settings-restore",
                classes="settings-warning-button",
            )
            yield Button(
                "RESET DEFAULTS",
                id="settings-reset",
                classes="settings-danger-button",
            )

        yield Static(
            "Runtime configuration: config/settings.json"
            "    //    Backups: config/backups/"
            "    //    Exports: config/exports/",
            id="settings-path",
        )

    def on_mount(self) -> None:
        self.load_settings(self.settings)
        self.refresh_diagnostics()

    def on_button_pressed(
        self,
        event: Button.Pressed,
    ) -> None:
        button_id = event.button.id

        if button_id is None:
            return

        direction_actions = {
            "interval-prev": (
                "telemetry_interval",
                self.INTERVAL_VALUES,
                -1,
            ),
            "interval-next": (
                "telemetry_interval",
                self.INTERVAL_VALUES,
                1,
            ),
            "start-prev": (
                "start_screen",
                self.START_SCREEN_VALUES,
                -1,
            ),
            "start-next": (
                "start_screen",
                self.START_SCREEN_VALUES,
                1,
            ),
            "logs-prev": (
                "log_rows",
                self.LOG_ROW_VALUES,
                -1,
            ),
            "logs-next": (
                "log_rows",
                self.LOG_ROW_VALUES,
                1,
            ),
            "ai-context-prev": (
                "ai_context_window",
                self.AI_CONTEXT_VALUES,
                -1,
            ),
            "ai-context-next": (
                "ai_context_window",
                self.AI_CONTEXT_VALUES,
                1,
            ),
            "ai-keep-alive-prev": (
                "ai_keep_alive",
                self.AI_KEEP_ALIVE_VALUES,
                -1,
            ),
            "ai-keep-alive-next": (
                "ai_keep_alive",
                self.AI_KEEP_ALIVE_VALUES,
                1,
            ),
        }

        action = direction_actions.get(
            button_id
        )

        if action is None:
            return

        attribute, values, direction = action

        setattr(
            self,
            attribute,
            self._cycle(
                values,
                getattr(self, attribute),
                direction,
            ),
        )

        self.clear_confirmation()
        self._refresh_controls()
        self._mark_dirty()

        event.stop()

    def on_input_changed(
        self,
        event: Input.Changed,
    ) -> None:
        if (
            self._loading
            or event.input.id != "ai-model-input"
        ):
            return

        self.clear_confirmation()
        self._mark_dirty()

    def on_switch_changed(
        self,
        event: Switch.Changed,
    ) -> None:
        if (
            self._loading
            or event.switch.id
            != "navigation-logging"
        ):
            return

        self.clear_confirmation()
        self._mark_dirty()

    def read_settings(self) -> HelmSettings:
        model = self.query_one(
            "#ai-model-input",
            Input,
        ).value.strip()

        if not model:
            raise ValueError(
                "Local AI model cannot be empty."
            )

        return HelmSettings(
            telemetry_interval=float(
                self.telemetry_interval
            ),
            start_screen=str(
                self.start_screen
            ),
            navigation_logging=bool(
                self.query_one(
                    "#navigation-logging",
                    Switch,
                ).value
            ),
            log_rows=int(self.log_rows),
            ai_model=model,
            ai_context_window=int(
                self.ai_context_window
            ),
            ai_keep_alive=str(
                self.ai_keep_alive
            ),
        )

    def load_settings(
        self,
        settings: HelmSettings,
    ) -> None:
        self._loading = True

        try:
            self.settings = settings

            self.telemetry_interval = (
                settings.telemetry_interval
            )
            self.start_screen = (
                settings.start_screen
            )
            self.log_rows = settings.log_rows

            self.ai_context_window = (
                settings.ai_context_window
            )
            self.ai_keep_alive = (
                settings.ai_keep_alive
            )

            self.query_one(
                "#navigation-logging",
                Switch,
            ).value = (
                settings.navigation_logging
            )

            self.query_one(
                "#ai-model-input",
                Input,
            ).value = settings.ai_model

            self._refresh_controls()
            self.update_summary(settings)

            self._dirty = False
            self.clear_confirmation()

        finally:
            self._loading = False

        self.refresh_diagnostics()

    def _refresh_controls(self) -> None:
        self.query_one(
            "#telemetry-interval-value",
            Static,
        ).update(
            self._interval_label()
        )

        self.query_one(
            "#start-screen-value",
            Static,
        ).update(
            self.start_screen.upper()
        )

        self.query_one(
            "#log-rows-value",
            Static,
        ).update(
            f"{self.log_rows} EVENTS"
        )

        self.query_one(
            "#ai-context-value",
            Static,
        ).update(
            f"{self.ai_context_window} TOKENS"
        )

        keep_alive_label = {
            "0": "UNLOAD IMMEDIATELY",
            "5m": "5 MINUTES",
            "10m": "10 MINUTES",
            "30m": "30 MINUTES",
            "1h": "1 HOUR",
        }.get(
            self.ai_keep_alive,
            self.ai_keep_alive.upper(),
        )

        self.query_one(
            "#ai-keep-alive-value",
            Static,
        ).update(keep_alive_label)

    def update_summary(
        self,
        settings: HelmSettings,
    ) -> None:
        self.query_one(
            "#setting-refresh-summary",
            Static,
        ).update(
            "[b]REFRESH RATE[/b]\n\n"
            f"[b]{settings.telemetry_interval:g}s[/b]"
        )

        self.query_one(
            "#setting-start-summary",
            Static,
        ).update(
            "[b]START SCREEN[/b]\n\n"
            f"[b]{settings.start_screen.upper()}[/b]"
        )

        self.query_one(
            "#setting-log-summary",
            Static,
        ).update(
            "[b]LOG CAPACITY[/b]\n\n"
            f"[b]{settings.log_rows} EVENTS[/b]"
        )

        model = settings.ai_model

        if len(model) > 22:
            model = model[:19] + "..."

        self.query_one(
            "#setting-ai-summary",
            Static,
        ).update(
            "[b]LOCAL AI[/b]\n\n"
            f"[b cyan]{escape(model)}[/b cyan]\n"
            f"{settings.ai_context_window} TOKENS"
        )

    def refresh_diagnostics(self) -> None:
        service = getattr(
            self.app,
            "settings_service",
            None,
        )

        if not isinstance(
            service,
            SettingsService,
        ):
            return

        diagnostics = service.diagnostics()

        active_mode = str(
            getattr(
                self.app,
                "active_mode_id",
                "UNKNOWN",
            )
        ).upper()

        provider_state = "UNKNOWN"
        provider_detail = "NO AI STATE"

        try:
            ai_screen = self.app.query_one(
                "#ai-screen"
            )

            local_status = getattr(
                ai_screen,
                "local_status",
                None,
            )

            if local_status is not None:
                if not local_status.online:
                    provider_state = "OFFLINE"
                elif not local_status.model_installed:
                    provider_state = "MODEL MISSING"
                elif local_status.model_loaded:
                    provider_state = "GPU LOADED"
                else:
                    provider_state = "READY"

                provider_detail = str(
                    local_status.detail
                )

        except Exception:
            pass

        self._update_diagnostics_panel(
            diagnostics,
            active_mode,
            provider_state,
            provider_detail,
        )

    def _update_diagnostics_panel(
        self,
        diagnostics: SettingsDiagnostics,
        active_mode: str,
        provider_state: str,
        provider_detail: str,
    ) -> None:
        health = (
            "VALID"
            if diagnostics.config_valid
            else "INVALID"
        )

        health_color = (
            "cyan"
            if diagnostics.config_valid
            else "red"
        )

        latest_backup = (
            Path(
                diagnostics.latest_backup
            ).name
            if diagnostics.latest_backup
            else "NONE"
        )

        dirty_state = (
            "UNSAVED CHANGES"
            if self._dirty
            else "SYNCHRONIZED"
        )

        dirty_color = (
            "yellow"
            if self._dirty
            else "cyan"
        )

        self.query_one(
            "#settings-diagnostics",
            Static,
        ).update(
            "[b cyan]CONFIGURATION DIAGNOSTICS[/b cyan]\n\n"
            f"[b]DATABASE[/b]       "
            f"[b {health_color}]"
            f"{health}"
            f"[/b {health_color}]"
            f"  //  {diagnostics.config_size} B\n"
            f"[b]EDITOR STATE[/b]   "
            f"[b {dirty_color}]"
            f"{dirty_state}"
            f"[/b {dirty_color}]\n"
            f"[b]ACTIVE MODE[/b]    "
            f"{escape(active_mode)}\n"
            f"[b]LOCAL AI[/b]       "
            f"{escape(provider_state)}"
            f"  //  {escape(provider_detail)}\n"
            f"[b]BACKUPS[/b]        "
            f"{diagnostics.backup_count}"
            f"  //  LATEST {escape(latest_backup)}\n"
            f"[b]EXPORTS[/b]        "
            f"{diagnostics.export_count}\n"
            f"[b]CONFIG PATH[/b]    "
            f"{escape(diagnostics.config_path)}"
        )

    def _mark_dirty(self) -> None:
        if self._loading:
            return

        try:
            self._dirty = (
                self.read_settings()
                != self.settings
            )
        except ValueError:
            self._dirty = True

        if self._dirty:
            self.show_status(
                "Editor contains unapplied changes.",
                warning=True,
                state="UNSAVED CHANGES",
            )

        self.refresh_diagnostics()

    def confirm_action(
        self,
        action: str,
    ) -> bool:
        if self.pending_confirmation == action:
            self.pending_confirmation = None
            self._restore_action_labels()
            return True

        self.clear_confirmation()
        self.pending_confirmation = action

        if action == "reset":
            self.query_one(
                "#settings-reset",
                Button,
            ).label = "CONFIRM RESET"

            detail = (
                "Press CONFIRM RESET to restore "
                "all default settings."
            )

        elif action == "restore":
            self.query_one(
                "#settings-restore",
                Button,
            ).label = "CONFIRM RESTORE"

            detail = (
                "Press CONFIRM RESTORE to apply "
                "the latest settings backup."
            )

        else:
            detail = (
                "Repeat the action to confirm."
            )

        self.show_status(
            detail,
            warning=True,
            state="CONFIRMATION REQUIRED",
        )

        return False

    def clear_confirmation(self) -> None:
        self.pending_confirmation = None
        self._restore_action_labels()

    def _restore_action_labels(self) -> None:
        self.query_one(
            "#settings-reset",
            Button,
        ).label = "RESET DEFAULTS"

        self.query_one(
            "#settings-restore",
            Button,
        ).label = "RESTORE LATEST BACKUP"

    def show_status(
        self,
        message: str,
        *,
        error: bool = False,
        warning: bool = False,
        state: str | None = None,
    ) -> None:
        if error:
            color = "red"
            label = state or "CONFIGURATION ERROR"
        elif warning:
            color = "yellow"
            label = state or "CONFIGURATION WARNING"
        else:
            color = "cyan"
            label = state or "SETTINGS APPLIED"

        self.query_one(
            "#settings-status",
            Static,
        ).update(
            f"[b {color}]"
            f"● {escape(label)}"
            f"[/b {color}]"
            f"    //    {escape(message)}"
        )

    def _interval_label(self) -> str:
        if self.telemetry_interval == 1.0:
            return "1 SECOND"

        return (
            f"{self.telemetry_interval:g} SECONDS"
        )

    @staticmethod
    def _cycle(
        values: tuple,
        current: object,
        direction: int,
    ):
        try:
            current_index = values.index(
                current
            )
        except ValueError:
            current_index = 0

        return values[
            (
                current_index + direction
            ) % len(values)
        ]
