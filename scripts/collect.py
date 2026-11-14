"""서울 열린데이터광장 상권분석서비스 수집기.

사용: python scripts/collect.py
- .env 의 SEOUL_API_KEY 사용
- 분기별 전량을 1,000행씩 받아 data/raw/<서비스>/<분기>.csv 로 저장
- 매출·점포는 업종 필터가 API에서 안 되므로 받은 뒤 커피-음료(CS100010)·제과점(CS100005)만 남김
- 이미 받은 파일은 건너뜀 (재실행 안전)
"""
import csv
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
KEEP_INDUSTRY = {"CS100010", "CS100005"}  # 커피-음료, 제과점

QUARTERS = [f"{y}{q}" for y in range(2021, 2027) for q in range(1, 5)]
QUARTERS = [q for q in QUARTERS if q <= "20262"]

SERVICES = {
    "VwsmTrdarSelngQq": True,     # 추정매출-상권 (업종 필터)
    "VwsmTrdarStorQq": True,      # 점포-상권 (업종 필터)
    "VwsmTrdarIxQq": False,       # 상권변화지표-상권
    "VwsmTrdarFlpopQq": False,    # 길단위인구-상권
}
# 분기 필터가 적용되지 않는 서비스: 한 번에 전량 받은 뒤 STDR_YYQU_CD로 나눠 저장
SERVICES_NOFILTER = [
    "VwsmTrdarRepopQq",       # 상주인구-상권
    "VwsmTrdarWrcPopltnQq",   # 직장인구-상권
    "VwsmTrdarFcltyQq",       # 집객시설-상권
]


def key():
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("SEOUL_API_KEY="):
                return line.strip().split("=", 1)[1]
    sys.exit("SEOUL_API_KEY 없음")


KEY = key()


def get(service, start, end, quarter=None):
    url = f"http://openapi.seoul.go.kr:8088/{KEY}/json/{service}/{start}/{end}/"
    if quarter:
        url += quarter
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
            if service in d:
                return d[service]
            code = d.get("RESULT", {}).get("CODE")
            if code == "INFO-200":
                return {"list_total_count": 0, "row": []}
            raise RuntimeError(d)
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))


def fetch_all(service, quarter=None):
    first = get(service, 1, 1000, quarter)
    total = int(first.get("list_total_count", 0))
    rows = list(first.get("row", []))
    starts = list(range(1001, total + 1, 1000))
    with ThreadPoolExecutor(max_workers=6) as ex:
        for part in ex.map(lambda s: get(service, s, min(s + 999, total), quarter), starts):
            rows.extend(part.get("row", []))
    return total, rows


def save(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        open(path, "w").close()
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    log = []
    # 상권 영역(좌표·자치구·행정동)
    p = os.path.join(RAW, "TbgisTrdarRelm", "all.csv")
    if not os.path.exists(p):
        total, rows = fetch_all("TbgisTrdarRelm")
        save(p, rows)
        log.append(("TbgisTrdarRelm", "all", total, len(rows)))
    for service, filt in SERVICES.items():
        for q in QUARTERS:
            p = os.path.join(RAW, service, f"{q}.csv")
            if os.path.exists(p):
                continue
            total, rows = fetch_all(service, q)
            if len(rows) != total:
                print(f"경고 {service} {q}: {len(rows)}/{total}", flush=True)
            kept = [r for r in rows if r.get("SVC_INDUTY_CD") in KEEP_INDUSTRY] if filt else rows
            save(p, kept)
            log.append((service, q, total, len(kept)))
            print(service, q, total, len(kept), flush=True)
    for service in SERVICES_NOFILTER:
        if os.path.exists(os.path.join(RAW, service, "_done")):
            continue
        total, rows = fetch_all(service)
        if len(rows) != total:
            print(f"경고 {service}: {len(rows)}/{total}", flush=True)
        by_q = {}
        for r in rows:
            by_q.setdefault(r["STDR_YYQU_CD"], []).append(r)
        for q, part in sorted(by_q.items()):
            save(os.path.join(RAW, service, f"{q}.csv"), part)
            log.append((service, q, total, len(part)))
        open(os.path.join(RAW, service, "_done"), "w").close()
        print(service, total, sorted(by_q), flush=True)
    with open(os.path.join(RAW, "collect_log.csv"), "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in log:
            w.writerow(row + (time.strftime("%Y-%m-%d %H:%M"),))


if __name__ == "__main__":
    main()
