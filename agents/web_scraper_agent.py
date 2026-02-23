"""Web Scraper Agent — crawls target website using Playwright or httpx fallback."""

import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from agents.base_agent import BaseAgent
from agents.context_store import PageData, ScreenshotData

logger = logging.getLogger(__name__)

# JavaScript extraction function — used by both Playwright and httpx paths.
# Returns a JSON-serializable dict with all page data.
PAGE_EXTRACT_JS = """() => {
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

    // Tech stack detection
    const techStack = [];
    const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src.toLowerCase());
    const allScripts = Array.from(document.querySelectorAll('script')).map(s => (s.textContent || '').substring(0, 500).toLowerCase());
    const allHTML = document.documentElement.innerHTML.substring(0, 50000).toLowerCase();

    const techSignals = [
        { name: 'Google Analytics', patterns: ['gtag', 'google-analytics.com', 'googletagmanager.com/gtag'] },
        { name: 'Google Tag Manager', patterns: ['googletagmanager.com/gtm.js', 'gtm.start'] },
        { name: 'HubSpot', patterns: ['js.hs-scripts.com', 'js.hsforms.net', '_hsp', 'hubspot'] },
        { name: 'Marketo', patterns: ['munchkin', 'marketo.net', 'marketo.com'] },
        { name: 'Salesforce/Pardot', patterns: ['pardot.com', 'pi.pardot.com', 'salesforce'] },
        { name: 'Segment', patterns: ['cdn.segment.com', 'analytics.js', 'segment.io'] },
        { name: 'Hotjar', patterns: ['static.hotjar.com', 'hotjar'] },
        { name: 'FullStory', patterns: ['fullstory.com', 'fs.js'] },
        { name: 'Drift', patterns: ['drift.com', 'js.driftt.com'] },
        { name: 'Intercom', patterns: ['intercom.io', 'widget.intercom.io', 'intercomcdn'] },
        { name: 'Zendesk', patterns: ['zendesk.com', 'zdassets.com'] },
        { name: 'Facebook Pixel', patterns: ['connect.facebook.net', 'fbevents.js', 'fbq('] },
        { name: 'LinkedIn Insight', patterns: ['snap.licdn.com', 'linkedin.com/insight'] },
        { name: 'Google Ads', patterns: ['googleads.g.doubleclick.net', 'googlesyndication', 'adsbygoogle'] },
        { name: 'Mixpanel', patterns: ['cdn.mxpnl.com', 'mixpanel'] },
        { name: 'Amplitude', patterns: ['cdn.amplitude.com', 'amplitude'] },
        { name: 'Heap', patterns: ['heap-analytics', 'heapanalytics.com'] },
        { name: 'Clearbit', patterns: ['clearbit.com', 'tag.clearbitscripts'] },
        { name: 'Crisp', patterns: ['client.crisp.chat'] },
        { name: 'Optimizely', patterns: ['cdn.optimizely.com', 'optimizely'] },
        { name: 'WordPress', patterns: ['wp-content', 'wp-includes'] },
        { name: 'Webflow', patterns: ['webflow.com', 'assets-global.website-files.com'] },
        { name: 'Stripe', patterns: ['js.stripe.com', 'stripe.com'] },
        { name: 'Cloudflare', patterns: ['cdnjs.cloudflare.com', 'cloudflare'] },
        { name: 'Cookiebot', patterns: ['cookiebot.com', 'consentmanager'] },
        { name: 'OneTrust', patterns: ['onetrust.com', 'cdn.cookielaw.org'] },
        { name: 'Sentry', patterns: ['browser.sentry-cdn.com', 'sentry.io'] },
        { name: 'ChatGPT Widget', patterns: ['chat.openai.com'] },
        { name: 'Qualified', patterns: ['qualified.com', 'js.qualified.com'] },
        { name: '6sense', patterns: ['6sense.com', 'j.6sc.co'] },
    ];
    const combined = scripts.join(' ') + ' ' + allScripts.join(' ');
    techSignals.forEach(sig => {
        if (sig.patterns.some(p => combined.includes(p) || allHTML.includes(p))) {
            techStack.push(sig.name);
        }
    });

    // Publish date detection
    let publishDate = '';
    const timeEl = document.querySelector('time[datetime]');
    if (timeEl) publishDate = timeEl.getAttribute('datetime') || '';
    if (!publishDate) {
        const dateMeta = document.querySelector('meta[property="article:published_time"]')
            || document.querySelector('meta[name="date"]')
            || document.querySelector('meta[name="publish-date"]')
            || document.querySelector('meta[name="DC.date.issued"]');
        if (dateMeta) publishDate = dateMeta.content || '';
    }

    // Word count
    const bodyText = document.body?.innerText || '';
    const wordCount = bodyText.split(/\s+/).filter(w => w.length > 0).length;

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
        ogSiteName: document.querySelector('meta[property="og:site_name"]')?.content || '',
        techStack,
        publishDate,
        wordCount,
    };
}"""


