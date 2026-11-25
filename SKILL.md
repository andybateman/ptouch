# ptouch: print labels on Brother label printers

If `LOCAL.md` sits beside this file, read it first: it holds this machine's own conventions (house label, naming, who to ask).

## When

The user wants a label: a device or board, a cable, a box, a drive, a QR code (contact details, a link), a Home Assistant tag, a Wi-Fi join code, a reprint. A P-touch (PT-E560BT, PT-E550W and other 128-pin USB models) on the Mac's USB, or a QL-1110NWB through macOS printing.

## Steps

1. `ptouch status`: the model, tape width and ink colour, no error. If no printer is found, ask the user to plug it in by USB and switch it on. `ptouch models` lists what is supported.
2. Work out the text.
3. Preview anything new with `--preview` (from a scratch folder), look at the PNG, then print **one** and ask before the run. Previews show the loaded tape's colours.
4. Print, all in one call so a set comes out as one half-cut strip:
   - `ptouch LABEL [LABEL ...]` house-style text (`--plain` drops the configured top line; a bare number sets the text height in dots, 28 = 4 mm); `FILE.png` prints an image
   - `ptouch qr PAYLOAD [LINE1 [LINE2]] [--small TEXT]` QR label; it refuses to print a code that fails the scan check
   - `ptouch me [N]` the user's own QR label from `~/.config/ptouch/config.json`, N copies
   - `ptouch tag NAME [LINE]` creates a Home Assistant tag and prints its QR; then build the automation (trigger: Tag scanned)
   - `ptouch flag TEXT [TEXT ...] [--wrap MM]` cable flags, one per TEXT on one strip (`--wrap 6` for a component lead)
   - `ptouch wifi SSID [--keychain]` Wi-Fi join code: the password is typed hidden or read from Keychain (macOS asks first); never print or log it
   - `ptouch ql --size WxHmm TEXT... | FILE.png` the QL-1110NWB (sizes: `lpoptions -p Brother_QL_1110NWB -l`)
   - `--copies N` on any of them
5. Say what printed and how long each label is (the script prints it). The first label carries the printer's blank lead.

## Rules

- Don't print anything the user hasn't asked for: tape costs money.
- Never send many separate jobs for a set: each job wastes the leading feed.
- A model marked untested (`ptouch models`): one test label first.
- Detail (models, config, protocol): HOWITWORKS.md beside this file.
