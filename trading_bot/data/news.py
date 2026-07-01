"""Financial news acquisition with sentiment scoring.

Uses NewsAPI when a key is configured, otherwise falls back to public RSS
feeds (CoinDesk, Cointelegraph, Investing.com, Reuters, Yahoo Finance) which
require no API key.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

import feedparser
import httpx

from ..config import settings
from ..models import NewsItem
from ..ai.sentiment import score_text

logger = logging.getLogger(__name__)

NEWS_API_BASE = "https://newsapi.org/v2/everything"

RSS_FEEDS = {
    "general": [
        "https://www.investing.com/rss/news_25.rss",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://finance.yahoo.com/news/rssindex",
    ],
    "crypto": [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
    ],
}


class NewsProvider:
    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    async def get_news(self, query: Optional[str] = None, limit: int = 10) -> List[NewsItem]:
        if settings.news_api_key:
            try:
                return await self._from_newsapi(query, limit)
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning("NewsAPI failed, falling back to RSS: %s", exc)
        return await self._from_rss(query, limit)

    async def _from_newsapi(self, query: Optional[str], limit: int) -> List[NewsItem]:
        params = {
            "apiKey": settings.news_api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(limit, 50),
            "q": query or "markets OR stocks OR crypto OR forex OR economy",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(NEWS_API_BASE, params=params)
            data = resp.json()
        if data.get("status") != "ok":
            raise RuntimeError(data.get("message", "NewsAPI error"))
        items: List[NewsItem] = []
        for art in data.get("articles", [])[:limit]:
            title = art.get("title") or ""
            summary = art.get("description") or ""
            published = None
            if art.get("publishedAt"):
                try:
                    published = datetime.fromisoformat(art["publishedAt"].replace("Z", "+00:00"))
                except ValueError:
                    published = None
            items.append(
                NewsItem(
                    title=title,
                    source=(art.get("source") or {}).get("name", "NewsAPI"),
                    url=art.get("url", ""),
                    published=published,
                    summary=summary,
                    sentiment=score_text(f"{title}. {summary}"),
                )
            )
        return items

    async def _from_rss(self, query: Optional[str], limit: int) -> List[NewsItem]:
        feeds = list(RSS_FEEDS["general"])
        if query and any(k in query.lower() for k in ("btc", "eth", "crypto", "coin", "usdt")):
            feeds = RSS_FEEDS["crypto"] + feeds

        parsed = await asyncio.gather(*(self._parse_feed(url) for url in feeds), return_exceptions=True)
        items: List[NewsItem] = []
        for result in parsed:
            if isinstance(result, Exception):
                continue
            items.extend(result)

        if query:
            q = query.lower()
            filtered = [i for i in items if q in i.title.lower() or q in i.summary.lower()]
            # Keep filtered results if we found any, otherwise show general news.
            if filtered:
                items = filtered

        items.sort(key=lambda i: i.published or datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)
        return items[:limit]

    async def _parse_feed(self, url: str) -> List[NewsItem]:
        def _fetch() -> List[NewsItem]:
            feed = feedparser.parse(url)
            source = feed.feed.get("title", url) if hasattr(feed, "feed") else url
            out: List[NewsItem] = []
            for entry in feed.entries[:15]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                published = None
                if entry.get("published_parsed"):
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                out.append(
                    NewsItem(
                        title=title,
                        source=source,
                        url=entry.get("link", ""),
                        published=published,
                        summary=summary,
                        sentiment=score_text(f"{title}. {summary}"),
                    )
                )
            return out

        return await asyncio.to_thread(_fetch)

    async def market_sentiment(self, query: Optional[str] = None, limit: int = 20) -> float:
        """Aggregate sentiment (-1..+1) over recent news for a topic."""
        news = await self.get_news(query=query, limit=limit)
        if not news:
            return 0.0
        return round(sum(n.sentiment for n in news) / len(news), 3)


news_provider = NewsProvider()
