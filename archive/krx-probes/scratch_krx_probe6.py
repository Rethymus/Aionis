"""Probe 6: mine the main-index HTML for the margin (신용) menu pages."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

time.sleep(SLEEP)
r = requests.get("http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd", headers=UA, timeout=30)
html = r.text
print("len", len(html))
# Menu entries mentioning 신용 (credit/margin) or 대주 (lending).
for kw in ("신용", "대주", "융자"):
    print(f"\n### {kw}")
    for m in re.finditer(kw, html):
        s = max(0, m.start() - 250)
        ctx = html[s : m.end() + 120].replace("\n", " ")
        # Extract any .cmd page ids in the context.
        pages = re.findall(r"([A-Z0-9]{10,20}\.cmd|[A-Z0-9]+/[A-Z0-9]+)", ctx)
        print(" *", ctx[-330:])
        if pages:
            print("   pages:", sorted(set(pages))[-5:])
