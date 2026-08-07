#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

MODE="${1:-next-boot}"

case "$MODE" in
    next-boot | --now)
        ;;
    *)
        echo 'Usage: restore-stage4c-sddm-access-gate.sh [next-boot|--now]' >&2
        exit 2
        ;;
esac

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE="$DATA_HOME/helm-mobile/stage4c-sddm-candidate-last-apply.json"
SYSTEM_THEME="/usr/share/sddm/themes/helm-mobile"
SYSTEM_CONFIG="/etc/sddm.conf.d/90-helm-mobile.conf"
RECOVERY=""

if [[ -s "$STATE" ]]; then
    RECOVERY="$(jq -r '.recovery // empty' "$STATE")"
fi

echo '===== RESTORE PLASMA LOGIN MANAGER ====='

sudo -v

if [[ "$MODE" == "--now" ]]; then
    sudo systemctl stop sddm.service 2>/dev/null || true
fi

sudo systemctl disable sddm.service >/dev/null 2>&1 || true
sudo systemctl enable --force plasmalogin.service
sudo rm -rf "$SYSTEM_THEME"
sudo rm -f "$SYSTEM_CONFIG"

if [[ -n "$RECOVERY" && -d "$RECOVERY/system-theme-before" ]]; then
    sudo cp -a "$RECOVERY/system-theme-before" "$SYSTEM_THEME"
    sudo chown -R root:root "$SYSTEM_THEME"
fi

if [[ -n "$RECOVERY" && -s "$RECOVERY/sddm-config-before.conf" ]]; then
    sudo cp -a "$RECOVERY/sddm-config-before.conf" "$SYSTEM_CONFIG"
    sudo chown root:root "$SYSTEM_CONFIG"
fi

rm -f "$STATE"
sudo systemctl daemon-reload
sudo systemctl reset-failed sddm.service plasmalogin.service >/dev/null 2>&1 || true

if [[ "$MODE" == "--now" ]]; then
    sudo systemctl start plasmalogin.service
    sleep 3
    sudo chvt 1 2>/dev/null || true
fi

echo
echo '[PASS] Plasma Login Manager enabled.'
echo '[PASS] HELM SDDM configuration removed.'

if [[ "$MODE" == "next-boot" ]]; then
    echo 'The change will take effect at the next boot.'
fi
