#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

PYTHON_BIN="${PYTHON_BIN:-$REPO/venv/bin/python}"

SYSTEM_SHELL="/usr/share/plasma/shells/org.kde.plasma.desktop"
TARGET_SHELL="$DATA_HOME/plasma/shells/org.kde.plasma.desktop"

LOCK_DIR="$TARGET_SHELL/contents/lockscreen"
LOCK_QML="$LOCK_DIR/LockScreen.qml"
INSTALLED_OVERLAY="$LOCK_DIR/HELMOverlay.qml"

SOURCE_OVERLAY="$REPO/mobile/plasma/lockscreen/HELMOverlay.qml"
SOURCE_MANIFEST="$REPO/mobile/plasma/lockscreen/lockscreen.json"

WALLPAPER_SOURCE="$REPO/mobile/assets/wallpapers/helm-mobile-field-node-v2.svg"
WALLPAPER_TARGET="$DATA_HOME/helm-mobile/wallpapers/helm-mobile-field-node-v2.svg"

LOCK_CONFIG="$CONFIG_HOME/kscreenlockerrc"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY="$DATA_HOME/helm-mobile/recovery/stage4b-lockscreen-$STAMP"
STATE="$DATA_HOME/helm-mobile/stage4b-lockscreen-last-apply.json"

HAD_TARGET=0
HAD_CONFIG=0
HAD_WALLPAPER=0

LIVE_TOUCHED=0
SUCCESS=0

restore_file() {
    local destination="$1"
    local backup="$2"
    local existed="$3"

    if [[ "$existed" == "1" ]]; then
        mkdir -p "$(dirname "$destination")"
        cp -a "$backup" "$destination"
    else
        rm -f "$destination"
    fi
}

rollback() {
    local status=$?

    if (( SUCCESS == 0 && LIVE_TOUCHED == 1 )); then
        echo
        echo '[ROLLBACK] Restoring previous lock-screen state...' >&2

        rm -rf "$TARGET_SHELL"

        if (( HAD_TARGET == 1 )); then
            mkdir -p "$(dirname "$TARGET_SHELL")"

            cp -a \
                "$RECOVERY/plasma-shell" \
                "$TARGET_SHELL"
        fi

        restore_file \
            "$LOCK_CONFIG" \
            "$RECOVERY/kscreenlockerrc" \
            "$HAD_CONFIG"

        restore_file \
            "$WALLPAPER_TARGET" \
            "$RECOVERY/wallpaper.svg" \
            "$HAD_WALLPAPER"

        kbuildsycoca6 --noincremental \
            >/dev/null 2>&1 \
            || true

        echo '[ROLLBACK] Previous lock-screen state restored.' >&2
    fi

    exit "$status"
}

trap rollback EXIT

echo '===== APPLY HELM MOBILE SECURITY LOCK ====='

for command_name in \
    "$PYTHON_BIN" \
    kwriteconfig6 \
    kreadconfig6 \
    kbuildsycoca6 \
    sha256sum
do
    command -v "$command_name" >/dev/null
done

test -d "$SYSTEM_SHELL"
test -s "$SYSTEM_SHELL/contents/lockscreen/LockScreen.qml"

test -s "$SOURCE_OVERLAY"
test -s "$SOURCE_MANIFEST"
test -s "$WALLPAPER_SOURCE"

"$PYTHON_BIN" \
    - "$SOURCE_MANIFEST" \
    >/dev/null <<'PY_MANIFEST'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

if payload.get("stage") != "4b-security-lock":
    raise SystemExit(
        "Invalid Security Lock manifest stage."
    )

authentication = payload.get(
    "authentication",
    {},
)

if authentication.get("modified") is not False:
    raise SystemExit(
        "Authentication modification is not allowed."
    )

behavior = payload.get(
    "behavior",
    {},
)

for key in (
    "automatic_lock_settings_modified",
    "authentication_flow_modified",
    "session_unlocking_modified",
):
    if behavior.get(key) is not False:
        raise SystemExit(
            f"Unsafe lock-screen behavior: {key}"
        )
PY_MANIFEST

mkdir -p "$RECOVERY"

if [[ -e "$TARGET_SHELL" ]]; then
    cp -a \
        "$TARGET_SHELL" \
        "$RECOVERY/plasma-shell"

    HAD_TARGET=1
fi

if [[ -e "$LOCK_CONFIG" ]]; then
    cp -a \
        "$LOCK_CONFIG" \
        "$RECOVERY/kscreenlockerrc"

    HAD_CONFIG=1
fi

if [[ -e "$WALLPAPER_TARGET" ]]; then
    cp -a \
        "$WALLPAPER_TARGET" \
        "$RECOVERY/wallpaper.svg"

    HAD_WALLPAPER=1
fi

{
    echo "created=$(date --iso-8601=seconds)"
    echo "target_shell=$TARGET_SHELL"
    echo "lock_config=$LOCK_CONFIG"
    echo "wallpaper_target=$WALLPAPER_TARGET"
    echo "had_target=$HAD_TARGET"
    echo "had_config=$HAD_CONFIG"
    echo "had_wallpaper=$HAD_WALLPAPER"
} > "$RECOVERY/recovery-info.txt"

LIVE_TOUCHED=1

rm -rf "$TARGET_SHELL"

mkdir -p "$(dirname "$TARGET_SHELL")"

cp -a \
    "$SYSTEM_SHELL" \
    "$TARGET_SHELL"

test -s "$LOCK_QML"

install \
    -Dm644 \
    "$SOURCE_OVERLAY" \
    "$INSTALLED_OVERLAY"

LOCK_QML="$LOCK_QML" \
"$PYTHON_BIN" - <<'PY_PATCH'
import os
from pathlib import Path

