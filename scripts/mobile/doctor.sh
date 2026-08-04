#!/usr/bin/env bash
set -uo pipefail

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
MANIFEST="$REPO/mobile/config/mobile-node.example.json"
PYTHON_BIN="$REPO/venv/bin/python"

OK=0
WARN=0
FAIL=0

green=$'\033[1;32m'
yellow=$'\033[1;33m'
red=$'\033[1;31m'
cyan=$'\033[1;36m'
reset=$'\033[0m'

pass() { printf '%s[OK]%s   %s\n' "$green" "$reset" "$*"; ((OK+=1)); }
warning() { printf '%s[WARN]%s %s\n' "$yellow" "$reset" "$*"; ((WARN+=1)); }
fail() { printf '%s[FAIL]%s %s\n' "$red" "$reset" "$*"; ((FAIL+=1)); }

check_command() {
    local command_name="$1"
    local label="${2:-$1}"

    if command -v "$command_name" >/dev/null 2>&1; then
        pass "$label"
    else
        fail "$label — command unavailable: $command_name"
    fi
}

check_package() {
    local package="$1"
    local label="${2:-$1}"

    if pacman -Q "$package" >/dev/null 2>&1; then
        pass "$label"
    else
        fail "$label — package unavailable: $package"
    fi
}

printf '%s◈ HELM CYBERDECK MOBILE DIAGNOSTIC%s\n\n' "$cyan" "$reset"

[[ -d "$REPO/.git" ]] \
    && pass "Repository" \
    || fail "Repository — missing: $REPO/.git"

[[ -f "$REPO/VERSION" ]] \
    && pass "Version manifest" \
    || fail "Version manifest"

if [[ "$(cat "$REPO/VERSION" 2>/dev/null)" == "1.3.0-dev" ]]; then
    pass "Development version: 1.3.0-dev"
else
    warning "Development version: $(cat "$REPO/VERSION" 2>/dev/null || echo unknown)"
fi

if [[ -x "$PYTHON_BIN" ]] \
    && "$PYTHON_BIN" -c 'import textual, psutil' >/dev/null 2>&1
then
    pass "Python virtual environment"
else
    fail "Python virtual environment or dependencies"
fi

if [[ -f "$MANIFEST" ]] \
    && "$PYTHON_BIN" - "$MANIFEST" >/dev/null 2>&1 <<'PY_JSON'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("node", {}).get("role") != "mobile":
    raise SystemExit("invalid node role")
PY_JSON
then
    pass "Mobile Node manifest"
else
    fail "Mobile Node manifest"
fi

model="$(cat /sys/class/dmi/id/product_version 2>/dev/null || true)"
[[ "$model" == "ThinkPad T14 Gen 2a" ]] \
    && pass "Platform: ThinkPad T14 Gen 2a" \
    || warning "Platform: ${model:-unknown}"

hostname_value="$(hostnamectl --static 2>/dev/null || true)"
[[ "$hostname_value" == "cyberdeck-laptop" ]] \
    && pass "Hostname: cyberdeck-laptop" \
    || warning "Hostname: ${hostname_value:-unknown}"

[[ "${XDG_CURRENT_DESKTOP:-}" == *KDE* ]] \
    && pass "KDE session" \
    || warning "Desktop session: ${XDG_CURRENT_DESKTOP:-unknown}"

[[ "${XDG_SESSION_TYPE:-}" == "wayland" ]] \
    && pass "Wayland session" \
    || warning "Session protocol: ${XDG_SESSION_TYPE:-unknown}"

if command -v kscreen-doctor >/dev/null 2>&1; then
    display_state="$(
        script \
            -qec 'kscreen-doctor -o' \
            /dev/null \
            2>&1 |
        tr -d '\r'
    )"

    if grep -Fq '1920x1080' <<< "$display_state"; then
        pass "Internal display: 1920x1080"
    else
        warning "Internal display resolution differs"
    fi

    scale_value="$(
        DISPLAY_STATE="$display_state" python - <<'PY_SCALE'
import os
import re

text = os.environ.get("DISPLAY_STATE", "")

# Remove ANSI terminal escape sequences and control characters.
text = re.sub(
    r"\x1b\[[0-?]*[ -/]*[@-~]",
    "",
    text,
)
text = "".join(
    character
    for character in text
    if character in "\n\t" or ord(character) >= 32
)

match = re.search(
    r"Scale:\s*([0-9]+(?:\.[0-9]+)?)",
    text,
)

if match:
    print(f"{float(match.group(1)):g}")
PY_SCALE
    )"

    if [[ "$scale_value" == "1" ]]; then
        pass "Display scale: 1"
    else
        warning \
            "Display scale differs from Mobile baseline: ${scale_value:-unknown}"
    fi
else
    warning "KScreen diagnostic unavailable"
fi


