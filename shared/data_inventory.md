# 데이터 인벤토리 (Phase 0)

점검일: 2026-11-14

## 1. seoul-opendata MCP (카탈로그 28개, 인증키 불필요)

| 데이터셋 | id / 도구 | 쓸 수 있는 정도 | 비고 |
|---|---|---|---|
| 골목상권 추정매출 | `VwsmTrdarSelngQq` | 샘플만 | 전체 481,462행. `params:["20211"]`로 분기 필터는 됨(2021Q1 22,239행). 하지만 호출당 최대 50행, 페이지 이동·업종·상권 필터가 없어 같은 50행만 반복됨 → 시계열 구축 불가 |
| 실시간 상권 | `get_commercial_activity` | 보조 | 신한카드 실시간 결제, 핫스팟 82곳 |
| 생활인구(행정동) | `get_living_population` | 보조 | 날짜·행정동·시간대 단위 조회 |
| 지하철 승하차 | `get_subway_ridership` | 보조 | 일별 역별 |
| 부동산 실거래가 | `get_real_estate_prices` | 보조 | 임대료 대용지표 후보 |

카탈로그에 없는 것: 점포 수(개폐업률), 상권변화지표, 상주·직장인구, 소득소비, 집객시설.

## 2. 서울 열린데이터광장 REST API (인증키 필요)

`http://openapi.seoul.go.kr:8088/{KEY}/json/{SERVICE}/{START}/{END}/` 형식, 호출당 1,000행.
필요 서비스(상권분석서비스): 추정매출, 점포, 상권변화지표, 길단위인구, 상주인구, 직장인구, 소득소비, 집객시설, 아파트.

상태: 2026-11-14 키 확인 완료(INFO-000). 분기 필터(`.../{START}/{END}/{YYYYQ}`)는 되고 업종 필터는 안 됨.

| 서비스 | 내용 | 기간 | 수집 |
|---|---|---|---|
| VwsmTrdarSelngQq | 추정매출-상권 | 2021Q1~2026Q2 | 분기 전량 → 커피-음료·제과점만 저장 |
| VwsmTrdarStorQq | 점포-상권 (점포수·개폐업·프랜차이즈) | 2021Q1~2026Q2 | 분기 전량 → 커피-음료·제과점만 저장 |
| VwsmTrdarIxQq | 상권변화지표 (LL/LH/HL/HH, 운영·폐업 영업개월) | 2021Q1~ | 전량 |
| VwsmTrdarFlpopQq | 길단위인구(유동) | 분기 | 전량 |
| VwsmTrdarRepopQq | 상주인구 | 분기 | 전량 |
| VwsmTrdarWrcPopltnQq | 직장인구 | 분기 | 전량 |
| VwsmTrdarFcltyQq | 집객시설 | 분기 | 전량 |
| TbgisTrdarRelm | 상권영역(좌표·자치구·행정동) | 현재 | 1,650개 상권 |
| VwsmTrdarNcmCnsmpQq / VwsmTrdarAptQq | 소득소비 / 아파트 | — | ERROR-500으로 제외 |

2021Q1 이전 매출 데이터가 API에 없음(INFO-200) → 백테스트는 2021 지표 → 2021~2024 매출 성장으로 설계.
수집 스크립트: `scripts/collect.py`, 로그: `data/raw/collect_log.csv`

## 3. 로컬 도구

| 도구 | 상태 |
|---|---|
| python | C:\Python314\python.exe |
| ffmpeg | winget Gyan.FFmpeg 9.0.2 설치 완료 (2026-11-14). 새 셸 전까지 PATH 미반영 → `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe` |
| TTS | Windows SAPI 한국어 음성 `Microsoft Heami Desktop` 있음. edge-tts는 미설치 |
| git / gh | 있음, gh 로그인됨 |
| node | 있음 |

## Gate 0 판정

**통과 (2026-11-14).** 추정매출 시계열·점포 수·유동인구 모두 REST API로 확보 가능.
