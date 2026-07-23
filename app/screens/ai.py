from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, RichLog, Static

from services.assistant_service import AssistantService
from services.data_service import SystemSnapshot


class AIScreen(Vertical):
    """Interactive local HELM diagnostic console."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.assistant = AssistantService()
        self.latest_snapshot: SystemSnapshot | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="ai-summary"):
            yield Static(
                "[b]CORE MODE[/b]\n\n"
                "[b cyan]LOCAL[/b cyan]",
                classes="ai-card",
            )
            yield Static(
                "[b]PROVIDER[/b]\n\n"
                "[b]HELM CORE[/b]",
                classes="ai-card",
            )
            yield Static(
                "[b]CONTEXT[/b]\n\n"
                "[b]LIVE TELEMETRY[/b]",
                classes="ai-card",
            )
            yield Static(
                "[b]CORE STATE[/b]\n\n"
                "[b cyan]● READY[/b cyan]",
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
                "HELP",
                id="ai-help",
                classes="ai-action",
            )
            yield Button(
                "CLEAR TERMINAL",
                id="ai-clear",
                classes="ai-action",
            )

        yield RichLog(
            id="ai-transcript",
            markup=True,
            wrap=True,
            auto_scroll=True,
            max_lines=1000,
        )

        with Horizontal(id="ai-command-row"):
            yield Input(
                placeholder=(
                    "Enter command: diagnostic, cpu, gpu, network, "
                    "devices, projects..."
                ),
                id="ai-command",
            )
            yield Button(
                "EXECUTE",
                id="ai-execute",
                variant="primary",
            )

        yield Static(
            "[b cyan]● LOCAL CORE ONLINE[/b cyan]"
            "    //    NO EXTERNAL DATA TRANSMISSION",
            id="ai-status-bar",
        )

    def on_mount(self) -> None:
        self._write_boot_message()

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        self.latest_snapshot = snapshot

        self.query_one("#ai-core-state", Static).update(
            "[b]CORE STATE[/b]\n\n"
            f"[b cyan]● LIVE {snapshot.timestamp}[/b cyan]"
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "ai-command":
            return

        command = event.value.strip()
        event.input.value = ""

        self._submit_command(command)
        event.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        commands = {
            "ai-diagnostic": "diagnostic",
            "ai-status": "status",
            "ai-help": "help",
        }

        button_id = event.button.id

        if button_id == "ai-clear":
            self._clear_terminal()
            event.stop()
            return

        if button_id == "ai-execute":
            command_input = self.query_one("#ai-command", Input)
            command = command_input.value.strip()
            command_input.value = ""

            self._submit_command(command)
            command_input.focus()
            event.stop()
            return

        command = commands.get(button_id)

        if command is not None:
            self._submit_command(command)
            event.stop()

    def execute_command(self, command: str) -> None:
        """Execute a diagnostic command from another HELM component."""
        self._submit_command(command)

    def _submit_command(self, command: str) -> None:
        if not command:
            return

        if command.lower().strip() in {"clear", "cls"}:
            self._clear_terminal()
            return

        transcript = self.query_one("#ai-transcript", RichLog)

        transcript.write(
            "[b #36d7ff]YOU // COMMAND[/b #36d7ff]\n"
            f"{escape(command)}"
        )

        response = self.assistant.respond(
            command,
            self.latest_snapshot,
        )

        if response == "CLEAR":
            self._clear_terminal()
            return

        transcript.write(
            "[b cyan]HELM CORE // RESPONSE[/b cyan]\n"
            f"{escape(response)}"
        )

        self.query_one("#ai-status-bar", Static).update(
            "[b cyan]● COMMAND COMPLETE[/b cyan]"
            f"    //    {escape(command.upper())}"
        )

    def _clear_terminal(self) -> None:
        transcript = self.query_one("#ai-transcript", RichLog)
        transcript.clear()

        self._write_boot_message()

        self.query_one("#ai-status-bar", Static).update(
            "[b cyan]● TERMINAL CLEARED[/b cyan]"
            "    //    CORE READY"
        )

    def _write_boot_message(self) -> None:
        transcript = self.query_one("#ai-transcript", RichLog)

        transcript.write(
            "[b cyan]HELM DIAGNOSTIC CORE v1.0[/b cyan]\n"
            "Local command processor initialized.\n"
            "Live CyberDeck telemetry context enabled.\n\n"
            "Type [b]HELP[/b] to display available commands."
        )
