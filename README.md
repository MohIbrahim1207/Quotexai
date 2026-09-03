# AI PDF → Excel Quotation Converter (QuotexAI)

Production-ready enterprise B2B web application that automatically extracts structured quotation information from supplier PDF quotations, validates prices and part numbers against source documents, and fills existing formatted Excel templates while preserving 100% of formatting, formulas, styles, and leading zeros.

---

## 🌟 Key Features

* **Zero-Loss Part Number Retention**: Automatically enforces text-mode `@` formatting for part numbers (`00138737`, `02174072`, `02305474`) so leading zeros are never stripped or converted to numbers.
* **100% Excel Template Preservation**: Preserves merged cells, formulas (`=D14*F14`, `=SUM(...)`), custom fonts, border styles, column widths, row heights, print settings, and branding.
* **Deterministic Multi-Step Validation Engine**: Validates AI extractions against raw PyMuPDF text, checks price arithmetic , verifies grand totals, and computes field-level confidence ratings (`✓ Verified`, `⚠ Review`, `✕ Error`).
* **Equipment & Machine Grouping**: Automatically identifies and groups line items associated with specific equipment or serial numbers 
* **Dynamic Pricing & Margin Modes**: Support for 3 distinct pricing strategies:
  1. *Quoted PDF Price* (Raw supplier pricing)
  2. *Supplier Discount* (Net cost deduction)
  3. *Target Margin* (Transparent customer selling price calculation)
* **Interactive B2B Review Screen**: Full in-place cell editing for all fields, add/remove line items, live totals recalculation, and instant Excel generation.
* **Flexible Column Mapping Layer**: Auto-detects table headers and supports manual column adjustments.

---

## 🏗 Architecture & Tech Stack

```text
┌─────────────────────────────────────────────────────────────┐
│                   React + Vite + TypeScript                 │
│     (Drag-and-Drop Upload, Editable Review Table, Badges)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST API
┌──────────────────────────────▼──────────────────────────────┐
│                     FastAPI Backend                         │
│  ├── PDF Service (PyMuPDF / fitz, pdfplumber, OCR fallback) │
│  ├── AI Service (GeminiProvider with fallback parser)       │
│  ├── Validation Engine (Deterministic arithmetic & text)    │
│  └── Excel Engine (openpyxl with style cloning & @ format)  │
└─────────────────────────────────────────────────────────────┘
```

* **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Lucide React, Axios.
* **Backend**: Python 3.12, FastAPI, Uvicorn, Pydantic v2, PyMuPDF (`fitz`), openpyxl, google-genai, pytest.
* **AI Provider**: Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`) with clean provider abstraction.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables (optional for live Gemini)
cp ../.env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start backend server
uvicorn app.main:app --reload --port 8000
```
Backend will be available at: `http://localhost:8000` (Swagger docs at `http://localhost:8000/docs`).

### 3. Frontend Setup
```bash
cd frontend

# Install npm packages
npm install

# Start development server
npm run dev
```
Frontend will be available at: `http://localhost:5173`.

---

## 🧪 Running Automated Tests

Run the backend test suite:
```bash
cd backend
pytest -v
```

Tests include:
* `test_part_numbers.py`: Verifies leading zero retention in schemas, regex parsing, and openpyxl `@` cell writing.
* `test_validation.py`: Tests arithmetic mismatch detection, missing part numbers, and confidence scoring.
* `test_pdf_and_excel.py`: Complete end-to-end integration test against the DMN India quotation (`Quote_41260607.pdf`) and Excel template (`ENQ-2026-07-2549.xlsx`).

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health status and AI configuration check |
| `POST` | `/api/quotation/upload-pdf` | Uploads supplier PDF quotation |
| `POST` | `/api/quotation/upload-template` | Uploads Excel quotation template |
| `POST` | `/api/quotation/extract` | Extracts structured items using Gemini AI & validation engine |
| `POST` | `/api/quotation/validate` | Re-validates updated quotation data |
| `POST` | `/api/quotation/analyze-template` | Auto-detects headers from Excel template |
| `POST` | `/api/quotation/generate` | Generates formatted `.xlsx` file |
| `GET` | `/api/quotation/download/{file_id}` | Serves downloadable Excel file |

---

## 🚢 Production Deployment

### Backend Deployment (Render)
1. Push repository to GitHub.
2. In Render, create a **Web Service** pointing to the repository root.
3. Configure settings:
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - `GEMINI_API_KEY`: `your_gemini_api_key`
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `FRONTEND_URL`: `https://your-frontend-app.vercel.app`

### Frontend Deployment (Vercel)
1. In Vercel, import your repository.
2. Set **Root Directory** to `frontend`.
3. Add Environment Variable:
   - `VITE_API_URL`: `https://your-backend-app.onrender.com`
4. Deploy.

---

## 🔒 Security Best Practices
- Never hardcodes API keys in source code or frontend bundles.
- Uploaded files are strictly validated by MIME type, extension (`.pdf`, `.xlsx`, `.xlsm`), and file size limits.
- Temporary files are isolated in working directories.
- Full CORS origin protection.
