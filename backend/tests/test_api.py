from fastapi.testclient import TestClient

from backend.app.main import MAX_UPLOAD_BYTES, app

client = TestClient(app)


def _csv_upload(content: bytes, filename: str = "sample.csv"):
    return {"file": (filename, content, "text/csv")}


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_success():
    csv_content = b"a,b\n1,2\n3,4\n5,6\n"
    response = client.post("/api/analyze", files=_csv_upload(csv_content))

    assert response.status_code == 200
    body = response.json()
    assert body["shape"] == {"rows": 3, "columns": 2}
    assert body["filename"] == "sample.csv"
    assert "processing_ms" in body
    assert "insights" in body
    assert "boxplot_stats" in body


def test_analyze_rejects_non_csv_extension():
    response = client.post("/api/analyze", files=_csv_upload(b"not,csv", filename="sample.txt"))
    assert response.status_code == 400
    assert "csv" in response.json()["detail"].lower()


def test_analyze_rejects_empty_file():
    response = client.post("/api/analyze", files=_csv_upload(b""))
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_rejects_headers_only_csv():
    response = client.post("/api/analyze", files=_csv_upload(b"a,b\n"))
    assert response.status_code == 400


def test_analyze_rejects_oversized_file():
    oversized = b"a,b\n" + b"1,2\n" * ((MAX_UPLOAD_BYTES // 4) + 1)
    response = client.post("/api/analyze", files=_csv_upload(oversized))
    assert response.status_code == 413


def test_analyze_rejects_invalid_outlier_method():
    response = client.post(
        "/api/analyze?outlier_method=bogus",
        files=_csv_upload(b"a,b\n1,2\n3,4\n"),
    )
    assert response.status_code == 400


def test_analyze_handles_malformed_csv_gracefully():
    malformed = b'"unterminated quote,1\n2,3\n'
    response = client.post("/api/analyze", files=_csv_upload(malformed))
    # pandas' C parser tolerates this particular case; the important
    # contract is: never a raw 500 with a stack trace, always 200 or a
    # clean 400 with a message.
    assert response.status_code in (200, 400)
    assert isinstance(response.json(), dict)


def test_analyze_html_success():
    csv_content = b"a,b\n1,2\n3,4\n"
    response = client.post("/api/analyze/html", files=_csv_upload(csv_content))
    assert response.status_code == 200
    assert "Data Detective Report" in response.text


def test_analyze_markdown_success():
    csv_content = b"a,b\n1,2\n3,4\n"
    response = client.post("/api/analyze/markdown", files=_csv_upload(csv_content))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# 🕵️ Data Detective Report" in response.text
    assert "Data Health Score:" in response.text
