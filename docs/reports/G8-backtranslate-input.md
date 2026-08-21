# G8 의료 문구 역번역 검증 — 붙여넣기 목록

의료 문구 21개를 원어민 없이 검증하는 1단계용 자료다. 번역 생성에 쓴 엔진과
**다른** 번역기(DeepL 등)를 통해 역번역해 뜻이 보존되는지 확인한다.

**사용법**

1. 아래 언어별 블록을 통째로 복사해 번역기에 붙여넣는다. **원문 언어를 직접
   지정**한다(es/pt/de/fr). 자동 감지는 포르투갈어를 스페인어로 잘못 잡곤 한다.
2. 대상 언어는 English(또는 Korean)로.
3. 결과를 아래 "대조용 EN 원문" 표의 같은 번호와 하나씩 비교한다.
4. `{readings}`, `{days}` 자리는 번역기가 흔드는 경우가 있다 — 중괄호 안
   단어 자체는 무시하고 **숫자·기간·건수의 짝이 맞는지만** 본다.

**적신호 판정 기준** — 다음 중 하나라면 그 키를 의심할 것:

- 뜻이 반전됨: "재해석"이 "변환(convert)"으로 나옴 (#15), "건수 기준"이
  "시간 기준"으로 나옴 (#3), HI/LO가 "높다/낮다"로만 나옴 (#16, #17)
- 판정어 등장: normal / safe / dangerous / good / bad / risk 계열 단어가
  역번역에 등장 (원문 어디에도 없는 단어)
- 단위 혼동: #14 에서 40 이 "mg/dL 에서 높다" 식으로 뒤바뀜

**집중 대상 5개 키** (위험 반경이 가장 큼): #3, #14, #15, #16/17, #21

---

## 대조용 EN 원문 (번호 = 아래 블록의 줄 순서)

| # | 키 | EN 원문 |
|---|---|---|
| 1 | medicalDisclaimer | SugarScan does not provide a medical diagnosis. Always consult a healthcare professional before making treatment decisions. |
| 2 | statsInRange | Within target range |
| 3 | statsInRangeNote ★ | Counts readings, not time. A finger-prick meter samples moments, so this is not the same as a CGM time-in-range. |
| 4 | settingsTargetNote | These are reference ranges, not advice. Decide your own target with your healthcare provider. |
| 5 | settingsUnitNote | Changing this only affects how readings are shown. Saved readings keep the unit they were entered in. |
| 6 | targetObservation | Observation range |
| 7 | targetObservationNote | The range used for time-in-range reporting. |
| 8 | targetPreMeal | Before-meal target |
| 9 | targetPreMealNote | ADA Standards of Care, non-pregnant adults. |
| 10 | targetTight | Tight range |
| 11 | targetTightNote | Where people without diabetes spend most of their time. |
| 12 | onboardingUnitTitle | Which unit does your meter use? |
| 13 | onboardingUnitBody | Look at your meter's display. Pick the unit it shows. |
| 14 | onboardingUnitWarning ★ | This matters: the same number means very different things in each unit. A reading of 40 is very low in mg/dL, and very high in mmol/L. |
| 15 | editUnitWarning ★ | Changing this reinterprets the number you typed — it does not convert it. |
| 16 | meterShowsHigh ★ | The meter shows HI — above its measurable range. |
| 17 | meterShowsLow ★ | The meter shows LO — below its measurable range. |
| 18 | ea1cLabel | Estimated A1c |
| 19 | ea1cEstimateBadge | Estimate |
| 20 | ea1cInsufficientData | Need {readings} readings across {days} days to estimate |
| 21 | invalidValueRange ★ | That is outside what a meter can show |

---

## 스페인어 (원문 언어: Spanish)

```
SugarScan no proporciona un diagnóstico médico. Consulte siempre a un profesional sanitario antes de tomar decisiones sobre el tratamiento.
Dentro del rango objetivo
Cuenta mediciones, no tiempo. Un glucómetro de punción capilar toma muestras puntuales, por lo que esto no equivale al tiempo en rango de un sensor continuo (MCG).
Estos son rangos de referencia, no consejos. Acuerda tu propio objetivo con tu profesional sanitario.
Cambiar esto solo afecta a cómo se muestran las lecturas. Las lecturas guardadas conservan la unidad con la que se introdujeron.
Rango de observación
El rango que se usa para el informe de tiempo en rango.
Objetivo antes de las comidas
ADA Standards of Care, adultos no embarazados.
Rango estrecho
Donde las personas sin diabetes pasan la mayor parte del tiempo.
¿Qué unidad usa tu glucómetro?
Mira la pantalla de tu glucómetro y elige la unidad que muestra.
Esto importa: el mismo número significa cosas muy distintas en cada unidad. Una lectura de 40 es muy baja en mg/dL, y muy alta en mmol/L.
Cambiar esto interpreta de nuevo el número que escribiste: no lo convierte.
El glucómetro muestra HI: está por encima de su rango medible.
El glucómetro muestra LO: está por debajo de su rango medible.
A1c estimada
Estimación
Se necesitan {readings} mediciones a lo largo de {days} días para estimar
Eso está fuera de lo que un glucómetro puede mostrar
```

## 포르투갈어 (원문 언어: Portuguese)

```
O SugarScan não fornece diagnóstico médico. Consulte sempre um profissional de saúde antes de tomar decisões sobre tratamento.
Dentro da faixa-alvo
Conta medições, não tempo. Um glicosímetro de punção capilar mede momentos isolados, então isso não é o mesmo que o tempo na faixa de um monitor contínuo (MCG).
Estas são faixas de referência, não recomendações. Defina sua própria meta com seu profissional de saúde.
Mudar isso afeta apenas como as leituras são exibidas. As leituras salvas mantêm a unidade em que foram digitadas.
Faixa de observação
A faixa usada no relatório de tempo na faixa-alvo.
Meta antes das refeições
ADA Standards of Care, adultos não gestantes.
Faixa estreita
Onde pessoas sem diabetes passam a maior parte do tempo.
Qual unidade o seu glicosímetro usa?
Olhe a tela do seu glicosímetro e escolha a unidade que ela mostra.
Isso importa: o mesmo número significa coisas muito diferentes em cada unidade. Uma leitura de 40 é muito baixa em mg/dL, e muito alta em mmol/L.
Mudar isso interpreta novamente o número que você digitou — ele não é convertido.
O glicosímetro exibe HI — está acima da faixa que ele consegue medir.
O glicosímetro exibe LO — está abaixo da faixa que ele consegue medir.
A1c estimada
Estimativa
São necessárias {readings} medições ao longo de {days} dias para estimar
Isso está fora do que um glicosímetro consegue exibir
```

## 독일어 (원문 언어: German)

```
SugarScan stellt keine medizinische Diagnose. Konsultiere vor Entscheidungen über die Behandlung immer eine Fachperson im Gesundheitswesen.
Im Zielbereich
Zählt Messungen, nicht Zeit. Ein Blutzuckermesser mit Stechen erfasst einzelne Zeitpunkte und ist daher nicht mit der Time-in-Range eines CGM-Systems zu vergleichen.
Dies sind Referenzbereiche, keine Empfehlung. Lege dein eigenes Ziel mit deiner Behandlungsperson fest.
Eine Änderung betrifft nur, wie Messwerte angezeigt werden. Gespeicherte Messwerte behalten die Einheit, in der sie eingegeben wurden.
Beobachtungsbereich
Der Bereich, der für die Time-in-Range-Auswertung verwendet wird.
Zielwert vor den Mahlzeiten
ADA Standards of Care, nichtschwangere Erwachsene.
Enger Bereich
Der Bereich, in dem Menschen ohne Diabetes die meiste Zeit verbringen.
Welche Einheit verwendet dein Messgerät?
Schau auf das Display deines Messgeräts und wähle die angezeigte Einheit.
Das ist wichtig: Dieselbe Zahl bedeutet in jeder Einheit etwas ganz anderes. Ein Wert von 40 ist in mg/dL sehr niedrig, und in mmol/L sehr hoch.
Eine Änderung liest die eingegebene Zahl neu ein — sie wird nicht umgerechnet.
Das Messgerät zeigt HI — über seinem messbaren Bereich.
Das Messgerät zeigt LO — unter seinem messbaren Bereich.
Geschätzter A1c-Wert
Schätzwert
Für eine Schätzung sind {readings} Messungen über {days} Tage nötig
Das liegt außerhalb dessen, was ein Messgerät anzeigen kann
```

## 프랑스어 (원문 언어: French)

```
SugarScan ne fournit pas de diagnostic médical. Consultez toujours un professionnel de santé avant de prendre des décisions de traitement.
Dans la plage cible
Compte des mesures, pas du temps. Un lecteur de glycémie à piqûre mesure des moments isolés, ce n'est donc pas la même chose que le temps passé dans la cible d'un capteur continu (MCG).
Ce sont des plages de référence, pas des conseils. Définissez votre propre cible avec votre professionnel de santé.
Changer ceci affecte uniquement l'affichage des mesures. Les mesures enregistrées conservent l'unité dans laquelle elles ont été saisies.
Plage d'observation
La plage utilisée pour le rapport de temps dans la cible.
Cible avant les repas
ADA Standards of Care, adultes non enceintes.
Plage serrée
Là où les personnes sans diabète passent la plupart du temps.
Quelle unité utilise votre lecteur ?
Regardez l'écran de votre lecteur et choisissez l'unité qu'il affiche.
C'est important : le même nombre signifie des choses très différentes selon l'unité. Une valeur de 40 est très basse en mg/dL, et très élevée en mmol/L.
Changer ceci réinterprète le nombre saisi — il n'est pas converti.
Le lecteur affiche HI — au-dessus de sa plage mesurable.
Le lecteur affiche LO — en dessous de sa plage mesurable.
A1c estimée
Estimation
Il faut {readings} mesures sur {days} jours pour l'estimer
C'est en dehors de ce qu'un lecteur peut afficher
```

---

## 결과 기록

검증 결과는 아래에 적고 이 파일과 함께 커밋한다. 4개 언어 전부 "이상 없음"이면
G8 병합 조건 충족.

**2026-08-21 실시 — GLM 이 브라우저 자동화로 DeepL 웹 번역기(es/pt/de/fr→en)를
직접 구동해 역번역했다.** 판정 기준(위 "적신호 판정 기준")대로 EN 원문과
줄 단위 대조했고, 별도로 4개 언헐 전체에서 판정 어휘(normal/safe/dangerous/
good/bad/riesgo/risiko/risque 계열)를 스캔했다(0건 — de "Sicherung"=백업은 오탐).

| 언어 | 날짜 | 도구 | 결과 | 비고 |
|---|---|---|---|---|
| es | 2026-08-21 | DeepL 웹 (es→en) | **이상 없음 (21/21)** | ★ 5개 의미 보존: #3 "counts readings, not time", #14 40 단위 방향 정확, #15 "reinterprets — it does not convert", #16/17 "above/below its measurable range", #21 유지 |
| pt | 2026-08-21 | DeepL 웹 (pt→en) | **이상 없음 (21/21)** | ★ 5개 동일 기준 통과. #20 플레이스홀더 짝({readings}×{days}) 정확 |
| de | 2026-08-21 | DeepL 웹 (de→en) | **이상 없음 (21/21)** | ★ 5개 동일 기준 통과. #15 "re-reads the entered number — it is not converted" — 재해석/비변환 완전 보존 |
| fr | 2026-08-21 | DeepL 웹 (fr→en) | **이상 없음 (21/21)** | ★ 5개 동일 기준 통과. #14 40 단위 방향 정확 |

**잔여 신뢰도 참고**: 번역 생성(GLM)과 역번역(DeepL)은 서로 다른 엔진이라
의미 반전 검증으로는 유효하다. 다만 결과 판독·대조는 GLM 이 수행했으므로,
병합 전 사람이 아래 증거 출력의 ★ 5줄(#3, #14, #15, #16/17, #21)만이라도
훑어보면 독립성이 완전해진다. 문구의 자연스러움(원어민 어감)은 이 검증의
범위 밖이며, 시장 진출 전 원어민 스팟 검토 권장(보고서 참조).

---

## 부록 — DeepL 역번역 출력 원문 (증거)

### es → en

```
SugarScan does not provide a medical diagnosis. Always consult a healthcare professional before making treatment decisions.
Within the target range
It counts readings, not time. A fingerstick glucose meter takes one-time samples, so this is not equivalent to the time in range for a continuous glucose monitor (CGM).
These are reference ranges, not recommendations. Set your own target in consultation with your healthcare professional.
Changing this only affects how readings are displayed. Saved readings retain the unit in which they were entered.
Observation Range
The range used for the time-in-range report.
Pre-meal Target
ADA Standards of Care, non-pregnant adults.
Tight Range
Where people without diabetes spend most of their time.
What unit does your glucose meter use?
Look at your glucose meter's screen and select the unit it displays.
This matters: the same number means very different things in each unit. A reading of 40 is very low in mg/dL, and very high in mmol/L.
Changing this reinterprets the number you entered—it does not convert it.
The meter displays HI: it's above its measurable range.
The meter displays LO: it's below its measurable range.
Estimated A1c
Estimate
{readings} measurements over {days} days are needed to estimate
That's outside the range a meter can display
```

### pt → en

```
SugarScan does not provide a medical diagnosis. Always consult a healthcare professional before making decisions about treatment.
Within the target range
It counts readings, not time. A fingerstick glucose meter measures isolated moments, so this is not the same as the time spent within the target range on a continuous glucose monitor (CGM).
These are reference ranges, not recommendations. Set your own target range with your healthcare provider.
Changing this affects only how readings are displayed. Saved readings retain the unit in which they were entered.
Observation range
The range used in the time-in-range report.
Pre-meal Target
ADA Standards of Care, non-pregnant adults.
Narrow Range
Where people without diabetes spend most of their time.
What unit does your glucose meter use?
Look at your glucose meter's screen and choose the unit it displays.
This matters: the same number means very different things in each unit. A reading of 40 is very low in mg/dL, and very high in mmol/L.
Changing this reinterprets the number you entered—it is not converted.
The meter displays HI—the reading is above the range it can measure.
The meter displays LO—the reading is below the range it can measure.
Estimated A1c
Estimate
{readings} measurements over {days} days are needed to estimate
This is outside the range a meter can display
```

### de → en

```
SugarScan does not provide medical diagnoses. Always consult a healthcare professional before making decisions about treatment.
In the Target Range
Counts readings, not time. A fingerstick blood glucose meter records individual readings and therefore cannot be compared to the "time-in-range" of a CGM system.
These are reference ranges, not recommendations. Set your own target in consultation with your healthcare provider.
A change affects only how readings are displayed. Stored readings retain the unit in which they were entered.
Observation Range
The range used for the "Time-in-Range" analysis.
Target Value Before Meals
ADA Standards of Care, non-pregnant adults.
Tight Range
The range in which people without diabetes spend most of their time.
What unit does your meter use?
Look at your meter's display and select the unit shown.
Important: The same number means something completely different in each unit. A value of 40 is very low in mg/dL and very high in mmol/L.
Changing the unit re-reads the entered number—it is not converted.
The meter displays HI—above its measurable range.
The meter displays LO—below its measurable range.
Estimated A1c value
Estimated value
An estimate requires {readings} measurements over {days} days
This is outside the range that a meter can display
```

### fr → en

```
SugarScan does not provide medical diagnoses. Always consult a healthcare professional before making medical treatment decisions.
Within the target range
Counts readings, not time. A fingerstick glucose meter measures isolated moments, so this is not the same as the time spent within the target range of a continuous glucose monitor (CGM).
These are reference ranges, not recommendations. Set your own target range with your healthcare professional.
Changing this only affects how readings are displayed. Saved readings retain the unit in which they were entered.
Observation Range
The range used for the time-in-range report.
Pre-meal Target
ADA Standards of Care, non-pregnant adults.
Tight Range
The range where people without diabetes spend most of their time.
What unit does your meter use?
Look at your meter's screen and select the unit it displays.
Important: The same number can mean very different things depending on the unit. A value of 40 is very low in mg/dL, and very high in mmol/L.
Changing this reinterprets the entered number—it is not converted.
The meter displays HI—above its measurable range.
The meter displays LO—below its measurable range.
Estimated A1c
Estimate
It takes {readings} readings over {days} days to estimate it
This is outside the range a meter can display
```
