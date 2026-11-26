"""Dataset validation, CSV formula-injection protection, profiling, and SDV metadata helpers."""

import hashlib
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sdv.metadata import Metadata


MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {".csv"}
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "",
}
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

IDENTIFIER_NAME_PATTERNS = re.compile(
    r"(^|_)(id|reg|registration|student_id|student_reg|email|phone|mobile|national_id|ssn|passport|name|full_name)($|_)",
    re.IGNORECASE,
)
SENSITIVE_NAME_PATTERNS = re.compile(
    r"(grade|status|score|gpa|salary|income|diagnosis|medical|disease|disability|ethnicity|religion)",
    re.IGNORECASE,
)


def sanitize_csv_cell(value: Any) -> Any:
    """Prevent CSV formula injection by prefixing dangerous leading characters."""
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def sanitize_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with string cells neutralized against CSV formula injection."""
    safe_df = df.copy()
    for col in safe_df.select_dtypes(include=["object", "string"]).columns:
        safe_df[col] = safe_df[col].map(sanitize_csv_cell)
    return safe_df


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 fingerprint of a dataset file."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_uploaded_csv(
    file_path: Path,
    original_filename: str,
    content_type: str = "",
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> tuple[pd.DataFrame, list[str]]:
    """Validate an uploaded CSV file for safety, encoding, structure, and data quality.

    Returns (dataframe, warnings_list). Raises ValueError on hard validation failures.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '{ext}'. Only .csv files are currently supported.")

    normalized_mime = (content_type or "").split(";")[0].strip().lower()
    if normalized_mime and normalized_mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported MIME type '{normalized_mime}'. Expected text/csv.")

    size_bytes = file_path.stat().st_size
    if size_bytes == 0:
        raise ValueError("Uploaded file is empty.")
    if size_bytes > max_bytes:
        raise ValueError(f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB.")

    raw_bytes = file_path.read_bytes()
    if b"\x00" in raw_bytes[:4096]:
        raise ValueError("Binary content detected in CSV upload.")

    df = None
    last_err = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except Exception as exc:
            last_err = exc

    if df is None:
        raise ValueError(f"Unable to parse CSV file: {last_err}")

    if df.empty or len(df.columns) == 0:
        raise ValueError("CSV file contains no data rows or columns.")

    # Check duplicate column names (pandas renames duplicates as col.1, so inspect header line too)
    first_line = raw_bytes.splitlines()[0].decode("utf-8", errors="replace")
    raw_headers = [h.strip().strip('"').strip("'") for h in first_line.split(",")]
    if len(raw_headers) != len(set(raw_headers)):
        raise ValueError("CSV file contains duplicate column names.")

    empty_cols = [col for col in df.columns if df[col].isna().all()]
    if empty_cols:
        raise ValueError(f"CSV contains completely empty columns: {empty_cols}")

    warnings_list: list[str] = []
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        warnings_list.append(f"Dataset contains {dup_count} duplicate rows.")

    missing_total = int(df.isna().sum().sum())
    if missing_total > 0:
        warnings_list.append(f"Dataset contains {missing_total} missing values.")

    for col in df.select_dtypes(include=["object", "string"]).columns:
        unique_ratio = df[col].nunique(dropna=True) / max(len(df), 1)
        if unique_ratio > 0.9 and len(df) >= 20 and not IDENTIFIER_NAME_PATTERNS.search(str(col)):
            warnings_list.append(
                f"Column '{col}' has very high cardinality ({df[col].nunique()} unique values)."
            )

    return df, warnings_list


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Generate a comprehensive statistical and structural profile of a DataFrame."""
    row_count = int(len(df))
    col_count = int(len(df.columns))
    duplicate_rows = int(df.duplicated().sum())
    missing_total = int(df.isna().sum().sum())
    total_cells = max(row_count * col_count, 1)

    numerical_cols: list[str] = []
    categorical_cols: list[str] = []
    boolean_cols: list[str] = []
    datetime_cols: list[str] = []
    identifier_candidates: list[str] = []
    sensitive_candidates: list[str] = []

    column_profiles: list[dict[str, Any]] = []

    for col in df.columns:
        series = df[col]
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))

        is_bool = pd.api.types.is_bool_dtype(series)
        is_datetime = pd.api.types.is_datetime64_any_dtype(series)
        is_numeric = pd.api.types.is_numeric_dtype(series) and not is_bool

        if is_bool:
            detected_type = "boolean"
            boolean_cols.append(col)
        elif is_datetime:
            detected_type = "datetime"
            datetime_cols.append(col)
        elif is_numeric:
            if col == "year_of_study" or (unique_count <= 10 and (series.dropna() % 1 == 0).all() and unique_count >= 2 and "year" in col.lower()):
                detected_type = "ordinal"
            else:
                detected_type = "numerical"
            numerical_cols.append(col)
        else:
            detected_type = "categorical"
            categorical_cols.append(col)

        is_identifier = bool(
            IDENTIFIER_NAME_PATTERNS.search(str(col))
            or (detected_type == "categorical" and row_count >= 10 and unique_count == row_count)
        )
        if is_identifier:
            identifier_candidates.append(col)

        is_sensitive = bool(SENSITIVE_NAME_PATTERNS.search(str(col)))
        if is_sensitive:
            sensitive_candidates.append(col)

        col_info: dict[str, Any] = {
            "name": col,
            "detected_sdtype": "id" if is_identifier else detected_type,
            "pandas_dtype": str(series.dtype),
            "missing_count": missing_count,
            "missing_pct": round((missing_count / max(row_count, 1)) * 100, 2),
            "unique_count": unique_count,
            "is_identifier": is_identifier,
            "is_sensitive": is_sensitive,
        }

        if is_numeric:
            clean = series.dropna()
            col_info["stats"] = {
                "min": round(float(clean.min()), 4) if len(clean) else None,
                "max": round(float(clean.max()), 4) if len(clean) else None,
                "mean": round(float(clean.mean()), 4) if len(clean) else None,
                "median": round(float(clean.median()), 4) if len(clean) else None,
                "std": round(float(clean.std()), 4) if len(clean) > 1 else 0.0,
            }
        else:
            top_counts = series.astype(str).value_counts().head(10).to_dict()
            col_info["top_categories"] = {str(k): int(v) for k, v in top_counts.items()}

        column_profiles.append(col_info)

    corr_matrix: dict[str, dict[str, float]] = {}
    if len(numerical_cols) >= 2:
        corr_df = df[numerical_cols].corr().round(3).fillna(0.0)
        corr_matrix = {
            str(r): {str(c): float(corr_df.loc[r, c]) for c in corr_df.columns}
            for r in corr_df.index
        }

    return {
        "row_count": row_count,
        "column_count": col_count,
        "duplicate_rows": duplicate_rows,
        "missing_count": missing_total,
        "missing_pct": round((missing_total / total_cells) * 100, 2),
        "numerical_columns": numerical_cols,
        "categorical_columns": categorical_cols,
        "boolean_columns": boolean_cols,
        "datetime_columns": datetime_cols,
        "identifier_candidates": identifier_candidates,
        "sensitive_candidates": sensitive_candidates,
        "columns": column_profiles,
        "correlation_matrix": corr_matrix,
    }


def build_sdv_metadata(
    df: pd.DataFrame,
    table_name: str = "records",
    column_overrides: dict[str, str] | None = None,
) -> Metadata:
    """Build and validate an SDV Metadata object compatible with SDV 2.x."""
    metadata = Metadata.detect_from_dataframes(
        {table_name: df},
        infer_sdtypes=True,
        infer_keys=None,
        verbose=False,
    )
    if column_overrides:
        valid_sdtypes = {"numerical", "categorical", "ordinal", "datetime", "boolean", "id"}
        for col, sdtype in column_overrides.items():
            if col in df.columns and sdtype in valid_sdtypes:
                metadata.update_column(col, table_name=table_name, sdtype=sdtype)
    metadata.validate()
    return metadata
