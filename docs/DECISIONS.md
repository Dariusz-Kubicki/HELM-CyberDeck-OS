# Technical Decisions and Known Limitations

This document records the decisions that should not be casually reversed during
future maintenance.

## Decisions

### D-001 — HELM is an application layer, not a distribution

HELM runs on top of Arch Linux and KDE Plasma. It does not own package management,
the kernel or the desktop session. Desktop integration is installed as explicit
user/system configuration with recovery paths.

### D-002 — Textual TUI is the primary control surface

The TUI keeps the project inspectable, keyboard-driven and usable over a normal
terminal. The intended layout is optimized for the target workstation rather
than every possible terminal size.

### D-003 — Telemetry is asynchronous and single-flight

Only one telemetry collection runs at a time. Overlapping timer ticks are counted
and skipped; late sequence results are ignored. This protects responsiveness and
prevents stale data from replacing newer state.

### D-004 — Collectors observe; action services mutate

`modules/` should not make user-visible system changes. Side effects live in
allow-listed services with fixed commands or validated paths/URLs. This is the
main security boundary around shell and desktop integration.

### D-005 — AI is advisory and local

The Ollama model receives a bounded read-only snapshot and explicit uncertainty
instructions. It cannot directly invoke HELM actions or claim that it changed the
machine.

### D-006 — Mutable state follows XDG data conventions

Live JSON is outside the repository. `HELM_DATA_DIR` supports isolated/test or
custom deployments; otherwise HELM uses `$XDG_DATA_HOME/helm` or
`~/.local/share/helm`.

### D-007 — Transparent JSON instead of a database

Settings, workspaces and projects remain human-readable and easy to back up. The
trade-off is limited concurrency and no multi-file transaction support.

### D-008 — Recovery favors last-known-good data

Invalid active JSON is preserved in quarantine, then recovered from last-good,
legacy, example or code defaults. Migration is non-destructive.

### D-009 — Missing optional telemetry is not failure evidence

`N/A`, `UNAVAILABLE`, `RESTRICTED` or absent SMART/GPU/AI data means the source is
not available. It does not by itself mean the hardware is broken.

### D-010 — Stable desktop components beat visual experiments

The release keeps the working Graphite-dark KWin decoration. The unstable custom
Aurorae decoration and KSplash experiment remain excluded. Plasma updates are
handled through `helm rebuild-lock` and `helm doctor` rather than hidden patches.

## Known limitations

- Primary testing is on one Arch Linux + KDE Plasma + Wayland workstation.
- GPU telemetry is NVIDIA-oriented because it uses `nvidia-smi`.
- SMART details may require privileges and can remain restricted.
- Local AI requires a separately installed Ollama service and model.
- The interface is tuned around 122 × 57 terminal cells; smaller windows may wrap
  or scroll.
- Runtime JSON assumes one active HELM writer and has no cross-process lock.
- Recovery stores one last-good snapshot, not a history of every edit.
- Quarantined broken JSON is not automatically pruned.
- Core Python tests focus on runtime persistence; automated Textual visual/snapshot
  tests do not yet exist.
- The desktop snapshot manifest records package versions from the v1.1 capture;
  later Plasma changes are detected as drift rather than automatically adapted.
- Full desktop backup uses `sudo` for system assets, is not encrypted and should be
  stored privately.
- Desktop recovery can restore configuration, but it cannot guarantee compatibility
  with a substantially different future KDE/SDDM/Plymouth version.
- No stable third-party plugin API exists; new collectors currently require source
  changes.

## Release posture

A limitation is release-blocking only when it contradicts a documented guarantee,
risks user data, prevents normal startup on the supported target or bypasses the
side-effect/AI safety boundary. Other limitations should be documented and tracked
for a later release instead of triggering broad late-stage refactors.
