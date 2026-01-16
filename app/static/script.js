/** @format */

const fileInput = document.getElementById("file-input");
const dropZone = document.getElementById("drop-zone");
const dropContent = document.getElementById("drop-content");
const secFileInput = document.getElementById("sec-file-input");
const btnUploadSec = document.getElementById("btn-upload-sec");

let sessionId = null;

// ==========================================
// 1. UPLOAD LOGIC (Main File)
// ==========================================
dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", handleUpload);

// Drag & Drop Visuals
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "#2563eb";
});
dropZone.addEventListener("dragleave", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "#e5e7eb";
});
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "#e5e7eb";
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    handleUpload({ target: fileInput });
  }
});

async function handleUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  dropContent.innerHTML = "<p>⏳ Uploading & Analyzing...</p>";

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();
    sessionId = data.session_id;

    // --- POPULATE COLUMN DROPDOWNS ---
    const mainSelect = document.getElementById("merge-key-main");
    if (mainSelect) {
      mainSelect.innerHTML = "";
      data.analysis.columns.forEach((col) => {
        const opt = document.createElement("option");
        opt.value = col;
        opt.innerText = col;
        mainSelect.appendChild(opt);
      });
    }

    const colSelect = document.getElementById("dedupe-col");
    if (colSelect) {
      colSelect.innerHTML =
        '<option value="ALL">ALL Columns (Entire Row)</option>';
      data.analysis.columns.forEach((col) => {
        const option = document.createElement("option");
        option.value = col;
        option.innerText = `Only "${col}"`;
        colSelect.appendChild(option);
      });
    }
    // ... (keep existing populate logic for mainSelect and dedupe-col) ...

    // 2. NEW: Populate "Ignore Columns" Checkboxes
    const ignoreList = document.getElementById("ignore-col-list");
    ignoreList.innerHTML = "";

    data.analysis.columns.forEach((col) => {
      const label = document.createElement("label");
      label.style.fontSize = "0.85rem";
      label.style.display = "flex";
      label.style.alignItems = "center";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = col;
      checkbox.style.marginRight = "5px";

      // Auto-check columns that usually shouldn't be touched
      if (
        ["id", "address", "desc", "comment"].some((k) =>
          col.toLowerCase().includes(k)
        )
      ) {
        checkbox.checked = true;
      }

      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(col));
      ignoreList.appendChild(label);
    });

    dropContent.innerHTML = `
        <p style="color:#059669; font-weight:bold;">✅ ${file.name}</p>
        <p style="font-size:0.9rem;">Detected ${data.analysis.rows} rows, ${data.analysis.columns.length} columns.</p>
    `;

    // Show Config Section
    document.getElementById("config-section").classList.remove("hidden");
  } catch (err) {
    alert(err.message);
    dropContent.innerHTML = "<p style='color:red'>❌ Error. Try again.</p>";
  }
}

// ==========================================
// 2. SECONDARY FILE LOGIC (Merge)
// ==========================================
btnUploadSec.addEventListener("click", () => secFileInput.click());

secFileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || !sessionId) {
    alert("Please upload a Main File first!");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  document.getElementById("sec-file-status").innerText = "Uploading...";

  try {
    const res = await fetch(`/api/upload-secondary/${sessionId}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();

    document.getElementById(
      "sec-file-status"
    ).innerText = `✅ ${file.name} (${data.rows} rows)`;
    document.getElementById("merge-config").classList.remove("hidden");

    // Populate Secondary Dropdown
    const secSelect = document.getElementById("merge-key-sec");
    secSelect.innerHTML = "";
    data.columns.forEach((col) => {
      const opt = document.createElement("option");
      opt.value = col;
      opt.innerText = col;
      secSelect.appendChild(opt);
    });
  } catch (err) {
    alert(err.message);
    document.getElementById("sec-file-status").innerText = "Error.";
  }
});

// ==========================================
// 3. UI TOGGLES
// ==========================================
const dedupeCheck = document.getElementById("opt-duplicates");
if (dedupeCheck) {
  dedupeCheck.addEventListener("change", (e) => {
    const opts = document.getElementById("dedupe-options");
    if (opts) {
      if (e.target.checked) opts.classList.remove("hidden");
      else opts.classList.add("hidden");
    }
  });
}

// ==========================================
// 4. CONFIG GATHERING
// ==========================================
function getConfig() {
  const mergeKeyMain = document.getElementById("merge-key-main");
  const mergeKeySec = document.getElementById("merge-key-sec");
  const dedupeColEl = document.getElementById("dedupe-col");
  const ignored = [];
  document.querySelectorAll("#ignore-col-list input:checked").forEach((cb) => {
    ignored.push(cb.value);
  });

  return {
    standardize_columns: document.getElementById("opt-standardize").checked,
    drop_empty_rows: document.getElementById("opt-empty-rows").checked,
    clean_arabic: document.getElementById("opt-arabic").checked,
    standardize_columns: document.getElementById("opt-standardize").checked,

    // DEDUPE
    remove_duplicates: document.getElementById("opt-duplicates").checked,
    dedupe_column: dedupeColEl ? dedupeColEl.value : "ALL",
    fuzzy_dedupe: document.getElementById("opt-fuzzy").checked,

    // MERGE
    merge_active: document.getElementById("opt-merge").checked,
    merge_key_main: mergeKeyMain ? mergeKeyMain.value : "",
    merge_key_sec: mergeKeySec ? mergeKeySec.value : "",
    merge_fuzzy: document.getElementById("opt-merge-fuzzy").checked,
    clean_merged_columns: document.getElementById("opt-clean-merged").checked,

    // PRIVACY & CLEANING
    anonymize_pii: document.getElementById("opt-privacy").checked,
    clean_money: document.getElementById("opt-money").checked,
    fix_dates: document.getElementById("opt-dates").checked,
    fix_phones: document.getElementById("opt-phones").checked,
    fix_emails: document.getElementById("opt-emails").checked,
    remove_special_chars: document.getElementById("opt-special").checked,
    fill_missing: {
      numeric: document.getElementById("opt-numeric-fill").value,
    },
    ignore_columns: ignored,
    fill_missing: {
      numeric: document.getElementById("opt-numeric-fill").value,
    },
  };
}

// ==========================================
// 5. LOGGING RENDERER (New!)
// ==========================================
function renderLogs(logs) {
  const logEl = document.getElementById("process-log");
  logEl.innerHTML = "";

  if (!logs || logs.length === 0) {
    logEl.innerHTML =
      "<li style='color:#71717a'>No changes made or logged.</li>";
    return;
  }

  logs.forEach((msg) => {
    const li = document.createElement("li");
    li.innerText = `> ${msg}`;
    // Style specific messages
    if (msg.includes("Merged")) li.style.color = "#fbbf24"; // Gold for merge
    if (msg.includes("Dropped") || msg.includes("Removed"))
      li.style.color = "#f87171"; // Red for drops
    logEl.appendChild(li);
  });
}

// ==========================================
// 6. ACTION: PREVIEW
// ==========================================
document.getElementById("btn-preview").addEventListener("click", async () => {
  if (!sessionId) return;
  const btn = document.getElementById("btn-preview");
  const originalText = btn.innerText;
  btn.disabled = true;
  btn.innerText = "Processing...";

  try {
    const res = await fetch(`/api/preview/${sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getConfig()),
    });
    const data = await res.json();

    document.getElementById("download-area").classList.add("hidden");

    // RENDER LOGS
    renderLogs(data.report_log);

    renderDashboard(data.diff_summary, false);
    document.getElementById("results-section").classList.remove("hidden");
    document
      .getElementById("results-section")
      .scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    alert(e);
  }

  btn.disabled = false;
  btn.innerText = originalText;
});

