#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
RECOVERY_DIR="$DATA_HOME/helm-mobile/recovery/stage2a-$STAMP"

mkdir -p "$RECOVERY_DIR"
mkdir -p "$DATA_HOME/helm-mobile"
mkdir -p "$HOME/Obrazy/HELM-Mobile"

for file in \
    kdeglobals \
    plasmarc \
    kcminputrc \
    kwinrc \
    konsolerc
do
    if [[ -f "$CONFIG_HOME/$file" ]]; then
        cp -a "$CONFIG_HOME/$file" "$RECOVERY_DIR/"
    fi
done

WALLPAPER_SOURCE="$ROOT_DIR/mobile/assets/wallpapers/helm-mobile-field-node.svg"
WALLPAPER_TARGET="$HOME/Obrazy/HELM-Mobile/helm-mobile-field-node.svg"

cp -f "$WALLPAPER_SOURCE" "$WALLPAPER_TARGET"

command -v plasma-apply-colorscheme >/dev/null
command -v plasma-apply-wallpaperimage >/dev/null
command -v kwriteconfig6 >/dev/null

plasma-apply-colorscheme BreezeDark
plasma-apply-wallpaperimage "$WALLPAPER_TARGET"

kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle Breeze
kwriteconfig6 --file kdeglobals --group Icons --key Theme breeze
kwriteconfig6 --file kcminputrc --group Mouse --key cursorTheme breeze_cursors
kwriteconfig6 --file plasmarc --group Theme --key name default

{
    echo "Stage: Stage 2A - Visual Foundation"
    echo "Timestamp: $STAMP"
    echo "Wallpaper: $WALLPAPER_TARGET"
    echo "Recovery: $RECOVERY_DIR"
} > "$DATA_HOME/helm-mobile/stage2a-last-apply.txt"

echo "Applied Stage 2A visual foundation."
echo "Wallpaper: $WALLPAPER_TARGET"
echo "Recovery:  $RECOVERY_DIR"
