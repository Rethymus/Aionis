"""Probe 15: full browser flow — mdiLoader page, then the query POST."""
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

s = requests.Session()
s.headers.update({"User-Agent": UA["User-Agent"]})

time.sleep(SLEEP)
main = s.get("http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd", timeout=30)
m = re.search(r"gotoMenu\('([^']*MDCSTAT01501[^']*)'", main.text)
print("전종목 시세 page url:", m.group(1) if m else "NOT FOUND")
if m:
    page_url = "http://data.krx.co.kr" + m.group(1)
    time.sleep(SLEEP)
    pr = s.get(page_url, timeout=30)
    print("page:", pr.status_code, "len", len(pr.text))
    print("cookies now:", sorted(s.cookies.keys()))

bld = "dbms/MDC/STAT/standard/MDCSTAT01501"
time.sleep(SLEEP)
r = s.post(
    f"http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd?bld={bld}",
    data={
        "locale": "ko_KR",
        "mktId": "ALL",
        "trdDd": "20260821",
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false",
    },
    headers={
        "Referer": page_url if m else "http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd",
        "X-Requested-With": "XMLHttpRequest",
    },
    timeout=30,
)
print("query:", r.status_code, len(r.text))
print(r.text[:500])
