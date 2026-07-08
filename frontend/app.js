(() => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const analyzeBtn = document.getElementById("analyze-btn");
  const outlierSelect = document.getElementById("outlier-method");
  const selectedFilename = document.getElementById("selected-filename");
  const errorBanner = document.getElementById("error-banner");

  const uploadSection = document.getElementById("upload-section");
  const loadingSection = document.getElementById("loading");
  const resultsSection = document.getElementById("results");
  const resetBtn = document.getElementById("reset-btn");

  const downloadJsonBtn = document.getElementById("download-json");
  const downloadHtmlBtn = document.getElementById("download-html");

  let selectedFile = null;
  let lastReport = null;

  // ---------- file selection ----------

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });

  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) {
      selectFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) selectFile(fileInput.files[0]);
  });

  function selectFile(file) {
    hideError();
    if (!file.name.toLowerCase().endsWith(".csv")) {
      showError("Only .csv files are supported.");
      return;
    }
    selectedFile = file;
    selectedFilename.textContent = file.name;
    analyzeBtn.disabled = false;
  }

  // ---------- analyze ----------

  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    hideError();
    uploadSection.hidden = true;
    loadingSection.hidden = false;

    const formData = new FormData();
    formData.append("file", selectedFile);
    const method = outlierSelect.value;

    try {
      const response = await fetch(`/api/analyze?outlier_method=${encodeURIComponent(method)}`, {
        method: "POST",
        body: formData,
      });
      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.detail || "Analysis failed.");
      }

      lastReport = body;
      renderReport(body);
      loadingSection.hidden = true;
      resultsSection.hidden = false;
    } catch (err) {
      loadingSection.hidden = true;
      uploadSection.hidden = false;
      showError(err.message || "Something went wrong while analyzing the file.");
    }
  });

  resetBtn.addEventListener("click", () => {
    selectedFile = null;
    lastReport = null;
    fileInput.value = "";
    selectedFilename.textContent = "";
    analyzeBtn.disabled = true;
    resultsSection.hidden = true;
    uploadSection.hidden = false;
  });

  function showError(message) {
    errorBanner.textContent = `❌ ${message}`;
    errorBanner.hidden = false;
  }

  function hideError() {
    errorBanner.hidden = true;
  }

  // ---------- downloads ----------

  downloadJsonBtn.addEventListener("click", () => {
    if (!lastReport) return;
    const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json" });
    triggerDownload(blob, "data-detective-report.json");
  });

  downloadHtmlBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append("file", selectedFile);
    const method = outlierSelect.value;

    const response = await fetch(`/api/analyze/html?outlier_method=${encodeURIComponent(method)}`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) return;
    const blob = await response.blob();
    triggerDownload(blob, "data-detective-report.html");
  });

  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // ---------- rendering ----------

  function severityClass(insight) {
    if (insight.startsWith("🚨")) return "severity-danger";
    if (insight.startsWith("⚠️")) return "severity-warning";
    return "";
  }

  function renderReport(report) {
    renderInsights(report.insights || []);
    renderStatGrid(report);
    renderHeatmap(report.correlation_matrix || {});
    renderHistograms(report.histogram_data || {});
    renderBoxplots(report.boxplot_stats || {});
    renderTechnicalTables(report);
  }

  function renderInsights(insights) {
    const list = document.getElementById("insights-list");
    list.innerHTML = "";
    if (!insights.length) {
      const li = document.createElement("li");
      li.className = "insight insight-empty";
      li.textContent = "✅ No notable issues found. This data looks clean.";
      list.appendChild(li);
      return;
    }
    for (const insight of insights) {
      const li = document.createElement("li");
      li.className = `insight ${severityClass(insight)}`.trim();
      li.textContent = insight;
      list.appendChild(li);
    }
  }

  function renderStatGrid(report) {
    const grid = document.getElementById("stat-grid");
    const shape = report.shape || {};
    const totalMemory = Object.values(report.memory_usage_kb || {}).reduce((a, b) => a + b, 0);

    const stats = [
      { label: "Rows", value: shape.rows ?? "N/A" },
      { label: "Columns", value: shape.columns ?? "N/A" },
      { label: "Duplicate rows", value: report.duplicates ?? 0 },
      { label: "Memory (KB)", value: totalMemory ? totalMemory.toFixed(1) : "0" },
      { label: "Processing time", value: `${report.processing_ms ?? "N/A"} ms` },
    ];

    if (report.quick_scan) {
      stats.push({ label: "Fast pre-scan", value: `${report.quick_scan.scan_ms} ms` });
    }

    grid.innerHTML = stats
      .map(
        (s) => `<div class="stat-card"><div class="value">${s.value}</div><div class="label">${s.label}</div></div>`
      )
      .join("");
  }

  function colorForCorrelation(value) {
    // -1 -> red, 0 -> light gray, 1 -> blue
    const v = Math.max(-1, Math.min(1, value));
    if (v >= 0) {
      const intensity = Math.round(255 - v * 140);
      return `rgb(${intensity - 60}, ${intensity - 20}, 255)`;
    }
    const intensity = Math.round(255 + v * 140);
    return `rgb(255, ${intensity - 60}, ${intensity - 20})`;
  }

  function renderHeatmap(matrix) {
    const wrap = document.getElementById("heatmap-wrap");
    const cols = Object.keys(matrix);
    if (cols.length < 2) {
      wrap.innerHTML = '<p class="empty-msg">Not enough numeric columns for a correlation heatmap.</p>';
      return;
    }

    let html = '<table class="heatmap-table"><thead><tr><th></th>';
    for (const c of cols) html += `<th>${escapeHtml(c)}</th>`;
    html += "</tr></thead><tbody>";

    for (const rowKey of cols) {
      html += `<tr><th>${escapeHtml(rowKey)}</th>`;
      for (const colKey of cols) {
        const value = matrix[rowKey][colKey];
        const color = colorForCorrelation(value);
        html += `<td><div class="heatmap-cell" style="background:${color}">${value.toFixed(2)}</div></td>`;
      }
      html += "</tr>";
    }
    html += "</tbody></table>";
    wrap.innerHTML = html;
  }

  function renderHistograms(histograms) {
    const container = document.getElementById("histograms");
    const cols = Object.keys(histograms);
    if (!cols.length) {
      container.innerHTML = '<p class="empty-msg">No numeric columns to chart.</p>';
      return;
    }

    container.innerHTML = cols
      .map((col) => {
        const { counts } = histograms[col];
        const max = Math.max(...counts, 1);
        const bars = counts
          .map((c) => `<div class="hist-bar" style="height:${Math.max((c / max) * 100, 2)}%"></div>`)
          .join("");
        return `<div class="hist-block"><h4>${escapeHtml(col)}</h4><div class="hist-bars">${bars}</div></div>`;
      })
      .join("");
  }

  function boxplotSvg(box) {
    const width = 300;
    const height = 46;
    const padding = 14;
    const domainMin = Math.min(box.min, box.whisker_low, ...box.outliers);
    const domainMax = Math.max(box.max, box.whisker_high, ...box.outliers);
    const span = domainMax - domainMin || 1;

    const scale = (v) => padding + ((v - domainMin) / span) * (width - 2 * padding);

    const midY = height / 2;
    const boxTop = midY - 13;
    const boxHeight = 26;

    const whiskerLine = `<line class="box-whisker" x1="${scale(box.whisker_low)}" y1="${midY}" x2="${scale(box.whisker_high)}" y2="${midY}" />`;
    const capLow = `<line class="box-whisker" x1="${scale(box.whisker_low)}" y1="${midY - 6}" x2="${scale(box.whisker_low)}" y2="${midY + 6}" />`;
    const capHigh = `<line class="box-whisker" x1="${scale(box.whisker_high)}" y1="${midY - 6}" x2="${scale(box.whisker_high)}" y2="${midY + 6}" />`;
    const boxX = scale(box.q1);
    const boxWidth = Math.max(scale(box.q3) - scale(box.q1), 1);
    const rect = `<rect class="box-rect" x="${boxX}" y="${boxTop}" width="${boxWidth}" height="${boxHeight}" rx="3" />`;
    const median = `<line class="box-median" x1="${scale(box.median)}" y1="${boxTop}" x2="${scale(box.median)}" y2="${boxTop + boxHeight}" />`;
    const outliers = box.outliers
      .map((v) => `<circle class="box-outlier" cx="${scale(v)}" cy="${midY}" r="3" />`)
      .join("");

    return `<svg class="box-plot-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">${whiskerLine}${capLow}${capHigh}${rect}${median}${outliers}</svg>`;
  }

  function renderBoxplots(boxplots) {
    const container = document.getElementById("boxplots");
    const cols = Object.keys(boxplots);
    if (!cols.length) {
      container.innerHTML = '<p class="empty-msg">No numeric columns to chart.</p>';
      return;
    }

    container.innerHTML = cols
      .map((col) => `<div class="box-block"><h4>${escapeHtml(col)}</h4>${boxplotSvg(boxplots[col])}</div>`)
      .join("");
  }

  function renderTechnicalTables(report) {
    renderKvTable("tech-column-types", report.column_types);
    renderKvTable("tech-missing", report.missing_percentage);
    renderKvTable("tech-outliers-mad", report.outliers_mad);
    renderKvTable("tech-outliers-iqr", report.outliers_iqr);
    renderList("tech-high-cardinality", report.high_cardinality_columns);
    renderList("tech-constant", report.constant_columns);
    renderPairs("tech-dup-columns", report.duplicate_columns);
    renderPairs("tech-correlated", report.correlated_columns);
    renderList("tech-date-like", report.date_like_columns);
    renderList("tech-mixed-type", report.mixed_type_columns);
    renderList("tech-negative", report.negative_in_nonnegative_columns);
    renderKvTable("tech-memory", report.memory_usage_kb);
  }

  function renderKvTable(elementId, data) {
    const el = document.getElementById(elementId);
    const entries = Object.entries(data || {});
    if (!entries.length) {
      el.innerHTML = '<p class="empty-msg">No data.</p>';
      return;
    }
    el.innerHTML = `<table><tbody>${entries
      .map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(String(v))}</td></tr>`)
      .join("")}</tbody></table>`;
  }

  function renderList(elementId, items) {
    const el = document.getElementById(elementId);
    if (!items || !items.length) {
      el.innerHTML = '<p class="empty-msg">None found.</p>';
      return;
    }
    el.innerHTML = `<ul>${items.map((i) => `<li>${escapeHtml(String(i))}</li>`).join("")}</ul>`;
  }

  function renderPairs(elementId, pairs) {
    const el = document.getElementById(elementId);
    if (!pairs || !pairs.length) {
      el.innerHTML = '<p class="empty-msg">None found.</p>';
      return;
    }
    el.innerHTML = `<ul>${pairs
      .map((pair) => {
        if (pair.length === 3) {
          const [a, b, score] = pair;
          return `<li>${escapeHtml(a)} ↔ ${escapeHtml(b)} (${score})</li>`;
        }
        const [a, b] = pair;
        return `<li>${escapeHtml(a)} ↔ ${escapeHtml(b)}</li>`;
      })
      .join("")}</ul>`;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
})();
