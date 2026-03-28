import base64
import io
import os

from google import genai
from google.genai import types
from PIL import Image


def generate_ad_images(
    image_file,
    product_name: str = "",
    category: str = "",
    ingredients: str = "",
    effects: str = "",
    brand_concept: str = "",
    headline1: str = "",
    body_text1: str = "",
    headline2: str = "",
    body_text2: str = "",
    key_messages: list = None,
    country: str = "US",
) -> dict:
    """
    제품 이미지 + 광고 전략 데이터 → Gemini로 인스타그램 광고 이미지 2장 생성
    Returns: {"images": [{"data": base64, "mime_type": "image/png"}, ...]}
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY가 설정되지 않았습니다."}

    client = genai.Client(api_key=api_key)

    try:
        pil_image = Image.open(image_file)
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        image_bytes = buf.getvalue()
    except Exception as e:
        return {"error": f"이미지 로드 실패: {e}"}

    product_ctx = f"{product_name} ({category})" if product_name else category or "스킨케어 제품"
    key_msg_str = ", ".join(key_messages) if key_messages else ""
    lang_label = "일본어" if country == "JP" else "영어"

    prompts = [
        # ── 1번: 브랜드 컨셉 기반 인스타그램 피드 광고 ──────────────────────────
        (
            f"다음 K-뷰티 제품의 인스타그램 피드 광고 이미지를 만들어주세요: {product_ctx}. "
            f"{'브랜드 컨셉: ' + brand_concept + '. ' if brand_concept else ''}"
            f"{'광고 헤드라인: ' + headline1 + '. ' if headline1 else ''}"
            f"{'광고 메시지: ' + body_text1 + '. ' if body_text1 else ''}"
            f"{'핵심 소구점: ' + key_msg_str + '. ' if key_msg_str else ''}"
            f"{'주요 성분: ' + ingredients + '. ' if ingredients else ''}"
            f"{'제품 효능: ' + effects + '. ' if effects else ''}"
            f"이미지에 텍스트가 포함될 경우 반드시 {lang_label}로 작성하세요. "
            "스타일: 깔끔하고 밝은 인스타그램 정사각형(1:1) 피드 광고 형식. "
            "제품 패키지 색상에 맞는 파스텔 또는 화이트 배경. "
            "제품을 중앙에 배치하고 우아한 그림자와 하이라이트 처리. "
            "여백을 충분히 활용한 미니멀 레이아웃 — 인스타그램 스폰서 광고 느낌. "
            "고급 뷰티 브랜드의 상업 사진 스타일, 자연광, 4K 해상도."
        ),
        # ── 2번: 광고 카피 기반 라이프스타일 인스타그램 스토리/릴스 썸네일 ────
        (
            f"다음 K-뷰티 제품의 인스타그램 스토리 광고 이미지를 만들어주세요: {product_ctx}. "
            f"{'캠페인 컨셉: ' + brand_concept + '. ' if brand_concept else ''}"
            f"{'광고 헤드라인: ' + headline2 + '. ' if headline2 else ''}"
            f"{'광고 카피: ' + body_text2 + '. ' if body_text2 else ''}"
            f"{'주요 성분: ' + ingredients + '. ' if ingredients else ''}"
            f"{'제품 효능: ' + effects + '. ' if effects else ''}"
            f"이미지에 텍스트가 포함될 경우 반드시 {lang_label}로 작성하세요. "
            "스타일: 모던 K-뷰티 에디토리얼 감성. "
            "9:16 세로 구도, 제품이 주인공. "
            "부드러운 그라데이션 배경 또는 미니멀 플랫레이 구성 — 인스타그램 스토리/릴스 썸네일에 최적화. "
            "프리미엄하면서도 친근한 K-뷰티 브랜드 색감. "
            "전문 뷰티 사진 스타일, 시네마틱 소프트 조명, 고해상도."
        ),
    ]

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

    def _generate(prompt: str) -> dict:
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-image-preview",
                contents=[prompt, image_part],
            )
            for part in response.parts:
                if part.inline_data is not None:
                    return {
                        "data": base64.b64encode(part.inline_data.data).decode("utf-8"),
                        "mime_type": part.inline_data.mime_type or "image/png",
                    }
            return {"error": "이미지 파트 없음"}
        except Exception as e:
            print(f"[ad_image] 예외: {e}")
            return {"error": str(e)}

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_generate, p) for p in prompts]
        images = [f.result() for f in futures]

    return {"images": images}
