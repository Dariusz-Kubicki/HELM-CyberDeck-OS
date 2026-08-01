from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.mode_service import ModeService


MODE_PAYLOAD = """{
  "modes": [
    {
      "id": "test",
      "name": "TEST",
      "description": "Test workspace",
      "telemetry_interval": 1.0,
      "target_screen": "system",
      "navigation_logging": true,
      "workload_profile": "BALANCED",
      "power_profile": "unchanged",
      "objective": "Test runtime storage",
      "features": [],
      "applications": []
    }
  ]
}
"""

STATE_PAYLOAD = """{
  "active_mode": "test"
}
"""


class ModeServiceRuntimeTests(unittest.TestCase):
    def make_service(
        self,
        root: Path,
        *,
        create_legacy: bool = False,
        create_examples: bool = True,
    ) -> ModeService:
        data = root / "data"
        repository = root / "repository"

        target_modes = data / "modes.json"
        target_state = data / "mode_state.json"

        legacy_modes = repository / "modes.json"
        legacy_state = repository / "mode_state.json"

        example_modes = repository / "modes.example.json"
        example_state = repository / "mode_state.example.json"

        repository.mkdir(
            parents=True,
            exist_ok=True,
        )

        if create_legacy:
            legacy_modes.write_text(
                MODE_PAYLOAD,
                encoding="utf-8",
            )
            legacy_state.write_text(
                STATE_PAYLOAD,
                encoding="utf-8",
            )

        if create_examples:
            example_modes.write_text(
                MODE_PAYLOAD,
                encoding="utf-8",
            )
            example_state.write_text(
                STATE_PAYLOAD,
                encoding="utf-8",
            )

        return ModeService(
            config_path=target_modes,
            state_path=target_state,
            legacy_config_path=legacy_modes,
            example_config_path=example_modes,
            legacy_state_path=legacy_state,
            example_state_path=example_state,
        )

    def test_migrates_legacy_modes_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = self.make_service(
                root,
                create_legacy=True,
            )

            modes = service.load_modes()
            active = service.load_active_mode()

            self.assertEqual(
                tuple(mode.mode_id for mode in modes),
                ("test",),
            )
            self.assertEqual(active, "test")
            self.assertTrue(service.config_path.is_file())
            self.assertTrue(service.state_path.is_file())
            self.assertTrue(
                (root / "repository" / "modes.json").is_file()
            )
            self.assertTrue(
                (
                    root
                    / "repository"
                    / "mode_state.json"
                ).is_file()
            )

    def test_missing_runtime_uses_examples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = self.make_service(root)

            self.assertEqual(
                service.load_modes()[0].mode_id,
                "test",
            )
            self.assertEqual(
                service.load_active_mode(),
                "test",
            )

    def test_corrupt_modes_recover_from_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = self.make_service(root)

            service.load_modes()

            service.config_path.write_text(
                "{broken",
                encoding="utf-8",
            )

            recovered = service.load_modes()

            self.assertEqual(
                recovered[0].mode_id,
                "test",
            )

            broken_files = tuple(
                (
                    service.config_path.parent
                    / "recovery"
                ).glob("modes-*.broken.json")
            )

            self.assertEqual(len(broken_files), 1)

    def test_corrupt_state_recovers_from_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = self.make_service(root)

            self.assertEqual(
                service.load_active_mode(),
                "test",
            )

            service.state_path.write_text(
                "[]",
                encoding="utf-8",
            )

            self.assertEqual(
                service.load_active_mode(),
                "test",
            )

            broken_files = tuple(
                (
                    service.state_path.parent
                    / "recovery"
                ).glob("mode_state-*.broken.json")
            )

            self.assertEqual(len(broken_files), 1)


if __name__ == "__main__":
    unittest.main()
