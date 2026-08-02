# Contributing

Thank you for considering a contribution to HELM CyberDeck OS.

## Before opening a pull request

1. Create a branch from `master`.
2. Keep Linux-specific observation in `modules/` and side effects in dedicated
   services.
3. Do not perform blocking subprocess, filesystem or network work in the Textual
   UI thread.
4. Do not let local AI execute arbitrary commands.
5. Preserve graceful fallback behavior when optional tools are absent.
6. Keep mutable user state outside Git and use `RuntimeJsonStore` for runtime JSON.
7. Add tests for migration, validation and recovery when persistence changes.
8. Run:

```bash
scripts/check-release.sh
git diff --check
```

9. For desktop changes, run `helm doctor` on the supported target.
10. Test the UI in a terminal close to 122 × 57 cells.

## Code style

- Python 3.11+ type hints.
- Small dataclasses for samples and action results.
- Dedicated service classes for side effects.
- Validated atomic writes for mutable JSON.
- User-visible errors should be actionable and logged.
- Avoid broad refactors in release-preparation commits.

## Test isolation

Use an isolated runtime root when a test or manual experiment can write data:

```bash
export HELM_DATA_DIR="$(mktemp -d)"
```

Never use or attach another person's live runtime data without reviewing it.

## Documentation

Update the relevant README and docs whenever behavior, storage, diagnostics,
commands, desktop installation or recovery changes. Architecture and recovery
claims must match the actual code paths.

## Bug reports

Include distribution, desktop, terminal dimensions, Python/Textual versions,
launch command, reviewed log lines, `helm doctor` summary and a screenshot for
visual issues. Remove secrets and personal data first.

## AI-generated contributions

AI-assisted pull requests are welcome, but contributors remain responsible for
testing, disclosure, security review and the correctness of every committed line.
