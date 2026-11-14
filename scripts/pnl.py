"""매장 손익 모델: Bottom-up ↔ Top-down 교차검증, 3개 시나리오, 민감도.

사용: python scripts/pnl.py   (profile_area.py 실행 후)
출력: data/processed/pnl.csv, data/processed/pnl.json
모든 '가정'은 shared/assumptions.md 의 A-코드와 1:1 대응.
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "processed")
prof = json.load(open(os.path.join(OUT, "profile.json"), encoding="utf-8"))
AREA = prof["areas"]["3001496"]  # 강남 마이스 관광특구

# ---------- 데이터에서 온 값 ----------
area_tx_per_store_day = AREA["tx_ttm"] / AREA["stores_avg"] / 365          # 상권 평균 점포당 일 거래건수
area_sales_per_store = AREA["sales_per_store_won"]                          # Top-down 기준
slot_share = AREA["slot_tx_share"]                                          # 시간대별 거래 비중
area_ticket = AREA["ticket_won"]

# ---------- 가정 (assumptions.md) ----------
A = {
    # A1 객수 배수: 신규 매장 일 거래건수 = 상권 평균 점포당 일 거래건수 × 배수
    "tx_mult": {"bear": 0.85, "base": 1.15, "bull": 1.40},
    # A2 객단가(원): 메뉴 믹스로 계산한 값(menu.md) — 상권 평균 11,916원 대비
    "ticket": {"bear": 11000, "base": 12000, "bull": 12600},
    "days": 360,                         # A3 연 영업일
    "cogs_rate": 0.29,                   # A4 매출원가율(메뉴 믹스 가중, menu.md)
    "fte": 5.0,                          # A5 상시 인원(FTE, 점장 포함)
    "hourly_cost": 15000,                # A6 1인 시간당 총인건비(원): 2026 최저임금 10,320원 + 주휴·4대보험·점장 프리미엄
    "hours_month": 209,                  # A7 월 소정근로시간
    "area_m2": 99,                       # A8 전용면적(㎡) ≈ 30평
    "rent_m2": {"bear": 140000, "base": 110000, "bull": 90000},   # A9 월 임대료+관리비(원/㎡)
    "hq_rate": 0.03,                     # A10 본사 관리비(자사 브랜드, 로열티 대신)
    "other_rate": 0.07,                  # A11 카드수수료·수도광열·소모품·마케팅
    "capex": 200_000_000,                # A12 시설 투자(인테리어 1.0억+장비 0.7억+설계·간판·초도 0.3억)
    "deposit_months": 12,                # A13 보증금 = 월세 × 12개월
    "dep_years": 5,                      # A14 감가상각 기간
}


def run(sc, tx_mult=None, ticket=None, rent_m2=None):
    tx_day = area_tx_per_store_day * (tx_mult if tx_mult is not None else A["tx_mult"][sc])
    tk = ticket if ticket is not None else A["ticket"][sc]
    rent = (rent_m2 if rent_m2 is not None else A["rent_m2"][sc]) * A["area_m2"] * 12
    rev = tx_day * tk * A["days"]
    cogs = rev * A["cogs_rate"]
    labor = A["fte"] * A["hourly_cost"] * A["hours_month"] * 12
    hq = rev * A["hq_rate"]
    other = rev * A["other_rate"]
    dep = A["capex"] / A["dep_years"]
    op = rev - cogs - labor - rent - hq - other - dep
    ebitda = op + dep
    invest = A["capex"] + rent / 12 * A["deposit_months"]
    return {
        "scenario": sc, "tx_day": round(tx_day), "ticket": tk, "revenue": round(rev), "cogs": round(cogs),
        "labor": round(labor), "rent": round(rent), "hq": round(hq), "other": round(other), "dep": round(dep),
        "op": round(op), "op_margin": round(op / rev, 4), "ebitda": round(ebitda), "invest": round(invest),
        "payback_years": round(invest / ebitda, 2) if ebitda > 0 else None,
        "breakeven_tx_day": round((labor + rent + dep) / (tk * A["days"] * (1 - A["cogs_rate"] - A["hq_rate"] - A["other_rate"]))),
    }


def main():
    sc = {k: run(k) for k in ["bear", "base", "bull"]}
    base = sc["base"]
    # Bottom-up 시간대 분해(기본 시나리오)
    slots = {s: round(base["tx_day"] * v) for s, v in slot_share.items()}
    # Top-down 교차검증: 상권 점포당 평균 매출 × 같은 배수
    topdown = area_sales_per_store * A["tx_mult"]["base"] * (A["ticket"]["base"] / area_ticket)
    cross = {
        "bottom_up_revenue": base["revenue"],
        "top_down_revenue": round(topdown),
        "top_down_raw_area_avg": round(area_sales_per_store),
        "gap_pct": round(base["revenue"] / topdown - 1, 4),
        "note": "Bottom-up=시간대별 일 거래건수×객단가×360일, Top-down=상권 커피점 점포당 연매출×같은 객수배수×(객단가/상권 객단가). 영업일 차이(360 vs 365)만큼 차이",
    }
    # 민감도: 기본 대비 ±10%/±20%
    sens = []
    for var in ["tx", "ticket", "rent"]:
        for d in [-0.2, -0.1, 0.1, 0.2]:
            kw = {}
            if var == "tx":
                kw["tx_mult"] = A["tx_mult"]["base"] * (1 + d)
            elif var == "ticket":
                kw["ticket"] = A["ticket"]["base"] * (1 + d)
            else:
                kw["rent_m2"] = A["rent_m2"]["base"] * (1 + d)
            r = run("base", **kw)
            sens.append({"var": var, "delta": d, "op": r["op"], "op_margin": r["op_margin"], "payback_years": r["payback_years"]})
    res = {"inputs_from_data": {"area_tx_per_store_day": round(area_tx_per_store_day, 1),
                                "area_sales_per_store": round(area_sales_per_store), "area_ticket": area_ticket,
                                "slot_tx_share": slot_share},
           "assumptions": A, "scenarios": sc, "bottom_up_slots_base": slots, "cross_check": cross, "sensitivity": sens}
    json.dump(res, open(os.path.join(OUT, "pnl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    keys = ["tx_day", "ticket", "revenue", "cogs", "labor", "rent", "hq", "other", "dep", "op", "op_margin", "ebitda",
            "invest", "payback_years", "breakeven_tx_day"]
    with open(os.path.join(OUT, "pnl.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["item", "bear", "base", "bull"])
        for k in keys:
            w.writerow([k] + [sc[s][k] for s in ["bear", "base", "bull"]])
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
