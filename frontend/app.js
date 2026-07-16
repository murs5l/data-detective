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
  const downloadMarkdownBtn = document.getElementById("download-markdown");

  let selectedFile = null;
  let lastReport = null;

  function showSections(show, hide) {
    show.forEach((el) => (el.hidden = false));
    hide.forEach((el) => (el.hidden = true));
  }

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
    showSections([loadingSection], [uploadSection]);

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
      showSections([resultsSection], [loadingSection]);
    } catch (err) {
      showSections([uploadSection], [loadingSection]);
      showError(err.message || "Something went wrong while analyzing the file.");
    }
  });

  resetBtn.addEventListener("click", () => {
    selectedFile = null;
    lastReport = null;
    fileInput.value = "";
    selectedFilename.textContent = "";
    analyzeBtn.disabled = true;
    showSections([uploadSection], [resultsSection]);
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

  downloadMarkdownBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append("file", selectedFile);
    const method = outlierSelect.value;

    const response = await fetch(`/api/analyze/markdown?outlier_method=${encodeURIComponent(method)}`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) return;
    const blob = await response.blob();
    triggerDownload(blob, "data-detective-report.md");
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
    renderHealthScore(report.health_score);
    renderInsights(report.insights || []);
    renderStatGrid(report);
    renderHeatmap(report.correlation_matrix || {});
    renderColumnExplorer(report);
    renderTechnicalTables(report);
  }

  const HEALTH_BREAKDOWN_LABELS = {
    missing_values: "Missing values",
    duplicate_rows: "Duplicate rows",
    outliers: "Outliers",
    duplicate_columns: "Duplicate columns",
    constant_columns: "Constant columns",
    mixed_type_columns: "Mixed-type columns",
    negative_values: "Unexpected negatives",
    skewed_distributions: "Skewed distributions",
    correlated_columns: "Correlated columns",
  };

  function gradeClass(grade) {
    if (grade === "Fair") return "grade-fair";
    if (grade === "Poor" || grade === "Critical") return "grade-poor";
    return "";
  }

  function renderHealthScore(health) {
    if (!health) return;

    const badge = document.getElementById("health-score-badge");
    const number = document.getElementById("health-score-number");
    const gradeEl = document.getElementById("health-score-grade");
    const toggle = document.getElementById("health-score-toggle");
    const breakdownEl = document.getElementById("health-score-breakdown");

    const cls = gradeClass(health.grade);
    badge.className = `health-score-badge ${cls}`.trim();
    gradeEl.className = `health-score-grade ${cls}`.trim();
    number.textContent = health.score;
    gradeEl.textContent = health.grade;

    const items = Object.entries(health.breakdown || {})
      .filter(([, points]) => points > 0)
      .sort(([, a], [, b]) => b - a);

    if (!items.length) {
      breakdownEl.innerHTML = '<span class="health-score-breakdown-item">No deductions, nothing flagged.</span>';
    } else {
      breakdownEl.innerHTML = items
        .map(([key, points]) => {
          const label = HEALTH_BREAKDOWN_LABELS[key] || key;
          return `<span class="health-score-breakdown-item">${escapeHtml(label)}: <strong>-${points}</strong></span>`;
        })
        .join("");
    }

    toggle.onclick = () => {
      const isHidden = breakdownEl.hidden;
      breakdownEl.hidden = !isHidden;
      toggle.textContent = isHidden ? "Hide breakdown" : "Show breakdown";
    };
    breakdownEl.hidden = true;
    toggle.textContent = "Show breakdown";
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

  function getExplorableColumns(report) {
    const histCols = Object.keys(report.histogram_data || {});
    const boxCols = Object.keys(report.boxplot_stats || {});
    const allCols = [...new Set([...histCols, ...boxCols])];
    const excluded = new Set([
      ...(report.high_cardinality_columns || []),
      ...(report.constant_columns || []),
    ]);
    return allCols.filter((c) => !excluded.has(c));
  }

  function renderColumnExplorer(report) {
    const select = document.getElementById("column-select");
    const emptyMsg = document.getElementById("explorer-empty");
    const content = document.getElementById("explorer-content");
    const columns = getExplorableColumns(report);

    if (!columns.length) {
      select.innerHTML = "";
      showSections([emptyMsg], [select, content]);
      const hasAnyNumericColumn =
        Object.keys(report.histogram_data || {}).length || Object.keys(report.boxplot_stats || {}).length;
      emptyMsg.textContent = hasAnyNumericColumn
        ? "No columns suitable for detailed charting: the remaining numeric columns look like IDs or are constant."
        : "No numeric columns to chart.";
      return;
    }

    showSections([select, content], [emptyMsg]);
    select.innerHTML = columns.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");

    const renderSelected = () => {
      const col = select.value;
      renderExplorerHistogram((report.histogram_data || {})[col]);
      renderExplorerBoxplot((report.boxplot_stats || {})[col]);
      renderExplorerStats(col, report);
    };

    select.onchange = renderSelected;
    renderSelected();
  }

  function renderExplorerHistogram(hist) {
    const el = document.getElementById("explorer-histogram");
    if (!hist) {
      el.innerHTML = '<p class="empty-msg">No histogram data for this column.</p>';
      return;
    }

    const { bin_edges: binEdges, counts } = hist;
    const max = Math.max(...counts, 1);
    const bars = counts
      .map((c, i) => {
        const height = Math.max((c / max) * 100, 2);
        const rangeLabel = `${binEdges[i]} to ${binEdges[i + 1]}`;
        return `<div class="explorer-hist-bar-wrap" title="${escapeHtml(rangeLabel)}: ${c} rows">
          <div class="explorer-hist-count">${c}</div>
          <div class="hist-bar" style="height:${height}%"></div>
          <div class="explorer-hist-edge">${binEdges[i]}</div>
        </div>`;
      })
      .join("");
    el.innerHTML = `<div class="explorer-hist-bars">${bars}</div>`;
  }

  function renderExplorerBoxplot(box) {
    const el = document.getElementById("explorer-boxplot");
    if (!box) {
      el.innerHTML = '<p class="empty-msg">No boxplot data for this column.</p>';
      return;
    }
    el.innerHTML = boxplotSvg(box);
  }

  function renderExplorerStats(col, report) {
    const el = document.getElementById("explorer-stats");
    const box = (report.boxplot_stats || {})[col];
    if (!box) {
      el.innerHTML = "";
      return;
    }

    const shape = (report.distribution_shape || {})[col];
    const outlierCountMad = (report.outliers_mad || {})[col];
    const outlierCountIqr = (report.outliers_iqr || {})[col];
    const missingPct = (report.missing_percentage || {})[col];

    const stats = [
      { label: "Min", value: box.min },
      { label: "Q1", value: box.q1 },
      { label: "Median", value: box.median },
      { label: "Q3", value: box.q3 },
      { label: "Max", value: box.max },
      { label: "Outliers beyond whiskers", value: box.outliers.length },
    ];

    if (typeof outlierCountMad === "number") stats.push({ label: "Outliers (MAD)", value: outlierCountMad });
    if (typeof outlierCountIqr === "number") stats.push({ label: "Outliers (IQR)", value: outlierCountIqr });
    if (shape) {
      stats.push({ label: "Skewness", value: shape.skewness });
      stats.push({ label: "Kurtosis", value: shape.kurtosis });
    }
    if (typeof missingPct === "number") stats.push({ label: "Missing", value: `${missingPct}%` });

    el.innerHTML = stats
      .map(
        (s) =>
          `<div class="stat-chip"><span class="stat-chip-value">${s.value}</span><span class="stat-chip-label">${s.label}</span></div>`
      )
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

  function renderTechnicalTables(report) {
    renderKvTable("tech-column-types", report.column_types);
    renderKvTable("tech-missing", report.missing_percentage);
    renderKvTable("tech-outliers-mad", report.outliers_mad);
    renderKvTable("tech-outliers-iqr", report.outliers_iqr);
    renderList("tech-high-cardinality", report.high_cardinality_columns);
    renderList("tech-constant", report.constant_columns);
    renderList("tech-near-constant", report.near_constant_columns);
    renderList("tech-target", report.possible_target_columns);
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
