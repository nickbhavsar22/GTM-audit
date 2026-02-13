# Changelog

## [0.1.0] - 2025-05-01

### Added
- 11 specialist AI agents (SEO, messaging, visual design, competitor, ICP, conversion, social, review sentiment, company research, web scraper, report)
- Orchestrator for parallel agent execution
- FastAPI backend with REST API and WebSocket progress updates
- Streamlit frontend with login, audit submission, progress dashboard, report viewer, and audit history
- Quick Audit (10-15 min) and Full Audit (30-45 min) modes
- HTML and Markdown report generation with Jinja2 templates
- SQLite database with SQLAlchemy ORM (Audit, AgentResult, Report, UserSession)
- Mock data providers for SEMrush, Crunchbase, and G2
- Password authentication for UI and API
- Rate limiting on audit creation endpoint
- BGC brand styling with dark theme
