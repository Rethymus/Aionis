"""Probe 19: second menu + KOFIA via curl.exe (different TLS stack)."""
import time

import requests

SLEEP = 2.1
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"})
time.sleep(SLEEP)
r = s.get(
    "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020301",
    timeout=30,
)
print("투자자별 거래실적 page:", r.status_code, "len", len(r.text))
print("is login page:", "로그인" in r.text[:400])
