#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
WALLPAPER=""
SKIP_BOOT=0

while (($#)); do
    case "$1" in
        --wallpaper)
            WALLPAPER="${2:-}"
            shift 2
            ;;
        --skip-boot)
            SKIP_BOOT=1
            shift
            ;;
        -h|--help)
            echo "Usage: helm install-desktop --wallpaper /absolute/path/image.png [--skip-boot]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 2
            ;;
    esac
done

[[ -n "$WALLPAPER" ]] || {
    echo "A local wallpaper is required and is intentionally not stored in Git."
    echo "Usage: helm install-desktop --wallpaper /absolute/path/image.png"
    exit 2
}
[[ -f "$WALLPAPER" ]] || { echo "Wallpaper not found: $WALLPAPER"; exit 2; }
WALLPAPER="$(realpath "$WALLPAPER")"

backup="$("$REPO/scripts/desktop/backup.sh" | tail -n 1)"
echo "Current state backed up: $backup"

install -Dm644 \
    "$REPO/desktop/plasma/color-schemes/HELMCyberdeck.colors" \
    "$HOME/.local/share/color-schemes/HELMCyberdeck.colors"

rm -rf "$HOME/.local/share/plasma/desktoptheme/HELM-Plasma"
mkdir -p "$HOME/.local/share/plasma/desktoptheme"
cp -a \
    "$REPO/desktop/plasma/desktoptheme/HELM-Plasma" \
    "$HOME/.local/share/plasma/desktoptheme/HELM-Plasma"

restore_template() {
    local source="$1" target="$2"
    [[ -f "$source" ]] || return 0
    mkdir -p "$(dirname "$target")"
    sed "s|__HOME__|$HOME|g" "$source" > "$target"
}

restore_template \
    "$REPO/desktop/apps/dolphin/dolphinrc.template" \
    "$HOME/.config/dolphinrc"
restore_template \
    "$REPO/desktop/apps/dolphin/user-places.xbel.template" \
    "$HOME/.local/share/user-places.xbel"
restore_template \
    "$REPO/desktop/apps/konsole/konsolerc.template" \
    "$HOME/.config/konsolerc"
restore_template \
    "$REPO/desktop/apps/kwin/kwinrulesrc.template" \
    "$HOME/.config/kwinrulesrc"
restore_template \
    "$REPO/desktop/plasma/layout/plasma-org.kde.plasma.desktop-appletsrc.template" \
    "$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc"
restore_template \
    "$REPO/desktop/plasma/lockscreen/kscreenlockerrc.template" \
    "$HOME/.config/kscreenlockerrc"

mkdir -p "$HOME/.local/share/kxmlgui5"
rm -rf "$HOME/.local/share/kxmlgui5/dolphin"
[[ -d "$REPO/desktop/apps/dolphin/kxmlgui5" ]] \
    && cp -a "$REPO/desktop/apps/dolphin/kxmlgui5" "$HOME/.local/share/kxmlgui5/dolphin"

mkdir -p "$HOME/.local/share/konsole"
cp -a "$REPO/desktop/apps/konsole/profiles"/. "$HOME/.local/share/konsole/" 2>/dev/null || true

install -Dm644 \
    "$REPO/desktop/conky/cyberdeck.conf" \
    "$HOME/.config/conky/cyberdeck.conf"

for file in "$REPO/desktop/launchers/"*; do
    [[ -f "$file" ]] || continue
    install -Dm755 "$file" "$HOME/.local/bin/$(basename "$file")"
done

for file in "$REPO/desktop/autostart/"*.desktop; do
    [[ -f "$file" ]] || continue
    install -Dm644 "$file" "$HOME/.config/autostart/$(basename "$file")"
done

install -Dm644 \
    "$REPO/desktop/apps/helm-data-vault.desktop" \
    "$HOME/.local/share/applications/helm-data-vault.desktop"

profile="$(find "$HOME/.config/mozilla/firefox" -maxdepth 1 \
    -type d -name '*.default-release' -print -quit 2>/dev/null || true)"
if [[ -n "$profile" && -f "$REPO/desktop/apps/firefox/userChrome.css" ]]; then
    install -Dm644 \
        "$REPO/desktop/apps/firefox/userChrome.css" \
        "$profile/chrome/userChrome.css"
fi

"$REPO/scripts/desktop/rebuild-lockscreen.sh"

kwriteconfig6 --file kdeglobals --group General --key ColorScheme HELMCyberdeck
kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle Breeze
kwriteconfig6 --file plasmarc --group Theme --key name HELM-Plasma

kwriteconfig6 \
    --file kscreenlockerrc \
    --group Greeter --group Wallpaper --group org.kde.image --group General \
    --key Image "file://$WALLPAPER"
kwriteconfig6 \
    --file kscreenlockerrc \
    --group Greeter --group Wallpaper --group org.kde.image --group General \
    --key PreviewImage "file://$WALLPAPER"

sudo rm -rf /usr/share/sddm/themes/HELM-Access-Gate
sudo cp -a \
    "$REPO/desktop/sddm/HELM-Access-Gate" \
    /usr/share/sddm/themes/HELM-Access-Gate
sudo install -m 644 "$WALLPAPER" \
    /usr/share/sddm/themes/HELM-Access-Gate/background.png
sudo install -Dm644 \
    "$REPO/desktop/sddm/zz-helm-theme.conf" \
    /etc/sddm.conf.d/zz-helm-theme.conf
sudo chown -R root:root /usr/share/sddm/themes/HELM-Access-Gate
sudo chmod -R a+rX /usr/share/sddm/themes/HELM-Access-Gate

if (( ! SKIP_BOOT )); then
    root_uuid="$(findmnt -no UUID /)"
    [[ -n "$root_uuid" ]] || { echo "Cannot determine root UUID."; exit 1; }

    sudo rm -rf /usr/share/plymouth/themes/helm-cyberdeck
    sudo cp -a \
        "$REPO/desktop/plymouth/helm-cyberdeck" \
        /usr/share/plymouth/themes/helm-cyberdeck
    sudo chown -R root:root /usr/share/plymouth/themes/helm-cyberdeck
    sudo chmod -R a+rX /usr/share/plymouth/themes/helm-cyberdeck

    sudo install -Dm644 \
        "$REPO/desktop/plymouth/plymouthd.conf" \
        /etc/plymouth/plymouthd.conf
    sudo install -Dm644 \
        "$REPO/desktop/boot/90-helm-plymouth.conf" \
        /etc/mkinitcpio.conf.d/90-helm-plymouth.conf
    sudo install -Dm644 \
        "$REPO/desktop/boot/loader.conf" \
        /boot/loader/loader.conf

    sed "s/__ROOT_UUID__/$root_uuid/g" "$REPO/desktop/boot/arch.conf.template" \
        | sudo tee /boot/loader/entries/arch.conf >/dev/null
    sed "s/__ROOT_UUID__/$root_uuid/g" "$REPO/desktop/boot/arch-diagnostic.conf.template" \
        | sudo tee /boot/loader/entries/arch-diagnostic.conf >/dev/null

    sudo plymouth-set-default-theme helm-cyberdeck
    sudo mkinitcpio -P
    sudo bootctl set-default arch.conf
fi

kbuildsycoca6 --noincremental >/dev/null 2>&1 || true

echo "HELM CyberDeck Desktop installed."
echo "Run: helm doctor"
echo "Reboot after all checks pass."
