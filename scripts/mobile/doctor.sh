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

access_gate_manifest="$REPO/mobile/sddm/access-gate.json"
access_gate_source="$REPO/mobile/sddm/helm-mobile"
access_gate_system="/usr/share/sddm/themes/helm-mobile"
access_gate_config="/etc/sddm.conf.d/90-helm-mobile.conf"
access_gate_state="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile/stage4c-sddm-candidate-last-apply.json"

if [[ -s "$access_gate_manifest" ]] \
    && [[ -s "$access_gate_source/Main.qml" ]] \
    && [[ -s "$access_gate_source/metadata.desktop" ]] \
    && [[ -s "$access_gate_source/theme.conf" ]] \
    && [[ -s "$access_gate_source/wallpaper.svg" ]]
then
    pass "HELM Mobile Access Gate source assets"
else
    fail "HELM Mobile Access Gate source assets"
fi

display_manager_target="$(readlink -f /etc/systemd/system/display-manager.service 2>/dev/null || true)"

if [[ "$display_manager_target" == "/usr/lib/systemd/system/sddm.service" ]] \
    && systemctl is-active --quiet sddm.service \
    && systemctl is-enabled --quiet sddm.service
then
    pass "HELM Mobile Access Gate runtime"

    access_gate_matches=1

    for access_gate_asset in Main.qml metadata.desktop theme.conf wallpaper.svg; do
        if ! cmp -s \
            "$access_gate_source/$access_gate_asset" \
            "$access_gate_system/$access_gate_asset"
        then
            access_gate_matches=0
        fi
    done

    if (( access_gate_matches == 1 )) \
        && grep -Fqx 'Current=helm-mobile' "$access_gate_config" 2>/dev/null \
        && grep -Fqx 'QtVersion=6' "$access_gate_system/metadata.desktop" 2>/dev/null
    then
        pass "Installed Access Gate matches source"
    else
        fail "Installed Access Gate differs from source"
    fi

    if [[ -s "$access_gate_state" ]] \
        && [[ "$(jq -r '.real_login_verified // false' "$access_gate_state" 2>/dev/null)" == "true" ]]
    then
        pass "Access Gate real login verified"
    else
        warning "Access Gate real login not yet verified"
    fi
else
    warning "HELM Mobile Access Gate is staged but inactive"
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


launcher_manifest="$REPO/mobile/apps/launchers/launchers.json"
launcher_source_icons="$REPO/mobile/icons/launchers"
launcher_data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
launcher_apps="$launcher_data_home/applications"
launcher_installed_icons="$launcher_data_home/helm-mobile/icons"
launcher_expected_order="applications:helm-mobile.desktop,applications:org.kde.konsole.desktop,applications:org.kde.dolphin.desktop,applications:firefox.desktop"

if [[ -f "$launcher_manifest" ]] \
    && "$PYTHON_BIN" - "$launcher_manifest" >/dev/null 2>&1 <<'PY_LAUNCHER_MANIFEST'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

expected_order = (
    "applications:helm-mobile.desktop,"
    "applications:org.kde.konsole.desktop,"
    "applications:org.kde.dolphin.desktop,"
    "applications:firefox.desktop"
)

expected_launchers = [
    (
        "helm-mobile.desktop",
        "helm-mobile-core.svg",
        "dedicated",
    ),
    (
        "org.kde.konsole.desktop",
        "helm-mobile-terminal.svg",
        "same-id-override",
    ),
    (
        "org.kde.dolphin.desktop",
        "helm-mobile-files.svg",
        "same-id-override",
    ),
    (
        "firefox.desktop",
        "helm-mobile-browser.svg",
        "same-id-override",
    ),
]

if payload.get("stage") != "2c-panel-launchers":
    raise SystemExit("invalid launcher stage")

if payload.get("global_icon_theme") != "breeze":
    raise SystemExit("global icon theme is not Breeze")

if payload.get("panel_launchers") != expected_order:
    raise SystemExit("invalid launcher order")

actual_launchers = [
    (
        item.get("desktop_id"),
        item.get("icon"),
        item.get("strategy"),
    )
    for item in payload.get("launchers", [])
]

if actual_launchers != expected_launchers:
    raise SystemExit("invalid launcher manifest entries")
PY_LAUNCHER_MANIFEST
then
    pass "Panel launcher manifest"
else
    fail "Panel launcher manifest"
fi

launcher_sources_ok=1

for icon in \
    helm-mobile-core.svg \
    helm-mobile-terminal.svg \
    helm-mobile-files.svg \
    helm-mobile-browser.svg
do
    if [[ ! -s "$launcher_source_icons/$icon" ]]; then
        launcher_sources_ok=0
    fi
done

if (( launcher_sources_ok == 1 )); then
    pass "Panel launcher icon sources"
else
    fail "Panel launcher icon sources"
fi

if [[ -x "$HOME/.local/bin/helm-start" ]]; then
    pass "HELM Mobile launcher command"
else
    fail "HELM Mobile launcher command"
fi

launcher_desktop_entries_ok=1

