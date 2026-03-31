# 광고 이미지 생성 — LLM 활용

`market_api/services/ad_image.py` → `generate_ad_images()`

---

## 개요

제품 이미지 + 광고 전략 데이터를 입력받아 Google Gemini로
인스타그램 광고 이미지 2장을 생성한다. 2번의 Gemini 호출이 병렬로 실행된다.

| 호출 | 이미지 | 포맷 |
|------|--------|------|
| 1번 | 브랜드 컨셉 기반 피드 광고 | 1:1 정사각형 |
| 2번 | 광고 카피 기반 스토리 광고 | 9:16 세로 |

---

## 기술 플로우

```
사용자 입력
제품 이미지 (file) + 광고 전략 결과
(brand_concept, headline1/2, body_text1/2, key_messages)
        ↓
이미지 PIL 로드 → PNG 변환 → bytes
        ↓
프롬프트 2개 조립
1번: 브랜드 컨셉 기반 피드 광고 (1:1)
2번: 광고 카피 기반 스토리 광고 (9:16)
        ↓
Gemini 병렬 호출 (ThreadPoolExecutor max_workers=2)
텍스트 프롬프트 + 이미지 파트 동시 전송
        ↓
응답에서 inline_data 추출
        ↓
Base64 인코딩
        ↓
이미지 2장 반환
{"images": [{data, mime_type}, {data, mime_type}]}
```

---

## 데이터 입출력 파이프라인

**입력**
- 사용자 업로드: `image_file` (제품 이미지)
- 광고 전략 결과: `brand_concept`, `headline1/2`, `body_text1/2`, `key_messages`
- 제품 정보: `product_name`, `category`, `ingredients`, `effects`
- 국가: `country` (US → 영어, JP → 일본어)

**파이프라인**

제품 이미지 업로드 + 광고 전략 데이터 → 이미지 PNG 변환 → 프롬프트 2개 조립 → Gemini 병렬 호출 (ThreadPoolExecutor) → Base64 인코딩 → 이미지 2장 반환

**출력**
```json
{
  "images": [
    {"data": "iVBORw0KGgo...", "mime_type": "image/png"},
    {"data": "iVBORw0KGgo...", "mime_type": "image/png"}
  ]
}
```

---

## 프롬프트 원문

시스템 프롬프트 없이 **단일 텍스트 프롬프트 + 이미지 파트** 구성.

### 1번 프롬프트 — 피드 광고 (1:1)

```
다음 K-뷰티 제품의 인스타그램 피드 광고 이미지를 만들어주세요: {product_name} ({category}).
브랜드 컨셉: {brand_concept}.
광고 헤드라인: {headline1}.
광고 메시지: {body_text1}.
핵심 소구점: {key_messages}.
주요 성분: {ingredients}.
제품 효능: {effects}.
이미지에 텍스트가 포함될 경우 반드시 영어로 작성하세요.
스타일: 깔끔하고 밝은 인스타그램 정사각형(1:1) 피드 광고 형식.
제품 패키지 색상에 맞는 파스텔 또는 화이트 배경.
제품을 중앙에 배치하고 우아한 그림자와 하이라이트 처리.
여백을 충분히 활용한 미니멀 레이아웃 — 인스타그램 스폰서 광고 느낌.
고급 뷰티 브랜드의 상업 사진 스타일, 자연광, 4K 해상도.
```

### 2번 프롬프트 — 스토리 광고 (9:16)

```
다음 K-뷰티 제품의 인스타그램 스토리 광고 이미지를 만들어주세요: {product_name} ({category}).
캠페인 컨셉: {brand_concept}.
광고 헤드라인: {headline2}.
광고 카피: {body_text2}.
주요 성분: {ingredients}.
제품 효능: {effects}.
이미지에 텍스트가 포함될 경우 반드시 영어로 작성하세요.
스타일: 모던 K-뷰티 에디토리얼 감성.
9:16 세로 구도, 제품이 주인공.
부드러운 그라데이션 배경 또는 미니멀 플랫레이 구성 — 인스타그램 스토리/릴스 썸네일에 최적화.
프리미엄하면서도 친근한 K-뷰티 브랜드 색감.
전문 뷰티 사진 스타일, 시네마틱 소프트 조명, 고해상도.
```

**Context 구성**:
- 텍스트: 광고 전략 생성 결과 (`ad_strategy_llm.md`) 에서 받은 `brand_concept`, `headline`, `body_text`, `key_messages`
- 이미지: 사용자 업로드 제품 이미지 (PNG 변환 후 `types.Part.from_bytes`로 전달)

---

## 프롬프트 엔지니어링 설계 의도

**① 광고 전략 결과 연결 (LLM 체이닝)**
광고 전략 생성 (`ad_strategy.py`) GPT 결과를 이미지 프롬프트에 그대로 주입
→ 텍스트 전략과 이미지 방향성의 일관성 확보

**② 이미지별 포맷 전용 프롬프트**
피드(1:1)와 스토리(9:16)를 별도 프롬프트로 분리
→ 각 광고 포맷에 최적화된 구도·레이아웃 지시

**③ 국가별 언어 분기**
`country == "JP"` → 일본어, 그 외 → 영어로 텍스트 언어 지정
→ 현지화된 광고 이미지 텍스트 생성

**④ 병렬 처리**
`ThreadPoolExecutor(max_workers=2)`로 2번 호출을 동시 실행
→ 응답 시간 단축
