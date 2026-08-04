#!/usr/bin/env bash
set -Eeuo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
LOCAL_APPS="$DATA_HOME/applications"
STATE_FILE="$DATA_HOME/helm-mobile/stage2c-launchers-last-apply.json"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

command -v jq >/dev/null
command -v qdbus6 >/dev/null

test -s "$STATE_FILE"

RECOVERY_DIR="$(
    jq -r '.recovery' "$STATE_FILE"
)"

test -d "$RECOVERY_DIR"
test -s "$RECOVERY_DIR/panel-before.json"
test -f "$RECOVERY_DIR/existing-files.txt"

echo '===== RESTORE STAGE 2C PANEL LAUNCHERS ====='
echo "Recovery: $RECOVERY_DIR"

TARGETS=(
    "$HOME/.local/bin/helm-start"

    "$LOCAL_APPS/helm-mobile.desktop"
    "$LOCAL_APPS/org.kde.konsole.desktop"
    "$LOCAL_APPS/org.kde.dolphin.desktop"
    "$LOCAL_APPS/firefox.desktop"

    "$DATA_HOME/helm-mobile/icons/helm-mobile-core.svg"
    "$DATA_HOME/helm-mobile/icons/helm-mobile-terminal.svg"
    "$DATA_HOME/helm-mobile/icons/helm-mobile-files.svg"
    "$DATA_HOME/helm-mobile/icons/helm-mobile-browser.svg"
)

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
echo '===== REBUILD APPLICATION DATABASE ====='

update-desktop-database \
    "$LOCAL_APPS"

kbuildsycoca6 \
    --noincremental \
    >/dev/null

echo
echo '===== RESTORE PANEL LAUNCHERS ====='

OLD_LAUNCHERS="$(
    RECOVERY_DIR="$RECOVERY_DIR" \
    python - <<'PY_OLD'
import json
import os
from pathlib import Path

path = (
    Path(os.environ["RECOVERY_DIR"])
    / "panel-before.json"
)

payload = json.loads(
    path.read_text(encoding="utf-8")
)

print(payload["launchers"])
PY_OLD
)"

OLD_LAUNCHERS_JSON="$(
    OLD_LAUNCHERS="$OLD_LAUNCHERS" \
    python - <<'PY_JSON'
import json
import os

print(json.dumps(
    os.environ["OLD_LAUNCHERS"]
))
PY_JSON
)"

cat > "$TMP_DIR/restore-launchers.js" <<JS
const ids = panelIds;
let panel = null;
let tasks = null;

for (let i = 0; i < ids.length; ++i) {
    const candidate = panelById(ids[i]);

    if (
        candidate
        && candidate.location === "bottom"
    ) {
        panel = candidate;
        break;
    }
}

if (!panel) {
    throw new Error("Bottom panel not found");
}

for (let i = 0; i < panel.widgetIds.length; ++i) {
    const widget = panel.widgetById(
        panel.widgetIds[i]
    );

    if (
        widget
        && widget.type === "org.kde.plasma.icontasks"
    ) {
        tasks = widget;
        break;
    }
}

if (!tasks) {
    throw new Error("Icon Tasks widget not found");
}

tasks.currentConfigGroup = ["General"];
tasks.writeConfig(
    "launchers",
    $OLD_LAUNCHERS_JSON
);
tasks.reloadConfig();

print("PREVIOUS LAUNCHERS RESTORED");
JS

qdbus6 \
    org.kde.plasmashell \
    /PlasmaShell \
    org.kde.PlasmaShell.evaluateScript \
    "$(cat "$TMP_DIR/restore-launchers.js")"

systemctl --user restart \
    plasma-plasmashell.service

for attempt in {1..30}; do
    if systemctl --user is-active --quiet \
        plasma-plasmashell.service
    then
        echo
        echo 'Stage 2C launcher state restored.'
        exit 0
    fi

    sleep 1
done

echo '[FAIL] Plasma Shell did not return.' >&2
exit 1
