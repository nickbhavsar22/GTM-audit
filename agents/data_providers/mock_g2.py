"""Mock G2/Capterra review data provider for development."""

import hashlib
from typing import Any

from agents.data_providers.base_provider import BaseDataProvider


class MockG2Provider(BaseDataProvider):
    """Returns plausible review data based on the domain."""

    @property
    def provider_name(self) -> str:
        return "g2_mock"

    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        seed = int(hashlib.md5(company_url.encode()).hexdigest()[:8], 16)

        return {
            "overall_rating": 3.5 + (seed % 15) / 10,  # 3.5 - 5.0
            "total_reviews": 20 + (seed % 500),
            "recommendation_rate": 70 + (seed % 30),  # 70-100%
            "categories": {
                "ease_of_use": 3.0 + (seed % 20) / 10,
                "quality_of_support": 3.0 + (seed % 20) / 10,
                "ease_of_setup": 3.0 + (seed % 20) / 10,
                "meets_requirements": 3.5 + (seed % 15) / 10,
            },
            "positive_themes": [
                "Easy to use interface",
                "Great customer support",
                "Powerful features",
            ],
            "negative_themes": [
                "Pricing could be more competitive",
                "Learning curve for advanced features",
            ],
            "competitor_comparison": {
                "wins_against": ["Competitor A", "Competitor B"],
                "loses_against": ["Competitor C"],
            },
            "_source": "mock",
            "_note": "This is mock data. Replace with real G2 API for production.",
        }
