# 트렌드 키워드 매칭 — LLM 활용

`market_api/services/country_recommender.py` → `calc_trend_score()`

---

## 개요

국가 추천 AI Score(0~100점)를 구성하는 3개 지표 중 하나.
사용자 제품의 성분·효능이 각 국가 시장 트렌드와 얼마나 부합하는지를 GPT-4o로 측정한다.

```
AI Score = 트렌드 적합도 (15%) + 시장 규모 (50%) + 리뷰 유사도 (35%)
```

---

## 기술 플로우

```
사용자 입력 (ingredients, effects)
        ↓
MarketResearch DB 조회
(trends.ingredients[], trends.functions[], trends.details)
        ↓
국가별 반복 (US / JP)
        ↓
System/User 프롬프트 조립
        ↓
GPT-4o 호출 (temperature=0)
        ↓
JSON 응답 파싱
{ matched_keywords: [...], reasoning: "..." }
        ↓
코드 검증 (실제 트렌드 목록 교차 확인)
        ↓
점수 계산: score = √(verified / max_possible)
        ↓
{ score, matched, reasoning } 반환
        ↓
_generate_rationale() 호출
reasoning → context로 재사용 (LLM 체이닝)
        ↓
GPT-4o 호출 (temperature=0.3)
        ↓
추천 근거 3~4문장 반환
```

---

## 프롬프트 원문

시스템 프롬프트 없이 **user 메시지 단일 구성**. 페르소나를 첫 줄에 포함한다.

```
당신은 K-Beauty 시장 분석 전문가입니다.

[사용자 제품 정보]
- 주요 성분: {ingredients}
- 핵심 효능: {effects}

[{country_name} 시장 트렌드]
- 트렌딩 성분: {', '.join(ing_list)}
- 트렌딩 기능: {', '.join(fn_list)}
- 트렌드 상세: {details[:500]}

사용자 제품의 성분/효능 중 위 트렌드 목록과 의미적으로 일치하는 항목을 찾으세요 (한국어·영어 무관).
- matched_keywords는 반드시 위 트렌드 목록에 실제로 있는 항목만 포함하세요
- 점수는 포함하지 마세요

반드시 아래 JSON 형식만 반환하세요:
{"matched_keywords": ["CICA", "보습"], "reasoning": "한두 문장 근거"}
```

---

## 데이터 입출력 파이프라인

**입력**
- 사용자 입력: `ingredients` (성분), `effects` (효능)
- DB 데이터: `MarketResearch.trends` → `ingredients[]`, `functions[]`, `details`

**파이프라인**

사용자 입력 + DB 트렌드 데이터 → 프롬프트 조립 → GPT-4o 호출 (temperature=0) → JSON 응답 파싱 → 코드 검증 (트렌드 목록 교차 확인) → 점수 계산 (√ratio) → 결과 반환

**출력**
```json
{
  "score": 0.63,
  "matched": ["CICA", "보습"],
  "reasoning": "CICA와 보습은 미국 트렌드 상위 성분으로 제품과 높은 적합도를 보입니다."
}
```

---

## 프롬프트 엔지니어링 설계 의도

**① Context 분리 주입**
사용자 입력과 DB 데이터를 `[사용자 제품 정보]` / `[시장 트렌드]` 섹션으로 명확히 구분해
LLM이 두 데이터의 출처를 혼동하지 않도록 구조화

**② GPT에게 점수를 맡기지 않음**
`"점수는 포함하지 마세요"` 명시 → GPT는 매칭 판단만 담당,
점수 계산은 코드에서 직접 처리 → 재현 가능하고 일관된 수치 보장

**③ Hallucination 이중 방지**
- 프롬프트 레벨: `"반드시 트렌드 목록에 실제로 있는 항목만 포함"` 지시
- 코드 레벨: GPT 응답을 실제 트렌드 목록과 교차 검증 후 없는 항목 제거

---

