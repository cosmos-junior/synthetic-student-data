export type ModelType = "gaussian_copula" | "ctgan" | "tvae";

export interface GenerationJobPayload {
  model_type: ModelType;
  num_rows: number;
  epochs?: number;
  batch_size?: number;
}

export interface GenerationJob {
  id: string;
  model_type: ModelType;
  model_type_display: string;
  num_rows: number;
  epochs: number;
  batch_size: number;
  status: "pending" | "running" | "completed" | "failed";
  output_file: string;
  validation_passed: boolean;
  validation_errors: string[];
  summary_stats: {
    num_records?: number;
    academic_status_counts?: Record<string, number>;
    programme_counts?: Record<string, number>;
  };
  error_message: string;
  created_by_username: string | null;
  created_at: string;
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
  status_accuracy: number;
  status_macro_f1: number;
  final_score_r2: number;
  final_score_rmse: number;
  evaluated_at: string;
}
