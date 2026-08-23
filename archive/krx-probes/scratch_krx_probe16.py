"""Probe 16: find the exact menu URL for 전종목 시세 (MDCSTAT01501)."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

s = requests.Session()
s.headers.update({"User-Agent": UA["User-Agent"]})
time.sleep(SLEEP)
main = s.get("http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd", timeout=30)

# All gotoMenu targets + their menu names.
pairs = re.findall(
    r"gotoMenu\('([^']+)','[^']*'\)[^>]*>\s*<span[^>]*data-menu-name=\"([^\"]+)\"",
    main.text,
)
for url, name in pairs:
    if "시세" in name or "거래실적" in name:
        print(f"{name}: {url[:110]}")
