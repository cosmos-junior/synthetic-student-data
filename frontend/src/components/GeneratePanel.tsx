import { useEffect, useState, type FormEvent } from "react";
import { createJob, downloadJobCsv, listJobs, previewJob } from "../api";
import type { GenerationJob, JobPreview, ModelType } from "../types";

interface GeneratePanelProps {
  token: string;
}

export function GeneratePanel({ token }: GeneratePanelProps) {
  const [modelType, setModelType] = useState<ModelType>("gaussian_copula");
  const [numRows, setNumRows] = useState(500);
  const [epochs, setEpochs] = useState(300);
  const [batchSize, setBatchSize] = useState(500);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [preview, setPreview] = useState<JobPreview | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  async function loadJobs() {
    try {
      const data = await listJobs(token);
      setJobs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs.");
    }
  }

  useEffect(() => {
    void loadJobs();
  }, [token]);

  async function handleGenerate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setStatusMessage(null);

    if (modelType === "ctgan" && batchSize % 10 !== 0) {
      setError("CTGAN requires batch_size to be divisible by 10.");
      return;
    }

    setSubmitting(true);
    try {
      const created = await createJob(token, {
        model_type: modelType,
        num_rows: numRows,
        epochs,
        batch_size: batchSize,
      });
      setStatusMessage(
        `Generated ${created.summary_stats.num_records ?? created.num_rows} records with ${created.model_type_display}. Validation ${
          created.validation_passed ? "passed" : "reported issues"
        }.`
      );
      await loadJobs();
      const previewData = await previewJob(token, created.id, 10);
      setPreview(previewData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePreview(jobId: string) {
    setError(null);
    try {
      const data = await previewJob(token, jobId, 10);
      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preview.");
    }
  }

  async function handleDownload(job: GenerationJob) {
    setError(null);
    try {
      await downloadJobCsv(token, job.id, `${job.model_type}_${job.num_rows}.csv`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download CSV.");
    }
  }

  return (
    <>
      <section className="card">
        <h2>Generate Synthetic Student Dataset</h2>
        <form onSubmit={handleGenerate} className="form-grid">
          <div className="field">
            <label htmlFor="modelType">Synthesizer Model</label>
            <select
              id="modelType"
              value={modelType}
              onChange={(e) => setModelType(e.target.value as ModelType)}
            >
              <option value="gaussian_copula">Gaussian Copula</option>
              <option value="ctgan">CTGAN</option>
              <option value="tvae">TVAE</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="numRows">Rows (10–10,000)</label>
            <input
              id="numRows"
              type="number"
              min={10}
              max={10000}
              value={numRows}
              onChange={(e) => setNumRows(Number(e.target.value))}
            />
          </div>
          {modelType !== "gaussian_copula" && (
            <>
              <div className="field">
                <label htmlFor="epochs">Epochs</label>
                <input
                  id="epochs"
                  type="number"
                  min={1}
                  max={2000}
                  value={epochs}
                  onChange={(e) => setEpochs(Number(e.target.value))}
                />
              </div>
              <div className="field">
                <label htmlFor="batchSize">Batch Size</label>
                <input
                  id="batchSize"
                  type="number"
                  min={10}
                  step={10}
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number(e.target.value))}
                />
              </div>
            </>
          )}
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Generating..." : "Run Generation"}
          </button>
        </form>
        {statusMessage && <div className="alert alert-success">{statusMessage}</div>}
        {error && <div className="alert alert-error">{error}</div>}
      </section>

      <section className="card">
        <div className="header-row">
          <h2>Generation Jobs</h2>
          <button type="button" className="btn btn-secondary" onClick={() => void loadJobs()}>
            Refresh
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>Rows</th>
                <th>Status</th>
                <th>Validation</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ color: "var(--muted)" }}>
                    No generation jobs yet. Run a model above to create one.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{job.model_type_display}</td>
                    <td>{job.num_rows}</td>
                    <td>
                      <span
                        className={`badge ${
                          job.status === "completed"
                            ? "badge-success"
                            : job.status === "failed"
                            ? "badge-danger"
                            : "badge-warn"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${job.validation_passed ? "badge-success" : "badge-danger"}`}>
                        {job.validation_passed ? "Passed" : "Issues"}
                      </span>
                    </td>
                    <td>{new Date(job.created_at).toLocaleString()}</td>
                    <td>
                      <div className="actions-inline">
                        <button
                          type="button"
                          className="btn btn-secondary"
                          disabled={job.status !== "completed"}
                          onClick={() => void handlePreview(job.id)}
                        >
                          Preview
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary"
                          disabled={job.status !== "completed"}
                          onClick={() => void handleDownload(job)}
                        >
                          Download CSV
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {preview && (
        <section className="card">
          <h2>
            Dataset Preview (First {preview.rows.length} of {preview.total_rows} rows)
          </h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {preview.columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, idx) => (
                  <tr key={idx}>
                    {preview.columns.map((col) => (
                      <td key={col}>{String(row[col] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
