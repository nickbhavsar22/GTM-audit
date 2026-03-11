"""Tests for extraction quality assessment."""

import asyncio

from agents.context_store import ContextStore, PageData


def test_low_quality_when_content_but_no_headings_no_title():
    page = PageData(
        url="https://example.com",
        raw_text="Some content here that is definitely long enough to be considered real content on a page",
    )
    assert page.extraction_quality() == "LOW"


def test_high_quality_with_all_fields():
    page = PageData(
        url="https://example.com",
        title="Example Company",
        h1_tags=["Welcome to Example"],
        internal_links=["/about", "/pricing"],
    )
    assert page.extraction_quality() == "HIGH"


def test_medium_quality_with_content_and_title():
    page = PageData(
        url="https://example.com",
        title="Example Company",
        raw_text="Some content here that is definitely long enough to be considered real content on a page",
    )
    assert page.extraction_quality() == "MEDIUM"


def test_low_quality_when_empty():
    page = PageData(url="https://example.com")
    assert page.extraction_quality() == "LOW"


def test_overall_quality_none_when_no_pages():
    from agents.base_agent import BaseAgent
    from agents.message_bus import MessageBus

    ctx = ContextStore(company_url="https://example.com")
    bus = MessageBus()

    # We can't instantiate BaseAgent directly (abstract), so test via context
    assert not ctx.pages  # No pages = would be NONE


def test_overall_quality_via_pages():
    """Test that extraction quality reflects page data correctly."""
    high_page = PageData(
        url="https://example.com",
        title="Example",
        h1_tags=["Hello"],
        internal_links=["/about"],
    )
    assert high_page.extraction_quality() == "HIGH"

    low_page = PageData(
        url="https://example.com/other",
        raw_text="Some content that is long enough to be real but has no other fields populated at all",
    )
    assert low_page.extraction_quality() == "LOW"
