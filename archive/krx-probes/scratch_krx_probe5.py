"""Probe 5: locate the exact .cmd?bld= base URL in the portal JS."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1


def get(url):
    time.sleep(SLEEP)
    r = requests.get(url, headers=UA, timeout=30)
    print(f"GET {url} -> {r.status_code} len={len(r.text)}")
    return r.text


util = get("http://data.krx.co.kr/inc/js/mdc.util.js")
# Context around .cmd?bld= and any URL-building around 'bld'.
for m in re.finditer(r'.cmd\?bld=', util):
    s = max(0, m.start() - 200)
    print("CTX:", util[s : m.end() + 120].replace("\n", " ")[:340])
    print("---")
# Also look for a servlet base like /ops or /bld or "getTrCode".
for kw in ("getBld", "servlet", "/MDC/", "execute", "query"):
    hits = [util[max(0, m.start() - 80) : m.start() + 120].replace("\n", " ") for m in re.finditer(re.escape(kw), util)][:4]
    for h in hits:
        print(f"[{kw}] {h}")
