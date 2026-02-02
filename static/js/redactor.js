/* ============================================================
   REDACTOR FRONTEND — PHASE 5
   - Preview Mode (DB-backed)
   - AI Suggestions with bounding boxes
   - Undo / Clear / Apply Preview
   - Page navigation
   - Workspace sidebar
   - Thumbnails sidebar + OCR toggle
   - Zoom controls
   - Multi-page preview
   - Viewer tips
   - Keyboard shortcuts (from settings)
   - Redaction templates (save/load/edit/apply)
   ============================================================ */

let filename = window.filename || '{{ filename }}';
let currentPage = 0;
let pageCount = window.pageCount || 1;

let previewBoxes = [];   // Loaded from DB
let drawing = false;
let startX, startY;

let appSettings = {};

const canv = document.getElementById('pdfCanvas');
const overlay = document.getElementById('overlay');
const ctx = canv.getContext('2d');

let zoom = 1;
let baseWidth = 0;
let baseHeight = 0;

let tips = [];
let tipIndex = 0;
let tipsTimer = null;

/* ============================================================
   SETTINGS LOAD + INITIALIZATION
   ============================================================ */

function applySettingsToUI(s) {
  // OCR default
  const ocrToggle = document.getElementById("ocrToggle");
  if (ocrToggle) ocrToggle.checked = !!s.ocr_default;

  // Sidebar collapsed (optional)
  if (s.sidebar_collapsed) {
    document.getElementById("thumbSidebar")?.classList.add("thumb-collapsed");
  }
}

function buildTipsFromSettings() {
  if (!appSettings) return;

  const sc = appSettings.shortcuts || {};
  tips = [];

  tips.push("Use the mouse wheel + Ctrl to zoom in and out.");
  if (sc.zoom_reset) tips.push(`Press ${sc.zoom_reset} to reset zoom.`);
  if (sc.apply) tips.push(`Press ${sc.apply} to apply redactions.`);
  if (sc.undo) tips.push(`Press ${sc.undo} to undo the last redaction.`);
  if (sc.clear) tips.push(`Press ${sc.clear} to clear all redactions.`);
  if (sc.prev_page && sc.next_page) {
    tips.push(`Use ${sc.prev_page} and ${sc.next_page} to change pages.`);
  }
  if (sc.toggle_thumbs) tips.push(`Press ${sc.toggle_thumbs} to toggle the thumbnails sidebar.`);
  if (sc.toggle_ocr) tips.push(`Press ${sc.toggle_ocr} to toggle OCR suggestions.`);

  if (tips.length === 0) {
    tips.push("Draw a box on the page to add a redaction preview.");
  }
}

function showCurrentTip() {
  const el = document.getElementById("viewerTips");
  if (!el) return;
  if (!appSettings || appSettings.show_tips === false) {
    el.textContent = "";
    return;
  }

  if (!tips.length) buildTipsFromSettings();

  const tip = tips[tipIndex % tips.length];
  el.innerHTML = `<span class="tip-label">TIP:</span> ${tip}`;
}

function startTipsRotation() {
  buildTipsFromSettings();
  showCurrentTip();

  if (tipsTimer) clearInterval(tipsTimer);
  tipsTimer = setInterval(() => {
    tipIndex = (tipIndex + 1) % tips.length;
    showCurrentTip();
  }, 10000);
}

function initFromSettings() {
  fetch("/settings/data")
    .then(r => r.json())
    .then(s => {
      appSettings = s;
      applySettingsToUI(s);
      startTipsRotation();
    });
}

/* ============================================================
   INIT
   ============================================================ */

window.onload = () => {
  initFromSettings();
  loadPage(0);
  loadPreview();
  loadSuggestions();
  openCurrentDocument();
  setTimeout(loadThumbnails, 500);
  loadTemplates();
};

/* ============================================================
   LOAD PAGE IMAGE
   ============================================================ */

function loadPage(p) {
  currentPage = p;

  const img = new Image();
  img.src = `/redactor/get_page/${filename}/${p}`;

  img.onload = () => {
    canv.width = img.width;
    canv.height = img.height;
    ctx.clearRect(0, 0, canv.width, canv.height);
    ctx.drawImage(img, 0, 0);

    document.getElementById('pageNum').textContent = p + 1;
    document.getElementById('pageCount').textContent = pageCount;

    baseWidth = canv.width;
    baseHeight = canv.height;

    drawOverlay();
    applyZoom();
    highlightThumbnail();
  };
}

/* ============================================================
   PAGE NAVIGATION
   ============================================================ */

