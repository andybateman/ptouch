# ptouch: how it works

## About

Prints labels on a Brother PT-E550W or PT-E560BT plugged into a Mac by USB, with no Brother driver. **PT-E560BT (USB 04f9:2203, added 2026-11-23):** the same raster commands work, but it sends no status notifications unless the job starts with `ESC i ! 0`, and the last page is marked with page index 2; both are now in every job, so the E550W gets them too. Written 2026-11-20: `ptouch-print` isn't in Homebrew and its git server wouldn't serve a clone, so this speaks Brother's raster commands directly.

- `pt.py`: finds the printer (USB 04f9:2060 PT-E550W, 04f9:2203 PT-E560BT) through libusb and reads its status (tape width, type, colours, errors).
- `printlabels.py`: lays out each label and prints the lot as one job.
- `ptouch`: the shell command wrapping both.

## Commands (2026-11-23)

`ptouch` (shell) runs `pt.py` for `status` and `models`, `ptouch.py` for `qr`, `me`, `tag`, `flag`, `wifi` and `ql`, and `printlabels.py` for plain labels. `qrlabel.py` holds the image layouts (QR, flag), the scan check and the Wi-Fi payload.

- **Tape and ink:** the layout height comes from the loaded tape (12 mm prints on 70 pins, 24 mm on 128). The QR module grows with it (2 dots, 7 mm, on 12 mm; 4 dots, 14 mm, on 24 mm). The ink colour comes from the status reply's text colour: white ink (0x01) on black tape inks the code's light modules and quiet zone; any other ink inks the dark modules. Either way the code reads as dark on light.
- **Scan check:** before printing, `qr`, `tag` and `wifi` decode their own code from a simulated print with OpenCV and refuse to print if it fails.
- **HA tags:** `tag` reuses an existing tag of the same name (`tag/list`), or creates one over the WebSocket API (`tag/create`, a random hex id, the name given) only after its code passes the scan check with the URL and token from `HA_URL` and `HA_TOKEN` or the config file, and encodes `https://www.home-assistant.io/tag/<id>`, the form the HA app recognises. Preview does not create a tag. The automation (trigger: Tag scanned) is a separate step.
- **Cable flag:** the text, a blank stretch of `--wrap` mm (default 25) that goes round the cable, then the text turned 180 degrees so both faces of the folded flag read the right way up. Several texts print as one strip, one flag each. `--wrap 6` suits a component lead (45 mm flags on 6 mm tape, 2026-11-25).
- **Wi-Fi:** `WIFI:T:WPA;S:<ssid>;P:<password>;;` with `\ ; , : "` escaped. The password is typed hidden or read with `security find-generic-password -D "AirPort network password" -a SSID -w` (macOS asks first); it is never printed or logged, only encoded in the code.
- **QL-1110NWB:** `ql` renders at 300 dpi to the page size (black on white, lines centred) or takes a PNG, then `lp -d Brother_QL_1110NWB -o PageSize=<size> -o fit-to-page`. Not yet printed from (as at 2026-11-23).

## Models

`ptouch models` prints the table in `pt.py`. Supported: USB P-touch models with the 128-pin, 180 dpi head and the same raster commands. Printed from: PT-E550W (04f9:2060), PT-E560BT (04f9:2203). Listed but untested (product ids from the ptouch-print project's model list): PT-E310BT, PT-H500, PT-E500, PT-P700, PT-P750W, PT-P710BT, PT-D410, PT-D460BT, PT-D610BT. Refused: the 560-pin, 360 dpi PT-P900, P900W, P950NW and P910BT (the layout assumes 128 pins), and a PT-P750W in mass-storage (Editor Lite) mode. Older PC-connected models (PT-2430PC and similar) are left out: they predate parts of this command set.

## Use

Needs `brew install libusb` and `uv` (pyusb and Pillow come in through `uv run`). Plug the printer in by USB and switch it on. Link the `ptouch` command into a folder on your PATH (it finds its own files through the link).

```sh
ptouch status                  # tape width and type, any error
ptouch BLE-4 THR-2             # one label per argument, printed as one half-cut strip
ptouch --preview BLE-4         # PNGs in ./ptouch-preview/, nothing printed
ptouch --plain Spare           # without the configured top line
ptouch 21 BLE-4                # main text 3 mm instead of 4 mm (height in dots, 180 dpi)
```

The default text height is 28 dots (4 mm). Print one test label before a run whenever anything changes.

## Configuration

Personal settings live outside the repo in `~/.config/ptouch/config.json` (or the file named by `$PTOUCH_CONFIG`); `localcfg.py` documents the keys:

- `top_line`: a small line printed above every house-style label (a network or household name). None if unset.
- `me`: your own QR label for `ptouch me [N]`: `payload` (the QR content, usually a URL), `lines` (up to two bold lines, such as name and phone) and `small`.
- `ha` (`url`, `token`) or `ha_config` (a JSON file holding them) for `ptouch tag`; `HA_URL` and `HA_TOKEN` override both.

## QR contact labels

`ptouch qr` and `ptouch me` draw a QR code (2-dot modules, 7 mm, on 12 mm tape), then up to two bold lines and a small one. `qrlabel.py URL NAME PHONE SMALL OUT.png` (run with `uv run -q --no-project --with qrcode --with pillow python`) writes the same layout to a PNG, which `ptouch OUT.png` prints as an image.

## The house label

- Designed on 12 mm laminated tape.
- The configured top line in small bold type (9 dots, about 1.3 mm) above the label in bold 4 mm type, both centred, Arial Bold. With no top line, or `--plain`, the label text alone.
- 16-dot space at each end: with 10 the last letter of the top line came out clipped, and the regular weight lost its thin strokes.
- Length follows the text: about 25 mm for a five-character label, plus the printer's fixed blank lead on the first label of a job.
- **Half cuts between labels, one full cut at the end:** a run comes out as one strip on whole backing and the labels peel off. Advanced mode `ESC i K 0x0C` (half cut, no chain) and `ESC i A n` (full cut every n labels) set to the size of the job, up to 99.

## Protocol notes

Per page: `ESC i z` print information (flags 0x86, media type, width, raster count, page 0 first, 1 middle, 2 last or only), various mode `ESC i M 0x40` (auto cut), margin `ESC i d` 14 dots (the 2 mm minimum), TIFF compression `M 0x02`, then one raster line per column of the image: `G` + length + a literal run of the 16 head bytes, or `Z` for a blank line. `0x0C` ends a page, `0x1A` ends the job. The head has 128 pins; 12 mm tape prints on the middle 70 (table in `pt.py` for other widths). The status reply (`ESC i S`, 32 bytes) gives width at byte 10 and media type at byte 11; the job echoes that media type in `ESC i z` (Flexible ID tape is 0x14, laminated 0x01): a mismatch stops the printer with "wrong media" (error byte 9 bit 0) until it is switched off and on (2026-11-23).

**Sending (2026-11-20):** pages go one at a time, each after the printer's "printing completed" status reply (byte 18 = 1; 2 is an error and stops the run, naming the label). A ten-label strip sent as one write stopped after six with no error: the job outgrew the printer's buffer. The status check also retries for up to a minute while a previous job is still printing. The printer can't sense the ink ribbon running out: the tape keeps feeding blank, so check the strip.
