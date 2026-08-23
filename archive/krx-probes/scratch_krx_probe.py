"""One-off source-archaeology probe for the KRX data portal (data.krx.co.kr).

Polite: >=2.1s between requests to the same host. NOT part of the library —
a scratch verifier for endpoint shapes, run once and deleted.
"""
import json
import time

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Referer": "http://data.krx.co.kr/ops/bld/bldAttache/bldAttache/getMDCSTAT01501",
}
SLEEP = 2.1


def probe(url, body):
    time.sleep(SLEEP)
    r = requests.post(url, data=body, headers=UA, timeout=30)
    print(f"POST {url}\n  body={body}\n  -> {r.status_code} len={len(r.text)}")
    head = r.text[:400].replace("\n", " ")
    print(f"  head: {head}")
    return r


# Endpoint-shape candidates with the canonical 전종목시세 query (MDCSTAT01501).
body = {
    "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
    "locale": "ko_KR",
    "mktId": "ALL",
    "trdDd": "20260821",
    "share": "1",
    "money": "1",
    "csvxls_isNo": "false",
}
cands = [
    "http://data.krx.co.kr/ops/bld/bldAttache/bldAttache/getMDCSTAT01501",
    "http://data.krx.co.kr/ops/bld/bldAttache/bldAttacheQuery",
    "http://openapi.krx.co.kr:8080/ops/bld/bldAttache/bldAttache/getMDCSTAT01501",
]
for url in cands:
    try:
        r = probe(url, body)
    except Exception as e:
        print(f"  EXC {type(e).__name__}: {e}")
