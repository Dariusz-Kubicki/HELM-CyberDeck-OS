#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." &&
    pwd
)"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

KONSOLE_DIR="$DATA_HOME/konsole"
HELM_CONFIG_DIR="$CONFIG_HOME/helm-mobile"
LOCAL_BIN="$HOME/.local/bin"
KONSOLE_RC="$CONFIG_HOME/konsolerc"

SOURCE_DIR="$ROOT_DIR/mobile/apps/konsole"
MANIFEST="$SOURCE_DIR/konsole.json"
PROFILE_TEMPLATE="$SOURCE_DIR/HELMMobile.profile.in"
SOURCE_SCHEME="$SOURCE_DIR/HELMMobile.colorscheme"
SOURCE_BASHRC="$SOURCE_DIR/terminal.bashrc"
SOURCE_WRAPPER="$SOURCE_DIR/helm-mobile-shell"

INSTALLED_PROFILE="$KONSOLE_DIR/HELMMobile.profile"
INSTALLED_SCHEME="$KONSOLE_DIR/HELMMobile.colorscheme"
INSTALLED_BASHRC="$HELM_CONFIG_DIR/terminal.bashrc"
INSTALLED_WRAPPER="$LOCAL_BIN/helm-mobile-shell"

STAMP="$(date +%Y%m%d-%H%M%S)"
RECOVERY_DIR="$DATA_HOME/helm-mobile/recovery/stage3a-konsole-$STAMP"
STATE_FILE="$DATA_HOME/helm-mobile/stage3a-konsole-last-apply.json"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

EXPECTED_DEFAULT_PROFILE="HELMMobile.profile"

echo '===== APPLY STAGE 3A KONSOLE ====='

for command_name in \
    python \
    kreadconfig6 \
    kwriteconfig6 \
    konsole \
    fc-match
do
    command -v "$command_name" >/dev/null
done

test -s "$MANIFEST"
test -s "$PROFILE_TEMPLATE"
test -s "$SOURCE_SCHEME"
test -s "$SOURCE_BASHRC"
test -x "$SOURCE_WRAPPER"

echo
echo '===== VALIDATE KONSOLE SOURCES ====='

MANIFEST="$MANIFEST" \
PROFILE_TEMPLATE="$PROFILE_TEMPLATE" \
SOURCE_SCHEME="$SOURCE_SCHEME" \
SOURCE_BASHRC="$SOURCE_BASHRC" \
python - <<'PY_MANIFEST'
import json
import os
from pathlib import Path

manifest = Path(os.environ["MANIFEST"])
profile_template = Path(os.environ["PROFILE_TEMPLATE"])
scheme = Path(os.environ["SOURCE_SCHEME"])
bashrc = Path(os.environ["SOURCE_BASHRC"])

payload = json.loads(
    manifest.read_text(encoding="utf-8")
)

if payload.get("stage") != "3a-konsole":
    raise SystemExit("Invalid Konsole stage identifier.")

profile = payload.get("profile", {})
color_scheme = payload.get("color_scheme", {})
shell = payload.get("shell", {})

expected_profile = {
    "file": "HELMMobile.profile",
    "template": "HELMMobile.profile.in",
    "name": "HELM Mobile Terminal",
    "default": True,
    "color_scheme": "HELMMobile",
    "font_family": "Hack",
    "font_size": 11,
    "terminal_margin": 8,
    "cursor_shape": "block",
    "blinking_cursor": True,
    "scrollbar_position": "hidden",
}

for key, expected_value in expected_profile.items():
    if profile.get(key) != expected_value:
        raise SystemExit(
            f"Invalid profile manifest value: {key}"
        )

if color_scheme.get("file") != "HELMMobile.colorscheme":
    raise SystemExit("Invalid color-scheme filename.")

if color_scheme.get("opacity") != 0.92:
    raise SystemExit("Invalid terminal opacity.")

if color_scheme.get("blur") is not False:
    raise SystemExit("Terminal blur must remain disabled.")

if shell.get("command") != "helm-mobile-shell":
    raise SystemExit("Invalid shell command.")

if shell.get("bashrc") != "terminal.bashrc":
    raise SystemExit("Invalid shell bashrc.")

if shell.get("prompt_label") != "HELM MOBILE":
    raise SystemExit("Invalid prompt label.")

