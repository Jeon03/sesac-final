"""
KeyBERT 키워드 한국어 번역 스크립트
keywords_to_translate.json → keyword_ko_map.json

python crawling/translate_keywords.py
"""
import json
import os
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).parent
INPUT  = BASE / "keywords_to_translate.json"
OUTPUT = BASE / "keyword_ko_map.json"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BATCH_SIZE = 80
SYSTEM_PROMPT = """You are a cosmetics/beauty product review keyword translator.
Translate English keywords to natural Korean.
Rules:
- Return ONLY a JSON object: {"original": "번역"}
- Keep brand names, product names as-is (e.g. "rhode" → "rhode")
- Generic noise words (use, good, just, ve, doesn, like, really, feel, time, day, week, etc.) → translate literally but keep short
- Beauty/skincare terms should use common Korean cosmetics terminology
- Compound phrases should be translated as a whole natural expression
"""

def translate_batch(keywords: list[str]) -> dict:
    kw_json = json.dumps(keywords, ensure_ascii=False)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Translate these keywords:\n{kw_json}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    return json.loads(raw)


def main():
    with open(INPUT, encoding="utf-8") as f:
        keywords = json.load(f)

    # 이미 번역된 것 불러오기 (중단 후 재시작 시 이어서)
    if OUTPUT.exists():
        with open(OUTPUT, encoding="utf-8") as f:
            ko_map = json.load(f)
        print(f"기존 번역 {len(ko_map)}개 로드")
    else:
        ko_map = {}

    remaining = [kw for kw in keywords if kw not in ko_map]
    total = len(remaining)
    print(f"번역 대상: {total}개")

    for i in range(0, total, BATCH_SIZE):
        batch = remaining[i:i + BATCH_SIZE]
        print(f"  [{i+1}~{min(i+BATCH_SIZE, total)}/{total}] 번역 중...", end=" ")
        try:
            result = translate_batch(batch)
            ko_map.update(result)
            print(f"완료 ({len(result)}개)")
        except Exception as e:
            print(f"오류: {e}")

        # 중간 저장 (10배치마다)
        if (i // BATCH_SIZE + 1) % 10 == 0:
            with open(OUTPUT, "w", encoding="utf-8") as f:
                json.dump(ko_map, f, ensure_ascii=False, indent=2)
            print(f"  [저장] 현재 {len(ko_map)}개")

        time.sleep(0.3)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(ko_map, f, ensure_ascii=False, indent=2)
    print(f"\n완료! 총 {len(ko_map)}개 저장 → {OUTPUT}")


if __name__ == "__main__":
    main()
