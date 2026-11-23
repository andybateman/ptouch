"""Lay out and print labels on a USB P-touch as one job: half cuts between labels (the backing stays whole,
so they peel off a strip), one full cut at the end. Advanced mode 0x0C = half cut + no chain;
ESC i A n = full cut every n labels, set to the whole job.
Importable (ptouch.py uses it): render_text(), render_png(), run(). Run as a script for text and PNG labels."""
import os, sys, struct, time
from PIL import Image, ImageDraw, ImageFont
import usb.core
import pt
import localcfg
from pt import open_dev, status, describe, PRINTABLE

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
TOP = localcfg.load().get("top_line", "")   # small line above the label; none unless configured
TOP_DOTS = 9      # cap height of the small line (about 1.3 mm)
GAP = 6
DPMM = 7.087      # dots per mm at 180 dpi
INK_DARK = False  # set from the loaded cassette by run(): white ink on black tape (False) or dark ink on light tape (True)

def set_ink(st):
    """Text colour 0x01 is white ink; anything else (black 0x08, red, blue, gold) is treated as dark ink."""
    global INK_DARK
    INK_DARK = int(st["text_colour"], 16) != 0x01

def font_for(path, cap):
    size = cap
    f = ImageFont.truetype(path, size)
    while f.getbbox("H")[3] - f.getbbox("H")[1] < cap: size += 1; f = ImageFont.truetype(path, size)
    return f

