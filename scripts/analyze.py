"""지표 계산 · 상관 점검 · 백테스트 · 현재 점수화.

사용: python scripts/analyze.py
입력: data/raw/<서비스>/<분기>.csv (scripts/collect.py 산출)
출력: data/processed/*.csv, data/processed/backtest.json

설계
- 단위: 서울시 상권분석서비스 상권(TRDAR_CD)
- 대상 업종: 커피-음료(CS100010)
- 백테스트: 기준기간 B=2022년(전년 2021) 지표 → 2022→2025 커피 추정매출 3년 CAGR
- 안정성 점검: 같은 가중치로 B=2023 → 2023→2025 2년 CAGR
- 현재 점수: B=최근 4분기(2025Q3~2026Q2), 전년=2024Q3~2025Q2 → 2029년 중반까지의 성장 예측
"""
import csv
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "processed")
os.makedirs(OUT, exist_ok=True)
COFFEE = "CS100010"

PERIODS = {
    "2021": ["20211", "20212", "20213", "20214"],
    "2022": ["20221", "20222", "20223", "20224"],
    "2023": ["20231", "20232", "20233", "20234"],
    "2024": ["20241", "20242", "20243", "20244"],
    "2025": ["20251", "20252", "20253", "20254"],
    "TTM2025": ["20243", "20244", "20251", "20252"],
    "TTM2026": ["20253", "20254", "20261", "20262"],
}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


_cache = {}


def load(service, q):
    k = (service, q)
    if k not in _cache:
        p = os.path.join(RAW, service, f"{q}.csv")
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            _cache[k] = []
        else:
            with open(p, encoding="utf-8-sig") as fh:
                _cache[k] = list(csv.DictReader(fh))
    return _cache[k]


