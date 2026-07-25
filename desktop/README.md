# Desktop snapshot

This directory contains the reproducible HELM CyberDeck Desktop layer.

- `apps/` — application-specific customization.
- `autostart/` — session startup entries.
- `boot/` — sanitized systemd-boot and mkinitcpio templates.
- `conky/` — Desktop Node configuration.
- `launchers/` — HELM command-line entry points.
- `manifests/` — package and active-state snapshot.
- `plasma/` — Plasma style, colors, layout and lock-screen overlay.
- `plymouth/` — HELM Early Boot.
- `sddm/` — HELM Access Gate without copyrighted wallpaper.
- `shell/` — aliases and prompt-related configuration.

Install with:

```bash
helm install-desktop --wallpaper /absolute/path/wallpaper.png
```
