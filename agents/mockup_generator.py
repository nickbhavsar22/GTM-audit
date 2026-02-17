"""Mockup generator — creates styled HTML mockups for before/after comparisons."""

import logging
import time
from typing import Optional

from agents.context_store import ContextStore, ScreenshotData
from agents.mcp_browser_client import MCPBrowserClient

logger = logging.getLogger(__name__)


class MockupGenerator:
    """Generates HTML mockups that mimic the original page style,
    then screenshots them for before/after report comparisons."""

    def __init__(self, context: ContextStore, browser: Optional[MCPBrowserClient] = None):
        self.context = context
        self.browser = browser

    def generate_headline_mockup_html(
        self,
        suggested_h1: str,
        suggested_subheadline: str = "",
    ) -> str:
        """Generate HTML that shows the suggested headline in a modern B2B SaaS style."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .mockup-container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 60px 40px;
            text-align: center;
        }}
        .mockup-label {{
            display: inline-block;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 3px;
            color: #575ECF;
            margin-bottom: 28px;
            padding: 6px 16px;
            border: 1px solid rgba(87, 94, 207, 0.3);
            border-radius: 20px;
            background: rgba(87, 94, 207, 0.08);
        }}
        h1 {{
            font-size: 2.75rem;
            font-weight: 800;
            line-height: 1.15;
            margin-bottom: 20px;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .subheadline {{
            font-size: 1.2rem;
            color: #94a3b8;
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
        }}
        .cta-button {{
            display: inline-block;
            margin-top: 36px;
            padding: 14px 36px;
            background: linear-gradient(135deg, #575ECF 0%, #6C73E0 100%);
            color: white;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            text-decoration: none;
            box-shadow: 0 4px 14px rgba(87, 94, 207, 0.4);
        }}
    </style>
</head>
<body>
    <div class="mockup-container">
        <div class="mockup-label">Suggested Improvement</div>
        <h1>{suggested_h1}</h1>
        {f'<p class="subheadline">{suggested_subheadline}</p>' if suggested_subheadline else ''}
        <a class="cta-button" href="#">Get Started</a>
    </div>
</body>
</html>"""

    def generate_cta_mockup_html(
        self,
        suggested_cta_text: str,
        suggested_supporting_text: str = "",
    ) -> str:
        """Generate HTML that shows a suggested CTA button design."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 250px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .mockup-container {{
            text-align: center;
            padding: 40px;
        }}
        .mockup-label {{
            display: inline-block;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 3px;
            color: #575ECF;
            margin-bottom: 24px;
            padding: 6px 16px;
            border: 1px solid rgba(87, 94, 207, 0.3);
            border-radius: 20px;
            background: rgba(87, 94, 207, 0.08);
        }}
        .cta-button {{
            display: inline-block;
            padding: 16px 40px;
            background: linear-gradient(135deg, #575ECF 0%, #6C73E0 100%);
            color: white;
            border-radius: 8px;
            font-size: 1.1rem;
            font-weight: 700;
            text-decoration: none;
            box-shadow: 0 4px 14px rgba(87, 94, 207, 0.4);
            transition: transform 0.2s;
        }}
        .supporting-text {{
            margin-top: 12px;
            font-size: 0.85rem;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="mockup-container">
        <div class="mockup-label">Suggested CTA</div>
        <a class="cta-button" href="#">{suggested_cta_text}</a>
        {f'<p class="supporting-text">{suggested_supporting_text}</p>' if suggested_supporting_text else ''}
    </div>
</body>
</html>"""

    async def generate_and_screenshot_mockup(
        self,
        html_content: str,
        mockup_name: str,
        recommendation_ref: str,
    ) -> Optional[ScreenshotData]:
        """Write HTML mockup, screenshot it, return ScreenshotData."""
        if not self.browser:
            logger.warning("No browser client available for mockup screenshots")
            return None

        try:
            file_path, b64 = await self.browser.screenshot_mockup_html(
                html_content, f"{mockup_name}.html"
            )

            if not b64:
                return None

            screenshot = ScreenshotData(
                url=f"mockup://{mockup_name}",
                screenshot_type="mockup",
                file_path=file_path,
                base64_data=b64,
                description=f"Mockup: {recommendation_ref}",
                mockup_for=recommendation_ref,
                captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
            await self.context.set_screenshot(screenshot)
            return screenshot
        except Exception as e:
            logger.warning(f"Mockup screenshot failed for {mockup_name}: {e}")
            return None
