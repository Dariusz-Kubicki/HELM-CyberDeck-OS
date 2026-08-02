from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.runtime_data import RuntimeJsonStore


def require_items(payload: dict) -> None:
    items = payload.get("items")

    if not isinstance(items, list):
        raise ValueError("'items' must be a list.")


class RuntimeJsonStoreTests(unittest.TestCase):
    def test_migrates_legacy_file_without_deleting_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy.json"
            target = root / "data" / "runtime.json"

            legacy.write_text(
                '{"items": ["legacy"]}\n',
                encoding="utf-8",
            )

            store = RuntimeJsonStore(
                filename="runtime.json",
                target_path=target,
                legacy_path=legacy,
                default_factory=lambda: {"items": []},
            )

            payload = store.read(require_items)

            self.assertEqual(
                payload,
                {"items": ["legacy"]},
            )
            self.assertTrue(target.is_file())
            self.assertTrue(legacy.is_file())

    def test_missing_file_is_created_from_example(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            example = root / "example.json"
            target = root / "data" / "runtime.json"

            example.write_text(
                '{"items": ["example"]}\n',
                encoding="utf-8",
            )

            store = RuntimeJsonStore(
                filename="runtime.json",
                target_path=target,
                example_path=example,
                default_factory=lambda: {"items": []},
            )

            self.assertEqual(
                store.read(require_items),
                {"items": ["example"]},
            )

    def test_invalid_file_is_quarantined_and_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "data" / "runtime.json"

            store = RuntimeJsonStore(
                filename="runtime.json",
                target_path=target,
                default_factory=lambda: {"items": ["safe"]},
            )

            store.write(
                {"items": ["last-good"]},
                require_items,
            )

            target.write_text(
                "{broken",
                encoding="utf-8",
            )

            self.assertEqual(
                store.read(require_items),
                {"items": ["last-good"]},
            )

            broken = tuple(
                store.recovery_directory.glob(
                    "runtime-*.broken.json"
                )
            )

            self.assertEqual(len(broken), 1)

    def test_write_updates_target_and_last_good(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "data" / "runtime.json"

            store = RuntimeJsonStore(
                filename="runtime.json",
                target_path=target,
                default_factory=lambda: {"items": []},
            )

            store.write(
                {"items": ["current"]},
                require_items,
            )

            target_payload = json.loads(
                target.read_text(encoding="utf-8")
            )

            backup_payload = json.loads(
                store.last_good_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                target_payload,
                {"items": ["current"]},
            )

            self.assertEqual(
                backup_payload,
                {"items": ["current"]},
            )


if __name__ == "__main__":
    unittest.main()

