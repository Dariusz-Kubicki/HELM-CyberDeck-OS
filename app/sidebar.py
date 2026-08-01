from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static


def display_version() -> str:
    version_path = (
        Path(__file__).resolve().parents[1]
        / "VERSION"
    )

    try:
        version = version_path.read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return "UNKNOWN"

    if version.endswith("-dev"):
        release = version.removesuffix("-dev")
        parts = release.split(".")

        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]} DEV"

        return f"{release} DEV"

    return version or "UNKNOWN"


class Sidebar(Vertical):
    """HELM navigation and live CyberDeck state rail."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[b #42e8ff]◈ H E L M[/b #42e8ff]\n"
            f"[#315965]CYBERDECK OS // {display_version()}[/]",
            id="sidebar-brand",
        )

        yield Static(
            "◆ CORE SYSTEMS",
            classes="sidebar-section",
        )

        yield Button(
            "◈  SYSTEM",
            id="system",
            classes="nav-button selected",
        )
        yield Button(
            "⌁  NETWORK",
            id="network",
            classes="nav-button",
        )
        yield Button(
            "▣  STORAGE",
            id="storage",
            classes="nav-button",
        )
        yield Button(
            "◇  DEVICES",
            id="devices",
            classes="nav-button",
        )

        yield Static(
            "◆ OPERATIONS",
            classes="sidebar-section",
        )

        yield Button(
            "◫  MODES",
            id="modes",
            classes="nav-button",
        )
        yield Button(
            "◆  PROJECTS",
            id="projects",
            classes="nav-button",
        )
        yield Button(
            "≡  EVENT LOG",
            id="logs",
            classes="nav-button",
        )

        yield Static(
            "◆ INTELLIGENCE",
            classes="sidebar-section",
        )

        yield Button(
            "◉  AI CORE",
            id="ai",
            classes="nav-button",
        )
        yield Button(
            "⚙  SETTINGS",
            id="settings",
            classes="nav-button",
        )

        yield Static(
            "[b]CORE LINK[/b]\n"
            "[b #ffbd59]● INITIALIZING[/b #ffbd59]",
            id="sidebar-core-state",
        )

        yield Static(
            "[b]WORKSPACE[/b]\n"
            "[#6f9da8]CUSTOM RUNTIME[/]",
            id="sidebar-mode-state",
        )

        yield Static(
            "CTRL+K  //  COMMAND MATRIX",
            id="sidebar-hotkey",
        )

    def update_core_state(
        self,
        health: str,
        telemetry: str,
        duration_ms: float,
        skipped_cycles: int,
    ) -> None:
        health_color = self._state_color(
            health
        )

        telemetry_color = self._state_color(
            telemetry
        )

        self.query_one(
            "#sidebar-core-state",
            Static,
        ).update(
            "[b]CORE LINK[/b]\n"
            f"[{health_color}]"
            f"● HEALTH {escape(health.upper())}"
            "[/]\n"
            f"[{telemetry_color}]"
            f"● DATA {escape(telemetry.upper())}"
            "[/]  "
            f"[#456d78]"
            f"{duration_ms:.0f}ms / S{skipped_cycles}"
            "[/]"
        )

    def update_mode(
        self,
        name: str,
        mode_id: str,
    ) -> None:
        clean_name = (
            name.strip()
            or mode_id.strip()
            or "CUSTOM"
        )

        self.query_one(
            "#sidebar-mode-state",
            Static,
        ).update(
            "[b]WORKSPACE[/b]\n"
            f"[b #42e8ff]"
            f"{escape(clean_name.upper())}"
            f"[/b #42e8ff]\n"
            f"[#456d78]"
            f"{escape(mode_id.upper())}"
            f"[/]"
        )

    @staticmethod
    def _state_color(
        state: str,
    ) -> str:
        normalized = state.upper()

        if normalized in {
            "NOMINAL",
            "READY",
            "ONLINE",
        }:
            return "#58f6d0"

        if normalized in {
            "CRITICAL",
            "FAILED",
            "OFFLINE",
        }:
            return "#ff4365"

        if normalized in {
            "DEGRADED",
            "WARNING",
            "BUSY",
            "SCANNING",
            "STARTING",
        }:
            return "#ffbd59"

        return "#42e8ff"
