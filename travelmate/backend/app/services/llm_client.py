from __future__ import annotations

import logging

import httpx

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


async def call_llm(
    messages: list[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """调用 DeepSeek API。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用 LLM。")

    full_messages: list[dict] = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        body = response.json()

        # DeepSeek 错误响应处理
        if "error" in body:
            error_msg = body["error"].get("message", str(body["error"]))
            error_code = body["error"].get("code", "unknown")
            logger.error("DeepSeek API 错误 [%s]: %s", error_code, error_msg)
            raise RuntimeError(f"DeepSeek API 错误 [{error_code}]: {error_msg}")

        if "choices" not in body:
            logger.error("DeepSeek 响应异常: %.500s", body)
            raise RuntimeError(f"DeepSeek 响应格式异常：缺少 choices 字段")

        return body["choices"][0]["message"]["content"]
