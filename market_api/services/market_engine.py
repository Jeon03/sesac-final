import os, requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import unquote
from market_api.models import MarketStat # Django 환경 가정

def get_stats(cat, hs, countries=["US", "JP"]):
    key = unquote(os.getenv("TRASS_API_KEY"))
    url = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
    
    # 동적 연도: 현재 2026년이면 [2021, 2022, 2023, 2024, 2025]
    cur_year = datetime.now().year
    target_years = [str(y) for y in range(cur_year - 5, cur_year)]
    
    final_data = {c: [] for c in countries}

    for c in countries:
        for y in target_years:
            # 1. DB 먼저 확인 (증분 업데이트의 핵심)
            stat = MarketStat.objects.filter(category=cat, country=c, year=y).first()
            
            if stat:
                final_data[c].append({"year": y, "amount": stat.amount, "weight": stat.weight})
                print(f"📦 {c}-{y}: DB 캐시 데이터 사용")
            else:
                # 2. DB에 없으면 해당 연도만 API 호출
                params = {'serviceKey': key, 'strtYymm': f"{y}01", 'endYymm': f"{y}12", 'hsSgn': hs, 'cntyCd': c}
                try:
                    res = requests.get(url, params=params, timeout=10)
                    if res.status_code == 200:
                        root = ET.fromstring(res.content)
                        for item in root.findall(".//item"):
                            if item.findtext("year") == "총계":
                                amount = int(item.findtext("expDlr") or 0)
                                weight = int(item.findtext("expWgt") or 0)
                                
                                # 수집 즉시 DB 저장 (다음 요청 땐 API 안 부름)
                                MarketStat.objects.create(
                                    category=cat, hs_code=hs, country=c, year=y,
                                    amount=amount, weight=weight
                                )
                                final_data[c].append({"year": y, "amount": amount, "weight": weight})
                                print(f"📡 {c}-{y}: API 신규 수집 완료")
                                break
                except Exception as e:
                    print(f"❌ {c}-{y} 에러: {e}")
    return final_data