for desktop_id in \
    helm-mobile.desktop \
    org.kde.konsole.desktop \
    org.kde.dolphin.desktop \
    firefox.desktop
do
    if [[ ! -s "$launcher_apps/$desktop_id" ]]; then
        launcher_desktop_entries_ok=0
    fi
done

if (( launcher_desktop_entries_ok == 1 )); then
    pass "Panel launcher desktop entries"
else
    fail "Panel launcher desktop entries"
fi

launcher_icon_overrides_ok=1

grep -Fqx \
    "Icon=$launcher_installed_icons/helm-mobile-core.svg" \
    "$launcher_apps/helm-mobile.desktop" \
    2>/dev/null \
    || launcher_icon_overrides_ok=0

grep -Fqx \
    "Icon=$launcher_installed_icons/helm-mobile-terminal.svg" \
    "$launcher_apps/org.kde.konsole.desktop" \
    2>/dev/null \
    || launcher_icon_overrides_ok=0

grep -Fqx \
    "Icon=$launcher_installed_icons/helm-mobile-files.svg" \
    "$launcher_apps/org.kde.dolphin.desktop" \
    2>/dev/null \
    || launcher_icon_overrides_ok=0

grep -Fqx \
    "Icon=$launcher_installed_icons/helm-mobile-browser.svg" \
    "$launcher_apps/firefox.desktop" \
    2>/dev/null \
    || launcher_icon_overrides_ok=0

if (( launcher_icon_overrides_ok == 1 )); then
    pass "Panel launcher icon overrides"
else
    fail "Panel launcher icon overrides"
fi

launcher_icons_match=1

for icon in \
    helm-mobile-core.svg \
    helm-mobile-terminal.svg \
    helm-mobile-files.svg \
    helm-mobile-browser.svg
do
    if ! cmp -s \
        "$launcher_source_icons/$icon" \
        "$launcher_installed_icons/$icon"
    then
        launcher_icons_match=0
    fi
done

if (( launcher_icons_match == 1 )); then
    pass "Installed launcher icons match sources"
else
    fail "Installed launcher icons differ from sources"
fi

if command -v kreadconfig6 >/dev/null 2>&1; then
    launcher_global_theme="$(
        kreadconfig6 \
            --file kdeglobals \
            --group Icons \
            --key Theme \
            2>/dev/null \
            || true
    )"

    if [[ "$launcher_global_theme" == "breeze" ]]; then
        pass "Global icon theme remains Breeze"
    else
        fail \
            "Global icon theme differs: ${launcher_global_theme:-unknown}"
    fi
else
    fail "Global icon theme diagnostic unavailable"
fi

if systemctl --user is-active --quiet \
    plasma-plasmashell.service \
    && command -v qdbus6 >/dev/null 2>&1
then
    launcher_live_order="$(
        qdbus6 \
            org.kde.plasmashell \
            /PlasmaShell \
            org.kde.PlasmaShell.evaluateScript \
            '
            const ids = panelIds;
            let panel = null;
            let tasks = null;

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

            for (
                let i = 0;
                i < panel.widgetIds.length;
                ++i
            ) {
                const widget = panel.widgetById(
                    panel.widgetIds[i]
                );

                if (
                    widget
                    && widget.type
                        === "org.kde.plasma.icontasks"
                ) {
                    tasks = widget;
                    break;
                }
            }

            if (!tasks) {
                throw new Error(
                    "Icon Tasks widget not found"
                );
            }

            tasks.currentConfigGroup = ["General"];

            print(String(
                tasks.readConfig("launchers", "")
            ));
            ' \
            2>/dev/null \
            || true
    )"

    if [[ "$launcher_live_order" == "$launcher_expected_order" ]]; then
        pass "Live panel launcher order"
    else
        warning "Live panel launcher order differs"
    fi
else
    warning "Live panel launcher diagnostic unavailable"
fi


konsole_source_dir="$REPO/mobile/apps/konsole"
konsole_manifest="$konsole_source_dir/konsole.json"
konsole_profile_template="$konsole_source_dir/HELMMobile.profile.in"
konsole_source_scheme="$konsole_source_dir/HELMMobile.colorscheme"
konsole_source_bashrc="$konsole_source_dir/terminal.bashrc"
konsole_source_wrapper="$konsole_source_dir/helm-mobile-shell"

konsole_data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
konsole_config_home="${XDG_CONFIG_HOME:-$HOME/.config}"

konsole_installed_profile="$konsole_data_home/konsole/HELMMobile.profile"
konsole_installed_scheme="$konsole_data_home/konsole/HELMMobile.colorscheme"
konsole_installed_bashrc="$konsole_config_home/helm-mobile/terminal.bashrc"
konsole_installed_wrapper="$HOME/.local/bin/helm-mobile-shell"

if [[ -f "$konsole_manifest" ]] \
    && "$PYTHON_BIN" \
        - "$konsole_manifest" \
        >/dev/null 2>&1 \
        <<'PY_KONSOLE_MANIFEST'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

if payload.get("stage") != "3a-konsole":
    raise SystemExit("invalid Konsole stage")

profile = payload.get("profile", {})
scheme = payload.get("color_scheme", {})
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
            f"invalid Konsole profile value: {key}"
        )

