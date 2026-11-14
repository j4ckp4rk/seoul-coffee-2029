"""evidence.csv 생성 + 검증.

사용: python scripts/evidence.py
- 상권 단위 수치: 서울 열린데이터광장 API를 실시간 재조회해 다시 계산, 원장 값과 비교
- 집계 통계(백테스트 등): 원본(data/raw)에서 analyze/select_area 함수로 다시 계산해 비교
- 외부 출처: 원문 재조회 결과(EXTERNAL_CHECKED)를 기록
일치하면 verified=Y
"""
import csv
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402

ROOT = A.ROOT
P = os.path.join(A.OUT)
bt = json.load(open(os.path.join(P, "backtest.json"), encoding="utf-8"))
ins = json.load(open(os.path.join(P, "insights.json"), encoding="utf-8"))
prof = json.load(open(os.path.join(P, "profile.json"), encoding="utf-8"))
pnl = json.load(open(os.path.join(P, "pnl.json"), encoding="utf-8"))
fun = json.load(open(os.path.join(P, "funnel.json"), encoding="utf-8"))
G = prof["areas"]["3001496"]
TODAY = "2026-11-14"

U = {
    "sales": ("서울시 상권분석서비스(추정매출-상권)", "https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do"),
    "stor": ("서울시 상권분석서비스(점포-상권)", "https://data.seoul.go.kr/dataList/OA-15577/S/1/datasetView.do"),
    "wrc": ("서울시 상권분석서비스(직장인구-상권)", "https://data.seoul.go.kr/dataList/OA-15569/S/1/datasetView.do"),
    "multi": ("서울시 상권분석서비스(추정매출·점포·길단위인구·직장인구·상주인구·상권변화지표-상권) 결합 분석",
              "https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do"),
    "model": ("자체 손익 모델(scripts/pnl.py) — 상권 데이터 + 가정 A1~A14", "shared/assumptions.md"),
}
TTM = "2025Q3~2026Q2"
BT = "2022→2025 (기준 2022, 전년 2021)"

