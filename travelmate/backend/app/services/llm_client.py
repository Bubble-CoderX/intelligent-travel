from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

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
    model: str = "",
) -> str:
    """调用 DeepSeek API（非流式）。model 为空时使用默认模型。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用 LLM。")

    use_model = model or DEEPSEEK_MODEL

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
                "model": use_model,
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        body = response.json()

        if "error" in body:
            error_msg = body["error"].get("message", str(body["error"]))
            error_code = body["error"].get("code", "unknown")
            logger.error("DeepSeek API 错误 [%s]: %s", error_code, error_msg)
            raise RuntimeError(f"DeepSeek API 错误 [{error_code}]: {error_msg}")

        if "choices" not in body:
            logger.error("DeepSeek 响应异常: %.500s", body)
            raise RuntimeError(f"DeepSeek 响应格式异常：缺少 choices 字段")

        return body["choices"][0]["message"]["content"]


async def call_llm_stream(
    messages: list[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2000,
    model: str = "",
) -> AsyncGenerator[str, None]:
    """O9: 流式调用 DeepSeek API，逐 token 返回文本片段。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用 LLM。")

    use_model = model or DEEPSEEK_MODEL

    full_messages: list[dict] = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT_SECONDS) as client:
        async with client.stream(
            "POST",
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": use_model,
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                error_data = json.loads(body) if body else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                raise RuntimeError(f"DeepSeek API 错误: {error_msg}")

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue
