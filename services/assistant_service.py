from __future__ import annotations

from services.data_service import SystemSnapshot


class AssistantService:
    """Local diagnostic command processor for HELM."""

    HELP_TEXT = """AVAILABLE COMMANDS

help / pomoc
    Display this command list.

status / diagnostyka
    Run a full CyberDeck diagnostic.

cpu
    Show CPU load and temperature.

gpu
    Show GPU load, temperature, memory and power.

ram / memory
    Show system memory usage.

storage / disk / dysk
    Show root filesystem and physical drive information.

network / sieć
    Show network interface, address and transfer rates.

devices / urządzenia / usb
    Show connected USB and serial devices.

projects / projekty
    Show current project status and primary objective.

uptime
    Show host, kernel and system uptime.

clear
    Clear the AI terminal."""

    def respond(
        self,
        command: str,
        snapshot: SystemSnapshot | None,
    ) -> str:
        normalized = " ".join(command.lower().strip().split())

        if not normalized:
            return "No command received."

        if normalized in {"help", "pomoc", "commands", "komendy", "?"}:
            return self.HELP_TEXT

        if snapshot is None:
            return (
                "LIVE TELEMETRY UNAVAILABLE\n"
                "Wait for the first system measurement and try again."
            )

        if normalized in {"clear", "cls"}:
            return "CLEAR"

        if self._contains(
            normalized,
            "diagnostic",
            "diagnostyka",
            "status",
            "system status",
            "stan systemu",
            "full scan",
        ):
            return self._full_diagnostic(snapshot)

        if self._contains(normalized, "cpu", "processor", "procesor"):
            return self._cpu_report(snapshot)

        if self._contains(normalized, "gpu", "graphics", "grafika", "karta"):
            return self._gpu_report(snapshot)

        if self._contains(
            normalized,
            "ram",
            "memory",
            "pamięć ram",
            "pamiec ram",
        ):
            return self._ram_report(snapshot)

        if self._contains(
            normalized,
            "storage",
            "disk",
            "dysk",
            "ssd",
            "nvme",
        ):
            return self._storage_report(snapshot)

        if self._contains(
            normalized,
            "network",
            "sieć",
            "siec",
            "internet",
            "ethernet",
            "wifi",
        ):
            return self._network_report(snapshot)

        if self._contains(
            normalized,
            "devices",
            "device",
            "urządzenia",
            "urzadzenia",
            "usb",
            "serial",
            "arduino",
            "esp32",
        ):
            return self._devices_report(snapshot)

        if self._contains(
            normalized,
            "projects",
            "project",
            "projekty",
            "projekt",
        ):
            return self._projects_report(snapshot)

        if self._contains(
            normalized,
            "uptime",
            "kernel",
            "host",
            "system",
        ):
            return self._host_report(snapshot)

        return (
            f"UNKNOWN COMMAND: {command}\n\n"
            "Type HELP to display the available diagnostic commands."
        )

    def _full_diagnostic(self, snapshot: SystemSnapshot) -> str:
        alerts: list[str] = []

        if snapshot.cpu_temp is not None and snapshot.cpu_temp >= 85:
            alerts.append(
                f"CPU temperature critical: {snapshot.cpu_temp:.1f}°C"
            )

        if snapshot.gpu_temp is not None and snapshot.gpu_temp >= 85:
            alerts.append(
                f"GPU temperature critical: {snapshot.gpu_temp:.1f}°C"
            )

        if snapshot.ram_usage >= 90:
            alerts.append(
                f"RAM usage critical: {snapshot.ram_usage:.1f}%"
            )

        if snapshot.storage.root_percent >= 90:
            alerts.append(
                "Root filesystem almost full: "
                f"{snapshot.storage.root_percent:.1f}%"
            )

        if not snapshot.network_online:
            alerts.append("Primary network interface is offline")

        failed_drives = [
            device.name
            for device in snapshot.storage.devices
            if device.smart_status == "FAILED"
        ]

        if failed_drives:
            alerts.append(
                "SMART failure: " + ", ".join(failed_drives)
            )

        if snapshot.projects.blocked_count:
            alerts.append(
                f"{snapshot.projects.blocked_count} project(s) blocked"
            )

        state = "NOMINAL" if not alerts else "ATTENTION REQUIRED"

        lines = [
            "HELM FULL DIAGNOSTIC",
            "",
            f"STATE       {state}",
            f"HOST        {snapshot.host}",
            f"CPU         {snapshot.cpu_usage:.1f}%"
            f"  //  {self._optional(snapshot.cpu_temp, '°C')}",
            f"GPU         {self._optional(snapshot.gpu_usage, '%')}"
            f"  //  {self._optional(snapshot.gpu_temp, '°C')}",
            f"RAM         {snapshot.ram_usage:.1f}%",
            f"ROOT        {snapshot.storage.root_percent:.1f}%",
            f"NETWORK     "
            f"{'ONLINE' if snapshot.network_online else 'OFFLINE'}",
            f"USB         {len(snapshot.devices.usb_devices)} device(s)",
            f"SERIAL      {len(snapshot.devices.serial_devices)} port(s)",
            f"PROJECTS    {snapshot.projects.active_count} active"
            f"  //  {snapshot.projects.blocked_count} blocked",
            "",
        ]

        if alerts:
            lines.append("DETECTED CONDITIONS")

            for index, alert in enumerate(alerts, start=1):
                lines.append(f"{index:02d}. {alert}")
        else:
            lines.append("No critical conditions detected.")

        return "\n".join(lines)

    def _cpu_report(self, snapshot: SystemSnapshot) -> str:
        return "\n".join(
            [
                "CPU CORE TELEMETRY",
                "",
                f"LOAD         {snapshot.cpu_usage:.1f}%",
                f"TEMPERATURE  "
                f"{self._optional(snapshot.cpu_temp, '°C')}",
                f"UPDATED      {snapshot.timestamp}",
            ]
        )

    def _gpu_report(self, snapshot: SystemSnapshot) -> str:
        return "\n".join(
            [
                "GPU CORE TELEMETRY",
                "",
                f"LOAD         "
                f"{self._optional(snapshot.gpu_usage, '%')}",
                f"TEMPERATURE  "
                f"{self._optional(snapshot.gpu_temp, '°C')}",
                f"MEMORY       "
                f"{self._optional(snapshot.gpu_memory, ' MiB')}",
                f"POWER        "
                f"{self._optional(snapshot.gpu_power, ' W')}",
                f"UPDATED      {snapshot.timestamp}",
            ]
        )

    def _ram_report(self, snapshot: SystemSnapshot) -> str:
        return "\n".join(
            [
                "SYSTEM MEMORY",
                "",
                f"LOAD         {snapshot.ram_usage:.1f}%",
                f"STATE        "
                f"{self._load_state(snapshot.ram_usage)}",
                f"UPDATED      {snapshot.timestamp}",
            ]
        )

    def _storage_report(self, snapshot: SystemSnapshot) -> str:
        storage = snapshot.storage

        lines = [
            "STORAGE ARRAY",
            "",
            f"ROOT USED    {storage.root_percent:.1f}%",
            f"ROOT FREE    {self._format_bytes(storage.root_free)}",
            f"READ RATE    {self._format_rate(storage.read_bps)}",
            f"WRITE RATE   {self._format_rate(storage.write_bps)}",
            "",
            f"PHYSICAL DRIVES: {len(storage.devices)}",
        ]

        for device in storage.devices:
            temperature = (
                f"{device.temperature_c:.1f}°C"
                if device.temperature_c is not None
                else "N/A"
            )

            lines.append(
                f"/dev/{device.name}  //  {device.model}"
                f"  //  TEMP {temperature}"
                f"  //  SMART {device.smart_status}"
            )

        return "\n".join(lines)

    def _network_report(self, snapshot: SystemSnapshot) -> str:
        status = "ONLINE" if snapshot.network_online else "OFFLINE"

        link_speed = (
            f"{snapshot.network_link_speed} Mbps"
            if snapshot.network_link_speed > 0
            else "UNKNOWN"
        )

        return "\n".join(
            [
                "NETWORK TELEMETRY",
                "",
                f"STATUS       {status}",
                f"INTERFACE    {snapshot.network_interface}",
                f"IPv4         {snapshot.network_ip}",
                f"LINK         {link_speed}",
                f"DOWNLOAD     "
                f"{self._format_rate(snapshot.network_download_bps)}",
                f"UPLOAD       "
                f"{self._format_rate(snapshot.network_upload_bps)}",
                f"RECEIVED     "
                f"{self._format_bytes(snapshot.network_bytes_received)}",
                f"SENT         "
                f"{self._format_bytes(snapshot.network_bytes_sent)}",
            ]
        )

    def _devices_report(self, snapshot: SystemSnapshot) -> str:
        devices = snapshot.devices

        lines = [
            "CONNECTED DEVICES",
            "",
            f"USB DEVICES   {len(devices.usb_devices)}",
            f"SERIAL PORTS  {len(devices.serial_devices)}",
        ]

        if devices.serial_devices:
            lines.extend(["", "SERIAL LINKS"])

            for device in devices.serial_devices:
                lines.append(
                    f"{device.path}  //  {device.driver}"
                    f"  //  {device.usb_manufacturer}"
                    f" {device.usb_product}"
                )
        else:
            lines.extend(
                [
                    "",
                    "No Arduino, ESP32 or other serial link detected.",
                ]
            )

        return "\n".join(lines)

    def _projects_report(self, snapshot: SystemSnapshot) -> str:
        projects = snapshot.projects

        lines = [
            "PROJECT COMMAND",
            "",
            f"TOTAL       {len(projects.projects)}",
            f"ACTIVE      {projects.active_count}",
            f"BLOCKED     {projects.blocked_count}",
            f"COMPLETED   {projects.completed_count}",
            f"AVERAGE     {projects.average_progress:.1f}%",
        ]

        if projects.focus_project is not None:
            focus = projects.focus_project

            lines.extend(
                [
                    "",
                    "PRIMARY OBJECTIVE",
                    f"PROJECT     {focus.name}",
                    f"STATUS      {focus.status}",
                    f"PRIORITY    {focus.priority}/5",
                    f"PROGRESS    {focus.progress}%",
                    f"NEXT ACTION {focus.next_action}",
                ]
            )

        return "\n".join(lines)

    def _host_report(self, snapshot: SystemSnapshot) -> str:
        return "\n".join(
            [
                "HOST INFORMATION",
                "",
                f"HOST       {snapshot.host}",
                f"USER       {snapshot.user}",
                f"OS         {snapshot.os_name}",
                f"KERNEL     {snapshot.kernel}",
                f"UPTIME     {snapshot.uptime}",
                f"UPDATED    {snapshot.timestamp}",
            ]
        )

    @staticmethod
    def _contains(command: str, *keywords: str) -> bool:
        return any(keyword in command for keyword in keywords)

    @staticmethod
    def _optional(
        value: float | None,
        suffix: str,
    ) -> str:
        if value is None:
            return "N/A"

        return f"{value:.1f}{suffix}"

    @staticmethod
    def _load_state(value: float) -> str:
        if value >= 90:
            return "CRITICAL"

        if value >= 75:
            return "HIGH"

        if value >= 50:
            return "MODERATE"

        return "NOMINAL"

    @staticmethod
    def _format_rate(value: float) -> str:
        return f"{AssistantService._format_bytes(value)}/s"

    @staticmethod
    def _format_bytes(value: float) -> str:
        size = float(value)

        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if size < 1024 or unit == "TiB":
                return f"{size:.1f} {unit}"

            size /= 1024

        return "0 B"
