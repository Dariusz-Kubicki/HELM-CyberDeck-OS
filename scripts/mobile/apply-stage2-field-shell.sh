#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY_DIR="$DATA_HOME/helm-mobile/recovery/stage2-field-shell-$STAMP"
STATE_FILE="$DATA_HOME/helm-mobile/stage2-field-shell-last-apply.json"
MANIFEST="$ROOT_DIR/mobile/plasma/field-shell.json"
WALLPAPER_SOURCE="$ROOT_DIR/mobile/assets/wallpapers/helm-mobile-field-node-v2.svg"
WALLPAPER_DIR="$HOME/Obrazy/HELM-Mobile"
WALLPAPER_TARGET="$WALLPAPER_DIR/helm-mobile-field-node-v2.svg"
TMP_DIR="$(mktemp -d)"

trap 'rm -rf "$TMP_DIR"' EXIT

command -v jq >/dev/null
command -v qdbus6 >/dev/null
command -v plasma-apply-colorscheme >/dev/null
command -v plasma-apply-wallpaperimage >/dev/null
command -v kwriteconfig6 >/dev/null

test -s "$MANIFEST"
test -s "$WALLPAPER_SOURCE"
systemctl --user is-active --quiet plasma-plasmashell.service

mkdir -p \
    "$RECOVERY_DIR" \
    "$WALLPAPER_DIR" \
    "$(dirname "$STATE_FILE")"

for file in \
    kdeglobals \
    plasmarc \
    kcminputrc \
    plasma-org.kde.plasma.desktop-appletsrc \
    plasmashellrc
do
    if [[ -f "$CONFIG_HOME/$file" ]]; then
        cp -a \
            "$CONFIG_HOME/$file" \
            "$RECOVERY_DIR/"
    fi
done

cat > "$TMP_DIR/read-panel.js" <<'JS'
const ids = panelIds;
let panel = null;

for (let i = 0; i < ids.length; ++i) {
    const candidate = panelById(ids[i]);

    if (candidate && candidate.location === "bottom") {
        panel = candidate;
        break;
    }
}

if (!panel) {
    throw new Error("Bottom panel not found");
}

print(JSON.stringify({
    id: panel.id,
    location: panel.location,
    height: panel.height,
    length: panel.length,
    minimumLength: panel.minimumLength,
    maximumLength: panel.maximumLength,
    lengthMode: panel.lengthMode,
    alignment: panel.alignment,
    offset: panel.offset,
    hiding: panel.hiding,
    floating: panel.floating,
    opacity: panel.opacity
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
    jq . \
    > "$RECOVERY_DIR/panel-before.json"

cp -f \
    "$WALLPAPER_SOURCE" \
    "$WALLPAPER_TARGET"

plasma-apply-colorscheme BreezeDark
plasma-apply-wallpaperimage "$WALLPAPER_TARGET"

kwriteconfig6 \
    --file kdeglobals \
    --group KDE \
    --key widgetStyle \
    Breeze

kwriteconfig6 \
    --file kdeglobals \
    --group Icons \
    --key Theme \
    breeze

kwriteconfig6 \
    --file kcminputrc \
    --group Mouse \
    --key cursorTheme \
    breeze_cursors

kwriteconfig6 \
    --file plasmarc \
    --group Theme \
    --key name \
    default

PANEL_ID="$(jq -r '.id' "$RECOVERY_DIR/panel-before.json")"

cat > "$TMP_DIR/apply-panel.js" <<JS
const panel = panelById($PANEL_ID);

if (!panel) {
    throw new Error("Panel $PANEL_ID not found");
}

panel.location = "bottom";
panel.height = 40;
panel.lengthMode = "custom";
panel.minimumLength = 1200;
panel.maximumLength = 1200;
panel.length = 1200;
panel.alignment = "center";
panel.offset = 0;
panel.hiding = "dodgewindows";
panel.floating = true;
panel.opacity = "translucent";

print("FIELD SHELL APPLIED");
JS

qdbus6 \
    org.kde.plasmashell \
    /PlasmaShell \
    org.kde.PlasmaShell.evaluateScript \
    "$(cat "$TMP_DIR/apply-panel.js")"

sleep 2

PANEL_AFTER="$(
    qdbus6 \
        org.kde.plasmashell \
        /PlasmaShell \
        org.kde.PlasmaShell.evaluateScript \
        "$(cat "$TMP_DIR/read-panel.js")"
)"

printf '%s\n' "$PANEL_AFTER" | jq .

jq -e '
    .location == "bottom"
    and .height == 40
    and .minimumLength == 1200
    and .maximumLength == 1200
    and .lengthMode == "custom"
    and .alignment == "center"
    and .offset == 0
    and .hiding == "dodgewindows"
    and .floating == true
    and .opacity == "translucent"
' <<< "$PANEL_AFTER" >/dev/null

STATE_FILE="$STATE_FILE" \
RECOVERY_DIR="$RECOVERY_DIR" \
WALLPAPER_TARGET="$WALLPAPER_TARGET" \
PANEL_AFTER="$PANEL_AFTER" \
python - <<'PY_STATE'
import json
import os
from datetime import datetime
from pathlib import Path

payload = {
    "stage": "2-field-shell",
    "applied": datetime.now().astimezone().isoformat(),
    "recovery": os.environ["RECOVERY_DIR"],
    "wallpaper": os.environ["WALLPAPER_TARGET"],
    "panel": json.loads(os.environ["PANEL_AFTER"]),
}

Path(os.environ["STATE_FILE"]).write_text(
    json.dumps(payload, indent=2) + "\n",
    encoding="utf-8",
)
PY_STATE

echo 'Applied Stage 2 Plasma Field Shell.'
echo "Wallpaper: $WALLPAPER_TARGET"
echo "Recovery:  $RECOVERY_DIR"
echo "State:     $STATE_FILE"
