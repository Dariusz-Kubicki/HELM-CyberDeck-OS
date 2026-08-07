#!/usr/bin/env bash
set -euo pipefail

REPO="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
    pwd
)"

DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile"
STAGE6B_STATE="$DATA_ROOT/stage6b-suspend-validation-state.json"

printf 'HELM Mobile Stage 6 wake-source read-only audit\n'
printf '==============================================\n\n'

printf '%s\n' '--- Stage 6B evidence ---'
if [[ -s "$STAGE6B_STATE" ]]; then
    python - "$STAGE6B_STATE" <<'PY_STATE'
import json
import sys
from pathlib import Path

p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("status:", p.get("status"))
print("sleep_backend:", p.get("sleep_backend"))
print(
    "lid_s2idle_entries:",
    p.get("lid_suspend", {}).get("s2idle_entry_count"),
)
PY_STATE
else
    printf 'state: missing\n'
fi

printf '\n%s\n' '--- Kernel wake IRQ ---'
if [[ -r /sys/power/pm_wakeup_irq ]]; then
    printf 'pm_wakeup_irq: '
    cat /sys/power/pm_wakeup_irq
else
    printf 'pm_wakeup_irq: unavailable\n'
fi

printf '\n%s\n' '--- ACPI wake table ---'
cat /proc/acpi/wakeup 2>/dev/null || true

printf '\n%s\n' '--- Enabled sysfs wake devices ---'
while IFS= read -r file; do
    [[ "$(cat "$file" 2>/dev/null || true)" == "enabled" ]] || continue
    device="${file%/power/wakeup}"
    driver="no-driver"
    if [[ -L "$device/driver" ]]; then
        driver="$(basename "$(readlink -f "$device/driver")")"
    fi
    printf 'enabled  %-20s %s\n' "$driver" "$device"
done < <(
    find /sys/devices \
        -path '*/power/wakeup' \
        -type f \
        2>/dev/null \
        | sort
)

printf '\n%s\n' '--- Network wake state ---'
for iface in /sys/class/net/*; do
    [[ -e "$iface" ]] || continue
    name="$(basename "$iface")"
    device="$(readlink -f "$iface/device" 2>/dev/null || true)"
    [[ -n "$device" ]] || continue
    wake="n/a"
    [[ -r "$device/power/wakeup" ]] && wake="$(cat "$device/power/wakeup")"
    printf '%-12s wake=%s\n' "$name" "$wake"
done

printf '\n%s\n' '--- GPU wake state ---'
for card in /sys/class/drm/card[0-9]*; do
    [[ -e "$card/device" ]] || continue
    wake="n/a"
    [[ -r "$card/device/power/wakeup" ]] \
        && wake="$(cat "$card/device/power/wakeup")"
    printf '%-12s wake=%s\n' "$(basename "$card")" "$wake"
done

printf '\n%s\n' '--- Recent PM / wake clues ---'
journalctl \
    -b \
    -k \
    --since '2 hours ago' \
    --no-pager \
    -o short-iso \
    2>/dev/null \
    | grep -Ei \
        'PM: suspend|PM: resume|PM: suspend exit|wakeup|wake source|amdgpu|xhci|rtw89|rtc' \
    | tail -n 180 \
    || true

printf '\n%s\n' '--- Decision contract ---'
python - "$REPO/mobile/power/wake-policy.json" <<'PY_DECISION'
import json
import sys
from pathlib import Path

p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
d = p["decision"]
print("action:", d["action"])
print("disable_wake_sources:", d["disable_wake_sources"])
print("preserve_lid_open_wake:", d["preserve_lid_open_wake"])
print("preserve_normal_input_wake:", d["preserve_normal_input_wake"])
print("reason:", d["reason"])
PY_DECISION

printf '\n[PASS] Read-only audit complete. No wake policy was modified.\n'