def area_meta():
    meta = {}
    with open(os.path.join(RAW, "TbgisTrdarRelm", "all.csv"), encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            meta[r["TRDAR_CD"]] = r
    return meta


def period_agg(pkey):
    """기간(4개 분기) 단위로 상권별 값을 집계. 매출은 4분기 모두 있어야 함."""
    qs = PERIODS[pkey]
    A = {}

    def a(cd):
        return A.setdefault(cd, {"_q": set()})

    for q in qs:
        for r in load("VwsmTrdarSelngQq", q):
            if r["SVC_INDUTY_CD"] != COFFEE:
                continue
            d = a(r["TRDAR_CD"])
            d["_q"].add(q)
            for col in ["THSMON_SELNG_AMT", "THSMON_SELNG_CO", "WKEND_SELNG_AMT",
                        "AGRDE_20_SELNG_AMT", "AGRDE_30_SELNG_AMT", "ML_SELNG_AMT", "FML_SELNG_AMT",
                        "TMZON_06_11_SELNG_AMT", "TMZON_11_14_SELNG_AMT", "TMZON_14_17_SELNG_AMT",
                        "TMZON_17_21_SELNG_AMT", "TMZON_21_24_SELNG_AMT",
                        "TMZON_06_11_SELNG_CO", "TMZON_11_14_SELNG_CO", "TMZON_14_17_SELNG_CO",
                        "TMZON_17_21_SELNG_CO", "TMZON_21_24_SELNG_CO", "MDWK_SELNG_CO", "WKEND_SELNG_CO"]:
                d[col] = d.get(col, 0.0) + f(r.get(col))
        for r in load("VwsmTrdarStorQq", q):
            if r["SVC_INDUTY_CD"] != COFFEE:
                continue
            d = a(r["TRDAR_CD"])
            d["stor_sum"] = d.get("stor_sum", 0.0) + f(r["SIMILR_INDUTY_STOR_CO"])
            d["frc_sum"] = d.get("frc_sum", 0.0) + f(r["FRC_STOR_CO"])
            d["open"] = d.get("open", 0.0) + f(r["OPBIZ_STOR_CO"])
            d["close"] = d.get("close", 0.0) + f(r["CLSBIZ_STOR_CO"])
            d["stor_n"] = d.get("stor_n", 0) + 1
        for r in load("VwsmTrdarFlpopQq", q):
            d = a(r["TRDAR_CD"])
            d["flpop_sum"] = d.get("flpop_sum", 0.0) + f(r["TOT_FLPOP_CO"])
            d["flpop_2030"] = d.get("flpop_2030", 0.0) + f(r["AGRDE_20_FLPOP_CO"]) + f(r["AGRDE_30_FLPOP_CO"])
            d["flpop_n"] = d.get("flpop_n", 0) + 1
        for r in load("VwsmTrdarWrcPopltnQq", q):
            d = a(r["TRDAR_CD"])
            d["wrc_sum"] = d.get("wrc_sum", 0.0) + f(r["TOT_WRC_POPLTN_CO"])
            d["wrc_n"] = d.get("wrc_n", 0) + 1
        for r in load("VwsmTrdarRepopQq", q):
            d = a(r["TRDAR_CD"])
            d["repop_sum"] = d.get("repop_sum", 0.0) + f(r["TOT_REPOP_CO"])
            d["repop_n"] = d.get("repop_n", 0) + 1
    # 상권변화지표: 기간 마지막 분기 값
    last = qs[-1]
    for r in load("VwsmTrdarIxQq", last):
        d = a(r["TRDAR_CD"])
        d["ix"] = r["TRDAR_CHNGE_IX"]
        d["ix_nm"] = r["TRDAR_CHNGE_IX_NM"]
        d["cls_months"] = f(r["CLS_SALE_MT_AVRG"])
        d["opr_months"] = f(r["OPR_SALE_MT_AVRG"])
    out = {}
    for cd, d in A.items():
        if len(d["_q"]) != 4:
            continue
        if not d.get("stor_n") or not d.get("flpop_n"):
            continue
        stores = d["stor_sum"] / d["stor_n"]
        if stores <= 0:
            continue
        e = {
            "sales": d["THSMON_SELNG_AMT"],
            "tx": d["THSMON_SELNG_CO"],
            "stores": stores,
            "frc_share": (d["frc_sum"] / d["stor_n"]) / stores,
            "open_rate": d["open"] / stores,
            "close_rate": d["close"] / stores,
            "flpop": d["flpop_sum"] / d["flpop_n"],
            "flpop_2030_share": d["flpop_2030"] / d["flpop_sum"] if d["flpop_sum"] else 0.0,
            "wrc": d.get("wrc_sum", 0.0) / d["wrc_n"] if d.get("wrc_n") else 0.0,
            "repop": d.get("repop_sum", 0.0) / d["repop_n"] if d.get("repop_n") else 0.0,
            "ix": d.get("ix", ""),
            "ix_nm": d.get("ix_nm", ""),
            "cls_months": d.get("cls_months", 0.0),
            "opr_months": d.get("opr_months", 0.0),
            "sales_2030_share": (d["AGRDE_20_SELNG_AMT"] + d["AGRDE_30_SELNG_AMT"]) / d["THSMON_SELNG_AMT"] if d["THSMON_SELNG_AMT"] else 0.0,
            "wkend_share": d["WKEND_SELNG_AMT"] / d["THSMON_SELNG_AMT"] if d["THSMON_SELNG_AMT"] else 0.0,
        }
        for k in ["TMZON_06_11_SELNG_CO", "TMZON_11_14_SELNG_CO", "TMZON_14_17_SELNG_CO",
                  "TMZON_17_21_SELNG_CO", "TMZON_21_24_SELNG_CO", "MDWK_SELNG_CO", "WKEND_SELNG_CO",
                  "ML_SELNG_AMT", "FML_SELNG_AMT"]:
            e[k] = d.get(k, 0.0)
        out[cd] = e
    return out


# ---------- 지표 정의 (MECE: 수요 / 공급 / 모멘텀 / 비용·리스크) ----------
# (코드, 이름, 분류, 기대부호, 설명)
FEATURES = [
    ("D1", "유동인구 규모(log)", "수요", +1, "ln(분기 평균 길단위 유동인구)"),
    ("D2", "20~30대 유동 비중", "수요", +1, "(20대+30대 유동인구)/전체 유동인구"),
    ("D3", "직장인구 규모(log)", "수요", +1, "ln(1+분기 평균 직장인구)"),
    ("S1", "커피점 밀도", "공급", -1, "커피-음료 점포 수 ÷ 유동인구 1만 명"),
    ("S2", "점포당 매출(log)", "공급", +1, "ln(커피 연매출 ÷ 평균 점포 수) — 높으면 공급 부족"),
    ("S3", "프랜차이즈 비중", "공급", -1, "프랜차이즈 점포 ÷ 전체 커피 점포"),
    ("M1", "커피 매출 1년 성장률", "모멘텀", +1, "ln(기준기간 매출 ÷ 전년 매출)"),
    ("M2", "유동인구 1년 성장률", "모멘텀", +1, "ln(기준기간 유동 ÷ 전년 유동)"),
    ("M3", "점포 수 1년 증감률", "모멘텀", +1, "ln(기준기간 점포 ÷ 전년 점포)"),
    ("R1", "커피점 폐업률", "비용·리스크", -1, "연간 폐업 점포 ÷ 평균 점포"),
    ("R2", "상권 매출 규모(log)", "비용·리스크", -1, "ln(커피 연매출) — 큰 상권일수록 임대료 부담·평균회귀"),
    ("R3", "폐업 점포 평균 영업개월", "비용·리스크", +1, "상권변화지표의 폐업 점포 평균 영업기간(개월), 길수록 생존 안정"),
]
FCODES = [x[0] for x in FEATURES]


def features(base, prev):
    rows = {}
    for cd, b in base.items():
        p = prev.get(cd)
        if not p or p["sales"] <= 0 or p["flpop"] <= 0 or p["stores"] <= 0:
            continue
        if b["sales"] <= 0 or b["flpop"] <= 0:
            continue
        rows[cd] = {
            "D1": math.log(b["flpop"]),
            "D2": b["flpop_2030_share"],
            "D3": math.log1p(b["wrc"]),
            "S1": b["stores"] / (b["flpop"] / 10000.0),
            "S2": math.log(b["sales"] / b["stores"]),
            "S3": b["frc_share"],
            "M1": math.log(b["sales"] / p["sales"]),
            "M2": math.log(b["flpop"] / p["flpop"]),
            "M3": math.log(b["stores"] / p["stores"]),
            "R1": b["close_rate"],
            "R2": math.log(b["sales"]),
            "R3": b["cls_months"],
        }
    return rows


def rank(a):
    a = np.asarray(a, float)
    order = a.argsort()
    r = np.empty(len(a))
    r[order] = np.arange(len(a))
    # 동점 평균 순위
    vals, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(vals))
    np.add.at(sums, inv, r)
    return sums[inv] / cnt[inv]


