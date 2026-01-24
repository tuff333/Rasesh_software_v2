// Sidebar navigation
document.querySelectorAll('.settings-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.settings-btn')
      .forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.querySelectorAll('.settings-panel')
      .forEach(p => p.classList.remove('active'));

    const target = btn.dataset.target;
    document.getElementById(`panel-${target}`).classList.add('active');
  });
});

let currentSettings = null;

// Load settings data
fetch("/settings/data")
  .then(r => r.json())
  .then(s => {
    currentSettings = s;
    initGeneralSettings(s);
    renderShortcutList(s.shortcuts || {});
  });

function initGeneralSettings(s) {
  document.getElementById("set-theme").value = s.theme || "light";
  document.getElementById("set-upload-folder").value = s.upload_folder || "redaction";
  document.getElementById("set-ocr-default").checked = !!s.ocr_default;
  document.getElementById("set-zoom-mode").value = s.zoom_mode || "fit-width";
  document.getElementById("set-show-tips").checked = s.show_tips !== false;

  document.getElementById("set-output-redactions").value = s.output_redactions || "output/redactions";
  document.getElementById("set-output-invoices").value = s.output_invoices || "output/invoices";
  document.getElementById("set-output-manifests").value = s.output_manifests || "output/manifests";
}

// Render shortcuts list
function renderShortcutList(shortcuts) {
  const container = document.getElementById("shortcut-list");
  container.innerHTML = "";

  const labels = {
    prev_page: "Previous Page",
    next_page: "Next Page",
    undo: "Undo",
    clear: "Clear All",
    apply: "Apply Redactions",
    zoom_in: "Zoom In",
    zoom_out: "Zoom Out",
    zoom_reset: "Reset Zoom",
    toggle_thumbs: "Toggle Thumbnails",
    toggle_ocr: "Toggle OCR"
  };

  Object.keys(labels).forEach(key => {
    const row = document.createElement("div");
    row.className = "d-flex justify-content-between align-items-center mb-2";

    const label = document.createElement("span");
    label.textContent = labels[key];

    const btn = document.createElement("button");
    btn.className = "btn btn-sm btn-outline-primary";
    btn.textContent = shortcuts[key] || "";
    btn.dataset.action = key;

    btn.onclick = () => captureShortcut(btn);

    row.appendChild(label);
    row.appendChild(btn);
    container.appendChild(row);
  });

  document.getElementById("reset-shortcuts").onclick = () => {
    fetch("/settings/data")
      .then(r => r.json())
      .then(s => {
        renderShortcutList(s.shortcuts || {});
      });
  };
}

// Capture shortcut
function captureShortcut(btn) {
  btn.textContent = "Press keys...";
  btn.disabled = true;

  function handler(e) {
    e.preventDefault();

    const parts = [];
    if (e.ctrlKey) parts.push("Ctrl");
    if (e.shiftKey) parts.push("Shift");
    if (e.altKey) parts.push("Alt");

    let key = e.key;
    if (key === " ") key = "Space";
    if (key === "ArrowLeft" || key === "ArrowRight" || key === "ArrowUp" || key === "ArrowDown") {
      parts.push(key);
    } else if (!["Control", "Shift", "Alt"].includes(key)) {
      parts.push(key.length === 1 ? key.toUpperCase() : key);
    }

    const combo = parts.join("+");
    btn.textContent = combo || "(none)";
    btn.disabled = false;

    document.removeEventListener("keydown", handler);
  }

  document.addEventListener("keydown", handler);
}

// Save settings
function saveSettings() {
  const shortcuts = {};
  document.querySelectorAll("#shortcut-list button[data-action]").forEach(btn => {
    shortcuts[btn.dataset.action] = btn.textContent;
  });

  const data = {
    theme: document.getElementById("set-theme").value,
    upload_folder: document.getElementById("set-upload-folder").value,
    ocr_default: document.getElementById("set-ocr-default").checked,
    zoom_mode: document.getElementById("set-zoom-mode").value,
    show_tips: document.getElementById("set-show-tips").checked,

    output_redactions: document.getElementById("set-output-redactions").value,
    output_invoices: document.getElementById("set-output-invoices").value,
    output_manifests: document.getElementById("set-output-manifests").value,

    shortcuts
  };

  fetch("/settings/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        alert("Settings saved!");
      }
    });
}

// Add Save Button
const footer = document.createElement("div");
footer.innerHTML = `
  <div class="text-end mt-4">
    <button class="btn btn-primary">Save Settings</button>
  </div>
`;
document.querySelector(".settings-content").appendChild(footer);
footer.querySelector("button").onclick = saveSettings;
