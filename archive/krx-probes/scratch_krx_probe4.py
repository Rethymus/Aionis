"""Probe 4: grep the portal's own JS for the query endpoint base + bld codes."""
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
for pat in (r'["\']/?ops/[^"\']+', r'bldAttache[^"\']*', r'\.cmd[^"\']*', r'ajax[^;]{0,80}'):
    hits = sorted(set(re.findall(pat, util)))[:15]
    print(f"\npattern {pat!r}:")
    for h in hits:
        print("   ", h[:120])