// ==========================================
// 7. ACTION: CLEAN & DOWNLOAD
// ==========================================
document.getElementById("btn-clean").addEventListener("click", async () => {
  if (!sessionId) return;
  const btn = document.getElementById("btn-clean");
  const originalText = btn.innerText;
  btn.disabled = true;
  btn.innerText = "Cleaning...";

  try {
    const res = await fetch(`/api/clean/${sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getConfig()),
    });
    const data = await res.json();

    document.getElementById("download-area").classList.remove("hidden");
    document.getElementById("download-link").href = data.download_url;
    document.getElementById(
      "status-msg"
    ).innerText = `✨ Success! Cleaned file ready.`;

    // RENDER LOGS
    renderLogs(data.report_log);

    renderDashboard(data.diff_summary, true);
    document.getElementById("results-section").classList.remove("hidden");
  } catch (e) {
    alert(e);
  }

  btn.disabled = false;
  btn.innerText = originalText;
});

// ==========================================
// 8. DASHBOARD (Diff Table)
// ==========================================
function renderDashboard(diff, isFinal) {
  const statsEl = document.getElementById("diff-stats");
  const viewerEl = document.getElementById("diff-viewer");

  statsEl.innerHTML = `
        <div class="stat-card">
            <span class="stat-val" style="color:#d97706">${diff.stats.changed_count}</span>
            <span class="stat-label">Rows Modified</span>
        </div>
        <div class="stat-card">
            <span class="stat-val" style="color:#ef4444">${diff.stats.removed_count}</span>
            <span class="stat-label">Rows Removed</span>
        </div>
        <div class="stat-card">
            <span class="stat-val" style="color:#059669">${diff.stats.total_cleaned}</span>
            <span class="stat-label">Final Row Count</span>
        </div>
    `;

  let html = "";
  const formatVal = (val) => {
    if (val === null || val === "" || val === "nan" || val === undefined)
      return '<span style="color:#9ca3af; font-style:italic;">(empty)</span>';
    return val;
  };

  // Removed Rows Section
  if (diff.removed_preview && diff.removed_preview.length > 0) {
    html += `<h4 style="color:#ef4444; margin-top:20px;">🗑️ Removed Rows (Preview first 20)</h4>`;
    html += `<table class="diff-table" style="border-color:#fecaca;">
            <thead><tr style="background:#fef2f2;"><th>Row</th><th>Data (First 3 Columns)</th></tr></thead>
            <tbody>`;

    diff.removed_preview.forEach((row) => {
      const keys = Object.keys(row.data);
      const previewText = keys
        .slice(0, 3)
        .map((k) => `<b>${k}:</b> ${formatVal(row.data[k])}`)
        .join(", ");
      html += `<tr><td>${row.row_index}</td><td style="color:#7f1d1d;">${previewText} ...</td></tr>`;
    });
    html += `</tbody></table><hr style="border:0; border-top:1px solid #eee; margin:20px 0;">`;
  }

  html += `<h4>📝 Modified Rows (Sample)</h4>`;

  if (diff.changed_rows.length === 0) {
    html += `<p style="text-align:center; color:#6b7280;">No modified rows detected.</p>`;
  } else {
    html += `<table class="diff-table">
            <thead>
                <tr>
                    <th style="width: 50px;">Row</th>
                    <th style="width: 150px;">Column</th>
                    <th>Transformation (Before &rarr; After)</th>
                </tr>
            </thead>
            <tbody>`;

    const sample = diff.changed_rows.slice(0, 50);
    sample.forEach((row) => {
      for (const [col, val] of Object.entries(row.changes)) {
        html += `
                <tr>
                    <td><strong>${row.row_index}</strong></td>
                    <td>${col}</td>
                    <td>
                        <div class="cell-diff">
                            <span class="val-before">${formatVal(
                              val.before
                            )}</span>
                            <span class="val-after">${formatVal(
                              val.after
                            )}</span>
                        </div>
                    </td>
                </tr>`;
      }
    });
    html += `</tbody></table>`;
  }

  viewerEl.innerHTML = html;
}

// ... existing code ...

// QUIT LOGIC
const btnQuit = document.getElementById("btn-quit");
if (btnQuit) {
  btnQuit.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to close DataFrog?")) return;

    btnQuit.innerText = "Closing...";
    try {
      await fetch("/api/shutdown", { method: "POST" });
      document.body.innerHTML = `
                <div style="display:flex; justify-content:center; align-items:center; height:100vh; flex-direction:column; font-family:sans-serif;">
                    <h2 style="color:#ef4444;">App Closed</h2>
                    <p>You can close this tab now.</p>
                </div>
            `;
    } catch (e) {
      alert("Could not shutdown automatically. Please close the window.");
    }
  });
}
