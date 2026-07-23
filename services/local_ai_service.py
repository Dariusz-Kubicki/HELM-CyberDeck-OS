from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable

from services.data_service import SystemSnapshot


@dataclass(frozen=True, slots=True)
class LocalAIStatus:
    online: bool
    version: str
    model: str
    model_installed: bool
    model_loaded: bool
    detail: str


@dataclass(frozen=True, slots=True)
class LocalAIMetrics:
    model: str
    prompt_tokens: int
    generated_tokens: int
    total_seconds: float
    stopped: bool = False


class LocalAIError(RuntimeError):
    """Raised when the local Ollama provider cannot complete a request."""


class LocalAIService:
    """Local Ollama chat client with live HELM telemetry context."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3:8b",
        context_window: int = 4096,
        keep_alive: str = "10m",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.context_window = max(
            2048,
            int(context_window),
        )
        self.keep_alive = keep_alive

    def check_status(self) -> LocalAIStatus:
        try:
            version_payload = self._get_json(
                "/api/version",
                timeout=2.0,
            )
            tags_payload = self._get_json(
                "/api/tags",
                timeout=2.0,
            )
            running_payload = self._get_json(
                "/api/ps",
                timeout=2.0,
            )

        except LocalAIError as error:
            return LocalAIStatus(
                online=False,
                version="N/A",
                model=self.model,
                model_installed=False,
                model_loaded=False,
                detail=str(error),
            )

        installed_names = self._model_names(
            tags_payload.get("models", [])
        )
        running_names = self._model_names(
            running_payload.get("models", [])
        )

        installed = self._matches_model(
            self.model,
            installed_names,
        )
        loaded = self._matches_model(
            self.model,
            running_names,
        )

        if not installed:
            detail = (
                f"Provider online, but "
                f"{self.model} is not installed."
            )
        elif loaded:
            detail = (
                f"{self.model} loaded on local provider."
            )
        else:
            detail = (
                f"{self.model} installed and ready to load."
            )

        return LocalAIStatus(
            online=True,
            version=str(
                version_payload.get(
                    "version",
                    "UNKNOWN",
                )
            ),
            model=self.model,
            model_installed=installed,
            model_loaded=loaded,
            detail=detail,
        )

    def stream_chat(
        self,
        history: Iterable[dict[str, str]],
        snapshot: SystemSnapshot | None,
        *,
        on_chunk: Callable[[str], None],
        should_stop: Callable[[], bool],
    ) -> LocalAIMetrics:
        messages = [
            {
                "role": "system",
                "content": self._system_prompt(),
            },
            {
                "role": "system",
                "content": self._snapshot_context(
                    snapshot
                ),
            },
            *[
                {
                    "role": str(
                        message.get(
                            "role",
                            "user",
                        )
                    ),
                    "content": str(
                        message.get(
                            "content",
                            "",
                        )
                    ),
                }
                for message in history
                if str(
                    message.get(
                        "content",
                        "",
                    )
                ).strip()
            ],
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.25,
                "num_ctx": self.context_window,
                "num_predict": 1024,
            },
        }

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(
                payload
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        final_event: dict = {}

        try:
            with urllib.request.urlopen(
                request,
                timeout=240.0,
            ) as response:
                for raw_line in response:
                    if should_stop():
                        return LocalAIMetrics(
                            model=self.model,
                            prompt_tokens=0,
                            generated_tokens=0,
                            total_seconds=0.0,
                            stopped=True,
                        )

                    line = raw_line.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()

                    if not line:
                        continue

                    event = json.loads(line)
                    final_event = event

                    message = event.get(
                        "message",
                        {},
                    )
                    content = str(
                        message.get(
                            "content",
                            "",
                        )
                    )

                    if content:
                        on_chunk(content)

                    if event.get("done"):
                        break

        except urllib.error.HTTPError as error:
            detail = error.read().decode(
                "utf-8",
                errors="replace",
            )

            raise LocalAIError(
                f"Ollama HTTP {error.code}: {detail}"
            ) from error

        except urllib.error.URLError as error:
            raise LocalAIError(
                "Ollama connection failed: "
                f"{error.reason}"
            ) from error

        except (
            OSError,
            TimeoutError,
            json.JSONDecodeError,
        ) as error:
            raise LocalAIError(
                f"{type(error).__name__}: {error}"
            ) from error

        return LocalAIMetrics(
            model=str(
                final_event.get(
                    "model",
                    self.model,
                )
            ),
            prompt_tokens=int(
                final_event.get(
                    "prompt_eval_count",
                    0,
                )
                or 0
            ),
            generated_tokens=int(
                final_event.get(
                    "eval_count",
                    0,
                )
                or 0
            ),
            total_seconds=(
                float(
                    final_event.get(
                        "total_duration",
                        0,
                    )
                    or 0
                )
                / 1_000_000_000
            ),
            stopped=False,
        )

    def _get_json(
        self,
        path: str,
        *,
        timeout: float,
    ) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
            ) as response:
                payload = json.load(response)

        except urllib.error.HTTPError as error:
            raise LocalAIError(
                f"Ollama HTTP {error.code} for {path}"
            ) from error

        except urllib.error.URLError as error:
            raise LocalAIError(
                f"Ollama unavailable: {error.reason}"
            ) from error

        except (
            OSError,
            TimeoutError,
            json.JSONDecodeError,
        ) as error:
            raise LocalAIError(
                f"{type(error).__name__}: {error}"
            ) from error

        if not isinstance(payload, dict):
            raise LocalAIError(
                f"Invalid Ollama response for {path}"
            )

        return payload

    @staticmethod
    def _model_names(
        raw_models: object,
    ) -> tuple[str, ...]:
        if not isinstance(raw_models, list):
            return ()

        names: list[str] = []

        for item in raw_models:
            if not isinstance(item, dict):
                continue

            value = item.get(
                "name",
                item.get(
                    "model",
                    "",
                ),
            )

            name = str(value).strip()

            if name:
                names.append(name)

        return tuple(names)

    @staticmethod
    def _matches_model(
        expected: str,
        available: tuple[str, ...],
    ) -> bool:
        if ":" in expected:
            return expected in available

        expected_name = expected.split(
            ":",
            1,
        )[0]

        return any(
            candidate.split(
                ":",
                1,
            )[0] == expected_name
            for candidate in available
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are HELM AI, a local engineering and "
            "diagnostic assistant inside a CyberDeck "
            "control interface. Answer in the language "
            "used by the user; default to Polish. "
            "Be direct, technically precise and practical. "
            "You receive a read-only HELM telemetry snapshot. "
            "Never claim that you executed a command, changed "
            "a file, controlled hardware, accessed the internet "
            "or inspected anything not present in the supplied "
            "context. Clearly separate measured facts, likely "
            "causes and recommended next steps. Missing telemetry, "
            "N/A values and statuses such as SMART UNAVAILABLE mean "
            "that HELM could not obtain the measurement; they are not "
            "evidence of hardware failure. Do not recommend replacing "
            "hardware or claim risk of data loss unless the supplied "
            "context contains supporting evidence such as SMART FAILED, "
            "I/O errors, repeated disconnects, filesystem corruption or "
            "other concrete symptoms. Ask for an appropriate diagnostic "
            "check when evidence is insufficient. For risky electrical, "
            "battery or system operations, include concise safety checks."
        )

    @classmethod
    def _snapshot_context(
        cls,
        snapshot: SystemSnapshot | None,
    ) -> str:
        if snapshot is None:
            return (
                "HELM LIVE TELEMETRY\n"
                "No snapshot is currently available."
            )

        storage = snapshot.storage
        devices = snapshot.devices
        projects = snapshot.projects

        drive_lines = [
            (
                f"/dev/{device.name}: {device.model}; "
                f"temperature="
                f"{cls._optional(device.temperature_c, '°C')}; "
                f"SMART={device.smart_status}"
            )
            for device in storage.devices[:8]
        ]

        serial_lines = [
            (
                f"{device.path}: driver={device.driver}; "
                f"device={device.usb_manufacturer} "
                f"{device.usb_product}"
            )
            for device in devices.serial_devices[:8]
        ]

        project_lines = [
            (
                f"{project.name}: "
                f"status={project.status}; "
                f"priority={project.priority}/5; "
                f"progress={project.progress}%; "
                f"next={project.next_action}"
            )
            for project in projects.projects[:10]
        ]

        lines = [
            "HELM LIVE TELEMETRY // READ ONLY",
            f"Updated: {snapshot.timestamp}",
            (
                f"Host: {snapshot.host}; "
                f"user={snapshot.user}; "
                f"OS={snapshot.os_name}; "
                f"kernel={snapshot.kernel}; "
                f"uptime={snapshot.uptime}"
            ),
            (
                f"CPU: usage={snapshot.cpu_usage:.1f}%; "
                f"temperature="
                f"{cls._optional(snapshot.cpu_temp, '°C')}"
            ),
            (
                f"GPU: usage="
                f"{cls._optional(snapshot.gpu_usage, '%')}; "
                f"temperature="
                f"{cls._optional(snapshot.gpu_temp, '°C')}; "
                f"memory_used="
                f"{cls._optional(snapshot.gpu_memory, ' MiB')}; "
                f"power="
                f"{cls._optional(snapshot.gpu_power, ' W')}"
            ),
            f"RAM: usage={snapshot.ram_usage:.1f}%",
            (
                f"Root filesystem: "
                f"used={storage.root_percent:.1f}%; "
                f"free={cls._format_bytes(storage.root_free)}; "
                f"read={cls._format_rate(storage.read_bps)}; "
                f"write={cls._format_rate(storage.write_bps)}"
            ),
            (
                f"Network: "
                f"interface={snapshot.network_interface}; "
                f"IPv4={snapshot.network_ip}; "
                f"online={snapshot.network_online}; "
                f"link={snapshot.network_link_speed} Mbps; "
                f"download="
                f"{cls._format_rate(snapshot.network_download_bps)}; "
                f"upload="
                f"{cls._format_rate(snapshot.network_upload_bps)}"
            ),
            (
                f"Devices: "
                f"USB={len(devices.usb_devices)}; "
                f"serial={len(devices.serial_devices)}"
            ),
            (
                f"Projects: total={len(projects.projects)}; "
                f"active={projects.active_count}; "
                f"blocked={projects.blocked_count}; "
                f"completed={projects.completed_count}; "
                f"average_progress="
                f"{projects.average_progress:.1f}%"
            ),
        ]

        if drive_lines:
            lines.extend(
                [
                    "Physical drives:",
                    *drive_lines,
                ]
            )

        if serial_lines:
            lines.extend(
                [
                    "Serial devices:",
                    *serial_lines,
                ]
            )

        if project_lines:
            lines.extend(
                [
                    "Project database:",
                    *project_lines,
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _optional(
        value: float | None,
        suffix: str,
    ) -> str:
        if value is None:
            return "N/A"

        return f"{value:.1f}{suffix}"

    @staticmethod
    def _format_rate(value: float) -> str:
        return (
            f"{LocalAIService._format_bytes(value)}/s"
        )

    @staticmethod
    def _format_bytes(value: float) -> str:
        size = float(value)

        for unit in (
            "B",
            "KiB",
            "MiB",
            "GiB",
            "TiB",
        ):
            if size < 1024 or unit == "TiB":
                return f"{size:.1f} {unit}"

            size /= 1024

        return "0 B"