path = Path(os.environ["LOCK_QML"])

text = path.read_text(
    encoding="utf-8"
)

marker = "HELM MOBILE SECURITY OVERLAY"

if marker in text:
    raise SystemExit(
        "Unexpected HELM marker in clean system shell."
    )

if "LockScreenUi" not in text:
    raise SystemExit(
        "Unsupported Plasma LockScreen.qml structure."
    )

closing = text.rfind("\n}")

if closing == -1:
    raise SystemExit(
        "Root QML closing brace not found."
    )

injection = """
    /*
     * HELM MOBILE SECURITY OVERLAY
     * Visual layer only. Plasma remains responsible
     * for authentication and session unlocking.
     */
    HELMOverlay {
        anchors.fill: parent
    }
"""

patched = (
    text[:closing]
    + injection
    + text[closing:]
)

if patched.count(
    "HELMOverlay {"
) != 1:
    raise SystemExit(
        "Invalid HELMOverlay instance count."
    )

path.write_text(
    patched,
    encoding="utf-8",
)
PY_PATCH

install \
    -Dm644 \
    "$WALLPAPER_SOURCE" \
    "$WALLPAPER_TARGET"

WALLPAPER_URI="$(
    WALLPAPER_TARGET="$WALLPAPER_TARGET" \
    "$PYTHON_BIN" - <<'PY_URI'
import os
from pathlib import Path

print(
    Path(
        os.environ["WALLPAPER_TARGET"]
    ).resolve().as_uri()
)
PY_URI
)"

kwriteconfig6 \
    --file kscreenlockerrc \
    --group Greeter \
    --key Theme \
    org.kde.plasma.desktop

kwriteconfig6 \
    --file kscreenlockerrc \
    --group Greeter \
    --key WallpaperPlugin \
    org.kde.image

kwriteconfig6 \
    --file kscreenlockerrc \
    --group Greeter \
    --group Wallpaper \
    --group org.kde.image \
    --group General \
    --key Image \
    "$WALLPAPER_URI"

kwriteconfig6 \
    --file kscreenlockerrc \
    --group Greeter \
    --group Wallpaper \
    --group org.kde.image \
    --group General \
    --key PreviewImage \
    "$WALLPAPER_URI"

kbuildsycoca6 --noincremental \
    >/dev/null 2>&1 \
    || true

cmp \
    "$SOURCE_OVERLAY" \
    "$INSTALLED_OVERLAY"

cmp \
    "$WALLPAPER_SOURCE" \
    "$WALLPAPER_TARGET"

grep -Fq \
    'HELM MOBILE SECURITY OVERLAY' \
    "$LOCK_QML"

test "$(
    grep -Fc \
        'HELMOverlay {' \
        "$LOCK_QML"
)" = "1"

test "$(
    kreadconfig6 \
        --file kscreenlockerrc \
        --group Greeter \
        --key Theme
)" = "org.kde.plasma.desktop"

test "$(
    kreadconfig6 \
        --file kscreenlockerrc \
        --group Greeter \
        --key WallpaperPlugin
)" = "org.kde.image"

test "$(
    kreadconfig6 \
        --file kscreenlockerrc \
        --group Greeter \
        --group Wallpaper \
        --group org.kde.image \
        --group General \
        --key Image
)" = "$WALLPAPER_URI"

OVERLAY_SHA="$(
    sha256sum "$SOURCE_OVERLAY" |
    awk '{print $1}'
)"

WALLPAPER_SHA="$(
    sha256sum "$WALLPAPER_SOURCE" |
    awk '{print $1}'
)"

mkdir -p "$(dirname "$STATE")"

STATE_TMP="$STATE.tmp.$$"

STATE="$STATE_TMP" \
RECOVERY="$RECOVERY" \
TARGET_SHELL="$TARGET_SHELL" \
LOCK_CONFIG="$LOCK_CONFIG" \
WALLPAPER_TARGET="$WALLPAPER_TARGET" \
OVERLAY_SHA="$OVERLAY_SHA" \
WALLPAPER_SHA="$WALLPAPER_SHA" \
HAD_TARGET="$HAD_TARGET" \
HAD_CONFIG="$HAD_CONFIG" \
HAD_WALLPAPER="$HAD_WALLPAPER" \
"$PYTHON_BIN" - <<'PY_STATE'
import json
import os
from datetime import datetime
from pathlib import Path

state = {
    "stage": "4b-security-lock",
    "applied": (
        datetime.now()
        .astimezone()
        .isoformat()
    ),
    "recovery": os.environ["RECOVERY"],
    "target_shell": os.environ["TARGET_SHELL"],
    "lock_config": os.environ["LOCK_CONFIG"],
    "wallpaper_target": os.environ[
        "WALLPAPER_TARGET"
    ],
    "overlay_sha256": os.environ[
        "OVERLAY_SHA"
    ],
    "wallpaper_sha256": os.environ[
        "WALLPAPER_SHA"
    ],
    "had_target": (
        os.environ["HAD_TARGET"] == "1"
    ),
    "had_config": (
        os.environ["HAD_CONFIG"] == "1"
    ),
    "had_wallpaper": (
        os.environ["HAD_WALLPAPER"] == "1"
    ),
}

Path(os.environ["STATE"]).write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY_STATE

chmod 600 "$STATE_TMP"
mv -f "$STATE_TMP" "$STATE"

SUCCESS=1

echo "Recovery:   $RECOVERY"
echo "State file: $STATE"
echo 'HELM Mobile Security Lock installed.'
echo 'Authentication and automatic-lock behavior remain unchanged.'
echo 'No service restart or reboot is required.'
