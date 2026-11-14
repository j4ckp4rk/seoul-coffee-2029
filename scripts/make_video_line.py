"""라인드로잉 피치 영상: 종이 위에 펜으로 그려지는 데이터 근거.

- 크림색 종이 + 잉크 선, 강조색은 주황(핵심) · 초록(성장) 두 가지
- 모든 선은 '그려지는' 애니메이션(경로 길이 비율), 살짝 흔들리는 손그림 선, 빗금 채움
- 데이터는 make_video_motion.py와 동일(상권 1,650곳 좌표, 분기 매출, 백테스트, 손익)
- 내레이션: 차분한 프레젠테이션 톤, 문장 간격을 자동 조정해 총 약 120초
사용: python scripts/make_video_line.py [--preview]
출력: docs/video/pitch.mp4, docs/video/script.md, docs/assets/poster.png
"""
import math
import os
import random
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_video_motion as M  # noqa: E402  (데이터·유틸 재사용)
import make_video_retro as R  # noqa: E402

ROOT, VID, FF = R.ROOT, R.VID, R.FF
TMP = os.path.join(ROOT, "data", "video_tmp", "line")
os.makedirs(TMP, exist_ok=True)
W, H, S, FPS = 480, 270, 4, 12
TARGET_SEC = 119.0

PAPER, INK, PENCIL, GRID = "#faf6ee", "#1f2430", "#8b8f98", "#ebe5d8"
ACC, GOOD, NEG = "#e4572e", "#2a7f62", "#e4572e"
BOLD, REG = "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"
seg, blink = M.seg, M.blink

# ---------------- 내레이션 (차분한 톤) ----------------
SCENES = [
    ("결론", [
        ("결론부터 말씀드리겠습니다. 다음 매장은 삼성동 코엑스, 봉은사역 7번 출구입니다.", "다음 매장: 삼성동 코엑스, 봉은사역 7번 출구"),
        ("예상 연매출 칠억 이천만 원, 영업이익률 십일 점 사 퍼센트, 투자회수 이 점 칠 년입니다.", "연매출 7.2억 · 영업이익률 11.4% · 투자회수 2.7년"),
    ]),
    ("왜 여기인가", [
        ("서울 커피 상권 육백칠십팔 곳을 수요, 공급, 모멘텀, 리스크의 열두 개 지표로 점수화했습니다.", "서울 커피 상권 678곳 × 지표 12개"),
        ("이천이십이년 지표로 삼 년 뒤를 맞혀 보니, 점수 상위 십 퍼센트는 연 삼 점 사 퍼센트 성장했고, 전체 평균은 마이너스였습니다.", "백테스트: 점수 상위 10% 연 +3.4%, 전체 평균 -0.7%"),
        ("그런데 이천이십이년 매출 상위 십 퍼센트 상권 중 사십일 퍼센트는, 삼 년 뒤 오히려 역성장했습니다.", "매출 상위 10% 상권의 41%가 3년 뒤 역성장"),
        ("삼 년 성장을 가른 건 매출 규모가 아니라 직장인구였습니다.", "성장을 가른 것은 매출 규모가 아니라 직장인구"),
        ("강남 마이스 특구는 직장인구 십만 명, 커피 매출이 삼 년 새 팔십팔 퍼센트 늘었고, 이천이십팔년 지티엑스 에이 삼성역이 열립니다.", "직장인구 10.2만 · 커피 매출 +88% · 2028 GTX-A"),
    ]),
    ("타깃 · 공간 · 메뉴", [
        ("고객은 삼십대와 사십대가 매출의 육십 퍼센트이고, 거래의 육십삼 퍼센트가 오전 열한 시부터 오후 다섯 시에 몰립니다.", "30~40대 매출 60% · 11~17시 거래 63%"),
        ("그래서 컨셉은, 미팅과 미팅 사이 삼십 분을 위한 프리미엄 미팅 라운지 커피입니다.", "컨셉: 미팅과 미팅 사이 30분"),
        ("사십 석 중 칠십 퍼센트를 미팅 좌석으로 두고, 아침에는 구십 초 픽업 바를 운영합니다.", "40석 중 70% 미팅 좌석 + 아침 90초 픽업 바"),
        ("객단가 만 이천 원은 단체 캐리어 세트와 시그니처 메뉴 세 가지로 만듭니다.", "객단가 12,000원 = 캐리어 세트 + 시그니처 3종"),
    ]),
    ("손익", [
        ("하루 백육십칠 건, 객단가 만 이천 원이면 연매출 칠억 이천만 원, 영업이익 팔천이백만 원입니다.", "일 167건 × 12,000원 → 연 7.2억, 영업이익 0.82억"),
        ("상권 평균 점포 매출로 계산한 값과 비교해도 차이는 일 점 사 퍼센트입니다.", "Top-down 교차검증 차이 -1.4%"),
        ("다만 손익분기는 하루 백삼십육 건이라, 객수가 이십 퍼센트 줄면 적자입니다.", "손익분기 일 136건 · 객수 -20%면 적자"),
    ]),
    ("요청", [
        ("요청드립니다. 출점 전 사 주 동안 같은 동선의 객수를 실측하고,", "조건 1: 출점 전 4주 객수 실측"),
        ("임대료가 제곱미터당 십일만 원 이하인 매물이 나오면, 삼억 삼천만 원 투자를 승인해 주십시오.", "조건 2: ㎡당 11만 원 이하 → 투자 3.3억 승인"),
    ]),
]

_fc = {}


