"""
채널별 전체 업데이트 파이프라인

① top10 크롤링 → rankings_current.jsonl 갱신
② rankings DB 업데이트
③ top10 전체 상품 리뷰 크롤링 (기존 리뷰 만나면 중단)
④ 신규 리뷰 번역 + KeyBERT + GPT 분류
⑤ reviews DB 적재
⑥ 신규 리뷰 있는 상품 ReviewAnalysisCache 재계산

사용법:
    python manage.py update_pipeline --channel ulta
    python manage.py update_pipeline --channel all
"""
import sys
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

# crawling 디렉토리를 sys.path에 추가
CRAWLING_DIR = Path(__file__).resolve().parents[3] / "crawling"
if str(CRAWLING_DIR) not in sys.path:
    sys.path.insert(0, str(CRAWLING_DIR))

from market_api.models import ProductRanking, ProductReview, ReviewAnalysisCache
from market_api.services.review_analysis import compute_review_analysis, reload_kw_map

CHANNEL_PLATFORM = {
    "ulta":    ("Ulta",    "US"),
    "sephora": ("Sephora", "US"),
    "qoo10":   ("Qoo10",   "JP"),
    "rakuten": ("Rakuten", "JP"),
}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_known_review_ids(platform: str) -> set:
    """플랫폼의 기존 review_id 전체 반환"""
    return set(
        ProductReview.objects
        .filter(platform=platform)
        .values_list("review_id", flat=True)
    )


def _get_known_date_map(platform: str) -> dict:
    """Rakuten용: {(shop_id, item_id): latest_review_date}"""
    result = {}
    rows = (
        ProductReview.objects
        .filter(platform=platform)
        .values("platform_item_id", "review_date")
    )
    for row in rows:
        pid   = row["platform_item_id"]          # "{shop_id}_{item_id}"
        rdate = row["review_date"]
        if rdate is None:
            continue
        parts = pid.split("_", 1)
        if len(parts) != 2:
            continue
        key = tuple(parts)
        dt  = datetime.combine(rdate, datetime.min.time())
        if key not in result or dt > result[key]:
            result[key] = dt
    return result


def _save_rankings(rankings: list, platform: str, country: str):
    # 기존 랭킹 전체 삭제 후 최신 top10으로 교체
    deleted, _ = ProductRanking.objects.filter(platform=platform).delete()

    objs = []
    for row in rankings:
        if platform in ("Ulta", "Sephora"):
            pid = str(row.get("product_id", ""))
        elif platform == "Qoo10":
            pid = str(row.get("item_id", ""))
        else:
            pid = f"{row.get('shop_id', '')}_{row.get('item_id', '')}"

        collected_at = timezone.make_aware(
            datetime.strptime(row.get("collected_at", ""), "%Y-%m-%d %H:%M:%S")
        )
        objs.append(ProductRanking(
            platform=platform,
            platform_item_id=pid,
            rank=row.get("rank", 0),
            title=row.get("title", ""),
            brand=row.get("brand") or row.get("shop_name", ""),
            price=str(row.get("price", "")),
            rating=row.get("rating") or None,
            reviews_count=row.get("reviews") or None,
            url=row.get("url", ""),
            country=country,
            collected_at=collected_at,
        ))

    ProductRanking.objects.bulk_create(objs)
    print(f"  Rankings: 기존 {deleted}개 삭제 → 신규 {len(objs)}개 저장")


def _parse_review_id(row: dict, platform: str) -> str:
    if platform == "Ulta":
        return str(row.get("review_id", ""))
    if platform == "Sephora":
        return str(row.get("ReviewId", ""))
    if platform == "Qoo10":
        pid       = str(row.get("gd_no", ""))
        user_info = str(row.get("UserInfo", ""))
        return f"{pid}_{row.get('Page', '')}_{user_info[:30]}"
    # Rakuten
    shop_id  = str(row.get("shop_id", ""))
    item_id  = str(row.get("item_id", ""))
    pid      = f"{shop_id}_{item_id}"
    nickname = str(row.get("Nickname", ""))
    post_date = str(row.get("PostDate", ""))
    return f"{pid}_{nickname}_{post_date}"


