#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

PYTHON_BIN="${PYTHON_BIN:-$REPO/venv/bin/python}"

STATE="$DATA_HOME/helm-mobile/stage4b-lockscreen-last-apply.json"

test -x "$PYTHON_BIN"
test -s "$STATE"

readarray -t VALUES < <(
    STATE="$STATE" \
    "$PYTHON_BIN" - <<'PY_STATE'
import json
import os
from pathlib import Path

state = json.loads(
    Path(os.environ["STATE"]).read_text(
        encoding="utf-8"
    )
)

if state.get("stage") != "4b-security-lock":
    raise SystemExit(
        "Invalid Security Lock state."
    )

print(state["recovery"])
print(state["target_shell"])
print(state["lock_config"])
print(state["wallpaper_target"])
print("1" if state["had_target"] else "0")
print("1" if state["had_config"] else "0")
print("1" if state["had_wallpaper"] else "0")
PY_STATE
)

RECOVERY="${VALUES[0]}"
TARGET_SHELL="${VALUES[1]}"
LOCK_CONFIG="${VALUES[2]}"
WALLPAPER_TARGET="${VALUES[3]}"
HAD_TARGET="${VALUES[4]}"
HAD_CONFIG="${VALUES[5]}"
HAD_WALLPAPER="${VALUES[6]}"

test -d "$RECOVERY"

rm -rf "$TARGET_SHELL"

if [[ "$HAD_TARGET" == "1" ]]; then
    test -d "$RECOVERY/plasma-shell"

    mkdir -p "$(dirname "$TARGET_SHELL")"

    cp -a \
        "$RECOVERY/plasma-shell" \
        "$TARGET_SHELL"
fi

if [[ "$HAD_CONFIG" == "1" ]]; then
    test -f "$RECOVERY/kscreenlockerrc"

    mkdir -p "$(dirname "$LOCK_CONFIG")"

    cp -a \
        "$RECOVERY/kscreenlockerrc" \
        "$LOCK_CONFIG"
else
    rm -f "$LOCK_CONFIG"
fi

if [[ "$HAD_WALLPAPER" == "1" ]]; then
    test -f "$RECOVERY/wallpaper.svg"

    mkdir -p "$(dirname "$WALLPAPER_TARGET")"

    cp -a \
        "$RECOVERY/wallpaper.svg" \
        "$WALLPAPER_TARGET"
else
    rm -f "$WALLPAPER_TARGET"
fi

kbuildsycoca6 --noincremental \
    >/dev/null 2>&1 \
    || true

echo 'HELM Mobile Security Lock restored.'
echo "Recovery source: $RECOVERY"
