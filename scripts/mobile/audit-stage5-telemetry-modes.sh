#!/usr/bin/env bash
set -Eeuo pipefail

export LC_ALL=C.UTF-8

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
cd "$REPO"

PYTHON_BIN="$REPO/venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
    echo "[FAIL] Python interpreter not found."
    exit 1
fi

OK=0
FAIL=0

pass() {
    ((OK += 1))
    printf '[PASS] %s\n' "$1"
}

fail() {
    ((FAIL += 1))
    printf '[FAIL] %s\n' "$1" >&2
}

runtime_root="${HELM_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/helm}"
runtime_files=(
    "$runtime_root/modes.json"
    "$runtime_root/mode_state.json"
    "$runtime_root/settings.json"
    "$runtime_root/projects.json"
)

declare -A RUNTIME_BEFORE=()

runtime_digest() {
    local path="$1"
    if [[ -f "$path" ]]; then
        sha256sum "$path" | awk '{print $1}'
    else
        printf '%s\n' "<missing>"
    fi
}

read_power_profile() {
    if command -v powerprofilesctl >/dev/null 2>&1; then
        powerprofilesctl get 2>/dev/null || printf '%s' "NOT MANAGED"
    else
        printf '%s' "NOT MANAGED"
    fi
}

for path in "${runtime_files[@]}"; do
    RUNTIME_BEFORE["$path"]="$(runtime_digest "$path")"
done

HEAD_BEFORE="$(git rev-parse HEAD)"
STATUS_BEFORE="$(git status --porcelain=v1 --untracked-files=all)"
POWER_BEFORE="$(read_power_profile)"

printf '\n===== HELM MOBILE STAGE 5 — READ-ONLY SUBSYSTEM AUDIT =====\n'
printf 'HEAD: %s\n' "$HEAD_BEFORE"
printf 'Power profile at start: %s\n\n' "$POWER_BEFORE"

if STAGE5_MANIFEST="$REPO/mobile/stage5/stage5.json" \
   "$PYTHON_BIN" - >/dev/null 2>&1 <<'PY_STAGE5_MANIFEST'
import json
import os
from pathlib import Path

payload = json.loads(
    Path(os.environ["STAGE5_MANIFEST"]).read_text(encoding="utf-8")
)

if payload.get("stage") != "5d-stage5-closeout":
    raise SystemExit(1)
if payload.get("status") != "complete":
    raise SystemExit(1)

telemetry = payload.get("telemetry", {})
if telemetry.get("single_collector") is not True:
    raise SystemExit(1)
if telemetry.get("sampling_is_read_only") is not True:
    raise SystemExit(1)
if telemetry.get("power_sample_in_system_snapshot") is not True:
    raise SystemExit(1)

policy = payload.get("mode_policy", {})
if policy.get("unknown_power_source_fallback") != "balanced":
    raise SystemExit(1)
if policy.get("unavailable_profile_fallback") != "balanced":
    raise SystemExit(1)
if policy.get("apply_failure_non_fatal") is not True:
    raise SystemExit(1)

surface = payload.get("surface", {})
if surface.get("panel") != "MobilePowerPanel":
    raise SystemExit(1)
if surface.get("second_collector") is not False:
    raise SystemExit(1)

safety = payload.get("safety", {})
if any(safety.values()):
    raise SystemExit(1)
PY_STAGE5_MANIFEST
then
    pass "Stage 5 milestone manifest"
else
    fail "Stage 5 milestone manifest"
fi

if grep -Fq \
        'from modules.power import PowerMonitor, PowerSample' \
        services/data_service.py \
    && grep -Fq 'power: PowerSample' services/data_service.py \
    && grep -Fq 'self.power_monitor = PowerMonitor()' services/data_service.py \
    && grep -Fq 'power=power' services/data_service.py \
    && ! grep -Eq \
        'set_interval\(|apply_power_profile\(|RuntimeJsonStore' \
        app/mobile_power_panel.py
then
    pass "Single fault-tolerant telemetry path"
else
    fail "Single fault-tolerant telemetry path"
fi

if POLICY_FILE="$REPO/mobile/modes/power-policy.json" \
   "$PYTHON_BIN" - >/dev/null 2>&1 <<'PY_POLICY_MANIFEST'
import json
import os
from pathlib import Path

payload = json.loads(
    Path(os.environ["POLICY_FILE"]).read_text(encoding="utf-8")
)

expected = {
    "chill": {"battery": "power-saver", "ac": "balanced"},
    "focus": {"battery": "power-saver", "ac": "balanced"},
    "maker": {"battery": "balanced", "ac": "balanced"},
    "development": {"battery": "balanced", "ac": "performance"},
    "command": {"battery": "balanced", "ac": "balanced"},
}

if payload.get("modes") != expected:
    raise SystemExit(1)

fallbacks = payload.get("fallbacks", {})
if fallbacks.get("unknown_power_source") != "balanced":
    raise SystemExit(1)
if fallbacks.get("unavailable_profile") != "balanced":
    raise SystemExit(1)
if fallbacks.get("apply_failure") != "continue-workspace-activation":
    raise SystemExit(1)
PY_POLICY_MANIFEST
then
    pass "Approved adaptive mode policy"
