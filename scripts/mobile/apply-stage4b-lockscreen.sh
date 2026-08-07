#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

SYSTEM_SHELL="/usr/share/plasma/shells/org.kde.plasma.desktop"
SYSTEM_LOCK="$SYSTEM_SHELL/contents/lockscreen"

TARGET_SHELL="$DATA_HOME/plasma/shells/org.kde.plasma.desktop"
LOCK_DIR="$TARGET_SHELL/contents/lockscreen"

SOURCE_DIR="$REPO/mobile/plasma/lockscreen"
MANIFEST="$SOURCE_DIR/lockscreen.json"

WALLPAPER_SOURCE="$REPO/mobile/assets/wallpapers/helm-mobile-field-node-v2.svg"
WALLPAPER_TARGET="$DATA_HOME/helm-mobile/wallpapers/helm-mobile-field-node-v2.svg"

LOCK_CONFIG="$CONFIG_HOME/kscreenlockerrc"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY="$DATA_HOME/helm-mobile/recovery/stage4b-lockscreen-v2-1-$STAMP"
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
            cp -a "$RECOVERY/plasma-shell" "$TARGET_SHELL"
        fi

        restore_file \
            "$LOCK_CONFIG" \
            "$RECOVERY/kscreenlockerrc" \
            "$HAD_CONFIG"

        restore_file \
            "$WALLPAPER_TARGET" \
            "$RECOVERY/wallpaper.svg" \
            "$HAD_WALLPAPER"

        kbuildsycoca6 --noincremental >/dev/null 2>&1 || true

        echo '[ROLLBACK] Previous lock-screen state restored.' >&2
    fi

    exit "$status"
}

trap rollback EXIT

echo '===== APPLY HELM MOBILE SECURITY LOCK V2.1 ====='

for command_name in \
    jq \
    kwriteconfig6 \
    kreadconfig6 \
    kbuildsycoca6 \
    sha256sum
do
    command -v "$command_name" >/dev/null
done

test -d "$SYSTEM_LOCK"
test -s "$MANIFEST"
test -s "$WALLPAPER_SOURCE"

for file in \
    LockScreen.qml \
    LockScreenUi.qml \
    MainBlock.qml \
    HELMOverlay.qml
do
    test -s "$SOURCE_DIR/$file"
done

jq -e \
    '.stage == "4b-security-lock"
     and .revision == "2.1"
     and .authentication.modified == false
     and .authentication.native_authenticator_preserved == true
     and .behavior.automatic_lock_settings_modified == false
     and .behavior.authentication_flow_modified == false
     and .behavior.session_unlocking_modified == false' \
    "$MANIFEST" >/dev/null

for file in \
    LockScreen.qml \
    LockScreenUi.qml \
    MainBlock.qml
do
    expected="$(
        jq -r \
            --arg file "$file" \
            '.shell.base_system_sha256[$file]' \
            "$MANIFEST"
    )"

    actual="$(
        sha256sum "$SYSTEM_LOCK/$file" |
        awk '{print $1}'
    )"

    if [[ "$actual" != "$expected" ]]; then
        echo "[FAIL] KDE baseline changed: $file" >&2
        echo "Expected: $expected" >&2
        echo "Actual:   $actual" >&2
        echo 'Rebase the Security Lock UI before applying it to this Plasma version.' >&2
        exit 1
    fi
done

for file in \
    LockScreen.qml \
    LockScreenUi.qml \
    MainBlock.qml \
    HELMOverlay.qml
do
    expected="$(
        jq -r \
            --arg file "$file" \
            '.shell.approved_sha256[$file]' \
            "$MANIFEST"
    )"

    actual="$(
        sha256sum "$SOURCE_DIR/$file" |
        awk '{print $1}'
    )"

    test "$actual" = "$expected"
done

grep -Fq 'authenticator.respond(password)' "$SOURCE_DIR/LockScreenUi.qml"
grep -Fq 'signal passwordResult(string password)' "$SOURCE_DIR/MainBlock.qml"
grep -Fq 'passwordResult(password)' "$SOURCE_DIR/MainBlock.qml"
grep -Fq '// HELM-STYLE: security-lock-controls-v2' "$SOURCE_DIR/MainBlock.qml"
grep -Fq 'NATIVE KSCREENLOCKER CREDENTIAL FLOW' "$SOURCE_DIR/HELMOverlay.qml"

if grep -RqsE \
    'LD_PRELOAD|HELM_PLASMA_LOGIN_MAIN_QML|libhelm-plasmalogin-mainqml|/etc/pam[.]d' \
    "$SOURCE_DIR"
then
    echo '[FAIL] Unsafe lock-screen integration detected.' >&2
    exit 1
fi

mkdir -p "$RECOVERY"

if [[ -e "$TARGET_SHELL" ]]; then
    cp -a "$TARGET_SHELL" "$RECOVERY/plasma-shell"
    HAD_TARGET=1