def F(sz, bold=False):
    k = (sz, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(BOLD if bold else REG, max(sz, 9) * S)
    return _fc[k]


class Pen:
    """480x270 좌표로 그리면 1920x1080에 잉크 선으로 그린다."""

    def __init__(self, im):
        self.d = ImageDraw.Draw(im)

    # --- 기본 ---
    def _p(self, x, y):
        return (x * S, y * S)

    def text(self, xy, s, sz, fill=INK, bold=False, anchor="la"):
        self.d.text(self._p(*xy), s, font=F(sz, bold), fill=fill, anchor=anchor)

    def tlen(self, s, sz, bold=False):
        return self.d.textlength(s, font=F(sz, bold)) / S

    def dot(self, x, y, r=0.5, fill=INK):
        cx, cy = self._p(x, y)
        rr = r * S
        self.d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=fill)

    # --- 손그림 경로 ---
    @staticmethod
    def _wobble(pts, seed, amp=0.45, step=6):
        rnd = random.Random(seed)
        out = []
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
            for k in range(n):
                t = k / n
                j = 0 if (i == 0 and k == 0) else amp
                out.append((x0 + (x1 - x0) * t + rnd.uniform(-j, j), y0 + (y1 - y0) * t + rnd.uniform(-j, j)))
        out.append(pts[-1])
        return out

    def path(self, pts, p=1.0, fill=INK, w=1.0, seed=None, wobble=True, dash=False):
        if p <= 0 or len(pts) < 2:
            return
        sd = seed if seed is not None else hash(tuple(round(c) for pt in pts[:3] for c in pt)) & 0xFFFF
        q = self._wobble(pts, sd) if wobble else list(pts)
        L = [0.0]
        for i in range(1, len(q)):
            L.append(L[-1] + math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]))
        lim = L[-1] * min(1.0, p)
        drawn = [q[0]]
        for i in range(1, len(q)):
            if L[i] <= lim:
                drawn.append(q[i])
            else:
                t = (lim - L[i - 1]) / max(1e-9, L[i] - L[i - 1])
                drawn.append((q[i - 1][0] + (q[i][0] - q[i - 1][0]) * t, q[i - 1][1] + (q[i][1] - q[i - 1][1]) * t))
                break
        sc = [self._p(x, y) for x, y in drawn]
        if dash:
            for i in range(0, len(sc) - 1, 2):
                self.d.line([sc[i], sc[i + 1]], fill=fill, width=max(2, int(w * S * 0.6)))
        else:
            self.d.line(sc, fill=fill, width=max(2, int(w * S * 0.6)), joint="curve")

    def line(self, x0, y0, x1, y1, p=1.0, **kw):
        self.path([(x0, y0), (x1, y1)], p, **kw)

    def rect(self, x0, y0, x1, y1, p=1.0, **kw):
        self.path([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], p, **kw)

    def circle(self, cx, cy, r, p=1.0, **kw):
        n = max(16, int(r * 2))
        self.path([(cx + r * math.cos(2 * math.pi * i / n - math.pi / 2), cy + r * math.sin(2 * math.pi * i / n - math.pi / 2))
                   for i in range(n + 1)], p, **kw)

    def hatch(self, x0, y0, x1, y1, p=1.0, fill=INK, gap=3.0):
        """사각형 안을 45도 빗금으로 채움(p만큼)."""
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        w, h = x1 - x0, y1 - y0
        lines = []
        k = -h
        while k < w:
            a = (x0 + max(k, 0), y1 - max(0, -k))
            bx = min(x0 + k + h, x1)
            b = (bx, y1 - (bx - (x0 + k)))
            lines.append((a, b))
            k += gap
        n = int(len(lines) * max(0, min(1, p)))
        for (ax, ay), (bx, by) in lines[:n]:
            self.d.line([self._p(ax, ay), self._p(bx, by)], fill=fill, width=2)

    def bar(self, x0, y0, x1, y1, p, fill=INK):
        """손그림 막대: 테두리 + 빗금. p에 따라 길이가 자람(가로 막대는 x1이, 세로 막대는 위아래로)."""
        if p <= 0:
            return
        self.rect(x0, y0, x1, y1, 1.0, fill=fill, w=1.0)
        self.hatch(x0, y0, x1, y1, 1.0, fill=fill)

    def arrow(self, x0, y0, x1, y1, p=1.0, fill=INK):
        self.line(x0, y0, x1, y1, p, fill=fill)
        if p >= 1:
            a = math.atan2(y1 - y0, x1 - x0)
            for s in (+1, -1):
                self.line(x1, y1, x1 - 6 * math.cos(a + s * 0.45), y1 - 6 * math.sin(a + s * 0.45), fill=fill, wobble=False)

    def underline(self, x0, x1, y, p, fill=ACC):
        self.path([(x0, y), ((x0 + x1) / 2, y + 1.2), (x1, y - 0.6)], p, fill=fill, w=1.4)

    def typewrite(self, xy, s, sz, p, **kw):
        n = max(0, min(len(s), int(math.ceil(len(s) * p))))
        if n:
            self.text(xy, s[:n], sz, **kw)


def cup(pen, x, y, k=1.0, p=1.0, steam_t=0.0):
    pen.path([(x, y), (x + 3 * k, y + 22 * k), (x + 21 * k, y + 22 * k), (x + 24 * k, y)], p, w=1.2)
    pen.line(x - 2 * k, y, x + 26 * k, y, p, w=1.2)
    pen.path([(x + 23 * k, y + 5 * k), (x + 30 * k, y + 6 * k), (x + 30 * k, y + 13 * k), (x + 22 * k, y + 15 * k)], p, w=1.0)
    pen.line(x - 4 * k, y + 25 * k, x + 28 * k, y + 25 * k, p, w=1.0)
    if p >= 1:
        for i, dx in enumerate((7, 13, 19)):
            ph = steam_t * 3 + i
            pen.path([(x + dx * k + math.sin(ph + j) * 1.5, y - 3 - j * 3 * k) for j in range(5)], 1, fill=PENCIL, w=0.8, wobble=False)


def person(pen, x, y, p=1.0, fill=INK):
    pen.circle(x, y, 3.2, p, fill=fill)
    pen.path([(x - 6, y + 16), (x - 5, y + 7), (x, y + 5), (x + 5, y + 7), (x + 6, y + 16)], p, fill=fill)


