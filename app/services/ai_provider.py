import asyncio
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.services.search_provider import SearchResult


async def stream_chat_response(prompt: str, search_results: list[SearchResult]) -> AsyncIterator[str]:
    if not settings.use_mock_ai:
        async for chunk in stream_deepseek_response(prompt, search_results):
            yield chunk
        return

    async for chunk in stream_mock_response(prompt, search_results):
        yield chunk


async def stream_mock_response(prompt: str, search_results: list[SearchResult]) -> AsyncIterator[str]:
    source_hint = ""
    if search_results:
        source_hint = " 我参考了搜索结果，并在回答里保留来源线索。"
    text = (
        "这是一个 Demo Mode 的流式回答。"
        "当前后端已经完成登录、会话、消息持久化、搜索降级和刷新恢复所需的状态设计。"
        f"{source_hint} 你可以刷新页面，已保存的消息会从后端恢复。"
    )
    for chunk in text.split(" "):
        await asyncio.sleep(0.02)
        yield chunk + " "


def build_messages(prompt: str, search_results: list[SearchResult]) -> list[dict[str, str]]:
    system = (
        "You are Atom MVP, a concise and practical AI workbench assistant. "
        "Answer in the user's language, prefer concrete steps, and mention source clues when search results are provided."
    )
    if search_results:
        sources = "\n".join(
            f"- {result.title}: {result.snippet} ({result.url})"
            for result in search_results
        )
        prompt = f"{prompt}\n\nSearch results:\n{sources}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]


async def stream_deepseek_response(prompt: str, search_results: list[SearchResult]) -> AsyncIterator[str]:
    url = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.ai_model,
        "messages": build_messages(prompt, search_results),
        "stream": True,
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ").strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    event = httpx.Response(200, content=data).json()
                except ValueError:
                    continue
                for choice in event.get("choices", []):
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
