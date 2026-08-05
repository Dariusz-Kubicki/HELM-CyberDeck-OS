#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
FIREFOX_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox"

PYTHON_BIN="${PYTHON_BIN:-python}"

SOURCE="$REPO/mobile/apps/firefox/userChrome.css"
RESOLVER="$REPO/scripts/mobile/resolve-firefox-profile.py"

STAMP="$(date +%Y%m%d-%H%M%S)"
STATE_FILE="$DATA_HOME/helm-mobile/firefox-preview-state.txt"
RECOVERY="$DATA_HOME/helm-mobile/recovery/firefox-before-helm-mobile-$STAMP"

echo '===== APPLY HELM MOBILE FIREFOX CHROME ====='

for command_name in \
    "$PYTHON_BIN" \
    sha256sum
do
    command -v "$command_name" >/dev/null
done

test -s "$SOURCE"
test -s "$RESOLVER"
test -s "$FIREFOX_ROOT/profiles.ini"

if pgrep -x firefox >/dev/null 2>&1; then
    echo '[STOP] Close every Firefox window before applying the profile.' >&2
    exit 2
fi

PROFILE_DIR="$(
    "$PYTHON_BIN" \
        "$RESOLVER" \
        "$FIREFOX_ROOT"
)"

PROFILE_RESOLUTION="$(
    "$PYTHON_BIN" \
        "$RESOLVER" \
        --method \
        "$FIREFOX_ROOT"
)"

test -d "$PROFILE_DIR"
test -n "$PROFILE_RESOLUTION"

echo "Firefox profile:    $PROFILE_DIR"
echo "Profile resolution: $PROFILE_RESOLUTION"

mkdir -p \
    "$RECOVERY" \
    "$PROFILE_DIR/chrome" \
    "$(dirname "$STATE_FILE")"

had_userchrome=0
had_userjs=0

if [[ -f "$PROFILE_DIR/chrome/userChrome.css" ]]; then
    cp -a \
        "$PROFILE_DIR/chrome/userChrome.css" \
        "$RECOVERY/userChrome.css"

    had_userchrome=1
fi

if [[ -f "$PROFILE_DIR/user.js" ]]; then
    cp -a \
        "$PROFILE_DIR/user.js" \
        "$RECOVERY/user.js"

    had_userjs=1
fi

install \
    -Dm644 \
    "$SOURCE" \
    "$PROFILE_DIR/chrome/userChrome.css"

PROFILE_DIR="$PROFILE_DIR" \
"$PYTHON_BIN" - <<'PY_PREF'
import os
import re
from pathlib import Path

profile = Path(os.environ["PROFILE_DIR"])
path = profile / "user.js"

text = (
    path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    if path.exists()
    else ""
)

pattern = re.compile(
    r'^\s*user_pref\('
    r'"toolkit\.legacyUserProfileCustomizations\.stylesheets"'
    r'.*$',
    re.MULTILINE,
)

text = pattern.sub("", text).rstrip()

managed = (
    'user_pref('
    '"toolkit.legacyUserProfileCustomizations.stylesheets", '
    'true);'
)

new_text = (
    f"{text}\n{managed}\n"
    if text
    else f"{managed}\n"
)

path.write_text(
    new_text,
    encoding="utf-8",
)
PY_PREF

cmp \
    "$SOURCE" \
    "$PROFILE_DIR/chrome/userChrome.css"

USER_JS="$PROFILE_DIR/user.js" \
"$PYTHON_BIN" - <<'PY_VERIFY'
import os
import re
from pathlib import Path

path = Path(os.environ["USER_JS"])

text = path.read_text(
    encoding="utf-8",
    errors="replace",
)

pattern = re.compile(
    r'user_pref\(\s*'
    r'"toolkit\.legacyUserProfileCustomizations\.stylesheets"'
    r'\s*,\s*(true|false)\s*\)\s*;'
)

matches = pattern.findall(text)

if matches != ["true"]:
    raise SystemExit(
        "Firefox stylesheet preference "
        f"is invalid: {matches}"
    )
PY_VERIFY

SOURCE_SHA="$(
    sha256sum "$SOURCE" |
    awk '{print $1}'
)"

STATE_TMP="$STATE_FILE.tmp.$$"

{
    echo 'stage=firefox-preview'
    echo "applied=$(date --iso-8601=seconds)"
    echo "profile=$PROFILE_DIR"
    echo "profile_resolution=$PROFILE_RESOLUTION"
    echo "source_sha256=$SOURCE_SHA"
    echo "recovery=$RECOVERY"
    echo "had_userchrome=$had_userchrome"
    echo "had_userjs=$had_userjs"
} > "$STATE_TMP"

chmod 600 "$STATE_TMP"
mv -f "$STATE_TMP" "$STATE_FILE"

echo "Recovery:        $RECOVERY"
echo "State file:      $STATE_FILE"
echo "Source SHA256:   $SOURCE_SHA"
echo 'HELM Mobile Firefox chrome installed.'
echo 'Start Firefox again to load the chrome.'
