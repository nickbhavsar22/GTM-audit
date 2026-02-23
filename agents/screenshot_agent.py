"""Screenshot Agent — captures full-page and element-level screenshots via Playwright."""

import asyncio
import base64
import logging
import time
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.context_store import ScreenshotData

logger = logging.getLogger(__name__)

# Element types to capture and their CSS selectors (ordered by priority)
ELEMENT_TARGETS = [
    {
        "type": "hero",
        "selectors": [
            "section[class*='hero']", "div[class*='hero']",
            "[class*='banner']", "header + section", "header + div",
            "main > section:first-child", "main > div:first-child",
        ],
        "description": "Hero section / above-the-fold content",
    },
    {
        "type": "h1",
        "selectors": ["h1"],
        "description": "Primary headline",
    },
    {
        "type": "cta_primary",
        "selectors": [
            "a[class*='cta']", "a[class*='CTA']", "button[class*='cta']",
            "a[href*='demo']", "a[href*='trial']", "a[href*='signup']",
            ".hero a.btn", ".hero button", "header a.btn",
        ],
        "description": "Primary call-to-action button",
    },
    {
        "type": "nav",
        "selectors": ["nav", "header nav", "[role='navigation']"],
        "description": "Navigation bar",
    },
    {
        "type": "footer",
        "selectors": ["footer", "[role='contentinfo']"],
        "description": "Footer section",
    },
    {
        "type": "pricing",
        "selectors": [
            "[class*='pricing']", "[class*='plans']", "[class*='packages']",
            "section[id*='pricing']", "div[id*='pricing']",
        ],
        "description": "Pricing table / plans section",
    },
    {
        "type": "testimonial",
        "selectors": [
            "[class*='testimonial']", "[class*='review']", "[class*='quote']",
            "[class*='social-proof']", "blockquote",
        ],
        "description": "Testimonials / social proof section",
    },
    {
        "type": "form",
        "selectors": [
            "form", "[class*='signup']", "[class*='contact']",
        ],
        "description": "Lead capture form",
    },
]

# Priority page types to screenshot (in order)
PRIORITY_PAGE_TYPES = ["home", "product", "pricing", "demo", "contact", "customers", "about"]

# Which element types to capture per page type
PAGE_ELEMENT_MAP = {
    "home": {"hero", "h1", "cta_primary", "nav", "footer", "testimonial"},
    "pricing": {"pricing", "cta_primary", "nav"},
    "product": {"hero", "h1", "cta_primary"},
    "demo": {"form", "h1", "cta_primary"},
    "contact": {"form", "h1", "cta_primary"},
    "customers": {"testimonial", "h1"},
}
DEFAULT_ELEMENTS = {"hero", "h1"}


