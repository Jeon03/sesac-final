"""
크롤링 데이터를 LLM으로 구조화하여 MarketResearch DB에 저장하는 커맨드.

사용법:
    python manage.py ingest_research                    # 크롤링 파일만 처리
    python manage.py ingest_research --deep-research    # 크롤링 + Tavily 딥리서치 병행
    python manage.py ingest_research --deep-research --force   # 기존 DB 덮어쓰기
    python manage.py ingest_research --country JP       # 일본만
    python manage.py ingest_research --country US       # 미국만
    python manage.py ingest_research --category 기초화장품  # 특정 카테고리만

딥리서치 우선순위:
    크롤링 원문 → Tavily 웹 검색 → LLM 파라메트릭 지식 추정
"""
import os
from django.core.management.base import BaseCommand
from market_api.services.research_engine import process_and_save

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

# 크롤링 파일 매핑: 팀원이 수집한 파일들
DATA_SOURCES = [
    {
        "file": os.path.join(BASE_DIR, "code", "KOTRA_Proper_Table_Project", "reports", "article_1_summary.txt"),
        "country": "JP",
        "category": "기초화장품",
        "source": "https://dream.kotra.or.kr/kotranews/",
    },
    {
        "file": os.path.join(BASE_DIR, "code", "Spherical_Insights_Final", "refined_kbeauty_report.txt"),
        "country": "JP",
        "category": "기초화장품",
        "source": "https://www.sphericalinsights.com/ko/reports/japan-k-beauty-product-market",
    },
    {
        "file": os.path.join(BASE_DIR, "code", "retailtalk", "article_inside_full.txt"),
        "country": "JP",
        "category": "기초화장품",
        "source": "https://retailtalk.co.kr/Trend/?bmode=view&idx=165200000",
    },
    {
        "file": os.path.join(BASE_DIR, "code", "us_market", "us_kbeauty_combined.txt"),
        "country": "US",
        "category": "기초화장품",
        "source": "KOTRA, Grand View Research, Euromonitor, Fortune Business Insights",
    },
]

# 딥리서치 대상 (크롤링 파일 없는 카테고리/국가 조합 포함)
DEEP_RESEARCH_TARGETS = [
    {"category": "기초화장품", "country": "US"},
    {"category": "기초화장품", "country": "JP"},
    {"category": "마스크팩",   "country": "US"},
    {"category": "마스크팩",   "country": "JP"},
    # {"category": "메이크업",   "country": "US"},
    # {"category": "메이크업",   "country": "JP"},
    # {"category": "입술화장품", "country": "US"},
    # {"category": "입술화장품", "country": "JP"},
    # {"category": "눈화장품",   "country": "US"},
    # {"category": "눈화장품",   "country": "JP"},
    # {"category": "샴푸",       "country": "US"},
    # {"category": "샴푸",       "country": "JP"},
    # {"category": "헤어케어",   "country": "US"},
    # {"category": "헤어케어",   "country": "JP"},
    # {"category": "매니큐어",   "country": "US"},
    # {"category": "매니큐어",   "country": "JP"},
]


def _load_crawled_text(category: str, country: str) -> tuple[str, list[str]]:
    """해당 카테고리/국가의 크롤링 원문을 모두 합쳐서 반환"""
    texts = []
    sources = []
    for src in DATA_SOURCES:
        if src["category"] != category or src["country"] != country:
            continue
        if not os.path.exists(src["file"]):
            continue
        with open(src["file"], "r", encoding="utf-8") as f:
            text = f.read().strip()
        if text:
            texts.append(text)
            sources.append(src["source"])
    return "\n\n---\n\n".join(texts), sources


