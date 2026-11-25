# Synthetic Student Data Project: Detailed Codebase & Architecture Guide

**Project:** Privacy-Aware Synthetic Student Data Generation and Evaluation Framework  
**Purpose:** This guide explains every file in the repository, what each function does, how data flows through the pipeline, and why key design decisions were made.

---

## 1. End-to-End Pipeline Overview

The project is structured as a modular Python pipeline under `src/synthetic_data/`:

1. **Schema & Validation (`schema.py`, `validation.py`)**: Defines the exact structure, value ranges, categories, and deterministic grading formulas, and verifies that any dataset obeys them.
2. **Source Data & Exploration (`generate_demo_data.py`, `analyze_data.py`)**: Creates a 500-row simulated student dataset for development and inspects its statistical properties.
3. **Training Data Preparation (`prepare_training_data.py`)**: Removes `student_id` so generative models do not memorize or model unique identifiers.
4. **SDV Metadata Configuration (`configure_metadata.py`)**: Builds and validates an SDV `Metadata` object describing column types (`numerical`, `categorical`, `ordinal`).
5. **Shared Generation Pipeline (`generation_utils.py`)**: Provides a single reusable workflow for training, sampling, deterministic post-processing, ID generation, CSV export, and validation.
6. **Generative Models (`generate_gaussian_copula.py`, `generate_ctgan.py`, `generate_tvae.py`)**: Trains and samples 500 synthetic student records from three different model families and saves them to `outputs/`.

---

## 2. Project Configuration & Documentation

### 2.1 `requirements.txt`
Lists the Python libraries required for data manipulation, synthetic data generation, evaluation, notebooks, and testing:
- **Core data science:** `numpy`, `pandas`, `scipy`, `scikit-learn`
- **Visualization:** `matplotlib`, `seaborn`
- **Synthetic data & evaluation:** `sdv` (installed version `2.2.0`), `sdmetrics`
- **Development & testing:** `jupyterlab`, `pytest`

### 2.2 `README.md`
Documents the project's research aim, specific objectives, the three models to compare (**Gaussian Copula**, **CTGAN**, and **TVAE**), and the three evaluation dimensions (**statistical fidelity**, **privacy risk**, and **downstream ML utility**), along with setup instructions and data-protection guidelines.

---

## 3. Domain Schema & Data Validation

### 3.1 `src/synthetic_data/schema.py`
Acts as the **single source of truth** for all dataset rules so that data generation, validation, and post-processing never drift out of sync.

- **Column definitions:**
  - `ID_COLUMN = "student_id"`
  - `NUMERIC_COLUMNS`: `age`, `year_of_study`, `attendance_percentage`, `coursework_score`, `exam_score`, `final_score`
  - `CATEGORICAL_COLUMNS`: `gender`, `programme`, `grade`, `academic_status`
  - `REQUIRED_COLUMNS`: combines `ID_COLUMN`, `NUMERIC_COLUMNS`, and `CATEGORICAL_COLUMNS` (11 columns total)
- **Allowed categories:**
  - `PROGRAMMES = ["BIT", "BCS", "BBIT", "BSE"]`
  - `GENDERS = ["Male", "Female"]`
  - `GRADES = ["A", "B", "C", "D", "E"]`
  - `ACADEMIC_STATUSES = ["Pass", "Fail"]`
- **Numeric ranges (`COLUMN_RANGES`):**
  - `age`: `(17, 35)`
  - `year_of_study`: `(1, 4)`
  - `attendance_percentage`, `coursework_score`, `exam_score`, `final_score`: `(0, 100)`
- **Grading constants & helper functions:**
  - `PASS_MARK = 40`, `COURSEWORK_WEIGHT = 0.40`, `EXAM_WEIGHT = 0.60`
  - `determine_grade(score)`: maps `>= 70` to `"A"`, `>= 60` to `"B"`, `>= 50` to `"C"`, `>= 40` to `"D"`, and `< 40` to `"E"`.
  - `determine_status(score)`: returns `"Pass"` if `score >= 40`, else `"Fail"`.

### 3.2 `src/synthetic_data/validation.py`
Contains `validate_student_data(data: pd.DataFrame) -> list`, which validates any student DataFrame against `schema.py` and returns a list of human-readable error strings (an empty list means all checks passed).

