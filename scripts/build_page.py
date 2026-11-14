"""docs/index.html 생성. 본문 숫자 각주 [E..] → 하단 출처표(evidence.csv)와 연결.

사용: python scripts/build_page.py
"""
import csv
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "processed")
ev = list(csv.DictReader(open(os.path.join(ROOT, "shared", "evidence.csv"), encoding="utf-8-sig")))
bt = json.load(open(os.path.join(P, "backtest.json"), encoding="utf-8"))
pnl = json.load(open(os.path.join(P, "pnl.json"), encoding="utf-8"))
fun = json.load(open(os.path.join(P, "funnel.json"), encoding="utf-8"))


def r(*ids):
    return "".join(f'<a class="fn" href="#{i}">{i}</a>' for i in ids)


SRC_OA = "서울시 상권분석서비스(OA-15572·15577·15568·15569·15576)"

# ---- 지표 표 ----
feat_rows = ""
for f in bt["features"]:
    w = bt["weights"][f["code"]]
    feat_rows += (f"<tr><td>{f['code']}</td><td>{f['group']}</td><td>{html.escape(f['name'])}</td>"
                  f"<td class='l'>{html.escape(f['formula'])}</td><td>{'+' if f['sign'] > 0 else '−'}</td>"
                  f"<td>{bt['univariate_spearman'][f['code']]:+.3f}</td><td><b>{w['final_blend']:+.3f}</b></td></tr>")

# ---- 백테스트 표 ----
names = {"data_ridge": "(a) 데이터 릿지", "expert_prior": "(b) 전문가 사전", "expert_signfix": "(c) 전문가 부호보정",
         "final_blend": "(d) 최종 = a50%+c50%"}
bt_rows = ""
for k, v in bt["backtest"].items():
    cls = " class='hl'" if k == "final_blend" else ""
    bt_rows += (f"<tr{cls}><td class='l'>{names[k]}</td><td>{v['spearman']:.3f}</td><td>{v['top10pct_hit_rate']*100:.1f}%</td>"
                f"<td>{v['top10pct_mean_cagr']*100:+.2f}%</td></tr>")

# ---- 5분위 SVG ----
# 층 분리: 값 라벨(막대 끝) / 축 라벨 Q1~Q5 (y=188) / 점수 낮음·높음 (y=206)
q = [x["mean_cagr"] * 100 for x in bt["backtest_quintiles"]]
ZERO, K = 84, 11  # 기준선 y, 1%p당 px
qsvg = '<svg viewBox="0 0 360 214" role="img" aria-label="점수 5분위별 실제 3년 CAGR">'
qsvg += f'<line x1="20" y1="{ZERO}" x2="350" y2="{ZERO}" class="ax"/><text x="16" y="{ZERO+4}" text-anchor="end" class="tk">0</text>'
for i, v in enumerate(q):
    x = 40 + i * 62
    h = abs(v) * K
    y = ZERO - h if v > 0 else ZERO
    qsvg += f'<rect x="{x}" y="{y:.1f}" width="40" height="{h:.1f}" class="{"pos" if v > 0 else "neg"}"/>'
    ly = (y - 6) if v > 0 else (ZERO + h + 14)
    qsvg += f'<text x="{x+20}" y="{ly:.1f}" text-anchor="middle" class="lbl">{v:+.1f}%</text>'
    qsvg += f'<text x="{x+20}" y="188" text-anchor="middle" class="tk">Q{i+1}</text>'
qsvg += '<line x1="40" y1="198" x2="328" y2="198" class="ax" stroke-dasharray="2 3"/>'
qsvg += '<text x="40" y="210" class="tk">← 점수 낮음</text><text x="328" y="210" text-anchor="end" class="tk">점수 높음 →</text></svg>'

# ---- 상권 비교(Top 3 + 참고) ----
prof = json.load(open(os.path.join(P, "profile.json"), encoding="utf-8"))["areas"]
cmp_rows = ""
for cd, rank, catalyst in [("3001496", 6, "GTX-A 삼성역 2028 하반기 " + r("E40")), ("3001494", 8, "2029 이전 확정 교통 호재 미확인"),
                           ("3001495", 10, "MICE 파크 2032 준공 " + r("E45"))]:
    a = prof[cd]
    cmp_rows += (f"<tr{' class=hl' if cd=='3001496' else ''}><td class='l'>{a['name']}</td><td>{rank}</td>"
                 f"<td>{a['sales_ttm_won']/1e8:,.0f}억</td><td>{(a['sales_ttm_won']/a['sales_2022_won']-1)*100:+.0f}%</td>"
                 f"<td>{a['stores_avg']:.0f}</td><td>{a['sales_per_store_won']/1e8:.2f}억</td><td>{a['ticket_won']:,}원</td>"
                 f"<td class='l'>{catalyst}</td></tr>")

