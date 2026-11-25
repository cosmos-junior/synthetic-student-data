# Synthetic Student Data Generation: Implementation & Model Results Report

**Project:** Privacy-Aware Synthetic Student Data Generation and Evaluation Framework  
**Library:** SDV (`sdv==2.2.0`), pandas, NumPy  
**Training Dataset:** `data/processed/student_training_data.csv` (500 rows, 10 modeling columns)

---

## 1. Architecture & Shared Implementation

All three models share a unified schema, metadata configuration, generation pipeline, deterministic post-processing, and validation suite.

### 1.1 Schema & Domain Constraints (`src/synthetic_data/schema.py`)
- **Identifier column:** `student_id` (excluded from model training; generated post-sampling as `IN1700001`–`IN1700500`)
- **Numeric columns & bounds:**
  - `age`: `[17, 35]` (whole numbers)
  - `year_of_study`: `[1, 4]` (whole numbers, modeled as `ordinal`)
  - `attendance_percentage`: `[0, 100]`
  - `coursework_score`: `[0, 100]`
  - `exam_score`: `[0, 100]`
  - `final_score`: `[0, 100]`
- **Categorical columns:**
  - `gender`: `["Male", "Female"]`
  - `programme`: `["BIT", "BCS", "BBIT", "BSE"]`
  - `grade`: `["A", "B", "C", "D", "E"]`
  - `academic_status`: `["Pass", "Fail"]`
- **Deterministic academic rules:**
  - `final_score = round(coursework_score * 0.40 + exam_score * 0.60, 2)`
  - `grade`: `A` ($\ge 70$), `B` ($\ge 60$), `C` ($\ge 50$), `D` ($\ge 40$), `E` ($< 40$)
  - `academic_status`: `Pass` if `final_score >= 40`, else `Fail`

### 1.2 Metadata Configuration (`src/synthetic_data/configure_metadata.py`)
- Uses `sdv.metadata.Metadata.detect_from_dataframes({"student_records": data}, infer_sdtypes=True, infer_keys=None)`.
- Explicitly sets `gender`, `programme`, `grade`, `academic_status` to `sdtype="categorical"` and `year_of_study` to `sdtype="ordinal"`.
- Validates metadata with `metadata.validate()`.

### 1.3 Shared Generation Pipeline (`src/synthetic_data/generation_utils.py`)
`run_synthesizer_pipeline(...)` executes the same workflow for each model:
1. Load `data/processed/student_training_data.csv` (500 rows, 10 columns).
2. Configure SDV `Metadata` via `configure_metadata()`.
3. Instantiate and fit the synthesizer on `{"student_records": training_data}`.
4. Sample `num_rows=500` records (`synthesizer.sample(num_rows=500)`), unwrapping the `"student_records"` DataFrame from the returned dictionary.
5. **Post-processing derived columns:** Recompute `final_score`, `grade`, and `academic_status` deterministically from `coursework_score` and `exam_score`.
   - *Why:* Statistical synthesizers sample all columns jointly with noise, which initially caused `final_score`, `grade`, and `academic_status` to violate the exact academic formulas. Post-processing guarantees 100% domain consistency.
6. Insert synthetic `student_id` values (`IN1700001`–`IN1700500`).
7. Save to `outputs/<model>_synthetic.csv` and run `validate_student_data(...)` (`src/synthetic_data/validation.py`).

---

## 2. Models Implemented

| Model | SDV Class | Script | Key Settings | Output File | Validation |
|---|---|---|---|---|---|
| **Gaussian Copula** | `GaussianCopulaSynthesizer` | `src/synthetic_data/generate_gaussian_copula.py` | `enforce_min_max_values=True`, `enforce_rounding=True` | `outputs/gaussian_copula_synthetic.csv` | Passed (0 errors) |
| **CTGAN** | `CTGANSynthesizer` | `src/synthetic_data/generate_ctgan.py` | `epochs=300`, `batch_size=500`, `enforce_min_max_values=True`, `enforce_rounding=True` | `outputs/ctgan_synthetic.csv` | Passed (0 errors) |
| **TVAE** | `TVAESynthesizer` | `src/synthetic_data/generate_tvae.py` | `epochs=300`, `batch_size=500`, `enforce_min_max_values=True`, `enforce_rounding=True` | `outputs/tvae_synthetic.csv` | Passed (0 errors) |

