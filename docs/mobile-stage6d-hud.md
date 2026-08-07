# HELM Mobile Stage 6D — Top-right telemetry HUD

Stage 6D brings the Desktop Node Conky HUD concept to the ThinkPad Mobile Node without copying desktop-only telemetry assumptions.

The Mobile HUD keeps the same HELM visual language and top-right 310 px geometry, while adapting the content to laptop operation: CPU, memory, AMD GPU, battery percentage and health, AC/BAT source, current power profile, estimated battery time, network throughput and address, root storage, uptime, kernel and HELM process state.

The runtime window uses Conky as a normal undecorated sticky XWayland window with taskbar and pager suppression. It does not alter the Plasma panel, KWin configuration, power policy, suspend policy, login, lock screen, boot chain or PAM.

Source assets live under `mobile/conky/` and `mobile/autostart/`. The live installer is `scripts/mobile/apply-stage6d-mobile-hud.sh`; recovery is `scripts/mobile/restore-stage6d-mobile-hud.sh`.

The live top-right HUD was visually approved on the ThinkPad display. During validation, the X11 `below` hint was removed because KWin/Plasma Wayland could place the XWayland Conky window beneath the Plasma desktop surface. The approved policy keeps a normal undecorated sticky window while suppressing taskbar and pager entries.
