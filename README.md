# 커피 브랜드 신규 출점 전략 — 2029년 성장할 서울 상권

**결론**: 다음 매장은 강남 마이스 관광특구(삼성동 코엑스), 9호선 봉은사역 7번 출구 ↔ 코엑스 연결 동선.
기본 시나리오 기준 연매출 7.2억 원, 영업이익률 11.4%, 투자회수 2.7년.

- 웹 보고서: `docs/index.html` (GitHub Pages)
- 피치 영상: `docs/video/pitch.mp4` (약 2분, 라인드로잉 데이터 애니메이션) · 보관: `pitch_pixel.mp4`(픽셀 모션), `pitch_static.mp4`(픽셀 정지화면), `pitch_retro.mp4`(레트로 원본)

## 데이터 출처

서울 열린데이터광장 · 서울시 상권분석서비스(2021Q1~2026Q2)
- 추정매출-상권 OA-15572 · 점포-상권 OA-15577 · 상권변화지표-상권 OA-15576
- 길단위인구-상권 OA-15568 · 직장인구-상권 OA-15569 · 상주인구-상권 OA-15584 · 집객시설-상권 OA-15580 · 영역-상권 OA-15560

외부 출처(임대료·최저임금·교통 호재·가격)는 `shared/evidence.csv` 참고.

## 재현 방법

```bash
echo SEOUL_API_KEY=<서울 열린데이터광장 인증키> > .env
pip install numpy pillow
python scripts/collect.py       # 원본 수집 → data/raw
python scripts/analyze.py       # 지표·상관·백테스트·점수 → data/processed
python scripts/select_area.py   # 선별 깔때기·인사이트
python scripts/profile_area.py  # 추천 상권 고객 프로필
python scripts/pnl.py           # 손익 3시나리오·민감도
python scripts/evidence.py      # 근거 원장 생성·재조회 검증
python scripts/build_page.py    # docs/index.html
python scripts/make_video_line.py     # docs/video/pitch.mp4 (메인: 라인드로잉, Windows SAPI 한국어 음성 + ffmpeg)
python scripts/make_video_motion.py   # docs/video/pitch_pixel.mp4 (보관용 픽셀 모션판)
python scripts/make_video_refined.py  # 정지화면판 (출력 경로를 pitch_static.mp4로 바꿔 사용)
python scripts/make_video_retro.py    # docs/video/pitch_retro.mp4 (보관용 레트로 버전)
```

## 폴더

- `shared/` 에이전트 간 계약 문서(브리프, 지표 설계, 컨셉, 인사이트, 공간, 메뉴, 손익, 가정, 근거 원장, 레드팀)
- `data/raw` 원본 · `data/processed` 분석 결과 · `scripts/` 재현 코드 · `docs/` 웹 루트

## 팀

{팀원}
