"""
파이프라인 공통 처리 단계: 번역 → KeyBERT → GPT 분류

사용법:
    from crawling.pipeline_steps import process_new_reviews
    classified = process_new_reviews(new_reviews, channel="ulta")
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from deep_translator import GoogleTranslator
from keybert import KeyBERT
from openai import OpenAI

# ── 설정 ───────────────────────────────────────────────────────────────────────

CHUNK_SIZE  = 5
MAX_WORKERS = 4
MAX_RETRIES = 3
RETRY_SLEEP = 2.0
CHUNK_DELAY = 0.3

# 채널별 필드 매핑
CHANNEL_CONFIG = {
    "ulta":    {"body": "comment",     "head": "headline",  "src_lang": "en", "en_field": "comment"},
    "sephora": {"body": "ReviewText",  "head": "Title",     "src_lang": "en", "en_field": "ReviewText"},
    "qoo10":   {"body": "Review",      "head": None,        "src_lang": "ja", "en_field": "Review_en"},
    "rakuten": {"body": "Body",        "head": None,        "src_lang": "ja", "en_field": "Body_en"},
}

CATEGORIES = [
    "효과_성분", "사용감_텍스처", "향_냄새", "피부_트러블_부작용", "부정_리뷰",
    "포장_배송", "가격_가성비", "고객서비스", "제품불량",
    "재구매_추천", "커버력_색상", "지속력_밀착력", "미분류",
]

# v2: 효과_성분을 효능별로 세분화 (리뷰 점수산출용)
CATEGORIES_V2 = [
    "보습_수분", "미백_브라이트닝", "모공_각질", "주름_노화", "진정_장벽",
    "사용감_텍스처", "향_냄새", "피부_트러블_부작용", "부정_리뷰",
    "포장_배송", "가격_가성비", "고객서비스", "제품불량",
    "재구매_추천", "커버력_색상", "지속력_밀착력", "미분류",
]

# v2 세분류 → v1 통합 카테고리 매핑 (대시보드용)
V2_TO_V1 = {
    "보습_수분":       "효과_성분",
    "미백_브라이트닝": "효과_성분",
    "모공_각질":       "효과_성분",
    "주름_노화":       "효과_성분",
    "진정_장벽":       "효과_성분",
}

CATEGORY_KEYWORDS = {
    "효과_성분": ["moistur", "hydrat", "brighten", "firm", "wrinkle", "anti-aging", "pore", "glow",
                  "sooth", "calm", "vitamin", "retinol", "hyaluronic", "ceramide", "niacinamide",
                  "result", "noticeable", "spf", "sunscreen"],
    "사용감_텍스처": ["texture", "consistency", "watery", "thick", "light", "weightless", "heavy",
                     "greasy", "smooth", "finish", "blend", "apply", "matte", "dewy"],
    "향_냄새": ["scent", "smell", "fragrance", "unscented", "fragrance-free", "odor", "perfume"],
    "피부_트러블_부작용": ["break", "acne", "irritat", "rash", "sting", "burn", "react", "sensitive",
                          "allerg", "red", "itch"],
    "포장_배송": ["packag", "ship", "deliver", "box", "bottle", "pump", "leak", "seal"],
    "가격_가성비": ["price", "worth", "value", "expensive", "cheap", "afford", "cost", "pricey"],
    "재구매_추천": ["repurchas", "rebuy", "recommend", "love", "favorite", "staple", "holy grail",
                   "will buy again", "keep buying"],
    "커버력_색상": ["cover", "color", "shade", "tint", "pigment", "foundation", "match"],
    "지속력_밀착력": ["last", "long-lasting", "wear", "fade", "stay", "hold", "throughout the day"],
    "고객서비스": ["customer service", "return", "refund", "support", "response"],
    "제품불량": ["defect", "broken", "damaged", "wrong", "expired", "contaminated"],
    "부정_리뷰": ["disappoint", "waste", "terrible", "awful", "horrible", "worst", "never again",
                  "don't buy", "regret"],
}

KW_KO_MAP_PATH = Path(__file__).parent / "keyword_ko_map.json"

_kbert_model = None


def _get_kbert():
    global _kbert_model
    if _kbert_model is None:
        _kbert_model = KeyBERT()
    return _kbert_model


# ── 번역 유틸 ──────────────────────────────────────────────────────────────────

def _build_numbered(texts):
    return "\n".join(f"[{i+1}] {str(t).strip()}" for i, t in enumerate(texts))

def _parse_numbered(text, expected_n):
    pattern = re.compile(r"\[(\d+)\]\s*(.*?)(?=\[\d+\]|$)", re.DOTALL)
    found   = pattern.findall(text)
    result  = {int(idx): body.strip() for idx, body in found}
    return [result.get(i + 1, "") for i in range(expected_n)]

def _translate_single(text, src, tgt):
    if not text or not str(text).strip():
        return ""
    for attempt in range(MAX_RETRIES):
        try:
            res = GoogleTranslator(source=src, target=tgt).translate(str(text))
            if res:
                return res.strip()
        except Exception:
            time.sleep(RETRY_SLEEP * (attempt + 1))
    return "번역실패"

def _translate_chunk(texts, src, tgt):
    if not texts:
        return []
    joined = _build_numbered(texts)
    for attempt in range(MAX_RETRIES):
        try:
            translated = GoogleTranslator(source=src, target=tgt).translate(joined)
            if not translated:
                raise ValueError("빈 응답")
            parts = _parse_numbered(translated, len(texts))
            if all(p.strip() for p in parts):
                return parts
            for i, p in enumerate(parts):
                if not p:
                    parts[i] = _translate_single(texts[i], src, tgt)
            return parts
        except Exception:
            time.sleep(RETRY_SLEEP * (attempt + 1))
    return [_translate_single(t, src, tgt) for t in texts]


# ── Step 1: 번역 ───────────────────────────────────────────────────────────────

def translate_reviews(reviews: list, channel: str) -> list:
    """리뷰 리스트에 번역 필드 추가 (in-place 수정 후 반환)"""
    if not reviews:
        return reviews

    cfg      = CHANNEL_CONFIG[channel]
    body_col = cfg["body"]
    src_lang = cfg["src_lang"]

    bodies = [str(r.get(body_col, "") or "") for r in reviews]
    chunks = [bodies[i:i + CHUNK_SIZE] for i in range(0, len(bodies), CHUNK_SIZE)]

    if src_lang == "en":
        # EN → KO 단일 단계
        def run_chunk(chunk):
            res = _translate_chunk(chunk, "en", "ko")
            time.sleep(CHUNK_DELAY)
            return res

        all_ko = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            for result in ex.map(run_chunk, chunks):
                all_ko.extend(result)

        ko_field = body_col + "_ko"
        for r, ko in zip(reviews, all_ko):
            r[ko_field] = ko

        # head 번역 (ulta만)
        if cfg.get("head"):
            head_col = cfg["head"]
            heads = [str(r.get(head_col, "") or "") for r in reviews]
            head_chunks = [heads[i:i + CHUNK_SIZE] for i in range(0, len(heads), CHUNK_SIZE)]
            all_head_ko = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                for result in ex.map(run_chunk, head_chunks):
                    all_head_ko.extend(result)
            head_ko_field = head_col + "_ko"
            for r, hko in zip(reviews, all_head_ko):
                r[head_ko_field] = hko

    else:
        # JA → EN → KO 2단계
        def run_chunk_ja(chunk):
            en_texts = _translate_chunk(chunk, "ja", "en")
            time.sleep(CHUNK_DELAY)
            ko_texts = _translate_chunk(en_texts, "en", "ko")
            time.sleep(CHUNK_DELAY)
            return en_texts, ko_texts

        all_en, all_ko = [], []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            for en_chunk, ko_chunk in ex.map(run_chunk_ja, chunks):
                all_en.extend(en_chunk)
                all_ko.extend(ko_chunk)

        en_field = body_col + "_en"
        ko_field = body_col + "_ko"
        for r, en, ko in zip(reviews, all_en, all_ko):
            r[en_field] = en
            r[ko_field] = ko

    print(f"  [translate] {len(reviews)}개 완료")
    return reviews


# ── Step 2: KeyBERT ────────────────────────────────────────────────────────────

def _categorize(keywords: list) -> str:
    keyword_lower = [k.lower() for k in keywords]
    scores = {}
    for cat, kw_list in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in kw_list if any(kw in k for k in keyword_lower))
        if score > 0:
            scores[cat] = score
    return max(scores, key=scores.get) if scores else "미분류"

def extract_keywords(reviews: list, channel: str) -> list:
    if not reviews:
        return reviews

    kbert    = _get_kbert()
    en_field = CHANNEL_CONFIG[channel]["en_field"]

    for r in reviews:
        text = str(r.get(en_field, "") or "")
        if not text.strip():
            r["keybert_keywords"]  = []
            r["primary_category"]  = "미분류"
            continue
        try:
            kws = kbert.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words="english", top_n=5)
            keywords = [kw for kw, _ in kws]
        except Exception:
            keywords = []
        r["keybert_keywords"] = keywords
        r["primary_category"] = _categorize(keywords)  # 임시 분류 (GPT로 교체 예정)

    print(f"  [keybert] {len(reviews)}개 완료")
    return reviews


# ── Step 2-b: 신규 키워드 번역 ────────────────────────────────────────────────

def translate_new_keywords(reviews: list, top_n: int = 30) -> None:
    """리뷰의 keybert_keywords 중 미번역 키워드를 GPT로 번역 → keyword_ko_map.json 갱신
    빈도 상위 top_n개만 번역 (대시보드 표시용 top8 커버 목적)"""
    from collections import Counter
    kw_counter = Counter()
    for r in reviews:
        for kw in (r.get("keybert_keywords") or []):
            kw_counter[kw] += 1
    if not kw_counter:
        return

    if KW_KO_MAP_PATH.exists():
        with open(KW_KO_MAP_PATH, encoding="utf-8") as f:
            ko_map = json.load(f)
    else:
        ko_map = {}

    # 빈도 높은 순으로 top_n개 중 미번역만
    new_kws = [kw for kw, _ in kw_counter.most_common() if kw not in ko_map][:top_n]
    if not new_kws:
        print(f"  [keywords] 신규 키워드 없음 (기존 {len(ko_map)}개)")
        return

    print(f"  [keywords] 신규 키워드 {len(new_kws)}개 번역 중...")
    import os
    from dotenv import load_dotenv
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    system = (
        "You are a cosmetics/beauty product review keyword translator. "
        "Translate English keywords to natural Korean. "
        "Return ONLY a JSON object: {\"original\": \"번역\"}. "
        "Keep brand/product names as-is. Use common Korean cosmetics terminology."
    )
    BATCH = 80
    for i in range(0, len(new_kws), BATCH):
        batch = new_kws[i:i + BATCH]
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": f"Translate these keywords:\n{json.dumps(batch, ensure_ascii=False)}"},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            ko_map.update(json.loads(resp.choices[0].message.content))
        except Exception as e:
            print(f"  [keywords] 번역 오류: {e}")
        time.sleep(0.3)

    with open(KW_KO_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(ko_map, f, ensure_ascii=False, indent=2)
    print(f"  [keywords] keyword_ko_map.json 업데이트 (총 {len(ko_map)}개)")


# ── Step 3: GPT 분류 ───────────────────────────────────────────────────────────

def _gpt_classify_batch(batch: list, client) -> dict:
    prompt_items = "\n".join(
        f"[{item['idx']}] keywords={item['keywords']} | text={item['text'][:300]}"
        for item in batch
    )
    system_msg = f"""뷰티 제품 리뷰를 아래 카테고리 중 하나로 분류하세요.