class ScreenshotAgent(BaseAgent):
    agent_name = "screenshot"
    agent_display_name = "Visual Screenshot Capture"
    dependencies = ["web_scraper"]
    max_retries = 2

    async def run(self) -> dict[str, Any]:
        """Navigate to key pages and capture full-page + element-level screenshots."""
        from config.settings import get_settings
        from playwright.async_api import async_playwright

        settings = get_settings()

        if not settings.screenshot_enabled:
            return {
                "score": None,
                "grade": None,
                "analysis_text": "Screenshot capture disabled in settings.",
                "recommendations": [],
                "result_data": {"total_screenshots": 0, "skipped": True},
            }

        await self.update_progress(5, "Launching Playwright browser")
        logger.info("[screenshot] Starting Playwright-based screenshot capture")

        pages_to_visit = self._prioritize_pages(settings.screenshot_max_pages)
        total_screenshots = 0
        element_screenshots = 0
        errors = []

        try:
            async with async_playwright() as p:
                try:
                    browser = await asyncio.wait_for(
                        p.chromium.launch(headless=True), timeout=60
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    diag = f"Playwright Chromium unavailable: {e}"
                    logger.warning(diag)
                    self.context.screenshot_diagnostic = diag
                    return {
                        "score": None,
                        "grade": None,
                        "analysis_text": diag,
                        "recommendations": [],
                        "result_data": {"total_screenshots": 0, "browser_unavailable": True},
                    }

                page = await browser.new_page(
                    viewport={
                        "width": settings.screenshot_viewport_width,
                        "height": settings.screenshot_viewport_height,
                    },
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                await self.update_progress(10, "Browser connected")

                try:
                    for i, (url, page_type) in enumerate(pages_to_visit):
                        pct = 10 + int((i / max(len(pages_to_visit), 1)) * 72)
                        await self.update_progress(
                            pct, f"Screenshotting {page_type} page ({i+1}/{len(pages_to_visit)})"
                        )

                        try:
                            await page.goto(
                                url, timeout=30000, wait_until="domcontentloaded"
                            )
                            await page.wait_for_timeout(1500)

                            # Dismiss cookie banners and popups
                            await self._dismiss_overlays(page)

                            # Scroll through page to trigger lazy-loaded content
                            await self._scroll_to_load(page)

                            # Full-page screenshot
                            screenshot_bytes = await page.screenshot(
                                full_page=True, type="png"
                            )
                            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                            if b64:
                                await self.context.set_screenshot(ScreenshotData(
                                    url=url,
                                    screenshot_type="full_page",
                                    base64_data=b64,
                                    width=settings.screenshot_viewport_width,
                                    page_type=page_type,
                                    description=f"Full page screenshot of {page_type} page",
                                    captured_at=time.strftime(
                                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                                    ),
                                ))
                                total_screenshots += 1

                            # Element-level screenshots
                            allowed_elements = PAGE_ELEMENT_MAP.get(
                                page_type, DEFAULT_ELEMENTS
                            )
                            for target in ELEMENT_TARGETS:
                                if target["type"] not in allowed_elements:
                                    continue

                                elem_result = await self._capture_element(
                                    page, url, page_type, target
                                )
                                if elem_result:
                                    element_screenshots += 1
                                    total_screenshots += 1

                        except Exception as e:
                            logger.warning(f"Failed to screenshot {url}: {e}")
                            errors.append(f"{page_type}: {str(e)[:100]}")
                            continue

                    # Mobile viewport screenshot of homepage
                    await self.update_progress(85, "Capturing mobile screenshot")
                    mobile_count = await self._capture_mobile_screenshot(
                        page, pages_to_visit
                    )
                    total_screenshots += mobile_count
                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Playwright screenshot capture failed: {e}")
            diag = (
                f"Screenshot capture failed: {e}. "
                f"Captured {total_screenshots} screenshots before error."
            )
            self.context.screenshot_diagnostic = diag
            return {
                "score": None,
                "grade": None,
                "analysis_text": diag,
                "recommendations": [],
                "result_data": {
                    "total_screenshots": total_screenshots,
                    "element_screenshots": element_screenshots,
                    "errors": errors,
                    "fallback": True,
                },
            }

        await self.update_progress(95, "Organizing screenshots")

        return {
            "score": None,
            "grade": None,
            "analysis_text": (
                f"Captured {total_screenshots} screenshots across "
                f"{len(pages_to_visit)} pages. "
                f"{element_screenshots} element-level screenshots captured."
            ),
            "recommendations": [],
            "result_data": {
                "total_screenshots": total_screenshots,
                "element_screenshots": element_screenshots,
                "pages_screenshotted": [url for url, _ in pages_to_visit],
                "errors": errors,
            },
        }

    def _prioritize_pages(self, max_pages: int) -> list[tuple[str, str]]:
        """Select and prioritize pages to screenshot based on type."""
        result = []
        seen_urls = set()

        # Ensure homepage is first
        homepage = self.context.get_homepage()
        if homepage:
            result.append((homepage.url, homepage.page_type or "home"))
            seen_urls.add(homepage.url)

        for page_type in PRIORITY_PAGE_TYPES:
            pages = self.context.get_pages_by_type(page_type)
            for page in pages:
                if page.url not in seen_urls:
                    result.append((page.url, page_type))
                    seen_urls.add(page.url)
                    break  # One page per type

        return result[:max_pages]

    async def _capture_element(
        self,
        page,
        url: str,
        page_type: str,
        target: dict,
    ) -> Optional[ScreenshotData]:
        """Try to find and screenshot a target element using CSS selectors."""
        for selector in target["selectors"]:
            try:
                locator = page.locator(selector).first
                if await locator.count() == 0:
                    continue

                screenshot_bytes = await locator.screenshot(
                    type="png", timeout=5000
                )
                b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                if b64:
                    screenshot_data = ScreenshotData(
                        url=url,
                        screenshot_type=target["type"],
                        base64_data=b64,
                        element_selector=selector,
                        page_type=page_type,
                        description=target["description"],
                        captured_at=time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                        ),
                    )
                    await self.context.set_screenshot(screenshot_data)
                    return screenshot_data

            except Exception as e:
                logger.debug(
                    f"Element capture failed for {target['type']} "
                    f"with {selector}: {e}"
                )
                continue

        return None

    async def _capture_mobile_screenshot(
        self, page, pages: list[tuple[str, str]]
    ) -> int:
        """Capture mobile-viewport screenshot of homepage. Returns count captured."""
        if not pages:
            return 0

        url, _ = pages[0]
        try:
            await page.set_viewport_size({"width": 375, "height": 812})
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            screenshot_bytes = await page.screenshot(full_page=True, type="png")
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            if b64:
                await self.context.set_screenshot(ScreenshotData(
                    url=url,
                    screenshot_type="mobile_full",
                    base64_data=b64,
                    width=375,
                    page_type="home",
                    description="Mobile viewport screenshot of homepage",
                    captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ))
                return 1
        except Exception as e:
            logger.warning(f"Mobile screenshot failed: {e}")
        return 0

    @staticmethod
    async def _dismiss_overlays(page) -> None:
        """Hide cookie banners, popups, and modal overlays via CSS injection."""
        try:
            await page.add_style_tag(content="""
                [class*="cookie" i], [id*="cookie" i], [class*="consent" i],
                [id*="consent" i], [class*="popup" i], [class*="modal" i],
                [class*="overlay" i]:not(body):not(html),
                [class*="gdpr" i], [id*="gdpr" i],
                [class*="banner" i][class*="notice" i],
                [aria-label*="cookie" i], [aria-label*="consent" i] {
                    display: none !important;
                    visibility: hidden !important;
                }
            """)
        except Exception as e:
            logger.debug(f"Could not inject overlay-dismiss CSS: {e}")

    @staticmethod
    async def _scroll_to_load(page) -> None:
        """Scroll through the page to trigger lazy-loaded images and content."""
        try:
            # Force eager loading on lazy images
            await page.evaluate("""
                () => {
                    document.querySelectorAll('img[loading="lazy"]')
                        .forEach(img => img.setAttribute('loading', 'eager'));
                    document.querySelectorAll('img[data-src]')
                        .forEach(img => {
                            if (img.dataset.src) img.src = img.dataset.src;
                        });
                }
            """)

            # Scroll through entire page to trigger intersection observers
            await page.evaluate("""
                async () => {
                    const delay = ms => new Promise(r => setTimeout(r, ms));
                    const height = document.body.scrollHeight;
                    const step = window.innerHeight;
                    for (let y = 0; y < height; y += step) {
                        window.scrollTo(0, y);
                        await delay(150);
                    }
                    // Scroll back to top
                    window.scrollTo(0, 0);
                }
            """)

            # Wait for any triggered network requests to settle
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                # networkidle may timeout on pages with persistent connections
                await page.wait_for_timeout(500)

        except Exception as e:
            logger.debug(f"Scroll-to-load failed (non-critical): {e}")
