from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LogEntry:
    timestamp: str
    level: str
    source: str
    message: str


class LogService:
    """Persistent HELM event log with simple file rotation."""

    MAX_FILE_SIZE = 1_000_000
    BACKUP_COUNT = 3

    VALID_LEVELS = {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }

    def __init__(self, log_path: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[1]

        self.log_path = log_path or project_root / "logs" / "helm.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)

    def debug(self, source: str, message: str) -> None:
        self.write("DEBUG", source, message)

    def info(self, source: str, message: str) -> None:
        self.write("INFO", source, message)

    def warning(self, source: str, message: str) -> None:
        self.write("WARNING", source, message)

    def error(self, source: str, message: str) -> None:
        self.write("ERROR", source, message)

    def critical(self, source: str, message: str) -> None:
        self.write("CRITICAL", source, message)

    def write(self, level: str, source: str, message: str) -> None:
        normalized_level = level.upper().strip()

        if normalized_level not in self.VALID_LEVELS:
            normalized_level = "INFO"

        safe_source = self._sanitize(source or "HELM")
        safe_message = self._sanitize(message)

        self._rotate_if_needed()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                f"{timestamp}|{normalized_level}|"
                f"{safe_source}|{safe_message}\n"
            )

    def tail(self, limit: int = 200) -> tuple[LogEntry, ...]:
        safe_limit = max(1, min(int(limit), 1000))

        try:
            lines = self.log_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError:
            return ()

        entries: list[LogEntry] = []

        for line in lines[-safe_limit:]:
            parts = line.split("|", 3)

            if len(parts) != 4:
                continue

            timestamp, level, source, message = parts

            entries.append(
                LogEntry(
                    timestamp=timestamp,
                    level=level,
                    source=source,
                    message=message,
                )
            )

        return tuple(entries)

    def clear(self) -> None:
        self.log_path.write_text("", encoding="utf-8")

    def _rotate_if_needed(self) -> None:
        try:
            current_size = self.log_path.stat().st_size
        except OSError:
            current_size = 0

        if current_size < self.MAX_FILE_SIZE:
            return

        oldest_backup = self.log_path.with_suffix(
            f"{self.log_path.suffix}.{self.BACKUP_COUNT}"
        )

        try:
            oldest_backup.unlink(missing_ok=True)
        except OSError:
            pass

        for number in range(self.BACKUP_COUNT - 1, 0, -1):
            source = self.log_path.with_suffix(
                f"{self.log_path.suffix}.{number}"
            )
            destination = self.log_path.with_suffix(
                f"{self.log_path.suffix}.{number + 1}"
            )

            try:
                if source.exists():
                    source.replace(destination)
            except OSError:
                continue

        first_backup = self.log_path.with_suffix(
            f"{self.log_path.suffix}.1"
        )

        try:
            self.log_path.replace(first_backup)
        except OSError:
            return

        self.log_path.touch(exist_ok=True)

    @staticmethod
    def _sanitize(value: str) -> str:
        return (
            str(value)
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("|", "/")
            .strip()
        )
