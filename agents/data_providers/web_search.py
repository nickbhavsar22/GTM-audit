"""Claude-powered web search synthesis provider."""

from typing import Any

from agents.data_providers.base_provider import BaseDataProvider


class WebSearchProvider(BaseDataProvider):
    """Uses Claude to synthesize company information from scraped content.

    Since we don't have real search API access, this provider
    analyzes the already-scraped website content to infer company details.
    """

    @property
    def provider_name(self) -> str:
        return "web_search_claude"

    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        """Placeholder — actual implementation uses Claude in the agent."""
        return {
            "company_url": company_url,
            "_source": "web_search_claude",
        }
