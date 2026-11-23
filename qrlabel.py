"""Image layouts for ptouch: QR labels, cable flags, and a scan check for the QR codes (2026-11-23)."""
import qrcode
from PIL import Image, ImageDraw, ImageFont
import printlabels as pl
from printlabels import font_for, FONT, DPMM, render_text

FONTR = "/System/Library/Fonts/Supplemental/Arial.ttf"

def qr_matrix(payload):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=0)
    q.add_data(payload); q.make(fit=True)
    return q.get_matrix()

def build_qr(payload, h, lines=(), small=None):
    """QR code on the left, up to two bold lines and one small line on the right. With white ink on black tape
    the code's light modules and a quiet zone are inked and the dark modules left bare; with dark ink on light
    tape the dark modules are inked. Either way it reads as a normal dark-on-light code. Module size grows with
    the tape: 2 dots (7 mm) on 12 mm, 4 dots (14 mm) on 24 mm."""
    m = qr_matrix(payload); n = len(m)
    mod = max(1, (h - 2) // (n + 2))          # at least one module of light margin above and below
    if mod < 2: raise SystemExit(f"payload too long for this tape: {n} modules on {h} pins (shorten it, or wider tape)")
    qz_h = 4 * mod                            # four modules left and right
    qw = n * mod + 2 * qz_h
    lines = [l for l in lines if l]
    cap, scap = round(h * 0.24), round(h * 0.13)
    gap = round(h * 0.13)
    fb, fs = font_for(FONT, cap), font_for(FONTR, scap)
    tw = max([fb.getbbox(l)[2] for l in lines] + ([fs.getbbox(small)[2]] if small else []) + [0])
    W = qw + (14 + tw + 16 if tw else 0)
    im = Image.new("1", (W, h), 0); dr = ImageDraw.Draw(im)
    dark = pl.INK_DARK
    if not dark: dr.rectangle([0, 0, qw - 1, h - 1], fill=1)
    y0 = (h - n * mod) // 2
    for r in range(n):
        for c in range(n):
            if m[r][c]: dr.rectangle([qz_h + c * mod, y0 + r * mod, qz_h + (c + 1) * mod - 1, y0 + (r + 1) * mod - 1], fill=1 if dark else 0)
    if tw:
        rows = [(l, fb, cap) for l in lines] + ([(small, fs, scap)] if small else [])
        block = sum(c for _, _, c in rows) + gap * (len(rows) - 1)
        y = (h - block) // 2; x = qw + 14
        for text, f, c in rows:
            dr.text((x - f.getbbox(text)[0], y - f.getbbox("H")[1]), text, font=f, fill=1)
            y += c + gap
    return im

def build_flag(text, h, wrap_mm=25, cap=28):
    """Cable flag: the text, a blank stretch that wraps round the cable, the text again turned 180 degrees,
    so both faces of the folded flag read the right way up."""
    t = render_text(text, h, min(cap, h - 8), plain=True)
    gapw = round(wrap_mm * DPMM)
    im = Image.new("1", (t.width * 2 + gapw, h), 0)
    im.paste(t, (0, 0)); im.paste(t.rotate(180), (t.width + gapw, 0))
    return im

def verify(im, payload):
    """Decode the QR from a simulated print of the loaded tape. True, False, or None if OpenCV is missing."""
    try:
        import cv2, numpy as np
    except ImportError:
        return None
    a = np.array(im.convert("L"))                     # 255 where inked
    if pl.INK_DARK: a = 255 - a                         # dark ink on light tape
    a = np.pad(a, 60, constant_values=255 if pl.INK_DARK else 0)   # 20 was too tight for OpenCV's standard detector (2026-11-23)
    dets = [cv2.QRCodeDetector()] + ([cv2.QRCodeDetectorAruco()] if hasattr(cv2, "QRCodeDetectorAruco") else [])
    for fx in (4, 6):
        b = cv2.resize(a, None, fx=fx, fy=fx, interpolation=cv2.INTER_NEAREST)
        if any(d.detectAndDecode(b)[0] == payload for d in dets): return True
    return False

def wifi_payload(ssid, password, kind="WPA"):
    esc = lambda s: "".join("\\" + ch if ch in '\\;,:"' else ch for ch in s)
    return f"WIFI:T:{kind};S:{esc(ssid)};P:{esc(password)};;"
