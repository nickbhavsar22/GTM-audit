"""Mock G2/Capterra review data provider for development."""

from typing import Any

from agents.data_providers.base_provider import BaseDataProvider


class MockG2Provider(BaseDataProvider):
    """Placeholder for G2 API integration. Returns unavailable signal."""

    @property
    def provider_name(self) -> str:
        return "g2_mock"

    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        return {
            "_source": "unavailable",
            "_note": "G2 API not configured. No review data available.",
        }
