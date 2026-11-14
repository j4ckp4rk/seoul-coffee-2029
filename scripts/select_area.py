"""상권 선별 깔때기 + 인사이트 후보 검증.

사용: python scripts/select_area.py  (analyze.py 실행 후)
출력: data/processed/funnel.json, data/processed/insights.json
"""
import csv
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402

OUT = A.OUT
MIN_SCALE = 50e8      # 화면2: 최근 4분기 커피 매출 50억 원 이상
MIN_TREND = 0.0       # 화면3: 2022→최근 4분기 매출 성장률 0% 이상(구조적 하락 제외)


def main():
    rows = list(csv.DictReader(open(os.path.join(OUT, "scores_current.csv"), encoding="utf-8-sig")))
    p22 = A.period_agg("2022")
    n = len(rows)
    top = rows[: max(1, n // 10)]
    s2 = [r for r in top if float(r["sales_ttm"]) >= MIN_SCALE]
    s3 = []
    for r in s2:
        b = p22.get(r["TRDAR_CD"])
        tr = (float(r["sales_ttm"]) / b["sales"] - 1) if b else None
        r["trend_22_ttm"] = round(tr, 4) if tr is not None else None
        if tr is not None and tr >= MIN_TREND:
            s3.append(r)
    keep = ["rank", "TRDAR_CD", "상권명", "자치구", "행정동", "구분", "score", "sales_ttm", "stores", "flpop_q",
            "flpop_2030", "wrc", "변화지표", "trend_22_ttm"]
    funnel = {
        "step0_scored": n,
        "step1_top10pct": len(top),
        "step2_scale": {"rule": f"최근 4분기 커피 매출 ≥ {MIN_SCALE/1e8:.0f}억 원", "n": len(s2)},
        "step3_trend": {"rule": "2022년 대비 최근 4분기 매출 성장 ≥ 0%", "n": len(s3)},
        "top10pct": [{k: r.get(k) for k in keep} for r in top],
        "after_step3": [{k: r.get(k) for k in keep} for r in s3],
        "dropped_step3": [{k: r.get(k) for k in keep} for r in s2 if r not in s3],
    }
    json.dump(funnel, open(os.path.join(OUT, "funnel.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- 인사이트 후보: 백테스트 표본에서 지표 5분위별 실제 3년 CAGR ----
    bt = list(csv.DictReader(open(os.path.join(OUT, "backtest_2022_2025.csv"), encoding="utf-8-sig")))
    y = np.array([float(r["actual_cagr_22_25"]) for r in bt])
    ins = {}
    for code in ["S1", "S2", "M1", "D3", "R2"]:
        x = np.array([float(r[code]) for r in bt])
        cuts = np.percentile(x, [20, 40, 60, 80])
        q = np.digitize(x, cuts)
        ins[code] = {
            "spearman": round(A.spearman(x, y), 3),
            "quintile_mean_cagr": [round(float(y[q == i].mean()), 4) for i in range(5)],
            "quintile_median_cagr": [round(float(np.median(y[q == i])), 4) for i in range(5)],
            "quintile_x_range": [[round(float(x[q == i].min()), 3), round(float(x[q == i].max()), 3)] for i in range(5)],
            "n_per_quintile": [int((q == i).sum()) for i in range(5)],
        }
    # 매출 상위 10% vs 점수 상위 10%
    sales = np.array([float(r["sales_2022"]) for r in bt])
    score = np.array([float(r["cv_pred"]) for r in bt])
    k = len(bt) // 10
    ts = np.argsort(-sales)[:k]
    tc = np.argsort(-score)[:k]
    ins["top_sales_vs_top_score"] = {
        "k": k,
        "sales_top_mean_cagr": round(float(y[ts].mean()), 4),
        "sales_top_share_declined": round(float((y[ts] < 0).mean()), 3),
        "score_top_mean_cagr": round(float(y[tc].mean()), 4),
        "score_top_share_declined": round(float((y[tc] < 0).mean()), 3),
        "all_mean_cagr": round(float(y.mean()), 4),
        "all_share_declined": round(float((y < 0).mean()), 3),
    }
    json.dump(ins, open(os.path.join(OUT, "insights.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in funnel.items() if not k.startswith("top10")}, ensure_ascii=False, indent=1))
    print(json.dumps(ins, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
