"""모션 픽셀 피치 영상 (메인): 문장마다 그 주장을 증명하는 데이터 애니메이션.

- 내레이션·TTS·게임 보이스는 make_video_retro.py의 SCENES 그대로 (길이 동일)
- 480x270 픽셀 캔버스, 12fps 계단식 애니메이션 → 1920x1080 nearest 확대
- 모든 화면에 출처·기간 태그
사용: python scripts/make_video_motion.py [--preview]
출력: docs/video/pitch.mp4, docs/video/script.md, docs/assets/poster.png
"""
import csv
import json
import math
import os
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402
import make_video_retro as R  # noqa: E402

ROOT, VID, FF = R.ROOT, R.VID, R.FF
TMP = os.path.join(ROOT, "data", "video_tmp", "motion")
os.makedirs(TMP, exist_ok=True)
P = os.path.join(ROOT, "data", "processed")
W, H, S, FPS = 480, 270, 4, 12
BOLD, REG = "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"

BG, PANEL, LINE, DARK = "#141a2e", "#1e2642", "#2e3860", "#0e1322"
TXT, MUTED, FAINT = "#f4efe6", "#9aa1ba", "#4a5378"
AMBER, MINT, CORAL, BLUE = "#f2a541", "#5fd3a8", "#ef6f6c", "#5aa9ff"
STAGES = ["결론", "왜 여기", "타깃·공간·메뉴", "손익", "요청"]
SRC_SALES = "출처: 서울시 상권분석서비스 추정매출(OA-15572)"

# ---------------- 데이터 ----------------
bt = json.load(open(os.path.join(P, "backtest.json"), encoding="utf-8"))
ins = json.load(open(os.path.join(P, "insights.json"), encoding="utf-8"))
prof = json.load(open(os.path.join(P, "profile.json"), encoding="utf-8"))
pnlj = json.load(open(os.path.join(P, "pnl.json"), encoding="utf-8"))
G = prof["areas"]["3001496"]
scores = list(csv.DictReader(open(os.path.join(P, "scores_current.csv"), encoding="utf-8-sig")))
relm = list(csv.DictReader(open(os.path.join(ROOT, "data", "raw", "TbgisTrdarRelm", "all.csv"), encoding="utf-8-sig")))
btrows = list(csv.DictReader(open(os.path.join(P, "backtest_2022_2025.csv"), encoding="utf-8-sig")))

XS = [float(r["XCNTS_VALUE"]) for r in relm]
YS = [float(r["YDNTS_VALUE"]) for r in relm]
X0, X1, Y0, Y1 = min(XS), max(XS), min(YS), max(YS)


def proj(x, y, box):
    bx0, by0, bx1, by1 = box
    sc = min((bx1 - bx0) / (X1 - X0), (by1 - by0) / (Y1 - Y0))
    ox = bx0 + ((bx1 - bx0) - (X1 - X0) * sc) / 2
    oy = by0 + ((by1 - by0) - (Y1 - Y0) * sc) / 2
    return ox + (x - X0) * sc, oy + (Y1 - y) * sc


QS = [f"{y}{q}" for y in range(2021, 2027) for q in range(1, 5) if f"{y}{q}" <= "20262"]


def series(cd):
    out = []
    for q in QS:
        v = sum(A.f(r["THSMON_SELNG_AMT"]) for r in A.load("VwsmTrdarSelngQq", q)
                if r["TRDAR_CD"] == cd and r["SVC_INDUTY_CD"] == A.COFFEE)
        out.append(v / 1e8)
    return out


SER_G, SER_K = series("3001496"), series("3120131")  # 강남 마이스, 가산디지털단지
top66 = sorted(btrows, key=lambda r: -float(r["sales_2022"]))[:66]
DECL = [float(r["actual_cagr_22_25"]) < 0 for r in top66]

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import pnl as PN  # noqa: E402
SENS = [(d, PN.run("base", tx_mult=PN.A["tx_mult"]["base"] * (1 + d / 100))["op_margin"] * 100) for d in range(-30, 31, 2)]

# ---------------- 그리기 도구 ----------------
_fc = {}


