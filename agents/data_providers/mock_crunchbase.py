"""Mock Crunchbase data provider for development."""

import hashlib
from typing import Any

from agents.data_providers.base_provider import BaseDataProvider


class MockCrunchbaseProvider(BaseDataProvider):
    """Returns plausible company data based on the domain."""

    @property
    def provider_name(self) -> str:
        return "crunchbase_mock"

    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        seed = int(hashlib.md5(company_url.encode()).hexdigest()[:8], 16)

        funding_stages = ["Seed", "Series A", "Series B", "Series C", "Series D"]
        stage_idx = seed % len(funding_stages)

        return {
            "funding_stage": funding_stages[stage_idx],
            "total_funding": f"${(seed % 200) + 5}M",
            "employee_count": f"{50 + (seed % 950)}",
            "founded_year": 2015 + (seed % 8),
            "headquarters": "San Francisco, CA",
            "categories": ["SaaS", "B2B", "Enterprise Software"],
            "investors": [
                "Venture Capital Firm",
                "Angel Investor Group",
            ],
            "_source": "mock",
            "_note": "This is mock data. Replace with real Crunchbase API for production.",
        }
