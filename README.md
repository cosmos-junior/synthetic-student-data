# Privacy-Aware Synthetic Student Data Generation and Evaluation Framework

A research and software project for generating synthetic student academic tabular data and evaluating it across statistical fidelity, privacy risk, and downstream machine-learning utility.

## Models to compare
- Gaussian Copula
- CTGAN (Conditional Tabular GAN)
- TVAE (Tabular Variational Autoencoder)

## Research aim
To design and develop a privacy-aware framework for generating and evaluating synthetic student academic datasets for research and machine-learning applications.

## Specific objectives
1. To investigate existing synthetic tabular data generation techniques and analyze the structural, statistical, and relational characteristics of student academic data.
2. To design and implement a synthetic student academic data generation framework using Gaussian Copula, CTGAN, and TVAE.
3. To evaluate the generated synthetic student academic datasets in terms of statistical fidelity, privacy risk, and downstream machine-learning utility.
4. To develop a user-facing platform that enables authorized users to generate synthetic student academic datasets and view comparative evaluation results.

## Evaluation dimensions

| Dimension | Focus |
|---|---|
| Statistical fidelity | Distributions, correlations, ranges, and multivariate relationships |
| Privacy risk | Similarity to source records and feasible disclosure or inference risks |
| ML utility | Performance on selected downstream machine-learning tasks |

Synthetic data is not automatically anonymous or privacy-safe. This project treats privacy as an evaluation dimension and will report limitations transparently.

## Planned technology stack
- Data science: Python, pandas, NumPy, SDV, SDMetrics, scikit-learn
- Backend: Django and Django REST Framework
- Frontend: React and TypeScript
- Database: PostgreSQL
- Possible background processing: Celery and Redis

## Repository structure
- `backend/`: Django REST API (planned)
- `frontend/`: React + TypeScript client (planned)
- `data/`: local source and processed datasets
- `docs/`: research and technical documentation
- `notebooks/`: exploratory analysis
- `src/synthetic_data/`: reusable generation and evaluation code
- `tests/`: automated tests

## Getting started (Windows CMD)

Python 3.11 is recommended for the initial data-science environment.

```cmd
git clone https://github.com/cosmos-junior/synthetic-student-data.git
cd synthetic-student-data
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify the installation:

```cmd
python -c "import pandas, sdv, sdmetrics; print('Environment ready')"
```

## Data protection
- Do not commit identifiable student records, institutional exports, credentials, API keys, or environment files.
- Keep raw datasets outside version control.
- Confirm dataset licensing and obtain institutional authorization where required.
- Document preprocessing, model settings, random seeds, and evaluation procedures.
- Use artificial fixtures in automated tests.

## Development status
Initial repository scaffold. The next implementation stage is to establish a validated student academic data schema and test the generation models before building the web platform.

## License
No license has been selected yet. All rights remain with the repository owner until a license is added.
