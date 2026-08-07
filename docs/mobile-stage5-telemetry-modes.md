# HELM Mobile Stage 5 — Telemetry and Modes

Stage 5 turns the Mobile Node from a styled HELM environment into a laptop-aware operational node.

## Audit conclusion

The existing code already contains a mature workspace engine. `ModeService` persists the active mode, validates telemetry intervals, target screens, navigation logging and power-profile policy. `app/main.py` already applies a selected mode to HELM settings, restarts the telemetry timer, optionally applies a power profile and launches configured workspace applications.

Stage 5 therefore extends the existing architecture instead of introducing a second mode system.

## Stage 5A — Mobile telemetry foundation

Stage 5A adds a read-only `PowerMonitor` to the shared telemetry engine. The sample includes:

- battery presence and percentage;
- charge/discharge state;
- current battery energy;
- current full-charge energy;
- design energy;
- calculated battery health;
- instantaneous battery power;
- estimated charge/discharge time when the kernel exposes enough data;
- external-power state when available;
- current `powerprofilesctl` profile.

The monitor prefers Linux power-supply sysfs and only queries `powerprofilesctl get`. It does not change the selected profile.

`DataService` treats power telemetry as fault-tolerant. A power-reading failure degrades that telemetry cycle and falls back to the previous `PowerSample` (or an explicit unavailable sample); it must not make storage, device, project or resource telemetry disappear.

## Stage 5B — Mobile mode policy

Stage 5B adds a Mobile-specific adaptive power policy without creating a second workspace database. The existing `ModeService` still owns mode identity, telemetry interval, target screen, navigation logging and the explicit per-mode `power_profile`.

When a mode keeps `power_profile` at `unchanged`, the Mobile policy resolves the platform profile from the current power source:

| Mode | Battery | AC |
| --- | --- | --- |
| `CHILL` | `power-saver` | `balanced` |
| `FOCUS` | `power-saver` | `balanced` |
| `MAKER` | `balanced` | `balanced` |
| `DEVELOPMENT` | `balanced` | `performance` |
| `COMMAND` | `balanced` | `balanced` |

An explicit mode `power_profile` other than `unchanged` takes precedence. This preserves the existing MODES editor semantics and lets custom workspaces opt out of the Mobile defaults.

The safety fallbacks are deliberately conservative:

- unknown AC/battery state resolves to `balanced`;
- an unavailable requested profile resolves to `balanced`;
- a failed profile change is reported but does not abort workspace activation;
- custom modes not present in the Mobile policy retain the legacy `power_profile` behavior.

The policy resolver samples Stage 5A power telemetry only when resolving a mode. It does not create another collector loop. Applying the resolved profile remains part of explicit workspace activation or restoring the already-active workspace when HELM starts.

## Stage 5C — Telemetry surfaces

Stage 5C exposes Stage 5A laptop power data directly on the `SYSTEM` screen through a dedicated `MobilePowerPanel`. The existing four-card CPU/GPU/RAM/STORAGE dashboard remains unchanged.

The surface reports:

- battery percentage and charge/discharge state;
- estimated remaining time;
- instantaneous battery draw;
- current and full-charge energy;
- calculated battery health;
- AC/battery source;
- the currently active platform power profile;
- active HELM mode and its configured adaptive policy target.

The panel consumes the existing `SystemSnapshot.power` sample. It does not create another collector loop and does not invoke a profile change.

Mode policy context is resolved through a pure source-mapping helper in `MobilePowerPolicyService`. That helper uses the already-collected AC/battery state and the active mode's existing `power_profile`; it performs no system sampling and no `powerprofilesctl` operation.

Stage 5C therefore remains a presentation layer over Stage 5A telemetry and Stage 5B policy rather than becoming another power-management subsystem.

## Safety contract

Stage 5 telemetry collection must remain read-only. Sampling must never:

- change the active power profile;
- activate a workspace;
- launch applications;
- write runtime JSON;
- modify system services;
- modify boot, login or lock-screen configuration.

Mode activation remains a separate, explicit action handled by the existing workspace engine.
