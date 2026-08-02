#!/usr/bin/env bash
set -Eeuo pipefail

ARCHIVE="${1:-}"
MODE="${2:-}"
[[ -n "$ARCHIVE" ]] || {
    echo "Usage: helm restore ARCHIVE [--apply]"
    exit 2
}
[[ -f "$ARCHIVE" ]] || {
    echo "Archive not found: $ARCHIVE"
    exit 2
}

echo "HELM recovery archive:"
echo "  $ARCHIVE"
echo
echo "The restore covers:"
echo "  • HELM launchers and autostart"
echo "  • Plasma, lock screen, Dolphin and Konsole configuration"
echo "  • SDDM Access Gate"
echo "  • Plymouth Early Boot and systemd-boot entries"
echo "  • HELM runtime settings, workspaces and projects"
echo "  • Repository bundle stored inside the archive"
echo

if [[ "$MODE" != "--apply" ]]; then
    echo "Dry run only. To restore:"
    echo "  helm restore '$ARCHIVE' --apply"
    exit 0
fi

read -r -p "Type RESTORE to continue: " confirmation
[[ "$confirmation" == "RESTORE" ]] || {
    echo "Cancelled."
    exit 1
}

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
tar -C "$STAGE" -xzf "$ARCHIVE"

before="$HOME/.cyberdeck/backups/pre-restore-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$before"
cp -a "$HOME/.config/kscreenlockerrc" "$before/" 2>/dev/null || true
cp -a "$HOME/.local/bin/helm" "$before/" 2>/dev/null || true

if [[ -d "$STAGE/user-home" ]]; then
    cp -a "$STAGE/user-home"/. "$HOME"/
fi

if [[ -d "$STAGE/runtime-data" ]]; then
    runtime_path_file="$STAGE/meta/runtime-data-path.txt"
    [[ -f "$runtime_path_file" ]] || {
        echo "Runtime data path metadata is missing." >&2
        exit 1
    }

    runtime_target="$(<"$runtime_path_file")"

    [[ "$runtime_target" == /* \
        && "$runtime_target" != "/" \
        && "$runtime_target" != "$HOME" ]] || {
        echo "Unsafe runtime data target: $runtime_target" >&2
        exit 1
    }

    mkdir -p "$runtime_target"
    cp -a "$STAGE/runtime-data"/. "$runtime_target"/
fi

sudo cp -a "$STAGE/system/sddm.conf.d"/. /etc/sddm.conf.d/
sudo rm -rf /usr/share/sddm/themes/HELM-Access-Gate
sudo cp -a "$STAGE/system/HELM-Access-Gate" /usr/share/sddm/themes/HELM-Access-Gate
sudo cp -a "$STAGE/system/plymouth"/. /etc/plymouth/
sudo rm -rf /usr/share/plymouth/themes/helm-cyberdeck
sudo cp -a "$STAGE/system/helm-cyberdeck" /usr/share/plymouth/themes/helm-cyberdeck
sudo cp -a "$STAGE/system/mkinitcpio.conf.d"/. /etc/mkinitcpio.conf.d/
sudo cp -a "$STAGE/system/loader"/. /boot/loader/

chmod +x "$HOME/.local/bin/helm" "$HOME/.local/bin/helm-"* "$HOME/.local/bin/vault" 2>/dev/null || true
kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
sudo plymouth-set-default-theme helm-cyberdeck
sudo mkinitcpio -P

echo "Restore completed. Reboot after reviewing:"
echo "  helm doctor"
