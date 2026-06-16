"""O8: 通义千问 VL 多模态图片识别服务。"""
from __future__ import annotations

import base64
import logging

import httpx

from app.core.config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_VL_MODEL

logger = logging.getLogger(__name__)


async def analyze_image(image_base64: str, question: str = "请分析这张图片的内容") -> str:
    """调用通义千问 VL 分析图片内容。返回识别结果文本。"""
    if not QWEN_API_KEY:
        raise RuntimeError("未配置 QWEN_API_KEY，无法调用图片识别。请在 .env 中设置 QWEN_API_KEY。")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                },
                {
                    "type": "text",
                    "text": question or "请分析这张图片。如果是景点请介绍景点名称和基本信息，如果是美食请介绍菜品名称，如果是路牌请说明位置。用中文简洁回答。"
                },
            ],
        }
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{QWEN_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": QWEN_VL_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 500,
            },
        )

        body = response.json()
        if "error" in body:
            error_msg = body["error"].get("message", str(body["error"]))
            logger.error("千问 VL API 错误: %s", error_msg)
            raise RuntimeError(f"千问 API 错误: {error_msg}")

        if "choices" not in body:
            raise RuntimeError("千问 API 响应格式异常")

        return body["choices"][0]["message"]["content"]
