#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
LOCAL_APPS="$DATA_HOME/applications"
LOCAL_ICONS="$DATA_HOME/helm-mobile/icons"
LOCAL_BIN="$HOME/.local/bin"

MANIFEST="$ROOT_DIR/mobile/apps/launchers/launchers.json"
TEMPLATE="$ROOT_DIR/mobile/apps/launchers/helm-mobile.desktop.in"
SOURCE_ICONS="$ROOT_DIR/mobile/icons/launchers"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY_DIR="$DATA_HOME/helm-mobile/recovery/stage2c-launchers-$STAMP"
STATE_FILE="$DATA_HOME/helm-mobile/stage2c-launchers-last-apply.json"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo '===== APPLY STAGE 2C PANEL LAUNCHERS ====='

for command_name in \
    jq \
    python \
    qdbus6 \
    desktop-file-validate \
    update-desktop-database \
    kbuildsycoca6
do
    command -v "$command_name" >/dev/null
done

test -s "$MANIFEST"
test -s "$TEMPLATE"
test -x "$ROOT_DIR/desktop/launchers/helm-run"

for icon in \
    helm-mobile-core.svg \
    helm-mobile-terminal.svg \
    helm-mobile-files.svg \
    helm-mobile-browser.svg
do
    test -s "$SOURCE_ICONS/$icon"
done

systemctl --user is-active --quiet \
    plasma-plasmashell.service

mkdir -p \
    "$LOCAL_APPS" \
    "$LOCAL_ICONS" \
    "$LOCAL_BIN" \
    "$RECOVERY_DIR/files" \
    "$(dirname "$STATE_FILE")"

echo
echo '===== VALIDATE MANIFEST ====='

python -m json.tool \
    "$MANIFEST" \
    >/dev/null

EXPECTED_LAUNCHERS="$(
    jq -r '.panel_launchers' "$MANIFEST"
)"

test "$EXPECTED_LAUNCHERS" = \
    'applications:helm-mobile.desktop,applications:org.kde.konsole.desktop,applications:org.kde.dolphin.desktop,applications:firefox.desktop'

test "$(jq -r '.global_icon_theme' "$MANIFEST")" = \
    'breeze'

echo '[PASS] Launcher manifest is valid.'

echo
echo '===== CAPTURE PANEL STATE ====='

cat > "$TMP_DIR/read-panel.js" <<'JS'
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

print(JSON.stringify({
    panelId: panel.id,
    widgetId: tasks.id,
    height: panel.height,
    minimumLength: panel.minimumLength,
    maximumLength: panel.maximumLength,
    lengthMode: panel.lengthMode,
    alignment: panel.alignment,
    offset: panel.offset,
    hiding: panel.hiding,
    floating: panel.floating,
    opacity: panel.opacity,
    launchers: String(
        tasks.readConfig("launchers", "")
    )
}));
JS

PANEL_BEFORE="$(
    qdbus6 \
        org.kde.plasmashell \
        /PlasmaShell \
        org.kde.PlasmaShell.evaluateScript \
        "$(cat "$TMP_DIR/read-panel.js")"
)"

printf '%s\n' "$PANEL_BEFORE" |
    python -m json.tool

printf '%s\n' "$PANEL_BEFORE" \
    > "$RECOVERY_DIR/panel-before.json"

echo
echo '===== BACK UP LOCAL FILES ====='

TARGETS=(
    "$LOCAL_BIN/helm-start"

    "$LOCAL_APPS/helm-mobile.desktop"
    "$LOCAL_APPS/org.kde.konsole.desktop"
    "$LOCAL_APPS/org.kde.dolphin.desktop"
    "$LOCAL_APPS/firefox.desktop"

    "$LOCAL_ICONS/helm-mobile-core.svg"
    "$LOCAL_ICONS/helm-mobile-terminal.svg"
    "$LOCAL_ICONS/helm-mobile-files.svg"
    "$LOCAL_ICONS/helm-mobile-browser.svg"
)

: > "$RECOVERY_DIR/existing-files.txt"

for target in "${TARGETS[@]}"; do
    if [[ -e "$target" || -L "$target" ]]; then
        relative="${target#/}"
        backup="$RECOVERY_DIR/files/$relative"

        mkdir -p "$(dirname "$backup")"

        cp -a \
            "$target" \
            "$backup"

        printf '%s\n' "$target" \
            >> "$RECOVERY_DIR/existing-files.txt"

        echo "[BACKUP] $target"
    else
        echo "[NEW]    $target"
    fi
done

echo
echo '===== INSTALL ICON SOURCES ====='

for icon in \
    helm-mobile-core.svg \
    helm-mobile-terminal.svg \
    helm-mobile-files.svg \
    helm-mobile-browser.svg
do
    install \
        -Dm644 \
        "$SOURCE_ICONS/$icon" \
        "$LOCAL_ICONS/$icon"
done

echo '[PASS] HELM Mobile launcher icons installed.'

echo
echo '===== INSTALL HELM START COMMAND ====='