# ---- 손익 표 ----
sc = pnl["scenarios"]
def eok(x):
    return f"{x/1e8:.2f}억"
pl_items = [("일 거래건수", "tx_day", lambda x: f"{x}건"), ("객단가", "ticket", lambda x: f"{x:,}원"), ("매출", "revenue", eok),
            ("매출원가 29%", "cogs", eok), ("인건비", "labor", eok), ("임대료+관리비", "rent", eok), ("본사 관리비 3%", "hq", eok),
            ("기타 운영비 7%", "other", eok), ("감가상각", "dep", eok), ("영업이익", "op", eok),
            ("영업이익률", "op_margin", lambda x: f"{x*100:.1f}%"), ("초기 투자", "invest", eok),
            ("투자회수기간", "payback_years", lambda x: f"{x}년" if x else "회수 불가"), ("손익분기 일 거래", "breakeven_tx_day", lambda x: f"{x}건")]
pl_rows = ""
for lab, k, fmt in pl_items:
    b = " class='hl'" if k in ("revenue", "op", "op_margin", "payback_years") else ""
    pl_rows += f"<tr{b}><td class='l'>{lab}</td>" + "".join(f"<td>{fmt(sc[s][k])}</td>" for s in ["bear", "base", "bull"]) + "</tr>"

sens = {(x["var"], x["delta"]): x for x in pnl["sensitivity"]}
sens_rows = ""
for var, lab in [("tx", "객수"), ("ticket", "객단가"), ("rent", "임대료")]:
    sens_rows += f"<tr><td class='l'>{lab}</td>" + "".join(
        f"<td>{sens[(var, d)]['op_margin']*100:.1f}%</td>" for d in [-0.2, -0.1, 0.1, 0.2]) + "</tr>"

# ---- 출처표 ----
src_rows = ""
for e in ev:
    url = e["source_url"]
    link = f'<a href="{html.escape(url)}" rel="noopener" target="_blank">{html.escape(e["source_name"])}</a>' if url.startswith("http") else html.escape(e["source_name"] + " · " + url)
    src_rows += (f"<tr id='{e['id']}'><td>{e['id']}</td><td class='l'>{html.escape(e['claim'])}</td><td>{html.escape(str(e['value']))}</td>"
                 f"<td>{html.escape(e['unit'])}</td><td>{html.escape(e['period'])}</td><td class='l'>{link}</td><td>{e['verified']}</td></tr>")


# ---- 히어로: 2022 매출 상위 66곳 역성장 격자 ----
_bt = sorted(csv.DictReader(open(os.path.join(P, "backtest_2022_2025.csv"), encoding="utf-8-sig")), key=lambda r: -float(r["sales_2022"]))[:66]
gsvg = '<svg viewBox="0 0 242 134" role="img" aria-label="2022 매출 상위 66곳 중 3년 뒤 역성장 상권">'
for i, rr in enumerate(_bt):
    neg = float(rr["actual_cagr_22_25"]) < 0
    gsvg += f'<rect x="{(i%11)*22}" y="{(i//11)*22}" width="18" height="18" class="{"neg" if neg else "pos"}"><title>{html.escape(rr["상권명"])} {float(rr["actual_cagr_22_25"])*100:+.1f}%/년</title></rect>'
gsvg += "</svg>"
page = open(os.path.join(ROOT, "scripts", "page_template.html"), encoding="utf-8").read()
page = (page.replace("{{FEAT_ROWS}}", feat_rows).replace("{{BT_ROWS}}", bt_rows).replace("{{QSVG}}", qsvg)
        .replace("{{CMP_ROWS}}", cmp_rows).replace("{{PL_ROWS}}", pl_rows).replace("{{SENS_ROWS}}", sens_rows)
        .replace("{{SRC_ROWS}}", src_rows).replace("{{SRC_OA}}", SRC_OA).replace("{{GRID}}", gsvg).replace("{{N_EV}}", str(len(ev)))
        .replace("{{N_Y}}", str(sum(1 for e in ev if e["verified"] == "Y"))))
page = re.sub(r"\[\[(E\d\d(?:,E\d\d)*)\]\]", lambda m: r(*m.group(1).split(",")), page)
missing = sorted(set(re.findall(r'href="#(E\d\d)"', page)) - {e["id"] for e in ev})
open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8").write(page)
print("written; footnote ids missing from evidence:", missing)