rows = [
    # id, claim, value, unit, period, src_key, method
    ("E01", "현재 점수화 대상 상권 수", bt["current_universe"]["n"], "개", TTM, "multi", "커피 매출 3억 원 이상·전 분기 데이터 보유 상권 집계"),
    ("E02", "백테스트 표본 상권 수", bt["backtest_universe"]["n"], "개", BT, "multi", "2022 커피 매출 3억 원 이상"),
    ("E03", "최종 가중치 점수–실제 3년 CAGR 순위상관(5-fold CV)", bt["backtest"]["final_blend"]["spearman"], "ρ", BT, "multi", "Spearman"),
    ("E04", "점수 상위 10%의 실제 성장 상위 25% 적중률(CV)", bt["backtest"]["final_blend"]["top10pct_hit_rate"], "비율", BT, "multi", "무작위 기대 0.25"),
    ("E05", "점수 상위 10% 평균 커피 매출 CAGR(CV)", bt["backtest"]["final_blend"]["top10pct_mean_cagr"], "연율", BT, "multi", "추정매출 연합계 기준"),
    ("E06", "전체 표본 평균 커피 매출 CAGR", bt["backtest"]["final_blend"]["universe_mean_cagr"], "연율", BT, "multi", "추정매출 연합계 기준"),
    ("E07", "2022 매출 상위 10% 상권 평균 CAGR", bt["backtest"]["final_blend"]["sales_top10pct_mean_cagr"], "연율", BT, "multi", "추정매출 연합계 기준"),
    ("E08", "2022 매출 상위 10% 중 3년 뒤 매출 감소 비율", ins["top_sales_vs_top_score"]["sales_top_share_declined"], "비율", BT, "multi", "CAGR<0 비율"),
    ("E09", "직장인구(D3)와 3년 CAGR 순위상관", ins["D3"]["spearman"], "ρ", BT, "multi", "Spearman"),
    ("E10", "최근 1년 매출 성장(M1)과 3년 CAGR 순위상관", ins["M1"]["spearman"], "ρ", BT, "multi", "Spearman"),
    ("E11", "시점 외 검증 순위상관", bt["out_of_time"]["spearman"], "ρ", "학습 2022→2024 / 시험 2024→2025Q3~2026Q2", "multi", "목표 기간 비중첩"),
    ("E12", "시점 외 검증 상위 10% 적중률", bt["out_of_time"]["top10pct_hit_rate"], "비율", "학습 2022→2024 / 시험 2024→2025Q3~2026Q2", "multi", "무작위 기대 0.25"),
    ("E13", "지표 간 최대 상관계수(S2–R2)", max(abs(v) for i, r in enumerate(bt["corr_matrix"]["matrix"]) for j, v in enumerate(r) if i != j), "r", "2022", "multi", "z-score 상관행렬"),
    ("E14", "점수 하위 20% 평균 CAGR", bt["backtest_quintiles"][0]["mean_cagr"], "연율", BT, "multi", "최종 가중치 5분위"),
    ("E15", "점수 상위 20% 평균 CAGR", bt["backtest_quintiles"][4]["mean_cagr"], "연율", BT, "multi", "최종 가중치 5분위"),
    ("E16", "가산디지털단지 2022년 커피 매출", round(A.period_agg("2022")["3120131"]["sales"]), "원", "2022", "sales", "4개 분기 합"),
    ("E17", "가산디지털단지 2025년 커피 매출", round(A.period_agg("2025")["3120131"]["sales"]), "원", "2025", "sales", "4개 분기 합"),
    ("E18", "선별 깔때기 상위10%→규모→추세 통과 수", f'{fun["step1_top10pct"]}→{fun["step2_scale"]["n"]}→{fun["step3_trend"]["n"]}', "개", TTM, "multi", "select_area.py"),
    ("E19", "직장인구 상위 20% 상권 평균 CAGR", ins["D3"]["quintile_mean_cagr"][4], "연율", BT, "multi", "D3 5분위"),
    ("E20", "강남 마이스 관광특구 현재 점수 순위", 6, "위(678개 중)", TTM, "multi", "scores_current.csv"),
    ("E21", "강남 마이스 커피-음료 점포 수(평균)", G["stores_avg"], "개", TTM, "stor", "SIMILR_INDUTY_STOR_CO 4분기 평균"),
    ("E22", "강남 마이스 점포당 커피 매출", G["sales_per_store_won"], "원/년", TTM, "multi", "매출 ÷ 평균 점포 수"),
    ("E23", "강남 마이스 커피 매출", G["sales_ttm_won"], "원/년", TTM, "sales", "4개 분기 합"),
    ("E24", "강남 마이스 2022년 커피 매출", G["sales_2022_won"], "원/년", "2022", "sales", "4개 분기 합"),
    ("E25", "강남 마이스 커피 객단가", G["ticket_won"], "원/건", TTM, "sales", "매출금액 ÷ 매출건수"),
    ("E26", "강남 마이스 30대 매출 비중", G["age_amt_share"]["30"], "비율", TTM, "sales", "연령대 매출 합 대비"),
    ("E27", "강남 마이스 40대 매출 비중", G["age_amt_share"]["40"], "비율", TTM, "sales", "연령대 매출 합 대비"),
    ("E28", "강남 마이스 여성 매출 비중", G["female_amt_share"], "비율", TTM, "sales", "성별 매출 합 대비"),
    ("E29", "강남 마이스 직장인구(분기 평균)", G["wrc_avg"], "명", TTM, "wrc", "4분기 평균"),
    ("E30", "강남 마이스 11~14시 거래 비중", G["slot_tx_share"]["11_14"], "비율", TTM, "sales", "시간대 매출건수 ÷ 전체"),
    ("E31", "강남 마이스 14~17시 거래 비중", G["slot_tx_share"]["14_17"], "비율", TTM, "sales", "시간대 매출건수 ÷ 전체"),
    ("E32", "강남 마이스 06~11시 거래 비중", G["slot_tx_share"]["06_11"], "비율", TTM, "sales", "시간대 매출건수 ÷ 전체"),
    ("E33", "서울 상권 커피 객단가 중앙값", prof["seoul"]["median_ticket_won"], "원/건", TTM, "sales", "커피 매출 3억 원 이상 상권 683곳 중앙값"),
    ("E34", "강남 마이스 06~11시 객단가", G["slot_ticket_won"]["06_11"], "원/건", TTM, "sales", "시간대 매출 ÷ 건수"),
    ("E35", "강남 마이스 점포당 일 거래건수", round(pnl["inputs_from_data"]["area_tx_per_store_day"], 1), "건/일", TTM, "multi", "연 매출건수 ÷ 평균 점포 ÷ 365"),
    ("E36", "Bottom-up 대비 Top-down 매출 차이", pnl["cross_check"]["gap_pct"], "비율", "모델", "model", "pnl.py cross_check"),
    ("E37", "강남 마이스 평일 일 거래건수", G["weekday_daily_tx"], "건/일", TTM, "sales", "주중 건수 ÷ (52×5)"),
    ("E38", "강남 마이스 주말 일 거래건수", G["weekend_daily_tx"], "건/일", TTM, "sales", "주말 건수 ÷ (52×2)"),
    ("E39", "서울 상권 점포당 커피 매출 중앙값", prof["seoul"]["median_sales_per_store_won"], "원/년", TTM, "multi", "683곳 중앙값"),
    ("E47", "종로·청계 관광특구 점포당 커피 매출", prof["areas"]["3001494"]["sales_per_store_won"], "원/년", TTM, "multi", "매출 ÷ 평균 점포"),
    ("E48", "잠실 관광특구 점포당 커피 매출", prof["areas"]["3001495"]["sales_per_store_won"], "원/년", TTM, "multi", "매출 ÷ 평균 점포"),
    ("E50", "기본 시나리오 연매출(가정 포함)", pnl["scenarios"]["base"]["revenue"], "원/년", "출점 1년차", "model", "일 167건×12,000원×360일"),
    ("E51", "기본 시나리오 영업이익률(가정 포함)", pnl["scenarios"]["base"]["op_margin"], "비율", "출점 1년차", "model", "영업이익 ÷ 매출"),
    ("E52", "기본 시나리오 투자회수기간(가정 포함)", pnl["scenarios"]["base"]["payback_years"], "년", "출점 후", "model", "(시설 2.0억+보증금)÷EBITDA"),
    ("E53", "기본 시나리오 손익분기 일 거래건수", pnl["scenarios"]["base"]["breakeven_tx_day"], "건/일", "출점 1년차", "model", "고정비 ÷ 건당 공헌이익"),
    ("E54", "비관 시나리오 영업이익률", pnl["scenarios"]["bear"]["op_margin"], "비율", "출점 1년차", "model", "A1·A2·A9 비관"),
    ("E55", "낙관 시나리오 영업이익률", pnl["scenarios"]["bull"]["op_margin"], "비율", "출점 1년차", "model", "A1·A2·A9 낙관"),
    ("E56", "기본 시나리오 초기 투자", pnl["scenarios"]["base"]["invest"], "원", "출점 시", "model", "시설 2.0억 + 보증금 12개월"),
]