if scheme.get("file") != "HELMMobile.colorscheme":
    raise SystemExit("invalid Konsole color scheme")

if scheme.get("description") != "HELM Mobile":
    raise SystemExit("invalid Konsole scheme description")

if scheme.get("opacity") != 0.92:
    raise SystemExit("invalid Konsole opacity")

if scheme.get("blur") is not False:
    raise SystemExit("Konsole blur must remain disabled")

if shell.get("command") != "helm-mobile-shell":
    raise SystemExit("invalid Konsole shell command")

if shell.get("bashrc") != "terminal.bashrc":
    raise SystemExit("invalid Konsole shell configuration")

if shell.get("prompt_label") != "HELM MOBILE":
    raise SystemExit("invalid Konsole prompt label")
PY_KONSOLE_MANIFEST
then
    pass "HELM Mobile Konsole manifest"
else
    fail "HELM Mobile Konsole manifest"
fi

konsole_sources_ok=1

for source in \
    "$konsole_profile_template" \
    "$konsole_source_scheme" \
    "$konsole_source_bashrc" \
    "$konsole_source_wrapper"
do
    if [[ ! -s "$source" ]]; then
        konsole_sources_ok=0
    fi
done

if [[ ! -x "$konsole_source_wrapper" ]]; then
    konsole_sources_ok=0
fi

if (( konsole_sources_ok == 1 )); then
    pass "HELM Mobile Konsole source assets"
else
    fail "HELM Mobile Konsole source assets"
fi

if "$PYTHON_BIN" \
    - "$konsole_profile_template" \
      "$konsole_installed_profile" \
      "$konsole_source_scheme" \
      "$konsole_installed_scheme" \
      "$konsole_source_bashrc" \
      "$konsole_installed_bashrc" \
      "$konsole_source_wrapper" \
      "$konsole_installed_wrapper" \
    >/dev/null 2>&1 \
    <<'PY_KONSOLE_INSTALLED'
import sys
from pathlib import Path

(
    profile_template,
    installed_profile,
    source_scheme,
    installed_scheme,
    source_bashrc,
    installed_bashrc,
    source_wrapper,
    installed_wrapper,
) = map(Path, sys.argv[1:])

for path in (
    profile_template,
    installed_profile,
    source_scheme,
    installed_scheme,
    source_bashrc,
    installed_bashrc,
    source_wrapper,
    installed_wrapper,
):
    if not path.is_file():
        raise SystemExit(f"missing file: {path}")

expected_profile = profile_template.read_text(
    encoding="utf-8"
).replace(
    "@HELM_MOBILE_SHELL@",
    str(installed_wrapper),
)

if "@HELM_" in expected_profile:
    raise SystemExit(
        "unresolved Konsole profile placeholder"
    )

actual_profile = installed_profile.read_text(
    encoding="utf-8"
)

if actual_profile != expected_profile:
    raise SystemExit(
        "installed Konsole profile differs"
    )

comparisons = (
    (source_scheme, installed_scheme),
    (source_bashrc, installed_bashrc),
    (source_wrapper, installed_wrapper),
)

for source, installed in comparisons:
    if source.read_bytes() != installed.read_bytes():
        raise SystemExit(
            f"installed asset differs: {installed}"
        )
PY_KONSOLE_INSTALLED
then
    pass "Installed Konsole assets match sources"
else
    fail "Installed Konsole assets differ from sources"
fi

konsole_profile_settings_ok=1

grep -Fqx \
    'Name=HELM Mobile Terminal' \
    "$konsole_installed_profile" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

grep -Fqx \
    'ColorScheme=HELMMobile' \
    "$konsole_installed_profile" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

grep -Fqx \
    'Font=Hack,11,-1,5,50,0,0,0,0,0' \
    "$konsole_installed_profile" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

grep -Fqx \
    'TerminalMargin=8' \
    "$konsole_installed_profile" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

grep -Fqx \
    'CursorShape=1' \
    "$konsole_installed_profile" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

grep -Fqx \
    'BlinkingCursorEnabled=true' \
    "$konsole_installed_profile" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

grep -Fqx \
    'ScrollBarPosition=2' \
    "$konsole_installed_profile" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

grep -Fqx \
    'Opacity=0.92' \
    "$konsole_installed_scheme" \
    2>/dev/null \
    || konsole_profile_settings_ok=0

if (( konsole_profile_settings_ok == 1 )); then
    pass "HELM Mobile Konsole profile settings"
else
    fail "HELM Mobile Konsole profile settings"
fi

if command -v kreadconfig6 >/dev/null 2>&1; then
    konsole_default_profile="$(
        kreadconfig6 \
            --file konsolerc \
            --group 'Desktop Entry' \
            --key DefaultProfile \
            2>/dev/null \
            || true
    )"

    if [[ "$konsole_default_profile" == "HELMMobile.profile" ]]; then
        pass "HELM Mobile default Konsole profile"
    else
        fail \
            "Default Konsole profile differs: ${konsole_default_profile:-not configured}"
    fi
else
    fail "Default Konsole profile diagnostic unavailable"
