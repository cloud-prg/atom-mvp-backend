from dataclasses import dataclass

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

    # Real Exa integration is intentionally isolated for later credentials.
    return ("exa", "failed", [])