def _parse_review_date(row: dict, platform: str):
    raw = None
    if platform == "Ulta":
        raw = row.get("date", "")
    elif platform == "Sephora":
        raw = row.get("Date", "")
    elif platform == "Rakuten":
        raw = row.get("PostDate", "")
    elif platform == "Qoo10":
        user_info = str(row.get("UserInfo", ""))
        raw = user_info.split("|")[1].strip() if "|" in user_info else ""
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:len(fmt)], fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _save_reviews(reviews: list, platform: str, country: str) -> set:
    """신규 리뷰 DB 적재. 새로 저장된 platform_item_id 집합 반환."""
    affected_items = set()
    created = skipped = 0

    for row in reviews:
        if platform in ("Ulta", "Sephora"):
            pid = str(row.get("product_id", ""))
        elif platform == "Qoo10":
            pid = str(row.get("gd_no", ""))
        else:
            pid = f"{row.get('shop_id', '')}_{row.get('item_id', '')}"

        review_id = _parse_review_id(row, platform)

        if platform in ("Ulta", "Sephora"):
            body_orig = str(row.get("comment" if platform == "Ulta" else "ReviewText", "") or "")
            body_en   = body_orig
            body_ko   = str(row.get(
                "comment_ko" if platform == "Ulta" else "ReviewText_ko", "") or "")
            title_orig = str(row.get("headline" if platform == "Ulta" else "Title", "") or "")
            title_ko   = str(row.get("headline_ko", "") or "")
        else:
            body_field = "Review" if platform == "Qoo10" else "Body"
            body_orig  = str(row.get(body_field, "") or "")
            body_en    = str(row.get(body_field + "_en", "") or "")
            body_ko    = str(row.get(body_field + "_ko", "") or "")
            title_orig = title_ko = ""

        _, c = ProductReview.objects.update_or_create(
            platform=platform,
            platform_item_id=pid,
            review_id=review_id,
            defaults=dict(
                author=str(row.get("author") or row.get("Author") or row.get("Nickname") or ""),
                rating=row.get("rating") or row.get("Rating") or None,
                title_original=title_orig,
                title_ko=title_ko,
                body_original=body_orig,
                body_en=body_en,
                body_ko=body_ko,
                review_date=_parse_review_date(row, platform),
                keybert_keywords=row.get("keybert_keywords") or [],
                primary_category=row.get("primary_category") or "",
                categories=row.get("categories") or [],
            ),
        )
        if c:
            created += 1
            affected_items.add(pid)
        else:
            skipped += 1

    print(f"  Reviews: 신규 {created} / 중복 {skipped}")
    return affected_items


def _recompute_analysis(platform: str, country: str, item_ids: set):
    if not item_ids:
        print("  분석 재계산: 변경 없음")
        return
    print(f"  분석 재계산: {len(item_ids)}개 상품...")
    for pid in item_ids:
        reviews = list(
            ProductReview.objects
            .filter(platform=platform, platform_item_id=pid)
            .exclude(primary_category="")
            .values("rating", "primary_category", "categories", "keybert_keywords", "body_ko", "country")
        )
        ranking = (
            ProductRanking.objects
            .filter(platform=platform, platform_item_id=pid)
            .values("rating", "reviews_count", "title", "rank")
            .first()
        )
        result = compute_review_analysis(platform, pid, reviews, ranking)
        if result:
            ReviewAnalysisCache.objects.update_or_create(
                platform=platform,
                platform_item_id=pid,
                defaults={"result": result},
            )
    print(f"  분석 재계산 완료")


# ── 채널 파이프라인 ──────────────────────────────────────────────────────────

def run_channel(channel: str):
    from pipeline_steps import process_new_reviews

    platform, country = CHANNEL_PLATFORM[channel]
    print(f"\n{'='*50}")
    print(f"[{channel.upper()}] 파이프라인 시작")
    print(f"{'='*50}")

    # ① 크롤링
    print("\n[1/5] 크롤링...")
    if channel == "ulta":
        import crawl_ulta as mod
        known_ids = _get_known_review_ids(platform)
        rankings, new_reviews = mod.crawl(known_ids)

    elif channel == "sephora":
        import crawl_sephora as mod
        known_ids = _get_known_review_ids(platform)
        rankings, new_reviews = mod.crawl(known_ids)

    elif channel == "qoo10":
        import crawl_qoo10 as mod
        # qoo10은 전체 재수집 후 DB upsert로 처리
        rankings, new_reviews = mod.crawl()

    elif channel == "rakuten":
        import crawl_rakuten as mod
        known_date_map = _get_known_date_map(platform)
        rankings, new_reviews = mod.crawl(known_date_map)

    # ② rankings DB 저장
    print("\n[2/5] Rankings DB 저장...")
    _save_rankings(rankings, platform, country)

    if not new_reviews:
        print("\n신규 리뷰 없음 - 파이프라인 종료")
        return

    # ③④ 번역 + KeyBERT + GPT 분류
    print(f"\n[3/5] 신규 리뷰 {len(new_reviews)}개 처리 (번역 → KeyBERT → 분류)...")
    classified_reviews = process_new_reviews(new_reviews, channel)

    # ⑤ reviews DB 저장
    print("\n[4/5] Reviews DB 저장...")
    affected_items = _save_reviews(classified_reviews, platform, country)

    # ⑥ 분석 재계산
    print("\n[5/5] ReviewAnalysisCache 재계산...")
    reload_kw_map()  # 신규 키워드 번역 반영
    _recompute_analysis(platform, country, affected_items)

    print(f"\n[{channel.upper()}] 완료!")


# ── Management Command ────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "채널별 전체 업데이트 파이프라인 실행"

    def add_arguments(self, parser):
        parser.add_argument(
            "--channel",
            required=True,
            choices=["ulta", "sephora", "qoo10", "rakuten", "all"],
            help="실행할 채널 (all이면 전체 순차 실행)",
        )

    def handle(self, *args, **options):
        channel = options["channel"]
        channels = ["ulta", "sephora", "qoo10", "rakuten"] if channel == "all" else [channel]

        for ch in channels:
            try:
                run_channel(ch)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{ch}] 오류: {e}"))
                import traceback
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS("\n파이프라인 완료!"))
