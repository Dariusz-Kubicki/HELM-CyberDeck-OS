#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST_DIR="$HOME/.cyberdeck/backups"
ARCHIVE="$DEST_DIR/helm-cyberdeck-$STAMP.tar.gz"
STAGE="$(mktemp -d)"

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

mkdir -p \
    "$DEST_DIR" \
    "$STAGE/user-home" \
    "$STAGE/system" \
    "$STAGE/meta"

copy_user() {
    local source="$1"
    local relative="$2"
    [[ -e "$source" ]] || return 0
    mkdir -p "$STAGE/user-home/$(dirname "$relative")"
    cp -a "$source" "$STAGE/user-home/$relative"
}

copy_user "$HOME/.config/helm" ".config/helm"
copy_user "$HOME/.config/conky" ".config/conky"
copy_user "$HOME/.config/autostart/helm-cyberdeck.desktop" ".config/autostart/helm-cyberdeck.desktop"
copy_user "$HOME/.config/autostart/helm-desktop-node.desktop" ".config/autostart/helm-desktop-node.desktop"
copy_user "$HOME/.config/dolphinrc" ".config/dolphinrc"
copy_user "$HOME/.config/konsolerc" ".config/konsolerc"
copy_user "$HOME/.config/kwinrulesrc" ".config/kwinrulesrc"
copy_user "$HOME/.config/kscreenlockerrc" ".config/kscreenlockerrc"
copy_user "$HOME/.config/ksplashrc" ".config/ksplashrc"
copy_user "$HOME/.config/plasmarc" ".config/plasmarc"
copy_user "$HOME/.config/kdeglobals" ".config/kdeglobals"
copy_user "$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc" ".config/plasma-org.kde.plasma.desktop-appletsrc"
copy_user "$HOME/.local/bin/helm" ".local/bin/helm"
copy_user "$HOME/.local/bin/helm-start" ".local/bin/helm-start"
copy_user "$HOME/.local/bin/helm-run" ".local/bin/helm-run"
copy_user "$HOME/.local/bin/helm-conky-start" ".local/bin/helm-conky-start"
copy_user "$HOME/.local/bin/helm-conky-status" ".local/bin/helm-conky-status"
copy_user "$HOME/.local/bin/vault" ".local/bin/vault"
copy_user "$HOME/.local/share/applications/helm-data-vault.desktop" ".local/share/applications/helm-data-vault.desktop"
copy_user "$HOME/.local/share/color-schemes/HELMCyberdeck.colors" ".local/share/color-schemes/HELMCyberdeck.colors"
copy_user "$HOME/.local/share/plasma/desktoptheme/HELM-Plasma" ".local/share/plasma/desktoptheme/HELM-Plasma"
copy_user "$HOME/.local/share/plasma/shells/org.kde.plasma.desktop" ".local/share/plasma/shells/org.kde.plasma.desktop"
copy_user "$HOME/.local/share/konsole" ".local/share/konsole"
copy_user "$HOME/.local/share/kxmlgui5/dolphin" ".local/share/kxmlgui5/dolphin"
copy_user "$HOME/.local/share/user-places.xbel" ".local/share/user-places.xbel"

firefox_css="$(find "$HOME/.config/mozilla/firefox" -maxdepth 3 \
    -type f -path '*/chrome/userChrome.css' -print -quit 2>/dev/null || true)"
if [[ -n "$firefox_css" ]]; then
    copy_user "$firefox_css" ".config/helm-backup/firefox/userChrome.css"
fi

wallpaper_uri="$(kreadconfig6 --file kscreenlockerrc \
    --group Greeter --group Wallpaper --group org.kde.image --group General \
    --key Image 2>/dev/null || true)"
wallpaper="${wallpaper_uri#file://}"
if [[ -n "$wallpaper" && -f "$wallpaper" ]]; then
    copy_user "$wallpaper" ".config/helm-backup/wallpaper/$(basename "$wallpaper")"
fi

sudo cp -a /etc/sddm.conf.d "$STAGE/system/sddm.conf.d"
sudo cp -a /usr/share/sddm/themes/HELM-Access-Gate "$STAGE/system/HELM-Access-Gate"
sudo cp -a /etc/plymouth "$STAGE/system/plymouth"
sudo cp -a /usr/share/plymouth/themes/helm-cyberdeck "$STAGE/system/helm-cyberdeck"
sudo cp -a /etc/mkinitcpio.conf.d "$STAGE/system/mkinitcpio.conf.d"
sudo cp -a /boot/loader "$STAGE/system/loader"
sudo chown -R "$USER:$USER" "$STAGE/system"

git -C "$REPO" bundle create "$STAGE/meta/repository.bundle" --all
git -C "$REPO" status --short --branch > "$STAGE/meta/git-status.txt"
pacman -Q > "$STAGE/meta/packages.txt"
date --iso-8601=seconds > "$STAGE/meta/created-at.txt"

tar -C "$STAGE" -czf "$ARCHIVE" .
ln -sfn "$ARCHIVE" "$DEST_DIR/helm-cyberdeck-latest.tar.gz"

printf 'Backup created:\n%s\n' "$ARCHIVE"
