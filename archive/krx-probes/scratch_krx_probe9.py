"""Probe 9: KOFIA fallback attempts — http, verify off, curl-style TLS."""
import requests
import urllib3

urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}

for url in (
    "http://data.kofia.or.kr/",
    "https://data.kofia.or.kr/",
    "https://www.kofia.or.kr/",
    "http://www.kofia.or.kr/",
):
    try:
        r = requests.get(url, headers=UA, timeout=25, verify=False)
        print(url, "->", r.status_code, "len", len(r.text), "final", r.url)
    except Exception as e:
        print(url, "EXC", type(e).__name__, str(e)[:140])
