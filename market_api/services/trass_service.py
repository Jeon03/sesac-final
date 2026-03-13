import requests, os
import xml.etree.ElementTree as ET
from urllib.parse import unquote

def fetch_api(hs_code, country, year):
    key = unquote(os.getenv("TRASS_API_KEY"))
    url = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
    params = {'serviceKey': key, 'strtYymm': f"{year}01", 'endYymm': f"{year}12", 'hsSgn': hs_code, 'cntyCd': country}
    
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item"):
                if item.findtext("year") == "총계":
                    return {
                        "amount": int(item.findtext("expDlr") or 0),
                        "weight": int(item.findtext("expWgt") or 0)
                    }
    except Exception as e:
        print(f"❌ API 호출 에러 ({year}): {e}")
    return None