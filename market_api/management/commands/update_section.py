"""
Tavily + LangGraph 기반 섹션별 시장 데이터 업데이트 커맨드.

사용법:
    python manage.py update_section market_size --country US
    python manage.py update_section trends --country JP
    python manage.py update_section competitors                # US+JP 둘 다
    python manage.py update_section kbeauty_share --country US --category 스킨케어
"""
from django.core.management.base import BaseCommand

VALID_SECTIONS = ["market_size", "kbeauty_share", "trends", "channels", "competitors"]


class Command(BaseCommand):
    help = "Tavily 검색 → GPT 구조화 → 개발자 승인 → DB 업데이트 (섹션 단위)"

    def add_arguments(self, parser):
        parser.add_argument(
            "section",
            type=str,
            choices=VALID_SECTIONS,
            help="업데이트할 섹션 (market_size / kbeauty_share / trends / channels / competitors)",
        )
        parser.add_argument("--country", type=str, help="특정 국가만 (US / JP). 미지정 시 둘 다")
        parser.add_argument("--category", type=str, default="스킨케어", help="카테고리 (기본: 스킨케어)")
        parser.add_argument("--month", type=str, help="조사 월 (예: 2026-03). 기본: 현재 월")

    def handle(self, *args, **options):
        from market_api.services.update_graph import run_update

        section = options["section"]
        country_filter = options.get("country")
        category = options["category"]
        month = options.get("month")

        countries = [country_filter] if country_filter else ["US", "JP"]

        for country in countries:
            try:
                run_update(
                    section=section,
                    country=country,
                    category=category,
                    month=month,
                )
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n중단됨"))
                return
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"\n[ERR] {section}-{country}: {e}"))

        self.stdout.write(self.style.SUCCESS("\n완료"))