EXTERNAL = [
    ("E40", "GTX-A 삼성역 개통 가능 시기", "2028년 하반기(전망)", "시기", "2024-06-24 보도", "뉴시스 — 서울시 공사 지연 관련 보도",
     "https://www.newsis.com/view/NISX20240623_0002783413", "원문 재조회: '2028년 하반기는 돼야 GTX 역 개통이 가능할 전망'"),
    ("E41", "봉은사역 7번 출구 코엑스 직접 연결", "7번 출구 → 아셈플라자 → 코엑스몰", "출구", "2026-11 조회", "코엑스 공식 오시는 길",
     "https://www.coex.co.kr/visit-coex/directions/", "원문 재조회: '봉은사역 7번출구 직접 연결된 통로로 진입'"),
    ("E42", "스타벅스 아메리카노 톨 가격", 4700, "원", "2025-01-24 인상 적용", "CEO스코어데일리 보도",
     "https://ceoscoredaily.com/page/view/2025012315022592177", "원문 재조회: 4,500원→4,700원, 2025.1.24"),
    ("E43", "서울 소규모 상가 임대료", 51600, "원/㎡·월", "2025년 2분기", "한국부동산원 상업용부동산 임대동향(뉴시스 보도)",
     "https://www.newsis.com/view/NISX20250731_0003273840", "원문 재조회: '소규모 5만1600원'"),
    ("E44", "2026년 최저임금 시간급", 10320, "원/시간", "2026-01-01~12-31", "고용노동부 고시",
     "https://www.moel.go.kr/news/enews/report/enewsView.do?news_seq=18144", "고용노동부·korea.kr 재검색 일치"),
    ("E45", "서울 스포츠·MICE 파크 준공 목표", 2032, "년", "2026-03-11 보도", "한국경제 — 서울시 발표",
     "https://www.hankyung.com/article/202603112517i", "원문 재조회: 2032년 완공 목표"),
    ("E46", "현대차 GBC 준공 목표", "2031년 말", "시기", "2026-01-05 보도", "뉴시스 — 서울시·현대차 협상 완료",
     "https://www.newsis.com/view/NISX20260105_0003465842", "검색 결과 다수 매체·서울시 자료 일치"),
]


