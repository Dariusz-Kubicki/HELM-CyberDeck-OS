#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

ROOT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

SOURCE_DIR="$ROOT_DIR/mobile/apps/dolphin"
MANIFEST="$SOURCE_DIR/dolphin.json"
SOURCE_RC="$SOURCE_DIR/dolphinrc.template"

INSTALLED_RC="$CONFIG_HOME/dolphinrc"
DATA_UI="$DATA_HOME/kxmlgui5/dolphin/dolphinui.rc"
CONFIG_UI="$CONFIG_HOME/kxmlgui5/dolphin/dolphinui.rc"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY_DIR="$DATA_HOME/helm-mobile/recovery/stage3b-dolphin-$STAMP"
STATE_FILE="$DATA_HOME/helm-mobile/stage3b-dolphin-last-apply.json"

TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

echo '===== APPLY STAGE 3B DOLPHIN DATA VAULT ====='

for command_name in \
    python \
    dolphin \
    kreadconfig6 \
    qmake6 \
    timeout
do
    command -v "$command_name" >/dev/null
done

test -s "$MANIFEST"
test -s "$SOURCE_RC"

echo
echo '===== VALIDATE DOLPHIN SOURCES ====='

MANIFEST="$MANIFEST" \
SOURCE_RC="$SOURCE_RC" \
python - <<'PY_MANIFEST'
import json
import os
from pathlib import Path

manifest = Path(os.environ["MANIFEST"])
source_rc = Path(os.environ["SOURCE_RC"])

payload = json.loads(
    manifest.read_text(encoding="utf-8")
)

if payload.get("stage") != "3b-dolphin":
    raise SystemExit(
        "Invalid Dolphin stage identifier."
    )

if payload.get("role") != "HELM Data Vault":
    raise SystemExit(
        "Invalid Dolphin role."
    )

configuration = payload.get("configuration", {})
toolbar = payload.get("toolbar", {})
appearance = payload.get("appearance", {})
integration = payload.get("integration", {})

expected_configuration = {
    "file": "dolphinrc.template",
    "editable_location": True,
    "show_full_path": True,
    "show_full_path_in_titlebar": True,
    "open_external_folders_in_new_tab": True,
    "menu_bar": False,
    "places_icon_size": 22,
    "places_auto_resize": False,
}

for key, expected_value in expected_configuration.items():
    if configuration.get(key) != expected_value:
        raise SystemExit(
            f"Invalid Dolphin configuration value: {key}"
        )

if toolbar.get("strategy") != "native":
    raise SystemExit(
        "Dolphin toolbar strategy must be native."
    )

if toolbar.get("local_kxmlgui_override") is not False:
    raise SystemExit(
        "Local Dolphin KXMLGUI overrides must be disabled."
    )

if appearance.get("global_color_scheme") != "BreezeDark":
    raise SystemExit(
        "Invalid Dolphin global color scheme."
    )

if appearance.get("global_icon_theme") != "breeze":
    raise SystemExit(
        "Invalid Dolphin global icon theme."
    )

if integration.get("terminal_profile") != "HELMMobile.profile":
    raise SystemExit(
        "Invalid Dolphin terminal integration."
    )

if integration.get("panel_desktop_id") != "org.kde.dolphin.desktop":
    raise SystemExit(
        "Invalid Dolphin desktop identifier."
    )

required_lines = {
    "EditableUrl=true",
    "OpenExternallyCalledFolderInNewTab=true",
    "ShowFullPath=true",
    "ShowFullPathInTitlebar=true",
    "Places Icons Auto-resize=false",
    "Places Icons Static Size=22",
    "MenuBar=Disabled",
}

actual_lines = set(
    source_rc.read_text(
        encoding="utf-8"
    ).splitlines()
)

missing = required_lines - actual_lines

if missing:
    raise SystemExit(
        f"Missing Dolphin settings: {sorted(missing)}"
    )
PY_MANIFEST

if find "$SOURCE_DIR" \
    -maxdepth 1 \
    -type f \
    -name 'dolphinui.rc' \
    | grep -q .
