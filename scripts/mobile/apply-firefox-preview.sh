#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
FIREFOX_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox"
STAMP="$(date +%Y%m%d-%H%M%S)"
STATE_FILE="$DATA_HOME/helm-mobile/firefox-preview-state.txt"

if pgrep -x firefox >/dev/null 2>&1; then
    echo '[STOP] Firefox nadal działa. Zamknij wszystkie jego okna.' >&2
    exit 2
fi

PROFILE_DIR="$(
    FIREFOX_ROOT="$FIREFOX_ROOT" python - <<'PY_PROFILE'
import configparser
import os
from pathlib import Path

root = Path(os.environ["FIREFOX_ROOT"])
profiles_ini = root / "profiles.ini"

if not profiles_ini.is_file():
    raise SystemExit("profiles.ini not found")

config = configparser.RawConfigParser()
config.read(profiles_ini, encoding="utf-8")

candidates = []
for section in config.sections():
    if not section.startswith("Profile"):
        continue

    path_value = config.get(section, "Path", fallback="")
    if not path_value:
        continue

    is_relative = config.getboolean(section, "IsRelative", fallback=True)
    profile = root / path_value if is_relative else Path(path_value)

    score = 0
    if config.getboolean(section, "Default", fallback=False):
        score += 10
    if profile.name.endswith(".default-release"):
        score += 5
    if (profile / "prefs.js").is_file():
        score += 2

    candidates.append((score, profile))

if not candidates:
    raise SystemExit("No Firefox profile found")

profile = max(candidates, key=lambda item: item[0])[1]
if not profile.is_dir():
    raise SystemExit(f"Profile directory missing: {profile}")

print(profile)
PY_PROFILE
)"

SOURCE="$REPO/mobile/apps/firefox/userChrome.css"
RECOVERY="$DATA_HOME/helm-mobile/recovery/firefox-before-helm-mobile-$STAMP"

test -f "$SOURCE"
test -d "$PROFILE_DIR"

mkdir -p \
    "$RECOVERY" \
    "$PROFILE_DIR/chrome" \
    "$(dirname "$STATE_FILE")"

had_userchrome=0
had_userjs=0

if [[ -f "$PROFILE_DIR/chrome/userChrome.css" ]]; then
    cp -a "$PROFILE_DIR/chrome/userChrome.css" "$RECOVERY/userChrome.css"
    had_userchrome=1
fi

if [[ -f "$PROFILE_DIR/user.js" ]]; then
    cp -a "$PROFILE_DIR/user.js" "$RECOVERY/user.js"
    had_userjs=1
fi

cp -f "$SOURCE" "$PROFILE_DIR/chrome/userChrome.css"

PROFILE_DIR="$PROFILE_DIR" python - <<'PY_PREF'
import os
import re
from pathlib import Path

profile = Path(os.environ["PROFILE_DIR"])
path = profile / "user.js"
text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

pattern = re.compile(
    r'^\s*user_pref\('
    r'"toolkit\.legacyUserProfileCustomizations\.stylesheets"'
    r'.*$',
    re.MULTILINE,
)

text = pattern.sub("", text).rstrip()
managed = 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
new_text = f"{text}\n{managed}\n" if text else f"{managed}\n"
path.write_text(new_text, encoding="utf-8")
PY_PREF

{
    echo 'stage=firefox-preview'
    echo "applied=$(date --iso-8601=seconds)"
    echo "profile=$PROFILE_DIR"
    echo "recovery=$RECOVERY"
    echo "had_userchrome=$had_userchrome"
    echo "had_userjs=$had_userjs"
} > "$STATE_FILE"

test -s "$PROFILE_DIR/chrome/userChrome.css"
grep -Fq 'toolkit.legacyUserProfileCustomizations.stylesheets' "$PROFILE_DIR/user.js"

echo "Firefox profile: $PROFILE_DIR"
echo "Recovery:        $RECOVERY"
echo "State file:      $STATE_FILE"
echo 'HELM Mobile Firefox preview installed.'
echo 'Uruchom teraz Firefoksa ponownie.'
