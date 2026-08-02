# Development and Handoff Guide

This guide is the operating procedure for continuing HELM after the v1.2
functional freeze. It is written for both human maintainers and AI-assisted work
sessions.

## Supported development baseline

- Primary platform: Arch Linux, KDE Plasma, Wayland.
- Python: 3.11 or newer; CI uses Python 3.12.
- Pinned packages: Textual 8.2.8, psutil 7.2.2, pyserial 3.5.
- Intended terminal geometry: approximately 122 columns × 57 rows.
- v1.2 functional freeze commit: `1d4b9ce`.

## Local setup

```bash
git clone https://github.com/Dariusz-Kubicki/HELM-CyberDeck-OS.git
cd HELM-CyberDeck-OS
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
./scripts/run-helm.sh
```

To isolate test data from personal runtime files:

```bash
export HELM_DATA_DIR="$(mktemp -d)"
./scripts/run-helm.sh
```

Do not point tests or experiments at the normal data root unless the task is
specifically testing migration or recovery on a reviewed backup.

## Mandatory checks

Run before every technical or release commit:

```bash
scripts/check-release.sh
git diff --check
git status --short --branch
```

For desktop-integration changes, also run on the target workstation:

```bash
helm doctor
```

Current runtime tests cover 12 cases across storage, settings, modes, active mode,
projects and ProjectMonitor recovery.

## Architectural rules

1. Keep blocking subprocess, filesystem and network work out of the Textual UI
   thread.
2. Keep collectors read-only and tolerant of missing optional tools.
3. Put side effects in dedicated allow-listed services.
4. Never route local AI output into command execution.
5. Preserve the previous valid telemetry snapshot when a recoverable collector
   fails.
6. Store mutable user state through `RuntimeJsonStore`, not inside Git.
7. Validate complete JSON payloads before writing them.
8. Log state transitions and actionable failures without leaking secrets.
9. Preserve graceful operation on machines without Ollama, NVIDIA or SMART access.
10. Add a doctor/recovery path for every new desktop component.

## Common change workflows

### Add telemetry

1. Add a sample dataclass and collector in `modules/`.
2. Integrate it into `DataService.collect_result()`.
3. Define required/optional behavior and previous-snapshot fallback.
4. Extend `SystemSnapshot` only when multiple consumers need the value.
5. Update the relevant screen and deterministic/AI context.
6. Add health checks and tests where failure semantics matter.
7. Update `FEATURES.md`, `ARCHITECTURE.md` and this codebase map.

### Add runtime JSON

1. Add `config/NAME.example.json` with a JSON object root.
2. Create an owning service and validator.
3. Use `RuntimeJsonStore` with runtime, legacy and example paths.
4. Define a safe default factory.
5. Add migration, corruption, last-good and write tests.
6. Add runtime checks to `helm doctor`.
7. Document ownership, backup and recovery.

### Add a system action

1. Define a stable action ID.
2. Map it to fixed arguments or strictly validated targets in an action service.
3. Use `shutil.which` and return an actionable unavailable state.
4. Run it outside the UI thread when it can block.
5. Add confirmation for destructive behavior.
6. Log the request and result, never raw secrets.

### Change desktop integration

1. Update the source snapshot under `desktop/`.
2. Update `scripts/desktop/install.sh`.
3. Add or update doctor checks.
4. Include the component in backup and restore.
5. Add recovery instructions.
6. Test a normal login, lock/unlock and diagnostic boot path.

## Review checklist

- Does failure degrade gracefully?
- Can user data be lost or overwritten?
- Does migration preserve the source file?
- Is the operation safe when an optional command is absent?
- Is any new path portable or explicitly host-specific?
- Is the side effect reachable from AI output?
- Are user-visible errors actionable?
- Are tests independent of the user's real data directory?
- Are README, architecture, recovery and release notes consistent?

## AI-assisted session handoff

Start a new AI session with concrete state instead of a broad description. A
minimal handoff should contain:

```text
Repository: ~/.cyberdeck/nexus
Branch: feature/helm-v1.2.0
Base/freeze commit: 1d4b9ce
Current HEAD: <commit>
Version file: <contents of VERSION>
Working tree: <git status --short --branch>
Last validation: <release check and doctor summary>
Task: <one bounded objective>
Constraints: preserve runtime data, no arbitrary AI execution, no unrelated refactor
Relevant files: <paths>
```

Attach a `git archive` snapshot when the assistant needs to inspect the complete
codebase. Never attach the live runtime data root unless its personal contents
have been reviewed and intentionally shared.

## Release branch workflow

1. Freeze functionality at a named commit.
2. Complete documentation and controlled screenshots.
3. Run release checks and `helm doctor`.
4. Change `VERSION` from `X.Y.Z-dev` to `X.Y.Z` only at final release prep.
5. Update `CHANGELOG.md` and release notes with the release date.
6. Commit release metadata.
7. Merge the feature/release branch into `master` with `--no-ff`.
8. Create an annotated tag on the merge commit.
9. Push `master` and the tag without force.
10. Create the GitHub release from the matching release-notes file.

The detailed v1.2 command sequence is in [PUBLISHING.md](PUBLISHING.md).
