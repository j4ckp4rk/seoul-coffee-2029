"""추천 상권 고객 프로필 + 서울 비교값.

사용: python scripts/profile_area.py [TRDAR_CD ...]
출력: data/processed/profile.json
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402

TARGETS = sys.argv[1:] or ["3001496", "3001495", "3001494", "3120222", "3120218"]
PERIOD = "TTM2026"
SLOTS = ["06_11", "11_14", "14_17", "17_21", "21_24"]


def raw_sum(service, cd, cols, industry=None):
    tot = {c: 0.0 for c in cols}
    for q in A.PERIODS[PERIOD]:
        for r in A.load(service, q):
            if r["TRDAR_CD"] != cd:
                continue
            if industry and r.get("SVC_INDUTY_CD") != industry:
                continue
            for c in cols:
                tot[c] += A.f(r.get(c))
    return tot


def main():
    base = A.period_agg(PERIOD)
    b22 = A.period_agg("2022")
    meta = A.area_meta()
    # 서울 전체(분석 대상 상권, 매출 3억 이상) 비교값
    U = [e for e in base.values() if e["sales"] >= A.MIN_SALES]
    ticket = np.array([e["sales"] / e["tx"] for e in U if e["tx"]])
    sps = np.array([e["sales"] / e["stores"] for e in U])
    out = {"period": "2025Q3~2026Q2", "seoul": {
        "n_areas": len(U),
        "median_ticket_won": round(float(np.median(ticket))),
        "median_sales_per_store_won": round(float(np.median(sps))),
        "p90_sales_per_store_won": round(float(np.percentile(sps, 90))),
    }, "areas": {}}
    sale_cols = ["THSMON_SELNG_AMT", "THSMON_SELNG_CO", "MDWK_SELNG_AMT", "WKEND_SELNG_AMT", "MDWK_SELNG_CO",
                 "WKEND_SELNG_CO", "ML_SELNG_AMT", "FML_SELNG_AMT"] + \
        [f"TMZON_{s}_SELNG_CO" for s in SLOTS] + [f"TMZON_{s}_SELNG_AMT" for s in SLOTS] + \
        [f"AGRDE_{a}_SELNG_AMT" for a in ["10", "20", "30", "40", "50", "60_ABOVE"]]
    fl_cols = ["TOT_FLPOP_CO"] + [f"TMZON_{s}_FLPOP_CO" for s in ["00_06"] + SLOTS] + \
        [f"AGRDE_{a}_FLPOP_CO" for a in ["10", "20", "30", "40", "50", "60_ABOVE"]] + \
        ["ML_FLPOP_CO", "FML_FLPOP_CO", "SAT_FLPOP_CO", "SUN_FLPOP_CO", "MON_FLPOP_CO"]
    for cd in TARGETS:
        s = raw_sum("VwsmTrdarSelngQq", cd, sale_cols, A.COFFEE)
        fl = raw_sum("VwsmTrdarFlpopQq", cd, fl_cols)
        e = base.get(cd, {})
        tx = s["THSMON_SELNG_CO"] or 1
        amt = s["THSMON_SELNG_AMT"] or 1
        age_amt = {a: s[f"AGRDE_{a}_SELNG_AMT"] for a in ["10", "20", "30", "40", "50", "60_ABOVE"]}
        age_tot = sum(age_amt.values()) or 1
        fac = {}
        for r in A.load("VwsmTrdarFcltyQq", "20262"):
            if r["TRDAR_CD"] == cd:
                fac = {k: r[k] for k in ["VIATR_FCLTY_CO", "SUBWAY_STATN_CO", "BUS_STTN_CO", "DRTS_CO", "THEAT_CO",
                                         "STAYNG_FCLTY_CO", "UNIV_CO"]}
        out["areas"][cd] = {
            "name": meta.get(cd, {}).get("TRDAR_CD_NM"),
            "gu": meta.get(cd, {}).get("SIGNGU_CD_NM"),
            "dong": meta.get(cd, {}).get("ADSTRD_CD_NM"),
            "area_m2": meta.get(cd, {}).get("RELM_AR"),
            "sales_ttm_won": round(amt),
            "sales_2022_won": round(b22[cd]["sales"]) if cd in b22 else None,
            "tx_ttm": round(tx),
            "ticket_won": round(amt / tx),
            "stores_avg": round(e.get("stores", 0), 1),
            "frc_share": round(e.get("frc_share", 0), 3),
            "sales_per_store_won": round(amt / e["stores"]) if e.get("stores") else None,
            "open_rate": round(e.get("open_rate", 0), 3),
            "close_rate": round(e.get("close_rate", 0), 3),
            "wrc_avg": round(e.get("wrc", 0)),
            "repop_avg": round(e.get("repop", 0)),
            "flpop_q_avg": round(fl["TOT_FLPOP_CO"] / 4),
            "ix": e.get("ix_nm"),
            "weekday_tx_share": round(s["MDWK_SELNG_CO"] / tx, 3),
            "weekday_daily_tx": round(s["MDWK_SELNG_CO"] / (52 * 5)),
            "weekend_daily_tx": round(s["WKEND_SELNG_CO"] / (52 * 2)),
            "female_amt_share": round(s["FML_SELNG_AMT"] / ((s["ML_SELNG_AMT"] + s["FML_SELNG_AMT"]) or 1), 3),
            "slot_tx_share": {sl: round(s[f"TMZON_{sl}_SELNG_CO"] / tx, 3) for sl in SLOTS},
            "slot_ticket_won": {sl: round(s[f"TMZON_{sl}_SELNG_AMT"] / s[f"TMZON_{sl}_SELNG_CO"]) if s[f"TMZON_{sl}_SELNG_CO"] else None for sl in SLOTS},
            "age_amt_share": {a: round(v / age_tot, 3) for a, v in age_amt.items()},
            "flpop_slot_share": {sl: round(fl[f"TMZON_{sl}_FLPOP_CO"] / (fl["TOT_FLPOP_CO"] or 1), 3) for sl in ["00_06"] + SLOTS},
            "flpop_age_share": {a: round(fl[f"AGRDE_{a}_FLPOP_CO"] / (fl["TOT_FLPOP_CO"] or 1), 3) for a in ["10", "20", "30", "40", "50", "60_ABOVE"]},
            "facilities_2026Q2": fac,
        }
    json.dump(out, open(os.path.join(A.OUT, "profile.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
