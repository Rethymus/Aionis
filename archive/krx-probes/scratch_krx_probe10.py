"""Probe 10: verify /comm/bldAttendant/getJsonData.cmd with MDCSTAT01501."""
import json
import time

import requests

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36",
    "Referer": "http://data.krx.co.kr/contents/MDC/STAT/standard/MDCSTAT01501",
    "X-Requested-With": "XMLHttpRequest",
}
SLEEP = 2.1

body = {
    "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
    "locale": "ko_KR",
    "mktId": "ALL",
    "trdDd": "20260821",
    "share": "1",
    "money": "1",
    "csvxls_isNo": "false",
}
url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
time.sleep(SLEEP)
r = requests.post(url, data=body, headers=UA, timeout=30)
print(r.status_code, len(r.text))
print(r.text[:600])