fi

if [[ -x "$konsole_installed_wrapper" ]] \
    && bash -n \
        "$konsole_installed_wrapper" \
        "$konsole_installed_bashrc" \
        >/dev/null 2>&1
then
    pass "HELM Mobile terminal shell"
else
    fail "HELM Mobile terminal shell"
fi

if grep -Fq \
    'HELM MOBILE' \
    "$konsole_installed_bashrc" \
    2>/dev/null
then
    pass "HELM Mobile terminal prompt"
else
    fail "HELM Mobile terminal prompt"
fi



firefox_root="${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox"
firefox_source="$REPO/mobile/apps/firefox/userChrome.css"
firefox_resolver="$REPO/scripts/mobile/resolve-firefox-profile.py"
firefox_apply="$REPO/scripts/mobile/apply-firefox-preview.sh"
firefox_restore="$REPO/scripts/mobile/restore-firefox-preview.sh"
firefox_state="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile/firefox-preview-state.txt"

firefox_profile=""
firefox_resolution=""

if [[ -s "$firefox_source" ]] \
    && [[ -x "$firefox_resolver" ]] \
    && [[ -x "$firefox_apply" ]] \
    && [[ -x "$firefox_restore" ]]
then
    pass "HELM Mobile Firefox source assets"
else
    fail "HELM Mobile Firefox source assets"
fi

if [[ -s "$firefox_root/profiles.ini" ]] \
    && [[ -x "$firefox_resolver" ]]
then
    firefox_profile="$(
        "$PYTHON_BIN" \
            "$firefox_resolver" \
            "$firefox_root" \
            2>/dev/null \
            || true
    )"

    firefox_resolution="$(
        "$PYTHON_BIN" \
            "$firefox_resolver" \
            --method \
            "$firefox_root" \
            2>/dev/null \
            || true
    )"
fi

if [[ -n "$firefox_profile" ]] \
    && [[ -d "$firefox_profile" ]] \
    && [[ -n "$firefox_resolution" ]]
then
    pass \
        "Firefox installation profile: $firefox_resolution"
else
    fail "Firefox installation-aware profile resolution"
fi

if [[ -n "$firefox_profile" ]] \
    && [[ -s "$firefox_profile/chrome/userChrome.css" ]] \
    && cmp -s \
        "$firefox_source" \
        "$firefox_profile/chrome/userChrome.css"
then
    pass "Installed Firefox chrome matches source"
else
    fail "Installed Firefox chrome differs from source"
fi

if [[ -n "$firefox_profile" ]] \
    && [[ -s "$firefox_state" ]] \
    && STATE_FILE="$firefox_state" \
       EXPECTED_PROFILE="$firefox_profile" \
       "$PYTHON_BIN" - >/dev/null 2>&1 <<'PY_FIREFOX_STATE_PROFILE'
import os
from pathlib import Path

values = {}

for line in Path(
    os.environ["STATE_FILE"]
).read_text(
    encoding="utf-8"
).splitlines():
    if "=" not in line:
        continue

    key, value = line.split("=", 1)
    values[key] = value

if (
    values.get("profile")
    != os.environ["EXPECTED_PROFILE"]
):
    raise SystemExit(1)

if not values.get("profile_resolution"):
    raise SystemExit(1)
PY_FIREFOX_STATE_PROFILE
then
    pass "Firefox state identifies installation profile"
else
    fail "Firefox state profile differs from resolver"
fi

firefox_source_sha="$(
    sha256sum "$firefox_source" \
        2>/dev/null \
        | awk '{print $1}'
)"

firefox_state_sha="$(
    awk -F= \
        '$1 == "source_sha256" {print $2; exit}' \
        "$firefox_state" \
        2>/dev/null \
        || true
)"

if [[ -n "$firefox_source_sha" ]] \
    && [[ "$firefox_state_sha" == "$firefox_source_sha" ]]
then
    pass "Firefox state source checksum"
else
    fail "Firefox state source checksum"
fi

if [[ -n "$firefox_profile" ]] \
    && [[ -s "$firefox_profile/user.js" ]] \
    && USER_JS="$firefox_profile/user.js" \
       "$PYTHON_BIN" - >/dev/null 2>&1 <<'PY_FIREFOX_PREF'
import os
import re
from pathlib import Path

text = Path(os.environ["USER_JS"]).read_text(
    encoding="utf-8",
    errors="replace",
)

pattern = re.compile(
    r'user_pref\(\s*'
    r'"toolkit\.legacyUserProfileCustomizations\.stylesheets"'
    r'\s*,\s*(true|false)\s*\)\s*;'
)

if pattern.findall(text) != ["true"]:
    raise SystemExit(1)
PY_FIREFOX_PREF
then
    pass "Firefox profile stylesheet support"
else
    fail "Firefox profile stylesheet support"
fi

dolphin_source_dir="$REPO/mobile/apps/dolphin"
dolphin_manifest="$dolphin_source_dir/dolphin.json"
dolphin_source_rc="$dolphin_source_dir/dolphinrc.template"

dolphin_data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
dolphin_config_home="${XDG_CONFIG_HOME:-$HOME/.config}"

