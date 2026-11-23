"""Minimal Brother P-touch USB driver (raster command reference): model table, status."""
import sys, time, usb.core, usb.util, usb.backend.libusb1
BK = usb.backend.libusb1.get_backend(find_library=lambda x: "/opt/homebrew/lib/libusb-1.0.dylib")
PRINTABLE = {3.5: 24, 6: 32, 9: 50, 12: 70, 18: 112, 24: 128}  # tape mm -> printable pins (of 128)

# USB P-touch models with the 128-pin, 180 dpi head and the same raster commands (ESC i z / M / G / Z).
# tested = printed from this Mac. The others are matched by the product ids in the ptouch-print project's
# model list and should work, but print one test label first. (2026-11-23)
MODELS = {
    0x2060: dict(name="PT-E550W", tested=True, max_mm=24),
    0x2203: dict(name="PT-E560BT", tested=True, max_mm=24),
    0x2201: dict(name="PT-E310BT", tested=False, max_mm=18),
    0x205E: dict(name="PT-H500", tested=False, max_mm=24),
    0x205F: dict(name="PT-E500", tested=False, max_mm=24),
    0x2061: dict(name="PT-P700", tested=False, max_mm=24),
    0x2062: dict(name="PT-P750W", tested=False, max_mm=24),
    0x20AF: dict(name="PT-P710BT", tested=False, max_mm=24),
    0x20DF: dict(name="PT-D410", tested=False, max_mm=18),
    0x20E0: dict(name="PT-D460BT", tested=False, max_mm=18),
    0x20E1: dict(name="PT-D610BT", tested=False, max_mm=24),
}
# Same command family but a 560-pin, 360 dpi head: the layout code assumes 128 pins, so these are refused.
UNSUPPORTED = {0x2083: "PT-P900", 0x2085: "PT-P900W", 0x2086: "PT-P950NW", 0x20C7: "PT-P910BT",
               0x2065: "PT-P750W in mass-storage (P-touch Editor Lite) mode: hold the Editor Lite button until its light goes out"}
MODEL = None   # set by open_dev()

def find():
    for pid, m in MODELS.items():
        d = usb.core.find(idVendor=0x04F9, idProduct=pid, backend=BK)
        if d is not None: return d, dict(m, pid=pid)
    for pid, n in UNSUPPORTED.items():
        if usb.core.find(idVendor=0x04F9, idProduct=pid, backend=BK) is not None:
            sys.exit(f"{n} found: not supported (see HOWITWORKS.md, Models)")
    return None, None

def open_dev():
    global MODEL
    d, MODEL = find()
    if d is None: sys.exit("No supported Brother P-touch on USB (ptouch models lists them): plug it in and switch it on")
    try:
        if d.is_kernel_driver_active(0): d.detach_kernel_driver(0)
    except Exception: pass
    d.set_configuration(); usb.util.claim_interface(d, 0)
    cfg = d.get_active_configuration()[(0, 0)]
    out = usb.util.find_descriptor(cfg, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    inp = usb.util.find_descriptor(cfg, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
    return d, out, inp

def status(out, inp):
    # The printer refuses writes while it is still printing a previous job: retry for up to a minute.
    for attempt in range(20):
        try:
            out.write(b"\x00" * 100 + b"\x1b\x40" + b"\x1b\x69\x53", timeout=3000); break
        except usb.core.USBTimeoutError:
            if attempt == 19: sys.exit("printer busy for over a minute")
            time.sleep(3)
    for _ in range(50):
        try:
            r = bytes(inp.read(32, timeout=200))
            if len(r) == 32: return r
        except usb.core.USBTimeoutError: pass
        time.sleep(0.05)
    sys.exit("no status reply")

def describe(r):
    kinds = {0x00: "none", 0x01: "laminated", 0x03: "non-laminated", 0x14: "flexible ID", 0x11: "heat-shrink 2:1", 0x17: "heat-shrink 3:1", 0xFF: "incompatible"}
    d = {"error1": r[8], "error2": r[9], "width_mm": r[10], "media": kinds.get(r[11], hex(r[11])), "status_type": r[18], "tape_colour": hex(r[24]), "text_colour": hex(r[25])}
    if MODEL: d = {"model": MODEL["name"] + ("" if MODEL["tested"] else " (untested)"), **d}
    return d

def models():
    for pid, m in MODELS.items(): print(f"04f9:{pid:04x}  {m['name']:<10} up to {m['max_mm']} mm  {'tested' if m['tested'] else 'untested'}")
    for pid, n in UNSUPPORTED.items(): print(f"04f9:{pid:04x}  {n.split(':')[0]:<10} not supported")

if __name__ == "__main__":
    if sys.argv[1:] == ["models"]: models(); sys.exit(0)
    d, o, i = open_dev()
    print(describe(status(o, i)))
