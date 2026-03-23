"""
Meta 광고 라이브러리에서 브랜드 page_id 탐색 (GraphQL 인터셉트 방식)

사용법:
    python find_page_ids.py --channel ulta
    python find_page_ids.py --channel ulta --force   # 이미 등록된 브랜드도 재검색
"""
import argparse
import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

_BASE = Path(__file__).parent

RANKINGS = {
    "ulta":    _BASE / "ulta_rankings_current.jsonl",
    "sephora": _BASE / "sephora_rankings_current.jsonl",
    "qoo10":   _BASE / "qoo10_rankings_current.jsonl",
    "rakuten": _BASE / "rakuten_rankings_current.jsonl",
}
MARKET = {
    "ulta": "US", "sephora": "US",
    "qoo10": "JP", "rakuten": "JP",
}
PAGE_ID_JSON = _BASE / "brand_page_ids_all.json"


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def load_rankings(channel):
    path = Path(RANKINGS[channel])
    if not path.exists():
        raise FileNotFoundError(f"{path} 없음")
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_page_map(channel):
    path = Path(PAGE_ID_JSON)
    if not path.exists():
        return {}
    data = json.load(open(path, encoding="utf-8"))
    return data.get(channel, {}).get("brands", {})


def save_page_map(channel, brand, page_id):
    path = Path(PAGE_ID_JSON)
    data = json.load(open(path, encoding="utf-8")) if path.exists() else {}
    if channel not in data:
        data[channel] = {"market": MARKET[channel], "brands": {}}
    data[channel]["brands"][brand] = {"page_id": page_id}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Selenium GraphQL 인터셉트 ──────────────────────────────────────────────────

def fetch_candidates(brand: str, market: str) -> list:
    """
    Meta Ads Library 검색창 클릭 → GraphQL typeahead_suggestions 인터셉트
    반환: [{"name": ..., "page_id": ..., "likes": ..., "ig_followers": ..., "category": ...}, ...]
         IG 팔로워 내림차순 정렬
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    wait = WebDriverWait(driver, 15)
    all_pages = {}

    try:
        url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status=active&ad_type=all&country={market}"
            f"&is_targeted_country=false&media_type=all"
            f"&q={brand}&search_type=keyword_unordered"
            f"&sort_data[direction]=desc&sort_data[mode]=total_impressions"
        )
        driver.get(url)
        time.sleep(6)

        # 검색창 클릭 → 자동완성 GraphQL 요청 유도
        search_input = None
        for css in [
            "input[placeholder*='키워드']",
            "input[placeholder*='keyword']",
            "input[placeholder*='Search']",
            "input[placeholder*='advertiser']",
            "input[type='text']",
        ]:
            try:
                search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
                break
            except Exception:
                continue

        if search_input is None:
            raise Exception("검색창을 찾을 수 없음")

        driver.execute_script("arguments[0].click();", search_input)
        time.sleep(6)

        # 네트워크 로그에서 GraphQL typeahead_suggestions 파싱
        for entry in driver.get_log("performance"):
            log = json.loads(entry["message"])["message"]
            if log.get("method") != "Network.responseReceived":
                continue
            if "facebook.com/api/graphql/" not in log["params"]["response"]["url"]:
                continue
            try:
                body = driver.execute_cdp_cmd(
                    "Network.getResponseBody",
                    {"requestId": log["params"]["requestId"]}
                )
                data = json.loads(body["body"])
                suggestions = (
                    data.get("data", {})
                    .get("ad_library_main", {})
                    .get("typeahead_suggestions", {})
                )
                for field in ["page_results", "exact_page_results", "filtered_page_results"]:
                    results = suggestions.get(field, [])
                    if isinstance(results, dict):
                        results = [results]
                    for p in results:
                        pid   = p.get("page_id")
                        pname = p.get("name")
                        if pid and pname:
                            ig_foll = int(p.get("ig_followers") or 0)
                            if ig_foll > 0:
                                all_pages[pid] = {
                                    "name":         pname,
                                    "page_id":      pid,
                                    "likes":        int(p.get("likes") or 0),
                                    "ig_followers": ig_foll,
                                    "category":     p.get("category", ""),
                                }
            except Exception:
                continue

    except Exception as e:
        print(f"  [fetch] 오류: {e}")
    finally:
        driver.quit()

    return sorted(all_pages.values(), key=lambda x: x["ig_followers"], reverse=True)


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, choices=list(RANKINGS.keys()))
    parser.add_argument("--force", action="store_true", help="이미 등록된 브랜드도 재검색")
    args = parser.parse_args()

    channel = args.channel
    market  = MARKET[channel]

    rankings = load_rankings(channel)
    brands = list(dict.fromkeys(
        str(r.get("brand", "")).strip() for r in rankings if r.get("brand")
    ))
    existing = load_page_map(channel)

    print(f"\n[{channel.upper()}] 총 {len(brands)}개 브랜드 탐색 시작\n")

    for brand in brands:
        if brand in existing and not args.force:
            print(f"  [SKIP] {brand} (이미 등록됨: {existing[brand]['page_id']})")
            continue

        print(f"\n  [{brand}] 검색 중...")
        candidates = fetch_candidates(brand, market)

        if not candidates:
            print(f"  → 후보 없음. 수동 등록 필요.")
            continue

        print(f"\n  {'번호':<4} {'이름':<30} {'Page ID':<20} {'IG 팔로워':>12} {'카테고리'}")
        print(f"  {'-'*80}")
        for i, c in enumerate(candidates):
            print(f"  {i:<4} {c['name']:<30} {c['page_id']:<20} {c['ig_followers']:>12,} {c['category']}")

        while True:
            choice = input(f"\n  선택 (0-{len(candidates)-1}, s=skip, q=전체종료): ").strip().lower()
            if choice == "q":
                print("\n  → 전체 취소")
                return
            if choice == "s":
                print(f"  → skip")
                break
            if choice.isdigit() and int(choice) < len(candidates):
                selected = candidates[int(choice)]
                save_page_map(channel, brand, selected["page_id"])
                print(f"  → 저장 완료: {selected['name']} ({selected['page_id']})")
                break
            print("  잘못된 입력입니다.")

    print(f"\n[완료] {PAGE_ID_JSON} 업데이트됨\n")


if __name__ == "__main__":
    main()