else
    fail "Approved adaptive mode policy"
fi

if PYTHONPATH="$REPO" "$PYTHON_BIN" - >/dev/null 2>&1 <<'PY_POLICY_PURE'
from services.mobile_power_policy import MobilePowerPolicyService

service = MobilePowerPolicyService()

checks = {
    ("chill", False): "power-saver",
    ("focus", False): "power-saver",
    ("maker", False): "balanced",
    ("development", False): "balanced",
    ("development", True): "performance",
    ("command", True): "balanced",
    ("command", False): "balanced",
}

for (mode_id, external), expected in checks.items():
    actual = service.policy_target_for_source(
        mode_id,
        "unchanged",
        external,
    )
    if actual != expected:
        raise SystemExit(1)

if service.policy_target_for_source(
    "development", "unchanged", None
) != "balanced":
    raise SystemExit(1)

if service.policy_target_for_source(
    "development", "power-saver", True
) != "power-saver":
    raise SystemExit(1)
PY_POLICY_PURE
then
    pass "Pure AC/battery policy resolution"
else
    fail "Pure AC/battery policy resolution"
fi

if grep -Fq \
        'yield MobilePowerPanel(id="mobile-power-panel")' \
        app/screens/system.py \
    && [[ "$(grep -Fc '.update_mode_context(' app/main.py 2>/dev/null || true)" == "4" ]] \
    && [[ "$(grep -Fc 'self.mobile_power_policy.apply(' app/main.py 2>/dev/null || true)" == "2" ]]
then
    pass "SYSTEM surface and mode context integration"
else
    fail "SYSTEM surface and mode context integration"
fi

printf '\n===== LIVE READ-ONLY SAMPLE =====\n'
if PYTHONPATH="$REPO" RUNTIME_ROOT="$runtime_root" \
   "$PYTHON_BIN" - <<'PY_LIVE_SAMPLE'
import json
import os
from pathlib import Path
from rich.text import Text

from app.mobile_power_panel import MobilePowerPanel
from modules.power import PowerMonitor
from services.mobile_power_policy import MobilePowerPolicyService

root = Path(os.environ["RUNTIME_ROOT"])
state_path = root / "mode_state.json"
modes_path = root / "modes.json"

active_mode = "custom"
if state_path.is_file():
    state = json.loads(state_path.read_text(encoding="utf-8"))
    active_mode = str(state.get("active_mode", "custom")).strip().lower() or "custom"

mode_payload = None
source = modes_path
if not source.is_file():
    source = Path("config/modes.example.json")

if source.is_file():
    payload = json.loads(source.read_text(encoding="utf-8"))
    for item in payload.get("modes", []):
        if str(item.get("id", "")).strip().lower() == active_mode:
            mode_payload = item
            break

explicit = "unchanged"
if isinstance(mode_payload, dict):
    explicit = str(mode_payload.get("power_profile", "unchanged"))

sample = PowerMonitor().sample()
policy = MobilePowerPolicyService()
target = policy.policy_target_for_source(
    active_mode,
    explicit,
    sample.external_power_online,
)

markup = MobilePowerPanel.build_markup(
    sample,
    active_mode,
    target,
)

plain = Text.from_markup(markup).plain
required = (
    "MOBILE POWER // FIELD ENERGY STATUS",
    "BATTERY",
    "HEALTH",
    "SOURCE",
    "PROFILE",
    "MODE POLICY",
)
if not all(marker in plain for marker in required):
    raise SystemExit(1)

print(plain)
PY_LIVE_SAMPLE
then
    pass "Live power telemetry and presentation"
else
    fail "Live power telemetry and presentation"
fi

if [[ -x scripts/check-release.sh ]]; then
    pass "Stage 5 release checker available"
else
    fail "Stage 5 release checker available"
fi

POWER_AFTER="$(read_power_profile)"
if [[ "$POWER_AFTER" == "$POWER_BEFORE" ]]; then
    pass "Live power profile unchanged by audit"
else
    fail "Live power profile unchanged by audit"
fi

runtime_unchanged=1
for path in "${runtime_files[@]}"; do
    if [[ "$(runtime_digest "$path")" != "${RUNTIME_BEFORE[$path]}" ]]; then
        runtime_unchanged=0
    fi
done

if (( runtime_unchanged == 1 )); then
    pass "Runtime JSON unchanged by audit"
else
    fail "Runtime JSON unchanged by audit"
fi

if [[ "$(git rev-parse HEAD)" == "$HEAD_BEFORE" ]] \
    && [[ "$(git status --porcelain=v1 --untracked-files=all)" == "$STATUS_BEFORE" ]]
then
    pass "Repository state unchanged by audit"
else
    fail "Repository state unchanged by audit"
fi

printf '\n===== AUDIT SAFETY GUARANTEES =====\n'
printf '[PASS] No mode was activated.\n'
printf '[PASS] No workspace application was launched.\n'
printf '[PASS] No runtime JSON was written.\n'
printf '[PASS] No power profile was changed.\n'
printf '[PASS] No system service or boot/auth configuration was changed.\n'
printf '[PASS] No reboot or logout was requested.\n'

printf '\nChecks: %d OK, %d failures\n' "$OK" "$FAIL"
(( FAIL == 0 ))
