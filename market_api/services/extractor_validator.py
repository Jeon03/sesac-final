"""
시장 규모 추출기 일관성 검증.

동일 원문에 temperature=0.8로 N회 추출 → 필드별 일관성 분석 → AI 채점.
"""
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from market_api.services.section_extractor import SECTION_PROMPTS, _parse_llm_json


# ── 섹션별 핵심 검증 필드 ─────────────────────────────────────────────────────
VALIDATION_FIELDS: dict[str, list[str]] = {
    "market_size":   ["value", "cagr", "year", "forecast_year", "forecast_value"],
    "kbeauty_share": ["share", "rank", "export_value", "yoy_growth"],
    "trends":        ["ingredients", "formulations", "functions"],
    "channels":      ["online_ratio", "key_platform"],
    "competitors":   ["market_leader", "market_leader_share"],
}


def _extract_once(
    section: str,
    country: str,
    raw_text: str,
    source_url: str,
    temperature: float = 0.8,
    max_chars: int = 20000,
) -> dict:
    """temperature=0.8로 단일 추출"""
    prompt = SECTION_PROMPTS[section]
    llm = ChatOpenAI(model="gpt-4o", temperature=temperature)
    chain = prompt | llm
    result = chain.invoke({
        "country": country,
        "source_url": source_url,
        "raw_text": raw_text[:max_chars],
    })
    data = _parse_llm_json(result.content)
    data["source_url"] = source_url
    return data


def run_extractions(
    section: str,
    country: str,
    raw_text: str,
    source_url: str,
    n: int = 30,
    temperature: float = 0.8,
    max_workers: int = 5,
) -> list[dict]:
    """N번 병렬 추출. 진행상황을 print로 출력."""
    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_extract_once, section, country, raw_text, source_url, temperature): i
            for i in range(n)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results.append(future.result())
                print(f"  [{len(results):>2}/{n}] 완료", end="\r")
            except Exception as e:
                errors.append(str(e))
                print(f"  [{idx+1}] 실패: {e}")

    print(f"\n총 {len(results)}개 성공, {len(errors)}개 실패")
    return results


def analyze_consistency(results: list[dict], section: str) -> dict:
    """
    필드별 일관성 분석.

    Returns:
        {
          "field_name": {
            "most_common": "가장 많이 나온 값",
            "consistency_pct": 86.7,
            "count": 26,
            "total": 30,
            "distribution": {"값A": 26, "값B": 3, "(없음)": 1},
          }
        }
    """
    fields = VALIDATION_FIELDS.get(section, [])
    analysis = {}

    for field in fields:
        all_values = []
        filled_values = []  # 빈값 제외

        for r in results:
            v = r.get(field)
            if isinstance(v, list):
                key = tuple(sorted(str(x) for x in v))
                is_empty = len(v) == 0
            elif v is None or v == "":
                key = "(없음)"
                is_empty = True
            else:
                key = str(v).strip()
                is_empty = False

            all_values.append(key)
            if not is_empty:
                filled_values.append(key)

        fill_rate = len(filled_values) / len(all_values) * 100

        if filled_values:
            filled_counter = Counter(filled_values)
            most_common_val, most_common_count = filled_counter.most_common(1)[0]
            # 빈값 제외 기준 일관성
            consistency_pct = most_common_count / len(filled_values) * 100
            distribution = {str(k): v for k, v in filled_counter.most_common(10)}
        else:
            most_common_val = "(없음)"
            most_common_count = 0
            consistency_pct = 0.0
            distribution = {}

        analysis[field] = {
            "most_common": most_common_val if not isinstance(most_common_val, tuple) else list(most_common_val),
            "consistency_pct": round(consistency_pct, 1),   # 값이 들어왔을 때 일치율
            "fill_rate": round(fill_rate, 1),               # 빈값 아닌 비율 (참고용)
            "count": most_common_count,
            "filled": len(filled_values),
            "total": len(all_values),
            "distribution": distribution,
        }

    return analysis


