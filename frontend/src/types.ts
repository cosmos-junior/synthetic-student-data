export type ModelType = "gaussian_copula" | "ctgan" | "tvae";

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  date_joined: string;
}

export interface ColumnProfile {
  name: string;
  detected_sdtype: string;
  pandas_dtype: string;
  missing_count: number;
  missing_pct: number;
  unique_count: number;
  is_identifier: boolean;
  is_sensitive: boolean;
  stats?: {
    min: number | null;
    max: number | null;
    mean: number | null;
    median: number | null;
    std: number | null;
  };
  top_categories?: Record<string, number>;
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  duplicate_rows: number;
  missing_count: number;
  missing_pct: number;
  numerical_columns: string[];
  categorical_columns: string[];
  boolean_columns: string[];
  datetime_columns: string[];
  identifier_candidates: string[];
  sensitive_candidates: string[];
  columns: ColumnProfile[];
  correlation_matrix: Record<string, Record<string, number>>;
}

export interface InstitutionalDataset {
  id: string;
  name: string;
  description: string;
  category: "student_academic" | "institutional_generic" | "research_benchmark";
  category_display: string;
  original_filename: string;
  file_size_bytes: number;
  file_sha256: string;
  row_count: number;
  column_count: number;
  authorization_confirmed: boolean;
  profile_json: DatasetProfile;
  metadata_json: Record<string, unknown>;
  column_overrides: Record<string, string>;
  metadata_confirmed: boolean;
  validation_warnings: string[];
  owner_username: string;
  created_at: string;
  updated_at: string;
}

export interface DatasetPreview {
  dataset_id: string;
  total_rows: number;
  page: number;
  page_size: number;
  columns: string[];
  rows: Record<string, string | number | null>[];
}

export interface GenerationJobPayload {
  dataset?: string | null;
  model_type: ModelType;
  num_rows: number;
  epochs?: number;
  batch_size?: number;
  random_seed?: number;
  model_config?: Record<string, unknown>;
}

export interface GenerationJob {
  id: string;
  dataset: string | null;
  dataset_name: string;
  dataset_fingerprint: string;
  model_type: ModelType;
  model_type_display: string;
  num_rows: number;
  epochs: number;
  batch_size: number;
  random_seed: number;
  training_row_count: number;
  sdv_version: string;
  model_config: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  output_file: string;
  validation_passed: boolean;
  validation_errors: string[];
  summary_stats: {
    num_records?: number;
    academic_status_counts?: Record<string, number>;
    programme_counts?: Record<string, number>;
  };
  evaluation_json: {
    fidelity?: Record<string, number>;
    privacy?: Record<string, number | string | null>;
    ml_utility?: Record<string, Record<string, number>>;
  };
  error_message: string;
  duration_seconds: number | null;
  created_by_username: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface JobPreview {
  job_id: string;
  total_rows: number;
  columns: string[];
  rows: Record<string, string | number>[];
}

export interface EvaluationResult {
  id: number;
  model_name: string;
  quality_overall: number;
  column_shapes: number;
  column_pair_trends: number;
  data_validity: number;
  data_structure: number;
  new_row_synthesis: number | null;
  dcr_baseline_protection: number | null;
  disclosure_protection: number | null;
  dcr_mean: number | null;
  dcr_min: number | null;
  dcr_p05: number | null;
  exact_duplicate_rate: number | null;
  near_duplicate_rate: number | null;
  membership_inference_risk: number | null;
  privacy_risk_label: string;
  status_accuracy: number;
  status_macro_f1: number;
  final_score_r2: number;
  final_score_rmse: number;
  evaluated_at: string;
}

export interface AuditLogEntry {
  id: number;
  username: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface DashboardSummary {
  total_datasets: number;
  total_experiments: number;
  completed_jobs: number;
  failed_jobs: number;
  latest_evaluations: EvaluationResult[];
  recent_experiments: GenerationJob[];
  recent_activity: AuditLogEntry[];
}
