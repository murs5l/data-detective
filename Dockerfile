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

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
