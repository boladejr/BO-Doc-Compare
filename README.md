# 📄 DocDiff — Supplier contract risk analysis Tool

A polished local tool that compares two versions of a document and produces a **human-readable, color-coded summary of meaningful changes** — with smart detection of material changes like numbers, dates, monetary values, and legal terms.

---

## ✨ Features

| Feature | Details |
|---|---|
| **File Support** | `.txt`, `.docx`, `.pdf`, `.xlsx` |
| **Diff Types** | Added, Removed, Modified, Moved paragraphs |
| **Material Detection** | 💰 Monetary, 📅 Dates, 🔢 Numbers, ⚖️ Legal terms |
| **Smart Grouping** | Nearby changes clustered together |
| **Ignore Options** | Skip punctuation-only or trivial changes |
| **Export** | Download `.txt` report or styled `.pdf` report |
| **UI** | Clean Streamlit app with red/green/yellow color coding |

---

## 🚀 Setup (5 minutes)

### 1. Prerequisites

Make sure you have **Python 3.9+** installed:
```bash
python3 --version
```

### 2. Create a virtual environment (recommended)

```bash
# Navigate to the project folder
cd doc_comparator

# Create virtual environment
python3 -m venv venv

# Activate it
# macOS / Linux:
source venv/bin/activate

# Windows (Command Prompt):
venv\Scripts\activate.bat

# Windows (PowerShell):
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `streamlit` — the web UI framework
- `python-docx` — reads `.docx` files
- `pdfplumber` — extracts text from PDFs (primary)
- `PyPDF2` — PDF fallback extractor
- `openpyxl` — reads `.xlsx` spreadsheets
- `chardet` — auto-detects text encoding
- `reportlab` — generates styled PDF reports

### 4. Run the app

```bash
streamlit run app.py
```

Your browser will automatically open to `http://localhost:8501`

---

## 🖥️ Usage

1. **Upload** your original document in the **"Old Version"** panel
2. **Upload** your revised document in the **"New Version"** panel
3. Click **🔍 Compare Documents**
4. View results — grouped by proximity, with material changes highlighted first
5. Optionally **download** a `.txt` or `.pdf` report

### Sidebar Options

| Option | Effect |
|---|---|
| **Ignore punctuation-only changes** | Skip diffs that only alter commas, periods, etc. |
| **Show only material changes** | Filter down to numbers, dates, legal terms |
| **Modification sensitivity** | 0.30 = catch subtle rewrites; 0.95 = only near-identical |

---

## 📋 Example Output (Text Report)

```
════════════════════════════════════════════════════════════════════════
  📄  DOCUMENT COMPARISON REPORT
════════════════════════════════════════════════════════════════════════

  Generated : 2024-06-01 14:22:00
  Old File  : contract_v1.docx
  New File  : contract_v2.docx

────────────────────────────────────────────────────────────────────────
  📊  EXECUTIVE SUMMARY
────────────────────────────────────────────────────────────────────────

  Total Changes    : 16
    ✚  Added       : 9
    ✖  Removed     : 3
    ✎  Modified    : 4
    ↕  Moved       : 0

  ⚡ Material Changes : 15   ← numbers, dates, legal terms

────────────────────────────────────────────────────────────────────────
  ⚡  MATERIAL CHANGES  (15 flagged)
────────────────────────────────────────────────────────────────────────

  ✎  MODIFIED  Line 10  (¶4)
  ⚡ Material: 🔢 Number Change, ⚖️  Legal Term
  OLD: "The client shall pay within 30 days of receiving the invoice."
  NEW: "The client shall pay within 15 days of receiving the invoice."
  ≈  96% similar

  ✎  MODIFIED  Line 14  (¶5)
  ⚡ Material: 🔢 Number Change, ⚖️  Legal Term
  OLD: "Termination requires 60 days written notice from either party."
  NEW: "Termination requires 30 days written notice from either party."
  ≈  96% similar

  ✚  ADDED  → Line 43  (¶11)
  ⚡ Material: ⚖️  Legal Term
  ▶  "Client shall indemnify Provider against all third-party claims..."
```

---

## 🧪 Try with Sample Files

Sample contracts are included in `samples/`:

```bash
# They're ready to upload in the UI, or test via CLI:
python3 -c "
from extractor import extract_text
from comparator import compare_documents
from reporter import build_text_report

old = extract_text('old_contract.txt', open('samples/old_contract.txt','rb').read())
new = extract_text('new_contract.txt', open('samples/new_contract.txt','rb').read())
result = compare_documents(old, new)
print(build_text_report(result, 'old_contract.txt', 'new_contract.txt'))
"
```

---

## 📁 Project Structure

```
doc_comparator/
│
├── app.py           # Streamlit UI — main entry point
├── extractor.py     # Text extraction for .txt/.docx/.pdf/.xlsx
├── comparator.py    # Core diff engine + material change detection
├── reporter.py      # Export to .txt and .pdf reports
├── requirements.txt # Python dependencies
├── README.md        # This file
│
└── samples/
    ├── old_contract.txt   # Sample "old" document
    └── new_contract.txt   # Sample "new" document (with deliberate changes)
```

---

## 🔧 Troubleshooting

**App won't start:**
```bash
# Make sure your venv is activated, then:
pip install -r requirements.txt
streamlit run app.py
```

**PDF extraction fails:**
```bash
pip install pdfplumber PyPDF2
```

**PDF export unavailable:**
```bash
pip install reportlab
```

**`.docx` file unreadable:**
```bash
pip install python-docx
```

**Port already in use:**
```bash
streamlit run app.py --server.port 8502
```

---

## 📦 Requirements

- Python 3.9+
- No internet connection needed after install
- Runs 100% locally — your documents never leave your machine
