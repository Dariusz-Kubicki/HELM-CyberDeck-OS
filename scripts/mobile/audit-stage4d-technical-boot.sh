#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C.UTF-8

REPO="${HELM_PROJECT_DIR:-$HOME/.cyberdeck/nexus}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
MANIFEST="$REPO/mobile/boot/technical-boot.json"
STATE="$DATA_HOME/helm-mobile/stage4d-technical-boot-baseline.json"
ACTIVE_UKI="/boot/EFI/Linux/arch-linux.efi"
PRESET="/etc/mkinitcpio.d/linux.preset"
MKINITCPIO_CONF="/etc/mkinitcpio.conf"
KERNEL_CMDLINE="/etc/kernel/cmdline"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT="$DATA_HOME/helm-mobile/audit/stage4d-technical-boot-$STAMP.txt"
mkdir -p "$(dirname "$REPORT")"
exec > >(tee "$REPORT") 2>&1

OK=0
FAIL=0
pass() { echo "[PASS] $*"; ((OK+=1)); }
fail() { echo "[FAIL] $*"; ((FAIL+=1)); }

echo '===== HELM MOBILE TECHNICAL BOOT — READ-ONLY AUDIT ====='
sudo -v

manifest_ok=0
if [[ -s "$MANIFEST" ]]; then
    if jq -e '.stage == "4d-technical-boot" and .kernel_command_line.quiet == false and .kernel_command_line.splash == false and .initramfs.plymouth_hook == false and .safety.modify_active_uki == false and .safety.automatic_reboot == false' "$MANIFEST" >/dev/null 2>&1; then
        manifest_ok=1
    fi
fi
if (( manifest_ok == 1 )); then pass "Technical Boot manifest"; else fail "Technical Boot manifest"; fi

BOOT_STATUS="$(sudo bootctl status --no-pager 2>/dev/null || true)"
if grep -Fq 'Current Entry: arch-linux.efi' <<< "$BOOT_STATUS" && grep -Fq '/EFI/Linux/arch-linux.efi' <<< "$BOOT_STATUS"; then
    pass "Selected entry maps to arch-linux.efi"
else
    fail "Selected entry / active UKI mapping"
fi

CURRENT_SHA=""
if sudo test -f "$ACTIVE_UKI"; then
    pass "Active UKI exists"
    CURRENT_SHA="$(sudo sha256sum "$ACTIVE_UKI" | awk '{print $1}')"
    echo "Current UKI SHA256: $CURRENT_SHA"
else
    fail "Active UKI missing"
fi

if [[ -s "$STATE" ]]; then
    BASELINE_SHA="$(jq -r '.baseline_uki_sha256 // empty' "$STATE")"
    BACKUP="$(jq -r '.active_uki_backup // empty' "$STATE")"
    if [[ -n "$BASELINE_SHA" ]] && [[ -s "$BACKUP" ]] && [[ "$(sha256sum "$BACKUP" | awk '{print $1}')" == "$BASELINE_SHA" ]]; then
        pass "Recovery UKI checksum"
    else
        fail "Recovery UKI checksum"
    fi
    if [[ -n "$CURRENT_SHA" ]] && [[ -n "$BASELINE_SHA" ]]; then
        if [[ "$CURRENT_SHA" == "$BASELINE_SHA" ]]; then
            echo "[INFO] Active UKI still matches Stage 4D baseline."
        else
            echo "[INFO] Active UKI changed since baseline; this can be normal after a kernel upgrade."
        fi
    fi
else
    fail "Stage 4D runtime baseline state"
fi

CURRENT_CMDLINE="$(cat /proc/cmdline)"
if [[ " $CURRENT_CMDLINE " != *" quiet "* ]] && [[ " $CURRENT_CMDLINE " != *" splash "* ]]; then pass "Running boot remains verbose"; else fail "Running command line contains quiet/splash"; fi

PERSISTENT_CMDLINE="$(cat "$KERNEL_CMDLINE")"
if [[ " $PERSISTENT_CMDLINE " != *" quiet "* ]] && [[ " $PERSISTENT_CMDLINE " != *" splash "* ]]; then pass "Persistent boot remains verbose"; else fail "Persistent command line contains quiet/splash"; fi

if grep -Fqx 'default_uki="/boot/EFI/Linux/arch-linux.efi"' "$PRESET" && grep -Fqx 'default_options="--splash /usr/share/systemd/bootctl/splash-arch.bmp"' "$PRESET"; then
    pass "Arch UKI splash preserved"
else
    fail "Arch UKI preset differs"
fi

HOOKS_LINE="$(grep -E '^[[:space:]]*HOOKS=' "$MKINITCPIO_CONF" | tail -n 1)"
HOOKS_WORDS="$(sed -E 's/^[^(]*\((.*)\).*/\1/' <<< "$HOOKS_LINE")"
if [[ " $HOOKS_WORDS " == *" block "* ]] && [[ " $HOOKS_WORDS " == *" encrypt "* ]] && [[ " $HOOKS_WORDS " == *" filesystems "* ]] && [[ " $HOOKS_WORDS " != *" plymouth "* ]] && [[ "$HOOKS_WORDS" =~ block.*encrypt.*filesystems ]]; then
    pass "Console LUKS hook policy"
else
    fail "Console LUKS hook policy"
fi

echo
echo '===== READ-ONLY GUARANTEES ====='
echo '[PASS] No UKI was rebuilt.'
echo '[PASS] No boot file was modified.'
echo '[PASS] mkinitcpio was not executed.'
echo '[PASS] No bootloader configuration was changed.'
echo '[PASS] No reboot was requested.'
echo
echo "Checks: $OK OK, $FAIL failures"
echo "Report: $REPORT"
(( FAIL == 0 ))
