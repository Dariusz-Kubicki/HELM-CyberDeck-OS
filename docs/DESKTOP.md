# HELM CyberDeck Desktop

HELM CyberDeck Desktop extends the Textual control center into a complete Arch
Linux and KDE Plasma workstation.

## Runtime chain

```text
UEFI
  → systemd-boot (hidden during normal startup)
  → HELM Plymouth Early Boot
  → HELM Access Gate (SDDM)
  → KDE Plasma / Wayland
  → HELM Core + Desktop Node
  → HELM Security Lock
```

## Components

- **HELM Core** — Textual control center and telemetry engine.
- **Desktop Node** — lightweight Conky HUD.
- **HELM-Plasma** — dark cyan Plasma style.
- **HELMCyberdeck** — KDE color scheme.
- **HELM Access Gate** — SDDM authentication theme.
- **HELM Security Lock** — Plasma lock-screen overlay.
- **HELM Early Boot** — Plymouth theme with spinner and progress bar.
- **HELM Data Vault** — Dolphin layout and launcher.
- **HELM Browser** — Firefox `userChrome.css`.
- **HELM Embedded Lab** — Arduino IDE visual configuration.

## Stability boundary

The working KWin decoration remains `Graphite-dark`. The disabled experimental
`HELM-Graphite` Aurorae decoration is not part of the release because it caused
KWin instability.

The custom KSplash experiment is also excluded from the active release. The
stable post-login transition remains the standard Plasma splash path.

## Update maintenance

A Plasma update can replace the system lock-screen implementation. Run:

```bash
helm rebuild-lock
helm doctor
```

A Plymouth or kernel update normally rebuilds initramfs through package hooks.
When in doubt:

```bash
sudo mkinitcpio -P
helm doctor
```
