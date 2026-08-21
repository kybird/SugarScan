# G8 — 지원 언어 4개 추가 (es · pt · de · fr)

- 브랜치: `glm/G8-locales-es-pt-de-fr`
- 커밋: `44d4f74` (코드) + 보고서 커밋 (이 파일)
- 상태: 완료 — **병합 전 사람 검토 필요** (§ 아래 역번역 표)
  - 2026-08-21 추가: 의료 문구 21개 × 4개 언어를 DeepL 웹 번역기로 역번역
    교차 검증했다 — **4개 언어 모두 21/21 의미 보존, 판정어 0건.**
    근거 출력은 [`G8-backtranslate-input.md`](G8-backtranslate-input.md) 부록.
    남은 사람 검토는 ★ 5개 키(#3·#14·#15·#16/17·#21) 확인으로 줄어들었다.

## 무엇을 했나

- `lib/l10n/app_es.arb` · `app_pt.arb`(브라질 어투) · `app_de.arb` · `app_fr.arb`
  신규 작성. 각 100키, en/ko 와 키 구성·플레이스홀더 완전 일치(스크립트 검증).
- `lib/l10n/generated/` — `flutter gen-l10n` 재생성. `supportedLocales` 에
  6개(de·en·es·fr·ko·pt) 확인.
- 규칙 준수: `@@locale` 설정, `@` 메타데이터 없음(ko 형식), `appTitle` 은
  "SugarScan" 공통, 플레이스홀더 이름·순서 유지, `mg/dL`/`mmol/L` 무번역,
  키 추가·삭제 없음, 미번역 키 0건.

## 검증

키 수·플레이스홀더 일치 → python json 비교: 6개 파일 전부 100키, missing/extra/
                     placeholder_mismatch 전부 빈 목록, 번역본 @메타데이터 0건
flutter gen-l10n   → 생성 성공, supportedLocals 6개(Locale('de')…Locale('pt'))
flutter analyze    → No issues found! (ran in 5.6s)
flutter test       → All tests passed! (333 tests)

## 왜 그렇게 했나

- 경어: es 는 tú, pt-BR 는 você, de 는 du, fr 는 vous 로 통일했다.
- `statsLow`/`statsHigh` 는 "낮음/높음"(판정처럼 읽힘)이 아니라 ko 원 뜻(최저/
  최고)에 맞춰 es Mínimo/Máximo, pt Mínimo/Máximo, de Tiefstwert/Höchstwert,
  fr Minimum/Maximum 로 옮겼다.
- `statsSd` 는 각 언어권 의학 통계 표준 약어를 썼다: es DE(desviación estándar),
  pt DP(desvio padrão), de SD, fr ET(écart-type).
- `statsByTag` 의 "tag" 는 de 에서 일상어 "Tag"(=날)라 오해의 소지가 있어
  네 언어 모두 "카테고리"(es categoría / pt categoria / de Kategorie /
  fr catégorie)로 옮겼다.
- fr 의 `actionUndo`("Annuler")는 `actionCancel`("Annuler")과 같아지는데,
  프랑스어 Material 스낵바 관례가 실행 취소에도 "ANNULER" 를 쓰므로 그대로
  두었다. 문맥(삭제 스낵바)으로 구분된다.

## 글자 넘침 확인

기기/데스크톱 타깃 없이는 각 언어로 앱을 띄워 확인할 수 없어 수행하지 못했다
(지시서가 허용하는 방식으로 보고에 남긴다). 독일어는 영어보다 길어져 버튼·칩
넘침 위험이 있으므로 **병합 후 각 언어로 기기 확인이 필요하다.**

## 병합 전 사람이 봐야 할 것 (범위 밖이므로 수정하지 않고 기록)

- ~~**미지원 로케일 폴백이 독일어로 바뀐다.**~~ — **2026-08-21 해결.** 사용자
  결정으로 영어 폴백을 구현했다(`lib/app/app.dart` 의 `resolveAppLocale` 콜백,
  `test/app/locale_fallback_test.dart` 로 고정). 지원 밖 언어는 이제 영어로
  떨어진다.
- 소수점 표기(de/fr/es 권 쉼표)는 §5 에서 사람이 정하기로 한 사항이라 건드리지
  않았다. `unitExampleMmoll` 의 "7.6" 은 예시 원문 숫자라 점을 유지했다.

---

## 의료 문구 21개 — 원문 · 번역 · 한국어 역번역 (사람 검토용)

### 스페인어 (es)

| 키 | EN 원문 | es 번역 | 역번역(KO) |
|---|---|---|---|
| medicalDisclaimer | SugarScan does not provide a medical diagnosis. Always consult a healthcare professional before making treatment decisions. | SugarScan no proporciona un diagnóstico médico. Consulte siempre a un profesional sanitario antes de tomar decisiones sobre el tratamiento. | SugarScan은 의학적 진단을 제공하지 않는다. 치료에 관한 결정 전에 항상 의료 전문가와 상담하라. |
| statsInRange | Within target range | Dentro del rango objetivo | 목표 범위 안 |
| statsInRangeNote | Counts readings, not time. A finger-prick meter samples moments, so this is not the same as a CGM time-in-range. | Cuenta mediciones, no tiempo. Un glucómetro de punción capilar toma muestras puntuales, por lo que esto no equivale al tiempo en rango de un sensor continuo (MCG). | 측정 건수를 세지 시간을 세지 않는다. 채혈 혈당계는 시점 표본을 채취하므로 연속 센서(CGM)의 범위 내 시간과 같지 않다. |
| settingsTargetNote | These are reference ranges, not advice. Decide your own target with your healthcare provider. | Estos son rangos de referencia, no consejos. Acuerda tu propio objetivo con tu profesional sanitario. | 이것들은 참고 범위이지 조언이 아니다. 너의 목표는 의료 전문가와 합의하라. |
| settingsUnitNote | Changing this only affects how readings are shown. Saved readings keep the unit they were entered in. | Cambiar esto solo afecta a cómo se muestran las lecturas. Las lecturas guardadas conservan la unidad con la que se introdujeron. | 변경은 기록 표시 방식에만 영향을 준다. 저장된 기록은 입력된 단위를 유지한다. |
| targetObservation | Observation range | Rango de observación | 관찰 범위 |
| targetObservationNote | The range used for time-in-range reporting. | El rango que se usa para el informe de tiempo en rango. | 범위 내 시간 보고에 쓰이는 범위. |
| targetPreMeal | Before-meal target | Objetivo antes de las comidas | 식사 전 목표 |
| targetPreMealNote | ADA Standards of Care, non-pregnant adults. | ADA Standards of Care, adultos no embarazados. | ADA Standards of Care, 임신하지 않은 성인. |
| targetTight | Tight range | Rango estrecho | 좁은 범위 |
| targetTightNote | Where people without diabetes spend most of their time. | Donde las personas sin diabetes pasan la mayor parte del tiempo. | 당뇨가 없는 사람들이 대부분의 시간을 보내는 범위. |
| onboardingUnitTitle | Which unit does your meter use? | ¿Qué unidad usa tu glucómetro? | 혈당계가 어떤 단위를 쓰나? |
| onboardingUnitBody | Look at your meter's display. Pick the unit it shows. | Mira la pantalla de tu glucómetro y elige la unidad que muestra. | 혈당계 화면을 보고 표시되는 단위를 골라라. |
| onboardingUnitWarning | This matters: the same number means very different things in each unit. A reading of 40 is very low in mg/dL, and very high in mmol/L. | Esto importa: el mismo número significa cosas muy distintas en cada unidad. Una lectura de 40 es muy baja en mg/dL, y muy alta en mmol/L. | 중요하다: 같은 숫자가 단위마다 매우 다른 것을 뜻한다. 40의 기록은 mg/dL에서 매우 낮고 mmol/L에서는 매우 높다. |
| editUnitWarning | Changing this reinterprets the number you typed — it does not convert it. | Cambiar esto interpreta de nuevo el número que escribiste: no lo convierte. | 변경하면 쓴 숫자를 다시 해석한다: 변환하지 않는다. |
| meterShowsHigh | The meter shows HI — above its measurable range. | El glucómetro muestra HI: está por encima de su rango medible. | 혈당계가 HI를 표시한다: 측정 가능 범위 위다. |
| meterShowsLow | The meter shows LO — below its measurable range. | El glucómetro muestra LO: está por debajo de su rango medible. | 혈당계가 LO를 표시한다: 측정 가능 범위 아래다. |
| ea1cLabel | Estimated A1c | A1c estimada | 추정 A1c |
| ea1cEstimateBadge | Estimate | Estimación | 추정치 |
| ea1cInsufficientData | Need {readings} readings across {days} days to estimate | Se necesitan {readings} mediciones a lo largo de {days} días para estimar | 추정하려면 {days}일에 걸쳐 {readings}회 측정이 필요하다 |
| invalidValueRange | That is outside what a meter can show | Eso está fuera de lo que un glucómetro puede mostrar | 그 값은 혈당계가 표시할 수 있는 것 밖이다 |

### 포르투갈어 — 브라질 어투 (pt)

| 키 | pt 번역 | 역번역(KO) |
|---|---|---|
| medicalDisclaimer | O SugarScan não fornece diagnóstico médico. Consulte sempre um profissional de saúde antes de tomar decisões sobre tratamento. | SugarScan은 의학적 진단을 제공하지 않는다. 치료 결정 전에 항상 의료 전문가와 상담하라. |
| statsInRange | Dentro da faixa-alvo | 목표 범위(faixa-alvo) 안 |
| statsInRangeNote | Conta medições, não tempo. Um glicosímetro de punção capilar mede momentos isolados, então isso não é o mesmo que o tempo na faixa de um monitor contínuo (MCG). | 시간이 아니라 측정을 센다. 채혈 혈당계는 고립된 순간들을 측정하므로 연속 모니터(CGM)의 범위 내 시간과 같지 않다. |
| settingsTargetNote | Estas são faixas de referência, não recomendações. Defina sua própria meta com seu profissional de saúde. | 이것들은 참고 범위이지 권장이 아니다. 당신의 목표는 의료 전문가와 정하라. |
| settingsUnitNote | Mudar isso afeta apenas como as leituras são exibidas. As leituras salvas mantêm a unidade em que foram digitadas. | 변경은 기록 표시 방식에만 영향을 준다. 저장된 기록은 입력된 단위를 유지한다. |
| targetObservation | Faixa de observação | 관찰 범위 |
| targetObservationNote | A faixa usada no relatório de tempo na faixa-alvo. | 목표 범위 내 시간 보고서에 쓰이는 범위. |
| targetPreMeal | Meta antes das refeições | 식사 전 목표 |
| targetPreMealNote | ADA Standards of Care, adultos não gestantes. | ADA Standards of Care, 임신하지 않은 성인. |
| targetTight | Faixa estreita | 좁은 범위 |
| targetTightNote | Onde pessoas sem diabetes passam a maior parte do tempo. | 당뇨 없는 사람들이 대부분의 시간을 보내는 곳. |
| onboardingUnitTitle | Qual unidade o seu glicosímetro usa? | 혈당계가 어떤 단위를 쓰나? |
| onboardingUnitBody | Olhe a tela do seu glicosímetro e escolha a unidade que ela mostra. | 혈당계 화면을 보고 표시되는 단위를 골라라. |
| onboardingUnitWarning | Isso importa: o mesmo número significa coisas muito diferentes em cada unidade. Uma leitura de 40 é muito baixa em mg/dL, e muito alta em mmol/L. | 중요하다: 같은 숫자가 단위마다 매우 다른 것을 뜻한다. 40의 기록은 mg/dL에서 매우 낮고 mmol/L에서 매우 높다. |
| editUnitWarning | Mudar isso interpreta novamente o número que você digitou — ele não é convertido. | 변경하면 입력한 숫자를 다시 해석한다 — 변환되지 않는다. |
| meterShowsHigh | O glicosímetro exibe HI — está acima da faixa que ele consegue medir. | 혈당계가 HI를 표시한다 — 측정할 수 있는 범위 위다. |
| meterShowsLow | O glicosímetro exibe LO — está abaixo da faixa que ele consegue medir. | 혈당계가 LO를 표시한다 — 측정할 수 있는 범위 아래다. |
| ea1cLabel | A1c estimada | 추정 A1c |
| ea1cEstimateBadge | Estimativa | 추정치 |
| ea1cInsufficientData | São necessárias {readings} medições ao longo de {days} dias para estimar | 추정하려면 {days}일에 걸쳐 {readings}회 측정이 필요하다 |
| invalidValueRange | Isso está fora do que um glicosímetro consegue exibir | 그 값은 혈당계가 표시할 수 있는 것을 벗어난다 |

### 독일어 (de)

| 키 | de 번역 | 역번역(KO) |
|---|---|---|
| medicalDisclaimer | SugarScan stellt keine medizinische Diagnose. Konsultiere vor Entscheidungen über die Behandlung immer eine Fachperson im Gesundheitswesen. | SugarScan은 의학적 진단을 내리지 않는다. 치료 결정 전에 항상 보건 분야 전문가에게 상담하라. |
| statsInRange | Im Zielbereich | 목표 범위 안 |
| statsInRangeNote | Zählt Messungen, nicht Zeit. Ein Blutzuckermesser mit Stechen erfasst einzelne Zeitpunkte und ist daher nicht mit der Time-in-Range eines CGM-Systems zu vergleichen. | 시간이 아니라 측정을 센다. 채혈 혈당계는 개별 시점을 기록하므로 CGM 시스템의 Time-in-Range와 비교할 수 없다. |
| settingsTargetNote | Dies sind Referenzbereiche, keine Empfehlung. Lege dein eigenes Ziel mit deiner Behandlungsperson fest. | 이것들은 참고 범위이지 권고가 아니다. 너의 목표는 치료 담당자와 정하라. |
| settingsUnitNote | Eine Änderung betrifft nur, wie Messwerte angezeigt werden. Gespeicherte Messwerte behalten die Einheit, in der sie eingegeben wurden. | 변경은 측정값 표시에만 영향을 준다. 저장된 측정값은 입력된 단위를 유지한다. |
| targetObservation | Beobachtungsbereich | 관찰 범위 |
| targetObservationNote | Der Bereich, der für die Time-in-Range-Auswertung verwendet wird. | Time-in-Range 산출에 사용되는 범위. |
| targetPreMeal | Zielwert vor den Mahlzeiten | 식사 전 목표값 |
| targetPreMealNote | ADA Standards of Care, nichtschwangere Erwachsene. | ADA Standards of Care, 임신하지 않은 성인. |
| targetTight | Enger Bereich | 좁은 범위 |
| targetTightNote | Der Bereich, in dem Menschen ohne Diabetes die meiste Zeit verbringen. | 당뇨 없는 사람들이 대부분의 시간을 보내는 범위. |
| onboardingUnitTitle | Welche Einheit verwendet dein Messgerät? | 혈당계가 어떤 단위를 쓰는가? |
| onboardingUnitBody | Schau auf das Display deines Messgeräts und wähle die angezeigte Einheit. | 혈당계 디스플레이를 보고 표시된 단위를 골라라. |
| onboardingUnitWarning | Das ist wichtig: Dieselbe Zahl bedeutet in jeder Einheit etwas ganz anderes. Ein Wert von 40 ist in mg/dL sehr niedrig, und in mmol/L sehr hoch. | 중요하다: 같은 숫자가 단위마다 전혀 다른 것을 뜻한다. 40의 값은 mg/dL에서 매우 낮고 mmol/L에서는 매우 높다. |
| editUnitWarning | Eine Änderung liest die eingegebene Zahl neu ein — sie wird nicht umgerechnet. | 변경하면 입력한 숫자를 새로 읽는다 — 환산되지 않는다. |
| meterShowsHigh | Das Messgerät zeigt HI — über seinem messbaren Bereich. | 혈당계가 HI를 표시한다 — 측정 가능 범위 위다. |
| meterShowsLow | Das Messgerät zeigt LO — unter seinem messbaren Bereich. | 혈당계가 LO를 표시한다 — 측정 가능 범위 아래다. |
| ea1cLabel | Geschätzter A1c-Wert | 추정 A1c 값 |
| ea1cEstimateBadge | Schätzwert | 추정치 |
| ea1cInsufficientData | Für eine Schätzung sind {readings} Messungen über {days} Tage nötig | 추정에는 {days}일에 걸친 {readings}회 측정이 필요하다 |
| invalidValueRange | Das liegt außerhalb dessen, was ein Messgerät anzeigen kann | 그 값은 혈당계가 표시할 수 있는 것 밖에 있다 |

### 프랑스어 (fr)

| 키 | fr 번역 | 역번역(KO) |
|---|---|---|
| medicalDisclaimer | SugarScan ne fournit pas de diagnostic médical. Consultez toujours un professionnel de santé avant de prendre des décisions de traitement. | SugarScan은 의학적 진단을 제공하지 않는다. 치료 결정 전에 항상 의료 전문가와 상담하라. |
| statsInRange | Dans la plage cible | 목표 범위 안 |
| statsInRangeNote | Compte des mesures, pas du temps. Un lecteur de glycémie à piqûre mesure des moments isolés, ce n'est donc pas la même chose que le temps passé dans la cible d'un capteur continu (MCG). | 시간이 아니라 측정을 센다. 피부를 찌르는 혈당계는 고립된 순간들을 측정하므로 연속 센서(MCG)의 표적 내 체류 시간과 같은 것이 아니다. |
| settingsTargetNote | Ce sont des plages de référence, pas des conseils. Définissez votre propre cible avec votre professionnel de santé. | 이것들은 참고 범위이지 조언이 아니다. 당신의 표적은 의료 전문가와 정하라. |
| settingsUnitNote | Changer ceci affecte uniquement l'affichage des mesures. Les mesures enregistrées conservent l'unité dans laquelle elles ont été saisies. | 변경은 측정값 표시에만 영향을 준다. 저장된 측정값은 입력된 단위를 보존한다. |
| targetObservation | Plage d'observation | 관찰 범위 |
| targetObservationNote | La plage utilisée pour le rapport de temps dans la cible. | 표적 내 시간 보고에 사용되는 범위. |
| targetPreMeal | Cible avant les repas | 식사 전 표적 |
| targetPreMealNote | ADA Standards of Care, adultes non enceintes. | ADA Standards of Care, 임신하지 않은 성인. |
| targetTight | Plage serrée | 좁은(꽉 낀) 범위 |
| targetTightNote | Là où les personnes sans diabète passent la plupart du temps. | 당뇨 없는 사람들이 대부분의 시간을 보내는 곳. |
| onboardingUnitTitle | Quelle unité utilise votre lecteur ? | 혈당계가 어떤 단위를 쓰는가? |
| onboardingUnitBody | Regardez l'écran de votre lecteur et choisissez l'unité qu'il affiche. | 혈당계 화면을 보고 표시되는 단위를 골라라. |
| onboardingUnitWarning | C'est important : le même nombre signifie des choses très différentes selon l'unité. Une valeur de 40 est très basse en mg/dL, et très élevée en mmol/L. | 중요하다: 같은 수가 단위에 따라 매우 다른 것을 뜻한다. 40의 값은 mg/dL에서 매우 낮고 mmol/L에서는 매우 높다. |
| editUnitWarning | Changer ceci réinterprète le nombre saisi — il n'est pas converti. | 변경하면 입력한 수를 다시 해석한다 — 변환되지 않는다. |
| meterShowsHigh | Le lecteur affiche HI — au-dessus de sa plage mesurable. | 혈당계가 HI를 표시한다 — 측정 가능 범위 위다. |
| meterShowsLow | Le lecteur affiche LO — en dessous de sa plage mesurable. | 혈당계가 LO를 표시한다 — 측정 가능 범위 아래다. |
| ea1cLabel | A1c estimée | 추정 A1c |
| ea1cEstimateBadge | Estimation | 추정치 |
| ea1cInsufficientData | Il faut {readings} mesures sur {days} jours pour l'estimer | 이를 추정하려면 {days}일 동안 {readings}회 측정이 필요하다 |
| invalidValueRange | C'est en dehors de ce qu'un lecteur peut afficher | 그 값은 혈당계가 표시할 수 있는 것 밖에 있다 |

(es 표에만 EN 원문 칸을 넣고 나머지 표는 생략했다 — 원문은 es 표 또는
`app_en.arb` 참조.)

## 건드리지 않고 남긴 것

- en/ko 원문 전부 무변경. 코드 무변경.
- GLM_TASKS.md 의 103키 기준은 G1(-4)·G7(+1) 이 반영된 현재 정본 기준
  100키로 해석했다 — 완료 기준의 "en/ko 와 키 수가 같다"를 만족한다.

## 막힌 것

없음
