#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
SOURCE="/usr/share/plasma/shells/org.kde.plasma.desktop"
TARGET="$HOME/.local/share/plasma/shells/org.kde.plasma.desktop"
CUSTOM="$REPO/desktop/plasma/lockscreen/LockScreen.qml"
STAMP="$(date +%Y%m%d-%H%M%S)"

[[ -d "$SOURCE" ]] || { echo "Missing system Plasma shell: $SOURCE"; exit 1; }
[[ -f "$CUSTOM" ]] || { echo "Missing HELM LockScreen.qml: $CUSTOM"; exit 1; }

if [[ -d "$TARGET" ]]; then
    backup="$HOME/.cyberdeck/backups/lockscreen-shell-$STAMP"
    mkdir -p "$(dirname "$backup")"
    cp -a "$TARGET" "$backup"
    echo "Previous shell backed up to: $backup"
fi

rm -rf "$TARGET"
mkdir -p "$(dirname "$TARGET")"
cp -a "$SOURCE" "$TARGET"
install -m 644 "$CUSTOM" "$TARGET/contents/lockscreen/LockScreen.qml"

kwriteconfig6 \
    --file kscreenlockerrc \
    --group Greeter \
    --key Theme \
    org.kde.plasma.desktop

kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
echo "HELM Security Lock rebuilt."
