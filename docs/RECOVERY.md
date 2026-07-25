# HELM CyberDeck recovery

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

## TTY access

Use `Ctrl+Alt+F3`, sign in, and perform recovery commands there when the
graphical session cannot start.
