# Third-party components and attribution

HELM CyberDeck OS contains original code and configuration, plus modified visual
components derived from upstream projects.

## SDDM Access Gate

The Access Gate is derived from the Graphite SDDM theme by Vince Liuice. The
upstream metadata declares CC-BY-SA. Original metadata is retained in the theme
directory.

## Plymouth Early Boot

The HELM Plymouth theme is derived from KDE Breeze Plymouth. The original script
header and SPDX notices are retained. The Breeze script declares
`GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL`.

## Plasma style

`HELM-Plasma` was created from an installed Plasma theme and then customized.
The snapshot retains its original metadata. Review the upstream license field
and preserve all attribution before redistributing the complete theme.

## External assets not included

The Night City wallpaper and user avatar are intentionally excluded from Git.
The installer requires a local wallpaper path and injects it into SDDM and the
lock screen. Papirus icons and Graphite-dark window decorations are referenced
as installed dependencies and are not vendored.
