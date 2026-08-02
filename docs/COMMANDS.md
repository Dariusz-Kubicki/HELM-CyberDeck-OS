# HELM CyberDeck command cheat sheet

## HELM Core

```bash
helm
helm start
helm stop
helm restart
helm status
helm logs
helm version
```

## Desktop Node

```bash
helm hud
helm hud-stop
helm hud-restart
helm hud-logs
```

## Maintenance and recovery

```bash
helm doctor
helm backup
helm restore ~/.cyberdeck/backups/helm-cyberdeck-YYYYMMDD-HHMMSS.tar.gz
helm restore ~/.cyberdeck/backups/helm-cyberdeck-YYYYMMDD-HHMMSS.tar.gz --apply
helm rebuild-lock
helm install-desktop --wallpaper /absolute/path/wallpaper.png
helm commands
```

## Everyday aliases

```bash
sys       # fastfetch
mon       # btop
gpu       # nvidia-smi
temp      # sensors
vault     # HELM Data Vault
```

## Session and desktop

```bash
loginctl lock-session
kcmshell6 kcm_screenlocker
kbuildsycoca6 --noincremental
helm status
```

## Boot and Plymouth

```bash
sudo systemctl reboot --boot-loader-menu=5
sudo mkinitcpio -P
plymouth-set-default-theme
sudo plymouth-set-default-theme helm-cyberdeck
bootctl status --no-pager
cat /proc/cmdline
```

The normal `Arch Linux` entry uses the silent HELM Plymouth path.<br>
`Arch Linux (diagnostic)` disables Plymouth and restores detailed messages.

## Logs

```bash
journalctl -b --no-pager
journalctl --user -b --no-pager
journalctl -b -1 --no-pager
helm logs
helm hud-logs
```

## Git release workflow

```bash
scripts/check-release.sh
helm doctor
printf '1.2.0\n' > VERSION
git add -A
git commit -m "Prepare HELM CyberDeck OS v1.2.0 release"
git push origin feature/helm-v1.2.0

git switch master
git pull --ff-only origin master
git merge --no-ff feature/helm-v1.2.0 -m "Merge HELM CyberDeck OS v1.2.0"
git tag -a v1.2.0 -m "HELM CyberDeck OS v1.2.0"
git push origin master
git push origin v1.2.0
```

Use [PUBLISHING.md](PUBLISHING.md) as the authoritative checklist. Do not force
push release branches or move existing tags.
