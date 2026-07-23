from textual.widgets import Static

from services.data_service import SystemSnapshot


class SystemPanel(Static):
    """Displays general system information."""

    def update_snapshot(self, snapshot: SystemSnapshot) -> None:
        self.update(
            "\n".join(
                [
                    "[b cyan]● ONLINE[/b cyan]",
                    "",
                    f"[b]HOST[/b]      {snapshot.host}",
                    f"[b]USER[/b]      {snapshot.user}",
                    f"[b]OS[/b]        {snapshot.os_name}",
                    f"[b]KERNEL[/b]    {snapshot.kernel}",
                    f"[b]UPTIME[/b]    {snapshot.uptime}",
                    f"[b]UPDATED[/b]   {snapshot.timestamp}",
                ]
            )
        )
