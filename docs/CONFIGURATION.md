# Configuration Reference

Configuration lives in `config/`. Stop HELM before manual editing.

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

Allowed intervals: `0.5`, `1`, `2`, `5`, `10`. Screens: `system`, `network`, `storage`, `devices`, `modes`, `projects`, `logs`, `ai`, `settings`. Log rows: `50`, `100`, `200`, `500`, `1000`. Context: `2048`, `4096`, `8192`, `16384`. Keep-alive: `0`, `5m`, `10m`, `30m`, `1h`.

## `modes.json`

Each workspace defines an ID/name, telemetry interval, target screen, navigation logging, workload and power profiles, objective, features and applications.

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

Placeholders: `{project_root}` and `{home}`. Power profiles: `balanced`, `performance`, `power-saver`, `unchanged`.

## `projects.json`

Fields: `id`, `name`, `category`, `status`, `priority`, `progress`, `tech`, `next_action`, `description`, `path`, `github_url`, `updated_at`.

Status order:

```text
CONCEPT → PLANNING → ACTIVE → BUILDING → TESTING → BLOCKED
→ PAUSED → STABLE → DONE
```

`STABLE` and `DONE` appear in the completed table. GitHub URLs must use HTTPS and the GitHub host. `{project_root}` is a portable path value.

## Runtime files

- `mode_state.json` — generated active mode; defaults to `command` when absent.
- `config/backups/` — settings backups.
- `config/exports/` — settings profiles.
- `logs/exports/` — log, AI and health exports.

These paths are ignored by Git. Example files are included as `*.example.json`.
