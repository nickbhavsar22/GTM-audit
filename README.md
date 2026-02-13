# GTM Audit Platform

AI-powered Go-To-Market audit tool for B2B SaaS companies. Analyzes websites, messaging, SEO, competitive positioning, and more — then generates a scored report with actionable recommendations.

Built by [Bhavsar Growth Consulting](https://www.bhavsargrowth.com).

## Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit | Interactive UI (submit audits, view reports) |
| Backend | FastAPI | REST API + WebSocket for real-time progress |
| Database | SQLite (dev) / PostgreSQL (prod) | Audit state, agent results, reports |
| Agents | 11 specialist agents + orchestrator | Parallel analysis via Claude API |
| Reports | Jinja2 HTML + Markdown | Branded, downloadable audit reports |

## Quick Start

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Local Development

```bash
# Clone and set up
git clone https://github.com/nickbhavsar22/GTM-audit.git
cd GTM-audit
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

# Run (two terminals)
uvicorn backend.main:app --reload          # Terminal 1: API server
streamlit run frontend/streamlit_app.py    # Terminal 2: UI
```

### Docker

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
docker-compose up
```

The UI will be available at `http://localhost:8501` and the API at `http://localhost:8000`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_PASSWORD` | Yes | `changeme` | Password for the login screen |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key for LLM-powered analysis |
| `DEBUG` | No | `false` | Enable debug logging |
| `DATABASE_URL` | No | `sqlite:///./gtm_audit.db` | Database connection string |
| `LLM_MODEL` | No | `claude-sonnet-4-5-20250929` | Claude model to use |
| `LLM_MAX_TOKENS` | No | `8000` | Max tokens per LLM call |
| `MAX_PAGES_FULL` | No | `30` | Pages to crawl for full audit |
| `MAX_PAGES_QUICK` | No | `10` | Pages to crawl for quick audit |
| `AUDIT_TIMEOUT_MINUTES` | No | `45` | Audit timeout |
| `RATE_LIMIT_PER_HOUR` | No | `5` | Max audits per hour per client |

> **Security note:** Change `APP_PASSWORD` from the default before deploying. Never commit `.env` to version control.

## Project Structure

```
GTM-audit/
├── agents/              # 11 specialist agents + orchestrator
│   ├── data_providers/  # Mock data providers (SEMrush, Crunchbase, G2)
│   ├── base_agent.py    # Abstract base class for agents
│   ├── orchestrator.py  # Coordinates agent execution
│   └── llm_client.py    # Async Claude API wrapper
├── backend/
│   ├── models/          # SQLAlchemy ORM models
│   ├── routers/         # FastAPI route handlers
│   ├── middleware/       # Auth, rate limiting
│   ├── services/        # Business logic (audit, report)
│   └── main.py          # FastAPI app factory
├── config/              # Settings, constants, logging
├── frontend/
│   ├── components/      # Streamlit UI components
│   ├── pages/           # Multi-page app pages
│   ├── assets/          # CSS, images
│   └── streamlit_app.py # Streamlit entry point
├── reports/
│   ├── templates/       # Jinja2 HTML templates
│   ├── renderer.py      # HTML report renderer
│   └── scoring.py       # Scoring engine
└── tests/               # Pytest test suite
```

## Running Tests

```bash
pytest tests/ -v
```

## License

Proprietary — Bhavsar Growth Consulting.
