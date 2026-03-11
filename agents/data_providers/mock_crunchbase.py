"""Mock Crunchbase data provider for development."""

from typing import Any

from agents.data_providers.base_provider import BaseDataProvider


class MockCrunchbaseProvider(BaseDataProvider):
    """Placeholder for Crunchbase API integration. Returns unavailable signal."""

    @property
    def provider_name(self) -> str:
        return "crunchbase_mock"

    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        return {
            "_source": "unavailable",
            "_note": "Crunchbase API not configured. No company data available.",
        }
