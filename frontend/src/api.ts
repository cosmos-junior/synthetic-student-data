import type {
  DashboardSummary,
  DatasetPreview,
  EvaluationResult,
  GenerationJob,
  GenerationJobPayload,
  InstitutionalDataset,
  JobPreview,
  ModelType,
  UserProfile,
} from "./types";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(
  path: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Token ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    let message = `Request failed (${response.status})`;
    try {
      const parsed = JSON.parse(text);
      message =
        parsed.detail ??
        parsed.non_field_errors?.[0] ??
        JSON.stringify(parsed);
    } catch {
      if (text) message = text;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<string> {
  const data = await request<{ token: string }>("/auth/token/", null, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  return data.token;
}

export async function registerUser(
  username: string,
  email: string,
  password: string
): Promise<{ token: string; user: UserProfile }> {
  return request<{ token: string; user: UserProfile }>("/auth/register/", null, {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

export function logoutUser(token: string): Promise<{ detail: string }> {
  return request<{ detail: string }>("/auth/logout/", token, { method: "POST" });
}

export function fetchProfile(token: string): Promise<UserProfile> {
  return request<UserProfile>("/auth/me/", token);
}

export function fetchDashboardSummary(token: string): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary/", token);
}

export function listDatasets(token: string, search = ""): Promise<InstitutionalDataset[]> {
  const q = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<InstitutionalDataset[]>(`/datasets/${q}`, token);
}

export function uploadDataset(
  token: string,
  formData: FormData
): Promise<InstitutionalDataset> {
  return request<InstitutionalDataset>("/datasets/", token, {
    method: "POST",
    body: formData,
  });
}

export function deleteDataset(token: string, datasetId: string): Promise<void> {
  return request<void>(`/datasets/${datasetId}/`, token, { method: "DELETE" });
}

export function previewDataset(
  token: string,
  datasetId: string,
  params: { page?: number; pageSize?: number; search?: string; sortBy?: string; sortDir?: string }
): Promise<DatasetPreview> {
  const sp = new URLSearchParams();
  if (params.page) sp.set("page", String(params.page));
  if (params.pageSize) sp.set("page_size", String(params.pageSize));
  if (params.search) sp.set("search", params.search);
  if (params.sortBy) sp.set("sort_by", params.sortBy);
  if (params.sortDir) sp.set("sort_dir", params.sortDir);
  return request<DatasetPreview>(`/datasets/${datasetId}/preview/?${sp.toString()}`, token);
}

export function confirmDatasetMetadata(
  token: string,
  datasetId: string,
  columnOverrides: Record<string, string>
): Promise<InstitutionalDataset> {
  return request<InstitutionalDataset>(`/datasets/${datasetId}/confirm-metadata/`, token, {
    method: "POST",
    body: JSON.stringify({ column_overrides: columnOverrides }),
  });
}

export function listJobs(token: string): Promise<GenerationJob[]> {
  return request<GenerationJob[]>("/jobs/", token);
}

export function createJob(token: string, payload: GenerationJobPayload): Promise<GenerationJob> {
  return request<GenerationJob>("/jobs/", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createBatchJobs(
  token: string,
  payload: Omit<GenerationJobPayload, "model_type"> & { model_types: ModelType[] }
): Promise<GenerationJob[]> {
  return request<GenerationJob[]>("/jobs/batch/", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rerunJob(token: string, jobId: string): Promise<GenerationJob> {
  return request<GenerationJob>(`/jobs/${jobId}/rerun/`, token, { method: "POST" });
}

export function cancelJob(token: string, jobId: string): Promise<GenerationJob> {
  return request<GenerationJob>(`/jobs/${jobId}/cancel/`, token, { method: "POST" });
}

export function deleteJob(token: string, jobId: string): Promise<void> {
  return request<void>(`/jobs/${jobId}/`, token, { method: "DELETE" });
}

export function previewJob(token: string, jobId: string, limit = 10): Promise<JobPreview> {
  return request<JobPreview>(`/jobs/${jobId}/preview/?limit=${limit}`, token);
}

async function downloadBinary(token: string, path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Token ${token}` },
  });
  if (!response.ok) {
    throw new Error(`Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function downloadJobCsv(token: string, jobId: string, filename: string): Promise<void> {
  return downloadBinary(token, `/jobs/${jobId}/download/`, filename);
}

export function downloadJobPdf(token: string, jobId: string, filename: string): Promise<void> {
  return downloadBinary(token, `/jobs/${jobId}/report-pdf/`, filename);
}

export function listEvaluations(token: string): Promise<EvaluationResult[]> {
  return request<EvaluationResult[]>("/evaluations/", token);
}

export function runEvaluations(token: string): Promise<EvaluationResult[]> {
  return request<EvaluationResult[]>("/evaluations/run/", token, { method: "POST" });
}