dolphin_installed_rc="$dolphin_config_home/dolphinrc"
dolphin_data_ui="$dolphin_data_home/kxmlgui5/dolphin/dolphinui.rc"
dolphin_config_ui="$dolphin_config_home/kxmlgui5/dolphin/dolphinui.rc"

if [[ -f "$dolphin_manifest" ]] \
    && "$PYTHON_BIN" \
        - "$dolphin_manifest" \
        >/dev/null 2>&1 \
        <<'PY_DOLPHIN_MANIFEST'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

if payload.get("stage") != "3b-dolphin":
    raise SystemExit("invalid Dolphin stage")

if payload.get("role") != "HELM Data Vault":
    raise SystemExit("invalid Dolphin role")

configuration = payload.get("configuration", {})
toolbar = payload.get("toolbar", {})
appearance = payload.get("appearance", {})
integration = payload.get("integration", {})

expected_configuration = {
    "file": "dolphinrc.template",
    "editable_location": True,
    "show_full_path": True,
    "show_full_path_in_titlebar": True,
    "open_external_folders_in_new_tab": True,
    "menu_bar": False,
    "places_icon_size": 22,
    "places_auto_resize": False,
}

for key, expected_value in expected_configuration.items():
    if configuration.get(key) != expected_value:
        raise SystemExit(
            f"invalid Dolphin setting: {key}"
        )

if toolbar.get("strategy") != "native":
    raise SystemExit(
        "Dolphin toolbar strategy is not native"
    )

if toolbar.get("local_kxmlgui_override") is not False:
    raise SystemExit(
        "local Dolphin KXMLGUI override enabled"
    )

if appearance.get("global_color_scheme") != "BreezeDark":
    raise SystemExit(
        "invalid Dolphin color scheme"
    )

if appearance.get("global_icon_theme") != "breeze":
    raise SystemExit(
        "invalid Dolphin icon theme"
    )

if integration.get("terminal_profile") != "HELMMobile.profile":
    raise SystemExit(
        "invalid Dolphin terminal integration"
    )

if integration.get("panel_desktop_id") != "org.kde.dolphin.desktop":
    raise SystemExit(
        "invalid Dolphin desktop identifier"
    )
PY_DOLPHIN_MANIFEST
then
    pass "HELM Data Vault manifest"
else
    fail "HELM Data Vault manifest"
fi

if [[ -s "$dolphin_source_rc" ]]; then
    pass "HELM Data Vault source configuration"
else
    fail "HELM Data Vault source configuration"
fi

if [[ -s "$dolphin_installed_rc" ]] \
    && cmp -s \
        "$dolphin_source_rc" \
        "$dolphin_installed_rc"
then
    pass "Installed Dolphin configuration matches source"
else
    fail "Installed Dolphin configuration differs from source"
fi

dolphin_settings_ok=1

grep -Fqx \
    'EditableUrl=true' \
    "$dolphin_installed_rc" \
    2>/dev/null \
    || dolphin_settings_ok=0

grep -Fqx \
    'OpenExternallyCalledFolderInNewTab=true' \
    "$dolphin_installed_rc" \
    2>/dev/null \
    || dolphin_settings_ok=0

grep -Fqx \
    'ShowFullPath=true' \
    "$dolphin_installed_rc" \
    2>/dev/null \
    || dolphin_settings_ok=0

grep -Fqx \
    'ShowFullPathInTitlebar=true' \
    "$dolphin_installed_rc" \
    2>/dev/null \
    || dolphin_settings_ok=0

grep -Fqx \
    'Places Icons Auto-resize=false' \
    "$dolphin_installed_rc" \
    2>/dev/null \
    || dolphin_settings_ok=0

grep -Fqx \
    'Places Icons Static Size=22' \
    "$dolphin_installed_rc" \
    2>/dev/null \
    || dolphin_settings_ok=0

grep -Fqx \
    'MenuBar=Disabled' \
    "$dolphin_installed_rc" \
    2>/dev/null \
    || dolphin_settings_ok=0

if (( dolphin_settings_ok == 1 )); then
    pass "HELM Data Vault settings"
else
    fail "HELM Data Vault settings"
fi

if [[ ! -e "$dolphin_data_ui" ]] \
    && [[ ! -e "$dolphin_config_ui" ]]
then
    pass "Native Dolphin toolbar policy"
else
    fail "Local Dolphin KXMLGUI override detected"
fi

if command -v kreadconfig6 >/dev/null 2>&1; then
    dolphin_color_scheme="$(
        kreadconfig6 \
            --file kdeglobals \
            --group General \
            --key ColorScheme \
            2>/dev/null \
            || true
    )"

    dolphin_icon_theme="$(
        kreadconfig6 \
            --file kdeglobals \
            --group Icons \
            --key Theme \
            2>/dev/null \
            || true
    )"

    if [[ "$dolphin_color_scheme" == "BreezeDark" ]] \
        && [[ "$dolphin_icon_theme" == "breeze" ]]
    then
        pass "HELM Data Vault appearance"
    else
        fail \
            "Dolphin appearance differs: ${dolphin_color_scheme:-unknown}, ${dolphin_icon_theme:-unknown}"
    fi