install \
    -Dm755 \
    "$ROOT_DIR/desktop/launchers/helm-run" \
    "$LOCAL_BIN/helm-start"

test -x "$LOCAL_BIN/helm-start"

echo '[PASS] HELM start command installed.'

echo
echo '===== RENDER HELM DESKTOP ENTRY ====='

TEMPLATE="$TEMPLATE" \
OUTPUT="$LOCAL_APPS/helm-mobile.desktop" \
HELM_START="$LOCAL_BIN/helm-start" \
HELM_ICON="$LOCAL_ICONS/helm-mobile-core.svg" \
python - <<'PY_RENDER'
import os
from pathlib import Path

template = Path(os.environ["TEMPLATE"])
output = Path(os.environ["OUTPUT"])

text = template.read_text(encoding="utf-8")

text = text.replace(
    "@HELM_START@",
    os.environ["HELM_START"],
)

text = text.replace(
    "@HELM_ICON@",
    os.environ["HELM_ICON"],
)

if "@HELM_" in text:
    raise SystemExit(
        "Unresolved HELM desktop placeholder"
    )

output.write_text(
    text.rstrip("\n") + "\n",
    encoding="utf-8",
)
PY_RENDER

chmod 644 \
    "$LOCAL_APPS/helm-mobile.desktop"

desktop-file-validate \
    "$LOCAL_APPS/helm-mobile.desktop"

echo '[PASS] HELM desktop entry installed.'

echo
echo '===== LOCATE SYSTEM DESKTOP FILES ====='

find_system_desktop() {
    local desktop_id="$1"
    local root
    local candidate
    local roots=()

    IFS=: read -r -a roots <<< \
        "${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"

    roots+=(
        /usr/local/share
        /usr/share
    )

    for root in "${roots[@]}"; do
        [[ -n "$root" ]] || continue

        candidate="$root/applications/$desktop_id"

        if [[ -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

SYSTEM_KONSOLE="$(
    find_system_desktop \
        org.kde.konsole.desktop
)"

SYSTEM_DOLPHIN="$(
    find_system_desktop \
        org.kde.dolphin.desktop
)"

SYSTEM_FIREFOX="$(
    find_system_desktop \
        firefox.desktop
)"

echo "Konsole: $SYSTEM_KONSOLE"
echo "Dolphin: $SYSTEM_DOLPHIN"
echo "Firefox: $SYSTEM_FIREFOX"

echo
echo '===== CREATE SAME-ID ICON OVERRIDES ====='

cp -f \
    "$SYSTEM_KONSOLE" \
    "$LOCAL_APPS/org.kde.konsole.desktop"

cp -f \
    "$SYSTEM_DOLPHIN" \
    "$LOCAL_APPS/org.kde.dolphin.desktop"

cp -f \
    "$SYSTEM_FIREFOX" \
    "$LOCAL_APPS/firefox.desktop"

patch_desktop_icon() {
    local desktop_file="$1"
    local icon_file="$2"

    python - \
        "$desktop_file" \
        "$icon_file" \
        <<'PY_ICON'
import sys
from pathlib import Path

desktop = Path(sys.argv[1])
icon = sys.argv[2]

lines = desktop.read_text(
    encoding="utf-8",
    errors="replace",
).splitlines()

output = []
inside_entry = False
icon_written = False

for line in lines:
    if line == "[Desktop Entry]":
        inside_entry = True
        output.append(line)
        continue

    if inside_entry and line.startswith("["):
        if not icon_written:
            output.append(f"Icon={icon}")
            icon_written = True

        inside_entry = False

    if inside_entry and line.startswith("Icon="):
        if not icon_written:
            output.append(f"Icon={icon}")
            icon_written = True

        continue

    output.append(line)

if inside_entry and not icon_written:
    output.append(f"Icon={icon}")

desktop.write_text(
    "\n".join(output).rstrip() + "\n",
    encoding="utf-8",
)
PY_ICON
}

patch_desktop_icon \
    "$LOCAL_APPS/org.kde.konsole.desktop" \
    "$LOCAL_ICONS/helm-mobile-terminal.svg"

patch_desktop_icon \
    "$LOCAL_APPS/org.kde.dolphin.desktop" \
    "$LOCAL_ICONS/helm-mobile-files.svg"

patch_desktop_icon \
    "$LOCAL_APPS/firefox.desktop" \
    "$LOCAL_ICONS/helm-mobile-browser.svg"

chmod 644 \
    "$LOCAL_APPS/org.kde.konsole.desktop" \
    "$LOCAL_APPS/org.kde.dolphin.desktop" \
    "$LOCAL_APPS/firefox.desktop"

desktop-file-validate \
    "$LOCAL_APPS/org.kde.konsole.desktop"

desktop-file-validate \
    "$LOCAL_APPS/org.kde.dolphin.desktop"

desktop-file-validate \
    "$LOCAL_APPS/firefox.desktop"

echo '[PASS] Same-ID application overrides installed.'

