import { useEffect, useState } from "react";
import { listEvaluations, runEvaluations } from "../api";
import type { EvaluationResult } from "../types";

interface EvaluationPanelProps {
  token: string;
}

function MetricBars({
  title,
  items,
}: {
  title: string;
  items: { label: string; value: number | null }[];
}) {
  return (
    <div className="card">
      <h2>{title}</h2>
      {items.map((item) => {
        const val = item.value ?? 0;
        const pct = Math.max(0, Math.min(100, val * 100));
        return (
          <div key={item.label} className="bar-row">
            <span>{item.label}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${pct}%` }} />
            </div>
            <span>{item.value !== null ? item.value.toFixed(3) : "—"}</span>
          </div>
        );
      })}
    </div>
  );
}

export function EvaluationPanel({ token }: EvaluationPanelProps) {
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadResults() {
    setLoading(true);
    setError(null);
    try {
      const data = await listEvaluations(token);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evaluation results.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadResults();
  }, [token]);

  async function handleRunEvaluation() {
    setRunning(true);
    setError(null);
    try {
      const data = await runEvaluations(token);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run comparative evaluation.");
    } finally {
      setRunning(false);
    }
  }

  const syntheticOnly = results.filter((r) => r.model_name !== "Real Baseline (TRTR)");

  return (
    <>
      <section className="card">
        <div className="header-row">
          <div>
            <h2>Comparative Evaluation Report</h2>
            <p className="topbar-sub">
              Statistical fidelity (SDMetrics), privacy protection, and downstream ML utility (TRTR vs. TSTR).
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            disabled={running}
            onClick={() => void handleRunEvaluation()}
          >
            {running ? "Running Evaluation..." : "Run / Refresh Evaluation"}
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <p style={{ color: "var(--muted)" }}>Loading evaluation metrics...</p>
        ) : results.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>
            No stored evaluation results yet. Click "Run / Refresh Evaluation" to compute metrics across all models.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Quality</th>
                  <th>Col Shapes</th>
                  <th>Pair Trends</th>
                  <th>New Row Synth</th>
                  <th>DCR Prot.</th>
                  <th>Disclosure Prot.</th>
                  <th>Status Acc.</th>
                  <th>Macro-F1</th>
                  <th>Score R²</th>
                  <th>Score RMSE</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.model_name}</strong>
                    </td>
                    <td>{r.quality_overall.toFixed(4)}</td>
                    <td>{r.column_shapes.toFixed(4)}</td>
                    <td>{r.column_pair_trends.toFixed(4)}</td>
                    <td>{r.new_row_synthesis !== null ? r.new_row_synthesis.toFixed(4) : "—"}</td>
                    <td>{r.dcr_baseline_protection !== null ? r.dcr_baseline_protection.toFixed(4) : "—"}</td>
                    <td>{r.disclosure_protection !== null ? r.disclosure_protection.toFixed(4) : "—"}</td>
                    <td>{r.status_accuracy.toFixed(4)}</td>
                    <td>{r.status_macro_f1.toFixed(4)}</td>
                    <td>{r.final_score_r2.toFixed(4)}</td>
                    <td>{r.final_score_rmse.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {results.length > 0 && (
        <section className="metrics-grid">
          <MetricBars
            title="Overall Statistical Quality"
            items={syntheticOnly.map((r) => ({ label: r.model_name, value: r.quality_overall }))}
          />
          <MetricBars
            title="DCR Privacy Protection"
            items={syntheticOnly.map((r) => ({
              label: r.model_name,
              value: r.dcr_baseline_protection,
            }))}
          />
          <MetricBars
            title="Downstream Macro-F1 (TRTR vs TSTR)"
            items={results.map((r) => ({ label: r.model_name, value: r.status_macro_f1 }))}
          />
        </section>
      )}
    </>
  );
}
