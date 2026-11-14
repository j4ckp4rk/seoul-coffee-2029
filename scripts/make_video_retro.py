"""레트로 픽셀아트 피치 영상: 문장별 TTS(Windows SAPI 한국어) + 320x180 도트 화면 x4 확대 + ffmpeg 합성.

사용: python scripts/make_video.py
출력: docs/video/pitch_retro.mp4, docs/video/script_retro.md, docs/assets/poster_retro.png (보관용 레트로 버전)
"""
import glob
import json
import os
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "data", "video_tmp")
VID = os.path.join(ROOT, "docs", "video")
os.makedirs(TMP, exist_ok=True)
os.makedirs(VID, exist_ok=True)
FF = glob.glob(os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"))[0]
FONT = "C:/Windows/Fonts/malgunbd.ttf"
W, H, S = 320, 180, 4

# 팔레트 (PICO-8 계열)
BG, NAVY, PURP, GREEN, BROWN, GRAY, LGRAY, WHITE = "#1d2b53", "#1d2b53", "#7e2553", "#008751", "#ab5236", "#5f574f", "#c2c3c7", "#fff1e8"
RED, ORANGE, YELLOW, LIME, BLUE, PINK, PEACH, BLACK = "#ff004d", "#ffa300", "#ffec27", "#00e436", "#29adff", "#ff77a8", "#ffccaa", "#000000"

# (장면, 문장) — 숫자는 TTS가 읽기 쉽게 한글 표기, 자막은 숫자 표기
SCENES = [
    ("STAGE 1 · 결론", [
        ("스테이지 원, 결론부터 간다! 다음 매장은 삼성동 코엑스, 봉은사역 7번 출구!",
         "결론: 다음 매장은 삼성동 코엑스, 봉은사역 7번 출구!"),
        ("획득 보상은 연매출 칠억 이천만 원, 영업이익률 십일 점 사 퍼센트, 투자회수 이 점 칠 년!",
         "연매출 7.2억 · 영업이익률 11.4% · 투자회수 2.7년"),
    ]),
    ("STAGE 2 · 왜 여기인가", [
        ("스테이지 투! 서울 커피 상권 육백칠십팔 곳을 수요, 공급, 모멘텀, 리스크 열두 개 지표로 점수화했습니다.",
         "서울 커피 상권 678곳 × 지표 12개로 점수화"),
        ("이천이십이년 지표로 삼 년 뒤를 맞혀 보니, 점수 상위 십 퍼센트는 연 삼 점 사 퍼센트 성장했고, 전체 평균은 마이너스였습니다.",
         "백테스트: 점수 상위 10% 연 +3.4% vs 전체 평균 -0.7%"),
        ("여기서 반전! 이천이십이년 매출 상위 십 퍼센트 상권의 사십일 퍼센트가 삼 년 뒤 역성장했다는 것입니다.",
         "반전! 매출 상위 10% 상권의 41%가 3년 뒤 역성장"),
        ("삼 년 성장을 가른 건 매출 규모가 아니라 직장인구였습니다.",
         "승부를 가른 건 매출 규모가 아니라 직장인구"),
        ("강남 마이스 특구는 직장인구 십만 명, 커피 매출이 삼 년 새 팔십팔 퍼센트 늘었고, 이천이십팔년 지티엑스 에이 삼성역이 열립니다.",
         "직장인구 10.2만 · 커피 매출 +88% · 2028 GTX-A 삼성역"),
    ]),
    ("STAGE 3 · 타깃·공간·메뉴", [
        ("스테이지 쓰리! 고객은 삼십대와 사십대가 매출의 육십 퍼센트, 거래의 육십삼 퍼센트가 오전 열한 시부터 오후 다섯 시에 몰립니다.",
         "30~40대 매출 60% · 11~17시 거래 63%"),
        ("그래서 컨셉은, 미팅과 미팅 사이 삼십 분, 프리미엄 미팅 라운지 커피입니다.",
         "컨셉: 미팅과 미팅 사이 30분, 프리미엄 미팅 라운지"),
        ("사십 석 중 칠십 퍼센트를 미팅 좌석으로, 아침에는 구십 초 픽업 바를 둡니다.",
         "40석 중 70% 미팅 좌석 + 아침 90초 픽업 바"),
        ("객단가 만 이천 원은 단체 캐리어 세트와 시그니처 세 종으로 만듭니다.",
         "객단가 12,000원 = 캐리어 세트 + 시그니처 3종"),
    ]),
    ("STAGE 4 · 손익", [
        ("스테이지 포! 하루 백육십칠 건, 객단가 만 이천 원이면 연매출 칠억 이천만 원, 영업이익 팔천이백만 원입니다.",
         "일 167건 × 12,000원 = 연 7.2억, 영업이익 0.82억"),
        ("상권 평균 점포 매출로 계산한 값과 일 점 사 퍼센트 차이로 일치합니다.",
         "Top-down 교차검증 차이 -1.4%"),
        ("다만 손익분기는 하루 백삼십육 건이라, 객수가 이십 퍼센트 줄면 적자입니다.",
         "주의: 손익분기 일 136건, 객수 -20%면 적자"),
    ]),
    ("STAGE 5 · 요청", [
        ("마지막 퀘스트! 출점 전 사 주 동안 같은 동선의 객수를 실측하고,",
         "QUEST 1: 출점 전 4주 객수 실측"),
        ("임대료가 제곱미터당 십일만 원 이하인 매물이 나오면, 삼억 삼천만 원 투자를 승인해 주세요. 게임 스타트!",
         "QUEST 2: ㎡당 11만 원 이하 매물 → 3.3억 투자 승인"),
    ]),
]


def tts(text, path, rate=2):
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.SelectVoice('Microsoft Heami Desktop');"
        f"$s.Rate={rate};"
        f"$s.SetOutputToWaveFile('{path}');"
        f"$s.Speak([IO.File]::ReadAllText('{path}.txt',[Text.Encoding]::UTF8));$s.Dispose()"
    )
    open(path + ".txt", "w", encoding="utf-8").write(text)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def font(sz):
    return ImageFont.truetype(FONT, sz)