# ---------------- 공통 프레임 ----------------
def paper(im):
    d = ImageDraw.Draw(im)
    for x in range(0, W * S, 16 * S):
        for y in range(0, H * S, 16 * S):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=GRID)


def frame_chrome(pen, si, cap, src, p):
    pen.text((14, 10), f"{si+1:02d}", 10, ACC, bold=True)
    pen.text((34, 10), SCENES[si][0], 10, INK, bold=True)
    for i in range(5):
        x = W - 14 - (5 - i) * 16
        pen.line(x, 15, x + 12, 15, 1, fill=ACC if i <= si else GRID, w=1.6, wobble=False)
    pen.line(14, H - 40, W - 14, H - 40, seg(p, 0, 0.3), fill=PENCIL, w=0.6)
    pen.text((W // 2, H - 26), cap, 12, INK, bold=True, anchor="mm")
    pen.text((14, H - 9), src, 9, PENCIL, anchor="lm")


# ---------------- 장면 ----------------
def s_map(pen, p, t):
    mb = (18, 30, 250, 222)
    k = int(len(M.relm) * seg(p, 0, 0.35))
    for r in M.relm[:k]:
        x, y = M.proj(float(r["XCNTS_VALUE"]), float(r["YDNTS_VALUE"]), mb)
        pen.dot(x, y, 0.45, PENCIL)
    tg = [s for s in M.scores if s["TRDAR_CD"] == "3001496"][0]
    gx, gy = M.proj(float(tg["x"]), float(tg["y"]), mb)
    pen.circle(gx, gy, 9, seg(p, 0.35, 0.55), fill=ACC, w=1.6)
    pen.dot(gx, gy, 1.3, ACC) if p > 0.4 else None
    pen.arrow(gx + 10, gy - 6, 266, 86, seg(p, 0.5, 0.65), fill=ACC)
    pen.typewrite((272, 60), "삼성동 코엑스", 22, seg(p, 0.6, 0.8), bold=True)
    pen.underline(272, 410, 88, seg(p, 0.75, 0.9))
    if p > 0.8:
        pen.text((272, 98), "강남 마이스 관광특구", 10, ACC, bold=True)
        pen.text((272, 114), "봉은사역 7번 출구 ↔ 코엑스 연결 동선", 10)
        cup(pen, 400, 150, 1.2, seg(p, 0.8, 0.95), t)
    pen.text((20, 210), "· 서울 상권 1,650곳 (실제 좌표)", 9, PENCIL)


def s_kpi(pen, p, t):
    vals = [("예상 연매출", 7.2, "억 원"), ("영업이익률", 11.4, "%"), ("투자회수", 2.7, "년")]
    for i, (lab, v, u) in enumerate(vals):
        q = seg(p, i * 0.15, i * 0.15 + 0.45)
        x = 24 + i * 148
        pen.rect(x, 54, x + 132, 152, seg(p, i * 0.12, i * 0.12 + 0.3), w=1.2)
        if q > 0:
            pen.text((x + 12, 64), lab, 10, PENCIL)
            pen.text((x + 12, 84), f"{v*q:.1f}", 32, ACC if i == 0 else INK, bold=True)
            pen.text((x + 14 + pen.tlen(f"{v:.1f}", 32, True), 104), u, 12, INK)
            pen.underline(x + 12, x + 12 + 108 * q, 142, 1.0, fill=ACC if i == 0 else INK)
    if p > 0.7:
        pen.text((W // 2, 176), "기본 시나리오 · 출점 1년차 · 투자 3.3억 원(시설 + 보증금)", 10, PENCIL, anchor="mm")
        pen.text((W // 2, 192), "비관 -19.6%  ·  낙관 +24.7%  (영업이익률)", 10, PENCIL, anchor="mm")


def s_tree(pen, p, t):
    mb = (14, 30, 214, 222)
    k = int(len(M.scores) * seg(p, 0.05, 0.6))
    for i, s in enumerate(M.scores[:k]):
        rk = int(s["rank"])
        x, y = M.proj(float(s["x"]), float(s["y"]), mb)
        pen.dot(x, y, 0.9 if rk <= 68 else 0.5, ACC if rk <= 68 else (INK if rk <= 339 else PENCIL))
    pen.text((18, 206), f"점수화 {min(k, 678)}/678곳 · ● 상위 10%", 9, PENCIL)
    # 지표 트리
    rx, ry = 250, 120
    pen.rect(rx - 26, ry - 12, rx + 26, ry + 12, seg(p, 0.05, 0.2), w=1.2)
    if p > 0.15:
        pen.text((rx, ry), "성장 점수", 10, INK, bold=True, anchor="mm")
    groups = [("수요", "유동 · 20~30대 · 직장인구"), ("공급", "밀도 · 점포당 매출 · 프랜차이즈"),
              ("모멘텀", "매출 · 유동 · 점포 1년 변화"), ("리스크", "폐업률 · 규모 · 영업개월")]
    for i, (g, desc) in enumerate(groups):
        y = 50 + i * 46
        q = seg(p, 0.2 + i * 0.12, 0.4 + i * 0.12)
        pen.path([(rx + 26, ry), (rx + 46, ry), (rx + 46, y), (300, y)], q, w=1.0)
        if q >= 1:
            pen.text((304, y - 9), g, 11, ACC if i == 0 else INK, bold=True)
            pen.text((304, y + 5), desc, 9, PENCIL)


def s_quint(pen, p, t):
    pen.text((24, 34), "2022년 점수 5분위 → 실제 3년 커피 매출 연평균 성장률", 11, INK, bold=True)
    pen.text((24, 52), "5-fold 교차검증 · 서울 상권 661곳", 9, PENCIL)
    q = [x["mean_cagr"] * 100 for x in M.bt["backtest_quintiles"]]
    zero, K = 112, 8
    pen.line(40, zero, 450, zero, seg(p, 0, 0.2), w=1.0)
    for i, v in enumerate(q):
        g = seg(p, 0.15 + i * 0.1, 0.45 + i * 0.1)
        x = 60 + i * 80
        h = v * K * g
        c = GOOD if v > 0 else NEG
        if abs(h) > 0.5:
            pen.bar(x, zero - h if h > 0 else zero, x + 46, zero if h > 0 else zero - h, 1, fill=c)
        if g > 0.95:
            pen.text((x + 23, zero - h - 9 if v > 0 else zero - h + 10), f"{v:+.1f}%", 11, c, bold=True, anchor="mm")
        pen.text((x + 23, 190), f"Q{i+1}", 10, PENCIL, anchor="mm")
    pen.arrow(60, 202, 430, 202, seg(p, 0.6, 0.8), fill=PENCIL)
    if p > 0.8:
        pen.text((60, 207), "점수 낮음", 9, PENCIL)
        pen.text((430, 207), "점수 높음", 9, PENCIL, anchor="ra")
        pen.circle(60 + 4 * 80 + 23, zero - q[4] * K / 2, 26, seg(p, 0.85, 1.0), fill=ACC, w=1.2)


def s_41(pen, p, t):
    pen.text((24, 34), "2022년 커피 매출 상위 10% 상권 66곳", 11, INK, bold=True)
    pen.text((24, 52), "3년 뒤(2025) 매출이 줄어든 곳에 빗금", 9, PENCIL)
    k = int(66 * seg(p, 0.05, 0.75))
    cnt = 0
    for i in range(66):
        x = 26 + (i % 11) * 20
        y = 66 + (i // 11) * 20
        if i < k:
            pen.rect(x, y, x + 15, y + 15, 1, w=0.8, fill=INK)
            if M.DECL[i]:
                pen.hatch(x, y, x + 15, y + 15, 1, fill=ACC, gap=2.5)
                cnt += 1
    pen.circle(370, 120, 52, seg(p, 0.2, 0.5), fill=ACC, w=1.4)
    pen.text((370, 104), "역성장", 10, PENCIL, anchor="mm")
    pen.text((370, 126), f"{round(cnt/66*100)}%", 30, ACC, bold=True, anchor="mm")
    pen.text((370, 150), f"{cnt} / 66곳", 10, INK, anchor="mm")
    if p > 0.85:
        pen.typewrite((370, 196), "큰 상권이 안전하다는 통념 ×", 11, seg(p, 0.85, 1), fill=INK, bold=True, anchor="mm")


def s_d3(pen, p, t):
    pen.text((24, 34), "무엇이 3년 성장을 맞혔나 (순위상관 ρ)", 11, INK, bold=True)
    rows = [("직장인구", M.ins["D3"]["spearman"], GOOD), ("커피점 밀도", M.ins["S1"]["spearman"], INK),
            ("최근 1년 매출 성장", M.ins["M1"]["spearman"], PENCIL)]
    for i, (lab, v, c) in enumerate(rows):
        g = seg(p, i * 0.12, i * 0.12 + 0.4)
        y = 58 + i * 26
        pen.text((24, y + 1), lab, 10, c if c != PENCIL else PENCIL, bold=(c == GOOD))
        if g > 0:
            pen.bar(140, y, 140 + v * 700 * g, y + 14, 1, fill=c)
        if g > 0.95:
            pen.text((146 + v * 700, y + 1), f"{v:.3f}", 10, c, bold=True)
    pen.text((24, 146), "직장인구 5분위별 3년 CAGR", 10, INK, bold=True)
    qv = [x * 100 for x in M.ins["D3"]["quintile_mean_cagr"]]
    zero = 196
    pen.line(24, zero, 300, zero, seg(p, 0.4, 0.5), w=0.8)
    for i, v in enumerate(qv):
        g = seg(p, 0.45 + i * 0.07, 0.75 + i * 0.05)
        x = 34 + i * 54
        h = v * 6 * g
        if abs(h) > 0.5:
            pen.bar(x, zero - h if h > 0 else zero, x + 34, zero if h > 0 else zero - h, 1, fill=GOOD if v > 0 else NEG)
        if g > 0.95:
            pen.text((x + 17, zero - h - 8 if v > 0 else zero - h + 8), f"{v:+.1f}", 9, GOOD if v > 0 else NEG, anchor="mm")
    for i in range(int(6 * seg(p, 0.5, 0.9))):
        person(pen, 350 + (i % 3) * 32, 120 + (i // 3) * 36, 1, fill=GOOD)


def s_series(pen, p, t):
    pen.text((24, 30), "분기 커피 매출 (억 원), 2021Q1 → 2026Q2", 11, INK, bold=True)
    x0, y0, x1, y1 = 40, 50, 340, 206
    mx = max(max(M.SER_G), max(M.SER_K))
    n = len(M.QS)
    pen.line(x0, y1, x1, y1, seg(p, 0, 0.15), w=0.8)
    pen.line(x0, y0, x0, y1, seg(p, 0, 0.15), w=0.8)

    def pt(i, v):
        return x0 + (x1 - x0) * i / (n - 1), y1 - (y1 - y0) * v / mx

    g = seg(p, 0.1, 0.75)
    pen.path([pt(i, v) for i, v in enumerate(M.SER_K)], g, fill=PENCIL, w=1.2, wobble=False)
    pen.path([pt(i, v) for i, v in enumerate(M.SER_G)], g, fill=ACC, w=1.8, wobble=False)
    for i, q in enumerate(M.QS):
        if q.endswith("1"):
            x, _ = pt(i, 0)
            pen.text((x, y1 + 5), q[:4], 8, PENCIL, anchor="ma")
    if g >= 1:
        x, y = pt(n - 1, M.SER_K[-1])
        pen.text((x - 4, y - 14), "가산디지털단지", 9, PENCIL, anchor="ra")
        x, y = pt(n - 1, M.SER_G[-1])
        pen.text((x - 4, y + 4), "강남 마이스", 10, ACC, bold=True, anchor="ra")
        xa, ya = pt(4, M.SER_G[4])
        pen.arrow(xa, ya - 6, x - 8, y - 4, seg(p, 0.75, 0.9), fill=ACC)
    items = [("직장인구", "10.2만 명"), ("커피 매출 2022 → 최근", "+88%"), ("GTX-A 삼성역", "2028 하반기")]
    for i, (a, b) in enumerate(items):
        q = seg(p, 0.3 + i * 0.15, 0.5 + i * 0.15)
        y = 56 + i * 50
        pen.line(356, y + 36, 470, y + 36, q, fill=PENCIL, w=0.6)
        if q > 0.5:
            pen.text((356, y), a, 9, PENCIL)
            pen.text((356, y + 14), b, 15, ACC if i == 1 else INK, bold=True)


def s_target(pen, p, t):
    G = M.G
    pen.text((24, 30), "연령대별 커피 매출 비중", 11, INK, bold=True)
    ages = [("10대", "10"), ("20대", "20"), ("30대", "30"), ("40대", "40"), ("50대", "50"), ("60+", "60_ABOVE")]
    for i, (lab, k) in enumerate(ages):
        v = G["age_amt_share"][k]
        g = seg(p, i * 0.05, 0.4 + i * 0.05)
        y = 50 + i * 20
        hot = k in ("30", "40")
        pen.text((24, y), lab, 10, INK if hot else PENCIL, bold=hot)
        if g > 0 and v * 400 * g > 1:
            pen.bar(62, y + 2, 62 + v * 400 * g, y + 13, 1, fill=ACC if hot else PENCIL)
        if g > 0.95:
            pen.text((68 + v * 400, y), f"{v*100:.1f}%", 9, ACC if hot else PENCIL, bold=hot)
    pen.text((270, 30), "시간대별 거래 비중", 11, INK, bold=True)
    slots = [("06-11", "06_11"), ("11-14", "11_14"), ("14-17", "14_17"), ("17-21", "17_21"), ("21-24", "21_24")]
    base = 200
    pen.line(268, base, 470, base, seg(p, 0.25, 0.35), w=0.8)
    for i, (lab, k) in enumerate(slots):
        v = G["slot_tx_share"][k]
        g = seg(p, 0.3 + i * 0.06, 0.7 + i * 0.05)
        x = 274 + i * 40
        hot = k in ("11_14", "14_17")
        h = v * 380 * g
        if h > 1:
            pen.bar(x, base - h, x + 28, base, 1, fill=ACC if hot else PENCIL)
        pen.text((x + 14, base + 4), lab, 8, PENCIL, anchor="ma")
        if g > 0.95:
            pen.text((x + 14, base - h - 8), f"{v*100:.0f}%", 9, ACC if hot else PENCIL, bold=hot, anchor="mm")
    if p > 0.8:
        pen.rect(24, 178, 236, 206, seg(p, 0.8, 0.95), fill=ACC, w=1.2)
        if p > 0.92:
            pen.text((130, 192), "30~40대 60% · 11~17시 63%", 11, ACC, bold=True, anchor="mm")


def s_concept(pen, p, t):
    pen.text((W // 2, 40), "CONCEPT", 10, ACC, bold=True, anchor="mm")
    pen.typewrite((W // 2, 66), "미팅과 미팅 사이 30분", 22, seg(p, 0, 0.35), bold=True, anchor="mm")
    if p > 0.35:
        pen.text((W // 2, 92), "삼성동 비즈니스 방문객을 위한 프리미엄 미팅 라운지 커피", 11, INK, anchor="mm")
    y = 150
    pen.arrow(50, y, 440, y, seg(p, 0.35, 0.55), fill=INK)
    blocks = [(70, 180, "미팅 A"), (300, 410, "미팅 B")]
    for i, (a, b, lab) in enumerate(blocks):
        q = seg(p, 0.45 + i * 0.1, 0.6 + i * 0.1)
        pen.rect(a, y - 14, b, y + 14, q, w=1.0)
        if q >= 1:
            pen.hatch(a, y - 14, b, y + 14, 1, fill=GRID, gap=4)
            pen.text(((a + b) / 2, y), lab, 10, INK, bold=True, anchor="mm")
    q = seg(p, 0.7, 0.9)
    pen.path([(186, y - 22), (186, y - 28), (294, y - 28), (294, y - 22)], q, fill=ACC, w=1.4)
    if q >= 1:
        pen.text((240, y - 40), "30분 = 우리 매장", 11, ACC, bold=True, anchor="mm")
        cup(pen, 228, y + 24, 0.9, 1, t)


def s_floor(pen, p, t):
    walls = [(24, 30), (300, 30), (300, 206), (150, 206)]
    pen.path(walls, seg(p, 0, 0.15), w=1.6)
    pen.path([(110, 206), (24, 206), (24, 30)], seg(p, 0.05, 0.2), w=1.6)
    pen.text((130, 212), "입구 · 봉은사역 7번 출구 동선", 8, PENCIL, anchor="ma") if p > 0.2 else None
    items = []
    for i in range(4):
        items.append(("r", 160 + (i % 2) * 64, 42 + (i // 2) * 44, 208 + (i % 2) * 64, 66 + (i // 2) * 44))
    for i in range(3):
        items.append(("r", 160 + i * 44, 140, 188 + i * 44, 156))
    for i in range(10):
        items.append(("c", 38 + (i % 5) * 18, 46 + (i // 5) * 18, 0, 0))
    items.append(("r", 34, 92, 56, 116))
    items.append(("r", 62, 92, 84, 116))
    items.append(("r", 34, 150, 130, 168))
    items.append(("r", 34, 182, 108, 198))
    k = seg(p, 0.2, 0.75) * len(items)
    for i, it in enumerate(items):
        q = max(0, min(1, k - i))
        if q <= 0:
            break
        if it[0] == "r":
            pen.rect(it[1], it[2], it[3], it[4], q, w=1.0)
        else:
            pen.circle(it[1], it[2], 5, q, w=0.8)
    if p > 0.75:
        pen.text((82, 159), "바리스타 바", 8, INK, anchor="mm")
        pen.text((71, 190), "픽업 90초", 8, ACC, bold=True, anchor="mm")
        pen.text((59, 122), "폰부스", 8, PENCIL, anchor="ma")
        pen.text((230, 116), "4인 미팅 ×4", 8, PENCIL, anchor="mm")
        pen.text((230, 164), "2인 ×6", 8, PENCIL, anchor="ma")
        pen.text((84, 80), "1인 바 ×10", 8, PENCIL, anchor="mm")
    seats = int(40 * seg(p, 0.2, 0.75))
    pen.text((390, 52), "좌석", 10, PENCIL, anchor="mm")
    pen.text((390, 82), f"{seats}석", 28, INK, bold=True, anchor="mm")
    mt = 70 * seg(p, 0.5, 0.85)
    pen.rect(330, 108, 450, 122, 1, w=0.8) if p > 0.5 else None
    if mt > 1:
        pen.hatch(330, 108, 330 + 120 * mt / 100, 122, 1, fill=ACC, gap=2.5)
    pen.text((390, 138), f"미팅 좌석 {mt:.0f}%", 11, ACC, bold=True, anchor="mm") if p > 0.5 else None
    if p > 0.85:
        pen.text((390, 164), "11~17시 거래 63% → 체류", 9, PENCIL, anchor="mm")
        pen.text((390, 180), "06~11시 18% → 테이크아웃", 9, PENCIL, anchor="mm")


def s_ticket(pen, p, t):
    G = M.G
    pen.text((24, 30), "커피 객단가 (원/건)", 11, INK, bold=True)
    rows = [("서울 상권 중앙값", M.prof["seoul"]["median_ticket_won"], PENCIL), ("강남 마이스 평균", G["ticket_won"], INK),
            ("우리 목표", 12000, ACC)]
    for i, (lab, v, c) in enumerate(rows):
        g = seg(p, i * 0.15, i * 0.15 + 0.4)
        y = 52 + i * 30
        pen.text((24, y + 1), lab, 10, c, bold=(c == ACC))
        if g > 0:
            pen.bar(124, y, 124 + v / 13000 * 150 * g, y + 15, 1, fill=c)
        if g > 0.95:
            pen.text((130 + v / 13000 * 150, y + 1), f"{v:,}", 10, c, bold=True)
    # 영수증
    q = seg(p, 0.3, 0.45)
    zz = [(330, 40), (466, 40), (466, 200)] + [(466 - i * 8, 200 + (4 if i % 2 else 0)) for i in range(1, 18)] + [(330, 200), (330, 40)]
    pen.path(zz, q, w=1.0)
    lines = [("RECEIPT", True, INK), ("음료 1.6잔 × 6,400", False, INK), ("= 10,240", True, INK), ("베이커리 0.4개 × 4,800", False, INK),
             ("= 1,920", True, INK), ("합계 12,160", True, ACC), ("→ 12,000원 (보수적)", False, GOOD)]
    k = int(len(lines) * seg(p, 0.45, 0.9))
    for i, (s, b, c) in enumerate(lines[:k]):
        pen.text((340, 48 + i * 20), s, 10 if i else 11, c, bold=b)
    if p > 0.6:
        pen.text((24, 156), "캐리어 4잔 세트 21,000원", 10, INK)
        pen.text((24, 172), "시그니처 6,800 · 7,200 · 8,500원", 10, INK)
        pen.text((24, 190), "스타벅스 톨 4,700원 대비 아메리카노 +800원", 9, PENCIL)


def s_waterfall(pen, p, t):
    pen.text((24, 30), "기본 시나리오 연간 손익 (억 원)", 11, INK, bold=True)
    b = M.pnlj["scenarios"]["base"]
    steps = [("매출", b["revenue"], INK, True), ("원가", -b["cogs"], PENCIL, False), ("인건비", -b["labor"], PENCIL, False),
             ("임대료", -b["rent"], PENCIL, False), ("본사·기타", -(b["hq"] + b["other"]), PENCIL, False),
             ("감가상각", -b["dep"], PENCIL, False), ("영업이익", b["op"], ACC, True)]
    top, bot = 64, 198
    sc = (bot - top) / b["revenue"]
    cur = 0
    k = seg(p, 0, 0.85) * len(steps)
    pen.line(24, bot, 456, bot, seg(p, 0, 0.1), w=0.8)
    for i, (lab, v, c, total) in enumerate(steps):
        x = 34 + i * 62
        if i > k:
            break
        g = min(1.0, k - i)
        if total:
            ya, yb = bot - v * sc * g, bot
            if lab == "매출":
                cur = v
        else:
            ya = bot - cur * sc
            yb = ya + (-v) * sc * g
        if abs(yb - ya) > 0.8:
            pen.bar(x, min(ya, yb), x + 40, max(ya, yb), 1, fill=c)
        if g >= 1:
            pen.text((x + 20, min(ya, yb) - 8), f"{abs(v)/1e8:.2f}", 9, c, bold=True, anchor="mm")
            if not total:
                pen.line(x - 22, ya, x, ya, 1, fill=PENCIL, w=0.5, dash=True, wobble=False)
                cur += v
        pen.text((x + 20, bot + 4), lab, 8, PENCIL, anchor="ma")
    if p > 0.9:
        pen.text((456, 32), "영업이익률 11.4%", 13, ACC, bold=True, anchor="ra")
        pen.underline(340, 456, 48, seg(p, 0.9, 1))


def s_cross(pen, p, t):
    pen.text((24, 30), "두 가지 방법으로 계산한 연매출 (억 원)", 11, INK, bold=True)
    cc = M.pnlj["cross_check"]
    rows = [("Bottom-up", "일 167건 × 12,000원 × 360일", cc["bottom_up_revenue"] / 1e8, INK),
            ("Top-down", "상권 점포당 6.33억 × 1.15 × 객단가 비", cc["top_down_revenue"] / 1e8, ACC)]
    for i, (lab, desc, v, c) in enumerate(rows):
        g = seg(p, i * 0.2, i * 0.2 + 0.5)
        y = 62 + i * 52
        pen.text((24, y), lab, 12, c, bold=True)
        pen.text((24, y + 18), desc, 9, PENCIL)
        if g > 0:
            pen.bar(200, y + 2, 200 + v * 32 * g, y + 22, 1, fill=c)
        if g > 0.95:
            pen.text((206 + v * 32, y + 6), f"{v:.2f}", 12, c, bold=True)
    q = seg(p, 0.7, 0.85)
    xr = 200 + 7.33 * 32 + 34
    pen.path([(xr - 8, 64), (xr, 64), (xr, 136), (xr - 8, 136)], q, fill=GOOD, w=1.2)
    if q >= 1:
        pen.text((W // 2, 160), f"차이 {cc['gap_pct']*100:+.1f}%", 16, GOOD, bold=True, anchor="mm")
        pen.text((W // 2, 184), "→ 두 계산이 사실상 일치", 12, GOOD, bold=True, anchor="mm")


def s_sens(pen, p, t):
    pen.text((24, 30), "객수가 바뀌면 영업이익률은? (기본 = 일 167건)", 11, INK, bold=True)
    x0, y0, x1, y1 = 50, 52, 330, 196
    lo, hi = -30, 30
    vmin, vmax = min(v for _, v in M.SENS), max(v for _, v in M.SENS)

    def pt(dx, v):
        return x0 + (x1 - x0) * (dx - lo) / (hi - lo), y1 - (y1 - y0) * (v - vmin) / (vmax - vmin)

    _, zy = pt(lo, 0)
    pen.line(x0, zy, x1, zy, seg(p, 0, 0.15), fill=PENCIL, w=0.8, dash=True, wobble=False)
    pen.text((x0 - 4, zy), "0%", 9, PENCIL, anchor="rm")
    pen.path([pt(dx, v) for dx, v in M.SENS], seg(p, 0.1, 0.65), fill=INK, w=1.6, wobble=False)
    for dx in (-20, 0, 20):
        x, _ = pt(dx, 0)
        pen.text((x, y1 + 6), f"{dx:+d}%", 9, PENCIL, anchor="ma")
    if p > 0.65:
        x, y = pt(0, [v for dx, v in M.SENS if dx == 0][0])
        pen.circle(x, y, 4, seg(p, 0.65, 0.75), fill=GOOD, w=1.2)
        pen.text((x + 8, y - 14), "기본 11.4%", 10, GOOD, bold=True)
        x2, y2 = pt(-20, [v for dx, v in M.SENS if dx == -20][0])
        pen.circle(x2, y2, 4, seg(p, 0.72, 0.82), fill=ACC, w=1.4)
        pen.text((x2 + 8, y2 + 2), "-20% → 적자", 10, ACC, bold=True)
    pen.rect(350, 52, 466, 196, seg(p, 0.3, 0.5), w=1.0)
    if p > 0.5:
        pen.text((408, 70), "손익분기", 10, PENCIL, anchor="mm")
        pen.text((408, 98), f"{M.pnlj['scenarios']['base']['breakeven_tx_day']}건/일", 20, INK, bold=True, anchor="mm")
        pen.line(364, 120, 452, 120, 1, fill=GRID, w=0.6)
        pen.text((408, 138), "상권 평균 점포", 9, PENCIL, anchor="mm")
        pen.text((408, 156), "145.5건/일", 12, INK, bold=True, anchor="mm")
        pen.text((408, 178), "여유 6%뿐", 11, ACC, bold=True, anchor="mm")


def s_quest1(pen, p, t):
    pen.text((24, 32), "조건 1 · 출점 전 4주 객수 실측", 13, ACC, bold=True)
    pen.text((24, 52), "봉은사역 7번 출구 동선 경쟁점, 시간대별", 10, PENCIL)
    for r in range(5):
        pen.line(40, 72 + r * 30, 250, 72 + r * 30, seg(p, 0, 0.2), w=0.8)
    for c in range(8):
        pen.line(40 + c * 30, 72, 40 + c * 30, 192, seg(p, 0.05, 0.25), w=0.8)
    k = int(28 * seg(p, 0.25, 0.85))
    for i in range(k):
        x = 40 + (i % 7) * 30
        y = 72 + (i // 7) * 30
        pen.path([(x + 8, y + 15), (x + 13, y + 21), (x + 23, y + 8)], 1, fill=GOOD, w=1.4, seed=i)
    pen.rect(280, 80, 462, 184, seg(p, 0.2, 0.4), w=1.2)
    if p > 0.4:
        pen.text((371, 100), "통과 조건", 10, PENCIL, anchor="mm")
        pen.text((371, 128), "일 150건 이상", 20, INK, bold=True, anchor="mm")
        pen.text((371, 156), "손익분기 136건 + 여유 10%", 9, PENCIL, anchor="mm")
    if k >= 28:
        pen.text((371, 174), "→ 통과 시 다음 단계", 10, GOOD, bold=True, anchor="mm")


def s_quest2(pen, p, t):
    pen.text((24, 32), "조건 2 · ㎡당 월 11만 원 이하 매물", 13, ACC, bold=True)
    pen.text((24, 52), "투자 회수 타임라인 (기본 시나리오)", 10, PENCIL)
    xa, xb, y = 44, 436, 112
    pen.arrow(xa, y, xb, y, seg(p, 0, 0.25), fill=INK)
    for yr in range(5):
        x = xa + (xb - xa - 10) * yr / 4
        pen.line(x, y - 4, x, y + 4, seg(p, 0.15, 0.3), w=1.0, wobble=False)
        pen.text((x, y + 10), f"{yr}년", 9, PENCIL, anchor="ma")
    pay = M.pnlj["scenarios"]["base"]["payback_years"]
    g = seg(p, 0.25, 0.7)
    xe = xa + (xb - xa - 10) * pay / 4
    if g > 0:
        pen.hatch(xa, y - 14, xa + (xe - xa) * g, y - 4, 1, fill=GOOD, gap=2.5)
    if g >= 1:
        pen.arrow(xe, y - 40, xe, y - 18, 1, fill=GOOD)
        pen.text((xe, y - 50), f"회수 {pay}년", 12, GOOD, bold=True, anchor="mm")
    q = seg(p, 0.7, 0.85)
    pen.rect(120, 150, 360, 200, q, w=1.2, fill=ACC)
    if q >= 1:
        pen.text((240, 166), "투자 3.3억 원 승인 요청", 13, ACC, bold=True, anchor="mm")
        pen.path([(200, 188), (240, 186), (280, 189)], seg(p, 0.85, 1), fill=INK, w=1.0)
        pen.text((240, 194), "서명", 8, PENCIL, anchor="ma")


SHOTS = [
    (s_map, "출처: 서울시 상권분석서비스 영역-상권(OA-15560) · 2026"),
    (s_kpi, "가정 포함 손익 모델(scripts/pnl.py) · 상권 데이터 2025Q3~2026Q2"),
    (s_tree, "출처: 상권분석서비스 추정매출·점포·인구·변화지표 · 2025Q3~2026Q2"),
    (s_quint, M.SRC_SALES + " · 2022→2025"),
    (s_41, M.SRC_SALES + " · 2022→2025, 매출 3억 원 이상 661곳"),
    (s_d3, "출처: 상권분석서비스 직장인구(OA-15569)·추정매출 · 2022→2025"),
    (s_series, M.SRC_SALES + " · 분기 · GTX: 뉴시스 2024.6.24"),
    (s_target, M.SRC_SALES + " · 강남 마이스 2025Q3~2026Q2"),
    (s_concept, "컨셉: 11~17시 거래 63% · 30~40대 매출 60%에서 도출"),
    (s_floor, "평면 개념도 · 전용 99㎡(가정) · 시간대 비중 OA-15572"),
    (s_ticket, M.SRC_SALES + " · 스타벅스 가격: 2025.1.24 인상"),
    (s_waterfall, "손익 모델 · 인건비: 2026 최저임금 10,320원 · 임대료 가정 A9"),
    (s_cross, "Top-down: 상권 점포당 커피 매출(OA-15572·15577) · 2025Q3~2026Q2"),
    (s_sens, "손익 모델 민감도 · 상권 점포당 일 145.5건(OA-15572·15577)"),
    (s_quest1, "손익분기 136건/일 = 고정비 ÷ 건당 공헌이익"),
    (s_quest2, "투자 = 시설 2.0억 + 보증금 12개월 (가정 A12·A13)"),
]


def render(idx, si, cap, p, t):
    im = Image.new("RGB", (W * S, H * S), PAPER)
    paper(im)
    pen = Pen(im)
    fn, src = SHOTS[idx]
    fn(pen, p, t)
    frame_chrome(pen, si, cap, src, p)
    return im


def wav_dur(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def main(preview=False):
    flat = [(si, sp, cap) for si, (_, ss) in enumerate(SCENES) for sp, cap in ss]
    if preview:
        for i, (si, _, cap) in enumerate(flat):
            render(i, si, cap, 1.0, 0.0).save(os.path.join(TMP, f"pv_{i:02d}.png"))
        print("preview done")
        return
    durs = []
    for i, (si, sp, cap) in enumerate(flat):
        wav = os.path.join(TMP, f"s{i:02d}.wav")
        txt = wav + ".txt"
        if not (os.path.exists(wav) and os.path.exists(txt) and open(txt, encoding="utf-8").read() == sp):
            R.tts(sp, wav, rate=2)
        durs.append(wav_dur(wav))
    pad = max(0.2, min(0.65, (TARGET_SEC - sum(durs)) / len(durs)))
    md = ["# 피치 영상 스크립트 (라인드로잉 버전)", "", "| 시작 | 장면 | 화면(근거) | 내레이션 |", "|---|---|---|---|"]
    clips, t0 = [], 0.0
    for i, (si, sp, cap) in enumerate(flat):
        wav = os.path.join(TMP, f"s{i:02d}.wav")
        dur = durs[i] + pad
        nfr = int(math.ceil(dur * FPS))
        mp4 = os.path.join(TMP, f"s{i:02d}.mp4")
        proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W*S}x{H*S}",
                                 "-r", str(FPS), "-i", "-", "-i", wav, "-af", f"highpass=f=70,volume=1.5,apad=pad_dur={pad:.3f}",
                                 "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                                 "-r", "24", "-c:a", "aac", "-ar", "44100", "-ac", "2", mp4], stdin=subprocess.PIPE)
        anim = max(1.0, dur * 0.8)
        for f in range(nfr):
            tt = f / FPS
            im = render(i, si, cap, tt / anim, tt)
            proc.stdin.write(im.tobytes())
            if i == 1 and f == nfr - 1:
                im.save(os.path.join(ROOT, "docs", "assets", "poster.png"))
        proc.stdin.close()
        proc.wait()
        md.append(f"| {int(t0 // 60)}:{t0 % 60:05.2f} | {SCENES[si][0]} | {SHOTS[i][0].__name__} | {sp} |")
        clips.append(mp4)
        t0 += dur
    lst = os.path.join(TMP, "list.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{c}'\n" for c in clips))
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(VID, "pitch.mp4")], check=True)
    md += ["", f"총 길이: {t0:.1f}초 (문장 간격 {pad:.2f}초 자동 조정)", "",
           "보관 버전: `pitch_pixel.mp4`(고해상도 픽셀 모션), `pitch_retro.mp4`(레트로 원본), `pitch_static.mp4`(정지화면 픽셀)"]
    open(os.path.join(VID, "script.md"), "w", encoding="utf-8").write("\n".join(md))
    print(f"total {t0:.1f}s pad {pad:.2f}")


if __name__ == "__main__":
    main(preview="--preview" in sys.argv)
