"""Web Scraper Agent — crawls target website using Crawl4AI or httpx fallback."""

import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from agents.base_agent import BaseAgent
from agents.context_store import PageData, ScreenshotData
from config.settings import get_settings

logger = logging.getLogger(__name__)

# JavaScript extraction for supplemental data Crawl4AI doesn't natively extract
# (CTAs, forms, testimonials, tech stack, schema, social links)
SUPPLEMENTAL_EXTRACT_JS = """() => {
    const getText = (sel) => {
        const els = document.querySelectorAll(sel);
        return Array.from(els).map(e => e.textContent.trim()).filter(Boolean);
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
    const schemaTypes = schemaScripts.flatMap(s => {
        try {
            const data = JSON.parse(s.textContent);
            if (data['@graph']) return data['@graph'].map(item => item['@type']).filter(Boolean);
            if (Array.isArray(data)) return data.map(item => item['@type']).filter(Boolean);
            if (data['@type']) return [].concat(data['@type']);
            return [];
        } catch { return []; }
    });

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

    return {
        h1: getText('h1'),
        h2: getText('h2'),
        h3: getText('h3'),
        socialLinks,
        ctas,
        forms,
        images,
        testimonials: testimonials.slice(0, 10),
        hasSchema: schemaScripts.length > 0,
        schemaTypes,
        techStack,
        publishDate,
    };
}"""


