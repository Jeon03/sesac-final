from django.db import models

class MarketStat(models.Model):
    category = models.CharField(max_length=100)
    hs_code = models.CharField(max_length=10)
    country = models.CharField(max_length=2)  # US, JP
    year = models.CharField(max_length=4)     # 2021, 2022...
    amount = models.BigIntegerField()         # 수출액(USD)
    weight = models.BigIntegerField()         # 수출중량(kg)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 같은 품목, 국가, 연도의 중복 저장을 방지합니다.
        unique_together = ('category', 'country', 'year')