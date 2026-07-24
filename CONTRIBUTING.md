# Contributing

Thank you for considering a contribution to HELM CyberDeck OS.

## Before opening a pull request

1. Create a branch from `master`.
2. Keep Linux-specific behavior isolated in `modules/` or `services/`.
3. Do not perform blocking subprocess or network work in the Textual UI thread.
4. Do not let the local AI execute arbitrary commands.
5. Preserve graceful fallback behavior when optional tools are absent.
6. Run:

```bash
python -m compileall -q app modules services
./scripts/check-release.sh
```

7. Test the UI in a terminal close to 122 × 57 cells.

## Code style

- Python 3.11+ type hints.
- Small dataclasses for samples and action results.
- Dedicated service classes for side effects.
- Atomic writes for mutable JSON.
- User-visible errors should be actionable and logged.

## Bug reports

Include distribution, desktop, terminal dimensions, Python/Textual versions, launch command, reviewed log lines and a screenshot for visual issues.

## AI-generated contributions

AI-assisted pull requests are welcome, but contributors remain responsible for testing, disclosure and safety.