document.getElementById('prevPage').onclick = () => {
  if (currentPage > 0) loadPage(currentPage - 1);
};

document.getElementById('nextPage').onclick = () => {
  if (currentPage < pageCount - 1) loadPage(currentPage + 1);
};

/* ============================================================
   PAGE JUMP
   ============================================================ */

const pageJumpInput = document.getElementById('pageJump');
const pageJumpGo    = document.getElementById('pageJumpGo');

if (pageJumpGo && pageJumpInput) {
  pageJumpGo.onclick = () => {
    const val = parseInt(pageJumpInput.value, 10);
    if (!isNaN(val) && val >= 1 && val <= pageCount) {
      loadPage(val - 1);
    }
  };

  pageJumpInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      pageJumpGo.click();
    }
  });
}

/* ============================================================
   DRAW AREA REDACTION (Preview Mode) — WITH LIVE OUTLINE
   ============================================================ */

let liveBox = null;   // temporary red outline div

canv.onmousedown = e => {
  const r = canv.getBoundingClientRect();
  drawing = true;
  startX = (e.clientX - r.left) / zoom;
  startY = (e.clientY - r.top) / zoom;

  // Create live outline box
  liveBox = document.createElement("div");
  liveBox.style.position = "absolute";
  liveBox.style.border = "2px dashed red";
  liveBox.style.background = "rgba(255,0,0,0.1)";
  liveBox.style.pointerEvents = "none";
  overlay.appendChild(liveBox);
};

canv.onmousemove = e => {
  if (!drawing || !liveBox) return;

  const r = canv.getBoundingClientRect();
  const currX = (e.clientX - r.left) / zoom;
  const currY = (e.clientY - r.top) / zoom;

  const x = Math.min(startX, currX);
  const y = Math.min(startY, currY);
  const w = Math.abs(currX - startX);
  const h = Math.abs(currY - startY);

  liveBox.style.left = (x * zoom) + "px";
  liveBox.style.top = (y * zoom) + "px";
  liveBox.style.width = (w * zoom) + "px";
  liveBox.style.height = (h * zoom) + "px";
};

canv.onmouseup = e => {
  if (!drawing) return;
  drawing = false;

  const r = canv.getBoundingClientRect();
  const endX = (e.clientX - r.left) / zoom;
  const endY = (e.clientY - r.top) / zoom;

  const width = Math.abs(endX - startX);
  const height = Math.abs(endY - startY);

  // Remove live outline
  if (liveBox) {
    overlay.removeChild(liveBox);
    liveBox = null;
  }

  if (width < 5 || height < 5) return;

  const box = {
    type: 'area',
    page: currentPage,
    x: Math.min(startX, endX) / canv.width,
    y: Math.min(startY, endY) / canv.height,
    width: width / canv.width,
    height: height / canv.height
  };

  previewBoxes.push(box);
  savePreview([box]);
  drawOverlay();
};

/* ============================================================
   DRAW OVERLAY BOXES
   ============================================================ */

function drawOverlay() {
  overlay.innerHTML = '';

  previewBoxes
    .filter(b => b.page === currentPage)
    .forEach(b => {
      const div = document.createElement('div');
      div.style.position = 'absolute';
      div.style.left = (b.x * canv.width) + 'px';
      div.style.top = (b.y * canv.height) + 'px';
      div.style.width = (b.width * canv.width) + 'px';
      div.style.height = (b.height * canv.height) + 'px';
      div.style.background = 'rgba(39,170,225,0.35)';
      div.style.border = '1px solid #27AAE1';
      overlay.appendChild(div);
    });
}

/* ============================================================
   LOAD PREVIEW FROM DB
   ============================================================ */

function loadPreview() {
  fetch(`/redactor/preview/load/${filename}`)
    .then(r => r.json())
    .then(d => {
      previewBoxes = d.preview || [];
      drawOverlay();
    });
}

/* ============================================================
   SAVE PREVIEW TO DB
   ============================================================ */

function savePreview(boxes) {
  fetch('/redactor/preview/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, changes: boxes })
  });
}

/* ============================================================
   UNDO PREVIEW
   ============================================================ */

document.getElementById('undoBtn').onclick = () => {
  fetch('/redactor/preview/undo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename })
  }).then(() => {
    previewBoxes.pop();
    drawOverlay();
  });
};

/* ============================================================
   CLEAR PREVIEW
   ============================================================ */

document.getElementById('clearBtn').onclick = () => {
  fetch('/redactor/preview/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename })
  }).then(() => {
    previewBoxes = [];
    drawOverlay();
  });
};

