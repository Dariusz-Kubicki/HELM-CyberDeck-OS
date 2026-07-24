#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
printf 'HELM release check\n==================\n\n'
python -m compileall -q app modules services
printf '[PASS] Python sources compile.\n'
python -c 'import json, pathlib; [json.load(p.open(encoding="utf-8")) for p in pathlib.Path("config").glob("*.json")]; print("[PASS] JSON configuration is valid.")'
for forbidden in logs/helm.log config/mode_state.json; do
    if [[ -d .git ]] && git ls-files --error-unmatch "$forbidden" >/dev/null 2>&1; then
        printf '[FAIL] Runtime file is tracked: %s\n' "$forbidden" >&2
        exit 1
    fi
done
printf '[PASS] Known runtime files are not tracked.\n'
if command -v rg >/dev/null 2>&1; then
    if rg -n --hidden -S --glob '!docs/images/**' --glob '!.git/**' '(ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AKIA[0-9A-Z]{16})' .; then
        printf '[FAIL] Possible secret found.\n' >&2
        exit 1
    fi
    printf '[PASS] No common secret pattern detected.\n'
else
    printf '[INFO] ripgrep unavailable; secret scan skipped.\n'
fi
printf '\nRelease check completed successfully.\n'
