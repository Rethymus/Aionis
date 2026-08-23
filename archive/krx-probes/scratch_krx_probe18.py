"""Probe 18: replicate browser sequence incl. getMdcMenu.cmd + full headers."""
import json
import time

import requests

SLEEP = 2.1
BASE = "http://data.krx.co.kr"
s = requests.Session()
s.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
})

time.sleep(SLEEP)
r = s.get(f"{BASE}/contents/MDC/MAIN/main/index.cmd", timeout=30)
print("1) main:", r.status_code)

time.sleep(SLEEP)
r = s.post(
    f"{BASE}/comm/menu/menuLoader/getMdcMenu.cmd",
    data={"locale": "ko_KR"},
    headers={
        "Referer": f"{BASE}/contents/MDC/MAIN/main/index.cmd",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": BASE,
    },
    timeout=30,
)
print("2) menu:", r.status_code, len(r.text), r.text[:120])

page_url = f"{BASE}/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101"
time.sleep(SLEEP)
r = s.get(page_url, headers={"Referer": f"{BASE}/contents/MDC/MAIN/main/index.cmd"}, timeout=30)
print("3) page:", r.status_code, "len", len(r.text))
print("   body head:", r.text[:300].replace("\n", " "))

bld = "dbms/MDC/STAT/standard/MDCSTAT01501"
time.sleep(SLEEP)
r = s.post(
    f"{BASE}/comm/bldAttendant/getJsonData.cmd?bld={bld}",
    data={
        "locale": "ko_KR",
        "mktId": "ALL",
        "trdDd": "20260821",
        "share": "1",
        "money": "1",
        "csvxls_isNo": "false",
    },
    headers={
        "Referer": page_url,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": BASE,
    },
    timeout=30,
)
print("4) query:", r.status_code, len(r.text))
print(r.text[:600])
