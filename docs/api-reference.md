# REST API reference

When running the web app or backend API server, you can integrate Data
Detective into your own applications.

## Endpoints

**POST /api/analyze** – Analyze a CSV file, return JSON report
```bash
curl -F "file=@data.csv" "http://localhost:8000/api/analyze?outlier_method=mad"
```
Response: JSON object with all profiling data (see the Python example below).
Optionally accepts a second file field, `rules_file`, overriding health-score
weights and severities; see [health score rules](rules-contract.md).

**POST /api/analyze/html** – Analyze a CSV file, return standalone HTML report
```bash
curl -F "file=@data.csv" "http://localhost:8000/api/analyze/html" > report.html
```
Response: A self-contained HTML file (no external dependencies).

**POST /api/analyze/markdown** – Analyze a CSV file, return a Markdown report
```bash
curl -F "file=@data.csv" "http://localhost:8000/api/analyze/markdown" > report.md
```
Response: Markdown text, suitable for pasting into a PR comment, CI summary, or Slack message.

**GET /api/health** – Health check
```bash
curl http://localhost:8000/api/health
```
Response: `{"status": "ok", "version": "x.y.z"}` (matches the installed package version)

## Rate limiting

The three `/api/analyze*` endpoints are limited to 60 requests per minute
per client IP (`/api/health` is exempt, so health checks always succeed).
Exceeding it returns `429 Too Many Requests` with a `Retry-After` header
telling you how many seconds to wait:

```bash
curl -i -F "file=@data.csv" "http://localhost:8000/api/analyze"
# HTTP/1.1 429 Too Many Requests
# retry-after: 42
```

This is in-memory and per-process: it resets on restart and doesn't
coordinate across multiple replicas behind a load balancer. Fine for the
single-container deployment this project ships (see [docker-compose.yml](../docker-compose.yml)); if you're running several replicas behind a shared proxy, put a real rate limiter (or your proxy's own) in front instead.

## Python example

```python
import requests

with open("mydata.csv", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/analyze",
        files={"file": f},
        params={"outlier_method": "mad"}
    )

report = response.json()
print(f"Shape: {report['shape']}")
print(f"Insights: {report['insights']}")
print(f"Outliers detected: {report['outliers_mad']}")
```

## JavaScript example

```javascript
const formData = new FormData();
formData.append("file", csvFile); // File object from input[type=file]

const response = await fetch("/api/analyze?outlier_method=mad", {
  method: "POST",
  body: formData
});

const report = await response.json();
console.log(report.insights);
```

Full interactive API documentation is available at `/docs` (Swagger UI) when
the backend is running.