echo
echo '===== REBUILD APPLICATION DATABASE ====='

update-desktop-database \
    "$LOCAL_APPS"

kbuildsycoca6 \
    --noincremental \
    >/dev/null

echo '[PASS] KDE application database rebuilt.'

echo
echo '===== APPLY PANEL LAUNCHER ORDER ====='

LAUNCHERS_JSON="$(
    EXPECTED_LAUNCHERS="$EXPECTED_LAUNCHERS" \
    python - <<'PY_JSON'
import json
import os

print(json.dumps(
    os.environ["EXPECTED_LAUNCHERS"]
))
PY_JSON
)"

cat > "$TMP_DIR/apply-launchers.js" <<JS
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
    $LAUNCHERS_JSON
);
tasks.reloadConfig();

print("STAGE 2C LAUNCHERS APPLIED");
JS

qdbus6 \
    org.kde.plasmashell \
    /PlasmaShell \
    org.kde.PlasmaShell.evaluateScript \
    "$(cat "$TMP_DIR/apply-launchers.js")"

echo
echo '===== RESTART PLASMA THROUGH SYSTEMD ====='

systemctl --user restart \
    plasma-plasmashell.service

for attempt in {1..30}; do
    if systemctl --user is-active --quiet \
        plasma-plasmashell.service
    then
        break
    fi

    sleep 1
done

systemctl --user is-active --quiet \
    plasma-plasmashell.service

sleep 3

echo
echo '===== VERIFY INSTALLED STATE ====='

PANEL_AFTER="$(
    qdbus6 \
        org.kde.plasmashell \
        /PlasmaShell \
        org.kde.PlasmaShell.evaluateScript \
        "$(cat "$TMP_DIR/read-panel.js")"
)"

printf '%s\n' "$PANEL_AFTER" |
    python -m json.tool

PANEL_AFTER="$PANEL_AFTER" \
EXPECTED_LAUNCHERS="$EXPECTED_LAUNCHERS" \
python - <<'PY_VERIFY'
import json
import os

state = json.loads(
    os.environ["PANEL_AFTER"]
)

expected = {
    "height": 40,
    "minimumLength": 1200,
    "maximumLength": 1200,
    "lengthMode": "custom",
    "alignment": "center",
    "offset": 0,
    "hiding": "dodgewindows",
    "floating": True,
    "opacity": "translucent",
    "launchers": os.environ["EXPECTED_LAUNCHERS"],
}

for key, expected_value in expected.items():
    actual_value = state.get(key)

    if actual_value != expected_value:
        raise SystemExit(
            f"{key}: {actual_value!r} "
            f"!= {expected_value!r}"
        )
PY_VERIFY

test "$(
    kreadconfig6 \
        --file kdeglobals \
        --group Icons \
        --key Theme
)" = "breeze"

cmp \
    "$SOURCE_ICONS/helm-mobile-core.svg" \
    "$LOCAL_ICONS/helm-mobile-core.svg"

cmp \
    "$SOURCE_ICONS/helm-mobile-terminal.svg" \
    "$LOCAL_ICONS/helm-mobile-terminal.svg"

cmp \
    "$SOURCE_ICONS/helm-mobile-files.svg" \
    "$LOCAL_ICONS/helm-mobile-files.svg"

cmp \
    "$SOURCE_ICONS/helm-mobile-browser.svg" \
    "$LOCAL_ICONS/helm-mobile-browser.svg"

grep -Fqx \
    "Icon=$LOCAL_ICONS/helm-mobile-core.svg" \
    "$LOCAL_APPS/helm-mobile.desktop"

grep -Fqx \
    "Icon=$LOCAL_ICONS/helm-mobile-terminal.svg" \
    "$LOCAL_APPS/org.kde.konsole.desktop"

grep -Fqx \
    "Icon=$LOCAL_ICONS/helm-mobile-files.svg" \
    "$LOCAL_APPS/org.kde.dolphin.desktop"

grep -Fqx \
    "Icon=$LOCAL_ICONS/helm-mobile-browser.svg" \
    "$LOCAL_APPS/firefox.desktop"

echo '[PASS] Installed Stage 2C state is correct.'

STATE_FILE="$STATE_FILE" \
RECOVERY_DIR="$RECOVERY_DIR" \
PANEL_AFTER="$PANEL_AFTER" \
python - <<'PY_STATE'
import json
import os
from datetime import datetime
from pathlib import Path

payload = {
    "stage": "2c-panel-launchers",
    "applied": datetime.now()
        .astimezone()
        .isoformat(),
    "recovery": os.environ["RECOVERY_DIR"],
    "panel": json.loads(
        os.environ["PANEL_AFTER"]
    ),
}

Path(os.environ["STATE_FILE"]).write_text(
    json.dumps(payload, indent=2) + "\n",
    encoding="utf-8",
)
PY_STATE

echo
echo 'STAGE 2C LAUNCHERS: APPLIED'
echo "Recovery: $RECOVERY_DIR"
echo "State:    $STATE_FILE"
