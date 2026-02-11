"""Mock SEMrush data provider for development."""

import hashlib
from typing import Any

from agents.data_providers.base_provider import BaseDataProvider


class MockSEMrushProvider(BaseDataProvider):
    """Returns plausible SEO metrics based on the domain."""

    @property
    def provider_name(self) -> str:
        return "semrush_mock"

    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        # Use URL hash to generate consistent but varied mock data
        seed = int(hashlib.md5(company_url.encode()).hexdigest()[:8], 16)

        return {
            "organic_traffic": 5000 + (seed % 50000),
            "keyword_count": 100 + (seed % 2000),
            "domain_authority": 20 + (seed % 60),
            "top_keywords": [
                {
                    "keyword": f"b2b {company_url.split('.')[0].split('//')[-1]} software",
                    "position": 5 + (seed % 20),
                    "volume": 500 + (seed % 5000),
                },
                {
                    "keyword": f"best {company_url.split('.')[0].split('//')[-1]} alternative",
                    "position": 8 + (seed % 30),
                    "volume": 300 + (seed % 3000),
                },
            ],
            "backlinks": 500 + (seed % 10000),
            "referring_domains": 30 + (seed % 500),
            "page_speed_score": 40 + (seed % 60),
            "_source": "mock",
            "_note": "This is mock data. Replace with real SEMrush API for production.",
        }