---

## 3. Comparative Results (500 Records Each)

### 3.1 Numerical Summary (`mean ± std [min, max]`)

| Column | Training Data | Gaussian Copula | CTGAN | TVAE |
|---|---|---|---|---|
| `age` | `21.29 ± 2.46 [17.00, 30.00]` | `21.04 ± 2.42 [17.00, 28.00]` | `21.09 ± 3.07 [17.00, 30.00]` | `21.67 ± 2.14 [17.00, 28.00]` |
| `year_of_study` | `2.35 ± 1.10 [1.00, 4.00]` | `2.20 ± 1.04 [1.00, 4.00]` | `2.27 ± 1.09 [1.00, 4.00]` | `2.10 ± 1.02 [1.00, 4.00]` |
| `attendance_percentage` | `76.42 ± 11.84 [39.13, 100.00]` | `76.25 ± 12.20 [40.01, 100.00]` | `66.26 ± 14.21 [39.13, 100.00]` | `76.70 ± 8.97 [54.88, 100.00]` |
| `coursework_score` | `57.28 ± 14.59 [5.91, 92.93]` | `57.04 ± 14.83 [11.75, 92.93]` | `59.23 ± 20.63 [6.86, 92.93]` | `59.56 ± 13.47 [20.41, 92.93]` |
| `exam_score` | `54.02 ± 17.76 [5.30, 100.00]` | `52.80 ± 18.17 [5.30, 100.00]` | `69.15 ± 23.50 [5.30, 100.00]` | `56.76 ± 14.38 [5.30, 92.11]` |
| `final_score` | `55.33 ± 14.69 [5.54, 96.90]` | `54.49 ± 15.19 [7.88, 95.56]` | `65.18 ± 15.91 [12.33, 97.17]` | `57.88 ± 12.15 [16.13, 86.08]` |

### 3.2 Categorical Distributions (%)

| Feature / Category | Training Data | Gaussian Copula | CTGAN | TVAE |
|---|---|---|---|---|
| **Gender: Male / Female** | 51.8% / 48.2% | 50.2% / 49.8% | 52.8% / 47.2% | 68.6% / 31.4% |
| **Programme: BIT** | 37.0% | 37.8% | 34.0% | 91.4% |
| **Programme: BCS** | 23.6% | 19.6% | 22.6% | 8.6% |
| **Programme: BSE** | 20.8% | 22.2% | 22.6% | 0.0% |
| **Programme: BBIT** | 18.6% | 20.4% | 20.8% | 0.0% |
| **Status: Pass / Fail** | 85.4% / 14.6% | 82.8% / 17.2% | 91.2% / 8.8% | 90.4% / 9.6% |
| **Grade: A** | 15.6% | 15.4% | 40.6% | 15.6% |
| **Grade: B** | 22.4% | 19.4% | 25.8% | 32.4% |
| **Grade: C** | 27.4% | 28.4% | 15.8% | 28.2% |
| **Grade: D** | 20.0% | 19.6% | 9.0% | 14.2% |
| **Grade: E** | 14.6% | 17.2% | 8.8% | 9.6% |

---

## 4. Key Observations

1. **Gaussian Copula** produced the closest match to the training data across both numerical means/standard deviations and categorical proportions (gender, programme, grades, and pass/fail rate).
2. **CTGAN** preserved `gender` and `programme` proportions well, but shifted `exam_score` upward (`69.15` vs `54.02`) and `attendance_percentage` downward (`66.26` vs `76.42`), resulting in an inflated Grade `A` share (`40.6%` vs `15.6%`).
3. **TVAE** exhibited category mode collapse on `programme` (`91.4%` `BIT`, `8.6%` `BCS`, `0%` `BSE`/`BBIT`), skewed `gender` (`68.6%` Male), and narrower numerical variance (e.g., `attendance_percentage` std `8.97` vs `11.84`).
4. **All three outputs** pass every schema, range, uniqueness, and deterministic formula check in `validate_student_data`.

---

## 5. How to Re-run Each Model

```powershell
.\.class\Scripts\python -m src.synthetic_data.generate_gaussian_copula
.\.class\Scripts\python -m src.synthetic_data.generate_ctgan
.\.class\Scripts\python -m src.synthetic_data.generate_tvae
```
