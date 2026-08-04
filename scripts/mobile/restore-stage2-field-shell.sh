#!/usr/bin/env bash
set -Eeuo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_FILE="$DATA_HOME/helm-mobile/stage2-field-shell-last-apply.json"

command -v jq >/dev/null
test -s "$STATE_FILE"

RECOVERY_DIR="$(jq -r '.recovery' "$STATE_FILE")"
test -d "$RECOVERY_DIR"

for file in \
    kdeglobals \
    plasmarc \
    kcminputrc \
    plasma-org.kde.plasma.desktop-appletsrc \
    plasmashellrc
do
    if [[ -f "$RECOVERY_DIR/$file" ]]; then
        cp -f \
            "$RECOVERY_DIR/$file" \
            "$CONFIG_HOME/$file"
    fi
done

systemctl --user restart \
    plasma-plasmashell.service

for _ in {1..30}; do
    if systemctl --user is-active --quiet \
        plasma-plasmashell.service
    then
        echo 'Stage 2 Plasma configuration restored.'
        echo "Recovery source: $RECOVERY_DIR"
        exit 0
    fi

    sleep 1
done

echo '[FAIL] Plasma Shell did not return after restore.' >&2
exit 1
