# Configuration Reference

HELM v1.2 stores mutable application data outside the repository. Stop HELM
before manual editing.

## Locations

Runtime root resolution:

1. `HELM_DATA_DIR`;
2. `$XDG_DATA_HOME/helm`;
3. `~/.local/share/helm`.

The repository `config/` directory contains examples and migration sources only:

```text
config/settings.example.json
config/modes.example.json
config/mode_state.example.json
config/projects.example.json
```

Live files are `settings.json`, `modes.json`, `mode_state.json` and
`projects.json` under the runtime root. See [RUNTIME_DATA.md](RUNTIME_DATA.md)
for fallback and recovery behavior.

## `settings.json`

```json
{
  "telemetry_interval": 0.5,
  "start_screen": "system",
  "navigation_logging": true,
  "log_rows": 200,
  "ai_model": "qwen3:8b",
  "ai_context_window": 8192,
  "ai_keep_alive": "10m"
}
```

Allowed telemetry intervals: `0.5`, `1`, `2`, `5`, `10`.

Allowed screens: `system`, `network`, `storage`, `devices`, `modes`,
`projects`, `logs`, `ai`, `settings`.

Allowed log rows: `50`, `100`, `200`, `500`, `1000`.

Allowed AI contexts: `2048`, `4096`, `8192`, `16384`.

Allowed keep-alive values: `0`, `5m`, `10m`, `30m`, `1h`.

SETTINGS backups are placed in `DATA_ROOT/backups/` and pruned to the newest ten.
Profile exports are placed in `DATA_ROOT/exports/`.

## `modes.json`

Each workspace defines an ID/name, telemetry interval, target screen, navigation
logging, workload and power profiles, objective, features and applications.

Native application example:

```json
{
  "name": "Code editor",
  "kind": "application",
  "enabled": true,
  "alternatives": [
    ["code", "{project_root}"],
    ["codium", "{project_root}"],
    ["kate", "{project_root}"]
  ],
  "process_names": ["code", "codium", "kate"],
  "skip_if_running": true,
  "working_directory": "{project_root}"
}
```

Browser application example:

```json
{
  "name": "Documentation",
  "kind": "browser",
  "enabled": true,
  "urls": ["https://textual.textualize.io/"]
}
```

Placeholders: `{project_root}` and `{home}`.

Power profiles: `balanced`, `performance`, `power-saver`, `unchanged`.

## `mode_state.json`

```json
{
  "active_mode": "command"
}
```

This small file stores the active workspace independently of the workspace
definitions. A missing file is created from the example/default path.

## `projects.json`

Fields: `id`, `name`, `category`, `status`, `priority`, `progress`, `tech`,
`next_action`, `description`, `path`, `github_url`, `updated_at`.

Status progression:

```text
CONCEPT → PLANNING → ACTIVE → BUILDING → TESTING → BLOCKED
→ PAUSED → STABLE → DONE
```

`STABLE`, `DONE` and legacy `COMPLETED` records appear in the completed table.
GitHub URLs must use HTTPS and a GitHub host. `{project_root}` is supported as a
portable path value.

## Desktop Node storage

The example is `desktop/config/desktop-node-storage.example.json`. The installed
user configuration is normally:

```text
~/.config/helm/desktop-node-storage.json
```

`max_volumes` limits visible rows. Each enabled volume defines a label, mount path
and optional stable device path such as `/dev/disk/by-uuid/...`.

## Other runtime paths

- `logs/helm.log` — rotating application log, ignored by Git;
- `logs/exports/` — log, AI and health exports;
- `~/.local/state/helm/` — launcher/autostart state;
- `~/.config/helm/` — Desktop Node and desktop integration configuration.