## 점수 계산 상세

```python
# 제곱근 스케일 적용
# 단순 비율 대비 첫 번째 매칭 항목에 더 큰 가중치 부여
ratio = len(verified) / max_possible  # verified: 검증된 매칭 수
score = ratio ** 0.5                  # sqrt: 1개 매칭도 의미있는 점수로 환산
```

| 매칭 수 / 최대 | ratio | score (√ratio) |
|:---:|:---:|:---:|
| 0 / 5 | 0.00 | 0.00 |
| 1 / 5 | 0.20 | 0.45 |
| 2 / 5 | 0.40 | 0.63 |
| 3 / 5 | 0.60 | 0.77 |
| 5 / 5 | 1.00 | 1.00 |

---

# 추천 근거 생성 — LLM 활용

`market_api/services/country_recommender.py` → `_generate_rationale()`

---

## 개요

트렌드 매칭 + 시장 데이터를 종합해 최적 진출 국가로 선정된 이유를 자연어로 생성한다.
`calc_trend_score()`의 `reasoning` 결과를 context로 재사용하는 LLM 체이닝 구조이다.

---

## 프롬프트 원문

시스템 프롬프트 없이 **user 메시지 단일 구성**. 페르소나를 첫 줄에 포함한다.

```
당신은 K-Beauty 글로벌 진출 전문 컨설턴트입니다.

[분석 제품]
- 제품명: {product_name}
- 주요 성분: {ingredients}
- 핵심 효능: {effects}

[최적 추천 국가: {country_name}]
- AI Score: {score_detail['total']:.1f} / 100
- 시장 규모: {ms.get('value', 'N/A')}, 성장률: {ms.get('cagr', 'N/A')}
- 트렌드 부합 근거: {trend_reasoning}
- 주요 유통 채널: {online}

위 데이터를 바탕으로 {country_name}이 최적 진출 국가인 이유를 3~4문장으로 설명하세요.
- 제품 성분/효능과 현지 트렌드의 연관성을 구체적으로 언급
- 시장 성장성 및 K-뷰티 수용도 언급
- 추천 유통 채널 언급
- 한국어, 전문가적이고 간결한 어조
```

---

## 데이터 입출력 파이프라인

**입력**
- 사용자 입력: `product_name`, `ingredients`, `effects`
- 1번 LLM 결과: `trend_reasoning` (트렌드 매칭 근거)
- DB 데이터: `MarketResearch` → 시장 규모(`value`, `cagr`), 유통 채널(`channels.online[]`)
- 계산 결과: `score_detail.total` (AI Score)

**파이프라인**

사용자 입력 + 1번 LLM reasoning + DB 시장 데이터 + AI Score → 프롬프트 조립 → GPT-4o 호출 (temperature=0.3) → 자연어 텍스트 반환

**출력**
```
미국 스킨케어 시장은 $19.6B 규모로 연 6.96% 성장 중이며,
CICA·보습 성분에 대한 소비자 수요가 높아 제품과의 트렌드 적합도가 우수합니다.
K-뷰티 브랜드에 대한 수용도가 높은 Sephora, Ulta를 통한 유통이 효과적일 것으로 판단됩니다.
```

---

## 프롬프트 엔지니어링 설계 의도

**① LLM 체이닝**
1번 호출(`calc_trend_score`)의 `reasoning`을 그대로 `트렌드 부합 근거`에 주입.
GPT가 이전 분석 결과를 바탕으로 일관된 근거를 생성하도록 연결

**② 수치 데이터 직접 주입**
AI Score, 시장 규모, 성장률을 프롬프트에 명시 → GPT가 수치를 지어내지 않도록 방지

**③ 출력 형식 제어**
문장 수(3~4문장), 언어(한국어), 어조(전문가적·간결)를 명시해 일관된 품질 유지.
temperature=0.3으로 자연스러운 문장 표현은 허용하되 과도한 창의성 억제
