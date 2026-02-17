"""Screenshot Agent — captures full-page and element-level screenshots via Chrome DevTools MCP."""

import asyncio
import logging
import re
import time
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.context_store import ScreenshotData
from agents.mcp_browser_client import MCPBrowserClient

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
        settings = get_settings()

        if not settings.screenshot_enabled:
            return {
                "score": None,
                "grade": None,
                "analysis_text": "Screenshot capture disabled in settings.",
                "recommendations": [],
                "result_data": {"total_screenshots": 0, "skipped": True},
            }

        await self.update_progress(5, "Connecting to Chrome DevTools MCP")

        pages_to_visit = self._prioritize_pages(settings.screenshot_max_pages)
        total_screenshots = 0
        element_screenshots = 0
        errors = []

        try:
            async with MCPBrowserClient(audit_id=self.context.audit_id) as browser:
                await browser.set_viewport(
                    settings.screenshot_viewport_width,
                    settings.screenshot_viewport_height,
                )
                await self.update_progress(10, "Browser connected")

                for i, (url, page_type) in enumerate(pages_to_visit):
                    pct = 10 + int((i / max(len(pages_to_visit), 1)) * 72)
                    await self.update_progress(
                        pct, f"Screenshotting {page_type} page ({i+1}/{len(pages_to_visit)})"
                    )

                    try:
                        await browser.navigate(url)
                        await asyncio.sleep(1.5)

                        # Full-page screenshot
                        file_path, b64 = await browser.take_full_screenshot(
                            url, filename_prefix=f"{page_type}_full"
                        )
                        if b64:
                            await self.context.set_screenshot(ScreenshotData(
                                url=url,
                                screenshot_type="full_page",
                                file_path=file_path,
                                base64_data=b64,
                                width=settings.screenshot_viewport_width,
                                page_type=page_type,
                                description=f"Full page screenshot of {page_type} page",
                                captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            ))
                            total_screenshots += 1

                        # Take accessibility snapshot for element discovery
                        snapshot = await browser.take_snapshot(verbose=True)

                        # Element-level screenshots
                        allowed_elements = PAGE_ELEMENT_MAP.get(page_type, DEFAULT_ELEMENTS)
                        for target in ELEMENT_TARGETS:
                            if target["type"] not in allowed_elements:
                                continue

                            elem_result = await self._capture_element(
                                browser, url, page_type, target, snapshot
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
                mobile_count = await self._capture_mobile_screenshot(browser, pages_to_visit)
                total_screenshots += mobile_count

        except Exception as e:
            logger.error(f"MCP browser client failed: {e}")
            return {
                "score": None,
                "grade": None,
                "analysis_text": (
                    f"Screenshot capture partially failed: {e}. "
                    f"Captured {total_screenshots} screenshots before error."
                ),
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
        browser: MCPBrowserClient,
        url: str,
        page_type: str,
        target: dict,
        snapshot: Any,
    ) -> Optional[ScreenshotData]:
        """Try to find and screenshot a target element using CSS selectors."""
        for selector in target["selectors"]:
            try:
                # Check element exists via JavaScript
                exists_result = await browser.evaluate_script(
                    f"() => {{ return document.querySelector('{selector}') !== null; }}"
                )
                if not self._result_truthy(exists_result):
                    continue

                # Find the uid in the accessibility snapshot
                uid = await self._find_uid_for_selector(browser, selector, snapshot)
                if not uid:
                    continue

                elem_shot = await browser.take_element_screenshot(
                    uid=uid,
                    element_type=target["type"],
                    filename_prefix=f"{page_type}_{target['type']}",
                )

                if elem_shot and elem_shot.base64_data:
                    screenshot_data = ScreenshotData(
                        url=url,
                        screenshot_type=target["type"],
                        file_path=elem_shot.file_path,
                        base64_data=elem_shot.base64_data,
                        element_selector=selector,
                        element_uid=uid,
                        page_type=page_type,
                        description=target["description"],
                        captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    )
                    await self.context.set_screenshot(screenshot_data)
                    return screenshot_data

            except Exception as e:
                logger.debug(f"Element capture failed for {target['type']} with {selector}: {e}")
                continue

        return None

    async def _find_uid_for_selector(
        self, browser: MCPBrowserClient, selector: str, snapshot: Any
    ) -> Optional[str]:
        """Find the MCP uid for a DOM element matching a CSS selector.

        Strategy: use snapshot text to find elements by role/tag, matched against
        the selector we're looking for.
        """
        if not snapshot or not hasattr(snapshot, "content") or not snapshot.content:
            return None

        snapshot_text = ""
        for block in snapshot.content:
            if hasattr(block, "text"):
                snapshot_text += block.text

        if not snapshot_text:
            return None

        # Map CSS selectors to what we expect in the a11y tree
        tag = selector.split("[")[0].split(":")[0].split(".")[0].split(">")[-1].strip()
        role_hints = {
            "nav": ["navigation"],
            "footer": ["contentinfo"],
            "h1": ["heading"],
            "h2": ["heading"],
            "form": ["form"],
            "button": ["button"],
            "a": ["link"],
        }

        search_terms = role_hints.get(tag, [])
        # Also look for class-based hints
        if "hero" in selector:
            search_terms.extend(["hero", "banner"])
        if "pricing" in selector:
            search_terms.extend(["pricing", "plans"])
        if "testimonial" in selector or "review" in selector:
            search_terms.extend(["testimonial", "review", "quote"])
        if "cta" in selector.lower() or "demo" in selector or "trial" in selector:
            search_terms.extend(["cta", "demo", "trial", "signup", "get started"])
        if "form" in selector:
            search_terms.extend(["form"])

        # Parse snapshot lines for uid matches
        for line in snapshot_text.split("\n"):
            line_lower = line.lower().strip()
            if not line_lower:
                continue

            for term in search_terms:
                if term in line_lower:
                    uid = self._extract_uid_from_line(line.strip())
                    if uid:
                        return uid

        return None

    def _extract_uid_from_line(self, line: str) -> Optional[str]:
        """Extract MCP uid from a snapshot line."""
        # Common patterns in MCP snapshots: [E123], uid="E123", E123
        match = re.search(r'\[([A-Z]\d+)\]', line)
        if match:
            return match.group(1)
        match = re.search(r'uid[=:]"?([A-Z]\d+)"?', line)
        if match:
            return match.group(1)
        # Pattern: starts with uid like "E12 - heading"
        match = re.match(r'^([A-Z]\d+)\s', line)
        if match:
            return match.group(1)
        return None

    def _result_truthy(self, result: Any) -> bool:
        """Check if an MCP tool result is truthy."""
        if not result or not hasattr(result, "content") or not result.content:
            return False
        for block in result.content:
            if hasattr(block, "text"):
                text = block.text.lower().strip()
                if text in ("false", "null", "undefined", "none", ""):
                    return False
                return True
        return False

    async def _capture_mobile_screenshot(
        self, browser: MCPBrowserClient, pages: list[tuple[str, str]]
    ) -> int:
        """Capture mobile-viewport screenshot of homepage. Returns count captured."""
        if not pages:
            return 0

        url, page_type = pages[0]
        try:
            await browser.set_viewport(375, 812)
            await browser.navigate(url)
            await asyncio.sleep(1)

            file_path, b64 = await browser.take_full_screenshot(
                url, filename_prefix="mobile_home"
            )
            if b64:
                await self.context.set_screenshot(ScreenshotData(
                    url=url,
                    screenshot_type="mobile_full",
                    file_path=file_path,
                    base64_data=b64,
                    width=375,
                    page_type="home",
                    description="Mobile viewport screenshot of homepage",
                    captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ))

                # Reset viewport to desktop
                from config.settings import get_settings
                settings = get_settings()
                await browser.set_viewport(
                    settings.screenshot_viewport_width,
                    settings.screenshot_viewport_height,
                )
                return 1
        except Exception as e:
            logger.warning(f"Mobile screenshot failed: {e}")
        return 0
