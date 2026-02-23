"""Chrome DevTools MCP client wrapper for browser automation."""

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ElementScreenshot:
    """Result from an element-level screenshot."""
    element_type: str       # hero, h1, cta_primary, nav, footer, etc.
    uid: str                # MCP element uid
    file_path: str          # .tmp/screenshots/...
    base64_data: str        # PNG as base64
    selector_used: str      # CSS selector or a11y role used to find it


class MCPBrowserClient:
    """Manages a Chrome DevTools MCP server session for browser automation.

    Usage:
        async with MCPBrowserClient(audit_id="abc123") as browser:
            await browser.navigate("https://example.com")
            path, b64 = await browser.take_full_screenshot("https://example.com")
            snapshot = await browser.take_snapshot()
    """

    def __init__(self, audit_id: str, screenshot_dir: Optional[Path] = None):
        self.audit_id = audit_id
        self.screenshot_dir = screenshot_dir or Path(".tmp/screenshots") / audit_id
        self.mockup_dir = Path(".tmp/mockups") / audit_id
        self._session = None
        self._transport_ctx = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.disconnect()

    async def connect(self) -> None:
        """Start the MCP server process and establish connection."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.mockup_dir.mkdir(parents=True, exist_ok=True)

        server_params = StdioServerParameters(
            command="npx",
            args=["chrome-devtools-mcp@latest", "--headless", "--isolated"],
        )

        self._transport_ctx = stdio_client(server_params)
        read, write = await self._transport_ctx.__aenter__()

        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()

        logger.info(f"MCP browser client connected for audit {self.audit_id}")

    async def disconnect(self) -> None:
        """Close the MCP session and server process."""
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
                self._session = None
        except Exception as e:
            logger.debug(f"Session cleanup: {e}")
        try:
            if self._transport_ctx:
                await self._transport_ctx.__aexit__(None, None, None)
                self._transport_ctx = None
        except Exception as e:
            logger.debug(f"Transport cleanup: {e}")
        logger.info(f"MCP browser client disconnected for audit {self.audit_id}")

    async def _call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call an MCP tool and return the result."""
        if not self._session:
            raise RuntimeError("MCP session not connected")
        result = await self._session.call_tool(tool_name, arguments)
        # Check for MCP error responses
        if result and hasattr(result, "isError") and result.isError:
            error_text = ""
            if hasattr(result, "content") and result.content:
                error_text = " ".join(
                    getattr(b, "text", "") for b in result.content
                )
            raise RuntimeError(f"MCP tool '{tool_name}' failed: {error_text}")
        return result

    async def is_available(self) -> bool:
        """Check if the MCP session is connected and responsive."""
        if not self._session:
            return False
        try:
            await self._call_tool("list_pages", {})
            return True
        except Exception as e:
            logger.debug(f"MCP availability check failed: {e}")
            return False

    async def navigate(self, url: str, timeout: int = 30000) -> None:
        """Navigate to a URL and wait for load."""
        logger.debug(f"MCP navigating to: {url}")
        await self._call_tool("navigate_page", {
            "type": "url",
            "url": url,
            "timeout": timeout,
        })

    async def set_viewport(self, width: int = 1440, height: int = 900) -> None:
        """Set the browser viewport dimensions."""
        await self._call_tool("emulate", {
            "viewport": {"width": width, "height": height},
        })

    async def take_full_screenshot(
        self, url: str, filename_prefix: str = "full"
    ) -> tuple[str, str]:
        """Take a full-page screenshot. Returns (file_path, base64_data)."""
        safe_name = url.replace("://", "_").replace("/", "_").replace("?", "_")[:80]
        file_path = str(self.screenshot_dir / f"{filename_prefix}_{safe_name}.png")

        await self._call_tool("take_screenshot", {
            "fullPage": True,
            "filePath": file_path,
            "format": "png",
        })

        # Read the file back as base64
        try:
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
        except FileNotFoundError:
            logger.warning(f"Screenshot file not found at {file_path}, using empty base64")
            b64 = ""

        return file_path, b64

    async def take_snapshot(self, verbose: bool = False) -> Any:
        """Take an accessibility tree snapshot of the current page."""
        return await self._call_tool("take_snapshot", {
            "verbose": verbose,
        })

    async def take_element_screenshot(
        self, uid: str, element_type: str, filename_prefix: str = "element"
    ) -> Optional[ElementScreenshot]:
        """Take a screenshot of a specific element by its a11y uid."""
        file_path = str(
            self.screenshot_dir / f"{filename_prefix}_{element_type}.png"
        )

        try:
            await self._call_tool("take_screenshot", {
                "uid": uid,
                "filePath": file_path,
                "format": "png",
            })

            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            return ElementScreenshot(
                element_type=element_type,
                uid=uid,
                file_path=file_path,
                base64_data=b64,
                selector_used=f"uid:{uid}",
            )
        except Exception as e:
            logger.warning(f"Failed to screenshot element {element_type} (uid={uid}): {e}")
            return None

    async def evaluate_script(self, function_str: str) -> Any:
        """Execute arbitrary JavaScript on the page."""
        return await self._call_tool("evaluate_script", {
            "function": function_str,
        })

    async def screenshot_mockup_html(
        self, html_content: str, filename: str
    ) -> tuple[str, str]:
        """Write an HTML file, navigate to it, screenshot it, return (path, base64)."""
        mockup_path = self.mockup_dir / filename
        mockup_path.write_text(html_content, encoding="utf-8")

        file_url = mockup_path.resolve().as_uri()
        await self.navigate(file_url)
        await asyncio.sleep(0.5)

        screenshot_path = str(
            self.screenshot_dir / f"mockup_{filename.replace('.html', '.png')}"
        )
        await self._call_tool("take_screenshot", {
            "fullPage": False,
            "filePath": screenshot_path,
            "format": "png",
        })

        try:
            with open(screenshot_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
        except FileNotFoundError:
            b64 = ""

        return screenshot_path, b64
