"""ptouch subcommands beyond plain labels: qr, me, tag, flag, wifi, ql. See HOWITWORKS.md."""
import json, os, subprocess, sys, uuid, getpass
from PIL import Image, ImageDraw
import printlabels as pl
import qrlabel as ql
import localcfg

def usage():
    sys.exit(__doc__ + """
  ptouch qr PAYLOAD [LINE1 [LINE2]] [--small TEXT]   QR code (a link, any text) with up to two lines
  ptouch me [N]                                    your own QR label from the config file, N copies
  ptouch tag NAME [LINE]                           Home Assistant tag: creates it in HA, prints its QR
  ptouch flag TEXT [--wrap MM]                     cable flag: TEXT, a blank wrap, TEXT turned round
  ptouch wifi SSID [--keychain]                    Wi-Fi join code; password typed (hidden) or from Keychain
  ptouch ql --size WxHmm TEXT... | FILE.png        print on the QL-1110NWB through macOS printing
Common: --preview, --copies N, --tape MM (preview width when no printer answers)""")

def checked(payload):
    def make(h, lines, small):
        im = ql.build_qr(payload, h, lines, small)
        ok = ql.verify(im, payload)
        if ok is False: sys.exit("the QR code did not decode in the scan check: not printing (shorten the payload or use wider tape)")
        if ok is None: print("scan check skipped (OpenCV not available)")
        return im
    return make

def ha():
    c = localcfg.load(); h = dict(c.get("ha") or {})
    if c.get("ha_config"):
        with open(os.path.expanduser(c["ha_config"])) as f: h = {**h, **json.load(f)}   # the file wins; "ha" fills gaps
    token = os.environ.get("HA_TOKEN") or h.get("token") or h.get("ha_token") or h.get("access_token")
    url = os.environ.get("HA_URL") or h.get("url") or h.get("base_url")
    if not (url and token): sys.exit(f"Home Assistant not configured: set HA_URL and HA_TOKEN, or 'ha' in {localcfg.PATH}")
    return url.rstrip("/"), token

def ha_ws(msg):
    from websockets.sync.client import connect
    url, token = ha()
    with connect(url.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket") as ws:
        json.loads(ws.recv()); ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(ws.recv()).get("type") != "auth_ok": sys.exit("Home Assistant refused the token")
        ws.send(json.dumps({"id": 1, **msg}))
        r = json.loads(ws.recv())
        if not r.get("success"): sys.exit(f"{msg['type']} failed: {r}")
        return r.get("result")

def ha_tag_id(name):
    """An existing HA tag with this name (reprints reuse it), or a new id to create once the code passes."""
    for t in ha_ws({"type": "tag/list"}) or []:
        if t.get("name") == name: return t["id"], False
    return uuid.uuid4().hex, True

def ql_print(o, size, args):
    """QL-1110NWB through CUPS: render at 300 dpi to the page size, black on white, then lp."""
    printer = "Brother_QL_1110NWB"
    try: wmm, hmm = (float(v) for v in size.lower().rstrip("m").rstrip("m").split("x"))
    except Exception: sys.exit("--size like 62x100mm (lpoptions -p Brother_QL_1110NWB -l lists the sizes)")
    dpmm = 300 / 25.4
    W, H = round(wmm * dpmm), round(hmm * dpmm)
    if len(args) == 1 and args[0].lower().endswith(".png"):
        page = args[0]
    else:
        im = Image.new("L", (W, H), 255); dr = ImageDraw.Draw(im)
        cap = max(20, min(int(H * 0.6 / max(1, len(args))), int(W / max(8, max(len(a) for a in args)) * 1.4)))
        f = pl.font_for(pl.FONT, cap); y = (H - (cap * len(args) + cap // 2 * (len(args) - 1))) // 2
        for a in args:
            bx = f.getbbox(a); dr.text(((W - (bx[2] - bx[0])) // 2 - bx[0], y - f.getbbox("H")[1]), a, font=f, fill=0); y += cap + cap // 2
        os.makedirs("ptouch-preview", exist_ok=True); page = "ptouch-preview/ql_label.png"; im.save(page, dpi=(300, 300))
    if o["preview"]: print(f"QL page {size}: {page}"); return
    subprocess.run(["lp", "-d", printer, "-n", str(o["copies"]), "-o", f"PageSize={size}", "-o", "fit-to-page", page], check=True)
    print(f"sent to {printer}: {size}, {o['copies']} copy(ies)")

def main():
    if len(sys.argv) < 2: usage()
    cmd, args = sys.argv[1], sys.argv[2:]
    small = wrap = size = None; keychain = False
    rest = []
    it = iter(args)
    for a in it:
        if a == "--small": small = next(it)
        elif a == "--wrap": wrap = float(next(it))
        elif a == "--size": size = next(it)
        elif a == "--keychain": keychain = True
        else: rest.append(a)
    o = pl.opts(rest); r = o["rest"]
    rep = lambda f: (lambda h: [x for _ in range(o["copies"]) for x in f(h)])

    if cmd == "qr":
        if not r: usage()
        make = checked(r[0])
        pl.run(rep(lambda h: [(r[0][:40].replace("/", "_"), make(h, r[1:3], small))]), o["preview"], o["tape"])
    elif cmd == "me":
        m = localcfg.load().get("me")
        if not m or not m.get("payload"):
            sys.exit(f'no "me" label in {localcfg.PATH}: {{"me": {{"payload": URL, "lines": [NAME, PHONE], "small": TEXT}}}}')
        make = checked(m["payload"]); lines = (m.get("lines") or [])[:2]; sm = small or m.get("small")
        pl.run(rep(lambda h: [("me", make(h, lines, sm))]), o["preview"], o["tape"])
    elif cmd == "tag":
        if not r: usage()
        name = r[0]
        tag_id, new = ha_tag_id(name)
        payload = f"https://www.home-assistant.io/tag/{tag_id}"
        make = checked(payload)
        def build(h):
            im = make(h, [name] + r[1:2], "Scan with the HA app")   # scan check first
            if new and not o["preview"]: ha_ws({"type": "tag/create", "tag_id": tag_id, "name": name})
            return [(f"tag {name}", im)] * o["copies"]
        pl.run(build, o["preview"], o["tape"])
        if not o["preview"]: print(f"HA tag '{name}' = {tag_id} ({'created' if new else 'existing'}): add an automation with trigger 'Tag scanned' on it")
    elif cmd == "flag":
        if not r: usage()
        pl.run(rep(lambda h: [(f"flag {r[0]}", ql.build_flag(r[0], h, wrap or 25, o["cap"]))]), o["preview"], o["tape"])
    elif cmd == "wifi":
        if not r: usage()
        ssid = r[0]
        if keychain:
            pw = subprocess.run(["security", "find-generic-password", "-D", "AirPort network password", "-a", ssid, "-w"],
                                capture_output=True, text=True).stdout.strip()
            if not pw: sys.exit(f"no Keychain Wi-Fi password for {ssid} (or access refused)")
        else:
            pw = getpass.getpass(f"Password for {ssid} (not shown): ")
        payload = ql.wifi_payload(ssid, pw)
        make = checked(payload)
        pl.run(rep(lambda h: [(f"wifi {ssid}", make(h, [f"Wi-Fi: {ssid}"], "Scan to join"))]), o["preview"], o["tape"])
    elif cmd == "ql":
        if not size or not r: usage()
        ql_print(o, size, r)
    else:
        usage()

if __name__ == "__main__":
    main()