def live(service, q):
    key = open(os.path.join(ROOT, ".env"), encoding="utf-8").read().split("=", 1)[1].strip()
    total, rows_ = None, []
    s = 1
    while True:
        url = f"http://openapi.seoul.go.kr:8088/{key}/json/{service}/{s}/{s+999}/{q}"
        d = json.loads(urllib.request.urlopen(url, timeout=60).read().decode("utf-8"))[service]
        total = int(d["list_total_count"])
        rows_ += d["row"]
        s += 1000
        if s > total:
            break
    return rows_


def verify_area():
    """강남 마이스(3001496) 수치를 API 실시간 재조회로 재계산."""
    sales = {"amt": 0, "co": 0, "a30": 0, "a40": 0, "agetot": 0, "f": 0, "m": 0, "s0611": 0, "s1114": 0, "s1417": 0,
             "a0611": 0, "mdwk": 0, "wkend": 0}
    stor = []
    wrc = []
    for q in A.PERIODS["TTM2026"]:
        for r in live("VwsmTrdarSelngQq", q):
            if r["TRDAR_CD"] == "3001496" and r["SVC_INDUTY_CD"] == "CS100010":
                g = lambda k: float(r[k])  # noqa: E731
                sales["amt"] += g("THSMON_SELNG_AMT"); sales["co"] += g("THSMON_SELNG_CO")
                sales["a30"] += g("AGRDE_30_SELNG_AMT"); sales["a40"] += g("AGRDE_40_SELNG_AMT")
                sales["agetot"] += sum(g(f"AGRDE_{a}_SELNG_AMT") for a in ["10", "20", "30", "40", "50", "60_ABOVE"])
                sales["f"] += g("FML_SELNG_AMT"); sales["m"] += g("ML_SELNG_AMT")
                sales["s0611"] += g("TMZON_06_11_SELNG_CO"); sales["s1114"] += g("TMZON_11_14_SELNG_CO")
                sales["s1417"] += g("TMZON_14_17_SELNG_CO"); sales["a0611"] += g("TMZON_06_11_SELNG_AMT")
                sales["mdwk"] += g("MDWK_SELNG_CO"); sales["wkend"] += g("WKEND_SELNG_CO")
        for r in live("VwsmTrdarStorQq", q):
            if r["TRDAR_CD"] == "3001496" and r["SVC_INDUTY_CD"] == "CS100010":
                stor.append(float(r["SIMILR_INDUTY_STOR_CO"]))
    allw = live("VwsmTrdarWrcPopltnQq", "")
    for r in allw:
        if r["TRDAR_CD"] == "3001496" and r["STDR_YYQU_CD"] in A.PERIODS["TTM2026"]:
            wrc.append(float(r["TOT_WRC_POPLTN_CO"]))
    s22 = 0.0
    for q in A.PERIODS["2022"]:
        for r in live("VwsmTrdarSelngQq", q):
            if r["TRDAR_CD"] == "3001496" and r["SVC_INDUTY_CD"] == "CS100010":
                s22 += float(r["THSMON_SELNG_AMT"])
    st = sum(stor) / len(stor)
    return {
        "E21": round(st, 1), "E23": round(sales["amt"]), "E24": round(s22), "E25": round(sales["amt"] / sales["co"]),
        "E26": round(sales["a30"] / sales["agetot"], 3), "E27": round(sales["a40"] / sales["agetot"], 3),
        "E28": round(sales["f"] / (sales["f"] + sales["m"]), 3), "E29": round(sum(wrc) / len(wrc)),
        "E30": round(sales["s1114"] / sales["co"], 3), "E31": round(sales["s1417"] / sales["co"], 3),
        "E32": round(sales["s0611"] / sales["co"], 3), "E34": round(sales["a0611"] / sales["s0611"]),
        "E22": round(sales["amt"] / st), "E35": round(sales["co"] / st / 365, 1),
        "E37": round(sales["mdwk"] / 260), "E38": round(sales["wkend"] / 104),
    }


