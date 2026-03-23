"""
JSONL 파일 → DB 로드 command

python manage.py load_review_data
"""
import json
from datetime import datetime, date
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from market_api.models import ProductRanking, ProductReview, ReviewAnalysisCache
from market_api.services.review_analysis import compute_review_analysis

CRAWLING_DIR = Path(__file__).resolve().parents[3] / "crawling"


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _parse_date(val):
    """다양한 날짜 문자열 → date 또는 None"""
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(val[:len(fmt)], fmt).date()
        except (ValueError, TypeError):
            continue
    try:
        return parse_datetime(val).date()
    except Exception:
        return None


def _parse_collected_at(val):
    """'2026-03-20 19:16:19' → timezone-aware datetime"""
    try:
        return timezone.make_aware(datetime.strptime(val, "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return timezone.now()


def _load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ── Rankings 로드 ─────────────────────────────────────────────────────────────

def load_rankings():
    files = [
        ("ulta_rankings_current.jsonl",    "Ulta",    "US"),
        ("sephora_rankings_current.jsonl", "Sephora", "US"),
        ("qoo10_rankings_current.jsonl",   "Qoo10",   "JP"),
        ("rakuten_rankings_current.jsonl", "Rakuten", "JP"),
    ]
    created_total = updated_total = 0

    for fname, platform, country in files:
        path = CRAWLING_DIR / fname
        if not path.exists():
            print(f"  [skip] {fname} 없음")
            continue

        rows = _load_jsonl(path)
        for row in rows:
            # platform_item_id 결정
            if platform in ("Ulta", "Sephora"):
                pid = row.get("product_id", "")
            elif platform == "Qoo10":
                pid = str(row.get("item_id", ""))
            else:  # Rakuten
                pid = f"{row.get('shop_id', '')}_{row.get('item_id', '')}"

            collected_at = _parse_collected_at(row.get("collected_at", ""))

            defaults = dict(
                rank=row.get("rank", 0),
                title=row.get("title", ""),
                brand=row.get("brand", "") or row.get("shop_name", ""),
                price=row.get("price", "") or "",
                rating=row.get("rating") or None,
                reviews_count=row.get("reviews") or None,
                url=row.get("url", ""),
            )

            obj, created = ProductRanking.objects.update_or_create(
                platform=platform,
                platform_item_id=pid,
                collected_at=collected_at,
                defaults=defaults,
            )
            # country는 update_or_create 키가 아니므로 별도 세팅
            if obj.country != country:
                obj.country = country
                obj.save(update_fields=["country"])

            if created:
                created_total += 1
            else:
                updated_total += 1

        print(f"  {platform}: {len(rows)}건 처리")

    print(f"  Rankings 완료 → 신규 {created_total}, 갱신 {updated_total}")


# ── Reviews 로드 ─────────────────────────────────────────────────────────────

def load_reviews():
    configs = [
        # (파일명, platform, country, 파서함수)
        ("ulta_final_categorized.jsonl",    "Ulta",    "US", _parse_ulta),
        ("sephora_final_categorized.jsonl", "Sephora", "US", _parse_sephora),
        ("qoo10_final_categorized.jsonl",   "Qoo10",   "JP", _parse_qoo10),
        ("rakuten_final_categorized.jsonl", "Rakuten", "JP", _parse_rakuten),
    ]
    created_total = updated_total = 0

    for fname, platform, country, parser in configs:
        path = CRAWLING_DIR / fname
        if not path.exists():
            print(f"  [skip] {fname} 없음")
            continue

        rows = _load_jsonl(path)
        for row in rows:
            pid, review_id, author, rating, title_original, title_ko, body_original, body_en, body_ko, review_date = parser(row)

            obj, created = ProductReview.objects.update_or_create(
                platform=platform,
                platform_item_id=pid,
                review_id=review_id,
                defaults=dict(
                    country=country,
                    author=author,
                    rating=rating,
                    title_original=title_original,
                    title_ko=title_ko,
                    body_original=body_original,
                    body_en=body_en,
                    body_ko=body_ko,
                    review_date=review_date,
                    keybert_keywords=row.get("keybert_keywords") or [],
                    primary_category=row.get("primary_category") or "",
                    categories=row.get("categories") or [],
                ),
            )
            if created:
                created_total += 1
            else:
                updated_total += 1

        print(f"  {platform}: {len(rows)}건 처리")

    print(f"  Reviews 완료 → 신규 {created_total}, 갱신 {updated_total}")


def _s(val):
    """None-safe string"""
    return val if isinstance(val, str) else (str(val) if val is not None else "")


def _parse_ulta(row):
    # 반환: pid, review_id, author, rating, title_original, title_ko, body_original, body_en, body_ko, review_date
    pid = _s(row.get("product_id"))
    review_id = _s(row.get("review_id"))
    author = _s(row.get("author"))
    rating = row.get("rating")
    title_original = _s(row.get("headline"))       # 영어 원문
    title_ko = _s(row.get("headline_ko"))
    body_original = _s(row.get("comment"))          # 영어 원문
    body_en = body_original                         # 원문이 영어
    body_ko = _s(row.get("comment_ko"))
    review_date = _parse_date(row.get("date", ""))
    return pid, review_id, author, rating, title_original, title_ko, body_original, body_en, body_ko, review_date


def _parse_sephora(row):
    pid = _s(row.get("product_id"))
    review_id = _s(row.get("ReviewId"))
    author = _s(row.get("Author"))
    rating = row.get("Rating")
    title_original = _s(row.get("Title"))           # 영어 원문
    title_ko = ""                                   # 세포라는 제목 번역 없음
    body_original = _s(row.get("ReviewText"))       # 영어 원문
    body_en = body_original
    body_ko = _s(row.get("ReviewText_ko"))
    review_date = _parse_date(row.get("Date", ""))
    return pid, review_id, author, rating, title_original, title_ko, body_original, body_en, body_ko, review_date


def _parse_qoo10(row):
    pid = _s(row.get("gd_no"))
    user_info = _s(row.get("UserInfo"))
    review_id = f"{pid}_{row.get('Page', '')}_{user_info[:30]}"
    author = user_info.split("|")[0].strip() if user_info else ""
    rating = row.get("Rating")
    try:
        rating = float(rating)
    except (TypeError, ValueError):
        rating = None
    body_original = _s(row.get("Review"))           # 일본어 원문
    body_en = _s(row.get("Review_en"))              # 영어 번역 (final_categorized에 포함)
    body_ko = _s(row.get("Review_ko"))
    date_str = user_info.split("|")[1].strip() if "|" in user_info else ""
    review_date = _parse_date(date_str.replace(".", "-"))
    return pid, review_id, author, rating, "", "", body_original, body_en, body_ko, review_date


def _parse_rakuten(row):
    shop_id = _s(row.get("shop_id"))
    item_id = _s(row.get("item_id"))
    pid = f"{shop_id}_{item_id}"
    nickname = _s(row.get("Nickname"))
    post_date = _s(row.get("PostDate"))
    review_id = f"{pid}_{nickname}_{post_date}"
    author = nickname
    rating = row.get("Rating")
    try:
        rating = float(rating)
    except (TypeError, ValueError):
        rating = None
    body_original = _s(row.get("Body"))             # 일본어 원문
    body_en = _s(row.get("Body_en"))                # 영어 번역
    body_ko = _s(row.get("Body_ko"))                # 한국어 번역
    review_date = _parse_date(post_date)
    return pid, review_id, author, rating, "", "", body_original, body_en, body_ko, review_date


# ── 분석 캐시 저장 ────────────────────────────────────────────────────────────

def build_analysis_cache(platform_filter=None, item_id_filter=None):
    """플랫폼별 전체 상품 리뷰 분석 결과를 계산하여 ReviewAnalysisCache에 저장"""
    platforms = [
        ("Ulta",    "US"),
        ("Sephora", "US"),
        ("Qoo10",   "JP"),
        ("Rakuten", "JP"),
    ]
    if platform_filter:
        platforms = [(p, c) for p, c in platforms if p.lower() == platform_filter.lower()]
        if not platforms:
            print(f"  [오류] 알 수 없는 플랫폼: {platform_filter}  (Ulta / Sephora / Qoo10 / Rakuten)")
            return
    total_saved = 0

    for platform, country in platforms:
        # 해당 플랫폼의 랭킹에 있는 상품 목록
        qs = ProductRanking.objects.filter(platform=platform, country=country)
        if item_id_filter:
            qs = qs.filter(platform_item_id=item_id_filter)
        item_ids = list(qs.values_list("platform_item_id", flat=True).distinct())
        print(f"  {platform}: {len(item_ids)}개 상품 분석 시작")

        for item_id in item_ids:
            reviews = list(
                ProductReview.objects
                .filter(platform=platform, platform_item_id=item_id)
                .exclude(primary_category="")
                .values("rating", "primary_category", "categories",
                        "keybert_keywords", "body_ko", "country")
            )
            ranking = (
                ProductRanking.objects
                .filter(platform=platform, platform_item_id=item_id)
                .values("rating", "reviews_count", "title", "rank")
                .first()
            )

            result = compute_review_analysis(platform, item_id, reviews, ranking)
            if not result:
                continue

            ReviewAnalysisCache.objects.update_or_create(
                platform=platform,
                platform_item_id=item_id,
                defaults={"result": result},
            )
            total_saved += 1

        print(f"  {platform}: 완료")

    print(f"  분석 캐시 완료 → 총 {total_saved}개 저장")


# ── Command ──────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "JSONL 파일(rankings + reviews)을 DB에 로드합니다."

    def add_arguments(self, parser):
        parser.add_argument("--only", choices=["rankings", "reviews", "cache"], help="한 쪽만 실행")
        parser.add_argument("--platform", help="캐시 빌드 대상 플랫폼 (Ulta / Sephora / Qoo10 / Rakuten)")
        parser.add_argument("--item_id", help="캐시 빌드 대상 상품 ID")

    def handle(self, *args, **options):
        only = options.get("only")
        platform_filter = options.get("platform")
        item_id_filter = options.get("item_id")

        if only != "reviews" and only != "cache":
            self.stdout.write("=== Rankings 로드 ===")
            load_rankings()

        if only != "rankings" and only != "cache":
            self.stdout.write("=== Reviews 로드 ===")
            load_reviews()

        if only != "rankings" and only != "reviews":
            self.stdout.write("=== 분석 캐시 저장 ===")
            build_analysis_cache(platform_filter, item_id_filter)

        self.stdout.write(self.style.SUCCESS("완료!"))
