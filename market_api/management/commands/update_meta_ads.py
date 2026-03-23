"""
Meta 광고 크롤링 + DB 업데이트 파이프라인

① brand_page_ids_all.json 기반으로 각 채널 Meta 광고 크롤링
② CSV 저장 (meta_crawling_result/)
③ MetaAdSummary DB 업데이트

사용법:
    python manage.py update_meta_ads --channel ulta
    python manage.py update_meta_ads --channel all
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

CRAWLING_DIR = Path(__file__).resolve().parents[3] / "crawling"
if str(CRAWLING_DIR) not in sys.path:
    sys.path.insert(0, str(CRAWLING_DIR))

from market_api.models import MetaAdSummary

PAGE_ID_JSON = CRAWLING_DIR / "brand_page_ids_all.json"
CHANNELS = ["ulta", "sephora", "qoo10", "rakuten"]


def _parse_date(val):
    if not val or str(val).strip() in ("", "nan"):
        return None
    try:
        return datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _load_page_id_map():
    if not PAGE_ID_JSON.exists():
        return {}
    data = json.load(open(PAGE_ID_JSON, encoding="utf-8"))
    result = {}
    for channel, info in data.items():
        for brand, meta in info.get("brands", {}).items():
            result[(channel, brand)] = meta.get("page_id", "")
    return result


def run_channel(channel: str):
    from crawl_meta import crawl

    print(f"\n{'='*50}")
    print(f"[{channel.upper()}] Meta 광고 업데이트 시작")
    print(f"{'='*50}")

    raw_df, df_90d, summary_df = crawl(channel)

    if summary_df.empty:
        print(f"  수집된 광고 없음")
        return

    page_id_map = _load_page_id_map()
    current_brands = set(summary_df["brand"].str.strip())

    # 현재 top10에 없는 브랜드 삭제
    deleted, _ = MetaAdSummary.objects.filter(channel=channel).exclude(brand__in=current_brands).delete()
    if deleted:
        print(f"  삭제: {deleted}개 브랜드 (top10 이탈)")

    saved = 0

    for _, row in summary_df.iterrows():
        brand = str(row["brand"]).strip()

        # 최신 ad_text: 90일 df에서 start_date 내림차순 첫 번째
        latest_text = ""
        if not df_90d.empty:
            brand_df = df_90d[df_90d["brand"] == brand].copy()
            brand_df["dt"] = __import__("pandas").to_datetime(brand_df["start_date"], errors="coerce")
            brand_df = brand_df.sort_values("dt", ascending=False)
            texts = brand_df["ad_text"].dropna()
            texts = texts[texts.str.strip() != ""]
            if len(texts):
                latest_text = texts.iloc[0]

        page_id = page_id_map.get((channel, brand), "")

        MetaAdSummary.objects.update_or_create(
            channel=channel,
            brand=brand,
            defaults={
                "total_ads":      int(row.get("total_ads", 0)),
                "image_ads":      int(row.get("image_ads", 0)),
                "video_ads":      int(row.get("video_ads", 0)),
                "image_ratio":    float(row.get("image_ratio", 0)),
                "video_ratio":    float(row.get("video_ratio", 0)),
                "latest_ad_date": _parse_date(row.get("latest_ad_date")),
                "recent_30d_ads": int(row.get("recent_30d_ads", 0)),
                "latest_ad_text": latest_text,
                "page_id":        page_id,
            },
        )
        saved += 1

    print(f"  DB 저장 완료: {saved}개 브랜드")


class Command(BaseCommand):
    help = "Meta 광고 크롤링 + MetaAdSummary DB 업데이트"

    def add_arguments(self, parser):
        parser.add_argument(
            "--channel",
            required=True,
            choices=CHANNELS + ["all"],
            help="실행할 채널 (all이면 전체 순차 실행)",
        )

    def handle(self, *args, **options):
        channel  = options["channel"]
        channels = CHANNELS if channel == "all" else [channel]

        for ch in channels:
            try:
                run_channel(ch)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{ch}] 오류: {e}"))
                import traceback
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS("\nMeta 광고 업데이트 완료!"))