then
    echo '[FAIL] Mobile Dolphin must not provide dolphinui.rc.' >&2
    exit 1
fi

echo '[PASS] Dolphin Data Vault sources are valid.'

echo
echo '===== VERIFY DOLPHIN IS CLOSED ====='

if pgrep -x dolphin >/dev/null; then
    echo '[FAIL] Close every Dolphin window before applying Stage 3B.' >&2
    pgrep -af '(^|/)dolphin( |$)' >&2 || true
    exit 1
fi

echo '[PASS] Dolphin is closed.'

echo
echo '===== CAPTURE CURRENT DOLPHIN STATE ====='

mkdir -p \
    "$CONFIG_HOME" \
    "$RECOVERY_DIR/files" \
    "$(dirname "$STATE_FILE")"

TARGETS=(
    "$INSTALLED_RC"
    "$DATA_UI"
    "$CONFIG_UI"
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
        echo "[ABSENT] $target"
    fi
done

echo
echo '===== INSTALL DATA VAULT CONFIGURATION ====='

install \
    -Dm644 \
    "$SOURCE_RC" \
    "$INSTALLED_RC"

rm -f \
    "$DATA_UI" \
    "$CONFIG_UI"

echo '[PASS] Dolphin configuration installed.'
echo '[PASS] Local KXMLGUI overrides removed.'

echo
echo '===== VERIFY INSTALLED SETTINGS ====='

cmp \
    "$SOURCE_RC" \
    "$INSTALLED_RC"

grep -Fqx \
    'EditableUrl=true' \
    "$INSTALLED_RC"

grep -Fqx \
    'OpenExternallyCalledFolderInNewTab=true' \
    "$INSTALLED_RC"

grep -Fqx \
    'ShowFullPath=true' \
    "$INSTALLED_RC"

grep -Fqx \
    'ShowFullPathInTitlebar=true' \
    "$INSTALLED_RC"

grep -Fqx \
    'Places Icons Auto-resize=false' \
    "$INSTALLED_RC"

grep -Fqx \
    'Places Icons Static Size=22' \
    "$INSTALLED_RC"

grep -Fqx \
    'MenuBar=Disabled' \
    "$INSTALLED_RC"

test ! -e "$DATA_UI"
test ! -e "$CONFIG_UI"

COLOR_SCHEME="$(
    kreadconfig6 \
        --file kdeglobals \
        --group General \
        --key ColorScheme
)"

ICON_THEME="$(
    kreadconfig6 \
        --file kdeglobals \
        --group Icons \
        --key Theme
)"

TERMINAL_PROFILE="$(
    kreadconfig6 \
        --file konsolerc \
        --group 'Desktop Entry' \
        --key DefaultProfile \
        2>/dev/null \
        || true
)"

echo "Color scheme:            $COLOR_SCHEME"
echo "Icon theme:              $ICON_THEME"
echo "Default terminal profile: $TERMINAL_PROFILE"

test "$COLOR_SCHEME" = "BreezeDark"
test "$ICON_THEME" = "breeze"
test "$TERMINAL_PROFILE" = "HELMMobile.profile"

echo '[PASS] Dolphin appearance and terminal integration are correct.'

echo
echo '===== OFFSCREEN STARTUP DIAGNOSTIC ====='

QT_PLUGIN_DIR="$(
    qmake6 -query QT_INSTALL_PLUGINS
)"

PLATFORM_DIR="$QT_PLUGIN_DIR/platforms"

test -f \
    "$PLATFORM_DIR/libqoffscreen.so"

TEST_ROOT="$TMP_DIR/offscreen"

mkdir -p \
    "$TEST_ROOT/config" \
    "$TEST_ROOT/data" \
    "$TEST_ROOT/cache" \
    "$TEST_ROOT/state"

install \
    -Dm644 \
    "$INSTALLED_RC" \
    "$TEST_ROOT/config/dolphinrc"