def F(sz, bold=True):
    k = (sz, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(BOLD if bold else REG, sz)
    return _fc[k]


def T(d, xy, s, sz, fill=TXT, bold=True, anchor="la"):
    d.text(xy, s, font=F(sz, bold), fill=fill, anchor=anchor)


def box(d, x0, y0, x1, y1, fill=PANEL, outline=LINE, n=3):
    d.rectangle([x0 + n, y0, x1 - n, y1], fill=fill)
    d.rectangle([x0, y0 + n, x1, y1 - n], fill=fill)
    if outline:
        d.line([x0 + n, y0, x1 - n, y0], fill=outline)
        d.line([x0 + n, y1, x1 - n, y1], fill=outline)
        d.line([x0, y0 + n, x0, y1 - n], fill=outline)
        d.line([x1, y0 + n, x1, y1 - n], fill=outline)
        for ax, ay, sx, sy in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
            for i in range(n):
                d.point((ax + sx * (n - i), ay + sy * i), fill=outline)


def ease(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def seg(p, a, b):
    """전체 진행 p 중 [a,b] 구간의 진행률."""
    return ease((p - a) / (b - a)) if b > a else 1.0


def blink(t, hz=2):
    return int(t * hz * 2) % 2 == 0


def hbar(d, x, y, w, h, color):
    if w <= 0:
        return
    d.rectangle([x, y, x + max(w - 2, 0), y + h], fill=color)
    if w > 2:
        d.rectangle([x + w - 2, y + 1, x + w, y + h - 1], fill=color)


CUP = ["...m.m....", "....m.m...", "..........", "cccccccc..", "cbbbbbbccc", "cbbbbbbc.c", "cbbbbbbc.c",
       "cbbbbbbccc", "cbbbbbbc..", ".cccccc...", "dddddddd.."]
CUP_P = {"m": MUTED, "c": TXT, "b": "#8a4b2a", "d": LINE}
COIN = [".aaa.", "aabaa", "abaaa", "aabaa", ".aaa."]
COIN_P = {"a": AMBER, "b": "#ffd27f"}
PERSON = ["..hh..", "..hh..", ".bbbb.", "b.bb.b", "..bb..", ".b..b."]


def sprite(d, x, y, rows, pal, k=2):
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c != "." and c in pal:
                d.rectangle([x + i * k, y + j * k, x + i * k + k - 1, y + j * k + k - 1], fill=pal[c])


def chrome(d, si, title, src, cap):
    d.rectangle([0, 0, W, 20], fill=DARK)
    tw = d.textlength(f"STAGE {si+1}", font=F(9))
    box(d, 6, 4, 6 + tw + 14, 16, fill=AMBER, outline=None, n=2)
    T(d, (13, 5), f"STAGE {si+1}", 9, BG)
    T(d, (26 + tw, 4), title, 10, TXT)
    for i in range(5):
        x = W - 6 - (5 - i) * 20
        d.rectangle([x, 8, x + 16, 12], fill=AMBER if i <= si else LINE)
    # 자막(보조)
    d.rectangle([0, H - 34, W, H], fill=DARK)
    T(d, (W // 2, H - 23), cap, 12, TXT, anchor="mm")
    T(d, (8, H - 8), src, 7, MUTED, bold=False, anchor="lm")


# ---------------- 샷 (문장별) ----------------
def shot_map_pin(d, p, t):
    """결론: 서울 상권 1,650곳 지도에서 추천지로 줌인 핀."""
    mb = (16, 26, 250, 228)
    k = int(len(relm) * seg(p, 0, 0.35))
    for r in relm[:k]:
        x, y = proj(float(r["XCNTS_VALUE"]), float(r["YDNTS_VALUE"]), mb)
        d.rectangle([x, y, x + 1, y + 1], fill="#5d6890")
    gx, gy = proj(205282, float([s for s in scores if s["TRDAR_CD"] == "3001496"][0]["y"]), mb)
    if p > 0.35:
        rr = int(4 + 14 * (1 - seg(p, 0.35, 0.6)))
        d.ellipse([gx - rr, gy - rr, gx + rr, gy + rr], outline=CORAL)
        d.rectangle([gx - 3, gy - 3, gx + 3, gy + 3], fill=CORAL)
    if p > 0.5:
        d.line([gx + 4, gy, 262, 70], fill=CORAL)
        q = seg(p, 0.5, 0.8)
        x0 = 262
        box(d, x0, 40, 470, 200)
        T(d, (x0 + 12, 52), "추천 입지", 9, MUTED, bold=False)
        T(d, (x0 + 12, 66), "삼성동 코엑스"[: max(1, int(7 * q))], 20, TXT)
        if q > 0.6:
            T(d, (x0 + 12, 96), "강남 마이스 관광특구", 10, AMBER)
            T(d, (x0 + 12, 112), "봉은사역 7번 출구 ↔ 코엑스", 10, TXT)
            T(d, (x0 + 12, 128), "연결 동선 (삼성1동)", 10, TXT)
            sprite(d, x0 + 150, 150, CUP, CUP_P, 3)
            if blink(t, 1):
                d.point((x0 + 160, 146), fill=MUTED)
    T(d, (20, 214), "점 = 서울 상권 1,650곳 (실제 좌표)", 8, MUTED, bold=False)


def shot_kpi(d, p, t):
    """보상: KPI 카운트업."""
    vals = [("예상 연매출", 7.2, "억 원", "{:.1f}", AMBER), ("영업이익률", 11.4, "%", "{:.1f}", MINT), ("투자회수", 2.7, "년", "{:.1f}", TXT)]
    for i, (lab, v, u, fmt, c) in enumerate(vals):
        q = seg(p, i * 0.15, i * 0.15 + 0.45)
        x = 20 + i * 152
        box(d, x, 60, x + 140, 150)
        T(d, (x + 12, 72), lab, 10, MUTED, bold=False)
        T(d, (x + 12, 92), fmt.format(v * q), 30, c)
        T(d, (x + 12 + d.textlength(fmt.format(v), font=F(30)) + 4, 108), u, 12, c)
        hbar(d, x + 12, 136, int(116 * q), 4, c)
    if p > 0.7:
        T(d, (W // 2, 176), "기본 시나리오 · 출점 1년차 · 투자 3.3억 원(시설+보증금)", 9, MUTED, bold=False, anchor="mm")
        T(d, (W // 2, 192), "비관 -19.6%  ·  낙관 +24.7%  영업이익률", 9, MUTED, bold=False, anchor="mm")


def shot_score_map(d, p, t):
    """678곳 점수화: 지도에 점수 색 + 지표 트리."""
    mb = (16, 26, 250, 228)
    for r in relm:
        x, y = proj(float(r["XCNTS_VALUE"]), float(r["YDNTS_VALUE"]), mb)
        d.point((x, y), fill=FAINT)
    k = int(len(scores) * seg(p, 0.1, 0.7))
    for s in reversed(scores[:]):
        pass
    for i, s in enumerate(scores):
        if i >= k:
            break
        rk = int(s["rank"])
        c = MINT if rk <= 68 else (AMBER if rk <= 339 else CORAL)
        x, y = proj(float(s["x"]), float(s["y"]), mb)
        d.rectangle([x, y, x + 1, y + 1], fill=c)
    T(d, (20, 214), f"점수화한 상권 {min(k,678)}/678", 9, TXT)
    groups = [("수요", "유동·20~30대·직장인구", BLUE), ("공급", "밀도·점포당매출·프랜차이즈", AMBER),
              ("모멘텀", "매출·유동·점포 1년 변화", MINT), ("리스크", "폐업률·규모·영업개월", CORAL)]
    for i, (g, desc, c) in enumerate(groups):
        if p > 0.15 + i * 0.12:
            y = 40 + i * 40
            box(d, 262, y, 470, y + 32)
            d.rectangle([268, y + 6, 272, y + 26], fill=c)
            T(d, (280, y + 5), g, 11, c)
            T(d, (280, y + 19), desc, 8, MUTED, bold=False)
    T(d, (262, 210), "■상위10% ■중간 ■하위", 8, MUTED, bold=False)


def shot_quintile(d, p, t):
    """백테스트 5분위 막대 성장."""
    T(d, (20, 30), "2022년 점수 5분위 → 실제 3년 커피 매출 CAGR", 11, TXT)
    T(d, (20, 46), "5-fold 교차검증 · 표본 661곳", 8, MUTED, bold=False)
    q = [x["mean_cagr"] * 100 for x in bt["backtest_quintiles"]]
    zero = 118
    d.line([30, zero, 450, zero], fill=MUTED)
    for i, v in enumerate(q):
        g = seg(p, i * 0.1, i * 0.1 + 0.4)
        x = 50 + i * 82
        h = int(v * 9 * g)
        c = MINT if v > 0 else CORAL
        if h >= 0:
            d.rectangle([x, zero - h, x + 50, zero], fill=c)
        else:
            d.rectangle([x, zero, x + 50, zero - h], fill=c)
        if g > 0.9:
            T(d, (x + 25, zero - h - 10 if v > 0 else zero - h + 10), f"{v:+.1f}%", 11, c, anchor="mm")
        T(d, (x + 25, 198), f"Q{i+1}", 9, MUTED, anchor="mm")
    if p > 0.75 and blink(t, 1.5):
        box(d, 50 + 4 * 82 - 6, 74, 50 + 4 * 82 + 56, 124, fill=None, outline=AMBER, n=2)
    T(d, (40, 214), "점수 낮음", 8, MUTED, bold=False)
    T(d, (440, 214), "높음", 8, MUTED, bold=False, anchor="ra")


def shot_41(d, p, t):
    """매출 상위 66곳 격자 → 27곳 빨갛게."""
    T(d, (20, 30), "2022년 커피 매출 상위 10% 상권 66곳", 11, TXT)
    T(d, (20, 46), "3년 뒤(2025) 매출이 줄어든 곳을 빨간색으로", 8, MUTED, bold=False)
    k = int(66 * seg(p, 0.1, 0.75))
    cnt = 0
    for i in range(66):
        x = 24 + (i % 11) * 22
        y = 64 + (i // 11) * 22
        c = PANEL
        if i < k:
            c = CORAL if DECL[i] else MINT
            cnt += DECL[i]
        d.rectangle([x, y, x + 17, y + 17], fill=c)
    box(d, 290, 64, 470, 196)
    T(d, (380, 84), "역성장", 10, MUTED, bold=False, anchor="mm")
    pct = round(cnt / 66 * 100)
    T(d, (380, 122), f"{pct}%", 36, CORAL, anchor="mm")
    T(d, (380, 156), f"{cnt} / 66곳", 11, TXT, anchor="mm")
    if p > 0.8:
        T(d, (380, 178), "큰 상권 ≠ 안전", 11, AMBER, anchor="mm")
    T(d, (24, 206), "■ 성장  ■ 역성장   (순서: 2022 매출 순위)", 8, MUTED, bold=False)


def shot_d3(d, p, t):
    """직장인구 5분위 vs 1년 매출성장 ρ 비교."""
    T(d, (20, 30), "무엇이 3년 성장을 맞혔나 (순위상관 ρ)", 11, TXT)
    rows = [("직장인구", ins["D3"]["spearman"], MINT), ("커피점 밀도", ins["S1"]["spearman"], BLUE),
            ("최근 1년 매출 성장", ins["M1"]["spearman"], MUTED)]
    for i, (lab, v, c) in enumerate(rows):
        g = seg(p, i * 0.12, i * 0.12 + 0.4)
        y = 56 + i * 26
        T(d, (20, y + 2), lab, 10, TXT if c != MUTED else MUTED)
        hbar(d, 130, y, int(v * 700 * g), 14, c)
        if g > 0.9:
            T(d, (136 + int(v * 700), y + 2), f"{v:.3f}", 10, c)
    T(d, (20, 140), "직장인구 5분위별 3년 CAGR", 10, TXT)
    qv = [x * 100 for x in ins["D3"]["quintile_mean_cagr"]]
    zero = 188
    d.line([20, zero, 300, zero], fill=MUTED)
    for i, v in enumerate(qv):
        g = seg(p, 0.45 + i * 0.07, 0.75 + i * 0.05)
        x = 30 + i * 54
        h = int(v * 9 * g)
        c = MINT if v > 0 else CORAL
        if h >= 0:
            d.rectangle([x, zero - h, x + 36, zero], fill=c)
        else:
            d.rectangle([x, zero, x + 36, zero - h], fill=c)
        if g > 0.9:
            T(d, (x + 18, zero - h - 8 if v > 0 else zero - h + 8), f"{v:+.1f}", 8, c, anchor="mm")
    for i in range(int(6 * seg(p, 0.5, 0.9))):
        sprite(d, 330 + (i % 3) * 34, 110 + (i // 3) * 36, PERSON, {"h": "#e9c9a5", "b": BLUE}, 4)


def shot_series(d, p, t):
    """강남 마이스 vs 가산 분기 매출선 그리기 + GTX 마커."""
    T(d, (20, 28), "분기 커피 매출 (억 원) 2021Q1 → 2026Q2", 10, TXT)
    px0, py0, px1, py1 = 30, 48, 340, 204
    mx = max(max(SER_G), max(SER_K))
    d.line([px0, py1, px1, py1], fill=MUTED)
    n = len(QS)
    k = max(2, int(n * seg(p, 0.05, 0.8)))

    def pt(i, v):
        return px0 + (px1 - px0) * i / (n - 1), py1 - (py1 - py0) * v / mx

    for ser, c in [(SER_K, MUTED), (SER_G, AMBER)]:
        pts = [pt(i, v) for i, v in enumerate(ser[:k])]
        d.line(pts, fill=c, width=2)
        x, y = pts[-1]
        d.rectangle([x - 2, y - 2, x + 2, y + 2], fill=c)
    for i, q in enumerate(QS):
        if q.endswith("1"):
            x, _ = pt(i, 0)
            T(d, (x, py1 + 4), q[:4], 7, MUTED, bold=False, anchor="ma")
    if k >= n:
        x, y = pt(n - 1, SER_K[-1])
        T(d, (x - 4, y + 6), "가산디지털단지", 8, MUTED, anchor="ra")
        x, y = pt(n - 1, SER_G[-1])
        T(d, (x - 4, y - 14), "강남 마이스", 9, AMBER, anchor="ra")
    box(d, 352, 40, 470, 204)
    items = [("직장인구", "10.2만 명", MINT), ("매출 2022→최근", "+88%", AMBER), ("GTX-A 삼성역", "2028 하반기", BLUE)]
    for i, (a, b, c) in enumerate(items):
        if p > 0.3 + i * 0.18:
            T(d, (362, 50 + i * 50), a, 8, MUTED, bold=False)
            T(d, (362, 62 + i * 50), b, 14, c)


def shot_target(d, p, t):
    """연령 매출 비중 + 시간대 거래 비중."""
    T(d, (20, 28), "연령대별 커피 매출 비중", 10, TXT)
    ages = [("10대", "10"), ("20대", "20"), ("30대", "30"), ("40대", "40"), ("50대", "50"), ("60+", "60_ABOVE")]
    for i, (lab, k) in enumerate(ages):
        v = G["age_amt_share"][k]
        g = seg(p, i * 0.05, 0.4 + i * 0.05)
        y = 46 + i * 18
        hot = k in ("30", "40")
        T(d, (20, y), lab, 9, TXT if hot else MUTED)
        hbar(d, 56, y + 1, int(v * 400 * g), 11, AMBER if hot else LINE)
        if g > 0.9:
            T(d, (62 + int(v * 400), y), f"{v*100:.1f}%", 9, AMBER if hot else MUTED)
    T(d, (260, 28), "시간대별 거래 비중", 10, TXT)
    slots = [("06-11", "06_11"), ("11-14", "11_14"), ("14-17", "14_17"), ("17-21", "17_21"), ("21-24", "21_24")]
    base = 196
    for i, (lab, k) in enumerate(slots):
        v = G["slot_tx_share"][k]
        g = seg(p, 0.3 + i * 0.06, 0.7 + i * 0.05)
        x = 262 + i * 42
        hot = k in ("11_14", "14_17")
        h = int(v * 380 * g)
        d.rectangle([x, base - h, x + 30, base], fill=MINT if hot else LINE)
        T(d, (x + 15, base + 3), lab, 7, MUTED, bold=False, anchor="ma")
        if g > 0.9:
            T(d, (x + 15, base - h - 9), f"{v*100:.0f}%", 8, MINT if hot else MUTED, anchor="mm")
    if p > 0.85:
        box(d, 20, 162, 240, 200, fill=DARK, outline=AMBER)
        T(d, (130, 181), "30~40대 60% · 11~17시 63%", 11, AMBER, anchor="mm")


def shot_concept(d, p, t):
    """컨셉 카드: 두 미팅 사이 30분 타임라인."""
    T(d, (W // 2, 44), "CONCEPT", 10, AMBER, anchor="mm")
    title = "미팅과 미팅 사이 30분"
    T(d, (W // 2, 72), title[: max(1, int(len(title) * seg(p, 0, 0.4)))], 22, TXT, anchor="mm")
    if p > 0.35:
        T(d, (W // 2, 98), "프리미엄 미팅 라운지 커피", 12, AMBER, anchor="mm")
    y = 150
    d.line([60, y, 420, y], fill=LINE, width=2)
    for x, lab in [(60, "10:00"), (180, "미팅 A 끝"), (300, "미팅 B 시작"), (420, "12:00")]:
        d.rectangle([x - 2, y - 4, x + 2, y + 4], fill=MUTED)
        T(d, (x, y + 10), lab, 8, MUTED, bold=False, anchor="ma")
    g = seg(p, 0.45, 0.85)
    d.rectangle([180, y - 10, 180 + int(120 * g), y - 4], fill=MINT)
    if g > 0.95:
        T(d, (240, y - 22), "30분 = 우리 매장", 10, MINT, anchor="mm")
        sprite(d, 228, y + 22, CUP, CUP_P, 2)


def shot_floor(d, p, t):
    """평면도 조립 + 좌석 카운터."""
    box(d, 20, 28, 300, 204)
    parts = []
    for i in range(4):
        parts.append(("m", 150 + (i % 2) * 70, 40 + (i // 2) * 40, 206 + (i % 2) * 70, 66 + (i // 2) * 40, "#8a4b2a"))
    for i in range(3):
        parts.append(("t", 150 + i * 46, 132, 180 + i * 46, 148, AMBER))
    for i in range(10):
        parts.append(("b", 30 + (i % 5) * 18, 40 + (i // 5) * 18, 42 + (i % 5) * 18, 52 + (i // 5) * 18, "#e9c9a5"))
    parts.append(("p", 30, 84, 54, 108, BLUE))
    parts.append(("p", 60, 84, 84, 108, BLUE))
    parts.append(("bar", 30, 150, 130, 166, LINE))
    parts.append(("pk", 30, 180, 120, 198, "#2f8f6b"))
    k = int(len(parts) * seg(p, 0, 0.7))
    for _, x0, y0, x1, y1, c in parts[:k]:
        d.rectangle([x0, y0, x1, y1], fill=c)
    if k > len(parts) - 2:
        T(d, (80, 158), "BAR", 8, TXT, anchor="mm")
    if k >= len(parts):
        T(d, (75, 189), "PICKUP 90s", 8, TXT, anchor="mm")
        if blink(t, 2):
            T(d, (126, 189), "▶", 8, MINT, anchor="lm")
    seats = int(40 * seg(p, 0, 0.7))
    box(d, 312, 40, 470, 204)
    T(d, (391, 60), "좌석", 9, MUTED, bold=False, anchor="mm")
    T(d, (391, 88), f"{seats}석", 24, TXT, anchor="mm")
    mt = int(70 * seg(p, 0.4, 0.85))
    hbar(d, 326, 116, int(130 * mt / 100), 10, MINT)
    T(d, (391, 140), f"미팅 좌석 {mt}%", 10, MINT, anchor="mm")
    T(d, (391, 162), "11~17시 거래 63%", 8, MUTED, bold=False, anchor="mm")
    T(d, (391, 176), "아침 06~11시 18% → 픽업", 8, MUTED, bold=False, anchor="mm")


def shot_ticket(d, p, t):
    """객단가: 서울 중앙값 vs 상권 vs 우리 + 영수증 산식."""
    T(d, (20, 28), "커피 객단가 (원/건)", 10, TXT)
    rows = [("서울 상권 중앙값", prof["seoul"]["median_ticket_won"], MUTED), ("강남 마이스 평균", G["ticket_won"], AMBER),
            ("우리 목표", 12000, MINT)]
    for i, (lab, v, c) in enumerate(rows):
        g = seg(p, i * 0.15, i * 0.15 + 0.4)
        y = 48 + i * 28
        T(d, (20, y + 2), lab, 9, c if c != MUTED else MUTED)
        hbar(d, 120, y, int(v / 13000 * 150 * g), 14, c)
        if g > 0.9:
            T(d, (126 + int(v / 13000 * 150), y + 2), f"{v:,}", 10, c)
    box(d, 320, 36, 470, 204, fill="#f4efe6", outline=None)
    lines = [("RECEIPT", BG, 10), ("음료 1.6잔 × 6,400", "#3a3a3a", 9), ("= 10,240", BG, 10), ("베이커리 0.4 × 4,800", "#3a3a3a", 9),
             ("= 1,920", BG, 10), ("----------------", "#888888", 9), ("합계 12,160", "#b0531e", 12), ("→ 12,000 (보수)", "#2f8f6b", 9)]
    k = int(len(lines) * seg(p, 0.35, 0.9))
    for i, (s, c, sz) in enumerate(lines[:k]):
        T(d, (330, 46 + i * 19), s, sz, c, bold=(sz >= 10))
    T(d, (20, 150), "캐리어 4잔 세트 21,000원", 9, TXT)
    T(d, (20, 166), "시그니처 6,800 · 7,200 · 8,500원", 9, TXT)
    T(d, (20, 182), "스타벅스 톨 4,700원 대비 아메리카노 +800원", 8, MUTED, bold=False)


def shot_waterfall(d, p, t):
    """손익 폭포 차트."""
    T(d, (20, 28), "기본 시나리오 연간 손익 (억 원)", 10, TXT)
    b = pnlj["scenarios"]["base"]
    steps = [("매출", b["revenue"], AMBER, True), ("원가", -b["cogs"], CORAL, False), ("인건비", -b["labor"], CORAL, False),
             ("임대료", -b["rent"], CORAL, False), ("본사·기타", -(b["hq"] + b["other"]), CORAL, False),
             ("감가상각", -b["dep"], CORAL, False), ("영업이익", b["op"], MINT, True)]
    top, bot = 70, 200
    sc = (bot - top) / b["revenue"]
    cur = 0
    k = seg(p, 0, 0.85) * len(steps)
    for i, (lab, v, c, total) in enumerate(steps):
        x = 30 + i * 62
        if i > k:
            break
        g = min(1.0, k - i)
        if total:
            y0, y1 = bot - v * sc * g, bot
            if lab == "매출":
                cur = v
        else:
            y0 = bot - cur * sc
            y1 = y0 + (-v) * sc * g
            cur += v * (1 if g >= 1 else 0)
        d.rectangle([x, min(y0, y1), x + 40, max(y0, y1)], fill=c)
        T(d, (x + 20, bot + 4), lab, 7, MUTED, bold=False, anchor="ma")
        if g >= 1:
            T(d, (x + 20, min(y0, y1) - 9), f"{abs(v)/1e8:.2f}", 8, c, anchor="mm")
    if p > 0.9:
        T(d, (470, 34), "영업이익률 11.4%", 12, MINT, anchor="ra")


def shot_cross(d, p, t):
    """Bottom-up vs Top-down 수렴."""
    T(d, (20, 28), "두 가지 방법으로 계산한 연매출 (억 원)", 10, TXT)
    bu, td = pnlj["cross_check"]["bottom_up_revenue"] / 1e8, pnlj["cross_check"]["top_down_revenue"] / 1e8
    rows = [("Bottom-up", "일 167건 × 12,000원 × 360일", bu, AMBER), ("Top-down", "상권 점포당 6.33억 × 1.15 × 객단가비", td, BLUE)]
    for i, (lab, desc, v, c) in enumerate(rows):
        g = seg(p, i * 0.2, i * 0.2 + 0.5)
        y = 60 + i * 50
        T(d, (20, y), lab, 11, c)
        T(d, (20, y + 16), desc, 8, MUTED, bold=False)
        hbar(d, 200, y + 2, int(v * 32 * g), 18, c)
        if g > 0.9:
            T(d, (206 + int(v * 32), y + 5), f"{v:.2f}", 11, c)
    if p > 0.7:
        box(d, 150, 170, 330, 204, fill=DARK, outline=MINT)
        T(d, (240, 187), f"차이 {pnlj['cross_check']['gap_pct']*100:+.1f}%  → 일치", 12, MINT, anchor="mm")


def shot_sens(d, p, t):
    """객수 변화 vs 영업이익률 곡선 + 손익분기."""
    T(d, (20, 28), "객수가 바뀌면 영업이익률은? (기본 = 일 167건)", 10, TXT)
    px0, py0, px1, py1 = 40, 50, 330, 200
    lo, hi = -30, 30
    vmin, vmax = min(v for _, v in SENS), max(v for _, v in SENS)

    def pt(dx, v):
        return px0 + (px1 - px0) * (dx - lo) / (hi - lo), py1 - (py1 - py0) * (v - vmin) / (vmax - vmin)

    zx0, zy = pt(lo, 0)
    d.line([px0, zy, px1, zy], fill=MUTED)
    T(d, (px0 - 4, zy), "0%", 8, MUTED, anchor="rm")
    k = max(2, int(len(SENS) * seg(p, 0, 0.7)))
    pts = [pt(dx, v) for dx, v in SENS[:k]]
    d.line(pts, fill=AMBER, width=2)
    for dx in (-20, 0, 20):
        x, _ = pt(dx, 0)
        T(d, (x, py1 + 4), f"{dx:+d}%", 8, MUTED, bold=False, anchor="ma")
    if p > 0.7:
        x, y = pt(0, [v for dx, v in SENS if dx == 0][0])
        d.rectangle([x - 3, y - 3, x + 3, y + 3], fill=MINT)
        T(d, (x + 6, y - 12), "기본 11.4%", 9, MINT)
        x2, y2 = pt(-20, [v for dx, v in SENS if dx == -20][0])
        if blink(t, 2):
            d.rectangle([x2 - 3, y2 - 3, x2 + 3, y2 + 3], fill=CORAL)
        T(d, (x2 + 6, y2 + 2), "-20% → 적자", 9, CORAL)
    box(d, 350, 50, 470, 200)
    T(d, (410, 70), "손익분기", 9, MUTED, bold=False, anchor="mm")
    T(d, (410, 98), f"{pnlj['scenarios']['base']['breakeven_tx_day']}건", 22, TXT, anchor="mm")
    T(d, (410, 118), "/일", 9, MUTED, bold=False, anchor="mm")
    T(d, (410, 150), "상권 평균 점포", 8, MUTED, bold=False, anchor="mm")
    T(d, (410, 166), "145.5건/일", 11, AMBER, anchor="mm")
    T(d, (410, 184), "여유 6% 뿐", 9, CORAL, anchor="mm")


def shot_quest1(d, p, t):
    """퀘스트 1: 4주 실측 캘린더 채우기."""
    T(d, (20, 30), "QUEST 1 · 출점 전 4주 객수 실측", 12, AMBER)
    T(d, (20, 48), "봉은사역 7번 출구 동선 경쟁점 · 시간대별", 9, MUTED, bold=False)
    k = int(28 * seg(p, 0.05, 0.85))
    for i in range(28):
        x = 40 + (i % 7) * 30
        y = 70 + (i // 7) * 28
        d.rectangle([x, y, x + 24, y + 22], fill=MINT if i < k else PANEL, outline=LINE)
    box(d, 270, 70, 470, 180)
    T(d, (370, 90), "통과 조건", 9, MUTED, bold=False, anchor="mm")
    T(d, (370, 118), "일 150건+", 20, TXT, anchor="mm")
    T(d, (370, 148), "손익분기 136건 + 여유 10%", 9, MUTED, bold=False, anchor="mm")
    if k >= 28:
        T(d, (370, 166), "CLEAR!", 11, MINT, anchor="mm")


def shot_quest2(d, p, t):
    """퀘스트 2: 임대료 상한 + 투자 회수 타임라인."""
    T(d, (20, 30), "QUEST 2 · ㎡당 월 11만 원 이하 매물", 12, AMBER)
    T(d, (20, 50), "투자 회수 타임라인 (기본 시나리오)", 9, MUTED, bold=False)
    x0, x1, y = 40, 430, 110
    d.line([x0, y, x1, y], fill=LINE, width=3)
    for yr in range(0, 5):
        x = x0 + (x1 - x0) * yr / 4
        d.rectangle([x - 1, y - 4, x + 1, y + 4], fill=MUTED)
        T(d, (x, y + 10), f"{yr}년", 8, MUTED, bold=False, anchor="ma")
    g = seg(p, 0.1, 0.75)
    pay = pnlj["scenarios"]["base"]["payback_years"]
    xe = x0 + (x1 - x0) * pay / 4 * g
    d.rectangle([x0, y - 8, xe, y - 3], fill=MINT)
    for i in range(int(8 * g)):
        sprite(d, int(x0 + i * (xe - x0) / 8), y - 22, COIN, COIN_P, 2)
    if g > 0.98:
        T(d, (xe, y - 34), f"회수 {pay}년", 11, MINT, anchor="mm")
    if p > 0.8:
        box(d, 120, 150, 360, 196, fill=DARK, outline=AMBER)
        T(d, (240, 166), "투자 3.3억 원 승인 요청", 12, AMBER, anchor="mm")
        if blink(t, 2):
            T(d, (240, 184), "PRESS START", 9, TXT, anchor="mm")


SHOTS = [
    (shot_map_pin, "출처: 서울시 상권분석서비스 영역-상권(OA-15560) · 2026"),
    (shot_kpi, "가정 포함 손익 모델(scripts/pnl.py) · 상권 데이터 2025Q3~2026Q2"),
    (shot_score_map, "출처: 상권분석서비스 추정매출·점포·인구·변화지표 · 2025Q3~2026Q2"),
    (shot_quintile, SRC_SALES + " · 2022→2025"),
    (shot_41, SRC_SALES + " · 2022→2025, 매출 3억 원 이상 661곳"),
    (shot_d3, "출처: 상권분석서비스 직장인구(OA-15569)·추정매출 · 2022→2025"),
    (shot_series, SRC_SALES + " · 분기 · GTX: 뉴시스 2024.6.24"),
    (shot_target, SRC_SALES + " · 강남 마이스 2025Q3~2026Q2"),
    (shot_concept, "컨셉: 11~17시 거래 63% · 30~40대 매출 60%에서 도출"),
    (shot_floor, "평면 개념도 · 전용 99㎡(가정) · 시간대 비중 OA-15572"),
    (shot_ticket, SRC_SALES + " · 스타벅스 가격: 2025.1.24 인상"),
    (shot_waterfall, "손익 모델 · 인건비: 2026 최저임금 10,320원 · 임대료 가정 A9"),
    (shot_cross, "Top-down: 상권 점포당 커피 매출(OA-15572·15577) · 2025Q3~2026Q2"),
    (shot_sens, "손익 모델 민감도 · 상권 점포당 일 145.5건(OA-15572·15577)"),
    (shot_quest1, "손익분기 136건/일 = 고정비 ÷ 건당 공헌이익"),
    (shot_quest2, "투자 = 시설 2.0억 + 보증금 12개월 (가정 A12·A13)"),
]


def render(idx, si, title, cap, p, t):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    fn, src = SHOTS[idx]
    fn(d, p, t)
    chrome(d, si, title, src, cap)
    return im


def wav_dur(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def main(preview=False):
    md = ["# 피치 영상 스크립트 (모션 픽셀 버전)", "", "| 시작 | 장면 | 화면(근거) | 내레이션 |", "|---|---|---|---|"]
    clips, t0, idx = [], 0.0, 0
    for si, (title, sents) in enumerate(R.SCENES):
        for speak, cap in sents:
            if preview:
                render(idx, si, STAGES[si], cap, 1.0, 0.0).resize((W * 2, H * 2), Image.NEAREST).save(
                    os.path.join(TMP, f"pv_{idx:02d}.png"))
                idx += 1
                continue
            wav = os.path.join(TMP, f"s{idx:02d}.wav")
            txt = wav + ".txt"
            if not (os.path.exists(wav) and os.path.exists(txt) and open(txt, encoding="utf-8").read() == speak):
                R.tts(speak, wav)
            dur = wav_dur(wav) + 0.3
            nfr = int(math.ceil(dur * FPS))
            mp4 = os.path.join(TMP, f"s{idx:02d}.mp4")
            proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                     "-r", str(FPS), "-i", "-", "-i", wav, "-af",
                                     "asetrate=22050*1.12,aresample=44100,atempo=0.893,acrusher=bits=8:mode=log:aa=1:mix=0.25,"
                                     "highpass=f=150,lowpass=f=7000,volume=1.6,apad=pad_dur=0.3",
                                     "-t", f"{dur:.3f}", "-vf", f"scale={W*S}:{H*S}:flags=neighbor", "-c:v", "libx264",
                                     "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-ar", "44100", "-ac", "2", mp4],
                                    stdin=subprocess.PIPE)
            anim = max(1.0, dur * 0.8)  # 문장 80% 지점까지 애니메이션 완료
            for f in range(nfr):
                tt = f / FPS
                im = render(idx, si, STAGES[si], cap, tt / anim, tt)
                proc.stdin.write(im.tobytes())
                if idx == 1 and f == nfr - 1:
                    im.resize((W * S, H * S), Image.NEAREST).save(os.path.join(ROOT, "docs", "assets", "poster.png"))
            proc.stdin.close()
            proc.wait()
            md.append(f"| {int(t0 // 60)}:{t0 % 60:05.2f} | {STAGES[si]} | {SHOTS[idx][0].__doc__.strip()} | {speak} |")
            clips.append(mp4)
            t0 += dur
            idx += 1
    if preview:
        print("preview done")
        return
    lst = os.path.join(TMP, "list.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{c}'\n" for c in clips))
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(VID, "pitch.mp4")], check=True)
    md += ["", f"총 길이: {t0:.1f}초", "",
           "보관 버전: `pitch_retro.mp4`(레트로 원본), `pitch_static.mp4`(정지화면 픽셀)"]
    open(os.path.join(VID, "script.md"), "w", encoding="utf-8").write("\n".join(md))
    print(f"total {t0:.1f}s")


if __name__ == "__main__":
    main(preview="--preview" in sys.argv)