fi

if [[ -e "$LOCK_CONFIG" ]]; then
    cp -a "$LOCK_CONFIG" "$RECOVERY/kscreenlockerrc"
    HAD_CONFIG=1
fi

if [[ -e "$WALLPAPER_TARGET" ]]; then
    cp -a "$WALLPAPER_TARGET" "$RECOVERY/wallpaper.svg"
    HAD_WALLPAPER=1
fi

{
    echo "created=$(date --iso-8601=seconds)"
    echo "revision=2.1"
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
cp -a "$SYSTEM_SHELL" "$TARGET_SHELL"

for file in \
    LockScreen.qml \
    LockScreenUi.qml \
    MainBlock.qml \
    HELMOverlay.qml
do
    install \
        -Dm644 \
        "$SOURCE_DIR/$file" \
        "$LOCK_DIR/$file"
done

install \
    -Dm644 \
    "$WALLPAPER_SOURCE" \
    "$WALLPAPER_TARGET"

WALLPAPER_URI="$(
    python -c \
        'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().as_uri())' \
        "$WALLPAPER_TARGET"
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

kbuildsycoca6 --noincremental >/dev/null 2>&1 || true

for file in \
    LockScreen.qml \
    LockScreenUi.qml \
    MainBlock.qml \
    HELMOverlay.qml
do
    cmp "$SOURCE_DIR/$file" "$LOCK_DIR/$file"
done

cmp "$WALLPAPER_SOURCE" "$WALLPAPER_TARGET"

grep -Fq 'authenticator.respond(password)' "$LOCK_DIR/LockScreenUi.qml"
grep -Fq 'signal passwordResult(string password)' "$LOCK_DIR/MainBlock.qml"
grep -Fq 'HELMOverlay {' "$LOCK_DIR/LockScreen.qml"

test "$(
    kreadconfig6 \
        --file kscreenlockerrc \
        --group Greeter \
        --key Theme
)" = "org.kde.plasma.desktop"

OVERLAY_SHA="$(sha256sum "$SOURCE_DIR/HELMOverlay.qml" | awk '{print $1}')"
LOCK_SHA="$(sha256sum "$SOURCE_DIR/LockScreen.qml" | awk '{print $1}')"
LOCK_UI_SHA="$(sha256sum "$SOURCE_DIR/LockScreenUi.qml" | awk '{print $1}')"
MAIN_BLOCK_SHA="$(sha256sum "$SOURCE_DIR/MainBlock.qml" | awk '{print $1}')"
WALLPAPER_SHA="$(sha256sum "$WALLPAPER_SOURCE" | awk '{print $1}')"

mkdir -p "$(dirname "$STATE")"

jq -n \
    --arg applied "$(date --iso-8601=seconds)" \
    --arg recovery "$RECOVERY" \
    --arg target_shell "$TARGET_SHELL" \
    --arg lock_config "$LOCK_CONFIG" \
    --arg wallpaper_target "$WALLPAPER_TARGET" \
    --arg overlay_sha "$OVERLAY_SHA" \
    --arg lock_sha "$LOCK_SHA" \
    --arg lock_ui_sha "$LOCK_UI_SHA" \
    --arg main_block_sha "$MAIN_BLOCK_SHA" \
    --arg wallpaper_sha "$WALLPAPER_SHA" \
    --argjson had_target "$([[ "$HAD_TARGET" == 1 ]] && echo true || echo false)" \
    --argjson had_config "$([[ "$HAD_CONFIG" == 1 ]] && echo true || echo false)" \
    --argjson had_wallpaper "$([[ "$HAD_WALLPAPER" == 1 ]] && echo true || echo false)" \
    '{
      stage: "4b-security-lock",
      visual_revision: "2.1",
      applied: $applied,
      recovery: $recovery,
      target_shell: $target_shell,
      lock_config: $lock_config,
      wallpaper_target: $wallpaper_target,
      overlay_sha256: $overlay_sha,
      lockscreen_sha256: $lock_sha,
      lockscreen_ui_sha256: $lock_ui_sha,
      main_block_sha256: $main_block_sha,
      wallpaper_sha256: $wallpaper_sha,
      had_target: $had_target,
      had_config: $had_config,
      had_wallpaper: $had_wallpaper,
      real_unlock_verified: false
    }' > "$STATE.tmp.$$"

chmod 600 "$STATE.tmp.$$"
mv -f "$STATE.tmp.$$" "$STATE"

SUCCESS=1

echo "Recovery:   $RECOVERY"
echo "State file: $STATE"
echo 'HELM Mobile Security Lock v2.1 installed.'
echo 'Native KScreenLocker authentication remains unchanged.'
echo 'No service restart or reboot is required.'
echo 'Run Win+L and verify a real password unlock; the state starts as unverified.'
