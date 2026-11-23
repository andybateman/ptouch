"""Personal settings, kept out of the repo: ~/.config/ptouch/config.json, or the file named by $PTOUCH_CONFIG.

{
  "top_line": "My Network",                 small line above house-style labels (omit for none)
  "me": {"payload": "https://example.com",  ptouch me: QR payload,
         "lines": ["Your Name", "+00 0000"], up to two bold lines,
         "small": "example.com"},           and a small line
  "ha": {"url": "https://ha.example:8123", "token": "..."},   for ptouch tag (or HA_URL and HA_TOKEN)
  "ha_config": "/path/to/other/config.json" a JSON file with url and token, read over "ha"
}"""
import json, os

PATH = os.environ.get("PTOUCH_CONFIG") or os.path.expanduser("~/.config/ptouch/config.json")

def load():
    try:
        with open(PATH) as f: return json.load(f)
    except FileNotFoundError:
        return {}
