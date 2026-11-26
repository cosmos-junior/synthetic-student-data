# Privacy-Aware Synthetic Student Data Generation and Evaluation Framework

A full-stack research and software platform for generating synthetic student and institutional tabular datasets and evaluating them across statistical fidelity, empirical privacy risk, and leak-free downstream machine-learning utility.

## Models Compared
- **Gaussian Copula** (`sdv.single_table.GaussianCopulaSynthesizer`)
- **CTGAN** (`sdv.single_table.CTGANSynthesizer`)
- **TVAE** (`sdv.single_table.TVAESynthesizer`)

## Research Aim & Objectives
To design and develop a privacy-aware framework for generating and evaluating synthetic student academic datasets for research and machine-learning applications:
1. Analyze structural, statistical, and relational characteristics of student academic data (`schema.py`, `validation.py`, `profiling.py`).
2. Implement synthetic tabular data generation using Gaussian Copula, CTGAN, and TVAE with deterministic domain post-processing (`generation_utils.py`).
3. Evaluate synthetic datasets across statistical fidelity (`SDMetrics`), empirical privacy risk (`NewRowSynthesis`, `DCRBaselineProtection`, `DisclosureProtection`, nearest-neighbor DCR, duplicate detection, membership inference indicator), and leak-free TRTR/TSTR ML utility (`evaluate_models.py`).
4. Provide a web platform (`backend/` + `frontend/`) enabling authorized users to upload datasets, review/confirm SDV metadata, run experiments, inspect interactive dashboards, and export CSVs and PDF reports.

## Architecture & Repository Structure
- `src/synthetic_data/`: Core ML/data-science pipeline (`schema.py`, `validation.py`, `profiling.py`, `configure_metadata.py`, `generation_utils.py`, `generate_gaussian_copula.py`, `generate_ctgan.py`, `generate_tvae.py`, `evaluate_models.py`, `visualize_evaluation.py`).
- `backend/`: Django + Django REST Framework API (`datasets` app, token auth, ownership isolation, Celery/Redis background tasks, ReportLab PDF export, OpenAPI/Swagger at `/api/docs/`).
- `frontend/`: React + TypeScript + Vite + Tailwind CSS + Recharts + TanStack Query + React Router + React Hook Form + Zod hybrid dashboard.
- `tests/`: Automated Python unit tests (`pytest`).
- `docs/`: Technical reports and codebase guides.

## Technology Stack
- **Data Science & ML:** Python 3.11, pandas, NumPy, SDV (`2.2.0`), SDMetrics (`0.33.0`), scikit-learn, Matplotlib, Seaborn
- **Backend:** Django 5, Django REST Framework, Celery, Redis, drf-spectacular, ReportLab, SQLite (dev) / PostgreSQL (production via env vars)
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, React Router, TanStack Query, React Hook Form, Zod

## Setup & Running Locally

### 1. Python Environment
```powershell
python -m venv .class
.\.class\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r backend\requirements.txt
```
Copy `.env.example` to `.env` and set secrets/database settings as needed.

### 2. Backend (Django REST API)
```powershell
.\.class\Scripts\python backend\manage.py migrate
.\.class\Scripts\python backend\manage.py createsuperuser
.\.class\Scripts\python backend\manage.py runserver
```
Optional Celery worker (when `CELERY_TASK_ALWAYS_EAGER=false` and Redis is running):
```powershell
cd backend
..\.class\Scripts\celery -A config worker --loglevel=info
```
Swagger API documentation is available at `http://127.0.0.1:8000/api/docs/`.

### 3. Frontend (React + TypeScript)
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

## Running Automated Tests
```powershell
# Python ML/data-science unit tests
.\.class\Scripts\pytest -v

# Django REST API, ownership, upload, and workflow tests
.\.class\Scripts\python backend\manage.py test datasets -v 2

# Frontend TypeScript & Vite production build
cd frontend && npm run build
```

## Data Protection & Limitations
- Direct identifiers (`student_id`, etc.) are excluded from synthesizer training and regenerated synthetically (`IN1700001`–`IN1700500` for student records).
- Exported CSVs are neutralized against CSV formula injection.
- Uploaded institutional CSVs are stored privately on disk and filtered per-user (`owner=request.user` / `created_by=request.user`).
- **Privacy disclaimer:** `NewRowSynthesis`, `DCRBaselineProtection`, `DisclosureProtection`, and nearest-neighbor DCR are empirical privacy-risk indicators, **not** formal Differential Privacy ($\epsilon, \delta$) guarantees.
- **Post-processing note:** Deterministic post-processing of derived student academic fields (`final_score`, `grade`, `academic_status`) alters joint statistics; all final evaluations are computed on the post-processed dataset.
