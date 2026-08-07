#!/usr/bin/env bash
set -Eeuo pipefail

DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile"
STATE_FILE="$DATA_ROOT/stage6d-mobile-hud-last-apply.json"
CONFIG_TARGET="$HOME/.config/conky/helm-mobile.conf"

[[ -s "$STATE_FILE" ]] || { echo "No Stage 6D recovery state found." >&2; exit 1; }

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

if pid="$(find_hud_pid 2>/dev/null || true)"; [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null || true
fi

python - "$STATE_FILE" <<'PY'
import json, shutil, sys
from pathlib import Path
state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for item in state.get("files", []):
    target = Path(item["target"])
    if item.get("existed"):
        backup = Path(item["backup"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
    else:
        target.unlink(missing_ok=True)
PY

if [[ "$(python - "$STATE_FILE" <<'PY'
import json,sys
from pathlib import Path
print(str(json.loads(Path(sys.argv[1]).read_text()).get('was_running', False)).lower())
PY
)" == "true" && -x "$HOME/.local/bin/helm-mobile-start" ]]; then
    "$HOME/.local/bin/helm-mobile-start" || true
fi

echo "Stage 6D Mobile HUD restored from recovery state."