/* ============================================================
   APPLY PREVIEW → FINAL REDACTION
   ============================================================ */

document.getElementById('applyPreview').onclick = () => {
  fetch('/redactor/apply_preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename })
  })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        window.location.href = d.download_url;
      } else {
        alert('Redaction failed: ' + d.error);
      }
    });
};

/* ============================================================
   AI SUGGESTIONS (with bounding boxes + OCR flag)
   ============================================================ */

function loadSuggestions() {
  const ocr = document.getElementById('ocrToggle').checked ? 1 : 0;

  fetch(`/redactor/suggestions/${filename}?ocr=${ocr}`)
    .then(r => r.json())
    .then(d => {
      const box = document.getElementById('suggestions');
      box.innerHTML = '';

      (d.suggestions || []).forEach(s => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-outline-primary me-2 mb-2';
        btn.textContent = `${s.label}: ${s.text}`;

        btn.onclick = () => {
          // If bbox present → area; else text-based
          if (s.bbox && s.bbox.length === 4) {
            const b = {
              type: 'area',
              page: s.page,
              x: s.bbox[0] / canv.width,
              y: s.bbox[1] / canv.height,
              width: (s.bbox[2] - s.bbox[0]) / canv.width,
              height: (s.bbox[3] - s.bbox[1]) / canv.height
            };
            previewBoxes.push(b);
            savePreview([b]);
            drawOverlay();
          } else {
            const b = {
              type: 'text',
              page: s.page,
              x: 0,
              y: 0,
              width: 0,
              height: 0,
              text: s.text
            };
            previewBoxes.push(b);
            savePreview([b]);
            drawOverlay();
          }
        };

        box.appendChild(btn);
      });
    });
}

/* ============================================================
   WORKSPACE SIDEBAR
   ============================================================ */

function loadWorkspace() {
  fetch('/redactor/workspace/list')
    .then(r => r.json())
    .then(d => renderWorkspace(d.documents));
}

function renderWorkspace(docs) {
  const list = document.getElementById('docList');
  list.innerHTML = '';

  docs.forEach(doc => {
    const div = document.createElement('div');
    div.className = 'doc-entry' + (doc.active ? ' active' : '');
    div.textContent = doc.display_name;

    const x = document.createElement('span');
    x.className = 'doc-close';
    x.textContent = '×';
    x.onclick = e => {
      e.stopPropagation();
      closeDocument(doc.filename);
    };
    div.appendChild(x);

    div.onclick = () => {
      if (!doc.active) switchDocument(doc.filename);
    };

    list.appendChild(div);
  });
}

function switchDocument(fname) {
  fetch('/redactor/workspace/set_active', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: fname })
  }).then(() => {
    window.location.href = `/redactor/viewer/${fname}`;
  });
}

function closeDocument(fname) {
  fetch('/redactor/workspace/close', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: fname })
  }).then(() => {
    loadWorkspace();
    if (fname === filename) {
      window.location.href = '/redactor/';
    }
  });
}

function openCurrentDocument() {
  fetch('/redactor/workspace/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename,
      display_name: filename
    })
  }).then(() => loadWorkspace());
}

/* ============================================================
   THUMBNAILS SIDEBAR + OCR MODE
   ============================================================ */

function loadThumbnails() {
  const list = document.getElementById('thumbList');
  list.innerHTML = '';

  for (let p = 0; p < pageCount; p++) {
    const img = document.createElement('img');
    img.className = 'thumb-img';
    img.dataset.page = p;
    img.src = `/redactor/thumbnail/${filename}/${p}`;

    img.onclick = () => loadPage(p);

    list.appendChild(img);
  }
}

function highlightThumbnail() {
  document.querySelectorAll('.thumb-img').forEach(img => {
    img.classList.toggle('active-thumb', parseInt(img.dataset.page) === currentPage);
  });
}

document.getElementById('thumbToggle').onclick = () => {
  document.getElementById('thumbSidebar').classList.toggle('thumb-collapsed');
};

document.getElementById('ocrToggle').onchange = () => {
  loadSuggestions();
};

/* ============================================================
   ZOOM CONTROLS
   ============================================================ */

function applyZoom() {
  canv.style.transform = `scale(${zoom})`;
  overlay.style.transform = `scale(${zoom})`;
  overlay.style.transformOrigin = "top left";
  canv.style.transformOrigin = "top left";
}

document.getElementById('zoomIn').onclick = () => {
  zoom = Math.min(zoom + 0.1, 3);
  applyZoom();
};

