# Runtime Data and Recovery

HELM v1.2 separates mutable user state from the Git working tree. Source and
example data stay in the repository; live settings, workspaces and projects are
stored in an XDG-compatible data directory.

## Data-root resolution

`services/runtime_data.py` resolves the root in this order:

1. `HELM_DATA_DIR` — used exactly as the explicit data directory;
2. `$XDG_DATA_HOME/helm` — when `XDG_DATA_HOME` is set;
3. `~/.local/share/helm` — default.

Check the active location with:

```bash
printf '%s\n' "${HELM_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/helm}"
```

The same resolution is used by `helm doctor`.

## Runtime tree

```text
DATA_ROOT/
├── settings.json
├── modes.json
├── mode_state.json
├── projects.json
├── backups/
│   └── settings-TIMESTAMP.json
├── exports/
│   └── settings-profile-TIMESTAMP.json
└── recovery/
    ├── settings.last-good.json
    ├── modes.last-good.json
    ├── mode_state.last-good.json
    ├── projects.last-good.json
    └── NAME-TIMESTAMP.broken.json
```

`logs/helm.log` and log/AI/health exports remain in the repository-local ignored
`logs/` tree. Desktop Node configuration remains in `~/.config/helm/`.

## File ownership

| Runtime file | Primary writer | Readers |
|---|---|---|
| `settings.json` | `SettingsService` | main app, SETTINGS, Core Health |
| `modes.json` | `ModeService` | main app, MODES, Core Health |
| `mode_state.json` | `ModeService` | main app, MODES, Core Health |
| `projects.json` | `ProjectService` | PROJECTS, `ProjectMonitor`, Core Health |

## Initialization and migration

Each file is managed by `RuntimeJsonStore`. When HELM needs a payload, the store
uses this recovery order:

```text
1. current runtime file
2. last-good recovery snapshot
3. legacy repository file (config/NAME.json)
4. repository example (config/NAME.example.json)
5. code default factory
```

Every candidate is parsed, required to have a JSON object as its root and then
validated by the owning service. Invalid candidates are skipped.

The v1.2 migration is non-destructive:

- a valid legacy `config/settings.json`, `modes.json`, `mode_state.json` or
  `projects.json` is copied into the runtime data root on first use;
- the legacy file is not deleted;
- later writes target only the runtime data root;
- repository examples remain unchanged.

## Normal reads and writes

A successful read refreshes `recovery/NAME.last-good.json`.

A write follows this sequence:

1. clone and validate the complete payload;
2. write formatted UTF-8 JSON to a process-specific temporary file;
3. flush and `fsync` the file;
4. atomically replace the target with `os.replace`;
5. repeat the same operation for the last-good snapshot.

This prevents readers from observing a partially written JSON document. It does
not provide a database transaction across multiple files.

## Corruption recovery

When the active runtime file exists but cannot be parsed or validated:

1. it is copied to `recovery/NAME-TIMESTAMP.broken.json`;
2. the invalid active file is removed;
3. HELM tries the last-good snapshot and then the remaining fallback sources;
4. the recovered payload is written back to the active path;
5. the recovered payload becomes the new last-good snapshot.

Do not delete the `.broken.json` copy until you have inspected it and confirmed
that no useful manual edits need to be recovered.

## Diagnostics

Run the application-level release checks:

```bash
cd ~/.cyberdeck/nexus
scripts/check-release.sh
```

Audit the installed workstation and runtime pipeline:

```bash
helm doctor
```

A nominal v1.2 target reports valid active JSON, all four last-good snapshots and
a passing runtime service recovery pipeline.

## Backups

There are two separate backup concepts.

### Settings backup

The SETTINGS screen creates up to ten timestamped copies of `settings.json` in
`DATA_ROOT/backups/`. It does not back up modes or projects.

### Full CyberDeck backup

`helm backup` creates a recovery archive under `~/.cyberdeck/backups/`. In v1.2
it includes the complete runtime data root in addition to desktop configuration,
launchers, boot/login assets and a Git repository bundle.

The archive is not encrypted. Treat it as private because projects, paths and AI
settings may identify the workstation or user.

## Manual backup and restore

For a direct runtime-only copy:

```bash
DATA_ROOT="${HELM_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/helm}"
cp -a "$DATA_ROOT" "$HOME/helm-runtime-backup"
```

Restore while HELM is stopped:

```bash
helm stop
DATA_ROOT="${HELM_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/helm}"
cp -a "$HOME/helm-runtime-backup/." "$DATA_ROOT/"
helm start
helm doctor
```

## Safe manual editing

1. Stop HELM to avoid competing writes.
2. Back up the target file.
3. Edit UTF-8 JSON with an object at the root.
4. Validate it before restarting:

```bash
python -m json.tool ~/.local/share/helm/settings.json >/dev/null
```

5. Start HELM and run `helm doctor`.

## Known limits

- Runtime JSON has no cross-process file lock; one HELM instance is the supported
  writer model.
- Last-good is one recovery point, not version history.
- Quarantined `.broken.json` files are retained until the user removes them.
- Atomic replacement is filesystem-local; power-loss durability still depends on
  the filesystem and storage stack.
- Settings backup rotation applies only to SETTINGS backups, not quarantine files.
- A custom data directory outside the home directory must be writable by the user
  and may require special handling during restore.