def spearman(x, y):
    return float(np.corrcoef(rank(x), rank(y))[0, 1])


def winsor_z(X, ref=None):
    """1~99% 윈저라이즈 후 z-score. ref가 있으면 그 분포로 표준화."""
    R = X if ref is None else ref
    lo = np.percentile(R, 1, axis=0)
    hi = np.percentile(R, 99, axis=0)
    Rc = np.clip(R, lo, hi)
    mu, sd = Rc.mean(0), Rc.std(0)
    sd[sd == 0] = 1
    return (np.clip(X, lo, hi) - mu) / sd


def ridge(X, y, lam=5.0):
    n, k = X.shape
    Xa = np.hstack([np.ones((n, 1)), X])
    I = np.eye(k + 1)
    I[0, 0] = 0
    return np.linalg.solve(Xa.T @ Xa + lam * I, Xa.T @ y)


def eval_score(score, target, sales):
    n = len(score)
    k10 = max(1, n // 10)
    top = np.argsort(-score)[:k10]
    q75 = np.percentile(target, 75)
    top_sales = np.argsort(-sales)[:k10]
    return {
        "spearman": round(spearman(score, target), 3),
        "top10pct_hit_rate": round(float((target[top] >= q75).mean()), 3),
        "base_rate": 0.25,
        "top10pct_mean_cagr": round(float(np.mean(np.exp(target[top]) - 1)), 4),
        "universe_mean_cagr": round(float(np.mean(np.exp(target) - 1)), 4),
        "sales_top10pct_mean_cagr": round(float(np.mean(np.exp(target[top_sales]) - 1)), 4),
        "n": n,
        "k": k10,
    }


def cagr_target(base, end, years):
    t = {}
    for cd, b in base.items():
        e = end.get(cd)
        if e and b["sales"] > 0 and e["sales"] > 0:
            t[cd] = math.log(e["sales"] / b["sales"]) / years
    return t


GROUP_W = {"수요": 0.25, "공급": 0.25, "모멘텀": 0.30, "비용·리스크": 0.20}


def make_weights(Z, y):
    """(a) 릿지 회귀 계수 (b) 전문가 사전(분류 비중×기대부호) (c) 전문가 비중×학습데이터 상관부호 (d) 최종=(a)와 (c) 50:50"""
    beta = ridge(Z, y)[1:]
    w_data = beta / np.abs(beta).sum()
    counts = {g: sum(1 for x in FEATURES if x[2] == g) for g in GROUP_W}
    mag = np.array([GROUP_W[x[2]] / counts[x[2]] for x in FEATURES])
    w_prior = mag * np.array([x[3] for x in FEATURES])
    sgn = np.sign([spearman(Z[:, i], y) for i in range(Z.shape[1])])
    w_fix = mag * sgn
    w_final = 0.5 * w_data + 0.5 * w_fix / np.abs(w_fix).sum()
    w_final = w_final / np.abs(w_final).sum()
    return {"data_ridge": w_data, "expert_prior": w_prior, "expert_signfix": w_fix, "final_blend": w_final}


MIN_SALES = 3e8  # 커피 연매출 3억 원 미만 상권은 기준 매출이 작아 성장률 잡음이 커서 제외


def build(base_key, prev_key, end_key=None, years=None):
    base, prev = period_agg(base_key), period_agg(prev_key)
    F = features(base, prev)
    T = cagr_target(base, period_agg(end_key), years) if end_key else {}
    cds = sorted(cd for cd in F if base[cd]["sales"] >= MIN_SALES and (not end_key or cd in T))
    X = np.array([[F[cd][c] for c in FCODES] for cd in cds])
    y = np.array([T[cd] for cd in cds]) if end_key else None
    sales = np.array([base[cd]["sales"] for cd in cds])
    return cds, X, y, sales, base


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main():
    meta = area_meta()
    res = {"features": [dict(zip(["code", "name", "group", "sign", "formula"], x)) for x in FEATURES]}

    # ---- 1) 백테스트 데이터: 2022 지표 → 2022→2025 CAGR ----
    cds, X, y, sales, base22 = build("2022", "2021", "2025", 3)
    Z = winsor_z(X)
    res["backtest_universe"] = {"n": len(cds), "min_sales_won": MIN_SALES,
                                "base": "2022(1~4Q)", "prev": "2021(1~4Q)", "target": "2022→2025 커피 추정매출 연평균 성장률(로그)"}

    # 단변량 상관
    uni = {c: round(spearman(Z[:, i], y), 3) for i, c in enumerate(FCODES)}
    res["univariate_spearman"] = uni

    # 상관행렬(중복 점검)
    C = np.corrcoef(Z.T)
    res["corr_matrix"] = {"codes": FCODES, "matrix": [[round(float(v), 2) for v in row] for row in C]}
    high = [(FCODES[i], FCODES[j], round(float(C[i, j]), 2)) for i in range(len(FCODES))
            for j in range(i + 1, len(FCODES)) if abs(C[i, j]) >= 0.8]
    res["high_corr_pairs"] = high
    write_csv(os.path.join(OUT, "corr_matrix_2022.csv"), [""] + FCODES,
              [[FCODES[i]] + [round(float(v), 3) for v in C[i]] for i in range(len(FCODES))])

    # 가중치 방식 3가지 — 모두 같은 5-fold 교차검증으로 표본외 성능 측정
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(cds))
    folds = np.array_split(idx, 5)
    cv = {k: np.zeros(len(cds)) for k in ["data_ridge", "expert_prior", "expert_signfix", "final_blend"]}
    for k in range(5):
        te = folds[k]
        tr = np.concatenate([folds[j] for j in range(5) if j != k])
        W = make_weights(Z[tr], y[tr])
        for name, w in W.items():
            cv[name][te] = Z[te] @ w
    W = make_weights(Z, y)
    w_final = W["final_blend"]
    res["backtest"] = {k: eval_score(v, y, sales) for k, v in cv.items()}
    res["backtest_note"] = "모든 방식은 5-fold CV 표본외 점수로 평가(가중치는 학습 fold에서만 추정)"
    res["weights"] = {c: {name: round(float(W[name][i]), 3) for name in W} for i, c in enumerate(FCODES)}

    # 시점 외 검증: 2022→2024(2년)로 가중치 학습 → 2024→TTM2026(약 1.5년)에 적용. 목표 기간이 겹치지 않음
    cdsA, XA, yA, _, _ = build("2022", "2021", "2024", 2)
    wA = make_weights(winsor_z(XA), yA)["final_blend"]
    cdsB, XB, yB, salesB, _ = build("2024", "2023", "TTM2026", 1.5)
    res["out_of_time"] = {"train": "2022 지표 → 2022→2024 성장", "test": "2024 지표 → 2024→2025Q3~2026Q2 성장",
                          **eval_score(winsor_z(XB) @ wA, yB, salesB)}

    # 점수 5분위별 실제 CAGR (계단형 확인)
    s = Z @ w_final
    qs = np.percentile(s, [20, 40, 60, 80])
    quint = np.digitize(s, qs)
    res["backtest_quintiles"] = [{"quintile": int(q) + 1,
                                  "mean_cagr": round(float(np.mean(np.exp(y[quint == q]) - 1)), 4),
                                  "n": int((quint == q).sum())} for q in range(5)]

    # 매출 상위 10 vs 점수 상위 10 (히어로 인사이트 후보)
    top_sales = np.argsort(-sales)[:10]
    top_score = np.argsort(-s)[:10]
    res["top10_compare_2022"] = {
        "sales_top10": [{"cd": cds[i], "name": meta.get(cds[i], {}).get("TRDAR_CD_NM", ""), "sales_2022": sales[i],
                         "cagr_22_25": round(float(math.exp(y[i]) - 1), 4)} for i in top_sales],
        "score_top10": [{"cd": cds[i], "name": meta.get(cds[i], {}).get("TRDAR_CD_NM", ""), "sales_2022": sales[i],
                         "cagr_22_25": round(float(math.exp(y[i]) - 1), 4)} for i in top_score],
    }
    write_csv(os.path.join(OUT, "backtest_2022_2025.csv"),
              ["TRDAR_CD", "상권명", "자치구", "구분"] + FCODES + ["score_final", "cv_pred", "actual_cagr_22_25", "sales_2022"],
              [[cd, meta.get(cd, {}).get("TRDAR_CD_NM", ""), meta.get(cd, {}).get("SIGNGU_CD_NM", ""),
                meta.get(cd, {}).get("TRDAR_SE_CD_NM", "")] + [round(float(v), 5) for v in X[i]] +
               [round(float(s[i]), 4), round(float(cv["final_blend"][i]), 4), round(float(math.exp(y[i]) - 1), 4), int(sales[i])]
               for i, cd in enumerate(cds)])

    # ---- 2) 안정성 점검: 같은 가중치, 2023 지표 → 2023→2025 (2년) ----
    cds3, X3, y3, sales3, _ = build("2023", "2022", "2025", 2)
    Z3 = winsor_z(X3)
    res["stability_2023_2025"] = eval_score(Z3 @ w_final, y3, sales3)

    # ---- 3) 현재 점수: TTM 2025Q3~2026Q2, 전년 TTM ----
    cdsN, XN, _, salesN, baseN = build("TTM2026", "TTM2025")
    ZN = winsor_z(XN)
    sN = ZN @ w_final
    # 점수 → 예상 CAGR: 백테스트 표본에서 score와 실제 CAGR의 선형관계
    a1, a0 = np.polyfit(s, y, 1)
    predN = a0 + a1 * sN
    res["score_to_cagr"] = {"slope": round(float(a1), 4), "intercept": round(float(a0), 4)}
    order = np.argsort(-sN)
    rows = []
    for rk, i in enumerate(order, 1):
        cd = cdsN[i]
        m = meta.get(cd, {})
        b = baseN[cd]
        rows.append([rk, cd, m.get("TRDAR_CD_NM", ""), m.get("SIGNGU_CD_NM", ""), m.get("ADSTRD_CD_NM", ""),
                     m.get("TRDAR_SE_CD_NM", ""), round(float(sN[i]), 4), round(float(math.exp(predN[i]) - 1), 4),
                     int(b["sales"]), round(b["stores"], 1), int(b["flpop"]), round(b["flpop_2030_share"], 3),
                     int(b["wrc"]), b["ix_nm"], m.get("XCNTS_VALUE", ""), m.get("YDNTS_VALUE", "")] +
                    [round(float(v), 5) for v in XN[i]] + [round(float(v), 3) for v in ZN[i]])
    write_csv(os.path.join(OUT, "scores_current.csv"),
              ["rank", "TRDAR_CD", "상권명", "자치구", "행정동", "구분", "score", "pred_cagr", "sales_ttm",
               "stores", "flpop_q", "flpop_2030", "wrc", "변화지표", "x", "y"] + FCODES + ["z_" + c for c in FCODES],
              rows)
    res["current_universe"] = {"n": len(cdsN), "base": "2025Q3~2026Q2", "prev": "2024Q3~2025Q2"}
    res["current_top10"] = [dict(zip(["rank", "cd", "name", "gu", "dong", "type", "score", "pred_cagr", "sales_ttm",
                                      "stores", "flpop_q", "flpop_2030", "wrc", "ix"], r[:14])) for r in rows[:10]]
    with open(os.path.join(OUT, "backtest.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: res[k] for k in ["backtest_universe", "univariate_spearman", "high_corr_pairs", "weights",
                                         "backtest", "backtest_quintiles", "stability_2023_2025", "out_of_time",
                                         "current_universe", "top10_compare_2022"]},
                     ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
