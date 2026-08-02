# Controlled Screenshot Checklist

Screenshots are release artifacts. Capture them from a known, clean state so the
README demonstrates HELM without leaking personal data or showing contradictory
versions.

## Capture environment

- Target workstation: supported Arch Linux + KDE Plasma session.
- HELM version: final release candidate, not an earlier tagged build.
- Sidebar and boot modal: both display the exact target release version.
- Terminal: approximately 122 × 57 cells or a larger window with the same layout.
- Theme: HELM/Graphite dark desktop state with cyan accents.
- Runtime data: reviewed demo-safe projects, modes and settings.
- Desktop Node: either intentionally visible in a desktop shot or intentionally
  excluded from a terminal-only shot.
- No notifications, browser tabs, usernames, private paths, IP addresses, serial
  numbers, tokens or personal project notes visible.

## Required images

| File | Required state |
|---|---|
| `docs/images/system-overview.png` | SYSTEM after telemetry is stable; no critical alert; full cards, histories and inspector visible. |
| `docs/images/boot-sequence.png` | HELM boot modal during an intentional, readable stage. |
| `docs/images/modes-control-center.png` | MODES with a representative workspace selected and no personal app/path data. |
| `docs/images/event-log.png` | LOGS with harmless representative events and readable filters/inspector. |
| `docs/images/ai-core.png` | AI screen showing deterministic or local read-only diagnostics without private prompts. |

## Recommended v1.2 additions

| File | Purpose |
|---|---|
| `docs/images/projects-mission-control.png` | Demonstrate the project database using example-safe entries. |
| `docs/images/settings-runtime-recovery.png` | Show SETTINGS diagnostics, runtime path and backup/recovery state. |
| `docs/images/cyberdeck-desktop.png` | Show the complete Plasma workstation and Desktop Node. |
| `docs/images/doctor-nominal.png` | Show the final `helm doctor` summary with `SYSTEM STATE: NOMINAL`. |

Only add recommended images to README when they improve the page rather than make
it excessively long.

## Capture procedure

1. Create a full recovery archive with `helm backup`.
2. Confirm `git status --short --branch` is expected.
3. Start HELM and wait for telemetry/Core Health to settle.
4. Verify visible data line by line.
5. Capture PNG at native scale; do not use lossy JPEG.
6. Crop only empty desktop margins; do not crop HELM labels or status context.
7. Replace the intended file in `docs/images/`.
8. Open every image and verify readability at README width.
9. Search the screenshot manually for private information.
10. Run the release check and review the README rendering on GitHub.

## Final verification

```bash
file docs/images/*.png
scripts/check-release.sh
git diff --stat
git diff -- docs/images README.md README.pl.md
```

The final release notes should mention only screenshots that are actually present
in the tagged commit.
