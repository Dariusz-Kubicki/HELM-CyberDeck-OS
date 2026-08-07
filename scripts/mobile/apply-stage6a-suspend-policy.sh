#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE="$REPO/mobile/systemd/90-helm-mobile-sleep.conf"
TARGET="/etc/systemd/sleep.conf.d/90-helm-mobile-sleep.conf"
STATE_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile"
STATE="$STATE_ROOT/stage6a-suspend-policy-state.json"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
KSCREEN="$CONFIG_HOME/kscreenlockerrc"
POWERDEVIL="$CONFIG_HOME/powerdevilrc"

[[ -s "$SOURCE" ]] || { echo "Missing Stage 6A sleep template." >&2; exit 1; }
command -v systemd-inhibit >/dev/null || exit 1
command -v kwriteconfig6 >/dev/null || exit 1
command -v kreadconfig6 >/dev/null || exit 1
command -v sudo >/dev/null || exit 1

systemd-inhibit --list --no-pager 2>/dev/null | grep -Fq 'PowerDevil' || {
    echo "PowerDevil does not own desktop power events." >&2
    exit 1
}

[[ -r /sys/power/mem_sleep ]] || exit 1
grep -Fq '[s2idle]' /sys/power/mem_sleep || {
    echo "s2idle is not active." >&2
    exit 1
}

mkdir -p "$STATE_ROOT/recovery"
STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY="$STATE_ROOT/recovery/stage6a-suspend-policy-$STAMP"
mkdir -p "$RECOVERY"

TARGET_EXISTED=false
KSCREEN_EXISTED=false
POWERDEVIL_EXISTED=false

if sudo test -f "$TARGET"; then
    TARGET_EXISTED=true
    sudo cp -a "$TARGET" "$RECOVERY/systemd-sleep.conf"
fi
if [[ -f "$KSCREEN" ]]; then
    KSCREEN_EXISTED=true
    cp -a "$KSCREEN" "$RECOVERY/kscreenlockerrc"
fi
if [[ -f "$POWERDEVIL" ]]; then
    POWERDEVIL_EXISTED=true
    cp -a "$POWERDEVIL" "$RECOVERY/powerdevilrc"
fi

rollback() {
    local status=$?
    set +e
    if [[ "$TARGET_EXISTED" == true ]]; then
        sudo install -Dm0644 "$RECOVERY/systemd-sleep.conf" "$TARGET" || true
    else
        sudo rm -f "$TARGET" || true
    fi
    if [[ "$KSCREEN_EXISTED" == true ]]; then
        cp -a "$RECOVERY/kscreenlockerrc" "$KSCREEN" || true
    else
        rm -f "$KSCREEN" || true
    fi
    if [[ "$POWERDEVIL_EXISTED" == true ]]; then
        cp -a "$RECOVERY/powerdevilrc" "$POWERDEVIL" || true
    else
        rm -f "$POWERDEVIL" || true
    fi
    echo "Stage 6A live changes rolled back after failure." >&2
    exit "$status"
}
trap rollback ERR

sudo install -Dm0644 "$SOURCE" "$TARGET"

# Plasma 6 PowerDevil owns lid handling while its logind inhibitor is active.
# Make the already-proven lid-close=suspend behavior explicit for AC and battery.
for profile in AC Battery; do
    kwriteconfig6 \
        --file powerdevilrc \
        --group "$profile" \
        --group SuspendAndShutdown \
        --key LidAction \
        1
 done

# Do not alter automatic lock timeout or grace-period policy. Only make
# resume locking explicit.
kwriteconfig6 \
    --file kscreenlockerrc \
    --group Daemon \
    --key LockOnResume \
    true

cmp -s "$SOURCE" "$TARGET"
[[ "$(kreadconfig6 --file powerdevilrc --group AC --group SuspendAndShutdown --key LidAction)" == "1" ]]
[[ "$(kreadconfig6 --file powerdevilrc --group Battery --group SuspendAndShutdown --key LidAction)" == "1" ]]
[[ "$(kreadconfig6 --file kscreenlockerrc --group Daemon --key LockOnResume --default true)" == "true" ]]

mkdir -p "$STATE_ROOT"
python3 - \
    "$STATE" "$RECOVERY" "$TARGET" \
    "$TARGET_EXISTED" "$KSCREEN_EXISTED" "$POWERDEVIL_EXISTED" <<'PY'
import json
import sys
from pathlib import Path

state, recovery, target, target_existed, kscreen_existed, powerdevil_existed = sys.argv[1:]
payload = {
    "stage": "6a-mobile-suspend-policy",
    "recovery": recovery,
    "systemd_sleep_target": target,
    "systemd_sleep_target_existed": target_existed == "true",
    "kscreenlockerrc_existed": kscreen_existed == "true",
    "powerdevilrc_existed": powerdevil_existed == "true",
    "service_restart_performed": False,
    "sleep_triggered": False,
}
Path(state).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY

trap - ERR
printf 'Stage 6A suspend policy applied.\nRecovery: %s\nState: %s\n' "$RECOVERY" "$STATE"
