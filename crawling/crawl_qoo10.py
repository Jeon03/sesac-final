"""
Qoo10 크롤링 모듈 (자동화 파이프라인용)

crawl(known_review_ids) → (rankings, new_reviews)
  - Qoo10은 리뷰에 고유 ID/날짜가 없어 전체 재수집 후 DB upsert로 중복 처리
  - known_review_ids는 참고용으로 받지만 중단 조건으로 사용 안 함
"""
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

RANK_SAVE_FILE   = Path(__file__).parent / "qoo10_rankings_current.jsonl"
REVIEW_SAVE_FILE = Path(__file__).parent / "qoo10_reviews_master.jsonl"


def _get_reviews(gd_no, product_name):
    reviews  = []
    page     = 1
    base_url = "https://www.qoo10.jp/gmkt.inc/Goods/GoodsReviewAjaxAppend.aspx"
    headers  = {
        "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept":           "text/html, */*",
        "Accept-Language":  "ja,en-US;q=0.9,en;q=0.8,ko;q=0.7",
        "Referer":          f"https://www.qoo10.jp/item/x/{gd_no}",
        "X-Requested-With": "XMLHttpRequest",
    }

    while True:
        params = {
            "gd_no":              gd_no,
            "group_code":         "2",
            "page_no":            page,
            "page_size":          "100",
            "sort_type":          "P",
            "contents_cnt":       "0",
            "___cache_expire___": int(time.time() * 1000),
        }
        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                break
            html = resp.text.strip()
            if not html:
                break

            soup  = BeautifulSoup(html, "html.parser")
            items = soup.find_all("li", recursive=False) or soup.select("li")
            if not items:
                break

            for item in items:
                txt_tag = item.select_one(".review_txt")
                if not txt_tag:
                    continue
                content   = txt_tag.get_text(strip=True)
                score_tag = item.select_one(".score")
                rating    = score_tag.get_text(strip=True) if score_tag else "5"
                user_info = item.select_one(".review_user_info")
                user_meta = user_info.get_text(" | ", strip=True) if user_info else ""
                type_tag  = item.select_one(".review_user_type")
                skin_info = type_tag.get_text(strip=True) if type_tag else ""

                reviews.append({
                    "gd_no":    gd_no,
                    "Page":     page,
                    "Rating":   rating,
                    "Review":   content,
                    "UserInfo": user_meta,
                    "SkinType": skin_info,
                })

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"  [qoo10] 리뷰 에러 ({product_name}): {e}")
            break

    return reviews


def crawl(known_review_ids: set = None):
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--incognito")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    driver = None

    rankings    = []
    new_reviews = []

    try:
        driver = uc.Chrome(options=options)
        print("[qoo10] 접속 중...")
        driver.get("https://www.qoo10.jp/cat/120000012")
        time.sleep(random.uniform(6, 9))
        driver.execute_script("window.scrollTo(0, 2000);")
        time.sleep(2)

        soup  = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.select("ul#search_result_item_list > li")

        rank_count = 1
        for item in items:
            if rank_count > 10:
                break
            try:
                is_pr = item.select_one(".ad_cps, .icon_pr, .item_pr") or "PR" in item.get_text()
                if is_pr:
                    continue

                review_tag  = item.select_one(".review_total_count")
                reviews_raw = review_tag.get_text(strip=True) if review_tag else "0"
                reviews_num = int(re.sub(r"[^0-9]", "", reviews_raw)) if reviews_raw != "0" else 0
                if reviews_num == 0:
                    continue

                goods_code = item.get("goodscode")
                brand_tag  = item.select_one(".txt_brand")
                brand      = brand_tag.get_text(strip=True).replace("公式", "").strip() if brand_tag else "N/A"
                title_tag  = item.select_one("a.tt")
                title      = title_tag.get_text(strip=True) if title_tag else "N/A"
                price_tag  = item.select_one(".prc strong")
                price_str  = price_tag.get_text(strip=True) if price_tag else "0"

                rating_star = item.select_one(".review_rating_star")
                rating = 0.0
                if rating_star and "style" in rating_star.attrs:
                    m = re.search(r"width:\s*(\d+)%", rating_star["style"])
                    if m:
                        rating = round(float(m.group(1)) / 20, 1)

                rankings.append({
                    "rank":         rank_count,
                    "title":        title,
                    "shop_name":    brand,
                    "rating":       rating,
                    "reviews":      reviews_num,
                    "price":        price_str,
                    "url":          f"https://www.qoo10.jp/item/x/{goods_code}",
                    "shop_id":      "",
                    "item_id":      goods_code,
                    "platform":     "Qoo10",
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                print(f"  [qoo10] {rank_count}위: {brand} / {goods_code}")

                if goods_code:
                    reviews = _get_reviews(goods_code, title)
                    new_reviews.extend(reviews)
                    print(f"  [qoo10] 리뷰: {len(reviews)}개")

                rank_count += 1

            except Exception as e:
                print(f"  [qoo10] 파싱 오류: {e}")

    except Exception as e:
        print(f"[qoo10] 치명적 오류: {e}")
    finally:
        if driver:
            driver.quit()

    with open(RANK_SAVE_FILE, "w", encoding="utf-8") as f:
        for r in rankings:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # qoo10은 전체 재수집이므로 덮어쓰기
    with open(REVIEW_SAVE_FILE, "w", encoding="utf-8") as f:
        for r in new_reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[qoo10] 완료: 랭킹 {len(rankings)}개 / 리뷰 {len(new_reviews)}개")
    return rankings, new_reviews
