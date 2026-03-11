"""Tests for the AEO (Answer Engine Optimization) Agent deterministic checks."""

import pytest
from agents.aeo_agent import AEOAgent
from agents.context_store import PageData


def _make_page(**kwargs) -> PageData:
    """Create a PageData with sensible defaults, overriding with kwargs."""
    defaults = {
        "url": "https://example.com",
        "title": "Example Page",
        "meta_description": "A good meta description that is between one hundred twenty and one hundred sixty characters long for optimal AI engine extraction.",
        "h1_tags": ["Example Heading"],
        "h2_tags": [],
        "h3_tags": [],
        "raw_text": "Some content",
        "html": "<html><body><h1>Example</h1></body></html>",
        "page_type": "home",
        "content_type": "",
        "has_schema": False,
        "schema_types": [],
        "images": [],
        "word_count": 500,
    }
    defaults.update(kwargs)
    return PageData(**defaults)


class TestCheckSchemaMarkup:
    """Tests for _check_schema_markup deterministic check."""

    def test_no_schema(self):
        pages = [_make_page(html="<html><body>No schema</body></html>")]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_schema_markup(pages)

        assert result["pass"] is False
        assert result["pages_with_json_ld"] == 0
        assert result["total_pages"] == 1

    def test_json_ld_present(self):
        html = '''<html><head>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "Organization", "name": "Test Co"}
        </script>
        </head><body>Content</body></html>'''
        pages = [_make_page(html=html, has_schema=True, schema_types=["Organization"])]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_schema_markup(pages)

        assert result["pass"] is True
        assert result["pages_with_json_ld"] == 1
        assert "Organization" in result["schema_types_found"]

    def test_missing_recommended_types(self):
        html = '''<html><head>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "Organization", "name": "Test"}
        </script>
        </head><body></body></html>'''
        pages = [_make_page(html=html)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_schema_markup(pages)

        assert "FAQPage" in result["missing_recommended_types"]
        assert "Article" in result["missing_recommended_types"]
        assert "HowTo" in result["missing_recommended_types"]

    def test_multiple_schema_types(self):
        html = '''<html><head>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "Organization", "name": "Test"}
        </script>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}
        </script>
        </head><body></body></html>'''
        pages = [_make_page(html=html)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_schema_markup(pages)

        assert "Organization" in result["schema_types_found"]
        assert "FAQPage" in result["schema_types_found"]
        assert "FAQPage" not in result["missing_recommended_types"]


class TestCheckTableOfContents:
    """Tests for _check_table_of_contents deterministic check."""

    def test_no_blog_pages(self):
        pages = [_make_page(page_type="home")]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_table_of_contents(pages)

        assert result["total_blog_pages"] == 0
        assert result["pass"] is True  # No blog pages = pass

    def test_blog_without_toc(self):
        pages = [_make_page(
            url="https://example.com/blog/post-1",
            page_type="blog",
            html="<html><body><h1>Blog Post</h1><p>Content</p></body></html>",
        )]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_table_of_contents(pages)

        assert result["total_blog_pages"] == 1
        assert result["blog_pages_with_toc"] == 0
        assert result["pass"] is False

    def test_blog_with_toc_id(self):
        html = '''<html><body>
        <div id="table-of-contents">
            <ul><li><a href="#section1">Section 1</a></li></ul>
        </div>
        <h2 id="section1">Section 1</h2>
        </body></html>'''
        pages = [_make_page(url="https://example.com/blog/post-1", page_type="blog", html=html)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_table_of_contents(pages)

        assert result["blog_pages_with_toc"] == 1
        assert result["pass"] is True

    def test_blog_with_anchor_links(self):
        html = '''<html><body>
        <ul>
            <li><a href="#intro">Introduction</a></li>
            <li><a href="#method">Methodology</a></li>
            <li><a href="#results">Results</a></li>
        </ul>
        </body></html>'''
        pages = [_make_page(url="https://example.com/blog/post-1", page_type="blog", html=html)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_table_of_contents(pages)

        assert result["blog_pages_with_toc"] == 1

    def test_url_based_blog_detection(self):
        """Pages with /blog/ in URL should be detected even without page_type."""
        pages = [_make_page(
            url="https://example.com/blog/some-article",
            page_type="",
            html="<html><body><p>Content</p></body></html>",
        )]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_table_of_contents(pages)

        assert result["total_blog_pages"] == 1


class TestCheckAltText:
    """Tests for _check_alt_text deterministic check."""

    def test_no_images(self):
        pages = [_make_page(images=[])]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_alt_text(pages)

        assert result["total_images"] == 0
        assert result["pass"] is False  # 0/0 = 0% coverage, below 80% threshold

    def test_all_images_have_alt(self):
        images = [
            {"src": "img1.png", "alt": "A descriptive alt text for image one"},
            {"src": "img2.png", "alt": "Another descriptive alt text for image two"},
        ]
        pages = [_make_page(images=images)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_alt_text(pages)

        assert result["images_with_alt"] == 2
        assert result["images_with_descriptive_alt"] == 2
        assert result["coverage_percentage"] == 100.0
        assert result["pass"] is True

    def test_missing_alt_text(self):
        images = [
            {"src": "img1.png", "alt": "Good description"},
            {"src": "img2.png", "alt": ""},
            {"src": "img3.png"},  # No alt key at all
        ]
        pages = [_make_page(images=images)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_alt_text(pages)

        assert result["images_with_alt"] == 1
        assert result["total_images"] == 3
        assert result["pass"] is False

    def test_filename_alt_not_descriptive(self):
        """Alt text like 'img_001.png' should not count as descriptive."""
        images = [{"src": "img.png", "alt": "img_001.png"}]
        pages = [_make_page(images=images)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_alt_text(pages)

        assert result["images_with_alt"] == 1
        assert result["images_with_descriptive_alt"] == 0


class TestCheckQuestionHeadings:
    """Tests for _check_question_headings deterministic check."""

    def test_no_headings(self):
        pages = [_make_page(h2_tags=[], h3_tags=[])]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_question_headings(pages)

        assert result["total_headings"] == 0

    def test_question_headings_detected(self):
        pages = [_make_page(
            h2_tags=["How does pricing work?", "Our Features", "What makes us different?"],
            h3_tags=["Why choose us?", "Product Details"],
        )]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_question_headings(pages)

        assert result["question_headings_count"] == 3
        assert result["total_headings"] == 5
        assert result["percentage"] == 60.0
        assert result["pass"] is True

    def test_question_mark_detection(self):
        """Headings ending with ? should be detected even without question words."""
        pages = [_make_page(h2_tags=["Ready to get started?", "Features"])]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_question_headings(pages)

        assert result["question_headings_count"] == 1

    def test_below_threshold(self):
        pages = [_make_page(
            h2_tags=["Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5",
                      "Feature 6", "Feature 7", "Feature 8", "Feature 9", "How it works?"],
        )]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_question_headings(pages)

        assert result["percentage"] == 10.0
        assert result["pass"] is False  # Below 20% threshold


class TestCheckFAQSections:
    """Tests for _check_faq_sections deterministic check."""

    def test_no_faq(self):
        pages = [_make_page(html="<html><body>No FAQ here</body></html>")]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_faq_sections(pages)

        assert result["pages_with_faq"] == 0
        assert result["pass"] is False

    def test_faq_schema_detected(self):
        html = '''<html><head>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}
        </script>
        </head><body></body></html>'''
        pages = [_make_page(html=html)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_faq_sections(pages)

        assert result["pages_with_faq"] == 1
        assert result["has_faq_schema"] is True
        assert result["pass"] is True

    def test_faq_heading_detected(self):
        pages = [_make_page(h2_tags=["Frequently Asked Questions"])]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_faq_sections(pages)

        assert result["pages_with_faq"] == 1
        assert result["pass"] is True

    def test_details_summary_detected(self):
        html = '''<html><body>
        <details><summary>Question 1</summary><p>Answer 1</p></details>
        </body></html>'''
        pages = [_make_page(html=html)]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_faq_sections(pages)

        assert result["pages_with_faq"] == 1


class TestCheckMetaDescriptions:
    """Tests for _check_meta_descriptions deterministic check."""

    def test_all_have_meta(self):
        pages = [
            _make_page(meta_description="A" * 140),
            _make_page(meta_description="B" * 130),
        ]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_meta_descriptions(pages)

        assert result["pages_with_meta"] == 2
        assert result["pages_with_good_length"] == 2
        assert result["pass"] is True

    def test_missing_meta(self):
        pages = [
            _make_page(meta_description="Good meta description here"),
            _make_page(meta_description=""),
            _make_page(meta_description=""),
        ]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_meta_descriptions(pages)

        assert result["pages_with_meta"] == 1
        assert result["coverage_percentage"] == pytest.approx(33.3, abs=0.1)
        assert result["pass"] is False

    def test_suboptimal_length(self):
        pages = [_make_page(meta_description="Too short")]
        agent = AEOAgent.__new__(AEOAgent)
        result = agent._check_meta_descriptions(pages)

        assert result["pages_with_meta"] == 1
        assert result["pages_with_good_length"] == 0


class TestFallbackAnalysis:
    """Tests for _fallback_analysis when LLM is unavailable."""

    def test_fallback_returns_valid_structure(self):
        agent = AEOAgent.__new__(AEOAgent)
        checks = {
            "schema_markup": {
                "pages_with_json_ld": 0, "total_pages": 3,
                "schema_types_found": [], "missing_recommended_types": ["FAQPage", "Article"],
                "pass": False,
            },
            "table_of_contents": {
                "blog_pages_with_toc": 0, "total_blog_pages": 2, "pass": False,
            },
            "alt_text": {
                "images_with_alt": 5, "total_images": 10,
                "images_with_descriptive_alt": 3, "coverage_percentage": 50.0, "pass": False,
            },
            "question_headings": {
                "question_headings_count": 1, "total_headings": 10,
                "percentage": 10.0, "examples": ["How does it work?"], "pass": False,
            },
            "faq_sections": {
                "pages_with_faq": 0, "has_faq_schema": False, "pass": False,
            },
            "meta_descriptions": {
                "pages_with_meta": 2, "total_pages": 3,
                "pages_with_good_length": 1, "coverage_percentage": 66.7, "pass": False,
            },
        }

        result = agent._fallback_analysis(checks)

        # Verify required keys
        assert "score" in result
        assert "grade" in result
        assert "analysis_text" in result
        assert "recommendations" in result
        assert "result_data" in result
        assert isinstance(result["score"], (int, float))
        assert 0 <= result["score"] <= 100
        assert result["grade"] is None
        assert result["result_data"]["fallback"] is True
        assert "automated_checks" in result["result_data"]
        assert len(result["result_data"]["score_items"]) >= 4

    def test_fallback_score_reflects_checks(self):
        """A site with all checks passing should score higher than one with all failing."""
        agent = AEOAgent.__new__(AEOAgent)

        good_checks = {
            "schema_markup": {
                "pages_with_json_ld": 5, "total_pages": 5,
                "schema_types_found": ["Organization", "FAQPage", "Article"],
                "missing_recommended_types": [], "pass": True,
            },
            "table_of_contents": {
                "blog_pages_with_toc": 3, "total_blog_pages": 3, "pass": True,
            },
            "alt_text": {
                "images_with_alt": 10, "total_images": 10,
                "images_with_descriptive_alt": 10, "coverage_percentage": 100.0, "pass": True,
            },
            "question_headings": {
                "question_headings_count": 8, "total_headings": 20,
                "percentage": 40.0, "examples": [], "pass": True,
            },
            "faq_sections": {
                "pages_with_faq": 2, "has_faq_schema": True, "pass": True,
            },
            "meta_descriptions": {
                "pages_with_meta": 5, "total_pages": 5,
                "pages_with_good_length": 5, "coverage_percentage": 100.0, "pass": True,
            },
        }

        bad_checks = {
            "schema_markup": {
                "pages_with_json_ld": 0, "total_pages": 5,
                "schema_types_found": [], "missing_recommended_types": ["FAQPage"],
                "pass": False,
            },
            "table_of_contents": {
                "blog_pages_with_toc": 0, "total_blog_pages": 3, "pass": False,
            },
            "alt_text": {
                "images_with_alt": 0, "total_images": 10,
                "images_with_descriptive_alt": 0, "coverage_percentage": 0.0, "pass": False,
            },
            "question_headings": {
                "question_headings_count": 0, "total_headings": 20,
                "percentage": 0.0, "examples": [], "pass": False,
            },
            "faq_sections": {
                "pages_with_faq": 0, "has_faq_schema": False, "pass": False,
            },
            "meta_descriptions": {
                "pages_with_meta": 0, "total_pages": 5,
                "pages_with_good_length": 0, "coverage_percentage": 0.0, "pass": False,
            },
        }

        good_result = agent._fallback_analysis(good_checks)
        bad_result = agent._fallback_analysis(bad_checks)

        assert good_result["score"] > bad_result["score"]
        assert good_result["score"] > 70
        assert bad_result["score"] < 20


class TestRunAutomatedChecks:
    """Tests for _run_automated_checks combining all checks."""

    def test_returns_all_check_categories(self):
        agent = AEOAgent.__new__(AEOAgent)

        # Mock context with pages
        class MockContext:
            pages = {
                "https://example.com": _make_page(),
                "https://example.com/blog/post": _make_page(
                    url="https://example.com/blog/post",
                    page_type="blog",
                    h2_tags=["How does this work?", "Features"],
                ),
            }

        agent.context = MockContext()
        result = agent._run_automated_checks()

        assert "schema_markup" in result
        assert "table_of_contents" in result
        assert "alt_text" in result
        assert "question_headings" in result
        assert "faq_sections" in result
        assert "meta_descriptions" in result
