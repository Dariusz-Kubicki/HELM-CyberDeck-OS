#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
SOURCE_THEME="$REPO/mobile/sddm/helm-mobile"
MANIFEST="$REPO/mobile/sddm/access-gate.json"
PYTHON="$REPO/venv/bin/python"

SYSTEM_THEME="/usr/share/sddm/themes/helm-mobile"
SYSTEM_CONFIG="/etc/sddm.conf.d/90-helm-mobile.conf"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE="$DATA_HOME/helm-mobile/stage4c-sddm-candidate-last-apply.json"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY="$DATA_HOME/helm-mobile/recovery/stage4c-sddm-apply-$STAMP"

PREVIOUS_DM=""
CHANGED=0
SUCCESS=0

rollback() {
    sudo rm -rf "$SYSTEM_THEME"
    sudo rm -f "$SYSTEM_CONFIG"

    if [[ -d "$RECOVERY/system-theme-before" ]]; then
        sudo cp -a "$RECOVERY/system-theme-before" "$SYSTEM_THEME"
        sudo chown -R root:root "$SYSTEM_THEME"
    fi

    if [[ -s "$RECOVERY/sddm-config-before.conf" ]]; then
        sudo cp -a "$RECOVERY/sddm-config-before.conf" "$SYSTEM_CONFIG"
        sudo chown root:root "$SYSTEM_CONFIG"
    fi

    sudo systemctl disable sddm.service >/dev/null 2>&1 || true
    sudo systemctl disable plasmalogin.service >/dev/null 2>&1 || true

    case "$PREVIOUS_DM" in
        */sddm.service)
            sudo systemctl enable --force sddm.service >/dev/null
            ;;
        */plasmalogin.service)
            sudo systemctl enable --force plasmalogin.service >/dev/null
            ;;
    esac

    sudo systemctl daemon-reload
}

cleanup() {
    local status=$?

    if (( status != 0 && CHANGED == 1 && SUCCESS == 0 )); then
        echo '[ROLLBACK] Restoring previous display-manager state.' >&2
        rollback
    fi

    exit "$status"
}

trap cleanup EXIT

echo '===== APPLY HELM MOBILE SDDM ACCESS GATE ====='

sudo -v

test -d "$SOURCE_THEME"
test -s "$MANIFEST"
test -x "$PYTHON"
test -x /usr/bin/sddm-greeter-qt6

for asset in Main.qml metadata.desktop theme.conf wallpaper.svg; do
    test -s "$SOURCE_THEME/$asset"
done

grep -Fqx '[SddmGreeterTheme]' "$SOURCE_THEME/metadata.desktop"
grep -Fqx 'QtVersion=6' "$SOURCE_THEME/metadata.desktop"
grep -Fq 'sddm.login(' "$SOURCE_THEME/Main.qml"
grep -Fq 'sddm.canPowerOff' "$SOURCE_THEME/Main.qml"

if grep -Fq 'HELM-PREVIEW-ONLY' "$SOURCE_THEME/Main.qml"; then
    echo '[FAIL] Source theme contains preview-only code.' >&2
    exit 1
fi

if ldd /usr/bin/sddm-greeter-qt6 | grep -Fq 'not found'; then
    echo '[FAIL] Qt 6 greeter has missing libraries.' >&2
    exit 1
fi

while IFS=$'\t' read -r asset expected; do
    actual="$(sha256sum "$SOURCE_THEME/$asset" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
        echo "[FAIL] Checksum mismatch: $asset" >&2
        exit 1
    fi
done < <(jq -r '.checksums | to_entries[] | [.key, .value] | @tsv' "$MANIFEST")

PREVIOUS_DM="$(readlink -f /etc/systemd/system/display-manager.service 2>/dev/null || true)"

mkdir -p "$RECOVERY"
printf '%s\n' "$PREVIOUS_DM" > "$RECOVERY/display-manager-before.txt"

if sudo test -d "$SYSTEM_THEME"; then
    sudo cp -a "$SYSTEM_THEME" "$RECOVERY/system-theme-before"
    sudo chown -R "$(id -u):$(id -g)" "$RECOVERY/system-theme-before"
fi

if sudo test -s "$SYSTEM_CONFIG"; then
    sudo cp -a "$SYSTEM_CONFIG" "$RECOVERY/sddm-config-before.conf"
    sudo chown "$(id -u):$(id -g)" "$RECOVERY/sddm-config-before.conf"
fi

CHANGED=1

sudo rm -rf "$SYSTEM_THEME"
sudo install -d -m 755 "$SYSTEM_THEME"
sudo cp -a "$SOURCE_THEME/." "$SYSTEM_THEME/"
sudo chown -R root:root "$SYSTEM_THEME"
sudo find "$SYSTEM_THEME" -type d -exec chmod 755 {} +
sudo find "$SYSTEM_THEME" -type f -exec chmod 644 {} +

sudo install -d -m 755 "$(dirname "$SYSTEM_CONFIG")"
sudo tee "$SYSTEM_CONFIG" >/dev/null <<'SDDM_CONFIG'
[General]
GreeterEnvironment=QT_QUICK_CONTROLS_STYLE=Basic

[Theme]
Current=helm-mobile
CursorTheme=breeze_cursors
Font=Hack

[Users]
RememberLastUser=true
RememberLastSession=true
SDDM_CONFIG

sudo chmod 644 "$SYSTEM_CONFIG"
sudo chown root:root "$SYSTEM_CONFIG"

for asset in Main.qml metadata.desktop theme.conf wallpaper.svg; do
    cmp "$SOURCE_THEME/$asset" <(sudo cat "$SYSTEM_THEME/$asset")
done

sudo systemctl disable plasmalogin.service >/dev/null 2>&1 || true
sudo systemctl enable --force sddm.service
sudo systemctl daemon-reload

NEXT_DM="$(readlink -f /etc/systemd/system/display-manager.service)"
test "$NEXT_DM" = "/usr/lib/systemd/system/sddm.service"

mkdir -p "$(dirname "$STATE")"

jq -n \
    --arg applied "$(date --iso-8601=seconds)" \
    --arg recovery "$RECOVERY" \
    --arg source_theme "$SOURCE_THEME" \
    --arg system_theme "$SYSTEM_THEME" \
    '{
        stage: "4c-sddm-access-gate",
        applied: $applied,
        recovery: $recovery,
        source_theme: $source_theme,
        system_theme: $system_theme,
        selected_qt_version: 6,
        selected_greeter: "/usr/bin/sddm-greeter-qt6",
        real_login_verified: false,
        next_boot_manager: "sddm.service"
    }' > "$STATE"

chmod 600 "$STATE"

SUCCESS=1

echo
echo '===== ACCESS GATE INSTALLED ====='
echo "Theme:    $SYSTEM_THEME"
echo "Recovery: $RECOVERY"
echo
echo 'Current graphical session was not restarted.'
echo 'Reboot to validate the real SDDM login.'
