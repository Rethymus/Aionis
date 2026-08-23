"""Probe 14: extract submitAjax implementation from mdc.util.js."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

time.sleep(SLEEP)
r = requests.get("http://data.krx.co.kr/inc/js/mdc.util.js?v=20260720_1", headers=UA, timeout=30)
txt = r.text
i = txt.find("submitAjax")
while i != -1:
    chunk = txt[i : i + 2600]
    if "function" in chunk[:200] or "submitAjax:" in chunk[:60] or "= function" in chunk[:200]:
        print("=== occurrence at", i, "===")
        print(chunk[:2600])
        print()
        break
    i = txt.find("submitAjax", i + 1)
