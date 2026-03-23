"""
Meta 광고 summary CSV → DB 로드 command

python manage.py load_meta_ads
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand
from market_api.models import MetaAdSummary, MetaAd

RESULT_DIR = Path(__file__).resolve().parents[3] / "crawling" / "meta_crawling_result"
PAGE_ID_JSON = Path(__file__).resolve().parents[3] / "crawling" / "brand_page_ids_all.json"

CHANNELS = {
    "ulta":    {"summary": "ulta_meta_summary.csv",    "raw": "ulta_meta_90.csv"},
    "sephora": {"summary": "sephora_meta_summary.csv", "raw": "sephora_meta_90.csv"},
    "qoo10":   {"summary": "qoo10_meta_summary.csv",   "raw": "qoo10_meta_90.csv"},
    "rakuten": {"summary": "rakuten_meta_summary.csv", "raw": "rakuten_meta_90.csv"},
}


def _latest_ad_text(raw_path, brand):
    """raw CSV에서 브랜드의 가장 최근 ad_text 반환"""
    try:
        df = pd.read_csv(raw_path)
        df = df[df["brand"] == brand].copy()
        if df.empty:
            return ""
        df["dt"] = pd.to_datetime(df["start_date"], errors="coerce")
        df = df.sort_values("dt", ascending=False)
        texts = df["ad_text"].dropna()
        texts = texts[texts.str.strip() != ""]
        return texts.iloc[0] if len(texts) else ""
    except Exception:
        return ""


def _parse_date(val):
    if not val or str(val).strip() in ("", "nan"):
        return None
    try:
        return datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


class Command(BaseCommand):
    help = "Meta 광고 summary CSV를 DB(MetaAdSummary)에 로드/업데이트"

    def handle(self, *args, **options):
        # page_id 맵 로드
        page_id_map = {}
        if PAGE_ID_JSON.exists():
            data = json.load(open(PAGE_ID_JSON, encoding="utf-8"))
            for channel, info in data.items():
                for brand, meta in info.get("brands", {}).items():
                    page_id_map[(channel, brand)] = meta.get("page_id", "")

        total = 0
        for channel, files in CHANNELS.items():
            summary_path = RESULT_DIR / files["summary"]
            raw_path = RESULT_DIR / files["raw"]

            if not summary_path.exists():
                self.stdout.write(f"[SKIP] {summary_path} 없음")
                continue

            df = pd.read_csv(summary_path)
            for _, row in df.iterrows():
                brand = str(row["brand"]).strip()
                latest_text = _latest_ad_text(raw_path, brand)
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
                total += 1
                self.stdout.write(f"  [{channel}] saved")

        self.stdout.write(self.style.SUCCESS(f"\n[Summary] 완료: {total}개 브랜드 저장"))

        # ── 개별 광고 레코드 로드 (MetaAd) ──
        ad_count = 0
        for channel, files in CHANNELS.items():
            raw_path = RESULT_DIR / files["raw"]
            if not raw_path.exists():
                self.stdout.write(f"[SKIP] {raw_path} 없음")
                continue

            df = pd.read_csv(raw_path)
            for _, row in df.iterrows():
                lib_id = str(row.get("library_id", "")).strip()
                if not lib_id:
                    continue

                brand = str(row.get("brand", "")).strip()
                ad_text = str(row.get("ad_text", "")).strip() if pd.notna(row.get("ad_text")) else ""
                market = str(row.get("market", "")).strip()
                page_id = str(row.get("page_id", "")).strip() if pd.notna(row.get("page_id")) else ""

                MetaAd.objects.update_or_create(
                    channel=channel,
                    library_id=lib_id,
                    defaults={
                        "brand":      brand,
                        "media_type": str(row.get("media_type", "")).strip(),
                        "start_date": _parse_date(row.get("start_date")),
                        "ad_text":    ad_text,
                        "page_id":    page_id,
                        "market":     market,
                    },
                )
                ad_count += 1

            self.stdout.write(f"  [{channel}] 개별 광고 로드 완료")

        self.stdout.write(self.style.SUCCESS(f"[MetaAd] 완료: {ad_count}개 광고 레코드 저장"))
