"""Mock SEMrush data provider for development."""

from typing import Any

from agents.data_providers.base_provider import BaseDataProvider


class MockSEMrushProvider(BaseDataProvider):
    """Placeholder for SEMrush API integration. Returns unavailable signal."""

    @property
    def provider_name(self) -> str:
        return "semrush_mock"

    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        return {
            "_source": "unavailable",
            "_note": "SEMrush API not configured. No SEO metrics available.",
        }
