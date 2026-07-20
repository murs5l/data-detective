# REST API reference

When running the web app or backend API server, you can integrate Data
Detective into your own applications.

## Endpoints

**POST /api/analyze** – Analyze a CSV file, return JSON report
```bash
curl -F "file=@data.csv" "http://localhost:8000/api/analyze?outlier_method=mad"
```
Response: JSON object with all profiling data (see the Python example below).

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
