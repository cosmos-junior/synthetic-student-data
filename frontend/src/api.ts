import type {
  EvaluationResult,
  GenerationJob,
  GenerationJobPayload,
  JobPreview,
} from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(
  path: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
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

  return response.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<string> {
  const data = await request<{ token: string }>("/auth/token/", null, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  return data.token;
}

export function listJobs(token: string): Promise<GenerationJob[]> {
  return request<GenerationJob[]>("/jobs/", token);
}

export function createJob(
  token: string,
  payload: GenerationJobPayload
): Promise<GenerationJob> {
  return request<GenerationJob>("/jobs/", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function previewJob(
  token: string,
  jobId: string,
  limit = 10
): Promise<JobPreview> {
  return request<JobPreview>(`/jobs/${jobId}/preview/?limit=${limit}`, token);
}

export async function downloadJobCsv(
  token: string,
  jobId: string,
  filename: string
): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/download/`, {
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

export function listEvaluations(token: string): Promise<EvaluationResult[]> {
  return request<EvaluationResult[]>("/evaluations/", token);
}

export function runEvaluations(token: string): Promise<EvaluationResult[]> {
  return request<EvaluationResult[]>("/evaluations/run/", token, {
    method: "POST",
  });
}
