"""
Ulta 크롤링 모듈 (자동화 파이프라인용)

crawl(known_review_ids) → (rankings, new_reviews)
  - known_review_ids: DB에 이미 있는 review_id set → 만나면 수집 중단
  - rankings: 최신 top10 랭킹 리스트
  - new_reviews: DB에 없는 새 리뷰만 반환
"""
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

API_KEY          = "daa0f241-c242-4483-afb7-4449942d1a2b"
RANK_SAVE_FILE   = Path(__file__).parent / "ulta_rankings_current.jsonl"
REVIEW_SAVE_FILE = Path(__file__).parent / "ulta_reviews_master.jsonl"

CUTOFF_DATE      = datetime.now() - timedelta(days=365 * 2)
CUTOFF_TIMESTAMP = CUTOFF_DATE.timestamp() * 1000


def _get_reviews(product_id, product_name, known_review_ids: set):
    """단일 상품 리뷰 수집. known_review_ids에 있는 review_id 만나면 중단."""
    reviews = []
    page_size   = 25
    paging_from = 0
    stop = False

    while not stop:
        url = f"https://display.powerreviews.com/m/6406/l/en_US/product/{product_id}/reviews"
        params = {
            "paging.from": paging_from,
            "paging.size": page_size,
            "sort":        "Newest",
            "apikey":      API_KEY,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                break
            data    = resp.json()
            results = data.get("results", [])
            if not results or not results[0].get("reviews"):
                break

            for rev in results[0].get("reviews", []):
                details = rev.get("details", {})
                metrics = rev.get("metrics", {})
                raw_ms  = details.get("created_date")
                rev_id  = str(rev.get("review_id", ""))

                # 2년 이전 → 중단
                if raw_ms and raw_ms < CUTOFF_TIMESTAMP:
                    stop = True
                    break

                # 이미 DB에 있는 리뷰 → 중단 (최신순이므로 이후도 전부 기존)
                if rev_id and rev_id in known_review_ids:
                    stop = True
                    break

                fmt_date = (
                    datetime.fromtimestamp(raw_ms / 1000.0).strftime("%Y-%m-%d %H:%M")
                    if raw_ms else "N/A"
                )
                reviews.append({
                    "product_id": product_id,
                    "review_id":  rev_id,
                    "author":     details.get("nickname"),
                    "rating":     metrics.get("rating"),
                    "headline":   details.get("headline"),
                    "comment":    details.get("comments"),
                    "date":       fmt_date,
                    "created_at": raw_ms,
                })

            if not stop:
                paging_from += page_size
                time.sleep(random.uniform(0.3, 0.5))

        except Exception as e:
            print(f"  [ulta] 리뷰 에러 ({product_name}): {e}")
            break

    return reviews


def crawl(known_review_ids: set = None):
    """
    Ulta top10 크롤링.
    known_review_ids: DB에 이미 있는 review_id set (없으면 전체 수집)
    반환: (rankings, new_reviews)
    """
    if known_review_ids is None:
        known_review_ids = set()

    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options)

    rankings    = []
    new_reviews = []

    try:
        print("[ulta] 접속 중...")
        driver.get("https://www.ulta.com/shop/skin-care/all?sort=best_sellers")
        time.sleep(random.uniform(7, 10))

        soup  = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.select("li.ProductListingResults__productCard")

        rank_count = 1
        for item in items:
            if rank_count > 10:
                break
            if item.select_one(".pal-c-ProductCardFooter__sponsored"):
                continue
            try:
                brand      = item.select_one(".pal-c-ProductCardBody--brandName p").get_text(strip=True)
                title_link = item.select_one("a.pal-c-Link")
                title      = title_link.get_text(strip=True)
                url        = title_link.get("href")
                if not url.startswith("http"):
                    url = "https://www.ulta.com" + url
                pid = url.split("-")[-1].split("?")[0]

                rankings.append({
                    "rank":         rank_count,
                    "brand":        brand,
                    "title":        title,
                    "url":          url,
                    "product_id":   pid,
                    "platform":     "Ulta",
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                print(f"  [ulta] {rank_count}위: {brand} / {title[:30]}")

                reviews = _get_reviews(pid, title, known_review_ids)
                new_reviews.extend(reviews)
                print(f"  [ulta] 신규 리뷰: {len(reviews)}개")
                rank_count += 1

            except Exception as e:
                print(f"  [ulta] 파싱 오류: {e}")

    finally:
        driver.quit()

    # JSONL 저장 (rankings 덮어쓰기, reviews 추가)
    with open(RANK_SAVE_FILE, "w", encoding="utf-8") as f:
        for r in rankings:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(REVIEW_SAVE_FILE, "a", encoding="utf-8") as f:
        for r in new_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[ulta] 완료: 랭킹 {len(rankings)}개 / 신규 리뷰 {len(new_reviews)}개")
    return rankings, new_reviews
