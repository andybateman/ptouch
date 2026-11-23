# ptouch

<!-- Project metadata: read by the project tools, hidden when the README is rendered.
**Keywords:** Brother P-touch, PT-E560BT, PT-E550W, QL-1110NWB, label printer, QR code labels, Home Assistant tags, cable flags, Wi-Fi QR, raster protocol, half cut, TZe tape, libusb, pyusb, USB, macOS, Claude Code skill, device labels
**Status:** Active
**Last Updated:** 2026-11-23
-->

Prints labels on Brother label printers from a Mac: USB P-touch models with no Brother driver, and the QL-1110NWB through macOS printing. Works as a shell command and as a Claude Code skill (`SKILL.md`).

## Why

Brother's own tools aren't scriptable and `ptouch-print` couldn't be installed, so this speaks Brother's raster commands directly: text labels, QR labels, Home Assistant tags, cable flags and Wi-Fi join codes, one half-cut strip per job.

## Status (as at 2026-11-23)

Printed from a PT-E560BT and a PT-E550W; other 128-pin USB P-touch models and the QL-1110NWB are supported but untested.

## Quick start

`brew install libusb uv`, link `ptouch` onto your PATH, plug the printer in by USB, then `ptouch status` and `ptouch --preview HELLO`. Personal settings (a top line for labels, your own QR label, Home Assistant) go in `~/.config/ptouch/config.json`: see `localcfg.py`.

## Where things live

- `ptouch` (the command), `pt.py` (models, USB, status), `printlabels.py` (text labels, printing), `ptouch.py` (qr, me, tag, flag, wifi, ql), `qrlabel.py` (layouts, scan check), `localcfg.py` (personal settings)
- [HOWITWORKS.md](HOWITWORKS.md): use, label layout, protocol notes
- [CHANGELOG.md](CHANGELOG.md): what changed
