#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile"
RECOVERY_ROOT="$DATA_ROOT/recovery"
STATE_FILE="$DATA_ROOT/stage6d-mobile-hud-last-apply.json"
STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY="$RECOVERY_ROOT/stage6d-mobile-hud-$STAMP"

CONFIG_TARGET="$HOME/.config/conky/helm-mobile.conf"
STATUS_TARGET="$HOME/.local/bin/helm-mobile-status"
START_TARGET="$HOME/.local/bin/helm-mobile-start"
AUTOSTART_TARGET="$HOME/.config/autostart/helm-mobile-node.desktop"

mkdir -p "$RECOVERY" "$(dirname "$CONFIG_TARGET")" "$(dirname "$STATUS_TARGET")" "$(dirname "$AUTOSTART_TARGET")" "$DATA_ROOT"

find_hud_pid() {
    local pid cmdline
    while IFS= read -r pid; do
        [[ -r "/proc/$pid/cmdline" ]] || continue
        cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
        [[ "$cmdline" == *"$CONFIG_TARGET"* ]] || continue
        printf '%s\n' "$pid"
        return 0
    done < <(pgrep -u "$UID" -x conky 2>/dev/null || true)
    return 1
}

WAS_RUNNING=false
if find_hud_pid >/dev/null; then WAS_RUNNING=true; fi

python - "$RECOVERY" "$STATE_FILE" "$WAS_RUNNING" \
    "$CONFIG_TARGET" "$STATUS_TARGET" "$START_TARGET" "$AUTOSTART_TARGET" <<'PY'
import json, shutil, sys
from pathlib import Path

recovery = Path(sys.argv[1])
state_file = Path(sys.argv[2])
was_running = sys.argv[3].lower() == "true"
targets = [Path(x) for x in sys.argv[4:]]
files = []
for target in targets:
    exists = target.is_file()
    backup = recovery / target.name
    if exists:
        shutil.copy2(target, backup)
    files.append({"target": str(target), "existed": exists, "backup": str(backup)})
state = {
    "stage": "6d-mobile-conky-hud",
    "recovery": str(recovery),
    "was_running": was_running,
    "files": files,
}
state_file.parent.mkdir(parents=True, exist_ok=True)
state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
PY

if pid="$(find_hud_pid 2>/dev/null || true)"; [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null || true
    for _ in {1..30}; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
    done
fi

install -Dm644 "$REPO/mobile/conky/helm-mobile.conf" "$CONFIG_TARGET"
install -Dm755 "$REPO/mobile/conky/helm-mobile-status" "$STATUS_TARGET"
install -Dm755 "$REPO/mobile/conky/helm-mobile-start" "$START_TARGET"
sed "s|__HOME__|$HOME|g" "$REPO/mobile/autostart/helm-mobile-node.desktop" > "$AUTOSTART_TARGET"
chmod 644 "$AUTOSTART_TARGET"

"$START_TARGET"
sleep 0.5
find_hud_pid >/dev/null || { echo "HELM Mobile HUD failed to start." >&2; exit 1; }

echo "HELM Mobile HUD preview applied."
echo "Recovery: $RECOVERY"
echo "State: $STATE_FILE"
