"""Probe 13: enumerate all .cmd endpoints across the portal's JS bundle."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

js_files = [
    "/inc/js/mdc.js",
    "/inc/js/mdc.util.js",
    "/inc/js/mdc.module.js",
    "/inc/js/mdc.lang.js",
    "/inc/js/mdc.validate.js",
]
found = {}
for jf in js_files:
    time.sleep(SLEEP)
    try:
        r = requests.get(f"http://data.krx.co.kr{jf}?v=20260720_1", headers=UA, timeout=30)
    except Exception as e:
        print(jf, "EXC", e)
        continue
    txt = r.text
    print(f"{jf} -> {r.status_code} len={len(txt)}")
    for m in re.finditer(r'''['"](/[^'"\s]{3,90}?\.cmd[^'"\s]{0,40})['"]''', txt):
        found.setdefault(m.group(1), set()).add(jf)
for ep in sorted(found):
    print(ep, " <-", sorted(found[ep]))