카테고리: {CATEGORIES_V2}

각 리뷰에 대해 JSON 배열로 응답하세요:
[{{"idx": 번호, "primary_category": "카테고리명", "categories": ["카테고리1", ...]}}]
primary_category는 가장 핵심 카테고리 1개, categories는 해당되는 카테고리 모두."""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": prompt_items},
        ],
        temperature=0,
    )
    raw   = resp.choices[0].message.content
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return {}
    results = json.loads(match.group())
    return {r["idx"]: r for r in results}


def classify_reviews(reviews: list, channel: str, batch_size: int = 30) -> list:
    if not reviews:
        return reviews

    import os
    from dotenv import load_dotenv
    load_dotenv()
    client   = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    en_field = CHANNEL_CONFIG[channel]["en_field"]

    # unclassified만 GPT 재분류 (primary_category == 미분류 or not set)
    to_classify = [
        (i, r) for i, r in enumerate(reviews)
        if r.get("primary_category", "미분류") == "미분류"
    ]

    batch_items = [
        {"idx": i, "keywords": r.get("keybert_keywords", []), "text": str(r.get(en_field, "") or "")}
        for i, r in to_classify
    ]

    for start in range(0, len(batch_items), batch_size):
        batch = batch_items[start:start + batch_size]
        try:
            result_map = _gpt_classify_batch(batch, client)
            for item in batch:
                if item["idx"] in result_map:
                    res = result_map[item["idx"]]
                    v2_primary = res.get("primary_category", "미분류")
                    v2_cats    = res.get("categories", [])

                    # v2 세분류 저장 (점수산출용)
                    reviews[item["idx"]]["primary_category_v2"] = v2_primary
                    reviews[item["idx"]]["categories_v2"]        = v2_cats

                    # v1 통합 카테고리 파생 (대시보드용)
                    reviews[item["idx"]]["primary_category"] = V2_TO_V1.get(v2_primary, v2_primary)
                    seen = []
                    for cat in v2_cats:
                        mapped = V2_TO_V1.get(cat, cat)
                        if mapped not in seen:
                            seen.append(mapped)
                    reviews[item["idx"]]["categories"] = seen
        except Exception as e:
            print(f"  [classify] GPT 오류: {e}")

    print(f"  [classify] {len(reviews)}개 완료")
    return reviews


# ── 통합 엔트리포인트 ──────────────────────────────────────────────────────────

def process_new_reviews(reviews: list, channel: str) -> list:
    """
    신규 리뷰 리스트를 번역 → KeyBERT → GPT 분류까지 처리.
    반환: 모든 필드가 추가된 분류 완료 리뷰 리스트
    """
    if not reviews:
        return reviews
    print(f"\n[pipeline] {channel} 신규 리뷰 {len(reviews)}개 처리 시작")
    reviews = translate_reviews(reviews, channel)
    reviews = extract_keywords(reviews, channel)
    translate_new_keywords(reviews)
    reviews = classify_reviews(reviews, channel)
    print(f"[pipeline] {channel} 처리 완료\n")
    return reviews