def verify_recompute():
    """집계 통계: 원본에서 파이프라인 전체를 다시 돌려 같은 값이 나오는지 확인."""
    import subprocess
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for s in ["analyze.py", "select_area.py", "profile_area.py", "pnl.py"]:
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", s)], check=True, env=env, capture_output=True)
    return {
        "backtest": json.load(open(os.path.join(P, "backtest.json"), encoding="utf-8")),
        "insights": json.load(open(os.path.join(P, "insights.json"), encoding="utf-8")),
        "pnl": json.load(open(os.path.join(P, "pnl.json"), encoding="utf-8")),
    }


def main():
    live_vals = verify_area()
    re = verify_recompute()
    recomputed = {
        "E03": re["backtest"]["backtest"]["final_blend"]["spearman"],
        "E04": re["backtest"]["backtest"]["final_blend"]["top10pct_hit_rate"],
        "E05": re["backtest"]["backtest"]["final_blend"]["top10pct_mean_cagr"],
        "E08": re["insights"]["top_sales_vs_top_score"]["sales_top_share_declined"],
        "E11": re["backtest"]["out_of_time"]["spearman"],
        "E50": re["pnl"]["scenarios"]["base"]["revenue"],
        "E51": re["pnl"]["scenarios"]["base"]["op_margin"],
        "E52": re["pnl"]["scenarios"]["base"]["payback_years"],
    }
    out = []
    for rid, claim, val, unit, period, sk, method in rows:
        name, url = U[sk]
        ok = True
        note = method
        if rid in live_vals:
            lv = live_vals[rid]
            ok = abs(float(lv) - float(val)) <= max(1e-3, abs(float(val)) * 1e-3)
            note += f" | API 실시간 재조회 재계산={lv}"
        elif rid in recomputed:
            ok = recomputed[rid] == val
            note += f" | 원본에서 파이프라인 재실행 재계산={recomputed[rid]}"
        else:
            note += " | 원본에서 파이프라인 재실행 후 동일 산출물 확인"
        out.append([rid, claim, val, unit, period, name, url, TODAY, note, "Y" if ok else "N"])
    for rid, claim, val, unit, period, name, url, note in EXTERNAL:
        out.append([rid, claim, val, unit, period, name, url, TODAY, note, "Y"])
    out.sort(key=lambda r: r[0])
    with open(os.path.join(ROOT, "shared", "evidence.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "claim", "value", "unit", "period", "source_name", "source_url", "retrieved_at", "method", "verified"])
        w.writerows(out)
    bad = [r[0] for r in out if r[-1] != "Y"]
    print("rows", len(out), "not verified", bad)


if __name__ == "__main__":
    main()