profile_text = profile_template.read_text(
    encoding="utf-8"
)

required_profile_lines = {
    "Command=@HELM_MOBILE_SHELL@",
    "Name=HELM Mobile Terminal",
    "ColorScheme=HELMMobile",
    "Font=Hack,11,-1,5,50,0,0,0,0,0",
    "TerminalMargin=8",
    "CursorShape=1",
    "BlinkingCursorEnabled=true",
    "ScrollBarPosition=2",
}

actual_profile_lines = set(profile_text.splitlines())

missing = required_profile_lines - actual_profile_lines

if missing:
    raise SystemExit(
        f"Missing profile lines: {sorted(missing)}"
    )

if "/home/" in profile_text:
    raise SystemExit(
        "Absolute home path found in profile template."
    )

scheme_text = scheme.read_text(encoding="utf-8")

if "Description=HELM Mobile" not in scheme_text:
    raise SystemExit("Invalid color-scheme description.")

if "Opacity=0.92" not in scheme_text:
    raise SystemExit("Invalid color-scheme opacity.")

if "Blur=false" not in scheme_text:
    raise SystemExit("Color-scheme blur must be disabled.")

if "HELM MOBILE" not in bashrc.read_text(
    encoding="utf-8"
):
    raise SystemExit("HELM prompt label missing.")
PY_MANIFEST

bash -n \
    "$SOURCE_BASHRC" \
    "$SOURCE_WRAPPER"

echo '[PASS] Konsole sources are valid.'

echo
echo '===== CAPTURE CURRENT KONSOLE STATE ====='

DEFAULT_BEFORE="$(
    kreadconfig6 \
        --file konsolerc \
        --group 'Desktop Entry' \
        --key DefaultProfile \
        2>/dev/null \
        || true
)"

echo "Default profile before apply: ${DEFAULT_BEFORE:-not configured}"

mkdir -p \
    "$KONSOLE_DIR" \
    "$HELM_CONFIG_DIR" \
    "$LOCAL_BIN" \
    "$RECOVERY_DIR/files" \
    "$(dirname "$STATE_FILE")"

printf '%s\n' "$DEFAULT_BEFORE" \
    > "$RECOVERY_DIR/default-profile-before.txt"

TARGETS=(
    "$KONSOLE_RC"
    "$INSTALLED_PROFILE"
    "$INSTALLED_SCHEME"
    "$INSTALLED_BASHRC"
    "$INSTALLED_WRAPPER"
)

: > "$RECOVERY_DIR/existing-files.txt"

echo
echo '===== BACK UP LOCAL FILES ====='

for target in "${TARGETS[@]}"; do
    if [[ -e "$target" || -L "$target" ]]; then
        relative="${target#/}"
        backup="$RECOVERY_DIR/files/$relative"

        mkdir -p "$(dirname "$backup")"

        cp -a \
            "$target" \
            "$backup"

        printf '%s\n' "$target" \
            >> "$RECOVERY_DIR/existing-files.txt"

        echo "[BACKUP] $target"
    else
        echo "[NEW]    $target"
    fi
done

echo
echo '===== INSTALL HELM MOBILE TERMINAL ASSETS ====='

install \
    -Dm644 \
    "$SOURCE_SCHEME" \
    "$INSTALLED_SCHEME"

install \
    -Dm644 \
    "$SOURCE_BASHRC" \
    "$INSTALLED_BASHRC"

install \
    -Dm755 \
    "$SOURCE_WRAPPER" \
    "$INSTALLED_WRAPPER"

echo '[PASS] Color scheme and shell assets installed.'

echo
echo '===== RENDER KONSOLE PROFILE ====='

PROFILE_TEMPLATE="$PROFILE_TEMPLATE" \
OUTPUT="$INSTALLED_PROFILE" \
SHELL_COMMAND="$INSTALLED_WRAPPER" \
python - <<'PY_RENDER'
import os
from pathlib import Path

template = Path(os.environ["PROFILE_TEMPLATE"])
output = Path(os.environ["OUTPUT"])
shell_command = os.environ["SHELL_COMMAND"]

text = template.read_text(encoding="utf-8")

text = text.replace(
    "@HELM_MOBILE_SHELL@",
    shell_command,
)

if "@HELM_" in text:
    raise SystemExit(
        "Unresolved HELM profile placeholder."
    )