else
    fail "Dolphin appearance diagnostic unavailable"
fi

if command -v kreadconfig6 >/dev/null 2>&1; then
    dolphin_terminal_profile="$(
        kreadconfig6 \
            --file konsolerc \
            --group 'Desktop Entry' \
            --key DefaultProfile \
            2>/dev/null \
            || true
    )"

    if [[ "$dolphin_terminal_profile" == "HELMMobile.profile" ]]; then
        pass "HELM Data Vault terminal integration"
    else
        fail \
            "Dolphin terminal profile differs: ${dolphin_terminal_profile:-not configured}"
    fi
else
    fail "Dolphin terminal integration diagnostic unavailable"
fi



lockscreen_source_dir="$REPO/mobile/plasma/lockscreen"
lockscreen_manifest="$lockscreen_source_dir/lockscreen.json"
lockscreen_overlay_source="$lockscreen_source_dir/HELMOverlay.qml"

lockscreen_apply="$REPO/scripts/mobile/apply-stage4b-lockscreen.sh"
lockscreen_restore="$REPO/scripts/mobile/restore-stage4b-lockscreen.sh"

lockscreen_data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
lockscreen_config_home="${XDG_CONFIG_HOME:-$HOME/.config}"

lockscreen_target_shell="$lockscreen_data_home/plasma/shells/org.kde.plasma.desktop"
lockscreen_installed_lock="$lockscreen_target_shell/contents/lockscreen/LockScreen.qml"
lockscreen_installed_overlay="$lockscreen_target_shell/contents/lockscreen/HELMOverlay.qml"

lockscreen_wallpaper_source="$REPO/mobile/assets/wallpapers/helm-mobile-field-node-v2.svg"
lockscreen_wallpaper_target="$lockscreen_data_home/helm-mobile/wallpapers/helm-mobile-field-node-v2.svg"

lockscreen_config="$lockscreen_config_home/kscreenlockerrc"
lockscreen_state="$lockscreen_data_home/helm-mobile/stage4b-lockscreen-last-apply.json"

if [[ -s "$lockscreen_manifest" ]] \
    && "$PYTHON_BIN" \
        - "$lockscreen_manifest" \
        >/dev/null 2>&1 \
        <<'PY_LOCK_MANIFEST'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

if payload.get("stage") != "4b-security-lock":
    raise SystemExit(1)

if payload.get("role") != "HELM Mobile Security Lock":
    raise SystemExit(1)

if (
    payload.get("authentication", {}).get("modified")
    is not False
):
    raise SystemExit(1)

appearance = payload.get("appearance", {})

if appearance.get("security_panel_background") != "#FF02070B":
    raise SystemExit(1)

if appearance.get("status_panel_background") != "#FC02070B":
    raise SystemExit(1)

if appearance.get("status_panel_bottom_margin") != 132:
    raise SystemExit(1)
PY_LOCK_MANIFEST
then
    pass "HELM Mobile Security Lock manifest"
else
    fail "HELM Mobile Security Lock manifest"
fi

if [[ -s "$lockscreen_overlay_source" ]] \
    && [[ -x "$lockscreen_apply" ]] \
    && [[ -x "$lockscreen_restore" ]] \
    && [[ -s "$lockscreen_wallpaper_source" ]]
then
    pass "HELM Mobile Security Lock source assets"
else
    fail "HELM Mobile Security Lock source assets"
fi

lock_runtime_state=""

if pacman -Q kscreenlocker >/dev/null 2>&1 \
    && command -v qdbus6 >/dev/null 2>&1
then
    lock_runtime_state="$(
        qdbus6 \
            org.freedesktop.ScreenSaver \
            /ScreenSaver \
            org.freedesktop.ScreenSaver.GetActive \
            2>/dev/null \
            || true
    )"
fi

case "$lock_runtime_state" in
    true | false)
        pass "Plasma Security Lock runtime"
        ;;
    *)
        fail "Plasma Security Lock runtime"
        ;;
esac

if [[ -s "$lockscreen_installed_overlay" ]] \
    && cmp -s \
        "$lockscreen_overlay_source" \
        "$lockscreen_installed_overlay"
then
    pass "Installed Security Lock overlay matches source"
else
    fail "Installed Security Lock overlay differs from source"
fi

if [[ -s "$lockscreen_installed_lock" ]] \
    && grep -Fq \
        'HELM MOBILE SECURITY OVERLAY' \
        "$lockscreen_installed_lock" \
    && [[ "$(
        grep -Fc \
            'HELMOverlay {' \
            "$lockscreen_installed_lock"
    )" == "1" ]]
then
    pass "Plasma lock-screen overlay integration"
else
    fail "Plasma lock-screen overlay integration"
fi

lockscreen_expected_uri="$(
    LOCK_WALLPAPER="$lockscreen_wallpaper_target" \
    "$PYTHON_BIN" - <<'PY_LOCK_URI'
import os
from pathlib import Path

print(
    Path(
        os.environ["LOCK_WALLPAPER"]
    ).resolve().as_uri()
)
PY_LOCK_URI
)"

