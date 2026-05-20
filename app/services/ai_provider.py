import asyncio
from collections.abc import AsyncIterator

from app.services.search_provider import SearchResult


async def stream_chat_response(prompt: str, search_results: list[SearchResult]) -> AsyncIterator[str]:
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

