import io
import base64
import os

import google.generativeai as genai
from PIL import Image


def generate_ad_images(
    image_file,
    product_name: str = "",
    category: str = "",
    ingredients: str = "",
    effects: str = "",
    headline1: str = "",
    headline2: str = "",
) -> dict:
    """
    제품 이미지 + 제품 정보 → Gemini로 광고 이미지 2장 생성
    Returns: {"images": [{"data": base64, "mime_type": "image/png"}, ...]}
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY가 설정되지 않았습니다."}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.1-flash-image-preview")

    try:
        pil_image = Image.open(image_file)
    except Exception as e:
        return {"error": f"이미지 로드 실패: {e}"}

    product_ctx = f"{category} product"
    if product_name:
        product_ctx = f"{product_name} ({category})"

    prompts = [
        (
            f"Create a high-end luxury beauty advertisement image for this {product_ctx}. "
            f"{'Key ingredients: ' + ingredients + '. ' if ingredients else ''}"
            f"{'Benefits: ' + effects + '. ' if effects else ''}"
            f"{'Ad concept: ' + headline1 + '. ' if headline1 else ''}"
            "Place the product on a smooth marble surface with soft morning sunlight. "
            "Add blurred botanical elements in the background. "
            "Professional commercial photography, cinematic lighting, 8k resolution."
        ),
        (
            f"Create a modern minimalist beauty ad campaign image for this {product_ctx}. "
            f"{'Featured ingredients: ' + ingredients + '. ' if ingredients else ''}"
            f"{'Product effects: ' + effects + '. ' if effects else ''}"
            f"{'Ad concept: ' + headline2 + '. ' if headline2 else ''}"
            "Clean studio background with subtle pastel color gradients. "
            "The product is centered with elegant shadow and reflection. "
            "High-fashion editorial style, premium cosmetics photography."
        ),
    ]

    images = []
    for prompt in prompts:
        try:
            response = model.generate_content([prompt, pil_image])
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                    images.append({
                        "data": b64,
                        "mime_type": part.inline_data.mime_type or "image/png",
                    })
                    break
        except Exception as e:
            images.append({"error": str(e)})

    return {"images": images}
