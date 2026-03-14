# tuxedo-power-profile-adapter

A DBus adapter that lets desktop environments control TUXEDO power profiles through the standard freedesktop power-profiles interface.

## Overview

Modern Linux desktop environments like KDE and GNOME rely on the
`org.freedesktop.UPower.PowerProfiles` DBus interface to switch between
*power-saver*, *balanced*, and *performance* profiles. Normally this
interface is provided by `power-profiles-daemon`.

TUXEDO laptops ship with the Tuxedo Control Center, which offers much more
fine-grained hardware and power configuration than `power-profiles-daemon`.
The catch: its daemon does not implement the
`org.freedesktop.UPower.PowerProfiles` interface, so the standard power
profile controls in your desktop environment simply stop working once you
switch to it.

## What it does

`tuxedo-power-profile-adapter` bridges that gap. It registers itself as the
`org.freedesktop.UPower.PowerProfiles` DBus service and translates any
incoming profile change requests into the corresponding calls to the Tuxedo
Control Center daemon — completely transparent to the desktop environment.

In short: you get the full Tuxedo Control Center experience *and* working
power profile controls in KDE, GNOME, or any other compliant desktop.

## Installation

### AUR

If you are on Arch Linux or an Arch-based distribution, the easiest way to
install the adapter is via the [AUR package](https://aur.archlinux.org/packages/tuxedo-power-profiles-adapter-git):

```
paru -S tuxedo-power-profile-adapter
```

or with any other AUR helper of your choice. The package pulls in all
required dependencies and sets up the systemd service automatically.

### Manual

See the PKGBUILD in the AUR repository for reference on how to build and install the package manually.

## Usage

The adapter is activated automatically by D-Bus when a desktop environment
or another client accesses the
`org.freedesktop.UPower.PowerProfiles` interface.