#!/usr/bin/env bash
set -uo pipefail

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
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

check_file() {
    [[ -f "$1" ]] && pass "$2" || fail "$2 — missing: $1"
}

check_dir() {
    [[ -d "$1" ]] && pass "$2" || fail "$2 — missing: $1"
}

check_contains() {
    local file="$1" pattern="$2" label="$3"
    if [[ -f "$file" ]] && grep -Eq "$pattern" "$file"; then
        pass "$label"
    else
        fail "$label"
    fi
}

printf '%s◈ HELM CYBERDECK DIAGNOSTIC%s\n\n' "$cyan" "$reset"

check_dir "$REPO/.git" "Repository"
check_file "$REPO/VERSION" "Version manifest"
check_file "$HOME/.local/bin/helm" "HELM launcher"
check_file "$HOME/.local/bin/helm-start" "HELM start bridge"
check_file "$HOME/.config/autostart/helm-cyberdeck.desktop" "HELM autostart"
check_file "$HOME/.config/autostart/helm-desktop-node.desktop" "Desktop Node autostart"
check_file "$HOME/.config/conky/cyberdeck.conf" "Desktop Node configuration"

if pgrep -u "$UID" -f '[p]ython.*-m app\.main' >/dev/null 2>&1; then
    pass "HELM Core running"
else
    warning "HELM Core is not running"
fi

if pgrep -u "$UID" -x conky >/dev/null 2>&1; then
    pass "Desktop Node online"
else
    warning "Desktop Node is offline"
fi

if [[ -x "$REPO/venv/bin/python" ]] \
    && "$REPO/venv/bin/python" -c 'import textual, psutil' >/dev/null 2>&1
then
    pass "Python virtual environment"
else
    fail "Python virtual environment or dependencies"
fi

color_scheme="$(kreadconfig6 --file kdeglobals --group General --key ColorScheme 2>/dev/null || true)"
plasma_style="$(kreadconfig6 --file plasmarc --group Theme --key name 2>/dev/null || true)"
global_theme="$(kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage 2>/dev/null || true)"

[[ "$color_scheme" == "HELMCyberdeck" ]] \
    && pass "KDE color scheme: HELMCyberdeck" \
    || warning "KDE color scheme: ${color_scheme:-unknown}"

[[ "$plasma_style" == "HELM-Plasma" ]] \
    && pass "Plasma style: HELM-Plasma" \
    || warning "Plasma style: ${plasma_style:-unknown}"

[[ -n "$global_theme" ]] \
    && pass "Global theme: $global_theme" \
    || warning "Global theme is not reported"

check_dir "$HOME/.local/share/plasma/desktoptheme/HELM-Plasma" "HELM Plasma package"
check_file "$HOME/.local/share/color-schemes/HELMCyberdeck.colors" "HELM color scheme"

lock_qml="$HOME/.local/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/LockScreen.qml"
check_contains "$lock_qml" 'helmSecurityOverlay|SECURITY LOCK' "HELM Security Lock overlay"

check_dir "/usr/share/sddm/themes/HELM-Access-Gate" "HELM Access Gate package"
check_contains "/etc/sddm.conf.d/zz-helm-theme.conf" 'Current=HELM-Access-Gate' "SDDM selects HELM Access Gate"

selected_plymouth="$(plymouth-set-default-theme 2>/dev/null || true)"
[[ "$selected_plymouth" == "helm-cyberdeck" ]] \
    && pass "Plymouth theme: helm-cyberdeck" \
    || fail "Plymouth theme: ${selected_plymouth:-unknown}"

check_dir "/usr/share/plymouth/themes/helm-cyberdeck" "HELM Plymouth package"
check_contains "/etc/mkinitcpio.conf.d/90-helm-plymouth.conf" 'systemd[[:space:]]+plymouth' "Plymouth initramfs hook"
check_contains "/boot/loader/entries/arch.conf" 'quiet.*splash.*plymouth\.use-simpledrm=1' "Silent SimpleDRM boot entry"
check_contains "/boot/loader/entries/arch-diagnostic.conf" 'plymouth\.enable=0.*disablehooks=plymouth' "Diagnostic boot entry"

if lsinitcpio /boot/initramfs-linux.img 2>/dev/null \
    | grep -q 'helm-cyberdeck'
then
    pass "HELM theme embedded in initramfs"
else
    fail "HELM theme missing from initramfs"
fi

check_file "$HOME/.config/dolphinrc" "Dolphin Data Vault configuration"
check_file "$HOME/.local/bin/vault" "Data Vault launcher"

firefox_css="$(find "$HOME/.config/mozilla/firefox" -maxdepth 3 \
    -type f -path '*/chrome/userChrome.css' -print -quit 2>/dev/null || true)"
[[ -n "$firefox_css" ]] \
    && pass "Firefox HELM userChrome" \
    || warning "Firefox userChrome.css not found"

if [[ -r "$REPO/desktop/manifests/desktop-state.env" ]]; then
    # shellcheck disable=SC1090
    source "$REPO/desktop/manifests/desktop-state.env"
    current_plasma="$(pacman -Q plasma-workspace 2>/dev/null | awk '{print $2}' || true)"
    if [[ -n "${PLASMA_WORKSPACE_VERSION:-}" \
        && "$current_plasma" != "$PLASMA_WORKSPACE_VERSION" ]]
    then
        warning "Plasma changed: snapshot $PLASMA_WORKSPACE_VERSION, current $current_plasma. Run: helm rebuild-lock"
    else
        pass "Plasma version matches desktop snapshot"
    fi
fi

printf '\n%sSYSTEM STATE%s: ' "$cyan" "$reset"
if (( FAIL > 0 )); then
    printf '%sDEGRADED%s\n' "$red" "$reset"
elif (( WARN > 0 )); then
    printf '%sNOMINAL WITH WARNINGS%s\n' "$yellow" "$reset"
else
    printf '%sNOMINAL%s\n' "$green" "$reset"
fi

printf 'Checks: %d OK, %d warnings, %d failures\n' "$OK" "$WARN" "$FAIL"
(( FAIL == 0 ))
