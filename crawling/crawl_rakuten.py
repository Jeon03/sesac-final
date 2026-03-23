"""
Rakuten 크롤링 모듈 (자동화 파이프라인용)

crawl(known_date_map) → (rankings, new_reviews)
  - known_date_map: {(shop_id, item_id): latest_date} — 이 날짜 이전 리뷰는 수집 안 함
  - Rakuten은 review_id 없음 → 최신 수집일 기반으로 중단
"""
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

TARGET_URL     = "https://ranking.rakuten.co.jp/weekly/100944/p=1/"
RANK_SAVE_FILE = Path(__file__).parent / "rakuten_rankings_current.jsonl"
REVIEW_SAVE_FILE = Path(__file__).parent / "rakuten_reviews_master.jsonl"

CUTOFF_DATE = datetime.now() - timedelta(days=365 * 2)

RAW_COOKIE = r"_ra=1773145336745|9810936d-5cda-4630-8e49-c98379684815; Rp=dc4c4487b0d3c4dce21f7d6bdbf70329f03486c8; rcxGlobal=d45a9a4c-4afa-4759-a9ed-229577264fb8"
SAFE_COOKIE = RAW_COOKIE.encode("utf-8").decode("latin-1", "ignore")

REVIEW_API_URL = "https://web-gateway.rakuten.co.jp/review/itemshopreviewlist/get/v1"
REVIEW_HEADERS = {
    "authkey":      "isrlPcMjUuXCVBUTVh91ZcHEfoI45CmPR",
    "content-type": "application/json; charset=UTF-8",
    "accept":       "application/json, text/plain, */*",
    "user-agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "cookie":       SAFE_COOKIE,
    "referer":      "https://review.rakuten.co.jp/",
}
MAX_PAGES = 100


def _parse_date(raw):
    if not raw:
        return None
    date_str = raw.split(" ")[0]
    try:
        return datetime.strptime(date_str, "%Y/%m/%d") if "/" in date_str else datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def _get_reviews_by_rating(shop_id, item_id, rating_filter, cutoff: datetime):
    reviews  = []
    page     = 1
    has_next = True
    stop     = False

    while has_next and page <= MAX_PAGES and not stop:
        payload = {
            "common": {"params": {"device": "pc"}, "include": ["itemReviewList"]},
            "features": {
                "itemReviewList": {
                    "params": {
                        "shopId":              int(shop_id),
                        "itemId":              int(item_id),
                        "sort":                "6",
                        "page":                str(page),
                        "hits":                30,
                        "filter":              {"rating": rating_filter},
                        "includePickupReview": True,
                    }
                }
            },
        }
        try:
            resp = requests.post(REVIEW_API_URL, headers=REVIEW_HEADERS, json=payload, timeout=15)
            if resp.status_code not in [200, 207]:
                break
            data     = resp.json()
            res_data = data.get("body", {}).get("itemReviewList", {}).get("data", {})
            revs     = res_data.get("reviews", [])
            if not revs:
                break

            for rev in revs:
                post_date = _parse_date(rev.get("postDate"))
                if post_date:
                    if post_date < CUTOFF_DATE:
                        stop = True
                        break
                    # DB에 이미 있는 날짜까지 도달 → 중단
                    if post_date <= cutoff:
                        stop = True
                        break

                reviews.append({
                    "shop_id":       shop_id,
                    "item_id":       item_id,
                    "rating_filter": rating_filter or "all",
                    "Nickname":      rev.get("nickname"),
                    "Rating":        rev.get("rating"),
                    "Body":          rev.get("body"),
                    "PostDate":      rev.get("postDate"),
                    "Age":           f"{rev.get('ageRange', '')}{rev.get('ageSuffix', '')}",
                    "Sex":           rev.get("sex"),
                    "Sku":           rev.get("skuInfo"),
                })

            if not stop:
                has_next = res_data.get("hasNextPage", False)
                page += 1
                time.sleep(1.8)

        except Exception as e:
            print(f"  [rakuten] 리뷰 에러: {e}")
            break

    return reviews


def _get_all_reviews(shop_id, item_id, product_name, cutoff: datetime):
    all_reviews = []
    print(f"  [rakuten] 리뷰 수집: {product_name[:30]}")
    for star in ["1", "2", "3", "4", "5"]:
        revs = _get_reviews_by_rating(shop_id, item_id, star, cutoff)
        all_reviews.extend(revs)
        time.sleep(1.0)
    return all_reviews


def crawl(known_date_map: dict = None):
    """
    known_date_map: {(shop_id, item_id): datetime} — 해당 날짜 이전 리뷰는 스킵
    """
    if known_date_map is None:
        known_date_map = {}

    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options)

    rankings    = []
    new_reviews = []

    try:
        print("[rakuten] 접속 중...")
        driver.get(TARGET_URL)
        time.sleep(random.uniform(7, 10))

        soup      = BeautifulSoup(driver.page_source, "html.parser")
        all_items = soup.select("div.rnkRanking_top3box, div.rnkRanking_after4box")
        rank_count = 1

        for item in all_items:
            if rank_count > 10:
                break
            try:
                review_link = item.select_one("a[href*='review.rakuten.co.jp/item']")
                shop_id = item_id = ""
                if review_link:
                    href   = review_link.get("href", "")
                    parts  = href.rstrip("/").split("/")
                    id_part = next((p for p in reversed(parts) if "_" in p), "")
                    if id_part:
                        shop_id, item_id = id_part.split("_", 1)

                if not shop_id or not item_id:
                    continue

                title_tag  = item.select_one(".rnkRanking_itemName a")
                title      = title_tag.get_text(strip=True) if title_tag else "N/A"
                shop_name  = item.select_one(".rnkRanking_shop a").get_text(strip=True) if item.select_one(".rnkRanking_shop a") else "N/A"
                price      = item.select_one(".rnkRanking_price").get_text(strip=True) if item.select_one(".rnkRanking_price") else "N/A"

                rankings.append({
                    "rank":         rank_count,
                    "title":        title,
                    "shop_name":    shop_name,
                    "price":        price,
                    "url":          title_tag.get("href") if title_tag else "",
                    "shop_id":      shop_id,
                    "item_id":      item_id,
                    "platform":     "Rakuten",
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                print(f"  [rakuten] {rank_count}위: {shop_name[:25]}")

                # 이 상품의 마지막 수집 날짜 (DB에 있는 가장 최신)
                cutoff = known_date_map.get((shop_id, item_id), datetime.min)
                reviews = _get_all_reviews(shop_id, item_id, title, cutoff)
                new_reviews.extend(reviews)
                print(f"  [rakuten] 신규 리뷰: {len(reviews)}개")
                rank_count += 1

            except Exception as e:
                print(f"  [rakuten] 파싱 오류: {e}")
                rank_count += 1

    finally:
        driver.quit()

    with open(RANK_SAVE_FILE, "w", encoding="utf-8") as f:
        for r in rankings:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(REVIEW_SAVE_FILE, "a", encoding="utf-8") as f:
        for r in new_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[rakuten] 완료: 랭킹 {len(rankings)}개 / 신규 리뷰 {len(new_reviews)}개")
    return rankings, new_reviews
