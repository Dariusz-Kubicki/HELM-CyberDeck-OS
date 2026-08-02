from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modules.projects import ProjectMonitor
from services.project_service import ProjectService
from services.settings_service import SettingsService


SETTINGS_PAYLOAD = """{
  "telemetry_interval": 2.0,
  "start_screen": "projects",
  "navigation_logging": false,
  "log_rows": 500,
  "ai_model": "qwen3:8b",
  "ai_context_window": 8192,
  "ai_keep_alive": "30m"
}
"""

PROJECTS_PAYLOAD = """{
  "projects": [
    {
      "id": "test-project",
      "name": "Test Project",
      "category": "SOFTWARE",
      "status": "ACTIVE",
      "priority": 4,
      "progress": 25,
      "tech": ["Python"],
      "next_action": "Run tests",
      "description": "Runtime migration test",
      "path": "",
      "github_url": "",
      "updated_at": "2026-08-01T20:00:00"
    }
  ]
}
"""


class RuntimeServicesTests(unittest.TestCase):
    def test_settings_migrate_legacy_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "data" / "settings.json"
            legacy = root / "legacy" / "settings.json"
            example = root / "examples" / "settings.json"

            legacy.parent.mkdir(parents=True)
            example.parent.mkdir(parents=True)

            legacy.write_text(
                SETTINGS_PAYLOAD,
                encoding="utf-8",
            )
            example.write_text(
                "{}\n",
                encoding="utf-8",
            )

            service = SettingsService(
                path=target,
                legacy_path=legacy,
                example_path=example,
            )

            settings = service.load()

            self.assertEqual(
                settings.start_screen,
                "projects",
            )
            self.assertEqual(
                settings.telemetry_interval,
                2.0,
            )
            self.assertTrue(target.is_file())
            self.assertTrue(legacy.is_file())

    def test_settings_recover_corrupt_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "data" / "settings.json"
            example = root / "examples" / "settings.json"

            example.parent.mkdir(parents=True)
            example.write_text(
                SETTINGS_PAYLOAD,
                encoding="utf-8",
            )

            service = SettingsService(
                path=target,
                example_path=example,
            )

            initial = service.load()

            target.write_text(
                "{broken",
                encoding="utf-8",
            )

            recovered = service.load()

            self.assertEqual(
                recovered,
                initial,
            )

            broken = tuple(
                (
                    target.parent / "recovery"
                ).glob("settings-*.broken.json")
            )

            self.assertEqual(len(broken), 1)

    def test_project_service_migrates_and_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "data" / "projects.json"
            legacy = root / "legacy" / "projects.json"
            example = root / "examples" / "projects.json"

            legacy.parent.mkdir(parents=True)
            example.parent.mkdir(parents=True)

            legacy.write_text(
                PROJECTS_PAYLOAD,
                encoding="utf-8",
            )
            example.write_text(
                '{"projects": []}\n',
                encoding="utf-8",
            )

            service = ProjectService(
                config_path=target,
                legacy_path=legacy,
                example_path=example,
            )

            result = service.create_project(
                {
                    "name": "Second Project",
                    "category": "EMBEDDED",
                    "status": "PLANNING",
                    "priority": 3,
                    "progress": 5,
                }
            )

            self.assertEqual(
                result.status,
                "CREATED",
            )
            self.assertTrue(target.is_file())
            self.assertTrue(legacy.is_file())

            payload = json.loads(
                target.read_text(encoding="utf-8")
            )

            self.assertEqual(
                len(payload["projects"]),
                2,
            )

    def test_project_monitor_recovers_corrupt_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "data" / "projects.json"
            example = root / "examples" / "projects.json"

            example.parent.mkdir(parents=True)
            example.write_text(
                PROJECTS_PAYLOAD,
                encoding="utf-8",
            )

            monitor = ProjectMonitor(
                config_path=target,
                example_path=example,
            )

            initial = monitor.sample()

            self.assertIsNone(initial.error)
            self.assertEqual(
                len(initial.projects),
                1,
            )

            target.write_text(
                "[]",
                encoding="utf-8",
            )

            monitor._next_refresh = 0.0
            monitor._last_modified_ns = None

            recovered = monitor.sample()

            self.assertIsNone(recovered.error)
            self.assertEqual(
                len(recovered.projects),
                1,
            )

            broken = tuple(
                (
                    target.parent / "recovery"
                ).glob("projects-*.broken.json")
            )

            self.assertEqual(len(broken), 1)


if __name__ == "__main__":
    unittest.main()