class WebScraperAgent(BaseAgent):
    agent_name = "web_scraper"
    agent_display_name = "Web Scraper"
    dependencies = []

    async def run(self) -> dict[str, Any]:
        """Crawl the target website and extract structured data."""
        max_pages = 10 if self.context.audit_type == "quick" else 30

        await self.update_progress(5, "Initializing browser")

        # Try Playwright first, fall back to httpx
        try:
            return await self._run_playwright(max_pages)
        except Exception as e:
            logger.warning(f"Playwright failed ({e}). Falling back to httpx.")

        logger.info("[web_scraper] Using httpx fallback")
        return await self._run_httpx_fallback(max_pages)

    async def _run_playwright(self, max_pages: int) -> dict[str, Any]:
        """Primary scraper using Playwright headless Chromium."""
        from playwright.async_api import async_playwright

        logger.info("[web_scraper] Starting Playwright scraper")

        pages_crawled = 0
        urls_to_visit = [self.context.company_url]
        visited: set[str] = set()
        base_domain = urlparse(self.context.company_url).netloc

        async with async_playwright() as p:
            try:
                browser = await asyncio.wait_for(
                    p.chromium.launch(headless=True), timeout=30
                )
            except (asyncio.TimeoutError, Exception) as e:
                raise RuntimeError(f"Playwright Chromium unavailable: {e}") from e
            page = await browser.new_page(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            await self.update_progress(10, "Browser connected via Playwright")

            try:
                while urls_to_visit and pages_crawled < max_pages:
                    url = urls_to_visit.pop(0)
                    normalized = url.rstrip("/")
                    if normalized in visited:
                        continue
                    visited.add(normalized)

                    try:
                        page_data = await self._scrape_page_playwright(
                            page, url, base_domain
                        )
                        if page_data:
                            await self.context.set_page(page_data)
                            pages_crawled += 1

                            # Take inline screenshot
                            screenshot = await self._take_screenshot_playwright(
                                page, url, page_data.page_type
                            )
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
                        else:
                            logger.warning(f"[web_scraper] No data extracted from {url}")

                        progress = min(90, int(10 + (pages_crawled / max_pages) * 80))
                        await self.update_progress(
                            progress,
                            f"Crawled {pages_crawled}/{max_pages} pages",
                        )

                    except Exception as e:
                        logger.warning(f"Failed to scrape {url}: {e}")
                        continue
            finally:
                await browser.close()

        await self._detect_company_name()
        await self.update_progress(95, "Analyzing site structure")

        if pages_crawled == 0:
            raise RuntimeError(
                f"Playwright crawled 0 pages from {self.context.company_url}. "
                f"Visited {len(visited)} URLs but all failed."
            )

        tech_stack = self._aggregate_tech_stack()

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
                "tech_stack": tech_stack,
            },
        }

    async def _scrape_page_playwright(
        self, page, url: str, base_domain: str
    ) -> Optional[PageData]:
        """Scrape a single page via Playwright."""
        start_time = time.time()

        response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)  # Wait for dynamic content

        status_code = response.status if response else 0
        if status_code >= 400:
            logger.warning(f"[web_scraper] {url} returned status {status_code}")
            return None

        # Extract page data via JavaScript (reuses PAGE_EXTRACT_JS)
        data = await page.evaluate(PAGE_EXTRACT_JS)
        if not data:
            return None

        load_time = time.time() - start_time
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
            og_site_name=data.get("ogSiteName", ""),
            tech_stack=data.get("techStack", []),
            word_count=data.get("wordCount", 0),
            publish_date=data.get("publishDate", ""),
            content_type=self._classify_content_type(page_type, data),
        )

    async def _take_screenshot_playwright(
        self, page, url: str, page_type: str
    ) -> Optional[ScreenshotData]:
        """Take a full-page screenshot via Playwright."""
        try:
            screenshot_bytes = await page.screenshot(full_page=True, type="png")
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            if b64:
                return ScreenshotData(
                    url=url,
                    screenshot_type="full_page",
                    base64_data=b64,
                    width=1440,
                    page_type=page_type,
                    description=f"Full page screenshot of {page_type} page",
                    captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
        except Exception as e:
            logger.warning(f"Playwright screenshot failed for {url}: {e}")
        return None

    async def _detect_company_name(self) -> None:
        """Detect company name from homepage data with multiple fallback strategies."""
        homepage = self.context.get_homepage()

        # Strategy 1: OG site_name (most reliable brand identifier)
        if homepage and homepage.og_site_name:
            logger.info(f"Company name from og:site_name: {homepage.og_site_name}")
            await self.context.set_company_name(homepage.og_site_name)
            return

        # Strategy 2: Parse from title tag using common separators
        if homepage and homepage.title:
            generic = {"home", "homepage", "welcome", "official site", "official website"}
            for sep in ["|", " - ", " — ", " – ", ": ", " · "]:
                if sep in homepage.title:
                    parts = [p.strip() for p in homepage.title.split(sep) if p.strip()]
                    candidates = [p for p in parts if p.lower() not in generic]
                    if candidates:
                        name = min(candidates, key=len)
                        if len(name) > 1:
                            logger.info(f"Company name from title (sep='{sep}'): {name}")
                            await self.context.set_company_name(name)
                            return
            # No separator — use full title if short
            title = homepage.title.strip()
            if title and len(title) < 40 and title.lower() not in generic:
                logger.info(f"Company name from full title: {title}")
                await self.context.set_company_name(title)
                return

        # Strategy 3: First H1 tag on homepage
        if homepage and homepage.h1_tags:
            h1 = homepage.h1_tags[0].strip()
            if h1 and len(h1) < 60:
                logger.info(f"Company name from H1: {h1}")
                await self.context.set_company_name(h1)
                return

        # Strategy 4: Extract from domain name (uses shared utility from ContextStore)
        from agents.context_store import ContextStore
        name_from_domain = ContextStore.name_from_domain(self.context.company_url)
        if name_from_domain:
            logger.info(f"Company name from domain: {name_from_domain}")
            await self.context.set_company_name(name_from_domain)
            return

        logger.warning(
            f"Could not detect company name for {self.context.company_url}. "
            f"Homepage found: {homepage is not None}, "
            f"Title: {getattr(homepage, 'title', 'N/A')}"
        )

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

    def _classify_content_type(self, page_type: str, data: dict) -> str:
        """Classify the content type for blog/resource pages."""
        if page_type not in ("blog", "resources", "customers"):
            return ""
        url_lower = data.get("url", "").lower() if "url" in data else ""
        title_lower = data.get("title", "").lower()
        text_lower = data.get("rawText", "")[:1000].lower()
        combined = url_lower + " " + title_lower + " " + text_lower

        if any(kw in combined for kw in ["case study", "case-study", "success story", "customer story"]):
            return "case_study"
        if any(kw in combined for kw in ["whitepaper", "white paper", "white-paper", "ebook", "e-book"]):
            return "whitepaper"
        if any(kw in combined for kw in ["webinar", "on-demand", "recording"]):
            return "webinar"
        if page_type == "blog":
            return "blog_post"
        return "landing_page"

    def _aggregate_tech_stack(self) -> list[str]:
        """Aggregate unique tech stack items across all crawled pages."""
        all_tech: set[str] = set()
        for page in self.context.pages.values():
            all_tech.update(page.tech_stack)
        return sorted(all_tech)

    async def _run_httpx_fallback(self, max_pages: int) -> dict[str, Any]:
        """Fallback scraper using httpx + BeautifulSoup (no screenshots)."""
        import httpx
        from bs4 import BeautifulSoup

        await self.update_progress(10, "Using httpx fallback scraper")

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

                    og_site_name = ""
                    og_tag = soup.find("meta", attrs={"property": "og:site_name"})
                    if og_tag:
                        og_site_name = og_tag.get("content", "")

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
                        og_site_name=og_site_name,
                    )
                    await self.context.set_page(page_data)
                    pages_crawled += 1

                    for link in internal_links:
                        if link.rstrip("/") not in visited and link not in urls_to_visit:
                            urls_to_visit.append(link)

                    progress = min(90, int(10 + (pages_crawled / max_pages) * 80))
                    await self.update_progress(
                        progress,
                        f"Crawled {pages_crawled}/{max_pages} pages (httpx)",
                    )

                except Exception as e:
                    logger.warning(f"httpx fallback failed for {url}: {e}")
                    continue

        await self._detect_company_name()

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
