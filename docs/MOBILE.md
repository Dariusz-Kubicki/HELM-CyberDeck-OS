# CyberDeck Mobile Node

CyberDeck Mobile is the field-oriented system profile for the ThinkPad T14.
It is part of the same HELM ecosystem as the Desktop Node, but it is not a
pixel-for-pixel copy. The mobile profile prioritizes battery awareness, compact
layouts, suspend reliability, wireless state and fast recovery.

## Target platform

The initial reference device is:

```text
ThinkPad T14 Gen 2a
AMD Ryzen 5 PRO 5650U
Radeon Vega / amdgpu
1920x1080 internal panel at scale 1
Arch Linux, KDE Plasma and Wayland
LUKS-backed Btrfs root with @ and @home subvolumes
```

The tracked manifest is `mobile/config/mobile-node.example.json`. It describes
expected capabilities and contains no credentials or mutable user data.

## Repository boundary

```text
mobile/
├── config/       tracked example configuration
├── manifests/    package and platform state
├── plasma/       future Mobile Plasma assets
├── apps/         future Konsole, Dolphin and Firefox assets
├── sddm/         future Mobile Access Gate
├── plymouth/     future Mobile Early Boot
└── boot/         future systemd-boot templates

scripts/mobile/
├── doctor.sh     read-only installed-state diagnostic
├── install.sh    future controlled installer
├── backup.sh     future Mobile Node backup
└── restore.sh    future Mobile Node recovery
```

Desktop assets remain under `desktop/` and `scripts/desktop/`. Mobile work must
not silently overwrite the Desktop Node snapshots. Shared HELM application code
stays in `app/`, `modules/` and `services/`.

## Delivery stages

1. **Baseline and rollback** — package inventory, configuration archives and
   read-only Btrfs snapshots.
2. **Foundation** — required packages, Python environment, power profiles,
   Mobile Node manifest and diagnostic.
3. **Plasma field shell** — compact panel, color system, window rules, desktop
   layout and battery/network HUD.
4. **Core applications** — Konsole, Dolphin Data Vault Mobile and Firefox chrome.
5. **Access surfaces** — Security Lock Mobile, SDDM Access Gate Mobile and
   Plymouth Early Boot Mobile.
6. **HELM Mobile** — battery, charging, radio, thermals, suspend and field modes.
7. **Node link** — private Desktop-to-Mobile status and data synchronization.
8. **Hardening and release** — backup/restore, diagnostics, tests, screenshots,
   documentation and v1.3.0 release.

## Power policy

The foundation uses `power-profiles-daemon` because it integrates with KDE
PowerDevil. TLP, tuned, auto-cpufreq and other competing managers are considered
conflicts unless a later architecture decision explicitly replaces the provider.

Future HELM modes will map intent to supported platform profiles rather than
writing arbitrary CPU governor or firmware values.

## Safety rules

- Create a backup before any installer changes Plasma, SDDM, Plymouth or boot
  entries.
- Keep the stable tag `v1.2.0` unchanged.
- Develop only on `feature/cyberdeck-mobile-v1.3.0` until release preparation.
- Treat `mobile/config/*.example.json` as templates. Mutable device state must
  live outside Git.
- Do not activate SDDM or Plymouth until their recovery path and diagnostic are
  present.
- Validate every stage with `scripts/check-release.sh`,
  `scripts/mobile/doctor.sh` and `git diff --check`.

## Stage 1 diagnostic

Run:

```bash
scripts/mobile/doctor.sh
```

At this stage, SDDM and Plymouth are expected to be installed but inactive. The
diagnostic will warn if either was activated before the controlled visual and
recovery stages.

## Stage 2A — Plasma Field Shell foundation

CyberDeck Mobile adopts a new wallpaper direction for the ThinkPad:
a minimalist netrunner / field-terminal aesthetic rather than a franchise-style
character illustration. The visual layer for this stage establishes:

- dark graphite / near-black background,
- restrained cyan HUD accents,
- subtle technical lines and scan detail,
- a lightweight mobile cyberdeck identity,
- safe live application through `scripts/mobile/apply-stage2a-visual-foundation.sh`.

This stage intentionally does not reconfigure SDDM, Plymouth or a hard-coded
Plasma panel layout yet.

## Stage 2B — Plasma Field Shell

The approved ThinkPad shell uses the versioned target in
`mobile/plasma/field-shell.json`:

- bottom panel with a 40 px height,
- centered custom width constrained to 1200 px,
- floating and translucent presentation,
- dodge-windows visibility behavior,
- BreezeDark with the global Breeze icon theme,
- minimalist field-node wallpaper v2.

The shell intentionally keeps the standard Breeze icon theme so symbolic and
system icons remain readable. Dedicated HELM launcher icons are a separate
integration step and do not replace the global icon theme.

Apply the shell with:

    scripts/mobile/apply-stage2-field-shell.sh

Restore the configuration captured by the latest application with:

    scripts/mobile/restore-stage2-field-shell.sh

The restore path uses the Plasma user systemd service and does not call
`kquitapp6`.

## Firefox Mobile chrome

CyberDeck Mobile carries a compact Firefox 153 interface derived from the
Desktop Node HELM browser theme. The mobile variant preserves the dark terminal
palette and restrained cyan accents while reducing tab and navigation chrome
for the ThinkPad display.

The installer discovers the active Firefox profile under the XDG configuration
root, enables legacy profile stylesheets, creates a recovery copy and installs
`mobile/apps/firefox/userChrome.css`. It does not modify Plasma, the wallpaper
or the global icon theme.

Apply the preview only while Firefox is completely closed:

    scripts/mobile/apply-firefox-preview.sh

Restore the previous profile styling with:

    scripts/mobile/restore-firefox-preview.sh