lockscreen_live_theme="$(
    kreadconfig6 \
        --file kscreenlockerrc \
        --group Greeter \
        --key Theme \
        2>/dev/null \
        || true
)"

lockscreen_live_plugin="$(
    kreadconfig6 \
        --file kscreenlockerrc \
        --group Greeter \
        --key WallpaperPlugin \
        2>/dev/null \
        || true
)"

lockscreen_live_wallpaper="$(
    kreadconfig6 \
        --file kscreenlockerrc \
        --group Greeter \
        --group Wallpaper \
        --group org.kde.image \
        --group General \
        --key Image \
        2>/dev/null \
        || true
)"

if [[ "$lockscreen_live_theme" == "org.kde.plasma.desktop" ]] \
    && [[ "$lockscreen_live_plugin" == "org.kde.image" ]] \
    && [[ "$lockscreen_live_wallpaper" == "$lockscreen_expected_uri" ]] \
    && [[ -s "$lockscreen_wallpaper_target" ]] \
    && cmp -s \
        "$lockscreen_wallpaper_source" \
        "$lockscreen_wallpaper_target"
then
    pass "HELM Mobile Security Lock wallpaper"
else
    fail "HELM Mobile Security Lock wallpaper"
fi

if [[ -s "$lockscreen_state" ]] \
    && LOCK_STATE="$lockscreen_state" \
       OVERLAY_SOURCE="$lockscreen_overlay_source" \
       WALLPAPER_SOURCE="$lockscreen_wallpaper_source" \
       EXPECTED_SHELL="$lockscreen_target_shell" \
       EXPECTED_CONFIG="$lockscreen_config" \
       EXPECTED_WALLPAPER="$lockscreen_wallpaper_target" \
       "$PYTHON_BIN" - >/dev/null 2>&1 <<'PY_LOCK_STATE'
import hashlib
import json
import os
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


state = json.loads(
    Path(
        os.environ["LOCK_STATE"]
    ).read_text(
        encoding="utf-8"
    )
)

if state.get("stage") != "4b-security-lock":
    raise SystemExit(1)

if state.get("target_shell") != os.environ["EXPECTED_SHELL"]:
    raise SystemExit(1)

if state.get("lock_config") != os.environ["EXPECTED_CONFIG"]:
    raise SystemExit(1)

if state.get("wallpaper_target") != os.environ["EXPECTED_WALLPAPER"]:
    raise SystemExit(1)

if not Path(state.get("recovery", "")).is_dir():
    raise SystemExit(1)

if state.get("overlay_sha256") != digest(
    Path(os.environ["OVERLAY_SOURCE"])
):
    raise SystemExit(1)

if state.get("wallpaper_sha256") != digest(
    Path(os.environ["WALLPAPER_SOURCE"])
):
    raise SystemExit(1)
PY_LOCK_STATE
then
    pass "HELM Mobile Security Lock recovery state"
else
    fail "HELM Mobile Security Lock recovery state"
fi


lockscreen_v21_source_dir="$REPO/mobile/plasma/lockscreen"
lockscreen_v21_live_dir="${XDG_DATA_HOME:-$HOME/.local/share}/plasma/shells/org.kde.plasma.desktop/contents/lockscreen"

if [[ -s "$lockscreen_v21_source_dir/LockScreen.qml" ]] \
    && [[ -s "$lockscreen_v21_source_dir/LockScreenUi.qml" ]] \
    && [[ -s "$lockscreen_v21_source_dir/MainBlock.qml" ]] \
    && [[ -s "$lockscreen_v21_source_dir/HELMOverlay.qml" ]] \
    && [[ "$(jq -r '.revision // empty' "$lockscreen_v21_source_dir/lockscreen.json" 2>/dev/null)" == "2.1" ]]
then
    pass "HELM Security Lock v2.1 source UI"
else
    fail "HELM Security Lock v2.1 source UI"
fi

lockscreen_v21_matches=1

for lockscreen_v21_file in \
    LockScreen.qml \
    LockScreenUi.qml \
    MainBlock.qml \
    HELMOverlay.qml
do
    if ! cmp -s \
        "$lockscreen_v21_source_dir/$lockscreen_v21_file" \
        "$lockscreen_v21_live_dir/$lockscreen_v21_file"
    then
        lockscreen_v21_matches=0
    fi
done

if (( lockscreen_v21_matches == 1 )); then
    pass "Installed Security Lock v2.1 UI matches source"
else
    fail "Installed Security Lock v2.1 UI differs from source"
fi

if grep -Fq \
        'authenticator.respond(password)' \
        "$lockscreen_v21_live_dir/LockScreenUi.qml" \
    && grep -Fq \
        'signal passwordResult(string password)' \
        "$lockscreen_v21_live_dir/MainBlock.qml" \
    && grep -Fq \
        'passwordResult(password)' \
        "$lockscreen_v21_live_dir/MainBlock.qml"
then
    pass "Security Lock native authentication flow preserved"
else
    fail "Security Lock native authentication flow preserved"
fi

