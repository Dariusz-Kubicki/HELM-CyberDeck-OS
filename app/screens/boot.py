from __future__ import annotations

import getpass

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Static

from app.sidebar import display_version


class BootScreen(ModalScreen):
    """Animated HELM CyberDeck startup sequence."""

    BOOT_SEQUENCE = (
        "[#315965]01[/]  CORE FABRIC"
        ".................. [b #58f6d0]ONLINE[/]",
        "[#315965]02[/]  TELEMETRY BUS"
        "................ [b #58f6d0]SYNCED[/]",
        "[#315965]03[/]  HARDWARE MATRIX"
        ".............. [b #58f6d0]MAPPED[/]",
        "[#315965]04[/]  NETWORK LAYER"
        "................ [b #58f6d0]LINKED[/]",
        "[#315965]05[/]  STORAGE ARRAY"
        "................. [b #58f6d0]READY[/]",
        "[#315965]06[/]  WORKSPACE ENGINE"
        ".............. [b #58f6d0]ARMED[/]",
        "[#315965]07[/]  LOCAL AI PROVIDER"
        "............ [b #58f6d0]ONLINE[/]",
        "[#315965]08[/]  SECURITY ENVELOPE"
        "............ [b #58f6d0]SEALED[/]",
    )

    def __init__(self) -> None:
        super().__init__()

        self._step = 0
        self._hold_ticks = 0
        self._timer: Timer | None = None
        self._visible_lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static(
            "[b #42e8ff]◈  H  E  L  M[/b #42e8ff]\n"
            "[#315965]CYBERDECK OPERATING FABRIC[/]",
            id="boot-logo",
        )

        yield Static(
            "LOCAL SYSTEM INITIALIZATION"
            f"    //    BUILD {display_version()}",
            id="boot-build",
        )

        yield Static(
            "",
            id="boot-sequence",
        )

        yield Static(
            "[#42e8ff]░░░░░░░░░░░░░░░░░░░░░░░░[/]",
            id="boot-progress",
        )

        yield Static(
            "",
            id="boot-access",
        )

        yield Static(
            "PRESS ANY KEY TO BYPASS STARTUP SEQUENCE",
            id="boot-hint",
        )

    def on_mount(self) -> None:
        self._timer = self.set_interval(
            0.13,
            self._advance_sequence,
        )

    def on_key(self, event) -> None:
        self._finish()
        event.stop()

    def _advance_sequence(self) -> None:
        if self._step < len(self.BOOT_SEQUENCE):
            self._visible_lines.append(
                self.BOOT_SEQUENCE[self._step]
            )

            self._step += 1

            self.query_one(
                "#boot-sequence",
                Static,
            ).update(
                "\n".join(self._visible_lines)
            )

            width = 24
            completed = round(
                width
                * self._step
                / len(self.BOOT_SEQUENCE)
            )

            progress = (
                "█" * completed
                + "░" * (width - completed)
            )

            self.query_one(
                "#boot-progress",
                Static,
            ).update(
                f"[#42e8ff]{progress}[/]"
                f"  {self._step * 100 // len(self.BOOT_SEQUENCE):03d}%"
            )

            return

        if self._hold_ticks == 0:
            operator = getpass.getuser().upper()

            self.query_one(
                "#boot-access",
                Static,
            ).update(
                "[b #58f6d0]"
                "ACCESS GRANTED"
                "[/b #58f6d0]"
                f"    //    OPERATOR {operator}"
            )

        self._hold_ticks += 1

        if self._hold_ticks >= 6:
            self._finish()

    def _finish(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

        self.dismiss()
