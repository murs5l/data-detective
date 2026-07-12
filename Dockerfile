# --- Stage 1: build the Go fastscan speed layer ---
FROM golang:1.22-alpine AS fastscan-build
WORKDIR /src
COPY tools/fastscan/ .
RUN go build -o /out/fastscan .

# --- Stage 2: Python runtime serving the API + frontend ---
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[api]"

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY --from=fastscan-build /out/fastscan ./backend/bin/fastscan
RUN chmod +x ./backend/bin/fastscan

# Run as an unprivileged user; the app only reads its own files and writes
# to short-lived temp files, so it never needs root.
RUN useradd --create-home --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=2)" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