document.getElementById('zoomOut').onclick = () => {
  zoom = Math.max(zoom - 0.1, 0.3);
  applyZoom();
};

document.getElementById('zoomReset').onclick = () => {
  zoom = 1;
  applyZoom();
};

document.getElementById('zoomFitWidth').onclick = () => {
  const viewerWidth = document.getElementById('viewer').clientWidth;
  if (baseWidth > 0) {
    zoom = viewerWidth / baseWidth;
    applyZoom();
  }
};

document.getElementById('zoomFitPage').onclick = () => {
  const viewer = document.getElementById('viewer');
  if (baseWidth > 0 && baseHeight > 0) {
    zoom = Math.min(
      viewer.clientWidth / baseWidth,
      viewer.clientHeight / baseHeight
    );
    applyZoom();
  }
};

document.getElementById('viewer').addEventListener('wheel', e => {
  if (!e.ctrlKey) return;
  e.preventDefault();

  zoom += e.deltaY < 0 ? 0.1 : -0.1;
  zoom = Math.min(Math.max(zoom, 0.3), 3);
  applyZoom();
});

/* ============================================================
   MULTI-PAGE PREVIEW
   ============================================================ */

document.getElementById('previewAll').onclick = () => {
  const container = document.getElementById('previewPages');
  container.innerHTML = '';

  for (let p = 0; p < pageCount; p++) {
    const wrapper = document.createElement('div');
    wrapper.className = 'preview-page';
    wrapper.dataset.page = p;

    const img = document.createElement('img');
    img.className = 'preview-thumb';
    img.src = `/redactor/thumbnail/${filename}/${p}`;
    img.onclick = () => {
      loadPage(p);
      bootstrap.Modal.getInstance(document.getElementById('previewModal')).hide();
    };

    wrapper.appendChild(img);

    previewBoxes
      .filter(b => b.page === p)
      .forEach(b => {
        const box = document.createElement('div');
        box.className = 'preview-overlay-box';
        box.style.left = (b.x * 200) + 'px';
        box.style.top = (b.y * (200 * 1.3)) + 'px';
        box.style.width = (b.width * 200) + 'px';
        box.style.height = (b.height * (200 * 1.3)) + 'px';
        wrapper.appendChild(box);
      });

    container.appendChild(wrapper);
  }

  new bootstrap.Modal(document.getElementById('previewModal')).show();
};

document.getElementById('applyPreviewFromModal').onclick = () => {
  document.getElementById('applyPreview').click();
};

/* ============================================================
   KEYBOARD SHORTCUTS (USING SETTINGS)
   ============================================================ */

function matchShortcut(e, combo) {
  if (!combo) return false;
  const parts = combo.split("+");
  const needCtrl = parts.includes("Ctrl");
  const needShift = parts.includes("Shift");
  const needAlt = parts.includes("Alt");
  const keyPart = parts.find(p => !["Ctrl", "Shift", "Alt"].includes(p));

  if (!!needCtrl !== e.ctrlKey) return false;
  if (!!needShift !== e.shiftKey) return false;
  if (!!needAlt !== e.altKey) return false;

  if (!keyPart) return true;

  const k = e.key.length === 1 ? e.key.toUpperCase() : e.key;
  return k === keyPart || e.key === keyPart;
}

document.addEventListener('keydown', function (e) {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  if (!appSettings || !appSettings.shortcuts) return;

  const sc = appSettings.shortcuts;

  if (matchShortcut(e, sc.prev_page)) {
    e.preventDefault();
    if (currentPage > 0) loadPage(currentPage - 1);
  }

  if (matchShortcut(e, sc.next_page)) {
    e.preventDefault();
    if (currentPage < pageCount - 1) loadPage(currentPage + 1);
  }

  if (matchShortcut(e, sc.undo)) {
    e.preventDefault();
    document.getElementById('undoBtn').click();
  }

  if (matchShortcut(e, sc.clear)) {
    e.preventDefault();
    document.getElementById('clearBtn').click();
  }

  if (matchShortcut(e, sc.apply)) {
    e.preventDefault();
    document.getElementById('applyPreview').click();
  }

  if (matchShortcut(e, sc.zoom_in)) {
    e.preventDefault();
    document.getElementById('zoomIn').click();
  }

  if (matchShortcut(e, sc.zoom_out)) {
    e.preventDefault();
    document.getElementById('zoomOut').click();
  }

  if (matchShortcut(e, sc.zoom_reset)) {
    e.preventDefault();
    document.getElementById('zoomReset').click();
  }

  if (matchShortcut(e, sc.toggle_thumbs)) {
    e.preventDefault();
    document.getElementById('thumbToggle').click();
  }

  if (matchShortcut(e, sc.toggle_ocr)) {
    e.preventDefault();
    const ocr = document.getElementById('ocrToggle');
    ocr.checked = !ocr.checked;
    loadSuggestions();
  }
});

