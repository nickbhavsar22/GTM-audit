"""Web Scraper Agent — crawls target website using Playwright and extracts structured data."""

import asyncio
import base64
import logging
import re
import time
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from agents.base_agent import BaseAgent
from agents.context_store import PageData, ScreenshotData

logger = logging.getLogger(__name__)


class WebScraperAgent(BaseAgent):
    agent_name = "web_scraper"
    agent_display_name = "Web Scraper"
    dependencies = []

    async def run(self) -> dict[str, Any]:
        """Crawl the target website and extract structured data."""
        max_pages = (
            self.context.audit_type == "quick"
            and 10
            or 30
        )

        await self.update_progress(5, "Initializing browser")

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed. Using httpx fallback.")
            return await self._run_httpx_fallback(max_pages)

        pages_crawled = 0
        urls_to_visit = [self.context.company_url]
        visited: set[str] = set()
        base_domain = urlparse(self.context.company_url).netloc

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            while urls_to_visit and pages_crawled < max_pages:
                url = urls_to_visit.pop(0)
                normalized = url.rstrip("/")
                if normalized in visited:
                    continue
                visited.add(normalized)

                try:
                    page_data = await self._scrape_page(page, url, base_domain)
                    if page_data:
                        await self.context.set_page(page_data)
                        pages_crawled += 1

                        # Take screenshot
                        screenshot = await self._take_screenshot(page, url)
                        if screenshot:
                            await self.context.set_screenshot(screenshot)

                        # Add internal links to visit queue
                        for link in page_data.internal_links:
                            link_normalized = link.rstrip("/")
                            if (
                                link_normalized not in visited
                                and urlparse(link).netloc == base_domain
                                and link not in urls_to_visit
                            ):
                                urls_to_visit.append(link)

                    progress = min(90, int(5 + (pages_crawled / max_pages) * 85))
                    await self.update_progress(
                        progress,
                        f"Crawled {pages_crawled}/{max_pages} pages",
                    )

                except Exception as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
                    continue

            await browser.close()

        # Detect company name from homepage
        homepage = self.context.get_homepage()
        if homepage and homepage.title:
            name = homepage.title.split("|")[0].split("-")[0].split("—")[0].strip()
            self.context.company_name = name

        await self.update_progress(95, "Analyzing site structure")

        return {
            "score": None,
            "grade": None,
            "analysis_text": (
                f"Crawled {pages_crawled} pages from {self.context.company_url}. "
                f"Captured {len(self.context.screenshots)} screenshots."
            ),
            "recommendations": [],
            "result_data": {
                "pages_crawled": pages_crawled,
                "screenshots_captured": len(self.context.screenshots),
                "pages": list(self.context.pages.keys()),
            },
        }

    async def _scrape_page(
        self, page, url: str, base_domain: str
    ) -> Optional[PageData]:
        """Scrape a single page and return PageData."""
        start_time = time.time()

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            if not response:
                return None

            status_code = response.status
            if status_code >= 400:
                return None

            # Wait for content to load
            await page.wait_for_timeout(1000)

            # Extract data using JavaScript
            data = await page.evaluate(
                """() => {
                const getText = (sel) => {
                    const els = document.querySelectorAll(sel);
                    return Array.from(els).map(e => e.textContent.trim()).filter(Boolean);
                };

                const getLinks = (internal) => {
                    const base = window.location.hostname;
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links
                        .map(a => a.href)
                        .filter(href => {
                            try {
                                const u = new URL(href);
                                const isInternal = u.hostname === base || u.hostname === '';
                                return internal ? isInternal : !isInternal;
                            } catch { return false; }
                        })
                        .filter((v, i, a) => a.indexOf(v) === i)
                        .slice(0, 100);
                };

                const socialPlatforms = ['linkedin', 'twitter', 'x.com', 'facebook',
                                         'instagram', 'youtube', 'github', 'tiktok'];
                const socialLinks = {};
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href.toLowerCase();
                    socialPlatforms.forEach(p => {
                        if (href.includes(p) && !socialLinks[p]) {
                            socialLinks[p === 'x.com' ? 'twitter' : p] = a.href;
                        }
                    });
                });

                const ctas = Array.from(document.querySelectorAll(
                    'a.btn, a.button, button, a[class*="cta"], a[class*="CTA"], ' +
                    'a[href*="demo"], a[href*="trial"], a[href*="signup"], a[href*="contact"]'
                )).map(el => ({
                    text: el.textContent.trim().substring(0, 100),
                    href: el.href || '',
                    tag: el.tagName,
                })).slice(0, 20);

                const forms = Array.from(document.querySelectorAll('form')).map(f => ({
                    action: f.action || '',
                    method: f.method || 'GET',
                    fields: Array.from(f.querySelectorAll('input, select, textarea')).map(
                        i => ({ name: i.name, type: i.type, placeholder: i.placeholder })
                    ),
                }));

                const images = Array.from(document.querySelectorAll('img')).map(i => ({
                    src: i.src,
                    alt: i.alt,
                    width: i.naturalWidth,
                    height: i.naturalHeight,
                })).slice(0, 30);

                const testimonials = [];
                document.querySelectorAll(
                    '[class*="testimonial"], [class*="quote"], [class*="review"], blockquote'
                ).forEach(el => {
                    const text = el.textContent.trim();
                    if (text.length > 20 && text.length < 500) testimonials.push(text);
                });

                const schemaScripts = Array.from(
                    document.querySelectorAll('script[type="application/ld+json"]')
                );
                const schemaTypes = schemaScripts.map(s => {
                    try { return JSON.parse(s.textContent)['@type']; }
                    catch { return null; }
                }).filter(Boolean);

                return {
                    title: document.title || '',
                    metaDescription: document.querySelector('meta[name="description"]')?.content || '',
                    h1: getText('h1'),
                    h2: getText('h2'),
                    h3: getText('h3'),
                    rawText: document.body?.innerText?.substring(0, 10000) || '',
                    internalLinks: getLinks(true),
                    externalLinks: getLinks(false),
                    socialLinks,
                    ctas,
                    forms,
                    images,
                    testimonials: testimonials.slice(0, 10),
                    hasSchema: schemaScripts.length > 0,
                    schemaTypes,
                };
            }"""
            )

            load_time = time.time() - start_time

            # Classify page type
            page_type = self._classify_page(url, data)

            return PageData(
                url=url,
                title=data.get("title", ""),
                meta_description=data.get("metaDescription", ""),
                h1_tags=data.get("h1", []),
                h2_tags=data.get("h2", []),
                h3_tags=data.get("h3", []),
                raw_text=data.get("rawText", ""),
                ctas=data.get("ctas", []),
                forms=data.get("forms", []),
                images=data.get("images", []),
                internal_links=data.get("internalLinks", []),
                external_links=data.get("externalLinks", []),
                social_links=data.get("socialLinks", {}),
                load_time=load_time,
                status_code=status_code,
                page_type=page_type,
                testimonials=data.get("testimonials", []),
                has_schema=data.get("hasSchema", False),
                schema_types=data.get("schemaTypes", []),
            )

        except Exception as e:
            logger.warning(f"Error scraping {url}: {e}")
            return None

    async def _take_screenshot(self, page, url: str) -> Optional[ScreenshotData]:
        """Take a full-page screenshot."""
        try:
            screenshot_bytes = await page.screenshot(full_page=True, type="png")
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            return ScreenshotData(
                url=url,
                screenshot_type="full_page",
                base64_data=b64,
                width=1440,
                captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        except Exception as e:
            logger.warning(f"Failed to take screenshot of {url}: {e}")
            return None

    def _classify_page(self, url: str, data: dict) -> str:
        """Classify the page type based on URL and content."""
        url_lower = url.lower()
        title_lower = (data.get("title", "") + " " + data.get("rawText", "")[:200]).lower()

        patterns = {
            "pricing": ["pricing", "plans", "packages"],
            "about": ["about", "about-us", "our-story", "team"],
            "blog": ["blog", "articles", "news", "insights"],
            "contact": ["contact", "get-in-touch"],
            "demo": ["demo", "request-demo", "book-a-demo"],
            "product": ["product", "features", "platform", "solution"],
            "customers": ["customers", "case-studies", "success-stories", "testimonials"],
            "careers": ["careers", "jobs", "hiring"],
            "legal": ["privacy", "terms", "legal", "cookie"],
            "resources": ["resources", "documentation", "docs", "help", "support"],
            "integrations": ["integrations", "partners", "marketplace"],
        }

        for page_type, keywords in patterns.items():
            if any(kw in url_lower for kw in keywords):
                return page_type
            if any(kw in title_lower for kw in keywords):
                return page_type

        # Homepage detection
        path = urlparse(url).path.rstrip("/")
        if not path or path == "":
            return "home"

        return "other"

    async def _run_httpx_fallback(self, max_pages: int) -> dict[str, Any]:
        """Fallback scraper using httpx + BeautifulSoup (no screenshots)."""
        import httpx
        from bs4 import BeautifulSoup

        pages_crawled = 0
        urls_to_visit = [self.context.company_url]
        visited: set[str] = set()
        base_domain = urlparse(self.context.company_url).netloc

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            while urls_to_visit and pages_crawled < max_pages:
                url = urls_to_visit.pop(0)
                normalized = url.rstrip("/")
                if normalized in visited:
                    continue
                visited.add(normalized)

                try:
                    start = time.time()
                    resp = await client.get(url)
                    if resp.status_code >= 400:
                        continue

                    soup = BeautifulSoup(resp.text, "lxml")
                    load_time = time.time() - start

                    # Extract basic data
                    title = soup.title.string if soup.title else ""
                    meta_desc = ""
                    meta_tag = soup.find("meta", attrs={"name": "description"})
                    if meta_tag:
                        meta_desc = meta_tag.get("content", "")

                    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
                    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
                    h3s = [h.get_text(strip=True) for h in soup.find_all("h3")]
                    raw_text = soup.get_text(separator="\n", strip=True)[:10000]

                    # Links
                    internal_links = []
                    external_links = []
                    for a in soup.find_all("a", href=True):
                        href = urljoin(url, a["href"])
                        parsed = urlparse(href)
                        if parsed.netloc == base_domain:
                            internal_links.append(href)
                        elif parsed.scheme in ("http", "https"):
                            external_links.append(href)

                    page_data = PageData(
                        url=url,
                        title=title or "",
                        meta_description=meta_desc,
                        h1_tags=h1s,
                        h2_tags=h2s,
                        h3_tags=h3s,
                        raw_text=raw_text,
                        internal_links=list(set(internal_links))[:100],
                        external_links=list(set(external_links))[:50],
                        load_time=load_time,
                        status_code=resp.status_code,
                        page_type=self._classify_page(url, {"title": title, "rawText": raw_text}),
                    )
                    await self.context.set_page(page_data)
                    pages_crawled += 1

                    for link in internal_links:
                        if link.rstrip("/") not in visited and link not in urls_to_visit:
                            urls_to_visit.append(link)

                    progress = min(90, int(5 + (pages_crawled / max_pages) * 85))
                    await self.update_progress(
                        progress,
                        f"Crawled {pages_crawled}/{max_pages} pages (httpx)",
                    )

                except Exception as e:
                    logger.warning(f"httpx fallback failed for {url}: {e}")
                    continue

        homepage = self.context.get_homepage()
        if homepage and homepage.title:
            name = homepage.title.split("|")[0].split("-")[0].split("—")[0].strip()
            self.context.company_name = name

        return {
            "score": None,
            "grade": None,
            "analysis_text": (
                f"Crawled {pages_crawled} pages from {self.context.company_url} "
                f"(httpx fallback, no screenshots)."
            ),
            "recommendations": [],
            "result_data": {
                "pages_crawled": pages_crawled,
                "screenshots_captured": 0,
                "pages": list(self.context.pages.keys()),
                "fallback": True,
            },
        }
