# HELM CyberDeck OS v1.2.0

HELM v1.2.0 moves mutable settings, workspaces, workspace state and projects out
of the Git working tree and into resilient XDG-style runtime storage. The release
also improves desktop storage presentation, control geometry, recovery diagnostics
and maintainer documentation.

## Highlights

- Runtime data root at `~/.local/share/helm` by default, with `XDG_DATA_HOME` and
  `HELM_DATA_DIR` overrides.
- Non-destructive first-run migration from legacy `config/*.json` files.
- Validated atomic writes with last-known-good recovery snapshots.
- Automatic quarantine of corrupt runtime JSON before recovery.
- Runtime migration/recovery tests for settings, modes, active mode and projects.
- Extended `helm doctor` runtime checks and release validation.
- Configurable Desktop Node storage volumes.
- Refined HELM control geometry and signature rail.
- Complete codebase, runtime, development, decision and screenshot documentation.
- Full CyberDeck backup now includes the runtime data root.

## Upgrade notes

1. Back up the workstation with `helm backup`.
2. Update the repository and launch HELM normally.
3. On first access, valid legacy runtime files in `config/` are copied to the new
   data root; the originals are retained.
4. Run `helm doctor` and confirm all runtime JSON and last-good snapshots pass.
5. After verification, keep legacy files only as temporary migration evidence;
   they remain ignored and are no longer active write targets.

Default runtime tree:

```text
~/.local/share/helm/
├── settings.json
├── modes.json
├── mode_state.json
├── projects.json
└── recovery/*.last-good.json
```

## Validation target

The release candidate is expected to pass:

```text
12/12 runtime unit tests
5/5 example JSON files
38/38 installed CyberDeck diagnostic checks
0 warnings
0 failures
SYSTEM STATE: NOMINAL
```

The installed diagnostic count is specific to the complete supported workstation;
missing optional tools or a stopped Desktop Node can produce documented warnings
on other installations.

## Known limitations

- Primary support remains Arch Linux + KDE Plasma.
- NVIDIA, SMART and Ollama telemetry depends on optional host tools/services.
- Runtime JSON is designed for one HELM writer at a time.
- Automated Textual visual snapshot tests are not yet included.
- Full backup archives are not encrypted.

See [docs/DECISIONS.md](docs/DECISIONS.md) for the complete list.
