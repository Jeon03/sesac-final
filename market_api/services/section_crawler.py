"""
섹션별 URL 크롤러 - 각 시장 조사 항목마다 전용 URL + 전용 셀렉터로 텍스트 추출.

report.ipynb에서 검증된 셀렉터를 그대로 사용합니다.
JP channels(biz.chosun.com)만 Selenium 사용, 나머지는 requests + BeautifulSoup.

crawl_all_sections(country) → {section: (text, source_url)}
"""
import time
import requests
from bs4 import BeautifulSoup

# ── 섹션별 × 국가별 URL 매핑 ─────────────────────────────────────────────────
SECTION_URLS = {
    "market_size": {
        "US": "https://www.zionmarketresearch.com/report/us-skincare-market",
        "JP": "https://menafn.com/1109977082/Japan-Skin-Care-Products-Market-Size-Worth-USD-116-Billion-By-2033-CAGR-418",
    },
    "kbeauty_share": {
        "US": "https://koreaproductpost.com/korea-surpasses-france-becomes-top-cosmetics-exporter-to-the-us/",
        "JP": "https://kokusaishogyo-online.jp/2025/02/175944",
    },
    "trends": {
        "US": "https://dream.kotra.or.kr/dream/cms/news/actionKotraBoardDetail.do?SITE_NO=2&MENU_ID=3530&bbsSn=254&pNttSn=234165&CONTENTS_NO=1",
        "JP": "https://www.sourceready.com/report/detail/japan-skincare-market-report-2025-trends-brands-products",
    },
    "channels": {
        "US": "https://www.kedglobal.com/beauty-cosmetics/newsView/ked202510100010",
        "JP": "https://biz.chosun.com/en/en-retail/2025/03/14/4MAZV5QDYJHPRMHAELGWZOLPU4/",
    },
    "competitors": {
        "US": "https://www.mjsmedicals.com/what-is-the-most-popular-skincare-brand-in-the-usa/",
        "JP": "https://www.fortunebusinessinsights.com/ko/japan-cosmetics-market-114215",
    },
}

SECTION_LABELS = {
    "market_size":   "시장 규모·성장률",
    "kbeauty_share": "K-뷰티 점유율",
    "trends":        "성분·기능 트렌드",
    "channels":      "유통 채널",
    "competitors":   "경쟁 브랜드",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/110.0.0.0 Safari/537.36"
    ),
}


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def _get_soup(url: str, timeout: int = 15) -> BeautifulSoup | None:
    """requests로 페이지를 가져와 BeautifulSoup 반환. 실패 시 None."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "latin-1"):
            resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"      ⚠️  요청 실패: {e}")
        return None


def _extract(soup: BeautifulSoup, selector: str, remove_selectors: list[str] | None = None) -> str:
    """
    selector로 컨테이너를 찾고, remove_selectors에 해당하는 하위 태그를 제거한 뒤
    텍스트를 반환. 컨테이너를 못 찾으면 빈 문자열.
    """
    container = soup.select_one(selector)
    if not container:
        return ""
    for sel in (remove_selectors or []):
        for tag in container.select(sel):
            tag.decompose()
    return container.get_text(separator="\n\n", strip=True)


# ── URL별 전용 크롤러 ─────────────────────────────────────────────────────────

def _fetch_us_market_size(url: str) -> str:
    """zionmarketresearch.com - div#Descriptionss"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(soup, "div#Descriptionss")


def _fetch_jp_market_size(url: str) -> str:
    """menafn.com - div#ContentPlaceHolder1_div_story"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(soup, "div#ContentPlaceHolder1_div_story", ["script", "style"])


def _fetch_us_kbeauty_share(url: str) -> str:
    """koreaproductpost.com - .entry-content.clearfix"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(
        soup,
        ".entry-content.clearfix",
        [".addtoany_share_save_container", "#ez-toc-container", "script", "style"],
    )


def _fetch_jp_kbeauty_share(url: str) -> str:
    """kokusaishogyo-online.jp - .main .article-body"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(
        soup,
        ".main .article-body",
        [".sns-share", ".related-post", ".ads-sec", "script", "style", "iframe", "object"],
    )


def _fetch_us_trends(url: str) -> str:
    """dream.kotra.or.kr - #pdfArea .viewDataWrap"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(soup, "#pdfArea .viewDataWrap", ["script", "style"])