if [[ -f "$CONFIG_HOME/kdeglobals" ]]; then
    cp -f \
        "$CONFIG_HOME/kdeglobals" \
        "$TEST_ROOT/config/kdeglobals"
fi

if [[ -f "$CONFIG_HOME/kcminputrc" ]]; then
    cp -f \
        "$CONFIG_HOME/kcminputrc" \
        "$TEST_ROOT/config/kcminputrc"
fi

OUT="$TEST_ROOT/stdout.log"
ERR="$TEST_ROOT/stderr.log"

: > "$OUT"
: > "$ERR"

set +e

env \
    LC_ALL=C.UTF-8 \
    XDG_CONFIG_HOME="$TEST_ROOT/config" \
    XDG_DATA_HOME="$TEST_ROOT/data" \
    XDG_CACHE_HOME="$TEST_ROOT/cache" \
    XDG_STATE_HOME="$TEST_ROOT/state" \
    QT_QPA_PLATFORM=offscreen \
    QT_QPA_PLATFORM_PLUGIN_PATH="$PLATFORM_DIR" \
    KDE_FULL_SESSION=true \
    timeout \
        --foreground \
        --signal=TERM \
        --kill-after=2s \
        4s \
        dolphin \
            --new-window \
            "$HOME/.cyberdeck/nexus" \
        >"$OUT" \
        2>"$ERR"

STATUS=$?

set -e

if [[ "$STATUS" != 0 && "$STATUS" != 124 ]]; then
    echo "[FAIL] Unexpected Dolphin diagnostic status: $STATUS" >&2
    cat "$ERR" >&2
    exit 1
fi

if grep -Eqi \
    'could not (find|load).*platform plugin|no Qt platform plugin' \
    "$ERR"
then
    echo '[FAIL] Qt offscreen platform failed.' >&2
    cat "$ERR" >&2
    exit 1
fi

WARNING_COUNT="$(
    grep -Fc \
        'QGridLayout: Multi-cell fromRow greater than toRow' \
        "$ERR" \
        || true
)"

echo "Exit status: $STATUS"
echo "QGridLayout warning count: $WARNING_COUNT"

if (( WARNING_COUNT != 0 )); then
    echo '[FAIL] Dolphin Data Vault emitted the QGridLayout warning.' >&2
    cat "$ERR" >&2
    exit 1
fi

if [[ -s "$ERR" ]]; then
    echo 'Other diagnostic stderr:'
    cat "$ERR"
else
    echo '[PASS] No Dolphin diagnostic warnings.'
fi

if pgrep -x dolphin >/dev/null; then
    echo '[FAIL] Diagnostic Dolphin process remained active.' >&2
    pgrep -af '(^|/)dolphin( |$)' >&2 || true
    exit 1
fi

echo '[PASS] Native Dolphin interface starts without QGridLayout warnings.'

STATE_FILE="$STATE_FILE" \
RECOVERY_DIR="$RECOVERY_DIR" \
COLOR_SCHEME="$COLOR_SCHEME" \
ICON_THEME="$ICON_THEME" \
TERMINAL_PROFILE="$TERMINAL_PROFILE" \
python - <<'PY_STATE'
import json
import os
from datetime import datetime
from pathlib import Path

payload = {
    "stage": "3b-dolphin",
    "applied": datetime.now()
        .astimezone()
        .isoformat(),
    "recovery": os.environ["RECOVERY_DIR"],
    "toolbar_strategy": "native",
    "local_kxmlgui_override": False,
    "color_scheme": os.environ["COLOR_SCHEME"],
    "icon_theme": os.environ["ICON_THEME"],
    "terminal_profile": os.environ["TERMINAL_PROFILE"],
}

Path(os.environ["STATE_FILE"]).write_text(
    json.dumps(payload, indent=2) + "\n",
    encoding="utf-8",
)
PY_STATE

echo
echo 'STAGE 3B DOLPHIN: APPLIED'
echo "Recovery: $RECOVERY_DIR"
echo "State:    $STATE_FILE"
echo 'Dolphin remains closed.'
