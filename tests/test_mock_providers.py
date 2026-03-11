"""Tests for mock data providers — verify they return unavailable, not fabricated data."""

import asyncio

from agents.data_providers.mock_semrush import MockSEMrushProvider
from agents.data_providers.mock_crunchbase import MockCrunchbaseProvider
from agents.data_providers.mock_g2 import MockG2Provider


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_mock_semrush_returns_unavailable():
    provider = MockSEMrushProvider()
    data = _run(provider.get_data("https://www.redoak.com"))
    assert data["_source"] == "unavailable"
    assert "organic_traffic" not in data
    assert "domain_authority" not in data
    assert "keyword_count" not in data


def test_mock_crunchbase_returns_unavailable():
    provider = MockCrunchbaseProvider()
    data = _run(provider.get_data("https://www.redoak.com"))
    assert data["_source"] == "unavailable"
    assert "categories" not in data
    assert "headquarters" not in data
    assert "funding_stage" not in data


def test_mock_g2_returns_unavailable():
    provider = MockG2Provider()
    data = _run(provider.get_data("https://www.redoak.com"))
    assert data["_source"] == "unavailable"
    assert "total_reviews" not in data
    assert "overall_rating" not in data
    assert "recommendation_rate" not in data
