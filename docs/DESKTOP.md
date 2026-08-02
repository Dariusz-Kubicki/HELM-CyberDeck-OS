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
- **Desktop Node** — lightweight Conky HUD with configurable storage volumes.
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


## Desktop Node storage configuration

The tracked example is `desktop/config/desktop-node-storage.example.json`; the
installed user file is `~/.config/helm/desktop-node-storage.json`. It controls the
maximum number of storage rows and their labels, mount paths and stable device
identifiers.

## Backup boundary

`helm backup` captures desktop/user/system integration, a Git repository bundle
and, in v1.2, the active HELM runtime data root. Application logs are still
separate runtime artifacts and should be exported intentionally when needed.