if [[ -s "$lockscreen_state" ]] \
    && [[ "$(jq -r '.visual_revision // empty' "$lockscreen_state" 2>/dev/null)" == "2.1" ]] \
    && [[ "$(jq -r '.real_unlock_verified // false' "$lockscreen_state" 2>/dev/null)" == "true" ]]
then
    pass "Security Lock v2.1 real unlock verified"
else
    warning "Security Lock v2.1 real unlock not yet verified"
fi

technical_boot_manifest="$REPO/mobile/boot/technical-boot.json"
technical_boot_state="${XDG_DATA_HOME:-$HOME/.local/share}/helm-mobile/stage4d-technical-boot-baseline.json"

technical_boot_manifest_ok=0
if [[ -s "$technical_boot_manifest" ]]; then
    if jq -e '.stage == "4d-technical-boot" and .role == "HELM Mobile Technical Boot" and .bootloader.provider == "systemd-boot" and .bootloader.selected_entry == "arch-linux.efi" and .bootloader.active_uki == "/boot/EFI/Linux/arch-linux.efi" and .kernel_command_line.quiet == false and .kernel_command_line.splash == false and .kernel_command_line.preserve_verbose_output == true and .initramfs.plymouth_hook == false and .initramfs.preserve_console_luks_prompt == true and .safety.modify_active_uki == false and .safety.rebuild_uki == false and .safety.modify_kernel_cmdline == false and .safety.modify_mkinitcpio_hooks == false and .safety.modify_bootloader == false and .safety.automatic_reboot == false' "$technical_boot_manifest" >/dev/null 2>&1; then
        technical_boot_manifest_ok=1
    fi
fi
if (( technical_boot_manifest_ok == 1 )); then pass "HELM Mobile Technical Boot manifest"; else fail "HELM Mobile Technical Boot manifest"; fi

technical_boot_status="$(bootctl status --no-pager 2>/dev/null || true)"
if grep -Fq 'Current Entry: arch-linux.efi' <<< "$technical_boot_status" && grep -Fq '/EFI/Linux/arch-linux.efi' <<< "$technical_boot_status"; then pass "Technical Boot active UKI"; else fail "Technical Boot active UKI"; fi

technical_boot_cmdline="$(cat /proc/cmdline 2>/dev/null || true)"
if [[ " $technical_boot_cmdline " != *" quiet "* ]] && [[ " $technical_boot_cmdline " != *" splash "* ]]; then pass "Technical Boot verbose command line"; else fail "Technical Boot verbose command line"; fi

if grep -Fqx 'default_uki="/boot/EFI/Linux/arch-linux.efi"' /etc/mkinitcpio.d/linux.preset 2>/dev/null && grep -Fqx 'default_options="--splash /usr/share/systemd/bootctl/splash-arch.bmp"' /etc/mkinitcpio.d/linux.preset 2>/dev/null; then pass "Technical Boot Arch UKI splash"; else fail "Technical Boot Arch UKI splash"; fi

technical_boot_hooks="$(grep -E '^[[:space:]]*HOOKS=' /etc/mkinitcpio.conf 2>/dev/null | tail -n 1)"
technical_boot_hook_words="$(sed -E 's/^[^(]*\((.*)\).*/\1/' <<< "$technical_boot_hooks")"
if [[ " $technical_boot_hook_words " == *" block "* ]] && [[ " $technical_boot_hook_words " == *" encrypt "* ]] && [[ " $technical_boot_hook_words " == *" filesystems "* ]] && [[ " $technical_boot_hook_words " != *" plymouth "* ]] && [[ "$technical_boot_hook_words" =~ block.*encrypt.*filesystems ]]; then pass "Technical Boot console LUKS flow"; else fail "Technical Boot console LUKS flow"; fi

technical_boot_recovery_ok=0
if [[ -s "$technical_boot_state" ]]; then
    technical_boot_recovery="$(jq -r '.recovery // empty' "$technical_boot_state" 2>/dev/null || true)"
    technical_boot_backup="$(jq -r '.active_uki_backup // empty' "$technical_boot_state" 2>/dev/null || true)"
    technical_boot_baseline_sha="$(jq -r '.baseline_uki_sha256 // empty' "$technical_boot_state" 2>/dev/null || true)"
    technical_boot_modified="$(jq -r 'if has("boot_modified") then .boot_modified else true end' "$technical_boot_state" 2>/dev/null || true)"
    technical_boot_rebuilt="$(jq -r 'if has("uki_rebuilt") then .uki_rebuilt else true end' "$technical_boot_state" 2>/dev/null || true)"
    if [[ -d "$technical_boot_recovery" ]] && [[ -s "$technical_boot_backup" ]] && [[ "$technical_boot_modified" == "false" ]] && [[ "$technical_boot_rebuilt" == "false" ]] && [[ "$(sha256sum "$technical_boot_backup" 2>/dev/null | awk '{print $1}')" == "$technical_boot_baseline_sha" ]]; then
        technical_boot_recovery_ok=1
    fi
fi
if (( technical_boot_recovery_ok == 1 )); then pass "Technical Boot recovery baseline"; else fail "Technical Boot recovery baseline"; fi
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
