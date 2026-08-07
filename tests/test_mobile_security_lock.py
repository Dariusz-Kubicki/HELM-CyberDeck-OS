import json
import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]

SOURCE_DIR = (
    REPOSITORY
    / "mobile"
    / "plasma"
    / "lockscreen"
)

LOCK_SCREEN = SOURCE_DIR / "LockScreen.qml"
LOCK_UI = SOURCE_DIR / "LockScreenUi.qml"
MAIN_BLOCK = SOURCE_DIR / "MainBlock.qml"
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

        self.assertEqual(
            payload["revision"],
            "2.1",
        )

        self.assertFalse(
            payload["authentication"]["modified"]
        )

        self.assertTrue(
            payload["authentication"][
                "native_authenticator_preserved"
            ]
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

        validation = payload["validation"]

        self.assertTrue(
            validation["testing_preview_verified"]
        )

        self.assertTrue(
            validation["real_win_l_verified"]
        )

        self.assertTrue(
            validation[
                "real_password_unlock_verified"
            ]
        )

    def test_approved_v21_sources_exist(self) -> None:
        for path in (
            LOCK_SCREEN,
            LOCK_UI,
            MAIN_BLOCK,
            OVERLAY,
        ):
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)

    def test_native_authentication_flow_is_preserved(
        self,
    ) -> None:
        lock_ui = LOCK_UI.read_text(
            encoding="utf-8"
        )

        main_block = MAIN_BLOCK.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "authenticator.respond(password)",
            lock_ui,
        )

        self.assertIn(
            "signal passwordResult(string password)",
            main_block,
        )

        self.assertIn(
            "passwordResult(password)",
            main_block,
        )

        self.assertIn(
            "enabled: !authenticator.graceLocked",
            main_block,
        )

    def test_v21_visual_contract(self) -> None:
        lock_ui = LOCK_UI.read_text(
            encoding="utf-8"
        )

        main_block = MAIN_BLOCK.read_text(
            encoding="utf-8"
        )

        overlay = OVERLAY.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "showUserList: false",
            lock_ui,
        )

        self.assertIn(
            "footer is intentionally hidden",
            lock_ui,
        )

        self.assertIn(
            "action hidden for clean lock UI",
            lock_ui,
        )

        self.assertIn(
            "// HELM-STYLE: "
            "security-lock-controls-v2",
            main_block,
        )

        self.assertIn(
            'text: "AUTHENTICATE"',
            main_block,
        )

        required_overlay = (
            "HELM MOBILE // SECURITY LOCK",
            "SECURE SESSION CHANNEL",
            "NATIVE KSCREENLOCKER CREDENTIAL FLOW",
            'color: "#FF02070B"',
            'color: "#FC02070B"',
            "anchors.bottomMargin: 132",
        )

        for marker in required_overlay:
            self.assertIn(marker, overlay)

    def test_overlay_integration_is_single(self) -> None:
        text = LOCK_SCREEN.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "HELM MOBILE SECURITY OVERLAY",
            text,
        )

        self.assertEqual(
            text.count("HELMOverlay {"),
            1,
        )

    def test_kde_license_headers_are_preserved(self) -> None:
        for path in (
            LOCK_SCREEN,
            LOCK_UI,
            MAIN_BLOCK,
        ):
            text = path.read_text(
                encoding="utf-8"
            )

            self.assertRegex(
                text,
                re.compile(
                    r"SPDX-License-Identifier:"
                ),
            )

    def test_controlled_tools_exist(self) -> None:
        self.assertTrue(APPLY.is_file())
        self.assertTrue(RESTORE.is_file())

        apply_text = APPLY.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "KDE baseline changed",
            apply_text,
        )

        self.assertIn(
            "LockScreenUi.qml",
            apply_text,
        )

        self.assertIn(
            "MainBlock.qml",
            apply_text,
        )

        self.assertNotIn(
            "systemctl restart",
            apply_text,
        )

        # The apply tool intentionally contains the names of unsafe
        # mechanisms inside its rejection scanner. Test for actual use,
        # not for the presence of those names in the safety check.
        self.assertIn(
            "libhelm-plasmalogin-mainqml",
            apply_text,
        )

        for forbidden in (
            "export LD_PRELOAD",
            "Environment=LD_PRELOAD",
            "LD_PRELOAD=",
            "/etc/pam.d/",
            "HELM_PLASMA_LOGIN_MAIN_QML=",
            "libhelm-plasmalogin-mainqml.so",
        ):
            self.assertNotIn(
                forbidden,
                apply_text,
            )

        self.assertIn(
            "4b-security-lock",
            RESTORE.read_text(
                encoding="utf-8"
            ),
        )


if __name__ == "__main__":
    unittest.main()
