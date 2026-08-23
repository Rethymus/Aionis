"""Probe 17: mdiLoader page visit (menuId=MDC0201020101), then query POST."""
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}
SLEEP = 2.1

s = requests.Session()
s.headers.update({"User-Agent": UA["User-Agent"]})
page_url = "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101"
time.sleep(SLEEP)
pr = s.get(page_url, timeout=30)
print("page:", pr.status_code, "len", len(pr.text))
print("cookies:", sorted(s.cookies.keys()))

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
    headers={"Referer": page_url, "X-Requested-With": "XMLHttpRequest"},
    timeout=30,
)
print("query:", r.status_code, len(r.text))
print(r.text[:600])
