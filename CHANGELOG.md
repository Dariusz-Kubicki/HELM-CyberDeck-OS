# Changelog

All notable changes to HELM CyberDeck OS are documented here.

## [Unreleased]

### Added

- CyberDeck Mobile Stage 2A visual foundation with a minimalist field-node wallpaper
  and a safe Plasma appearance application script.
- HELM Mobile Firefox 153 chrome theme with compact cyberdeck styling, XDG profile detection and reversible installation.
- CyberDeck Mobile Plasma Field Shell with the approved compact floating panel, translucent presentation, dodge-windows behavior and wallpaper v2.


### Added

- Initial CyberDeck Mobile Node foundation for the ThinkPad field system.
- Mobile hardware, power and package manifest.
- Read-only Mobile Node diagnostic covering the Stage 1 foundation.
- Dedicated mobile architecture and staged implementation documentation.

### Changed

- Development version advanced to `1.3.0-dev`.

## [1.2.0] - 2026-08-02

### Added

- XDG-compatible runtime data root with `HELM_DATA_DIR` override.
- Last-known-good snapshots and corrupt-file quarantine for runtime JSON.
- Non-destructive migration from legacy repository configuration.
- Runtime persistence and recovery unit tests.
- Runtime storage and recovery checks in `helm doctor`.
- Configurable Desktop Node storage volumes.
- Codebase, runtime, development, decision and screenshot documentation.

### Changed

- Settings, modes, active mode and projects now write outside the Git working tree.
- ProjectMonitor reads from the resilient runtime project database.
- HELM control geometry and signature rail were refined.
- Release checks now compile tests, run unit tests and validate example JSON.
- Full CyberDeck backup includes the runtime data root.

### Removed

- Stale tracked local workspace backup artifacts from the public source tree.

## [1.1.0] - 2026-07-25

### Added

- Complete HELM CyberDeck Desktop integration.
- Access Gate, Security Lock and animated Early Boot.
- Desktop snapshot, installer, doctor, backup and recovery tools.
- Command cheat sheet and desktop recovery documentation.

## [1.0.0] - 2026-07-24

### Added

- Cyberpunk boot sequence, sidebar, signature rail and dynamic health accents.
- Threaded, fault-tolerant Telemetry Engine v2.
- Core Health Service with startup reporting and Markdown export.
- SYSTEM, NETWORK, STORAGE and DEVICES control centers.
- PROJECTS Mission Control and MODES Workspace Engine.
- LOGS control center and hybrid local AI core.
- SETTINGS backups, restore and profile export.
- Global Ctrl+K command palette integration.

### Safety

- Read-only AI telemetry context and explicit execution boundaries.
- Uncertainty safeguards for missing and unavailable measurements.
- Allow-listed action services and validated external targets.
- Atomic writes and destructive-action confirmations.