/* ============================================================
   REDACTION TEMPLATES (SAVE / LOAD / APPLY)
   ============================================================ */

function loadTemplates() {
  // For now, no company/doc_type filter (can be added later)
  fetch('/redactor/template/list')
    .then(r => r.json())
    .then(d => {
      const sel = document.getElementById('templateSelect');
      if (!sel) return;
      sel.innerHTML = '<option value="">Templates...</option>';

      (d.templates || []).forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.id;
        let label = t.name;
        if (t.company) label += ` [${t.company}]`;
        if (t.doc_type) label += ` (${t.doc_type})`;
        opt.textContent = label;
        sel.appendChild(opt);
      });
    });
}

function saveTemplate() {
  const name = prompt("Template name:");
  if (!name) return;

  const company = prompt("Company (optional, e.g. Amazon):") || "";
  const docType = prompt("Document type (optional, e.g. Invoice):") || "";

  fetch('/redactor/template/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename,
      name,
      company,
      doc_type: docType
    })
  })
    .then(r => r.json())
    .then(d => {
      if (!d.success) {
        alert("Failed to save template: " + (d.error || "Unknown error"));
        return;
      }
      alert("Template saved.");
      loadTemplates();
    });
}

function applyTemplate(mode) {
  const sel = document.getElementById('templateSelect');
  if (!sel || !sel.value) {
    alert("Select a template first.");
    return;
  }

  const templateId = parseInt(sel.value, 10);
  if (!templateId) {
    alert("Invalid template.");
    return;
  }

  const body = {
    filename,
    template_id: templateId,
    mode
  };

  if (mode === 'page') {
    body.page = currentPage;
  }

  fetch('/redactor/template/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
    .then(r => r.json())
    .then(d => {
      if (!d.success) {
        alert("Failed to apply template: " + (d.error || "Unknown error"));
        return;
      }
      // Reload preview boxes from DB
      loadPreview();
    });
}

const saveTemplateBtn = document.getElementById('saveTemplateBtn');
if (saveTemplateBtn) {
  saveTemplateBtn.onclick = () => saveTemplate();
}

const applyTemplateAllBtn = document.getElementById('applyTemplateAllBtn');
if (applyTemplateAllBtn) {
  applyTemplateAllBtn.onclick = () => applyTemplate('all');
}

const applyTemplatePageBtn = document.getElementById('applyTemplatePageBtn');
if (applyTemplatePageBtn) {
  applyTemplatePageBtn.onclick = () => applyTemplate('page');
}

/* ============================================================
   REDACTION TEMPLATES — LOAD FOR EDITING / OVERWRITE
   ============================================================ */

function loadTemplateForEditing() {
  const sel = document.getElementById('templateSelect');
  if (!sel || !sel.value) {
    alert("Select a template first.");
    return;
  }

  const templateId = parseInt(sel.value, 10);
  if (!templateId) {
    alert("Invalid template.");
    return;
  }

  fetch(`/redactor/template/load/${templateId}`)
    .then(r => r.json())
    .then(d => {
      if (!d.success) {
        alert("Failed to load template: " + (d.error || "Unknown error"));
        return;
      }

      previewBoxes = d.boxes || [];
      drawOverlay();
      alert("Template loaded into preview. Edit boxes, then click 'Overwrite Template'.");
    });
}

function overwriteTemplate() {
  const sel = document.getElementById('templateSelect');
  if (!sel || !sel.value) {
    alert("Select a template first.");
    return;
  }

  const templateId = parseInt(sel.value, 10);
  if (!templateId) {
    alert("Invalid template.");
    return;
  }

  fetch('/redactor/template/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      template_id: templateId,
      filename
    })
  })
    .then(r => r.json())
    .then(d => {
      if (!d.success) {
        alert("Failed to update template: " + (d.error || "Unknown error"));
        return;
      }
      alert("Template updated successfully.");
      loadTemplates();
    });
}

const loadTemplateBtn = document.getElementById('loadTemplateBtn');
if (loadTemplateBtn) {
  loadTemplateBtn.onclick = () => loadTemplateForEditing();
}

const overwriteTemplateBtn = document.getElementById('overwriteTemplateBtn');
if (overwriteTemplateBtn) {
  overwriteTemplateBtn.onclick = () => overwriteTemplate();
}
