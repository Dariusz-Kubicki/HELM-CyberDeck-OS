# HELM CyberDeck Recovery

## Runtime JSON recovery

HELM v1.2 automatically quarantines invalid active JSON and restores the newest
valid source in this order: last-good snapshot, legacy repository file, example,
code default.

Default paths:

```text
~/.local/share/helm/*.json
~/.local/share/helm/recovery/*.last-good.json
~/.local/share/helm/recovery/*.broken.json
```

Inspect the active data root:

```bash
DATA_ROOT="${HELM_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/helm}"
find "$DATA_ROOT" -maxdepth 2 -type f -printf '%p\n' | sort
```

Validate all active JSON:

```bash
DATA_ROOT="${HELM_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/helm}"
for file in settings modes mode_state projects; do
    python -m json.tool "$DATA_ROOT/$file.json" >/dev/null
done
```

Run the integrated audit:

```bash
helm doctor
```

### Restore one last-good file manually

Stop HELM first:

```bash
helm stop
DATA_ROOT="${HELM_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/helm}"
cp -a "$DATA_ROOT/recovery/projects.last-good.json" \
      "$DATA_ROOT/projects.json"
helm start
helm doctor
```

The same pattern applies to settings, modes and mode_state. Keep any
`*.broken.json` file until reviewed.

## Diagnostic boot

Show the boot menu once:

```bash
sudo systemctl reboot --boot-loader-menu=5
```

Select **Arch Linux (diagnostic)**. It disables Plymouth and displays detailed
kernel and systemd messages.

## Restore Plymouth to Breeze

```bash
sudo plymouth-set-default-theme breeze
sudo mkinitcpio -P
```

To disable the HELM Plymouth hook completely:

```bash
sudo rm -f /etc/mkinitcpio.conf.d/90-helm-plymouth.conf
sudo mkinitcpio -P
```

## Restore SDDM to Graphite

From a normal session or TTY:

```bash
sudo rm -f /etc/sddm.conf.d/zz-helm-theme.conf
sudo systemctl restart sddm
```

The older `kde_settings.conf` continues to select Graphite.

## Remove the lock-screen override

```bash
rm -rf ~/.local/share/plasma/shells/org.kde.plasma.desktop
kbuildsycoca6 --noincremental
```

Plasma then uses `/usr/share/plasma/shells/org.kde.plasma.desktop`.

Rebuild HELM Security Lock:

```bash
helm rebuild-lock
```

## Restore a full recovery archive

Preview:

```bash
helm restore /path/to/helm-cyberdeck-YYYYMMDD-HHMMSS.tar.gz
```

Apply:

```bash
helm restore /path/to/helm-cyberdeck-YYYYMMDD-HHMMSS.tar.gz --apply
```

The v1.2 archive includes runtime data, launchers, desktop configuration,
SDDM/Plymouth/boot assets and a Git repository bundle. The restore creates a small
pre-restore safety copy before changing the workstation.

After restore:

```bash
helm doctor
```

Review the result before rebooting.

## TTY access

Use `Ctrl+Alt+F3`, sign in, and perform recovery commands there when the graphical
session cannot start.
