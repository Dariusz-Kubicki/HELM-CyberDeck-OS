from collections import deque

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Sparkline, Static

from services.data_service import SystemSnapshot


class NetworkScreen(Vertical):
    """Live network telemetry screen."""

    HISTORY_SIZE = 60

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.download_history: deque[float] = deque(
            [0.0],
            maxlen=self.HISTORY_SIZE,
        )
        self.upload_history: deque[float] = deque(
            [0.0],
            maxlen=self.HISTORY_SIZE,
        )

    def compose(self) -> ComposeResult:
        with Horizontal(id="network-summary"):
            yield Static("--", id="network-interface", classes="network-card")
            yield Static("--", id="network-ip", classes="network-card")
            yield Static("--", id="network-link", classes="network-card")
            yield Static("--", id="network-status", classes="network-card")

        with Horizontal(id="network-rates"):
            yield Static("--", id="download-rate", classes="network-rate-card")
            yield Static("--", id="upload-rate", classes="network-rate-card")

        with Horizontal(id="network-history"):
            with Vertical(classes="network-graph"):
                yield Static(
                    "[b]DOWNLOAD // 60 SEC[/b]",
                    classes="network-graph-title",
                )
                yield Sparkline(
                    [0.0],
                    min_color="#164657",
                    max_color="#36d7ff",
                    summary_function=max,
                    id="download-history",
                )

            with Vertical(classes="network-graph"):
                yield Static(
                    "[b]UPLOAD // 60 SEC[/b]",
                    classes="network-graph-title",
                )
                yield Sparkline(
                    [0.0],
                    min_color="#164657",
                    max_color="#36d7ff",
                    summary_function=max,
                    id="upload-history",
                )

        yield Static(
            "TOTAL TRANSFER // WAITING FOR TELEMETRY",
            id="network-totals",
        )

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        download_kib = snapshot.network_download_bps / 1024
        upload_kib = snapshot.network_upload_bps / 1024

        self.download_history.append(download_kib)
        self.upload_history.append(upload_kib)

        status = "ONLINE" if snapshot.network_online else "OFFLINE"
        status_color = "cyan" if snapshot.network_online else "red"

        self.query_one("#network-interface", Static).update(
            "[b]INTERFACE[/b]\n\n"
            f"{snapshot.network_interface}"
        )

        self.query_one("#network-ip", Static).update(
            "[b]LOCAL IPv4[/b]\n\n"
            f"{snapshot.network_ip}"
        )

        link_speed = (
            f"{snapshot.network_link_speed} Mbps"
            if snapshot.network_link_speed > 0
            else "UNKNOWN"
        )

        self.query_one("#network-link", Static).update(
            "[b]LINK SPEED[/b]\n\n"
            f"{link_speed}"
        )

        self.query_one("#network-status", Static).update(
            "[b]CONNECTION[/b]\n\n"
            f"[b {status_color}]● {status}[/b {status_color}]"
        )

        self.query_one("#download-rate", Static).update(
            "[b]DOWNLOAD[/b]\n\n"
            f"[b]{self._format_rate(snapshot.network_download_bps)}[/b]"
        )

        self.query_one("#upload-rate", Static).update(
            "[b]UPLOAD[/b]\n\n"
            f"[b]{self._format_rate(snapshot.network_upload_bps)}[/b]"
        )

        self.query_one("#download-history", Sparkline).data = list(
            self.download_history
        )
        self.query_one("#upload-history", Sparkline).data = list(
            self.upload_history
        )

        self.query_one("#network-totals", Static).update(
            f"[b]RECEIVED[/b]  "
            f"{self._format_bytes(snapshot.network_bytes_received)}"
            "    //    "
            f"[b]SENT[/b]  "
            f"{self._format_bytes(snapshot.network_bytes_sent)}"
            f"    //    [b]UPDATED[/b]  {snapshot.timestamp}"
        )

    @staticmethod
    def _format_rate(bytes_per_second: float) -> str:
        if bytes_per_second >= 1024**2:
            return f"{bytes_per_second / 1024**2:.2f} MiB/s"

        if bytes_per_second >= 1024:
            return f"{bytes_per_second / 1024:.1f} KiB/s"

        return f"{bytes_per_second:.0f} B/s"

    @staticmethod
    def _format_bytes(value: int) -> str:
        size = float(value)

        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if size < 1024 or unit == "TiB":
                return f"{size:.1f} {unit}"

            size /= 1024

        return "0 B"
