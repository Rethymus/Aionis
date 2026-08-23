"""Probe 7: dump the full menu tree names to find margin/거래실적 sections."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

time.sleep(SLEEP)
r = requests.get("http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd", headers=UA, timeout=30)
html = r.text
names = re.findall(r'data-menu-name="([^"]+)"', html)
seen = []
for n in names:
    if n not in seen:
        seen.append(n)
print(f"{len(seen)} unique menu names")
for n in seen:
    print(" -", n)
