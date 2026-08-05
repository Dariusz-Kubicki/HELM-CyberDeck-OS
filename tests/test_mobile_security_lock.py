import json
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]

SOURCE_DIR = (
    REPOSITORY
    / "mobile"
    / "plasma"
    / "lockscreen"
)

OVERLAY = SOURCE_DIR / "HELMOverlay.qml"
MANIFEST = SOURCE_DIR / "lockscreen.json"

APPLY = (
    REPOSITORY
    / "scripts"
    / "mobile"
    / "apply-stage4b-lockscreen.sh"
)

RESTORE = (
    REPOSITORY
    / "scripts"
    / "mobile"
    / "restore-stage4b-lockscreen.sh"
)


class MobileSecurityLockTests(unittest.TestCase):
    def test_manifest_safety_contract(self) -> None:
        payload = json.loads(
            MANIFEST.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload["stage"],
            "4b-security-lock",
        )

        self.assertFalse(
            payload["authentication"]["modified"]
        )

        behavior = payload["behavior"]

        self.assertFalse(
            behavior[
                "automatic_lock_settings_modified"
            ]
        )

        self.assertFalse(
            behavior[
                "authentication_flow_modified"
            ]
        )

        self.assertFalse(
            behavior[
                "session_unlocking_modified"
            ]
        )

    def test_approved_overlay_layout(self) -> None:
        text = OVERLAY.read_text(
            encoding="utf-8"
        )

        required = (
            "HELM MOBILE // SECURITY LOCK",
            "AUTHENTICATION REQUIRED",
            'color: "#FF02070B"',
            'color: "#FC02070B"',
            "anchors.bottomMargin: 132",
            "STATUS: AWAITING OPERATOR",
        )

        for marker in required:
            self.assertIn(marker, text)

        self.assertEqual(
            text.count("{"),
            text.count("}"),
        )

    def test_controlled_tools_exist(self) -> None:
        self.assertTrue(APPLY.is_file())
        self.assertTrue(RESTORE.is_file())

        self.assertIn(
            "HELM MOBILE SECURITY OVERLAY",
            APPLY.read_text(
                encoding="utf-8"
            ),
        )

        self.assertIn(
            "4b-security-lock",
            RESTORE.read_text(
                encoding="utf-8"
            ),
        )


if __name__ == "__main__":
    unittest.main()
