import configparser
import json
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPOSITORY / "mobile" / "sddm"
THEME = SOURCE_DIR / "helm-mobile"
MANIFEST = SOURCE_DIR / "access-gate.json"
MAIN_QML = THEME / "Main.qml"
METADATA = THEME / "metadata.desktop"
THEME_CONFIG = THEME / "theme.conf"
WALLPAPER = THEME / "wallpaper.svg"
APPLY = REPOSITORY / "scripts" / "mobile" / "apply-stage4c-sddm-access-gate.sh"
RESTORE = REPOSITORY / "scripts" / "mobile" / "restore-stage4c-sddm-access-gate.sh"
DOCTOR = REPOSITORY / "scripts" / "mobile" / "doctor.sh"
DOCUMENTATION = REPOSITORY / "docs" / "mobile-access-gate.md"


class MobileAccessGateTests(unittest.TestCase):
    def test_manifest_safety_contract(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(payload["stage"], "4c-sddm-access-gate")
        self.assertEqual(payload["display_manager"]["service"], "sddm.service")
        self.assertEqual(payload["display_manager"]["qt_version"], 6)
        self.assertEqual(payload["display_manager"]["greeter"], "/usr/bin/sddm-greeter-qt6")
        self.assertEqual(payload["authentication"]["backend"], "native-sddm")
        self.assertFalse(payload["authentication"]["pam_modified"])
        self.assertFalse(payload["authentication"]["password_handling_modified"])
        self.assertFalse(payload["authentication"]["session_launch_modified"])
        self.assertFalse(payload["integration"]["plasma_login_manager_modified"])
        self.assertFalse(payload["integration"]["ld_preload_used"])
        self.assertFalse(payload["integration"]["binary_interposition_used"])
        self.assertFalse(payload["integration"]["qml_injection_used"])

    def test_two_layer_architecture(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        architecture = payload["architecture"]
        self.assertTrue(architecture["interfaces_are_independent"])
        self.assertEqual(architecture["access_gate"]["provider"], "sddm")
        self.assertEqual(architecture["security_lock"]["provider"], "kscreenlocker")

    def test_qt6_theme_metadata(self) -> None:
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.optionxform = str
        with METADATA.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
        self.assertEqual(parser.sections().count("SddmGreeterTheme"), 1)
        section = parser["SddmGreeterTheme"]
        self.assertEqual(section["MainScript"], "Main.qml")
        self.assertEqual(section["ConfigFile"], "theme.conf")
        self.assertEqual(section["QtVersion"], "6")

    def test_approved_access_gate_layout(self) -> None:
        text = MAIN_QML.read_text(encoding="utf-8")
        required = (
            "HELM MOBILE // ACCESS GATE",
            "AUTHENTICATE",
            "sddm.login(",
            "// HELM-STYLE: access-gate-controls-v2",
            "id: sessionBox",
            "id: suspendButton",
            "id: rebootButton",
            "id: shutdownButton",
            "sddm.canSuspend",
            "sddm.canReboot",
            "sddm.canPowerOff",
        )
        for marker in required:
            self.assertIn(marker, text)
        self.assertNotIn("HELM-PREVIEW-ONLY", text)
        self.assertEqual(text.count("{"), text.count("}"))

    def test_required_assets_exist(self) -> None:
        for path in (MAIN_QML, METADATA, THEME_CONFIG, WALLPAPER):
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)

    def test_controlled_tools_exist(self) -> None:
        self.assertTrue(APPLY.is_file())
        self.assertTrue(RESTORE.is_file())
        apply_text = APPLY.read_text(encoding="utf-8")
        restore_text = RESTORE.read_text(encoding="utf-8")
        self.assertIn("systemctl enable", apply_text)
        self.assertIn("sddm.service", apply_text)
        self.assertIn("plasmalogin.service", restore_text)
        self.assertNotIn("systemctl restart", apply_text)
        for dangerous in ("export LD_PRELOAD", "Environment=LD_PRELOAD", "/etc/pam.d/"):
            self.assertNotIn(dangerous, apply_text)
            self.assertNotIn(dangerous, restore_text)

    def test_mobile_doctor_understands_stage4c(self) -> None:
        text = DOCTOR.read_text(encoding="utf-8")
        self.assertIn("HELM Mobile Access Gate runtime", text)
        self.assertIn("Access Gate real login verified", text)
        self.assertIn("org.freedesktop.ScreenSaver.GetActive", text)
        self.assertNotIn("SDDM is already enabled before Access Gate installation", text)

    def test_documentation_separates_lock_and_login(self) -> None:
        text = DOCUMENTATION.read_text(encoding="utf-8")
        self.assertIn("Stage 4B — Security Lock", text)
        self.assertIn("Stage 4C — Access Gate", text)
        self.assertIn("KScreenLocker", text)
        self.assertIn("SDDM", text)


if __name__ == "__main__":
    unittest.main()
