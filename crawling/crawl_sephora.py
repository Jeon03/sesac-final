"""
Sephora 크롤링 모듈 (자동화 파이프라인용)

crawl(known_review_ids) → (rankings, new_reviews)
"""
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

BV_PASSKEY     = "calXm2DyQVjcCy9agq85vmTJv5ELuuBCF2sdg4BnJzJus"
BV_API_URL     = "https://api.bazaarvoice.com/data/reviews.json"
SEPHORA_API_URL = (
    "https://www.sephora.com/api/v2/catalog/categories/skincare/seo"
    "?targetSearchEngine=NLP"
    "&sortBy=P_BEST_SELLING%3A1%3A%3AP_RATING%3A1%3A%3AP_PROD_NAME%3A0"
    "&currentPage=1&pageSize=60&content=true"
    "&includeRegionsMap=true&pickupRampup=true&sddRampup=true"
    "&includeEDD=true&loc=en-US&ch=rwd&user-segment=external-app"
)
HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":          "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.sephora.com/shop/skincare?sortBy=BEST_SELLING",
    "Origin":          "https://www.sephora.com",
}

RANK_SAVE_FILE   = Path(__file__).parent / "sephora_rankings_current.jsonl"
REVIEW_SAVE_FILE = Path(__file__).parent / "sephora_reviews_master.jsonl"
CUTOFF_DATE      = datetime.now() - timedelta(days=365 * 2)


def _get_reviews(product_id, product_name, known_review_ids: set):
    reviews = []
    limit   = 100
    offset  = 0
    total   = None
    stop    = False

    while not stop:
        params = {
            "Filter":     ["contentlocale:en*", f"ProductId:{product_id}"],
            "Sort":       "SubmissionTime:desc",
            "Limit":      limit,
            "Offset":     offset,
            "Include":    "Products,Comments",
            "Stats":      "Reviews",
            "passkey":    BV_PASSKEY,
            "apiversion": "5.4",
            "Locale":     "en_US",
        }
        try:
            resp = requests.get(BV_API_URL, params=params, timeout=15)
            data = resp.json()

            if total is None:
                total = data.get("TotalResults", 0)

            results = data.get("Results", [])
            if not results:
                break

            for rev in results:
                sub_time_str = rev.get("SubmissionTime")
                rev_id       = str(rev.get("Id", ""))

                if sub_time_str:
                    sub_time = datetime.strptime(sub_time_str[:19], "%Y-%m-%dT%H:%M:%S")
                    if sub_time < CUTOFF_DATE:
                        stop = True
                        break

                # 이미 DB에 있는 리뷰 → 중단
                if rev_id and rev_id in known_review_ids:
                    stop = True
                    break

                reviews.append({
                    "product_id":     product_id,
                    "ReviewId":       rev_id,
                    "Author":         rev.get("UserNickname"),
                    "Rating":         rev.get("Rating"),
                    "Title":          rev.get("Title"),
                    "ReviewText":     rev.get("ReviewText"),
                    "SubmissionTime": sub_time_str,
                    "Date":           sub_time_str[:10] if sub_time_str else "N/A",
                    "IsRecommended":  rev.get("IsRecommended"),
                    "SkinType":       rev.get("ContextDataValues", {}).get("skinType", {}).get("ValueLabel", "N/A"),
                    "AgeRange":       rev.get("ContextDataValues", {}).get("ageRange", {}).get("ValueLabel", "N/A"),
                })

            if not stop:
                offset += limit
                if offset >= (total or 0):
                    break
                time.sleep(random.uniform(0.3, 0.6))

        except Exception as e:
            print(f"  [sephora] 리뷰 에러 ({product_name}): {e}")
            break

    return reviews


def crawl(known_review_ids: set = None):
    if known_review_ids is None:
        known_review_ids = set()

    print("[sephora] API 호출 중...")
    try:
        resp = requests.get(SEPHORA_API_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[sephora] API 오류: {e}")
        return [], []

    products_raw = data.get("products") or data.get("catalog", {}).get("products") or []

    rankings    = []
    new_reviews = []
    rank_count  = 1

    for product in products_raw:
        if rank_count > 10:
            break
        if product.get("isSponsored") or product.get("sponsored") or product.get("adBadge"):
            continue

        brand      = product.get("brandName", "N/A")
        title      = product.get("displayName", "N/A")
        sku        = product.get("currentSku", {})
        price      = sku.get("listPrice") or product.get("listPrice") or "N/A"
        rating     = float(product.get("rating", 0) or 0)
        reviews_cnt = int(product.get("reviews", 0) or 0)
        pid        = product.get("productId", "N/A")
        url_path   = product.get("targetUrl") or product.get("url", "")
        url        = f"https://www.sephora.com{url_path}" if url_path and not url_path.startswith("http") else url_path

        rankings.append({
            "rank":         rank_count,
            "brand":        brand,
            "title":        title,
            "rating":       rating,
            "reviews":      reviews_cnt,
            "price":        price,
            "url":          url,
            "product_id":   pid,
            "platform":     "Sephora",
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        print(f"  [sephora] {rank_count}위: {brand} / {title[:30]}")

        reviews = _get_reviews(pid, title, known_review_ids)
        new_reviews.extend(reviews)
        print(f"  [sephora] 신규 리뷰: {len(reviews)}개")
        rank_count += 1

    with open(RANK_SAVE_FILE, "w", encoding="utf-8") as f:
        for r in rankings:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(REVIEW_SAVE_FILE, "a", encoding="utf-8") as f:
        for r in new_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[sephora] 완료: 랭킹 {len(rankings)}개 / 신규 리뷰 {len(new_reviews)}개")
    return rankings, new_reviews
