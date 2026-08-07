#!/usr/bin/env bash
set -euo pipefail

STATE_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile"
STATE="$STATE_ROOT/stage6a-suspend-policy-state.json"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
KSCREEN="$CONFIG_HOME/kscreenlockerrc"
POWERDEVIL="$CONFIG_HOME/powerdevilrc"

[[ -s "$STATE" ]] || { echo "No Stage 6A state file." >&2; exit 1; }

mapfile -t VALUES < <(python3 - "$STATE" <<'PY'
import json
import sys
from pathlib import Path
p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if p.get("stage") != "6a-mobile-suspend-policy":
    raise SystemExit(1)
for key in (
    "recovery",
    "systemd_sleep_target",
    "systemd_sleep_target_existed",
    "kscreenlockerrc_existed",
    "powerdevilrc_existed",
):
    print(str(p.get(key, "")).lower() if isinstance(p.get(key), bool) else p.get(key, ""))
PY
)

RECOVERY="${VALUES[0]}"
TARGET="${VALUES[1]}"
TARGET_EXISTED="${VALUES[2]}"
KSCREEN_EXISTED="${VALUES[3]}"
POWERDEVIL_EXISTED="${VALUES[4]}"
[[ -d "$RECOVERY" ]] || { echo "Recovery directory missing: $RECOVERY" >&2; exit 1; }

if [[ "$TARGET_EXISTED" == true ]]; then
    sudo install -Dm0644 "$RECOVERY/systemd-sleep.conf" "$TARGET"
else
    sudo rm -f "$TARGET"
fi

if [[ "$KSCREEN_EXISTED" == true ]]; then
    cp -a "$RECOVERY/kscreenlockerrc" "$KSCREEN"
else
    rm -f "$KSCREEN"
fi

if [[ "$POWERDEVIL_EXISTED" == true ]]; then
    cp -a "$RECOVERY/powerdevilrc" "$POWERDEVIL"
else
    rm -f "$POWERDEVIL"
fi

printf 'Stage 6A configuration restored from %s\n' "$RECOVERY"
