import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Play, Sparkles } from "lucide-react";
import {
  createBatchJobs,
  createJob,
  downloadJobCsv,
  listDatasets,
  previewJob,
} from "../api";
import type { GenerationJob, JobPreview, ModelType } from "../types";

export function GeneratePage({ token }: { token: string }) {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [modelSelection, setModelSelection] = useState<ModelType | "all">("gaussian_copula");
  const [numRows, setNumRows] = useState(500);
  const [randomSeed, setRandomSeed] = useState(42);
  const [epochs, setEpochs] = useState(300);
  const [batchSize, setBatchSize] = useState(500);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completedJobs, setCompletedJobs] = useState<GenerationJob[]>([]);
  const [preview, setPreview] = useState<JobPreview | null>(null);

  const queryClient = useQueryClient();
  const { data: datasets = [] } = useQuery({
    queryKey: ["datasets", ""],
    queryFn: () => listDatasets(token),
  });

  const activeDataset = datasets.find((d) => d.id === selectedDatasetId) ?? null;
  const needsNeuralParams = modelSelection === "ctgan" || modelSelection === "tvae" || modelSelection === "all";

  async function handleStart() {
    setError(null);
    if ((modelSelection === "ctgan" || modelSelection === "all") && batchSize % 10 !== 0) {
      setError("CTGAN requires batch_size to be divisible by 10.");
      return;
    }

    setSubmitting(true);
    try {
      const common = {
        dataset: selectedDatasetId || null,
        num_rows: numRows,
        epochs,
        batch_size: batchSize,
        random_seed: randomSeed,
      };
      const jobs =
        modelSelection === "all"
          ? await createBatchJobs(token, {
              ...common,
              model_types: ["gaussian_copula", "ctgan", "tvae"],
            })
          : [await createJob(token, { ...common, model_type: modelSelection })];

      setCompletedJobs(jobs);
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });

      const firstCompleted = jobs.find((j) => j.status === "completed");
      if (firstCompleted) {
        setPreview(await previewJob(token, firstCompleted.id, 10));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Generate Synthetic Data</h1>
        <p className="text-sm text-slate-500">
          Guided workflow: select a source dataset, configure your synthesizer(s), run generation, and inspect results.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 space-y-5">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 mb-2">Step 1: Source Dataset</h2>
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm"
            >
              <option value="">Built-in Student Academic Training Data (500 rows)</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.row_count} rows · {d.metadata_confirmed ? "Metadata Confirmed" : "Auto-Detected"})
                </option>
              ))}
            </select>
            {activeDataset && !activeDataset.metadata_confirmed && (
              <p className="text-xs text-amber-600 mt-1">
                Tip: You can review and confirm column types in Dataset Explorer before running.
              </p>
            )}
          </div>

          <div>
            <h2 className="text-sm font-semibold text-slate-900 mb-2">Step 2: Select Generation Model(s)</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { id: "gaussian_copula", label: "Gaussian Copula" },
                { id: "ctgan", label: "CTGAN" },
                { id: "tvae", label: "TVAE" },
                { id: "all", label: "All 3 Models" },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setModelSelection(opt.id as ModelType | "all")}
                  className={`px-3 py-2.5 rounded-lg border text-xs font-semibold transition cursor-pointer ${
                    modelSelection === opt.id
                      ? "bg-teal-600 border-teal-600 text-white"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-slate-900 mb-2">Step 3: Configure Parameters</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Synthetic Records (10–10,000)
                </label>
                <input
                  type="number"
                  min={10}
                  max={10000}
                  value={numRows}
                  onChange={(e) => setNumRows(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Random Seed</label>
                <input
                  type="number"
                  value={randomSeed}
                  onChange={(e) => setRandomSeed(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
                />
              </div>
              {needsNeuralParams && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Training Epochs (CTGAN / TVAE)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={2000}
                      value={epochs}
                      onChange={(e) => setEpochs(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Batch Size (divisible by 10 for CTGAN)
                    </label>
                    <input
                      type="number"
                      min={10}
                      step={10}
                      value={batchSize}
                      onChange={(e) => setBatchSize(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
                    />
                  </div>
                </>
              )}
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">{error}</div>
          )}

          <button
            type="button"
            disabled={submitting}
            onClick={() => void handleStart()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold disabled:opacity-60 cursor-pointer"
          >
            <Play className="w-4 h-4" />
            {submitting ? "Training & Generating..." : "Start Experiment"}
          </button>
        </div>

        <aside className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <div className="flex items-center gap-2 text-slate-900 font-semibold text-sm">
            <Sparkles className="w-4 h-4 text-teal-600" />
            <span>Experiment Summary</span>
          </div>
          <dl className="text-xs space-y-2 text-slate-600">
            <div className="flex justify-between">
              <dt>Source:</dt>
              <dd className="font-medium text-slate-900">{activeDataset ? activeDataset.name : "Built-in Student Data"}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Model(s):</dt>
              <dd className="font-medium text-slate-900">{modelSelection}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Rows:</dt>
              <dd className="font-medium text-slate-900">{numRows}</dd>
            </div>
            <div className="flex justify-between">
              <dt>Seed:</dt>
              <dd className="font-medium text-slate-900">{randomSeed}</dd>
            </div>
          </dl>
          <p className="text-[11px] text-slate-500 border-t border-slate-100 pt-3">
            Direct identifiers are excluded during training and regenerated synthetically after sampling.
            For student academic datasets, deterministic formula post-processing is applied before final evaluation.
          </p>
        </aside>
      </div>

      {completedJobs.length > 0 && (
        <section className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <h2 className="text-base font-semibold text-slate-900">Generated Results</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {completedJobs.map((job) => (
              <div key={job.id} className="border border-slate-200 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm">{job.model_type_display}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-50 text-emerald-700 font-medium">
                    {job.status}
                  </span>
                </div>
                <div className="text-xs text-slate-600">
                  Quality: <strong>{job.evaluation_json?.fidelity?.quality_overall ?? "—"}</strong> · Duration:{" "}
                  {job.duration_seconds ?? 0}s
                </div>
                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => void downloadJobCsv(token, job.id, `${job.model_type}_${job.num_rows}.csv`)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-teal-600 text-white text-xs font-medium cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" /> CSV
                  </button>
                  <button
                    type="button"
                    onClick={async () => setPreview(await previewJob(token, job.id, 10))}
                    className="px-2.5 py-1 rounded border border-slate-200 text-xs font-medium text-slate-700 cursor-pointer"
                  >
                    Preview
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {preview && (
        <section className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="text-base font-semibold text-slate-900">
            Sample Preview ({preview.rows.length} of {preview.total_rows} rows)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                <tr>
                  {preview.columns.map((c) => (
                    <th key={c} className="px-3 py-2 whitespace-nowrap">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {preview.rows.map((row, idx) => (
                  <tr key={idx}>
                    {preview.columns.map((c) => (
                      <td key={c} className="px-3 py-2 whitespace-nowrap">
                        {String(row[c] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