class Command(BaseCommand):
    help = "크롤링/딥리서치 데이터를 LLM으로 구조화하여 MarketResearch DB에 저장합니다."

    def add_arguments(self, parser):
        parser.add_argument('--country', type=str, help='특정 국가만 처리 (JP, US)')
        parser.add_argument('--category', type=str, help='특정 카테고리만 처리')
        parser.add_argument('--month', type=str, help='조사 월 지정 (예: 2026-03)')
        parser.add_argument(
            '--deep-research', action='store_true',
            help='Tavily 딥리서치 병행 실행 (TAVILY_API_KEY 필요)'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='기존 DB 데이터 덮어쓰기'
        )

    def handle(self, *args, **options):
        country_filter = options.get('country')
        category_filter = options.get('category')
        month = options.get('month')
        use_deep_research = options.get('deep_research', False)
        force = options.get('force', False)

        if use_deep_research:
            self.stdout.write(self.style.WARNING("🌐 딥리서치 모드 활성화 (Tavily + LLM)"))
            self._run_deep_research_all(country_filter, category_filter, month, force)
        else:
            self.stdout.write("📄 크롤링 파일 인제스트 모드")
            self._run_crawl_ingest(country_filter, category_filter, month)

        self.stdout.write(self.style.SUCCESS("\n🏁 인제스트 완료"))

    def _run_crawl_ingest(self, country_filter, category_filter, month):
        """기존 크롤링 파일 처리"""
        for source in DATA_SOURCES:
            if country_filter and source["country"] != country_filter:
                continue
            if category_filter and source["category"] != category_filter:
                continue

            filepath = source["file"]
            if not os.path.exists(filepath):
                self.stderr.write(f"⚠️  파일 없음: {filepath}")
                continue

            self.stdout.write(f"\n📄 처리 중: {os.path.basename(filepath)}")
            self.stdout.write(f"   국가: {source['country']}, 카테고리: {source['category']}")

            with open(filepath, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            if not raw_text.strip():
                self.stderr.write(f"⚠️  빈 파일: {filepath}")
                continue

            try:
                process_and_save(
                    category=source["category"],
                    country=source["country"],
                    raw_text=raw_text,
                    sources=[source["source"]],
                    research_month=month,
                )
                self.stdout.write(self.style.SUCCESS("   ✅ 완료"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"   ❌ 에러: {e}"))

        self._merge_sources()

    def _run_deep_research_all(self, country_filter, category_filter, month, force):
        """딥리서치 모드: 크롤링 원문 요약 → Tavily 웹검색 병합 → LLM 구조화"""
        from market_api.services.deep_research_engine import run_deep_research
        from market_api.services.research_engine import summarize_crawled_text

        targets = [
            t for t in DEEP_RESEARCH_TARGETS
            if (not country_filter or t["country"] == country_filter)
            and (not category_filter or t["category"] == category_filter)
        ]

        self.stdout.write(f"   대상: {len(targets)}개 카테고리-국가 조합\n")

        for target in targets:
            category = target["category"]
            country = target["country"]

            self.stdout.write(f"\n🔍 [{category} - {country}]")

            # 1단계: 크롤링 원문 로드
            crawled_text, _ = _load_crawled_text(category, country)

            # 2단계: LLM으로 핵심 정보 요약 (토큰 초과 방지)
            summarized_text = ""
            if crawled_text:
                self.stdout.write(f"   + 크롤링 원문 {len(crawled_text)}자 → LLM 요약 중...")
                try:
                    summarized_text = summarize_crawled_text(category, country, crawled_text)
                    self.stdout.write(f"   + 요약 완료: {len(summarized_text)}자")
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"   ⚠️ 요약 실패, 원문 사용: {e}"))
                    summarized_text = crawled_text[:5000]

            # 3단계: 요약본 + Tavily 웹검색 → LLM 구조화 → DB 저장
            try:
                run_deep_research(
                    category=category,
                    country=country,
                    extra_crawled_text=summarized_text,
                    research_month=month,
                    force=force,
                )
                self.stdout.write(self.style.SUCCESS(f"   ✅ 완료"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"   ❌ 에러: {e}"))

    def _merge_sources(self):
        """같은 카테고리-국가-월의 여러 소스를 병합"""
        from market_api.models import MarketResearch
        from django.db.models import Count

        dupes = (
            MarketResearch.objects
            .values('category', 'country', 'research_month')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )

        for group in dupes:
            entries = MarketResearch.objects.filter(
                category=group['category'],
                country=group['country'],
                research_month=group['research_month'],
            ).order_by('-updated_at')

            base = entries.first()
            all_sources = []

            for entry in entries:
                all_sources.extend(entry.sources or [])
                if entry.id == base.id:
                    continue

                for field in ['market_size', 'kbeauty_share', 'trends', 'channels', 'competitors']:
                    base_val = getattr(base, field) or {}
                    other_val = getattr(entry, field) or {}
                    if isinstance(base_val, dict) and isinstance(other_val, dict):
                        for k, v in other_val.items():
                            if k not in base_val or not base_val[k]:
                                base_val[k] = v
                        setattr(base, field, base_val)

                if not base.raw_summary and entry.raw_summary:
                    base.raw_summary = entry.raw_summary

                entry.delete()

            base.sources = list(set(all_sources))
            base.save()
            self.stdout.write(f"🔗 병합 완료: {group['category']}-{group['country']}")
