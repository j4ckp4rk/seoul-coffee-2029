"""세련된 픽셀 스타일 피치 영상 (메인).

- 내레이션·TTS·게임 보이스 필터는 레트로 버전(make_video_retro.py)과 동일
- 화면: 480x270 픽셀 캔버스 → 4배 nearest 확대(1920x1080), 정돈된 그리드·고대비 자막
사용: python scripts/make_video_refined.py
출력: docs/video/pitch.mp4, docs/video/script.md, docs/assets/poster.png
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_video_retro as R  # noqa: E402

ROOT, TMP, VID, FF = R.ROOT, os.path.join(R.ROOT, "data", "video_tmp", "refined"), R.VID, R.FF
os.makedirs(TMP, exist_ok=True)
W, H, S = 480, 270, 4
BOLD, REG = "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"

# 절제된 팔레트: 배경 2톤 + 텍스트 2톤 + 강조 3색
BG, PANEL, LINE = "#141a2e", "#1e2642", "#2e3860"
TXT, MUTED = "#f4efe6", "#9aa1ba"
AMBER, MINT, CORAL = "#f2a541", "#5fd3a8", "#ef6f6c"
STAGES = ["결론", "왜 여기", "타깃·공간·메뉴", "손익", "요청"]

_fc = {}


def F(sz, bold=True):
    k = (sz, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(BOLD if bold else REG, sz)
    return _fc[k]


def T(d, xy, s, sz, fill=TXT, bold=True, anchor="la"):
    d.text(xy, s, font=F(sz, bold), fill=fill, anchor=anchor)


def box(d, x0, y0, x1, y1, fill=PANEL, outline=LINE, notch=3):
    """모서리를 계단형으로 깎은 픽셀 패널."""
    d.rectangle([x0 + notch, y0, x1 - notch, y1], fill=fill)
    d.rectangle([x0, y0 + notch, x1, y1 - notch], fill=fill)
    if outline:
        d.line([x0 + notch, y0, x1 - notch, y0], fill=outline)
        d.line([x0 + notch, y1, x1 - notch, y1], fill=outline)
        d.line([x0, y0 + notch, x0, y1 - notch], fill=outline)
        d.line([x1, y0 + notch, x1, y1 - notch], fill=outline)
        for (ax, ay, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
            for i in range(notch):
                d.point((ax + sx * (notch - i), ay + sy * i), fill=outline)


def sprite(d, x, y, rows, pal, k=2):
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c != ".":
                d.rectangle([x + i * k, y + j * k, x + i * k + k - 1, y + j * k + k - 1], fill=pal[c])


CUP = ["...m.m....", "....m.m...", "..........", "cccccccc..", "cbbbbbbccc", "cbbbbbbc.c", "cbbbbbbc.c",
       "cbbbbbbccc", "cbbbbbbc..", ".cccccc...", "dddddddd.."]
CUP_P = {"m": MUTED, "c": TXT, "b": "#8a4b2a", "d": LINE}
PIN = [".aaa.", "aaaaa", "aa.aa", "aaaaa", ".aaa.", "..a..", "..a.."]
PIN_P = {"a": CORAL}
COIN = [".aaa.", "aabaa", "abaaa", "aabaa", ".aaa."]
COIN_P = {"a": AMBER, "b": "#ffd27f"}


def hud(d, si):
    d.rectangle([0, 0, W, 22], fill="#0e1322")
    box(d, 8, 4, 8 + 18 + d.textlength(f"STAGE {si+1}", font=F(9)), 18, fill=AMBER, outline=None, notch=2)
    T(d, (17, 6), f"STAGE {si+1}", 9, BG)
    T(d, (78, 5), STAGES[si], 10, TXT)
    # 5칸 진행 바
    for i in range(5):
        x = W - 8 - (5 - i) * 22
        d.rectangle([x, 9, x + 18, 14], fill=AMBER if i <= si else LINE)


def caption(d, text):
    box(d, 8, 210, W - 9, H - 9, fill="#0e1322", outline=LINE)
    f = F(15)
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > W - 44:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    lines.append(cur)
    y0 = 218 if len(lines) > 1 else 228
    for i, ln in enumerate(lines[:2]):
        T(d, (22, y0 + i * 20), ln, 15, TXT)
    d.rectangle([W - 22, H - 21, W - 17, H - 18], fill=AMBER)


def kpi(d, x, y, w, label, value, color):
    box(d, x, y, x + w, y + 46)
    T(d, (x + 10, y + 7), label, 9, MUTED, bold=False)
    T(d, (x + 10, y + 20), value, 18, color)


def bar_h(d, x, y, w, h, color):
    """끝이 계단형인 픽셀 막대."""
    if w <= 0:
        return
    d.rectangle([x, y, x + w - 2, y + h], fill=color)
    d.rectangle([x + w - 2, y + 1, x + w, y + h - 1], fill=color)


def scene(si, cap):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    hud(d, si)
    if si == 0:
        T(d, (16, 34), "다음 매장", 11, MUTED, bold=False)
        T(d, (16, 48), "삼성동 코엑스", 26, TXT)
        T(d, (16, 82), "봉은사역 7번 출구 ↔ 코엑스 연결 동선", 11, AMBER)
        for i, (lab, val, c) in enumerate([("예상 연매출", "7.2억 원", AMBER), ("영업이익률", "11.4%", MINT), ("투자회수", "2.7년", TXT)]):
            kpi(d, 16 + i * 96, 108, 88, lab, val, c)
        # 미니 지도
        box(d, 318, 32, 470, 200)
        d.rectangle([326, 120, 462, 127], fill=LINE)          # 봉은사로
        d.rectangle([404, 40, 411, 192], fill=LINE)           # 영동대로
        box(d, 334, 52, 396, 110, fill="#3a2f55", outline=None, notch=2)
        T(d, (365, 76), "COEX", 10, TXT, anchor="mm")
        sprite(d, 391, 96, PIN, PIN_P, 3)
        T(d, (330, 136), "봉은사역 7", 9, MUTED, bold=False)
        T(d, (330, 176), "GTX-A 삼성역 2028↓", 9, MINT)
        sprite(d, 420, 140, CUP, CUP_P, 3)
    elif si == 1:
        T(d, (16, 34), "3년 커피 매출 연평균 성장률 (2022→2025)", 11, MUTED, bold=False)
        rows = [("지표 상위 10%", 3.4, MINT), ("매출 상위 10%", 0.8, AMBER), ("전체 평균", -0.7, CORAL)]
        zero = 140
        for i, (lab, v, c) in enumerate(rows):
            y = 60 + i * 34
            T(d, (16, y + 3), lab, 11, TXT)
            w = int(abs(v) * 34)
            if v >= 0:
                bar_h(d, zero, y, w, 16, c)
                T(d, (zero + w + 6, y + 2), f"{v:+.1f}%", 12, c)
            else:
                d.rectangle([zero - w, y, zero, y + 16], fill=c)
                T(d, (zero + 6, y + 2), f"{v:+.1f}%", 12, c)
        d.line([zero, 54, zero, 168], fill=MUTED)
        box(d, 330, 40, 470, 196)
        T(d, (400, 56), "반전", 11, CORAL, anchor="mm")
        T(d, (400, 96), "41%", 36, TXT, anchor="mm")
        T(d, (400, 130), "매출 상위 10% 상권 중", 9, MUTED, bold=False, anchor="mm")
        T(d, (400, 144), "3년 뒤 역성장", 11, TXT, anchor="mm")
        d.line([346, 160, 454, 160], fill=LINE)
        T(d, (400, 174), "성장의 열쇠 = 직장인구", 10, MINT, anchor="mm")
    elif si == 2:
        T(d, (16, 34), "컨셉", 11, MUTED, bold=False)
        T(d, (16, 48), "미팅과 미팅 사이 30분", 20, TXT)
        T(d, (16, 76), "프리미엄 미팅 라운지 커피", 12, AMBER)
        stats = [("30~40대 매출", "60%", MINT), ("11~17시 거래", "63%", AMBER), ("객단가 목표", "12,000원", TXT)]
        for i, (lab, val, c) in enumerate(stats):
            kpi(d, 16 + i * 96, 108, 88, lab, val, c)
        # 평면도
        box(d, 318, 32, 470, 200)
        for i in range(4):
            box(d, 384 + (i % 2) * 42, 44 + (i // 2) * 30, 418 + (i % 2) * 42, 64 + (i // 2) * 30, fill="#8a4b2a", outline=None, notch=1)
        for i in range(3):
            d.rectangle([386 + i * 28, 112, 404 + i * 28, 124], fill=AMBER)
        for i in range(6):
            d.rectangle([328 + i * 9, 44, 334 + i * 9, 50], fill="#e9c9a5")
        d.rectangle([328, 58, 344, 74], fill="#3c7ddc")
        d.rectangle([348, 58, 364, 74], fill="#3c7ddc")
        d.rectangle([328, 140, 400, 154], fill=LINE)
        T(d, (364, 147), "BAR", 9, TXT, anchor="mm")
        d.rectangle([328, 172, 400, 188], fill="#2f8f6b")
        T(d, (364, 180), "PICKUP 90s", 8, TXT, anchor="mm")
        T(d, (436, 172), "40석", 12, TXT, anchor="mm")
        T(d, (436, 188), "미팅 70%", 9, MINT, anchor="mm")
    elif si == 3:
        T(d, (16, 34), "기본 시나리오 · 연간 (억 원)", 11, MUTED, bold=False)
        items = [("매출", 7.23, AMBER), ("원가", 2.10, MUTED), ("인건비", 1.88, MUTED), ("임대료", 1.31, MUTED),
                 ("기타", 1.12, MUTED), ("영업이익", 0.82, MINT)]
        for i, (lab, v, c) in enumerate(items):
            y = 54 + i * 24
            T(d, (16, y + 1), lab, 11, TXT if c != MUTED else MUTED)
            bar_h(d, 80, y, int(v * 26), 14, c)
            T(d, (86 + int(v * 26), y + 1), f"{v:.2f}", 11, c)
        box(d, 330, 40, 470, 196)
        T(d, (400, 58), "손익분기", 10, MUTED, bold=False, anchor="mm")
        T(d, (400, 86), "136건/일", 20, TXT, anchor="mm")
        d.line([346, 108, 454, 108], fill=LINE)
        T(d, (400, 124), "교차검증 차이", 10, MUTED, bold=False, anchor="mm")
        T(d, (400, 146), "-1.4%", 18, MINT, anchor="mm")
        T(d, (400, 176), "객수 -20%면 적자", 10, CORAL, anchor="mm")
    else:
        T(d, (16, 34), "NEXT QUEST", 11, AMBER)
        T(d, (16, 50), "투자 승인 조건", 22, TXT)
        quests = [("1", "출점 전 4주, 같은 동선 객수 실측", "목표 일 150건 이상"),
                  ("2", "㎡당 월 11만 원 이하 매물 확보", "임대료 상한")]
        for i, (n, a, b) in enumerate(quests):
            y = 88 + i * 42
            box(d, 16, y, 300, y + 34)
            box(d, 24, y + 8, 42, y + 26, fill=AMBER, outline=None, notch=2)
            T(d, (33, y + 17), n, 11, BG, anchor="mm")
            T(d, (52, y + 5), a, 11, TXT)
            T(d, (52, y + 20), b, 9, MUTED, bold=False)
        box(d, 318, 60, 470, 170, fill="#20314a", outline=MINT)
        T(d, (394, 84), "보상", 10, MUTED, bold=False, anchor="mm")
        T(d, (394, 112), "투자 3.3억", 18, MINT, anchor="mm")
        T(d, (394, 140), "회수 2.7년", 12, TXT, anchor="mm")
        sprite(d, 330, 182, COIN, COIN_P, 3)
        sprite(d, 348, 186, COIN, COIN_P, 3)
    caption(d, cap)
    return im.resize((W * S, H * S), Image.NEAREST)


def main():
    clips, md, t, n = [], ["# 피치 영상 스크립트 (세련된 픽셀 버전)", "", "| 시작 | 장면 | 내레이션 |", "|---|---|---|"], 0.0, 0
    for si, (title, sents) in enumerate(R.SCENES):
        for speak, cap in sents:
            wav = os.path.join(TMP, f"s{n:02d}.wav")
            dur = R.tts(speak, wav)
            png = os.path.join(TMP, f"s{n:02d}.png")
            img = scene(si, cap)
            img.save(png)
            if n == 1:  # KPI가 보이는 화면을 포스터로
                img.save(os.path.join(ROOT, "docs", "assets", "poster.png"))
            pad = 0.3
            mp4 = os.path.join(TMP, f"s{n:02d}.mp4")
            subprocess.run([FF, "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav, "-af",
                            f"asetrate=22050*1.12,aresample=44100,atempo=0.893,acrusher=bits=8:mode=log:aa=1:mix=0.25,"
                            f"highpass=f=150,lowpass=f=7000,volume=1.6,apad=pad_dur={pad}",
                            "-t", f"{dur + pad:.3f}", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                            "-r", "24", "-c:a", "aac", "-ar", "44100", "-ac", "2", mp4], check=True)
            md.append(f"| {int(t // 60)}:{t % 60:05.2f} | {title} | {speak} |")
            clips.append(mp4)
            t += dur + pad
            n += 1
    lst = os.path.join(TMP, "list.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{c}'\n" for c in clips))
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(VID, "pitch.mp4")], check=True)
    md += ["", f"총 길이: {t:.1f}초", "", "보관용 레트로 버전: `pitch_retro.mp4` / `script_retro.md`"]
    open(os.path.join(VID, "script.md"), "w", encoding="utf-8").write("\n".join(md))
    print(f"total {t:.1f}s")


if __name__ == "__main__":
    if "--preview" in sys.argv:
        for si, (_, sents) in enumerate(R.SCENES):
            scene(si, sents[-1][1]).save(os.path.join(TMP, f"preview_{si}.png"))
        print("previews in", TMP)
    else:
        main()
