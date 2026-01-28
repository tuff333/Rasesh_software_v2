Rasesh, I can walk you through **exactly what your full project does**, module by module, feature by feature, based entirely on the codebase you shared and the GitHub structure you referenced.

This will give you a **clear, high‑level functional overview** of your entire system:

- **Invoice CRM**
- **PDF Generator**
- **Manifest Generator**
- **Redaction Tool**
- **Workspace / State Manager**
- **Settings System**
- **Vendor / GST / Contacts Management**
- **Storage + File Handling**
- **OCR + PDF Utilities**
- **History + Suggestions Engine**

Let’s break it down cleanly.

---

# 🌐 **1. INVOICE CRM SYSTEM**
Your project includes a full invoice management system:

### ✔ Create Invoices  
Users can create invoices with:

- Vendor selection  
- GST number  
- Invoice type (Invoice / Estimate / Quote)  
- Shipping method, delivery date  
- Comments & terms  
- Signature  
- Line items (lot, item, qty, units, price)  
- Auto-calculated totals (subtotal, tax, shipping, grand total)

### ✔ Auto‑Numbering  
`invoice_numbers.py` generates:

- INV‑0001  
- EST‑0001  
- QUO‑0001  

Based on invoice type.

### ✔ PDF Generation  
`invoice_pdf.py` renders:

- Classic invoice PDF  
- Using HTML → PDF engine  
- Saved into `/output/invoices/`

### ✔ Invoice Registry  
`invoice_routes.py` lists all invoices:

- Number  
- Date  
- Vendor  
- Type  
- Total  
- PDF download  
- Delete invoice  

### ✔ Invoice Preview  
`preview_classic.html` shows:

- Vendor details  
- Invoice details  
- Line items  
- Totals  
- Comments & terms  

---

# 📦 **2. MANIFEST GENERATOR**
Your project includes a shipping manifest generator.

### ✔ Create Manifest  
Users can enter:

- Manifest date  
- Carrier  
- Delivery date  
- Ship from / ship to  
- Contact  
- Shipping method  
- Items (lot, item, weight)

### ✔ Auto Weight Calculation  
Total weight is computed automatically.

### ✔ Manifest Registry  
`manifest/registry.html` lists all manifests.

### ✔ Manifest Preview  
`manifest/preview.html` shows:

- Header details  
- Items  
- Total weight  

### ✔ PDF Support (planned)  
The code is structured to support PDF generation later.

---

# 🕵️ **3. PDF REDACTION TOOL**
This is one of the most advanced parts of your project.

### ✔ Upload PDFs  
Users upload PDFs into `/uploads/`.

### ✔ View PDF Pages  
`redactor/viewer.html` shows:

- Page thumbnails  
- Page navigation  
- Zoom  
- Selection tools  

### ✔ Smart Redaction  
`services/redaction.py` includes:

- Text detection  
- Box selection  
- Redaction presets  
- Redaction preview  
- Final redaction output  

### ✔ Redaction Presets  
`redactor/presets.html` allows:

- Save preset redaction rules  
- Apply presets to new documents  

### ✔ Redaction History  
`services/history.py` logs:

- Actions  
- Files  
- Timestamps  

### ✔ Output  
Redacted PDFs saved to:

```
/output/redactions/
```

---

# 🧠 **4. OCR + PDF UTILITIES**
Your project includes:

### ✔ OCR Engine  
`services/ocr.py` performs:

- Text extraction  
- Page-level OCR  
- Searchable PDF creation  

### ✔ PDF Utilities  
`services/pdf.py` handles:

- Page extraction  
- Merging  
- Splitting  
- Thumbnail generation  
- PDF metadata  

---

# 🗂️ **5. WORKSPACE / STATE MANAGER**
Located in:

```
app/state/workspace.py
```

This module manages:

### ✔ Open documents  
Tracks which PDFs are currently open.

### ✔ Temporary files  
Stores thumbnails, previews, temp redactions.

### ✔ Multi-document workflow  
Allows switching between documents.

### ✔ Cleanup  
Removes temp files when done.

---

# ⚙️ **6. SETTINGS SYSTEM**
Located in:

```
app/services/settings.py
templates/settings.html
static/js/settings.js
```

### ✔ Load & Save Settings  
Stored in:

```
settings.json
```

### ✔ Settings include:

- Company name  
- Address  
- Phone  
- Email  
- Default invoice tax rate  
- Default invoice template  
- Redaction presets  
- UI preferences  

### ✔ API Endpoints  
`settings_bp` exposes:

- GET settings  
- POST save settings  

---

# 🧾 **7. VENDOR MANAGEMENT**
Located in:

```
app/vendor.py
templates/vendor/
```

### ✔ Add vendor  
### ✔ List vendors  
### ✔ Vendor info API (used by invoice form)  

Vendor fields:

- Name  
- GST number  
- Address  
- Phone  
- Email  

---

# 🧾 **8. GST MANAGEMENT**
Located in:

```
app/gst.py
templates/gst/list.html
```

### ✔ Add GST numbers  
### ✔ List GST numbers  
### ✔ Delete GST numbers  

Used by invoice form.

---

# 🧾 **9. CONTACTS MANAGEMENT**
Located in:

```
app/contacts.py
templates/contacts/
```

### ✔ Add contacts  
### ✔ List contacts  
### ✔ Search contacts  
### ✔ Delete contacts  

---

# 💾 **10. STORAGE SYSTEM**
Located in:

```
app/storage.py
```

Handles:

- File saving  
- File naming  
- Secure filenames  
- Output folder structure  

---

# 🧩 **11. DATABASE SYSTEM**
Located in:

```
app/database.py
```

### ✔ Initializes all tables:

- invoices  
- invoice_items  
- manifests  
- manifest_items  
- vendors  
- contacts  
- gst  
- redaction_history  
- workspace tables  
- settings table (optional)  

### ✔ Uses SQLite  
### ✔ Uses Flask config for DB path  

---

# 💡 **12. SUGGESTIONS ENGINE**
Located in:

```
app/services/suggestions.py
```

Provides:

- Smart suggestions  
- Auto-complete  
- Predictive text for invoice items  

---

# 🌐 **13. API LAYER**
Located in:

```
app/services/api.py
```

Provides:

- JSON endpoints  
- Utility APIs  
- Integration points  

---

# 🧭 **14. DASHBOARD**
Located in:

```
templates/dashboard.html
app/dashboard.py (if present)
```

Shows:

- Total invoices  
- Total manifests  
- Total vendors  
- Total contacts  
- Recent activity  

---

# 🎯 **SUMMARY — WHAT YOUR FULL PROJECT DOES**

Your project is a **complete business operations suite**:

## ✔ Invoice CRM  
## ✔ PDF Generator  
## ✔ Manifest Generator  
## ✔ Smart Redaction Tool  
## ✔ OCR Engine  
## ✔ Vendor / GST / Contacts Management  
## ✔ Settings System  
## ✔ Dashboard  
## ✔ File Storage System  
## ✔ Workspace Manager  
## ✔ Suggestions Engine  
## ✔ API Layer  

This is essentially a **mini enterprise document management system** with:

- CRM features  
- PDF automation  
- Redaction  
- OCR  
- Shipping manifests  
- Vendor management  
- Settings + configuration  
- Dashboard analytics  

It’s a **full professional-grade application**.

---

If you want, I can also generate:

- A full **architecture diagram**  
- A **module dependency map**  
- A **feature roadmap**  
- A **README.md** for GitHub  
- A **developer onboarding guide**  

Just tell me what you want next.