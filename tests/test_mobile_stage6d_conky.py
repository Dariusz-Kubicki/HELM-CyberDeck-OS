from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MobileStage6DConkyTests(unittest.TestCase):
    def test_manifest_contract(self) -> None:
        p = json.loads((ROOT / "mobile/conky/mobile-hud.json").read_text(encoding="utf-8"))
        self.assertEqual(p["stage"], "6d-mobile-conky-hud")
        self.assertEqual(p["window"]["alignment"], "top_right")
        self.assertEqual(p["window"]["width"], 310)
        self.assertEqual(p["status"], "visual-approved")
        self.assertFalse(p["window"]["visibility_policy"]["below"])
        self.assertIn("battery", p["telemetry"])
        self.assertIn("amdgpu", p["telemetry"])
        self.assertFalse(any(p["safety"].values()))

    def test_conky_visual_contract(self) -> None:
        text = (ROOT / "mobile/conky/helm-mobile.conf").read_text(encoding="utf-8")
        for marker in ("alignment = 'top_right'", "MOBILE NODE", "GPU CORE", "ROOT STORAGE", "HELMMobileNode"):
            self.assertIn(marker, text)
        self.assertIn("helm-mobile-status power", text)
        self.assertIn("helm-mobile-status battery-percent", text)
        self.assertNotIn("DESKTOP NODE", text)
        self.assertNotIn("undecorated,below,sticky", text)
        self.assertIn("undecorated,sticky,skip_taskbar,skip_pager", text)

    def test_helper_is_mobile_aware(self) -> None:
        text = (ROOT / "mobile/conky/helm-mobile-status").read_text(encoding="utf-8")
        for marker in ("powerprofilesctl get", "gpu_busy_percent", "BAT*", "BATTERY", "battery-percent", "network_state"):
            self.assertIn(marker, text)
        self.assertNotIn("nvidia-smi", text)

    def test_autostart_is_templated(self) -> None:
        text = (ROOT / "mobile/autostart/helm-mobile-node.desktop").read_text(encoding="utf-8")
        self.assertIn("Exec=__HOME__/.local/bin/helm-mobile-start", text)
        self.assertIn("OnlyShowIn=KDE;", text)

    def test_apply_restore_are_reversible_and_non_privileged(self) -> None:
        apply = (ROOT / "scripts/mobile/apply-stage6d-mobile-hud.sh").read_text(encoding="utf-8")
        restore = (ROOT / "scripts/mobile/restore-stage6d-mobile-hud.sh").read_text(encoding="utf-8")
        for forbidden in ("sudo ", "systemctl restart", "kwriteconfig6", "/proc/acpi/wakeup", "powerprofilesctl set"):
            self.assertNotIn(forbidden, apply)
            self.assertNotIn(forbidden, restore)
        self.assertIn("stage6d-mobile-hud-last-apply.json", apply)
        self.assertIn("stage6d-mobile-hud-last-apply.json", restore)

    def test_start_helper_targets_only_mobile_config(self) -> None:
        text = (ROOT / "mobile/conky/helm-mobile-start").read_text(encoding="utf-8")
        self.assertIn("helm-mobile.conf", text)
        self.assertIn("pgrep -u", text)
        self.assertIn("conky -d -c", text)

if __name__ == "__main__":
    unittest.main()
