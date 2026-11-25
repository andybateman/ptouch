# Changelog - ptouch

## [2026-11-25] - Several cable flags on one strip; --help no longer prints

- **`ptouch flag TEXT [TEXT ...]`:** one flag per text, all on one half-cut strip (it printed only the first text before). `--wrap 6` suits a component lead.
- **`-h` / `--help` after a subcommand** shows the usage; before, `ptouch flag --help` printed a flag reading "--help".

## [2026-11-23] - Public release: personal settings moved to a config file

- **`localcfg.py`:** the label top line, the `ptouch me` label and the Home Assistant connection come from `~/.config/ptouch/config.json` (or `$PTOUCH_CONFIG`); `HA_URL` and `HA_TOKEN` work too. No personal details, hosts or paths in the code.
- **`ptouch me [N]`:** your own QR label from the config, N copies on one strip; other options (`--preview`, `--tape`) pass through.
- The `ptouch` command finds its own folder through a symlink, so it can be linked anywhere on the PATH.
- MIT licence.
- `SKILL.md` reads an optional, untracked `LOCAL.md` for a machine's own conventions.

## [2026-11-23] - Other Brother models, the QL-1110NWB, qr / tag / flag / wifi, --copies, wider tape

- **Models:** `pt.py` has a model table: PT-E550W and PT-E560BT tested; PT-E310BT, H500, E500, P700, P750W, P710BT, D410, D460BT and D610BT listed as untested (warned on first print); 560-pin P9xx models refused. `ptouch models` lists them; status names the model.
- **QL-1110NWB:** `ptouch ql --size WxHmm` through macOS printing (CUPS, `lp`). Previewed only.
- **New subcommands** in `ptouch.py`: `qr` (with a scan check that refuses an unreadable code), `tag` (creates a Home Assistant tag and prints its QR), `flag` (cable flag), `wifi` (join code; password typed hidden or from Keychain, never shown).
- **`--copies N`** on everything; `--tape MM` for previews with no printer attached.
- **Tape and ink follow the cassette:** layouts size to the loaded tape (QR 14 mm on 24 mm tape) and QR codes ink the right modules for white-on-black or dark-on-light tape; previews show the tape's colours. Found when 24 mm dark-on-light tape was loaded: the old layout would have printed an inverted code.
- **First real HA tag:** printed on 24 mm Flexible ID tape (TZe-FX251) and scanned by the HA app. On the way: OpenCV's standard detector needs a wide margin (the check now pads 60 dots and also tries the Aruco detector), the job must echo the cassette's media type (Flexible ID is 0x14; a fixed 0x01 drew "wrong media", cleared only by switching the printer off and on), and `tag` reuses an existing tag of the same name and creates a new one only after its code passes.
- `printlabels.py` is now importable (`render_text`, `render_png`, `run`); `qrlabel.py` is the layouts module.

## [2026-11-23] - PT-E560BT, image labels, QR contact labels

- **PT-E560BT (USB 04f9:2203)** supported alongside the PT-E550W (`pt.py` tries both). Its first job hung at "printing" after the label had printed: it sends no status notifications unless asked, so every job now starts with `ESC i ! 0`, and the last page carries page index 2 (`printlabels.py`).
- **Image labels:** any argument ending in `.png` prints as a ready-made 1-bit image, centred on the pins; previews use the file's base name.
- **`qrlabel.py`:** QR code plus name, phone and a small line on 12 mm tape.

## [2026-11-20] - Written

- `pt.py`, `printlabels.py` and the `ptouch` command for the PT-E550W; the house label layout.
