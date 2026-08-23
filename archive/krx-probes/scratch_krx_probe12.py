"""Probe 12: bld in URL query string (as the portal JS does), body = form fields."""
import time

import requests

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
SLEEP = 2.1

s = requests.Session()
s.headers.update(UA)
time.sleep(SLEEP)
r0 = s.get("http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd", timeout=30)
print("page:", r0.status_code)

bld = "dbms/MDC/STAT/standard/MDCSTAT01501"
body = {
    "locale": "ko_KR",
    "mktId": "ALL",
    "trdDd": "20260821",
    "share": "1",
    "money": "1",
    "csvxls_isNo": "false",
}
time.sleep(SLEEP)
r = s.post(
    f"http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd?bld={bld}",
    data=body,
    headers={"Referer": "http://data.krx.co.kr/contents/MDC/STAT/standard/MDCSTAT01501"},
    timeout=30,
)
print("query:", r.status_code, len(r.text))
print(r.text[:1000])
