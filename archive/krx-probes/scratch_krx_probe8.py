"""Probe 8: KOFIA portal (data.kofia.or.kr) — find the credit-balance page."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

time.sleep(SLEEP)
try:
    r = requests.get("https://data.kofia.or.kr/", headers=UA, timeout=30)
    print("root:", r.status_code, "len", len(r.text), "url", r.url)
except Exception as e:
    print("EXC", type(e).__name__, e)
    raise SystemExit

# Look for menu links mentioning 신용 or 시장동향.
for kw in ("신용", "융자", "시장동향", "market"):
    for m in re.finditer(kw, r.text):
        s = max(0, m.start() - 160)
        print(f"[{kw}]", r.text[s : m.end() + 100].replace("\n", " ")[:270])
        break  # first hit each
