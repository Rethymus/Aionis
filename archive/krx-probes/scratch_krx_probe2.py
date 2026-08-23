"""Probe 2: inspect the portal shell + menu/config endpoints (>=2.1s spacing)."""
import time

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
SLEEP = 2.1

# 1. The root shell content.
time.sleep(SLEEP)
r = requests.get("http://data.krx.co.kr/", headers=UA, timeout=30)
print("root:", r.status_code, "len", len(r.text))
print(r.text)
