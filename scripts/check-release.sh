#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
    pwd
)"

cd "$PROJECT_ROOT"

PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="$(
        command -v python3 \
        || command -v python
    )"
fi

printf 'HELM release check\n'
printf '==================\n\n'

"$PYTHON_BIN" \
    -m compileall \
    -q \
    app \
    modules \
    services \
    tests

printf '[PASS] Python sources compile.\n'

"$PYTHON_BIN" \
    -m unittest \
    discover \
    -s tests \
    -p 'test_*.py'

printf '[PASS] Unit tests pass.\n'

"$PYTHON_BIN" - <<'PY_JSON'
import json
from pathlib import Path

paths = tuple(
    sorted(
        (
            *Path("config").glob("*.example.json"),
            *Path("desktop/config").glob(
                "*.example.json"
            ),
        )
    )
)

if not paths:
    raise SystemExit(
        "No example JSON files were found."
    )

for path in paths:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise SystemExit(
            f"JSON root must be an object: {path}"
        )

print(
    f"[PASS] {len(paths)} example JSON files "
    "are valid."
)
PY_JSON

for forbidden in \
    logs/helm.log \
    config/settings.json \
    config/modes.json \
    config/mode_state.json \
    config/projects.json
do
    if [[ -d .git ]] \
        && git ls-files \
            --error-unmatch \
            "$forbidden" \
            >/dev/null 2>&1
    then
        printf \
            '[FAIL] Runtime file is tracked: %s\n' \
            "$forbidden" \
            >&2
        exit 1
    fi
done

printf '[PASS] Mutable runtime files are not tracked.\n'

if [[ -d .git ]]; then
    tracked_artifacts="$({
        git ls-files \
            | grep -E '(^|/)([^/]+\.bak|[^/]+\.before-[^/]*|[^/]+\.backup-[^/]*)$' \
            | while IFS= read -r artifact; do
                [[ -e "$artifact" ]] \
                    && printf '%s\n' "$artifact"
            done \
            || true
    })"

    if [[ -n "$tracked_artifacts" ]]; then
        printf '[FAIL] Local backup artifact is tracked:\n%s\n' \
            "$tracked_artifacts" \
            >&2
        exit 1
    fi
fi

printf '[PASS] No local backup artifact is tracked.\n'

if command -v rg >/dev/null 2>&1; then
    if rg \
        -n \
        --hidden \
        -S \
        --glob '!docs/images/**' \
        --glob '!.git/**' \
        '(ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AKIA[0-9A-Z]{16})' \
        .
    then
        printf '[FAIL] Possible secret found.\n' >&2
        exit 1
    fi

    printf '[PASS] No common secret pattern detected.\n'
else
    printf \
        '[INFO] ripgrep unavailable; secret scan skipped.\n'
fi

printf '\nRelease check completed successfully.\n'
