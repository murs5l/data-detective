"""End-to-end test: a real browser, driving the real served web app, against
a real running backend. Everything else in this project is tested with
mocks or an in-process TestClient; this is the one test that proves the
whole stack (frontend JS, FastAPI, DataProfiler) actually works together.

Requires the `e2e` extra: `pip install -e ".[api,e2e]"` then
`playwright install chromium`.
"""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = REPO_ROOT / "examples" / "sample_data.csv"
SERVER_URL = "http://127.0.0.1:8123"


def _wait_until_healthy(url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.2)
    raise RuntimeError(f"Server at {url} did not become healthy within {timeout}s")


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", "8123"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_until_healthy(f"{SERVER_URL}/api/health")
        yield SERVER_URL
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_upload_csv_renders_health_score_and_insights(live_server: str, page: Page) -> None:
    """The golden path this whole project exists for: drop a CSV in the web
    app, get back a health score and insights that match what the CLI/API
    would produce for the same file (examples/sample_data.csv is checked
    into the repo with a known score of 64/Fair, see README.md)."""
    page.goto(live_server)

    page.set_input_files("#file-input", str(SAMPLE_CSV))
    page.click("#analyze-btn")

    expect(page.locator("#results")).to_be_visible(timeout=10_000)
    expect(page.locator("#health-score-number")).to_have_text("64")
    expect(page.locator("#health-score-grade")).to_have_text("Fair")

    insights = page.locator("#insights-list")
    expect(insights).to_contain_text("notes")