if lspci -k 2>/dev/null \
    | grep -A3 -Ei 'VGA|3D|Display' \
    | grep -Fq 'Kernel driver in use: amdgpu'
then
    pass "AMD graphics driver: amdgpu"
else
    fail "AMD graphics driver: amdgpu"
fi

root_fstype="$(findmnt -no FSTYPE / 2>/dev/null || true)"
[[ "$root_fstype" == "btrfs" ]] \
    && pass "Root filesystem: Btrfs" \
    || fail "Root filesystem: ${root_fstype:-unknown}"

root_source="$(findmnt -no SOURCE / 2>/dev/null || true)"
[[ "$root_source" == /dev/mapper/* ]] \
    && pass "Encrypted mapped root" \
    || warning "Root is not exposed through /dev/mapper"

battery="$(find /sys/class/power_supply -maxdepth 1 -type l -name 'BAT*' -print -quit 2>/dev/null || true)"
if [[ -n "$battery" ]]; then
    pass "Battery device"

    capacity="$(cat "$battery/capacity" 2>/dev/null || true)"
    [[ -n "$capacity" ]] \
        && pass "Battery charge: ${capacity}%" \
        || warning "Battery charge unavailable"

    if [[ -r "$battery/energy_full" \
        && -r "$battery/energy_full_design" ]]
    then
        health="$(awk \
            -v full="$(cat "$battery/energy_full")" \
            -v design="$(cat "$battery/energy_full_design")" \
            'BEGIN { printf "%.1f", full / design * 100 }')"

        if awk -v health="$health" 'BEGIN { exit !(health >= 80) }'; then
            pass "Battery health: ${health}%"
        elif awk -v health="$health" 'BEGIN { exit !(health >= 60) }'; then
            warning "Battery health: ${health}%"
        else
            fail "Battery health: ${health}%"
        fi
    else
        warning "Battery health counters unavailable"
    fi
else
    fail "Battery device"
fi

if systemctl is-active --quiet power-profiles-daemon.service; then
    pass "Power Profiles Daemon active"
else
    fail "Power Profiles Daemon active"
fi

if systemctl is-enabled --quiet power-profiles-daemon.service; then
    pass "Power Profiles Daemon enabled"
else
    fail "Power Profiles Daemon enabled"
fi

if command -v powerprofilesctl >/dev/null 2>&1; then
    active_profile="$(powerprofilesctl get 2>/dev/null || true)"
    [[ -n "$active_profile" ]] \
        && pass "Active power profile: $active_profile" \
        || warning "Active power profile unavailable"
else
    fail "Power profile control"
fi

conflicts=()
for package in \
    tlp \
    tlp-pd \
    tuned \
    tuned-ppd \
    auto-cpufreq \
    system76-power
do
    pacman -Q "$package" >/dev/null 2>&1 \
        && conflicts+=("$package")
done

if (( ${#conflicts[@]} == 0 )); then
    pass "No conflicting power manager"
else
    fail "Conflicting power managers: ${conflicts[*]}"
fi

for package in \
    dolphin \
    kate \
    spectacle \
    sddm \
    plymouth \
    kvantum \
    starship \
    power-profiles-daemon \
    upower \
    brightnessctl
do
    check_package "$package" "Package: $package"
done

for command_name in \
    dolphin \
    kate \
    spectacle \
    sddm \
    plymouth-set-default-theme \
    kvantummanager \
    starship \
    brightnessctl \
    smartctl \
    jq \
    rsync \
    ssh
do
    check_command "$command_name" "Command: $command_name"
done

if systemctl is-enabled --quiet sddm.service 2>/dev/null; then
    warning "SDDM is already enabled before Access Gate installation"
else
    pass "SDDM staged but not enabled"
fi

if grep -Rqs 'plymouth' \
    /etc/mkinitcpio.conf \
    /etc/mkinitcpio.conf.d 2>/dev/null
then
    warning "Plymouth is already referenced by initramfs configuration"
else
    pass "Plymouth staged but not activated"
fi

baseline_checksum="$(find "$HOME" -maxdepth 1 \
    -type f -name 'CyberDeck-Mobile-Baseline-*.tar.gz.sha256' \
    -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | awk 'NR == 1 { print $2 }')"

if [[ -n "$baseline_checksum" ]] \
    && sha256sum --check "$baseline_checksum" >/dev/null 2>&1
then
    pass "CyberDeck Mobile baseline archive"
else
    warning "CyberDeck Mobile baseline archive not verified"
fi

snapshot_record="$(find "$HOME" -maxdepth 3 \
    -type f \
    -path '*/CyberDeck-Mobile-Baseline-*/inventory/snapshot-paths.txt' \
    -print -quit 2>/dev/null || true)"

[[ -n "$snapshot_record" ]] \
    && pass "Btrfs snapshot recovery record" \
    || warning "Btrfs snapshot recovery record unavailable"

running_kernel="$(uname -r)"
installed_kernel="$(pacman -Q linux 2>/dev/null | awk '{print $2}' || true)"
installed_kernel="${installed_kernel/.arch/-arch}"

if [[ -n "$installed_kernel" && "$running_kernel" == "$installed_kernel" ]]; then
    pass "Running kernel matches installed package"
elif [[ -n "$installed_kernel" ]]; then
    warning "Kernel reboot pending: running $running_kernel, installed $installed_kernel"
else
    warning "Installed linux package version unavailable"
fi

failed_system_units="$(
    systemctl         --failed         --no-legend         --plain         --no-pager         2>/dev/null |
    awk '
        $2 == "loaded" ||
        $2 == "not-found" {
            print $1
        }
    '
)"

if [[ -n "$failed_system_units" ]]; then
    fail         "Failed system services: $(tr '\n' ' ' <<< "$failed_system_units")"
else
    pass "No failed system services"
fi

failed_user_units="$(
    systemctl         --user         --failed         --no-legend         --plain         --no-pager         2>/dev/null |
    awk '
        $2 == "loaded" ||
        $2 == "not-found" {
            print $1
        }
    '
)"

