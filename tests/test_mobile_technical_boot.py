import json
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY / "mobile" / "boot" / "technical-boot.json"
DOCUMENTATION = REPOSITORY / "docs" / "mobile-technical-boot.md"
AUDIT = REPOSITORY / "scripts" / "mobile" / "audit-stage4d-technical-boot.sh"
DOCTOR = REPOSITORY / "scripts" / "mobile" / "doctor.sh"

class MobileTechnicalBootTests(unittest.TestCase):
    def test_manifest_preserves_verbose_boot(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(payload["stage"], "4d-technical-boot")
        self.assertEqual(payload["bootloader"]["selected_entry"], "arch-linux.efi")
        self.assertEqual(payload["bootloader"]["active_uki"], "/boot/EFI/Linux/arch-linux.efi")
        self.assertTrue(payload["uki"]["arch_splash_embedded"])
        self.assertFalse(payload["kernel_command_line"]["quiet"])
        self.assertFalse(payload["kernel_command_line"]["splash"])
        self.assertTrue(payload["kernel_command_line"]["preserve_verbose_output"])
        self.assertFalse(payload["initramfs"]["plymouth_hook"])
        self.assertTrue(payload["initramfs"]["preserve_console_luks_prompt"])

    def test_stage4d_is_non_destructive(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for key, value in payload["safety"].items():
            self.assertFalse(value, key)
        checksum = payload["uki"]["baseline_sha256"]
        self.assertEqual(len(checksum), 64)
        int(checksum, 16)

    def test_documentation_explains_splash_distinction(self) -> None:
        text = DOCUMENTATION.read_text(encoding="utf-8")
        for marker in (
            "HELM Mobile Technical Boot",
            "splash-arch.bmp",
            "not the kernel command-line `splash`",
            "block -> encrypt -> filesystems",
            "Never identify the active UKI by alphabetical",
            "must not silently",
        ):
            self.assertIn(marker, text)

    def test_audit_tool_is_read_only(self) -> None:
        text = AUDIT.read_text(encoding="utf-8")
        for marker in (
            "READ-ONLY AUDIT",
            "Current Entry: arch-linux.efi",
            "splash-arch.bmp",
            "No UKI was rebuilt.",
            "No reboot was requested.",
        ):
            self.assertIn(marker, text)
        for forbidden in (
            "mkinitcpio -P",
            "bootctl update",
            "bootctl install",
            "plymouth-set-default-theme -R",
            "systemctl reboot",
            "reboot now",
        ):
            self.assertNotIn(forbidden, text)

    def test_mobile_doctor_understands_stage4d(self) -> None:
        text = DOCTOR.read_text(encoding="utf-8")
        for marker in (
            "HELM Mobile Technical Boot manifest",
            "Technical Boot active UKI",
            "Technical Boot verbose command line",
            "Technical Boot Arch UKI splash",
            "Technical Boot console LUKS flow",
            "Technical Boot recovery baseline",
        ):
            self.assertIn(marker, text)

if __name__ == "__main__":
    unittest.main()
