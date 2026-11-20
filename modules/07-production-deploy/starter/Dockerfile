# Small, non-root image for the agent service. Build from this folder:
#   docker build -t course-agent:dev .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Create an unprivileged user first.
RUN useradd --create-home --uid 10001 appuser

# Install dependencies before copying code, so code edits do not reinstall packages.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY service.py .

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

# Secrets such as SERVICE_API_KEY and LLM_API_KEY are passed at runtime with -e or a secret store.
CMD ["uvicorn", "--factory", "service:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