def _fetch_jp_trends(url: str) -> str:
    """sourceready.com - div[class*='AgentMarkdown__MarkdownContainer']"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(
        soup,
        'div[class*="AgentMarkdown__MarkdownContainer"]',
        ["button", "svg", "img", ".ProductCard__ButtonContainer"],
    )


def _fetch_us_channels(url: str) -> str:
    """kedglobal.com - div._content"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(soup, "div._content", ["figure", "figcaption", "script", "style", "ins"])


def _fetch_jp_channels_selenium(url: str) -> str:
    """
    biz.chosun.com - JS 렌더링 필요 → Selenium 사용.
    section[itemprop='articleBody'] 대기 후 불필요 요소 제거.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )

        try:
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            article = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "section[itemprop='articleBody']")
                )
            )
            time.sleep(2)  # JS 완료 대기

            driver.execute_script("""
                document.querySelectorAll('figure').forEach(el => el.remove());
                document.querySelectorAll('.arcad-wrapper, #taboola-mid-article-widget-1x1').forEach(el => el.remove());
                document.querySelectorAll('.text--grey-60').forEach(el => el.remove());
            """)

            return article.text.strip()
        finally:
            driver.quit()

    except Exception as e:
        print(f"      ⚠️  Selenium 실패: {e}")
        return ""


def _fetch_us_competitors(url: str) -> str:
    """mjsmedicals.com - .elementor-widget-theme-post-content .elementor-widget-container"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(
        soup,
        ".elementor-widget-theme-post-content .elementor-widget-container",
        ["#ez-toc-container", "script", "style", "img", "figure"],
    )


def _fetch_jp_competitors(url: str) -> str:
    """fortunebusinessinsights.com - div#summury-sub"""
    soup = _get_soup(url)
    if not soup:
        return ""
    return _extract(
        soup,
        "div#summury-sub",
        [".after-h2-images", ".chartTitle", "script", "style", ".chartjs-size-monitor"],
    )


# ── 디스패치 테이블 ───────────────────────────────────────────────────────────

_FETCHERS: dict[tuple[str, str], callable] = {
    ("market_size",   "US"): _fetch_us_market_size,
    ("market_size",   "JP"): _fetch_jp_market_size,
    ("kbeauty_share", "US"): _fetch_us_kbeauty_share,
    ("kbeauty_share", "JP"): _fetch_jp_kbeauty_share,
    ("trends",        "US"): _fetch_us_trends,
    ("trends",        "JP"): _fetch_jp_trends,
    ("channels",      "US"): _fetch_us_channels,
    ("channels",      "JP"): _fetch_jp_channels_selenium,
    ("competitors",   "US"): _fetch_us_competitors,
    ("competitors",   "JP"): _fetch_jp_competitors,
}


# ── 공개 인터페이스 ───────────────────────────────────────────────────────────

def crawl_section(section: str, country: str) -> tuple[str, str]:
    """
    지정된 섹션+국가의 URL을 크롤링.

    Returns:
        (text, source_url) - 텍스트 없으면 ("", url)
    """
    url = SECTION_URLS.get(section, {}).get(country, "")
    if not url:
        print(f"   ⚠️  URL 없음: {section}-{country}")
        return "", ""

    label = SECTION_LABELS.get(section, section)
    print(f"   [{country}] {label} 크롤링 중... {url[:60]}...")

    fetcher = _FETCHERS.get((section, country))
    if not fetcher:
        print(f"      ⚠️  크롤러 없음: {section}-{country}")
        return "", url

    text = fetcher(url)

    if text:
        print(f"      OK {len(text):,}자 수집")
    else:
        print(f"      FAIL 텍스트 수집 실패")

    return text, url


def crawl_all_sections(country: str, delay: float = 1.5) -> dict[str, tuple[str, str]]:
    """
    해당 국가의 모든 섹션을 순서대로 크롤링.

    Args:
        country: "US" 또는 "JP"
        delay: 요청 간 대기 시간(초)

    Returns:
        {section_name: (text, source_url)}
    """
    results = {}
    sections = list(SECTION_URLS.keys())

    for i, section in enumerate(sections):
        text, url = crawl_section(section, country)
        results[section] = (text, url)
        if i < len(sections) - 1:
            time.sleep(delay)

    return results