**Checks performed in order:**
1. **Required columns:** Verifies all 11 `REQUIRED_COLUMNS` are present; returns early if any are missing to avoid `KeyError` in later checks.
2. **Non-empty dataset:** Ensures `data.empty` is `False`; returns early if empty.
3. **Missing values:** Checks `data[REQUIRED_COLUMNS].isna().any().any()`.
4. **Unique student IDs:** Checks `data["student_id"].duplicated().any()`.
5. **Numeric types & ranges:** Confirms each column in `NUMERIC_COLUMNS` has a numeric dtype and lies within `COLUMN_RANGES[column]`.
6. **Whole-number constraint:** Confirms `age` and `year_of_study` have no fractional parts (`data[column] % 1 == 0`).
7. **Valid categories:** Confirms `gender`, `programme`, `grade`, and `academic_status` only contain allowed values from `schema.py`.
8. **Weighted final score:** Recomputes `(coursework_score * 0.40 + exam_score * 0.60).round(2)` and compares it to `final_score.round(2)`.
9. **Grade & status consistency:** Recomputes expected grades via `determine_grade` and expected status via `determine_status` and verifies they match `data["grade"]` and `data["academic_status"]`.

---

## 4. Source Data Generation, Exploration & Preparation

### 4.1 `src/synthetic_data/generate_demo_data.py`
Creates a reproducible simulated development dataset (`number_of_students=500`, `random_seed=42`) so the pipeline can be built and tested without exposing real institutional student records.

**How `generate_demo_data` works:**
- Uses `np.random.default_rng(random_seed)` for reproducibility.
- Samples `gender` (`52%` Male, `48%` Female), `programme` (`35%` BIT, `25%` BCS, `20%` BBIT, `20%` BSE), and `year_of_study` (`1`–`4` with probabilities `0.30, 0.27, 0.24, 0.19`).
- Generates `age` from a normal distribution centered at `19 + year * 1.1` (std `2.2`), clipped to `[17, 35]` and rounded to integers.
- Introduces a latent `ability` variable (`Normal(0, 1)`) so that `attendance_percentage`, `coursework_score`, and `exam_score` share realistic positive correlation instead of being independent noise.
- Computes `final_score`, `grade`, and `academic_status` using `COURSEWORK_WEIGHT`, `EXAM_WEIGHT`, `determine_grade`, and `determine_status` from `schema.py`.
- Generates sequential IDs (`IN1700001`–`IN1700500`).
- `save_demo_data(data)` writes the result to `data/raw/demo_student_data.csv`.

### 4.2 `src/synthetic_data/analyze_data.py`
Provides exploratory data analysis via `analyze_dataset()` on `data/raw/demo_student_data.csv`:
- Prints dataset shape and column data types (`data.dtypes`).
- Prints numerical summary statistics (`data.describe().round(2)`).
- Prints value counts for `gender`, `programme`, `grade`, and `academic_status`.
- Computes and prints the numerical correlation matrix (`numerical_data.corr().round(3)`).
- Checks for missing values (`data.isnull().sum()`) and duplicate `student_id`s.

### 4.3 `src/synthetic_data/prepare_training_data.py`
Prepares the raw dataset for generative modeling via `prepare_training_data()`:
- Reads `data/raw/demo_student_data.csv` (500 rows, 11 columns).
- Drops `student_id` (`data.drop(columns=["student_id"])`), leaving 10 modeling columns.
  - *Why:* Unique IDs carry no statistical pattern for tabular synthesizers and should never be memorized or leaked by a generative model.
- Saves the processed table to `data/processed/student_training_data.csv`.

---

## 5. SDV Metadata & Shared Generation Pipeline

### 5.1 `src/synthetic_data/configure_metadata.py`
Configures the schema metadata required by SDV (`sdv==2.2.0`):
- Reads `data/processed/student_training_data.csv`.
- Calls `Metadata.detect_from_dataframes({"student_records": data}, infer_sdtypes=True, infer_keys=None, verbose=True)` to auto-detect column types and numerical ranges/decimal places.
- Explicitly enforces `sdtype="categorical"` for `gender`, `programme`, `grade`, and `academic_status`, and `sdtype="ordinal"` for `year_of_study`.
- Calls `metadata.validate()`, prints the metadata dictionary, and returns the `Metadata` object.

