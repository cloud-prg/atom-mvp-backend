from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    published_at: str | None = None


def should_search(query: str, mode: str) -> bool:
    if mode == "off":
        return False
    if mode == "force":
        return True
    keywords = ["最新", "今天", "新闻", "价格", "竞品", "资料", "调研", "today", "latest", "news", "price"]
    lowered = query.lower()
    return any(keyword in lowered for keyword in keywords)


async def search(query: str, mode: str = "force") -> tuple[str, str, list[SearchResult]]:
    if not should_search(query, mode):
        return ("none", "skipped", [])
    if settings.use_mock_search:
        return (
            "mock",
            "completed",
            [
                SearchResult(
                    title="Mock source: AI workbench recovery patterns",
                    url="https://example.com/ai-workbench-recovery",
                    snippet="Refresh recovery keeps persisted messages, restores drafts locally, and marks interrupted streams as resumable.",
                    source="mock",
                    published_at="2026-05-21",
                ),
                SearchResult(
                    title="Mock source: SSE streaming design",
                    url="https://example.com/sse-streaming-design",
                    snippet="SSE is a simple fit for one-way assistant token streaming in MVP products.",
                    source="mock",
                    published_at="2026-05-21",
                ),
            ],
        )

    return await search_exa(query)


async def search_exa(query: str) -> tuple[str, str, list[SearchResult]]:
    headers = {
        "x-api-key": settings.exa_api_key or "",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "type": "auto",
        "numResults": 5,
        "contents": {"text": True},
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://api.exa.ai/search", headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        return ("exa", "failed", [])

    data = response.json()
    results = [
        SearchResult(
            title=item.get("title") or item.get("url") or "Untitled source",
            url=item.get("url") or "",
            snippet=(item.get("text") or item.get("summary") or "").strip(),
            source="exa",
            published_at=item.get("publishedDate"),
        )
        for item in data.get("results", [])
        if item.get("url")
    ]
    return ("exa", "completed", results)
