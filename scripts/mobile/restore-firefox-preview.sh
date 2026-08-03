#!/usr/bin/env bash
set -Eeuo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE_FILE="$DATA_HOME/helm-mobile/firefox-preview-state.txt"

if pgrep -x firefox >/dev/null 2>&1; then
    echo '[STOP] Zamknij całkowicie Firefoksa przed przywracaniem.' >&2
    exit 2
fi

test -f "$STATE_FILE"

read_value() {
    local key="$1"
    awk -F= -v key="$key" '
        $1 == key {
            sub(/^[^=]*=/, "")
            print
            exit
        }
    ' "$STATE_FILE"
}

profile="$(read_value profile)"
recovery="$(read_value recovery)"
had_userchrome="$(read_value had_userchrome)"
had_userjs="$(read_value had_userjs)"

test -d "$profile"
test -d "$recovery"

if [[ "$had_userchrome" == "1" ]]; then
    cp -f "$recovery/userChrome.css" "$profile/chrome/userChrome.css"
else
    rm -f "$profile/chrome/userChrome.css"
fi

if [[ "$had_userjs" == "1" ]]; then
    cp -f "$recovery/user.js" "$profile/user.js"
else
    rm -f "$profile/user.js"
fi

echo 'Firefox preview restored.'
echo 'Uruchom Firefoksa ponownie.'
