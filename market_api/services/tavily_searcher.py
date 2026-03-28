"""
Tavily 웹 검색으로 섹션별 최신 시장 데이터를 동적으로 수집.

search_section(section, country) → (합친 텍스트, [출처 URL들])
"""
import os
from datetime import datetime
from tavily import TavilyClient

# ── market_size 전용 도메인 고정 (section_crawler 출처와 일치) ─────────────────
MARKET_SIZE_DOMAINS: dict[str, list[str]] = {
    "US": ["zionmarketresearch.com"],
    "JP": ["menafn.com"],
}

# ── 섹션 × 국가별 검색 쿼리 템플릿 ({year}, {prev_year} 자동 치환) ────────────
SEARCH_QUERY_TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("market_size", "US"): [
        "United States domestic skincare market size {prev_year} revenue billion USD CAGR forecast NOT global",
        "US beauty skincare industry market value {prev_year} statistics report North America only",
    ],
    ("market_size", "JP"): [
        "Japan domestic skincare cosmetics market size {prev_year} billion yen revenue CAGR forecast NOT global",
        "일본 국내 스킨케어 화장품 시장 규모 {prev_year} 억 엔 성장률 통계 일본 한정",
    ],
    ("kbeauty_share", "US"): [
        "Korea cosmetics United States import market share ranking {prev_year} statistics percent",
        "한국 화장품 미국 수출 점유율 순위 {prev_year} 통계 1위 수입국",
        "K-beauty US import share {prev_year} HS 3304 customs trade data",
    ],
    ("kbeauty_share", "JP"): [
        "한국 화장품 일본 수입 점유율 순위 {prev_year} 통계 1위 KOTRA",
        "일본 화장품 수입국 한국 점유율 {prev_year} 수입액 전년대비 관세청",
        "Korea cosmetics Japan import share ranking {prev_year} HS 330499 trade statistics",
    ],
    ("trends", "US"): [
        "US skincare consumer trend {prev_year} {year} popular ingredients retinol niacinamide peptide report",
        "미국 스킨케어 소비자 트렌드 인기 성분 기능 {prev_year} {year} KOTRA",
    ],
    ("trends", "JP"): [
        "일본 스킨케어 소비자 트렌드 인기 성분 기능 {prev_year} {year} KOTRA",
        "Japan skincare ingredient trend {prev_year} {year} consumer popular functional beauty report",
    ],
    ("channels", "US"): [
        "K-beauty distribution channel US {prev_year} online offline Amazon Sephora Ulta retail market share",
        "한국 화장품 미국 유통 채널 온라인 오프라인 비중 {prev_year} 아마존 세포라",
    ],
    ("channels", "JP"): [
        "한국 화장품 일본 유통 채널 온라인 오프라인 Qoo10 라쿠텐 {prev_year}",
        "K-beauty Japan distribution channel online offline Qoo10 Rakuten {prev_year}",
    ],
    ("competitors", "US"): [
        "US skincare top brands market share ranking {prev_year} statistics revenue CeraVe Neutrogena",
        "미국 스킨케어 브랜드 시장 점유율 순위 {prev_year} 통계",
    ],
    ("competitors", "JP"): [
        "일본 스킨케어 화장품 브랜드 시장 점유율 순위 {prev_year} 시세이도 카오 코세",
        "Japan skincare cosmetics brand market share ranking {prev_year} Shiseido Kao Kose statistics",
    ],
}


def _build_queries(section: str, country: str) -> list[str]:
    """템플릿에 현재 연도를 주입하여 쿼리 리스트 반환."""
    templates = SEARCH_QUERY_TEMPLATES.get((section, country))
    if not templates:
        raise ValueError(f"검색 쿼리 없음: {section}-{country}")

    now = datetime.now()
    year = now.year
    prev_year = year - 1

    return [t.format(year=year, prev_year=prev_year) for t in templates]


def search_section(section: str, country: str, max_results: int = 3) -> tuple[str, list[str]]:
    """
    Tavily로 해당 섹션+국가의 최신 자료를 검색.

    Args:
        section: 섹션명 (market_size / kbeauty_share / trends / channels / competitors)
        country: 국가 코드 (US / JP)
        max_results: 쿼리당 검색 결과 수

    Returns:
        (합친 텍스트, [출처 URL들])
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY 환경변수가 설정되지 않았습니다.")

    queries = _build_queries(section, country)
    client = TavilyClient(api_key=api_key)

    texts = []
    seen_urls: set[str] = set()
    urls = []

    preferred_domains = MARKET_SIZE_DOMAINS.get(country) if section == "market_size" else None

    for query in queries:
        # market_size: 우선 도메인 고정 검색 → 결과 없으면 전체 검색 폴백
        if preferred_domains:
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_raw_content=section == "market_size",
                include_domains=preferred_domains,
            )
            if not response.get("results"):
                print(f"   ⚠️  도메인 고정 검색 결과 없음 → 전체 검색으로 폴백")
                response = client.search(
                    query=query,
                    max_results=max_results,
                    search_depth="advanced",
                    include_raw_content=section == "market_size",
                )
        else:
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_raw_content=section == "market_size",
            )
        for r in response.get("results", []):
            url = r.get("url", "")
            content = r.get("content", "")
            if content and url not in seen_urls:
                texts.append(f"[출처: {url}]\n{content}")
                urls.append(url)
                seen_urls.add(url)

    combined_text = "\n\n---\n\n".join(texts)
    return combined_text, urls
