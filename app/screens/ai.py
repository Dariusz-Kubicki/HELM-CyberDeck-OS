from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Input,
    RichLog,
    Static,
)
from textual.worker import get_current_worker

from services.assistant_service import AssistantService
from services.data_service import SystemSnapshot
from services.settings_service import HelmSettings
from services.local_ai_service import (
    LocalAIError,
    LocalAIMetrics,
    LocalAIService,
    LocalAIStatus,
)


class AIScreen(Vertical):
    """Hybrid HELM diagnostic core and local Ollama assistant."""

    MAX_HISTORY_MESSAGES = 16

    def __init__(
        self,
        settings: HelmSettings | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.runtime_settings = (
            settings or HelmSettings()
        )

        self.assistant = AssistantService()

        self.local_ai = LocalAIService(
            model=self.runtime_settings.ai_model,
            context_window=(
                self.runtime_settings.ai_context_window
            ),
            keep_alive=(
                self.runtime_settings.ai_keep_alive
            ),
        )

        self.latest_snapshot: SystemSnapshot | None = None

        self.local_status = LocalAIStatus(
            online=False,
            version="N/A",
            model=self.local_ai.model,
            model_installed=False,
            model_loaded=False,
            detail="Local provider has not been checked.",
        )

        self.core_mode = "DIAGNOSTIC"
        self.generating = False

        self.chat_history: list[
            dict[str, str]
        ] = []

        self.session_records: list[
            tuple[str, str, str]
        ] = []

        self.generation_worker = None
        self.generation_token = 0
        self.generation_buffer = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="ai-summary"):
            yield Static(
                "--",
                id="ai-mode-card",
                classes="ai-card",
            )
            yield Static(
                "--",
                id="ai-provider-card",
                classes="ai-card",
            )
            yield Static(
                "--",
                id="ai-context-card",
                classes="ai-card",
            )
            yield Static(
                "--",
                id="ai-core-state",
                classes="ai-card",
            )

        with Horizontal(id="ai-actions"):
            yield Button(
                "FULL DIAGNOSTIC",
                id="ai-diagnostic",
                classes="ai-action",
            )
            yield Button(
                "SYSTEM STATUS",
                id="ai-status",
                classes="ai-action",
            )
            yield Button(
                "CPU ANALYSIS",
                id="ai-cpu",
                classes="ai-action",
            )
            yield Button(
                "GPU ANALYSIS",
                id="ai-gpu",
                classes="ai-action",
            )

        with Horizontal(id="ai-session-actions"):
            yield Button(
                "CORE: DIAGNOSTIC",
                id="ai-toggle-core",
                classes="ai-action",
            )
            yield Button(
                "STOP GENERATION",
                id="ai-stop",
                classes="ai-stop-action",
                disabled=True,
            )
            yield Button(
                "EXPORT SESSION",
                id="ai-export",
                classes="ai-action",
            )
            yield Button(
                "CLEAR SESSION",
                id="ai-clear",
                classes="ai-action",
            )

        yield RichLog(
            id="ai-transcript",
            markup=True,
            wrap=True,
            auto_scroll=True,
            max_lines=2000,
        )

        yield RichLog(
            id="ai-live-response",
            markup=True,
            wrap=True,
            auto_scroll=True,
            max_lines=300,
        )

        with Horizontal(id="ai-command-row"):
            yield Input(
                placeholder=(
                    "Diagnostic command: status, cpu, gpu, "
                    "network, devices, projects..."
                ),
                id="ai-command",
            )
            yield Button(
                "EXECUTE",
                id="ai-execute",
                variant="primary",
            )

        yield Static(
            "[b cyan]● HELM CORE INITIALIZING[/b cyan]",
            id="ai-status-bar",
        )

    def on_mount(self) -> None:
        self._write_boot_message()
        self._check_local_provider()
        self._update_summary_cards()

        self.query_one(
            "#ai-live-response",
            RichLog,
        ).display = False

    def update_snapshot(
        self,
        snapshot: SystemSnapshot,
    ) -> None:
        self.latest_snapshot = snapshot

        self.query_one(
            "#ai-context-card",
            Static,
        ).update(
            "[b]CONTEXT[/b]\n\n"
            f"[b cyan]LIVE {snapshot.timestamp}[/b cyan]\n"
            f"CPU {snapshot.cpu_usage:.0f}%"
            f"  //  RAM {snapshot.ram_usage:.0f}%"
        )

        if not self.generating:
            self.query_one(
                "#ai-core-state",
                Static,
            ).update(
                "[b]CORE STATE[/b]\n\n"
                "[b cyan]● READY[/b cyan]\n"
                f"SNAPSHOT {snapshot.timestamp}"
            )

    def on_input_submitted(
        self,
        event: Input.Submitted,
    ) -> None:
        if event.input.id != "ai-command":
            return

        command = event.value.strip()
        event.input.value = ""

        self._submit(command)
        event.stop()

    def on_button_pressed(
        self,
        event: Button.Pressed,
    ) -> None:
        button_id = event.button.id

        quick_commands = {
            "ai-diagnostic": "diagnostic",
            "ai-status": "status",
            "ai-cpu": "cpu",
            "ai-gpu": "gpu",
        }

        if button_id in quick_commands:
            self._submit_diagnostic(
                quick_commands[button_id]
            )
            event.stop()
            return

        if button_id == "ai-toggle-core":
            self._toggle_core()
            event.stop()
            return

        if button_id == "ai-stop":
            self._stop_generation()
            event.stop()
            return

        if button_id == "ai-export":
            self._export_session()
            event.stop()
            return

        if button_id == "ai-clear":
            self._clear_session()
            event.stop()
            return

        if button_id == "ai-execute":
            command_input = self.query_one(
                "#ai-command",
                Input,
            )
            command = command_input.value.strip()
            command_input.value = ""

            self._submit(command)
            command_input.focus()
            event.stop()

    def execute_command(
        self,
        command: str,
    ) -> None:
        """Run diagnostics requested by another HELM component."""
        self._submit_diagnostic(command)

    def _submit(
        self,
        command: str,
    ) -> None:
        if not command:
            return

        normalized = command.lower().strip()

        if normalized in {
            "clear",
            "cls",
        }:
            self._clear_session()
            return

        if self.core_mode == "LOCAL AI":
            self._start_local_generation(command)
        else:
            self._submit_diagnostic(command)

    def _submit_diagnostic(
        self,
        command: str,
    ) -> None:
        if not command:
            return

        if self.generating:
            self._set_status(
                "CORE BUSY",
                (
                    "Stop local generation before "
                    "running diagnostics."
                ),
                "yellow",
            )
            return

        response = self.assistant.respond(
            command,
            self.latest_snapshot,
        )

        if response == "CLEAR":
            self._clear_session()
            return

        self._write_exchange(
            "YOU // COMMAND",
            command,
            "HELM CORE // RESPONSE",
            response,
        )

        self._set_status(
            "COMMAND COMPLETE",
            command.upper(),
            "cyan",
        )

        self._log(
            "AI DIAGNOSTIC",
            "INFO",
            f"Executed command: {command}",
        )

    def _start_local_generation(
        self,
        prompt: str,
    ) -> None:
        if self.generating:
            self._set_status(
                "GENERATION ACTIVE",
                (
                    "Stop the current response before "
                    "sending another prompt."
                ),
                "yellow",
            )
            return

        if (
            not self.local_status.online
            or not self.local_status.model_installed
        ):
            self._check_local_provider()

        if not self.local_status.online:
            self._set_status(
                "LOCAL AI OFFLINE",
                self.local_status.detail,
                "red",
            )
            return

        if not self.local_status.model_installed:
            self._set_status(
                "MODEL UNAVAILABLE",
                (
                    f"Install {self.local_ai.model} "
                    "before using LOCAL AI."
                ),
                "yellow",
            )
            return

        self.chat_history.append(
            {
                "role": "user",
                "content": prompt,
            }
        )
        self._trim_history()

        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.session_records.append(
            (
                timestamp,
                "YOU",
                prompt,
            )
        )

        self.query_one(
            "#ai-transcript",
            RichLog,
        ).write(
            "[b #36d7ff]"
            "YOU // LOCAL PROMPT"
            "[/b #36d7ff]\n"
            f"{escape(prompt)}"
        )

        self.generation_token += 1
        token = self.generation_token

        self.generation_buffer = ""
        self.generating = True
        self._set_generation_state(True)

        live = self.query_one(
            "#ai-live-response",
            RichLog,
        )
        live.display = True
        live.clear()
        live.write(
            "[b cyan]HELM AI // GENERATING[/b cyan]\n"
            "Waiting for the first token..."
        )

        self._set_status(
            "LOCAL GENERATION",
            (
                f"{self.local_ai.model}"
                " // live telemetry attached"
            ),
            "cyan",
        )

        history = tuple(
            dict(message)
            for message in self.chat_history
        )
        snapshot = self.latest_snapshot

        self.generation_worker = (
            self._generate_local_response(
                token,
                history,
                snapshot,
            )
        )

    @work(
        exclusive=True,
        thread=True,
        exit_on_error=False,
    )
    def _generate_local_response(
        self,
        token: int,
        history: tuple[dict[str, str], ...],
        snapshot: SystemSnapshot | None,
    ) -> None:
        worker = get_current_worker()

        def should_stop() -> bool:
            return (
                worker.is_cancelled
                or token != self.generation_token
            )

        def on_chunk(chunk: str) -> None:
            if should_stop():
                return

            self.app.call_from_thread(
                self._receive_ai_chunk,
                token,
                chunk,
            )

        try:
            metrics = self.local_ai.stream_chat(
                history,
                snapshot,
                on_chunk=on_chunk,
                should_stop=should_stop,
            )

            if should_stop() or metrics.stopped:
                return

            self.app.call_from_thread(
                self._finish_ai_response,
                token,
                metrics,
            )

        except LocalAIError as error:
            if should_stop():
                return

            self.app.call_from_thread(
                self._fail_ai_response,
                token,
                str(error),
            )

        except Exception as error:
            if should_stop():
                return

            self.app.call_from_thread(
                self._fail_ai_response,
                token,
                f"{type(error).__name__}: {error}",
            )

    def _receive_ai_chunk(
        self,
        token: int,
        chunk: str,
    ) -> None:
        if (
            token != self.generation_token
            or not self.generating
        ):
            return

        self.generation_buffer += chunk

        live = self.query_one(
            "#ai-live-response",
            RichLog,
        )
        live.clear()
        live.write(
            "[b cyan]HELM AI // LIVE RESPONSE[/b cyan]\n"
            f"{escape(self.generation_buffer)}"
        )

    def _finish_ai_response(
        self,
        token: int,
        metrics: LocalAIMetrics,
    ) -> None:
        if (
            token != self.generation_token
            or not self.generating
        ):
            return

        response = (
            self.generation_buffer.strip()
            or "Model returned an empty response."
        )

        self.chat_history.append(
            {
                "role": "assistant",
                "content": response,
            }
        )
        self._trim_history()

        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.session_records.append(
            (
                timestamp,
                "HELM AI",
                response,
            )
        )

        self.query_one(
            "#ai-transcript",
            RichLog,
        ).write(
            "[b cyan]HELM AI // RESPONSE[/b cyan]\n"
            f"{escape(response)}\n\n"
            f"[#6a8790]"
            f"MODEL {escape(metrics.model)}"
            f"  //  PROMPT {metrics.prompt_tokens}"
            f"  //  GENERATED {metrics.generated_tokens}"
            f"  //  {metrics.total_seconds:.2f}s"
            f"[/#6a8790]"
        )

        live = self.query_one(
            "#ai-live-response",
            RichLog,
        )
        live.clear()
        live.display = False

        self.generating = False
        self.generation_worker = None
        self._set_generation_state(False)

        self.local_status = LocalAIStatus(
            online=True,
            version=self.local_status.version,
            model=self.local_ai.model,
            model_installed=True,
            model_loaded=True,
            detail=f"{self.local_ai.model} loaded.",
        )

        self._update_summary_cards()

        self._set_status(
            "GENERATION COMPLETE",
            (
                f"{metrics.generated_tokens} token(s)"
                f" // {metrics.total_seconds:.2f}s"
            ),
            "cyan",
        )

        self._log(
            "LOCAL AI",
            "INFO",
            (
                f"Generated "
                f"{metrics.generated_tokens} token(s) "
                f"in {metrics.total_seconds:.2f}s"
            ),
        )

    def _fail_ai_response(
        self,
        token: int,
        detail: str,
    ) -> None:
        if token != self.generation_token:
            return

        self.generating = False
        self.generation_worker = None
        self._set_generation_state(False)

        live = self.query_one(
            "#ai-live-response",
            RichLog,
        )
        live.clear()
        live.display = False

        self.query_one(
            "#ai-transcript",
            RichLog,
        ).write(
            "[b red]HELM AI // ERROR[/b red]\n"
            f"{escape(detail)}"
        )

        self._set_status(
            "LOCAL AI ERROR",
            detail,
            "red",
        )

        self._log(
            "LOCAL AI",
            "ERROR",
            detail,
        )

    def _stop_generation(self) -> None:
        if not self.generating:
            self._set_status(
                "NO ACTIVE GENERATION",
                "The local model is idle.",
                "#70a9b8",
            )
            return

        partial = self.generation_buffer.strip()

        self.generation_token += 1

        if self.generation_worker is not None:
            self.generation_worker.cancel()

        self.generating = False
        self.generation_worker = None
        self._set_generation_state(False)

        live = self.query_one(
            "#ai-live-response",
            RichLog,
        )
        live.clear()
        live.display = False

        if partial:
            self.query_one(
                "#ai-transcript",
                RichLog,
            ).write(
                "[b yellow]"
                "HELM AI // GENERATION STOPPED"
                "[/b yellow]\n"
                f"{escape(partial)}"
            )

            self.session_records.append(
                (
                    datetime.now().strftime(
                        "%H:%M:%S"
                    ),
                    "HELM AI // STOPPED",
                    partial,
                )
            )

        self._set_status(
            "GENERATION STOPPED",
            "Partial response preserved in the transcript.",
            "yellow",
        )

        self._log(
            "LOCAL AI",
            "WARNING",
            "Generation stopped by user",
        )

    def _toggle_core(self) -> None:
        if self.generating:
            self._set_status(
                "CORE BUSY",
                (
                    "Stop generation before switching "
                    "the core."
                ),
                "yellow",
            )
            return

        if self.core_mode == "DIAGNOSTIC":
            self._check_local_provider()

            if (
                not self.local_status.online
                or not self.local_status.model_installed
            ):
                self._set_status(
                    "LOCAL AI UNAVAILABLE",
                    self.local_status.detail,
                    "yellow",
                )
                return

            self.core_mode = "LOCAL AI"
        else:
            self.core_mode = "DIAGNOSTIC"

        self._update_summary_cards()
        self._update_command_placeholder()

        self._set_status(
            "CORE SWITCHED",
            self.core_mode,
            "cyan",
        )

    def apply_settings(
        self,
        settings: HelmSettings,
    ) -> None:
        """Apply new local AI configuration without restarting HELM."""
        if self.generating:
            self._stop_generation()

        previous_model = self.local_ai.model

        self.runtime_settings = settings

        self.local_ai = LocalAIService(
            model=settings.ai_model,
            context_window=settings.ai_context_window,
            keep_alive=settings.ai_keep_alive,
        )

        self.local_status = LocalAIStatus(
            online=False,
            version="N/A",
            model=self.local_ai.model,
            model_installed=False,
            model_loaded=False,
            detail="Local provider configuration changed.",
        )

        self._check_local_provider()
        self._update_command_placeholder()

        self._set_status(
            "AI CONFIGURATION APPLIED",
            (
                f"{previous_model} -> {self.local_ai.model}"
                f" // context "
                f"{self.local_ai.context_window}"
                f" // keep-alive "
                f"{self.local_ai.keep_alive}"
            ),
            "cyan",
        )

        self._log(
            "LOCAL AI",
            "INFO",
            (
                f"Configuration updated; "
                f"model={self.local_ai.model}; "
                f"context={self.local_ai.context_window}; "
                f"keep_alive={self.local_ai.keep_alive}"
            ),
        )

    def _check_local_provider(self) -> None:
        self.local_status = (
            self.local_ai.check_status()
        )

        self._update_summary_cards()

    def _update_summary_cards(self) -> None:
        mode_color = (
            "cyan"
            if self.core_mode == "LOCAL AI"
            else "#8be9fd"
        )

        self.query_one(
            "#ai-mode-card",
            Static,
        ).update(
            "[b]CORE MODE[/b]\n\n"
            f"[b {mode_color}]"
            f"{self.core_mode}"
            f"[/b {mode_color}]"
        )

        if not self.local_status.online:
            provider_state = (
                "[b red]OFFLINE[/b red]"
            )
            provider_detail = "OLLAMA"

        elif not self.local_status.model_installed:
            provider_state = (
                "[b yellow]MODEL MISSING[/b yellow]"
            )
            provider_detail = self.local_ai.model

        elif self.local_status.model_loaded:
            provider_state = (
                "[b cyan]● GPU LOADED[/b cyan]"
            )
            provider_detail = self.local_ai.model

        else:
            provider_state = (
                "[b cyan]● READY[/b cyan]"
            )
            provider_detail = self.local_ai.model

        self.query_one(
            "#ai-provider-card",
            Static,
        ).update(
            "[b]LOCAL PROVIDER[/b]\n\n"
            f"{provider_state}\n"
            f"{escape(provider_detail)}"
        )

        snapshot = self.latest_snapshot

        if snapshot is None:
            context_text = (
                "[b]CONTEXT[/b]\n\n"
                "[b yellow]WAITING[/b yellow]\n"
                "NO SNAPSHOT"
            )
        else:
            context_text = (
                "[b]CONTEXT[/b]\n\n"
                f"[b cyan]LIVE "
                f"{snapshot.timestamp}"
                f"[/b cyan]\n"
                f"CPU {snapshot.cpu_usage:.0f}%"
                f"  //  RAM {snapshot.ram_usage:.0f}%"
            )

        self.query_one(
            "#ai-context-card",
            Static,
        ).update(context_text)

        if self.generating:
            core_text = (
                "[b]CORE STATE[/b]\n\n"
                "[b yellow]● GENERATING[/b yellow]\n"
                f"{escape(self.local_ai.model)}"
            )
        else:
            core_text = (
                "[b]CORE STATE[/b]\n\n"
                "[b cyan]● READY[/b cyan]\n"
                f"HISTORY {len(self.chat_history)}"
            )

        self.query_one(
            "#ai-core-state",
            Static,
        ).update(core_text)

        self.query_one(
            "#ai-toggle-core",
            Button,
        ).label = (
            f"CORE: {self.core_mode}"
        )

    def _update_command_placeholder(self) -> None:
        command_input = self.query_one(
            "#ai-command",
            Input,
        )

        if self.core_mode == "LOCAL AI":
            command_input.placeholder = (
                "Ask HELM AI about telemetry, code, "
                "electronics or the current project..."
            )
        else:
            command_input.placeholder = (
                "Diagnostic command: status, cpu, gpu, "
                "network, devices, projects..."
            )

    def _set_generation_state(
        self,
        active: bool,
    ) -> None:
        self.query_one(
            "#ai-stop",
            Button,
        ).disabled = not active

        self.query_one(
            "#ai-execute",
            Button,
        ).disabled = active

        self.query_one(
            "#ai-command",
            Input,
        ).disabled = active

        self.query_one(
            "#ai-toggle-core",
            Button,
        ).disabled = active

        self._update_summary_cards()

    def _write_exchange(
        self,
        request_title: str,
        request: str,
        response_title: str,
        response: str,
    ) -> None:
        transcript = self.query_one(
            "#ai-transcript",
            RichLog,
        )

        transcript.write(
            f"[b #36d7ff]"
            f"{escape(request_title)}"
            f"[/b #36d7ff]\n"
            f"{escape(request)}"
        )

        transcript.write(
            f"[b cyan]"
            f"{escape(response_title)}"
            f"[/b cyan]\n"
            f"{escape(response)}"
        )

        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.session_records.extend(
            [
                (
                    timestamp,
                    request_title,
                    request,
                ),
                (
                    timestamp,
                    response_title,
                    response,
                ),
            ]
        )

    def _clear_session(self) -> None:
        if self.generating:
            self._stop_generation()

        self.chat_history.clear()
        self.session_records.clear()
        self.generation_buffer = ""

        transcript = self.query_one(
            "#ai-transcript",
            RichLog,
        )
        transcript.clear()

        live = self.query_one(
            "#ai-live-response",
            RichLog,
        )
        live.clear()
        live.display = False

        self._write_boot_message()
        self._update_summary_cards()

        self._set_status(
            "SESSION CLEARED",
            "Conversation memory and transcript reset.",
            "cyan",
        )

    def _export_session(self) -> None:
        if not self.session_records:
            self._set_status(
                "EXPORT SKIPPED",
                "The current AI session is empty.",
                "yellow",
            )
            return

        project_root = Path(
            __file__
        ).resolve().parents[2]

        export_directory = (
            project_root
            / "logs"
            / "exports"
        )

        export_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        export_path = (
            export_directory
            / (
                "helm-ai-session-"
                + datetime.now().strftime(
                    "%Y%m%d-%H%M%S"
                )
                + ".md"
            )
        )

        lines = [
            "# HELM AI Session",
            "",
            (
                "- Exported: "
                + datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
            f"- Core mode: {self.core_mode}",
            f"- Local model: {self.local_ai.model}",
            "",
        ]

        for timestamp, role, content in self.session_records:
            lines.extend(
                [
                    f"## {timestamp} — {role}",
                    "",
                    content,
                    "",
                ]
            )

        try:
            export_path.write_text(
                "\n".join(lines),
                encoding="utf-8",
            )

        except OSError as error:
            self._set_status(
                "EXPORT FAILED",
                f"{type(error).__name__}: {error}",
                "red",
            )
            return

        self._set_status(
            "SESSION EXPORTED",
            str(export_path),
            "cyan",
        )

        self._log(
            "LOCAL AI",
            "INFO",
            f"Exported AI session to {export_path}",
        )

    def _trim_history(self) -> None:
        if (
            len(self.chat_history)
            <= self.MAX_HISTORY_MESSAGES
        ):
            return

        self.chat_history = self.chat_history[
            -self.MAX_HISTORY_MESSAGES:
        ]

    def _set_status(
        self,
        state: str,
        detail: str,
        color: str,
    ) -> None:
        self.query_one(
            "#ai-status-bar",
            Static,
        ).update(
            f"[b {color}]"
            f"● {escape(state)}"
            f"[/b {color}]"
            f"    //    {escape(detail)}"
        )

    def _log(
        self,
        source: str,
        level: str,
        message: str,
    ) -> None:
        log_service = getattr(
            self.app,
            "log_service",
            None,
        )

        if log_service is None:
            return

        if level == "ERROR":
            log_service.error(
                source,
                message,
            )
        elif level == "WARNING":
            log_service.warning(
                source,
                message,
            )
        else:
            log_service.info(
                source,
                message,
            )

    def _write_boot_message(self) -> None:
        transcript = self.query_one(
            "#ai-transcript",
            RichLog,
        )

        transcript.write(
            "[b cyan]HELM HYBRID AI CORE v2.0[/b cyan]\n"
            "Deterministic diagnostics and local Ollama "
            "reasoning enabled.\n"
            "Telemetry context is read-only and remains "
            "on this machine.\n\n"
            "Use [b]CORE: DIAGNOSTIC[/b] to switch engines."
        )
