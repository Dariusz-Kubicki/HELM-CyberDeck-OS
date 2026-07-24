#!/usr/bin/env bash

set -u

clear

line() {
    printf '%*s\n' 78 '' | tr ' ' '='
}

section() {
    printf '\n'
    line
    printf ' HELM // %s\n' "$1"
    line
    printf '\n'
}

run_if_available() {
    local command_name="$1"
    shift

    if command -v "$command_name" >/dev/null 2>&1; then
        "$@" 2>&1
    else
        printf '%s is not installed.\n' "$command_name"
    fi
}

section "SYSTEM IDENTITY"

printf 'HOST:   %s\n' "$(hostname)"
printf 'USER:   %s\n' "${USER:-unknown}"
printf 'KERNEL: %s\n' "$(uname -r)"
printf 'UPTIME: %s\n' "$(uptime -p 2>/dev/null || uptime)"

section "SYSTEM OVERVIEW"

if command -v fastfetch >/dev/null 2>&1; then
    fastfetch
else
    uname -a
fi

section "MEMORY"

run_if_available free free -h

section "FILESYSTEM"

df -h /
printf '\n'
run_if_available lsblk \
    lsblk -o NAME,MODEL,SIZE,TYPE,FSTYPE,MOUNTPOINTS

section "NETWORK"

if command -v ip >/dev/null 2>&1; then
    ip -brief address
    printf '\n'
    ip route
else
    printf 'iproute2 is not installed.\n'
fi

section "TEMPERATURES"

run_if_available sensors sensors

section "NVIDIA GPU"

run_if_available nvidia-smi nvidia-smi

section "RECENT BOOT ERRORS"

if command -v journalctl >/dev/null 2>&1; then
    journalctl \
        --boot \
        --priority=3 \
        --no-pager \
        --lines=15 2>&1
else
    printf 'journalctl is not available.\n'
fi

section "DIAGNOSTIC COMPLETE"

printf 'Generated: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
printf 'HELM project: %s\n' "$PROJECT_ROOT"