def render_text(text, h, cap=28, plain=False):
    big, small = font_for(FONT, cap), font_for(FONT, TOP_DOTS)
    bl, bt, br, bb = big.getbbox(text); sl, st, sr, sb = small.getbbox(TOP)
    pad = 16   # was 10: the final 'k' of Network came out clipped (2026-11-20)
    w = max(br - bl, sr - sl) + 2 * pad
    if plain or not TOP:
        w = br - bl + 2 * pad
        im = Image.new("1", (w, h), 0)
        ImageDraw.Draw(im).text(((w - (br - bl)) // 2 - bl, (h - cap) // 2 - big.getbbox("H")[1]), text, font=big, fill=1)
        return im
    block = TOP_DOTS + GAP + cap
    top_y = (h - block) // 2
    im = Image.new("1", (w, h), 0); dr = ImageDraw.Draw(im)
    dr.text(((w - (sr - sl)) // 2 - sl, top_y - small.getbbox("H")[1]), TOP, font=small, fill=1)
    dr.text(((w - (br - bl)) // 2 - bl, top_y + TOP_DOTS + GAP - big.getbbox("H")[1]), text, font=big, fill=1)
    return im

def render_png(path, h):
    """A ready-made 1-bit image (ink = 1), centred on the pins (2026-11-23)."""
    src = Image.open(path).convert("1")
    if src.height > h: sys.exit(f"{path} is {src.height} dots high; this tape prints {h}")
    im = Image.new("1", (src.width, h), 0); im.paste(src, (0, (h - src.height) // 2))
    return im

def lines(im, offset):
    out = b""
    for x in range(im.width):
        bits = [0] * 128
        for y in range(im.height):
            if im.getpixel((x, y)): bits[offset + y] = 1
        if not any(bits): out += b"Z"; continue
        data = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, 128, 8))
        out += b"G" + struct.pack("<H", 17) + b"\x0f" + data
    return out

def mm(im): return im.width / DPMM + 4

def run(build, preview=False, tape_mm=None):
    """build(h) -> [(name, image)]. Preview: PNGs in ./ptouch-preview, nothing printed (tape_mm, default 12,
    or the loaded tape if a printer answers). Otherwise one job on the printer."""
    if preview:
        if tape_mm is None:
            d, _ = pt.find()
            if d is not None:
                _, o, i = open_dev(); s = describe(status(o, i)); tape_mm = s["width_mm"]; set_ink(s)
        tape_mm = tape_mm or 12
        os.makedirs("ptouch-preview", exist_ok=True)
        for name, im in build(PRINTABLE[tape_mm]):
            f = f"ptouch-preview/{os.path.basename(name)}.png"
            g = im.convert("L")
            if INK_DARK: g = g.point(lambda v: 255 - v)   # show it as the tape will look: dark ink on light tape
            g.resize((im.width * 4, im.height * 4), 0).save(f)
            print(f"{name}: {mm(im):.0f} mm, {f} ({tape_mm} mm tape, {'dark' if INK_DARK else 'white'} ink)")
        return
    d, o, i = open_dev()
    raw = status(o, i); st = describe(raw); w = st["width_mm"]
    media = raw[11]   # echo the cassette's own media type: a fixed 0x01 (laminated) drew "wrong media" on a 0x14 cassette (2026-11-23)
    if st["error1"] or st["error2"]: sys.exit(f"printer error: {st}")
    if w not in PRINTABLE: sys.exit(f"tape width {w} mm not in the table: {st}")
    set_ink(st)
    if not pt.MODEL["tested"]: print(f"{pt.MODEL['name']} has not printed from this Mac before: check the first label")
    h = PRINTABLE[w]; offset = (128 - h) // 2
    labels = build(h)

    def wait_printed(label, limit=90):
        """Read status replies until the printer says this page is printed (status type 1). Error (2) stops."""
        end = time.time() + limit
        while time.time() < end:
            try:
                r = bytes(i.read(32, timeout=1000))
            except usb.core.USBTimeoutError:
                continue
            if len(r) != 32: continue
            if r[18] == 0x02 or r[8] or r[9]:
                sys.exit(f"printer error during {label}: {describe(r)} (out of tape or ribbon?)")
            if r[18] == 0x01:
                return
        sys.exit(f"no 'printed' reply for {label} after {limit} s")

    # ESC i ! 0: turn on status notifications. The PT-E550W sends them by default, the PT-E560BT does not, so
    # without this wait_printed() never heard "printed" and the job sat at "printing" (2026-11-23).
    o.write(b"\x00" * 100 + b"\x1b\x40" + b"\x1b\x69\x61\x01" + b"\x1b\x69\x21\x00", timeout=5000)
    # One page at a time, each sent only after the last is printed: a long strip sent as one write
    # lost its tail (stopped after 6 of 10 labels, 2026-11-20), the printer's buffer being smaller than the job.
    for n, (name, im) in enumerate(labels):
        page = b"\x1b\x69\x7a" + bytes([0x86, media, w, 0]) + struct.pack("<I", im.width) + bytes([2 if n == len(labels) - 1 else (0 if n == 0 else 1), 0])  # page: 0 first, 1 middle, 2 last (or only)
        page += b"\x1b\x69\x4d\x40" + b"\x1b\x69\x41" + bytes([min(len(labels), 99)]) + b"\x1b\x69\x4b\x0c" + b"\x1b\x69\x64" + struct.pack("<H", 14) + b"M\x02"
        page += lines(im, offset)
        page += b"\x1a" if n == len(labels) - 1 else b"\x0c"
        o.write(page, timeout=30000)
        wait_printed(name)
        print(f"{name}: {im.width} dots = {mm(im):.0f} mm incl. margins, printed")

def opts(args):
    """Shared flags: --preview, --plain, --copies N, --tape MM, a bare number = text cap height in dots."""
    o = dict(preview=False, plain=False, copies=1, tape=None, cap=28, rest=[])
    it = iter(args)
    for a in it:
        if a == "--preview": o["preview"] = True
        elif a == "--plain": o["plain"] = True
        elif a == "--copies": o["copies"] = int(next(it))
        elif a == "--tape": o["tape"] = float(next(it)) if "." in (v := next(it)) else int(v)
        elif a.isdigit(): o["cap"] = int(a)
        else: o["rest"].append(a)
    return o

if __name__ == "__main__":
    o = opts(sys.argv[1:])
    if not o["rest"]: sys.exit("usage: printlabels.py [28] [--preview] [--plain] [--copies N] [--tape MM] LABEL|FILE.png ...")
    def build(h):
        out = []
        for _ in range(o["copies"]):
            for t in o["rest"]:
                out.append((t, render_png(t, h) if t.lower().endswith(".png") else render_text(t, h, o["cap"], o["plain"])))
        return out
    run(build, o["preview"], o["tape"])