if [[ -n "$failed_user_units" ]]; then
    warning         "Failed user services: $(tr '\n' ' ' <<< "$failed_user_units")"
else
    pass "No failed user services"
fi


field_shell_manifest="$REPO/mobile/plasma/field-shell.json"
field_shell_wallpaper="$REPO/mobile/assets/wallpapers/helm-mobile-field-node-v2.svg"

if [[ -f "$field_shell_manifest" ]] \
    && "$PYTHON_BIN" - "$field_shell_manifest" >/dev/null 2>&1 <<'PY_FIELD_JSON'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

panel = payload.get("panel", {})

expected = {
    "location": "bottom",
    "height": 40,
    "minimum_length": 1200,
    "maximum_length": 1200,
    "length_mode": "custom",
    "alignment": "center",
    "offset": 0,
    "hiding": "dodgewindows",
    "floating": True,
    "opacity": "translucent",
}

if any(panel.get(key) != value for key, value in expected.items()):
    raise SystemExit("invalid field shell manifest")
PY_FIELD_JSON
then
    pass "Plasma Field Shell manifest"
else
    fail "Plasma Field Shell manifest"
fi

[[ -s "$field_shell_wallpaper" ]] \
    && pass "Field-node wallpaper v2 source" \
    || fail "Field-node wallpaper v2 source"

if systemctl --user is-active --quiet plasma-plasmashell.service \
    && command -v qdbus6 >/dev/null 2>&1
then
    panel_state="$(
        qdbus6 \
            org.kde.plasmashell \
            /PlasmaShell \
            org.kde.PlasmaShell.evaluateScript \
            '
            const ids = panelIds;
            let panel = null;

            for (let i = 0; i < ids.length; ++i) {
                const candidate = panelById(ids[i]);

                if (
                    candidate
                    && candidate.location === "bottom"
                ) {
                    panel = candidate;
                    break;
                }
            }

            if (!panel) {
                throw new Error("Bottom panel not found");
            }

            print(JSON.stringify({
                location: panel.location,
                height: panel.height,
                minimumLength: panel.minimumLength,
                maximumLength: panel.maximumLength,
                lengthMode: panel.lengthMode,
                alignment: panel.alignment,
                offset: panel.offset,
                hiding: panel.hiding,
                floating: panel.floating,
                opacity: panel.opacity
            }));
            '
    )"

    if PANEL_STATE="$panel_state" \
        "$PYTHON_BIN" >/dev/null 2>&1 <<'PY_PANEL_STATE'
import json
import os

panel = json.loads(os.environ["PANEL_STATE"])

expected = {
    "location": "bottom",
    "height": 40,
    "minimumLength": 1200,
    "maximumLength": 1200,
    "lengthMode": "custom",
    "alignment": "center",
    "offset": 0,
    "hiding": "dodgewindows",
    "floating": True,
    "opacity": "translucent",
}

if any(panel.get(key) != value for key, value in expected.items()):
    raise SystemExit("field shell differs")
PY_PANEL_STATE
    then
        pass "Live Plasma Field Shell"
    else
        warning "Live Plasma Field Shell differs from manifest"
    fi
else
    warning "Live Plasma Field Shell unavailable"
fi

printf '\n%sSYSTEM STATE%s: ' "$cyan" "$reset"
if (( FAIL > 0 )); then
    printf '%sDEGRADED%s\n' "$red" "$reset"
elif (( WARN > 0 )); then
    printf '%sFOUNDATION READY WITH WARNINGS%s\n' "$yellow" "$reset"
else
    printf '%sFOUNDATION READY%s\n' "$green" "$reset"
fi

printf 'Checks: %d OK, %d warnings, %d failures\n' "$OK" "$WARN" "$FAIL"
(( FAIL == 0 ))