class WebScraperAgent(BaseAgent):
    agent_name = "web_scraper"
    agent_display_name = "Web Scraper"
    dependencies = []

    async def run(self) -> dict[str, Any]:
        """Crawl the target website and extract structured data."""
        settings = get_settings()
        max_pages = settings.max_pages_quick if self.context.audit_type == "quick" else settings.max_pages_full

        await self.update_progress(5, "Initializing crawler")

        # Try Crawl4AI with one retry (browser launch can fail intermittently on Windows)
        crawl4ai_attempts = 2
        for attempt in range(1, crawl4ai_attempts + 1):
            try:
                return await self._run_crawl4ai(max_pages)
            except Exception as e:
                logger.warning(f"Crawl4AI attempt {attempt}/{crawl4ai_attempts} failed ({e}).")
                if attempt < crawl4ai_attempts:
                    await asyncio.sleep(2)

        logger.info("[web_scraper] Using httpx fallback")
        return await self._run_httpx_fallback(max_pages)

    async def _run_crawl4ai(self, max_pages: int) -> dict[str, Any]:
        """Primary scraper using Crawl4AI with sitemap discovery + deep crawl."""
        # Fix Windows encoding crash: Crawl4AI uses Rich console logging with
        # Unicode chars (→, ✓) that fail on cp1252 Windows terminals.
        import io
        import os
        import sys

        os.environ["PYTHONIOENCODING"] = "utf-8"
        # Force stdout/stderr to UTF-8 so Rich console doesn't crash
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        if hasattr(sys.stderr, "reconfigure"):
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        from crawl4ai import (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
        )
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DomainFilter, FilterChain

        logger.info("[web_scraper] Starting Crawl4AI scraper")

        base_domain = urlparse(self.context.company_url).netloc

        # Configure browser
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            viewport_width=1440,
            viewport_height=900,
            verbose=False,
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # Configure deep crawl strategy with domain filtering
        filter_chain = FilterChain(filters=[DomainFilter(allowed_domains=[base_domain])])

        deep_strategy = BFSDeepCrawlStrategy(
            max_depth=3,
            max_pages=max_pages,
            include_external=False,
            filter_chain=filter_chain,
        )

        # Configure crawler run
        run_config = CrawlerRunConfig(
            deep_crawl_strategy=deep_strategy,
            cache_mode=CacheMode.BYPASS,
            screenshot=True,
            screenshot_wait_for=2.0,
            wait_until="networkidle",
            page_timeout=30000,
            scan_full_page=True,
            scroll_delay=0.3,
            mean_delay=0.5,
            max_range=1.0,
            js_code=SUPPLEMENTAL_EXTRACT_JS,
            stream=True,
        )

        await self.update_progress(10, "Browser connected via Crawl4AI")

        pages_crawled = 0

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Try sitemap discovery first to seed URLs
            seed_urls = await self._discover_sitemap_urls(crawler, base_domain, max_pages)
            if seed_urls:
                logger.info(f"[web_scraper] Discovered {len(seed_urls)} URLs from sitemap")

            # Deep crawl from the main URL
            try:
                results_iter = await crawler.arun(
                    url=self.context.company_url,
                    config=run_config,
                )

                # Process results from deep crawl (streaming mode returns async iterable)
                async for result in results_iter:
                    if not result.success:
                        logger.warning(
                            f"[web_scraper] Failed to crawl {result.url}: "
                            f"{result.error_message}"
                        )
                        continue

                    page_data = self._crawl_result_to_page_data(result)
                    if page_data:
                        await self.context.set_page(page_data)
                        pages_crawled += 1

                        # Store screenshot if available
                        if result.screenshot:
                            screenshot = ScreenshotData(
                                url=result.url,
                                screenshot_type="full_page",
                                base64_data=result.screenshot,
                                width=1440,
                                page_type=page_data.page_type,
                                description=f"Full page screenshot of {page_data.page_type} page",
                                captured_at=time.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                                ),
                            )
                            await self.context.set_screenshot(screenshot)

                        progress = min(85, int(10 + (pages_crawled / max_pages) * 75))
                        await self.update_progress(
                            progress,
                            f"Crawled {pages_crawled}/{max_pages} pages",
                        )

            except Exception as e:
                logger.warning(f"[web_scraper] Deep crawl error: {e}")
                if pages_crawled == 0:
                    raise

            # If sitemap found extra URLs not yet visited, crawl them individually
            if seed_urls and pages_crawled < max_pages:
                crawled_urls = {u.rstrip("/") for u in self.context.pages.keys()}
                remaining = [
                    u for u in seed_urls if u.rstrip("/") not in crawled_urls
                ]
                # Prioritize GTM-relevant pages
                remaining = self._prioritize_urls(remaining)

                single_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    screenshot=True,
                    screenshot_wait_for=2.0,
                    wait_until="networkidle",
                    page_timeout=30000,
                    scan_full_page=True,
                    scroll_delay=0.3,
                    js_code=SUPPLEMENTAL_EXTRACT_JS,
                )

                for url in remaining[: max_pages - pages_crawled]:
                    try:
                        result = await crawler.arun(url=url, config=single_config)
                        # arun may return a container; handle both cases
                        if hasattr(result, '__aiter__'):
                            async for r in result:
                                result = r
                                break
                        if result.success:
                            page_data = self._crawl_result_to_page_data(result)
                            if page_data:
                                await self.context.set_page(page_data)
                                pages_crawled += 1
                                if result.screenshot:
                                    screenshot = ScreenshotData(
                                        url=result.url,
                                        screenshot_type="full_page",
                                        base64_data=result.screenshot,
                                        width=1440,
                                        page_type=page_data.page_type,
                                        description=f"Full page screenshot of {page_data.page_type} page",
                                        captured_at=time.strftime(
                                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                                        ),
                                    )
                                    await self.context.set_screenshot(screenshot)
                    except Exception as e:
                        logger.warning(f"[web_scraper] Failed to crawl sitemap URL {url}: {e}")
                        continue

        await self._detect_company_name()
        await self.update_progress(95, "Analyzing site structure")

        if pages_crawled == 0:
            raise RuntimeError(
                f"Crawl4AI crawled 0 pages from {self.context.company_url}."
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

    async def _discover_sitemap_urls(
        self, crawler, base_domain: str, max_urls: int
    ) -> list[str]:
        """Try to discover URLs from sitemap.xml."""
        try:
            from crawl4ai import SeedingConfig

            seeding_config = SeedingConfig(
                source="sitemap",
                max_urls=max_urls * 3,  # discover more than we'll crawl, then prioritize
                filter_nonsense_urls=True,
                cache_ttl_hours=1,
            )

            # aseed_urls expects domain without protocol
            domain = base_domain.replace("www.", "")
            urls = await asyncio.wait_for(
                crawler.aseed_urls(domain, config=seeding_config),
                timeout=15,
            )

            if isinstance(urls, dict):
                # Multiple domains returned
                all_urls = []
                for domain_urls in urls.values():
                    all_urls.extend(domain_urls)
                return all_urls
            elif isinstance(urls, list):
                return urls
            return []
        except Exception as e:
            logger.info(f"[web_scraper] Sitemap discovery failed (normal for sites without sitemap): {e}")
            return []

    def _crawl_result_to_page_data(self, result) -> Optional[PageData]:
        """Convert a Crawl4AI CrawlResult into our PageData dataclass."""
        try:
            url = result.redirected_url or result.url

            # Extract metadata
            metadata = result.metadata or {}
            title = metadata.get("title", "")
            meta_description = metadata.get("description", "") or metadata.get("meta_description", "")
            og_site_name = metadata.get("og:site_name", "")

            # Get raw text from markdown (LLM-ready format)
            raw_text = ""
            if result.markdown:
                md = str(result.markdown)
                raw_text = md[:10000]

            # Extract headings from HTML since Crawl4AI doesn't parse them separately
            h1_tags, h2_tags, h3_tags = self._extract_headings_from_html(
                result.html or result.cleaned_html or ""
            )

            # Extract links from Crawl4AI's link data
            internal_links = []
            external_links = []
            if result.links:
                for link in result.links.get("internal", []):
                    href = link.get("href", "")
                    if href:
                        internal_links.append(href)
                for link in result.links.get("external", []):
                    href = link.get("href", "")
                    if href:
                        external_links.append(href)

            # Get supplemental data from our JS extraction
            js_data = {}
            if result.js_execution_result:
                if isinstance(result.js_execution_result, dict):
                    js_data = result.js_execution_result
                elif isinstance(result.js_execution_result, str):
                    try:
                        js_data = json.loads(result.js_execution_result)
                    except (json.JSONDecodeError, TypeError):
                        pass

            # Use JS-extracted headings as fallback if HTML parsing missed them
            if not h1_tags and js_data.get("h1"):
                h1_tags = js_data["h1"]
            if not h2_tags and js_data.get("h2"):
                h2_tags = js_data["h2"]
            if not h3_tags and js_data.get("h3"):
                h3_tags = js_data["h3"]

            # Word count from raw text
            word_count = len(raw_text.split()) if raw_text else 0

            page_type = self._classify_page(url, {"title": title, "rawText": raw_text})

            # Schema detection: prefer JS extraction, fall back to HTML parsing
            has_schema = js_data.get("hasSchema", False)
            schema_types = js_data.get("schemaTypes", [])
            if not has_schema:
                has_schema, schema_types = self._detect_schema_from_html(
                    result.html or result.cleaned_html or ""
                )

            return PageData(
                url=url,
                title=title,
                meta_description=meta_description,
                h1_tags=h1_tags,
                h2_tags=h2_tags,
                h3_tags=h3_tags,
                raw_text=raw_text,
                ctas=js_data.get("ctas", []),
                forms=js_data.get("forms", []),
                images=js_data.get("images", []),
                internal_links=internal_links[:100],
                external_links=external_links[:50],
                social_links=js_data.get("socialLinks", {}),
                load_time=0.0,  # Crawl4AI doesn't expose individual page load time
                status_code=result.status_code or 200,
                page_type=page_type,
                testimonials=js_data.get("testimonials", []),
                has_schema=has_schema,
                schema_types=schema_types,
                og_site_name=og_site_name,
                tech_stack=js_data.get("techStack", []),
                word_count=word_count,
                publish_date=js_data.get("publishDate", ""),
                content_type=self._classify_content_type(
                    page_type, {"title": title, "rawText": raw_text}
                ),
            )
        except Exception as e:
            logger.warning(f"[web_scraper] Failed to convert CrawlResult for {result.url}: {e}")
            return None

    @staticmethod
    def _detect_schema_from_html(html: str) -> tuple[bool, list[str]]:
        """Detect JSON-LD schema from raw HTML as fallback when JS extraction fails."""
        import re
        schema_types = []
        for match in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.DOTALL | re.IGNORECASE,
        ):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    if data.get("@graph"):
                        schema_types.extend(
                            item["@type"]
                            for item in data["@graph"]
                            if isinstance(item, dict) and "@type" in item
                        )
                    elif "@type" in data:
                        t = data["@type"]
                        schema_types.extend(t if isinstance(t, list) else [t])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "@type" in item:
                            schema_types.append(item["@type"])
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return bool(schema_types), schema_types

    def _extract_headings_from_html(self, html: str) -> tuple[list[str], list[str], list[str]]:
        """Extract h1, h2, h3 tags from HTML string."""
        from bs4 import BeautifulSoup

        if not html:
            return [], [], []

        try:
            soup = BeautifulSoup(html, "lxml")
            h1s = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
            h2s = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]
            h3s = [h.get_text(strip=True) for h in soup.find_all("h3") if h.get_text(strip=True)]
            return h1s, h2s, h3s
        except Exception:
            return [], [], []

    def _prioritize_urls(self, urls: list[str]) -> list[str]:
        """Sort URLs by GTM relevance with section diversity guarantee."""
        priority_keywords = {
            "pricing": 10,
            "product": 9,
            "platform": 9,
            "solution": 9,
            "features": 8,
            "about": 7,
            "customer": 7,
            "case-stud": 7,
            "case_stud": 7,
            "success": 7,
            "resources": 7,
            "resource-hub": 7,
            "blog": 7,
            "demo": 6,
            "contact": 6,
            "webinar": 6,
            "whitepaper": 6,
            "white-paper": 6,
            "ebook": 6,
            "guide": 6,
            "library": 6,
            "learning": 6,
            "academy": 6,
            "knowledge": 6,
            "podcast": 5,
            "integrations": 5,
            "partners": 5,
            "news": 2,
            "careers": 1,
            "legal": 0,
            "privacy": 0,
            "terms": 0,
            "cookie": 0,
        }

        def score(url: str) -> int:
            url_lower = url.lower()
            best = 4  # default score for unknown pages
            for keyword, points in priority_keywords.items():
                if keyword in url_lower:
                    best = max(best, points)
            return best

        scored = sorted(urls, key=score, reverse=True)

        # Section diversity: ensure at least one URL from each major path prefix
        # so we don't cluster on /solutions/ and miss /resources/ entirely
        seen_sections: set[str] = set()
        diverse_head: list[str] = []
        remainder: list[str] = []

        for url in scored:
            path = urlparse(url).path.strip("/")
            section = path.split("/")[0] if path else ""
            if section and section not in seen_sections:
                seen_sections.add(section)
                diverse_head.append(url)
            else:
                remainder.append(url)

        return diverse_head + remainder

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

                    # Detect schema from HTML
                    page_has_schema, page_schema_types = self._detect_schema_from_html(
                        resp.text
                    )

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
                        has_schema=page_has_schema,
                        schema_types=page_schema_types,
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

        if pages_crawled == 0:
            raise RuntimeError(
                f"httpx fallback crawled 0 pages from {self.context.company_url}. "
                f"Site may be blocking automated requests."
            )

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