### 5.2 `src/synthetic_data/generation_utils.py`
Centralizes the shared training, sampling, post-processing, saving, and validation workflow in `run_synthesizer_pipeline(...)` so the three model scripts do not duplicate code.

**Step-by-step execution:**
1. Loads `data/processed/student_training_data.csv`.
2. Calls `configure_metadata()` to get the validated SDV `Metadata`.
3. Builds the model using `synthesizer_factory(metadata)` and trains it with `synthesizer.fit({"student_records": training_data})`.
4. Samples `number_of_rows` records using `synthesizer.sample(num_rows=number_of_rows)`. Because SDV `2.2.0` returns `dict[str, pd.DataFrame]` when using `Metadata.detect_from_dataframes`, it unwraps `sampled_data["student_records"]`.
5. **Deterministic post-processing:** Recomputes `final_score`, `grade`, and `academic_status` from the sampled `coursework_score` and `exam_score` using `COURSEWORK_WEIGHT`, `EXAM_WEIGHT`, `determine_grade`, and `determine_status`.
   - *Why:* Generative models sample columns probabilistically with noise. Without post-processing, sampled `final_score`, `grade`, and `academic_status` values frequently contradict the exact academic formula.
6. Inserts fresh synthetic `student_id` values (`IN1700001`–`IN1700500`) at column index `0`.
7. Saves the dataset to `outputs/<output_filename>` and runs `validate_student_data(synthetic_data)`, printing validation results, the first five rows, and a numerical summary.

---

## 6. The Three Generative Models

| Model | File | SDV Synthesizer | Key Parameters | Output CSV |
|---|---|---|---|---|
| **Gaussian Copula** | `src/synthetic_data/generate_gaussian_copula.py` | `GaussianCopulaSynthesizer` | `enforce_min_max_values=True`, `enforce_rounding=True` | `outputs/gaussian_copula_synthetic.csv` |
| **CTGAN** | `src/synthetic_data/generate_ctgan.py` | `CTGANSynthesizer` | `epochs=300`, `batch_size=500`, `enforce_min_max_values=True`, `enforce_rounding=True`, `verbose=True` | `outputs/ctgan_synthetic.csv` |
| **TVAE** | `src/synthetic_data/generate_tvae.py` | `TVAESynthesizer` | `epochs=300`, `batch_size=500`, `enforce_min_max_values=True`, `enforce_rounding=True`, `verbose=True` | `outputs/tvae_synthetic.csv` |

### How Each Model Differs
- **Gaussian Copula (`generate_gaussian_copula.py`):** A classical statistical model that fits marginal distributions to each column and models correlations in Gaussian space. It is fast, requires no neural-network training loop, and closely preserved the training dataset's means, standard deviations, and category proportions.
- **CTGAN (`generate_ctgan.py`):** A deep-learning Generative Adversarial Network (GAN) designed for tabular data using conditional sampling to handle imbalanced categories. Trained for 300 epochs with `batch_size=500`. It preserved `gender` and `programme` distributions well, though it shifted `exam_score` upward and `attendance_percentage` downward.
- **TVAE (`generate_tvae.py`):** A deep-learning Variational Autoencoder (VAE) for tabular data that encodes rows into a latent Gaussian distribution and reconstructs them. Trained for 300 epochs with `batch_size=500`. On this 500-row dataset, it produced narrower numerical variance and exhibited category mode collapse on `programme` (`91.4%` `BIT`, `8.6%` `BCS`, `0%` `BSE`/`BBIT`).

---

## 7. Commands to Run the Full Pipeline

```powershell
# 1. Generate raw demo data
.\.class\Scripts\python -m src.synthetic_data.generate_demo_data

# 2. Explore raw data
.\.class\Scripts\python -m src.synthetic_data.analyze_data

# 3. Prepare training data (drops student_id)
.\.class\Scripts\python -m src.synthetic_data.prepare_training_data

# 4. Inspect SDV metadata
.\.class\Scripts\python -m src.synthetic_data.configure_metadata

# 5. Generate & validate synthetic datasets
.\.class\Scripts\python -m src.synthetic_data.generate_gaussian_copula
.\.class\Scripts\python -m src.synthetic_data.generate_ctgan
.\.class\Scripts\python -m src.synthetic_data.generate_tvae
```
