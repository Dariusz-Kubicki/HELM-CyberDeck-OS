# HELM Mobile Stage 6 — Power and Suspend

Stage 6 makes laptop sleep behavior explicit and recoverable without replacing KDE PowerDevil or the systemd sleep stack.

## Audit conclusion

The Stage 6 read-only audit established the following reference state on the ThinkPad Mobile Node:

- KDE PowerDevil owns desktop lid/power handling through a systemd-logind inhibitor;
- a real lid-close event already caused PowerDevil to request `suspend`;
- the kernel exposes `freeze`, `mem` and `disk`, but the active memory-sleep backend is `s2idle` only;
- successful `s2idle` suspend/resume cycles are present in the current-boot journal;
- hibernation is not currently provisioned: swap is zram-only and the kernel command line has no `resume=` target;
- power-profiles-daemon is the only active power-profile provider;
- KScreenLocker has no explicit `LockOnResume` override, so Stage 6A makes that security property explicit while leaving timeout/grace policy untouched.

The journal also shows brief wake-and-resuspend sequences while the lid is closed. Stage 6A does not disable wake sources: current PowerDevil versions deliberately re-suspend a laptop that wakes spuriously while the lid remains closed, and the available evidence does not identify a harmful wake source that should be disabled.

## Stage 6A — Suspend reliability policy

The approved policy is:

- PowerDevil remains the owner of lid and desktop power-button policy;
- closing the lid on battery requests suspend;
- closing the lid on AC requests suspend;
- PowerDevil keeps its native external-monitor suppression behavior;
- `s2idle` remains the kernel sleep backend;
- normal suspend remains enabled;
- hibernation, hybrid sleep and suspend-then-hibernate are disabled until disk-backed swap and resume infrastructure are intentionally designed and tested;
- KScreenLocker locks on resume;
- no service restart, reboot, bootloader change or power-profile change is part of Stage 6A.

The systemd sleep policy is installed from `mobile/systemd/90-helm-mobile-sleep.conf`. The live installer also records a recovery snapshot before changing `powerdevilrc`, `kscreenlockerrc` or the systemd sleep drop-in.

Stage 6A does **not** trigger suspend during installation. Real lid-close and manual suspend/resume verification belongs to Stage 6B so that the test is deliberate and observable.

## Recovery

Apply:

    scripts/mobile/apply-stage6a-suspend-policy.sh

Restore:

    scripts/mobile/restore-stage6a-suspend-policy.sh

Neither path restarts the display manager or changes boot/authentication infrastructure.

## Stage 6B — Real suspend/resume validation

Stage 6B performs the deliberately deferred real-hardware validation without changing the Stage 6A policy.

The reference ThinkPad passed both required cycles:

- manual `systemctl suspend` entered and exited `s2idle`;
- physical lid close was handled by PowerDevil and produced a real suspend/resume cycle;
- KScreenLocker reported the resumed session locked after both cycles;
- HELM Security Lock was visible and the native password path unlocked the session after both cycles;
- `amdgpu` resumed successfully after both cycles;
- Wi-Fi was connected before the tests and recovered after both resumes;
- the active power profile and boot identity were preserved;
- no failed system or user services remained after resume;
- no hibernate, hybrid-sleep or suspend-then-hibernate path was used.

The milestone is tracked by `mobile/power/suspend-validation.json`. Device evidence remains outside Git in `~/.local/share/helm-mobile/stage6b-suspend-validation-state.json`.

Stage 6B status: **REAL-HARDWARE VERIFIED**.
