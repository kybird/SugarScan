# 공개 mmol/L 혈당계 화면 데이터셋 조사 — 2026-09-11

- 브랜치: `glm/synth-vs-real-atlas`
- 커밋: 이 보고서 커밋 시점의 HEAD
- 상태: 완료 (조사 카드. 반입 여부 판정은 사람 몫)

## 무엇을 했나

mmol/L 소수점 표시 혈당계 사진을 공개 데이터셋에서 확보할 수 있는지 조사했다.
데이터셋·논문 아무것도 저장소에 들이지 않았다(논문 PDF 만 저장소 밖 임시 폴더에
받아 본문을 읽었다). 후보 4건 + 즉시 탈락 1건을 표로 정리했다.

## 조사표 (AC #1·#2·#3)

### 후보 1 — Oxford CameraLab / Finnegan et al. 2019 (1순위 후보, 카드 Notes 지정)

| 항목 | 내용 |
|---|---|
| 출처 | 리소스 페이지 https://eng.ox.ac.uk/lcmt/resources/resources-seven-segment (구 `cameralab.eng.ox.ac.uk/seven_segment.html` 은 302 로 이 페이지 계열로 리다이렉트) · zip 공식 링크 `https://cameralab.eng.ox.ac.uk/data/bp_bg_meters.zip` |
| 논문 | Finnegan, Villarroel, Velardo, Tarassenko (2019), J Med Eng Technol 43(6) 341–355, DOI 10.1080/03091902.2019.1673844 — ORA 기록 `ora.ox.ac.uk/objects/uuid:72be1fdf-327d-4d30-ab66-8892e642fc68` |
| **라이선스** | **미확인.** 리소스 페이지에는 라이선스 문구가 없고 인용 요청만 있다(원문: "When using the code or data set, please cite the following manuscript:"). 논문 PDF 는 CC BY 4.0 이지만(ORA 라이선스 필드 "CC Attribution (CC BY)") **논문의 라이선스가 데이터셋의 라이선스가 아니다.** 데이터 별도 조건: 확인 안 됨 |
| **링크 상태 (2026-09-11 실측)** | **죽음.** zip URL → 302 → `https://eng.ox.ac.uk/lcmt`(랩 홈 200 HTML). 신규 호스트 `eng.ox.ac.uk/lcmt/data/bp_bg_meters.zip` → 404. Internet Archive CDX 조회 캡처 2건(2025-06-20) 모두 302 리다이렉트 캡처 — **zip 실체의 아카이브 백업 없음.** 리소스 페이지는 죽은 링크를 그대로 게시 중 |
| 총 장수 | 논문 본문 기준 실사진 300장 = 혈당계 **132장**(One Touch Ultra Mini 1기기) + 혈압계 168장(Microlife WatchBP Home). 카메라 5종(iPhone 6S·iPhone 5·Samsung S5·HTC Desire·Galaxy Tab E), "The camera phone was planar to the device" — 평면 정면·반사 통제된 촬영. 수동 추출 숫자 1,377개(혈당계 434). 합성 세트는 13,824장/자리×10자리(52×52 grayscale) |
| **mmol/L 소수점 장수 추정** | Figure 1 캡션 원문: "Blood Glucose metre, One Touch Ultra Mini, showing blood glucose value of 12.8 mmol/L". 기기가 mmol/L 1자리 소수 표시 기기이므로 혈당계 132장 전부 소수점 표시로 **추정** — 원본 미확인(zip 을 못 받아 확인 불가). 값 범위 가정 2.8–21.1 mmol/L 로 한 자리 정수(5.6)와 두 자리 정수(12.3) 형태가 모두 존재할 수 있으나 실제 분포는 미확인 |
| 소수점 라벨 | 그들의 분류기는 10 digit 클래스뿐("The output was a vector of length 10 indicating the 10 digit classes") — **소수점 클래스 없음.** GT 는 digit bbox 만 있으므로 소수점 GT 는 우리가 새로 붙여야 한다 |
| 파생 기록 | 후속 2Ai 그룹이 zip 을 다르게 기록: Moreira 2022 "487 images of four different medical devices" / Lobo 2023 공개 데이터셋 부분 "3 devices, 254 images". 487=233(카탈로그)+254(공개) 로 정합 — **zip 이 논문 본문(혈당계 132장·1기기)보다 클 가능성**, 기기 구성 명세는 없음(원본 미확인) |
| **우리 파이프라인 반입 시 추가 작업 (AC #3)** | ① 저자 연락으로 zip 확보(링크 사망 — eoin.finnegan@eng.ox.ac.uk, 논문 서신저자) ② 라이선스 문구 확인(지금은 미확인) ③ 밴드 쿼드 라벨링: 혈당계 132~254장 (우리 306장 밴드 라벨링 세션과 비슷한 1세션) ④ 값+소수점 GT 전량 신규 라벨링 ⑤ 기기 식별(zip 구성 기기 명세 없음 — 사진 보고 brand+model+variant 확정 필요, 기기 단절 분할의 축) ⑥ EXIF·디코드 좌표계 점검. 촬영이 평면 정면 통제형이라 각도·원근 다양성은 우리 Datumo 코퍼스보다 낮을 것 — 검출 각도 강건성에는 기여 못 함, 소수점 판독 표본에만 기여 |

### 후보 2 — 2Ai 그룹 1,614장 (Lobo 2023 → Moreira 2022 → Ferreira 2025)

| 항목 | 내용 |
|---|---|
| 출처 | Lobo et al., Heliyon 2023;9:e16297 (DOI 10.1016/j.heliyon.2023.e16297, PMC10279773) · Moreira et al., arXiv:2210.01325 (2022) · Ferreira et al., MDPI Appl. Sci. 2025, 15(10):5436 (DOI 10.3390/app15105436) |
| **데이터 가용성** | **공개 아님.** Lobo 2023 원문: "Data will be made available on request." + 결론에서 "is not made completely public given it contains images from company catalogs"(카탈로그 저작권 사유). Ferreira 2025: "The original contributions presented in this study are included in the article. Further inquiries can be directed to the corresponding author." |
| 라이선스 | Lobo 논문: **CC BY-NC-ND 4.0**(PMC 메타데이터 원문 "This is an open access article under the CC BY-NC-ND license"). Ferreira 논문: CC BY. **데이터 자체 조건은 미확인**(요청 시 제공 방식이라 고정 조항 없음). NC-ND 는 반입 검토 시 ND(파생 금지) 조항이 크롭·증강 학습셋에 어떻게 적용되는지부터 봐야 한다 |
| 총 장수 | 1,614장 — 혈당계 487장(**카탈로그 233장/~39기기 + 공개데이터셋 254장/3기기, 로컬 실촬 0장** — Lobo 2023 Table 1, Moreira 2022 "487 images" 와 정합), 산소계 321장, 혈압계 806장(산소·혈압 분해는 Ferreira 2025 본문 기준) |
| mmol/L 소수점 장수 추정 | **미확인.** 기기 모델·단위가 논문에 명시되지 않음("Glycemic" 클래스명만 존재). 카탈로그 사진(233장)은 제품 홍보 사진이라 실촬 맥락이 아니고, 공개데이터셋 부분(254장)은 후보 1과 동일 출처 |
| 소수점 라벨 | 15 클래스 = 10 digits + 5 약어(sys·dia·glycemic "m"·p·spO2) — **소수점 클래스 없음** |
| 추가 작업 (AC #3) | 요청→승인 절차, 승인 후 라이선스 검토(NC-ND), 카탈로그 사진의 현실성 부족(스튜디오 사진). 실촬 혈당계 사진은 결국 후보 1 부분집합 — **실질 가치 낮음, 후보 1 확보가 되면 중복** |

### 후보 3 — DataCluster Labs (Kaggle) Glucometer Reading OCR

| 항목 | 내용 |
|---|---|
| 출처 | https://www.kaggle.com/datasets/dataclusterlabs/glucometer-reading-ocr-medical-device-dataset |
| 라이선스 | Kaggle 페이지 메타데이터: "CC0: Public Domain". **그러나 설명 원문이 소유권을 병기한다**: "The images in this dataset are exclusively owned by Data Cluster Labs and were not downloaded from the internet. To access a larger portion of the training dataset for research and commercial purposes, a license can be purchased." — 표기(CC0)와 주장(배타적 소유·유료 라이선스)이 충돌하므로 **반입 전 사람 판단 필요** |
| 총 장수 | 3,000+장 (크라우드소싱 2,000+ 장소, 2020–2022 폰 촬영, HD 이상, 다양한 조도·거리) |
| mmol/L 소수점 장수 추정 | **미확인.** 인도 촬영 크라우드소싱이라(설명에 Hindi OCR 병기) mg/dL 표시 기기 비중이 높을 것으로 보이나 확인하지 못했다 |
| 추가 작업 (AC #3) | 표본 반입 검토 → 단위·기기 구성 확인(전량 확인 전엔 목적 부합 여부 자체를 모름), 이후 밴드 쿼드+값+소수점 전량 라벨링(3,000+장), 기기 식별. 유료 전체본은 상업 라이선스 검토가 선행 |

### 후보 4 — 일반 7세그 공개 세트 (Roboflow Universe 등)

일반 7세그 세트(Roboflow `seven-segment-digits-uptcy` 4,753장 등 다수)는 전력계량기·산업
디스플레이 중심이고 혈당계 mmol/L 소수점 표본이 목적인 이 카드의 목적에 부합하지
않아 후보에서 제외했다. 개별 세트의 라이선스는 이 카드에서 확인하지 않았다(미확인).

### 즉시 탈락 — GPL/AGPL 계열

SSOCR(GPL-3.0), lcd-digit-recognition(AGPL-3.0) 등은 이미지 데이터셋이 아니라
코드 저장소며, 라이선스 자체가 반입 금지 조건이라 카드 지시대로 조사를 중단했다.

## 결론

mmol/L 소수점 실츬 사진의 **유일한 공개 출처는 Oxford zip 하나뿐**이고, 그 zip 은
(1) 라이선스가 미확인이고 (2) 다운로드 링크가 죽어 있으며 웹아카이브 백업도 없다.
확보 경로는 저자에게 직접 연락하는 것뿐이다. 이 결과는 review 대기 중인
"mmol/L 실츬 데이터 확보" 카드(기기·장수 기준 결정)의 직접 입력이 된다:
Oxford 세트는 기기 1~3종·장수 132~254장으로, 해당 카드가 가정한 "2~3종 × 50~100장"
기준과 맞아떨어지지만 각도 다양성은 없다는 점을 함께 고려해야 한다.

## 왜 그렇게 했나

- 카드 Notes 가 "다운로드하지 말 것"이라 했으므로 링크 생사만 HEAD/CDX 로 확인했다.
  zip 실체를 받아 열어보지 않아 장수·소수점 수는 논문 원문 인용과 후속 논문의
  기록에 한정했다 — 추정은 전부 "추정/미확인"으로 표시했다.
- 2Ai 그룹 3편은 한 데이터셋의 연속 사용이라 한 행으로 묶고, 그들이 Finnegan zip 을
  다르게 기록한 점(487/4기기 vs 132/1기기)은 후보 1의 실제 내용 추정 근거로 썼다.
- Ferreira 2025 본문은 이 환경에서 MDPI 가 모든 경로로 차단(403)해 webReader 로만
  읽었다. 혈당계 487장 분해(233+254)는 Lobo 2023 PMC 전문과 Moreira 2022 arXiv PDF
  라는 독립 경로 두 곳이 일치해 채택했고, 산소·혈압 분해(321/806)는 Ferreira 단일
  출처다.

## 검증

명령과 출력 원문(요약 아님):

```
$ curl -sI https://cameralab.eng.ox.ac.uk/data/bp_bg_meters.zip
HTTP/1.1 302 Redirect
Location: https://eng.ox.ac.uk/lcmt
$ curl -sI https://eng.ox.ac.uk/lcmt/data/bp_bg_meters.zip
HTTP/1.1 404 Not Found

$ curl -s "https://web.archive.org/cdx/search/cdx?url=cameralab.eng.ox.ac.uk/data/bp_bg_meters.zip&limit=5"
uk,ac,ox,eng,cameralab)/data/bp_bg_meters.zip 20250620141927 https://... text/html 302 ... 386
uk,ac,ox,eng,cameralab)/data/bp_bg_meters.zip 20250620142854 http://...  text/html 302 ... 380
(캡처 2건 모두 302 리다이렉트 캡처 — zip 실체 없음)
```

논문 원문 인용(Finnegan 2019, ORA CC-BY PDF 에서 추출):

```
132 images were taken of the One Touch Ultra Mini and 168 images were taken
of the Microlife WatchBP Home.
The output was a vector of length 10 indicating the 10 digit classes.
Blood Glucose content (mmol/L): 2.8–21.1
Figure 1 ... One Touch Ultra Mini, showing blood glucose value of 12.8 mmol/L.
```

Lobo 2023 PMC 전문(PMC10279773) 인용:

```
"Data will be made available on request."
"This is an open access article under the CC BY-NC-ND license."
Table 1 — Commercial catalogs: ~39 devices, 233 images / Public dataset: 3 devices, 254 images
(no photographs were taken of glucometers)
```

Moreira 2022 arXiv PDF 인용:

```
The dataset used in this work were made public by [9](=Finnegan), consisting
in 487 images of four different medical devices
The total number of seven-segment digits present in the dataset is 2,190
```

Kaggle 페이지 JSON-LD 인용:

```
"license":{"@type":"CreativeWork","name":"CC0: Public Domain",...}
"The images in this dataset are exclusively owned by Data Cluster Labs ..."
```

Europe PMC API(Lobo 라이선스 확인): `PMCID: PMC10279773 | license: cc by-nc-nd`

이 카드는 코드를 고치지 않았으므로 flutter analyze/test 는 해당 없다. 저장소에
들어간 변경은 이 보고서 파일뿐이다.

## 건드리지 않고 남긴 것

- 데이터셋·이미지·코드 어떤 것도 저장소/assets_dev 에 들이지 않았다(카드 지시).
- Bitbucket 의 합성 생성기·검출 코드 저장소(eoinf96/…)는 라이선스를 확인하지 않았다
  (미확인). 코드 반입은 계획에 없다 — 자체 구현이 라이선스 방어선이다.
- review 대기 중 "mmol/L 실츬 데이터 확보" 카드의 기준(기기·장수)은 이 조사 결과를
  보고 사람이 다시 정하도록 그대로 뒀다.

## 막힌 것

- MDPI(Ferreira 2025)는 이 환경의 모든 접근 경로를 차단했다(WebFetch 403, 직접
  curl 403/Akamai Access Denied). webReader 로 본문을 읽었고 산소·혈압 분해 장수는
  이 단일 출처에 의존한다.
- Internet Archive availability API 가 IP 단위 429 를 계속 반환해 CDX API 로 대체
  확인했다(결과 동일 — 백업 없음).
