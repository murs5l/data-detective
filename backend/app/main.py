import math
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from data_detective.exceptions import DataDetectiveError
from data_detective.html_report import generate_html_report
from data_detective.loader import load_csv
from data_detective.profiler import DataProfiler

from .quick_scan import quick_scan

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
VALID_OUTLIER_METHODS = ("mad", "iqr")

app = FastAPI(
    title="Data Detective API",
    description="Upload a CSV, get an automated data-quality intelligence report.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_upload(file: UploadFile, contents: bytes) -> None:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        max_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {max_mb} MB.")


def _validate_outlier_method(outlier_method: str) -> None:
    if outlier_method not in VALID_OUTLIER_METHODS:
        raise HTTPException(
            status_code=400,
            detail=f"outlier_method must be one of {VALID_OUTLIER_METHODS}.",
        )


def _sanitize_json(value):
    """Recursively replaces NaN/Infinity floats with None.

    Starlette's JSONResponse encodes with allow_nan=False (strict JSON), but
    pandas statistics (e.g. kurtosis on small samples) can produce NaN/inf.
    Without this, a perfectly valid CSV upload would 500 instead of
    returning a report.
    """
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {k: _sanitize_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_json(v) for v in value]
    return value


def _load_dataframe(tmp_path: str):
    try:
        return load_csv(tmp_path)
    except DataDetectiveError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}") from e


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), outlier_method: str = "mad"):
    """Runs the full profiling engine over an uploaded CSV and returns JSON.

    The file is processed entirely in memory / a short-lived temp file and
    is never persisted after the request completes.
    """
    _validate_outlier_method(outlier_method)
    contents = await file.read()
    _validate_upload(file, contents)

    started = time.perf_counter()

    with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
        tmp.write(contents)
        tmp.flush()

        quick = quick_scan(tmp.name)
        df = _load_dataframe(tmp.name)

        profiler = DataProfiler(df)
        try:
            report = profiler.run_full_profile(outlier_method=outlier_method)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Profiling failed: {e}") from e

    report["filename"] = file.filename
    report["processing_ms"] = round((time.perf_counter() - started) * 1000, 1)
    if quick:
        report["quick_scan"] = quick

    return JSONResponse(_sanitize_json(report))


@app.post("/api/analyze/html", response_class=HTMLResponse)
async def analyze_html(file: UploadFile = File(...), outlier_method: str = "mad"):
    """Same profiling pipeline as /api/analyze, rendered as a standalone HTML report."""
    _validate_outlier_method(outlier_method)
    contents = await file.read()
    _validate_upload(file, contents)

    with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
        tmp.write(contents)
        tmp.flush()
        df = _load_dataframe(tmp.name)
        profiler = DataProfiler(df)
        report = profiler.run_full_profile(outlier_method=outlier_method)

    with tempfile.TemporaryDirectory() as out_dir:
        out_path = str(Path(out_dir) / "report.html")
        generate_html_report(report, output_path=out_path)
        html = Path(out_path).read_text(encoding="utf-8")

    return HTMLResponse(html)


# Serve the static frontend (if present) for anything not matched by the
# API routes above. Must be mounted last: Starlette matches routes in
# declaration order and this is a catch-all.
_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
