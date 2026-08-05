#!/usr/bin/env bash
set -Eeuo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

STATE_FILE="$DATA_HOME/helm-mobile/stage3b-dolphin-last-apply.json"

command -v python >/dev/null

test -s "$STATE_FILE"

RECOVERY_DIR="$(
    STATE_FILE="$STATE_FILE" \
    python - <<'PY_RECOVERY'
import json
import os
from pathlib import Path

payload = json.loads(
    Path(os.environ["STATE_FILE"]).read_text(
        encoding="utf-8"
    )
)

print(payload["recovery"])
PY_RECOVERY
)"

test -d "$RECOVERY_DIR"
test -f "$RECOVERY_DIR/existing-files.txt"

if pgrep -x dolphin >/dev/null; then
    echo '[FAIL] Close every Dolphin window before restoring Stage 3B.' >&2
    exit 1
fi

TARGETS=(
    "$CONFIG_HOME/dolphinrc"
    "$DATA_HOME/kxmlgui5/dolphin/dolphinui.rc"
    "$CONFIG_HOME/kxmlgui5/dolphin/dolphinui.rc"
)

echo '===== RESTORE STAGE 3B DOLPHIN ====='
echo "Recovery: $RECOVERY_DIR"

for target in "${TARGETS[@]}"; do
    rm -rf "$target"

    if grep -Fqx \
        "$target" \
        "$RECOVERY_DIR/existing-files.txt"
    then
        relative="${target#/}"
        backup="$RECOVERY_DIR/files/$relative"

        test -e "$backup" || test -L "$backup"

        mkdir -p "$(dirname "$target")"

        cp -a \
            "$backup" \
            "$target"

        echo "[RESTORED] $target"
    else
        echo "[REMOVED]  $target"
    fi
done

echo
echo 'Stage 3B Dolphin state restored.'
echo 'Dolphin remains closed.'