def px_text(d, xy, text, sz, fill, shadow=BLACK):
    f = font(sz)
    x, y = xy
    if shadow:
        d.text((x + 1, y + 1), text, font=f, fill=shadow)
    d.text((x, y), text, font=f, fill=fill)


def sprite(d, x, y, rows, pal, k=1):
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c != ".":
                d.rectangle([x + i * k, y + j * k, x + i * k + k - 1, y + j * k + k - 1], fill=pal[c])


CUP = ["..s.s...", "...s.s..", "wwwwww..", "wbbbbwww", "wbbbbw.w", "wbbbbwww", "wbbbbw..", ".wwww...", "gggggg.."]
CUP_P = {"s": LGRAY, "w": WHITE, "b": BROWN, "g": GRAY}
FLAG = ["rrrr", "rrrrr", "rrrr", "l...", "l...", "l...", "l..."]
FLAG_P = {"r": RED, "l": WHITE}
COIN = [".yyy.", "yyoyy", "yoyoy", "yyoyy", ".yyy."]
COIN_P = {"y": YELLOW, "o": ORANGE}


def frame(scene_idx, title, caption, t_scene):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    # 상단 HUD
    d.rectangle([0, 0, W, 13], fill=BLACK)
    px_text(d, (4, 1), title, 9, YELLOW, None)
    px_text(d, (230, 1), "SAMSEONG MICE", 9, LIME, None)
    # 별 배경
    for i in range(30):
        d.point(((i * 53) % W, 16 + (i * 29) % 90), fill=GRAY)
    if scene_idx == 0:
        # 지도: 도로 + 역 + 깃발
        d.rectangle([20, 70, 300, 78], fill=GRAY)      # 봉은사로
        d.rectangle([180, 20, 188, 120], fill=GRAY)    # 영동대로
        d.rectangle([110, 30, 170, 66], fill=PURP)     # 코엑스
        px_text(d, (118, 40), "COEX", 10, WHITE)
        d.rectangle([192, 82, 230, 98], fill=BLUE)
        px_text(d, (194, 84), "봉은사7", 8, WHITE, None)
        sprite(d, 172, 50, FLAG, FLAG_P, 2)
        sprite(d, 40, 30, CUP, CUP_P, 3)
        # KPI 3 박스
        for i, (k, v) in enumerate([("연매출", "7.2억"), ("영업이익률", "11.4%"), ("회수", "2.7년")]):
            x = 236 + 0
            y = 22 + i * 20
            d.rectangle([x, y, x + 80, y + 17], fill=BLACK, outline=YELLOW)
            px_text(d, (x + 3, y + 3), f"{k} {v}", 8, WHITE, None)
    elif scene_idx == 1:
        bars = [("점수 상위10%", 3.4, LIME), ("매출 상위10%", 0.8, ORANGE), ("전체 평균", -0.7, RED)]
        base_y = 85
        d.line([20, base_y, 200, base_y], fill=WHITE)
        for i, (lab, v, c) in enumerate(bars):
            x = 30 + i * 60
            h = int(v * 14)
            if h >= 0:
                d.rectangle([x, base_y - h, x + 30, base_y], fill=c)
            else:
                d.rectangle([x, base_y, x + 30, base_y - h], fill=c)
            px_text(d, (x - 4, 100), lab, 7, WHITE, None)
            px_text(d, (x + 2, base_y - max(h, 0) - 12), f"{v:+.1f}%", 8, c)
        px_text(d, (210, 22), "3년 CAGR", 9, LGRAY, None)
        d.rectangle([212, 40, 312, 110], fill=BLACK, outline=RED)
        px_text(d, (222, 46), "CRITICAL!", 9, RED, None)
        px_text(d, (222, 62), "41%", 22, YELLOW)
        px_text(d, (218, 92), "매출TOP 역성장", 8, WHITE, None)
    elif scene_idx == 2:
        # 평면도
        d.rectangle([20, 22, 200, 112], fill="#3b2e2a", outline=PEACH)
        for i in range(4):
            d.rectangle([110 + (i % 2) * 44, 30 + (i // 2) * 24, 140 + (i % 2) * 44, 46 + (i // 2) * 24], fill=BROWN)
        for i in range(6):
            d.rectangle([110 + (i % 3) * 30, 82 + 0 * 1, 124 + (i % 3) * 30, 92], fill=ORANGE) if i < 3 else None
        for i in range(10):
            d.rectangle([28 + i * 7, 28, 32 + i * 7, 32], fill=PEACH)
        d.rectangle([28, 40, 40, 52], fill=BLUE)
        d.rectangle([44, 40, 56, 52], fill=BLUE)
        d.rectangle([28, 70, 96, 84], fill=GRAY)
        px_text(d, (32, 72), "BAR", 8, WHITE, None)
        d.rectangle([20, 100, 80, 112], fill=GREEN)
        px_text(d, (24, 101), "PICKUP 90s", 7, WHITE, None)
        px_text(d, (210, 24), "40석", 12, YELLOW)
        px_text(d, (210, 44), "미팅좌석 70%", 9, WHITE, None)
        px_text(d, (210, 60), "30~40대 60%", 9, LIME, None)
        px_text(d, (210, 76), "11~17시 63%", 9, BLUE, None)
        sprite(d, 270, 92, CUP, CUP_P, 2)
    elif scene_idx == 3:
        items = [("매출", 7.23, BLUE), ("원가", 2.10, ORANGE), ("인건비", 1.88, PINK), ("임대료", 1.31, PURP),
                 ("기타", 1.13, GRAY), ("영업익", 0.82, LIME)]
        for i, (lab, v, c) in enumerate(items):
            y = 22 + i * 15
            px_text(d, (10, y), lab, 8, WHITE, None)
            d.rectangle([52, y + 2, 52 + int(v * 26), y + 10], fill=c)
            px_text(d, (56 + int(v * 26), y), f"{v:.2f}억", 8, c, None)
        d.rectangle([250, 22, 314, 66], fill=BLACK, outline=YELLOW)
        px_text(d, (254, 26), "BEP", 9, YELLOW, None)
        px_text(d, (254, 40), "136건/일", 9, WHITE, None)
        sprite(d, 270, 74, COIN, COIN_P, 3)
        sprite(d, 290, 80, COIN, COIN_P, 3)
    else:
        d.rectangle([30, 24, 290, 110], fill=BLACK, outline=LIME)
        px_text(d, (40, 28), "NEW QUEST", 11, LIME, None)
        px_text(d, (40, 50), "□ 4주 시간대별 객수 실측 (150건+)", 9, WHITE, None)
        px_text(d, (40, 66), "□ ㎡당 11만원 이하 매물 확보", 9, WHITE, None)
        px_text(d, (40, 82), "▶ 투자 3.3억 승인", 11, YELLOW, None)
        sprite(d, 250, 80, CUP, CUP_P, 2)
    # 대화창
    d.rectangle([4, 124, W - 5, H - 5], fill=BLACK, outline=WHITE)
    d.rectangle([6, 126, W - 7, H - 7], outline=GRAY)
    words = caption
    lines, cur = [], ""
    f = font(10)
    for ch in words:
        if d.textlength(cur + ch, font=f) > W - 26:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    lines.append(cur)
    for i, ln in enumerate(lines[:3]):
        px_text(d, (12, 132 + i * 13), ln, 10, WHITE, None)
    d.polygon([(W - 16, H - 14), (W - 10, H - 14), (W - 13, H - 10)], fill=YELLOW)
    return im.resize((W * S, H * S), Image.NEAREST)


def main():
    clips, script_md, t = [], ["# 피치 영상 스크립트 (자동 생성)", "", "| 시작 | 장면 | 내레이션 |", "|---|---|---|"], 0.0
    n = 0
    for si, (title, sents) in enumerate(SCENES):
        for speak, cap in sents:
            wav = os.path.join(TMP, f"s{n:02d}.wav")
            dur = tts(speak, wav)
            png = os.path.join(TMP, f"s{n:02d}.png")
            frame(si, title, cap, 0).save(png)
            if n == 0:
                frame(si, title, cap, 0).save(os.path.join(ROOT, "docs", "assets", "poster_retro.png"))
            pad = 0.3
            mp4 = os.path.join(TMP, f"s{n:02d}.mp4")
            subprocess.run([FF, "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", wav, "-af", f"asetrate=22050*1.12,aresample=44100,atempo=0.893,acrusher=bits=8:mode=log:aa=1:mix=0.35,highpass=f=180,lowpass=f=6000,volume=1.6,apad=pad_dur={pad}",
                            "-t", f"{dur + pad:.3f}", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                            "-r", "24", "-c:a", "aac", "-ar", "44100", "-ac", "2", mp4], check=True)
            script_md.append(f"| {int(t // 60)}:{t % 60:05.2f} | {title} | {speak} |")
            clips.append(mp4)
            t += dur + pad
            n += 1
    lst = os.path.join(TMP, "list.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{c}'\n" for c in clips))
    out = os.path.join(VID, "pitch_retro.mp4")
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    script_md += ["", f"총 길이: {t:.1f}초"]
    open(os.path.join(VID, "script_retro.md"), "w", encoding="utf-8").write("\n".join(script_md))
    print(json.dumps({"total_sec": round(t, 1), "first_scene_end": None}))


if __name__ == "__main__":
    main()  # 레트로 버전. 메인 영상은 scripts/make_video_refined.py
