"""Probe 3: fetch the MDC main index page + look for the query endpoint base."""
import re
import time

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
SLEEP = 2.1

time.sleep(SLEEP)
r = requests.get("http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd", headers=UA, timeout=30)
print("main index:", r.status_code, "len", len(r.text))
# Find script/link/src references to understand the SPA layout.
for m in re.findall(r'(?:src|href|action)=["\']([^"\']+)["\']', r.text)[:60]:
    print("  ref:", m)
print(r.text[:3000])
