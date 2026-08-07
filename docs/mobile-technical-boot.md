# HELM Mobile Technical Boot

Stage 4D intentionally preserves the Mobile Node's existing technical boot presentation instead of replacing it with a full-screen HELM Plymouth animation.

## Approved boot chain

```text
UEFI
  -> systemd-boot
  -> arch-linux.efi UKI
  -> embedded Arch systemd-stub splash
  -> verbose kernel/initramfs output
  -> console LUKS credential prompt
  -> normal system boot
  -> SDDM HELM Access Gate
  -> Plasma Wayland
```

## Arch splash

The Arch image is embedded in the UKI by the mkinitcpio preset:

```text
default_uki="/boot/EFI/Linux/arch-linux.efi"
default_options="--splash /usr/share/systemd/bootctl/splash-arch.bmp"
```

The `--splash` option above is an mkinitcpio UKI-build option. It is not the kernel command-line `splash` argument. The embedded Arch splash is part of the approved Technical Boot identity and should remain visible.

## Verbose boot output

The kernel command line intentionally contains neither `quiet` nor `splash`. Boot and initramfs messages therefore remain visible by design.

## LUKS authentication

The approved mkinitcpio encryption path remains console-based. The required relative hook order is:

```text
block -> encrypt -> filesystems
```

The `plymouth` hook must not be inserted into the initramfs as part of Stage 4D. This preserves the current visible LUKS credential interaction.

## Plymouth

The Plymouth package may exist on the installed system and late boot Plymouth services may be present. Stage 4D does not activate Plymouth in mkinitcpio and does not use Plymouth to replace the approved Arch + verbose boot sequence.

## UKI selection

Never identify the active UKI by alphabetical filename ordering. The approved mapping is resolved from systemd-boot:

```text
selected entry: arch-linux.efi
active UKI: /boot/EFI/Linux/arch-linux.efi
```

The LTS UKI is a separate boot entry and must not be modified merely because of filename ordering.

## Recovery baseline

Before any future Stage 4D operation that modifies or rebuilds the active UKI, a byte-for-byte backup and SHA256 checksum of the active UKI are required. The current baseline state is stored outside the repository under:

```text
~/.local/share/helm-mobile/stage4d-technical-boot-baseline.json
```

## Safety contract

Stage 4D must not silently:

- add `quiet`;
- add kernel command-line `splash`;
- insert the `plymouth` mkinitcpio hook;
- replace the Arch UKI splash;
- select a UKI by filename ordering;
- rebuild all UKIs when only one has been explicitly approved;
- modify the active UKI without a recovery copy;
- reboot automatically.

Formalizing Stage 4D does not itself modify `/boot`, `/etc/kernel/cmdline`, or `/etc/mkinitcpio.conf`.
