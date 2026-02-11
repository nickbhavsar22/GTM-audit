# GTM Audit Platform — Multi-stage Docker build

FROM python:3.11-slim as base

WORKDIR /app

# System dependencies for Playwright and Weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium && playwright install-deps chromium

# Copy application
COPY . .

# Create temp directory
RUN mkdir -p .tmp

# Expose ports (FastAPI + Streamlit)
EXPOSE 8000 8501

# Default: run both backend and frontend
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0"]
