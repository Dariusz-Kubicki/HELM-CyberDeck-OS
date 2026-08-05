#!/usr/bin/env bash
set -Eeuo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

STATE_FILE="$DATA_HOME/helm-mobile/stage3a-konsole-last-apply.json"

command -v python >/dev/null

test -s "$STATE_FILE"

RECOVERY_DIR="$(
    STATE_FILE="$STATE_FILE" \
    python - <<'PY_RECOVERY'
import json
import os
from pathlib import Path

state = Path(os.environ["STATE_FILE"])

payload = json.loads(
    state.read_text(encoding="utf-8")
)

print(payload["recovery"])
PY_RECOVERY
)"

test -d "$RECOVERY_DIR"
test -f "$RECOVERY_DIR/existing-files.txt"

TARGETS=(
    "$CONFIG_HOME/konsolerc"
    "$DATA_HOME/konsole/HELMMobile.profile"
    "$DATA_HOME/konsole/HELMMobile.colorscheme"
    "$CONFIG_HOME/helm-mobile/terminal.bashrc"
    "$HOME/.local/bin/helm-mobile-shell"
)

echo '===== RESTORE STAGE 3A KONSOLE ====='
echo "Recovery: $RECOVERY_DIR"

echo
echo '===== RESTORE LOCAL FILES ====='

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
echo '===== VERIFY RESTORED DEFAULT PROFILE ====='

DEFAULT_PROFILE="$(
    kreadconfig6 \
        --file konsolerc \
        --group 'Desktop Entry' \
        --key DefaultProfile \
        2>/dev/null \
        || true
)"

EXPECTED_DEFAULT="$(
    cat "$RECOVERY_DIR/default-profile-before.txt"
)"

echo "Expected: ${EXPECTED_DEFAULT:-not configured}"
echo "Current:  ${DEFAULT_PROFILE:-not configured}"

test "$DEFAULT_PROFILE" = "$EXPECTED_DEFAULT"

echo
echo 'Stage 3A Konsole state restored.'
echo 'Already open terminal windows remain unchanged.'