# ── AI 검증 프롬프트 ──────────────────────────────────────────────────────────
_AI_VALIDATOR_SYSTEM = """당신은 LLM 추출기 품질 검증 전문가입니다.
아래는 동일한 원문에서 temperature=0.8로 {n}회 반복 추출한 결과의 필드별 일관성 분석입니다.

아래 4가지 지표를 각각 5.0 만점으로 채점하세요.
**빈값(fill_rate)은 채점에서 무시하세요. 값이 실제로 들어왔을 때 얼마나 일관되고 정확한지만 평가합니다.**

1. accuracy (정확도): 들어온 값이 원문 수치와 일치할 가능성. 최빈값이 명확하고 구체적인 수치일수록 높음.
2. consistency (일관성): 값이 들어왔을 때 동일한 값이 나오는 비율 (consistency_pct 기준, 빈값 제외). 높을수록 좋음.
3. hallucination_free (환각 없음): 원문에 없는 내용을 생성하지 않는 정도. 값 분산이 심하거나 근거 없는 수치가 나올수록 낮음.
4. overall (종합): 위 3가지를 종합한 점수.

반드시 아래 JSON 형식으로만 반환하세요 (설명 텍스트 없이 순수 JSON):
{{
  "scores": {{
    "accuracy":          {{"score": 4.2, "reason": "근거 1문장"}},
    "consistency":       {{"score": 4.5, "reason": "근거 1문장"}},
    "hallucination_free":{{"score": 4.1, "reason": "근거 1문장"}},
    "overall":           {{"score": 4.2, "reason": "종합 근거 1문장"}}
  }},
  "recommendations": ["권고사항 1", "권고사항 2"],
  "summary": "종합 평가 2~3문장"
}}"""

_AI_VALIDATOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _AI_VALIDATOR_SYSTEM),
    ("human", "섹션: {section}\n국가: {country}\n추출 횟수: {n}\n\n[일관성 분석]\n{analysis_json}"),
])


def ai_score(section: str, country: str, n: int, analysis: dict) -> dict:
    """일관성 분석 결과를 AI로 채점하여 검증 보고서 반환."""
    llm = ChatOpenAI(model="gpt-5.4", temperature=0)
    chain = _AI_VALIDATOR_PROMPT | llm
    result = chain.invoke({
        "section": section,
        "country": country,
        "n": n,
        "analysis_json": json.dumps(analysis, ensure_ascii=False, indent=2),
    })
    return _parse_llm_json(result.content)


def print_report(report: dict, section: str, country: str) -> None:
    """검증 보고서를 바 차트 형식으로 출력."""
    MAX_SCORE = 5.0
    BAR_WIDTH  = 10  # 총 블록 수 (█ + ░)

    label_map = {
        "accuracy":           "accuracy          ",
        "consistency":        "consistency       ",
        "hallucination_free": "hallucination_free",
        "overall":            "overall           ",
    }

    print(f"\n{'─' * 55}")
    print(f"  추출기 검증 보고서 | {section} / {country}")
    print(f"{'─' * 55}")

    scores = report.get("scores", {})
    for key, label in label_map.items():
        entry = scores.get(key, {})
        score = entry.get("score", 0.0)
        filled = round(score / MAX_SCORE * BAR_WIDTH)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        print(f"  {label}  {bar}  {score:.2f}/{MAX_SCORE:.2f}")

    print(f"{'─' * 55}")

    if report.get("recommendations"):
        print("\n  [권고사항]")
        for rec in report["recommendations"]:
            print(f"    • {rec}")

    if report.get("summary"):
        print(f"\n  [종합 평가]\n  {report['summary']}")


def validate(
    section: str,
    country: str,
    raw_text: str,
    source_url: str,
    n: int = 30,
    temperature: float = 0.8,
    max_workers: int = 5,
) -> dict:
    """
    전체 검증 파이프라인.

    Returns:
        {
          "extraction_results": [...],   # n개 원본 추출 결과
          "consistency_analysis": {...}, # 필드별 일관성 통계
          "validation_report": {...},    # AI 채점 보고서
        }
    """
    print(f"[1/3] {section}/{country} — temperature={temperature}로 {n}회 추출 중...")
    results = run_extractions(section, country, raw_text, source_url, n, temperature, max_workers)

    print(f"[2/3] 일관성 분석 중...")
    analysis = analyze_consistency(results, section)

    print(f"[3/3] AI 채점 중...")
    report = ai_score(section, country, n, analysis)

    return {
        "extraction_results": results,
        "consistency_analysis": analysis,
        "validation_report": report,
    }