output.write_text(
    text.rstrip("\n") + "\n",
    encoding="utf-8",
)
PY_RENDER

chmod 644 "$INSTALLED_PROFILE"

echo '[PASS] HELM Mobile profile rendered.'

echo
echo '===== SET DEFAULT KONSOLE PROFILE ====='

kwriteconfig6 \
    --file konsolerc \
    --group 'Desktop Entry' \
    --key DefaultProfile \
    "$EXPECTED_DEFAULT_PROFILE"

DEFAULT_AFTER="$(
    kreadconfig6 \
        --file konsolerc \
        --group 'Desktop Entry' \
        --key DefaultProfile
)"

echo "Default profile after apply: $DEFAULT_AFTER"

test "$DEFAULT_AFTER" = "$EXPECTED_DEFAULT_PROFILE"

echo '[PASS] HELM Mobile is the default Konsole profile.'

echo
echo '===== VERIFY INSTALLED STATE ====='

EXPECTED_PROFILE="$TMP_DIR/HELMMobile.profile"

PROFILE_TEMPLATE="$PROFILE_TEMPLATE" \
OUTPUT="$EXPECTED_PROFILE" \
SHELL_COMMAND="$INSTALLED_WRAPPER" \
python - <<'PY_EXPECTED'
import os
from pathlib import Path

template = Path(os.environ["PROFILE_TEMPLATE"])
output = Path(os.environ["OUTPUT"])

text = template.read_text(encoding="utf-8").replace(
    "@HELM_MOBILE_SHELL@",
    os.environ["SHELL_COMMAND"],
)

if "@HELM_" in text:
    raise SystemExit(
        "Unresolved HELM profile placeholder."
    )

output.write_text(
    text.rstrip("\n") + "\n",
    encoding="utf-8",
)
PY_EXPECTED

cmp \
    "$EXPECTED_PROFILE" \
    "$INSTALLED_PROFILE"

cmp \
    "$SOURCE_SCHEME" \
    "$INSTALLED_SCHEME"

cmp \
    "$SOURCE_BASHRC" \
    "$INSTALLED_BASHRC"

cmp \
    "$SOURCE_WRAPPER" \
    "$INSTALLED_WRAPPER"

test -x "$INSTALLED_WRAPPER"

grep -Fqx \
    "Command=$INSTALLED_WRAPPER" \
    "$INSTALLED_PROFILE"

grep -Fqx \
    'Name=HELM Mobile Terminal' \
    "$INSTALLED_PROFILE"

grep -Fqx \
    'ColorScheme=HELMMobile' \
    "$INSTALLED_PROFILE"

grep -Fqx \
    'Font=Hack,11,-1,5,50,0,0,0,0,0' \
    "$INSTALLED_PROFILE"

grep -Fqx \
    'TerminalMargin=8' \
    "$INSTALLED_PROFILE"

grep -Fqx \
    'Opacity=0.92' \
    "$INSTALLED_SCHEME"

grep -Fq \
    'HELM MOBILE' \
    "$INSTALLED_BASHRC"

bash -n \
    "$INSTALLED_BASHRC" \
    "$INSTALLED_WRAPPER"

echo '[PASS] Installed Konsole state matches repository sources.'

STATE_FILE="$STATE_FILE" \
RECOVERY_DIR="$RECOVERY_DIR" \
DEFAULT_BEFORE="$DEFAULT_BEFORE" \
DEFAULT_AFTER="$DEFAULT_AFTER" \
python - <<'PY_STATE'
import json
import os
from datetime import datetime
from pathlib import Path

payload = {
    "stage": "3a-konsole",
    "applied": datetime.now()
        .astimezone()
        .isoformat(),
    "recovery": os.environ["RECOVERY_DIR"],
    "default_profile_before": (
        os.environ["DEFAULT_BEFORE"]
    ),
    "default_profile_after": (
        os.environ["DEFAULT_AFTER"]
    ),
}

Path(os.environ["STATE_FILE"]).write_text(
    json.dumps(payload, indent=2) + "\n",
    encoding="utf-8",
)
PY_STATE

echo
echo 'STAGE 3A KONSOLE: APPLIED'
echo "Recovery: $RECOVERY_DIR"
echo "State:    $STATE_FILE"
echo 'Already open Konsole windows were not changed.'
