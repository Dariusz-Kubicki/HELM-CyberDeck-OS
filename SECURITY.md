# Security Policy

## Supported version

Security fixes are currently applied to the latest `1.x` release.

## Reporting a vulnerability

Do not publish credentials, private logs or machine-specific data in a public issue. Open a minimal report and request a private channel when sensitive details are required.

## Trust boundaries

### Local AI

The Ollama model receives a textual, read-only snapshot. The system prompt forbids claims that it executed commands, changed files, controlled hardware or accessed the internet. AI output is advisory and must not be treated as proof of a hardware fault.

### System actions

Buttons do not pass arbitrary model output to a shell. Approved actions are mapped to fixed commands in dedicated services. Device names, file paths and GitHub URLs are validated before use.

### Privileges

HELM runs as a normal user. SMART data may be unavailable without elevated access. The optional `/usr/local/lib/helm/helm-smart-status` helper is not installed because privilege policy must be reviewed by the machine owner.

### Logs and exports

Runtime logs can contain hostnames, usernames, process names, device names, paths and project information. They are excluded by `.gitignore`; still inspect them before sharing.

### Configuration

Mutable JSON is written through temporary files, flushed and atomically replaced. Backups and exports are stored in ignored runtime directories.

## Public-release checklist

```bash
./scripts/check-release.sh
```

Manually inspect `config/projects.json`, `config/modes.json`, screenshots, logs, backups, exported AI sessions and health reports.
