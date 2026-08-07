# HELM Mobile login architecture

HELM CyberDeck Mobile uses two independent authentication interfaces. They intentionally serve different lifecycle points and do not replace one another.

## Stage 4B — Security Lock

Provider: Plasma KScreenLocker.

The Security Lock protects an existing Plasma session. It appears after automatic idle locking, manual session locking, and resume from sleep when locking is required. The Stage 4B overlay changes presentation only. Native Plasma session unlocking and password verification remain unchanged.

## Stage 4C — Access Gate

Provider: SDDM with the `helm-mobile` Qt 6 theme.

The Access Gate creates a new graphical session. It appears after boot, a real logout, and user switching. The theme uses native SDDM objects for authentication, user selection, session selection, and supported power actions. It does not modify PAM, password handling, or session launching.

## Separation of responsibilities

Automatic inactivity does not perform a logout. It locks the current session, so the Security Lock is expected. A real logout ends the Plasma session. SDDM then displays the Access Gate and starts a new session after successful authentication.

```text
Boot or logout
    -> SDDM Access Gate
    -> Plasma Wayland session
    -> idle, manual lock or resume
    -> KScreenLocker Security Lock
```

## Safety contract

Stage 4C must not use `LD_PRELOAD`, binary interposition, Plasma Login Manager QML injection, PAM replacement, password interception, or direct display-manager restart inside an active graphical session.

Installation switches the display manager for the next boot. Recovery can restore Plasma Login Manager from a TTY without modifying Stage 4B.

## Controlled tools

Apply:

```bash
scripts/mobile/apply-stage4c-sddm-access-gate.sh
```

Restore at the next boot:

```bash
scripts/mobile/restore-stage4c-sddm-access-gate.sh
```

Emergency restore from a TTY:

```bash
scripts/mobile/restore-stage4c-sddm-access-gate.sh --now
```
