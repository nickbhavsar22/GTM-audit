"""Shared in-memory state for all agents during an audit."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PageData:
    """Extracted data from a single crawled page."""
    url: str
    title: str = ""
    meta_description: str = ""
    h1_tags: list[str] = field(default_factory=list)
    h2_tags: list[str] = field(default_factory=list)
    h3_tags: list[str] = field(default_factory=list)
    raw_text: str = ""
    html: str = ""
    ctas: list[dict] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    load_time: float = 0.0
    status_code: int = 0
    page_type: str = ""  # home, product, pricing, about, blog, etc.
    testimonials: list[str] = field(default_factory=list)
    has_schema: bool = False
    schema_types: list[str] = field(default_factory=list)


@dataclass
class ScreenshotData:
    """Screenshot captured during crawling."""
    url: str
    screenshot_type: str = "full_page"  # "full_page" or "element"
    file_path: str = ""
    base64_data: str = ""
    width: int = 0
    height: int = 0
    element_selector: str = ""
    captured_at: str = ""
    annotations: list[dict] = field(default_factory=list)


@dataclass
class ContextStore:
    """Thread-safe shared state for all agents during an audit."""

    # Config
    company_url: str = ""
    company_name: str = ""
    audit_type: str = "full"
    audit_id: str = ""

    # Crawled data (populated by Web Scraper Agent)
    pages: dict[str, PageData] = field(default_factory=dict)
    screenshots: dict[str, ScreenshotData] = field(default_factory=dict)

    # Agent results (populated by each agent)
    agent_analyses: dict[str, Any] = field(default_factory=dict)

    # Company research (populated by Company Research Agent)
    company_profile: dict = field(default_factory=dict)

    # Competitors (populated by Competitor Agent)
    competitors: list[dict] = field(default_factory=list)

    # Lock for thread-safe writes
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def set_page(self, page: PageData) -> None:
        async with self._lock:
            self.pages[page.url] = page

    async def set_screenshot(self, screenshot: ScreenshotData) -> None:
        async with self._lock:
            self.screenshots[screenshot.url] = screenshot

    async def set_analysis(self, agent_name: str, analysis: Any) -> None:
        async with self._lock:
            self.agent_analyses[agent_name] = analysis

    def get_analysis(self, agent_name: str) -> Optional[Any]:
        return self.agent_analyses.get(agent_name)

    def get_homepage(self) -> Optional[PageData]:
        """Get the homepage PageData."""
        normalized = self.company_url.rstrip("/")
        for url, page in self.pages.items():
            if url.rstrip("/") == normalized:
                return page
        # Fallback: return first page
        return next(iter(self.pages.values()), None)

    def get_all_text(self, max_chars: int = 50000) -> str:
        """Aggregate text content from all crawled pages."""
        parts: list[str] = []
        total = 0
        for url, page in self.pages.items():
            chunk = f"\n--- PAGE: {url} ---\n"
            chunk += f"Title: {page.title}\n"
            if page.h1_tags:
                chunk += f"H1: {', '.join(page.h1_tags)}\n"
            if page.h2_tags:
                chunk += f"H2: {', '.join(page.h2_tags[:10])}\n"
            chunk += f"Content:\n{page.raw_text[:5000]}\n"
            if total + len(chunk) > max_chars:
                break
            parts.append(chunk)
            total += len(chunk)
        return "\n".join(parts)

    def get_pages_by_type(self, page_type: str) -> list[PageData]:
        """Get all pages of a specific type."""
        return [p for p in self.pages.values() if p.page_type == page_type]
