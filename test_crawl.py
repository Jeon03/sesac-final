"""
섹션별 크롤링 테스트 스크립트 - Django 없이 단독 실행 가능.

실행:
    python test_crawl.py           # 전체 테스트
    python test_crawl.py US        # 미국만
    python test_crawl.py JP        # 일본만
    python test_crawl.py US market_size   # 특정 섹션만
"""
import sys
import time
import requests
import io

# Windows 터미널 UTF-8 출력 강제
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from bs4 import BeautifulSoup

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside",
             "noscript", "form", "button", "iframe", "svg"}

PREVIEW_CHARS = 300  # 미리보기 출력 글자수


def fetch_and_preview(url: str) -> tuple[bool, str, int]:
    """URL 크롤링 → (성공여부, 미리보기텍스트, 전체글자수)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "latin-1"):
            resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup.find_all(SKIP_TAGS):
            tag.decompose()

        body = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", {"id": "content"})
            or soup.find("div", {"class": lambda c: c and "content" in c})
            or soup.body
        )
        text = (body or soup).get_text(separator="\n", strip=True)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        clean = "\n".join(lines)

        return True, clean[:PREVIEW_CHARS], len(clean)

    except requests.exceptions.Timeout:
        return False, "타임아웃", 0
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP {e.response.status_code}", 0
    except Exception as e:
        return False, str(e), 0


def run_test(country_filter=None, section_filter=None):
    countries = [country_filter] if country_filter else ["US", "JP"]
    sections  = [section_filter] if section_filter else list(SECTION_URLS.keys())

    total = ok = fail = 0

    for section in sections:
        label = SECTION_LABELS.get(section, section)
        print(f"\n{'='*60}")
        print(f"  섹션: {label} ({section})")
        print(f"{'='*60}")

        for country in countries:
            url = SECTION_URLS.get(section, {}).get(country)
            if not url:
                continue

            total += 1
            print(f"\n[{country}] {url}")
            print(f"  크롤링 중...", end=" ", flush=True)

            success, preview, char_count = fetch_and_preview(url)

            if success:
                ok += 1
                print(f"✅ {char_count:,}자 수집")
                print(f"  미리보기:")
                for line in preview.split("\n")[:8]:
                    if line.strip():
                        print(f"    {line[:100]}")
            else:
                fail += 1
                print(f"❌ 실패: {preview}")

            time.sleep(1.0)

    print(f"\n{'='*60}")
    print(f"  결과: {ok}/{total} 성공, {fail} 실패")
    print(f"{'='*60}\n")

    if fail > 0:
        print("⚠️  실패한 URL은 JS 렌더링이 필요하거나 접근 제한이 있을 수 있습니다.")
        print("   Selenium 또는 Playwright로 대체 크롤링이 필요할 수 있어요.")


if __name__ == "__main__":
    args = sys.argv[1:]
    country_arg = None
    section_arg = None

    for arg in args:
        if arg.upper() in ("US", "JP"):
            country_arg = arg.upper()
        elif arg in SECTION_URLS:
            section_arg = arg

    run_test(country_arg, section_arg)
