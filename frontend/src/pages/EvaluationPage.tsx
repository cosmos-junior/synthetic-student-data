import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { listEvaluations, runEvaluations } from "../api";

export function EvaluationPage({ token }: { token: string }) {
  const queryClient = useQueryClient();
  const { data: results = [], isLoading } = useQuery({
    queryKey: ["evaluations"],
    queryFn: () => listEvaluations(token),
  });

  const runMutation = useMutation({
    mutationFn: () => runEvaluations(token),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["evaluations"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const synthResults = results.filter((r) => r.model_name !== "Real Baseline (TRTR)");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Statistical Fidelity Evaluation</h1>
          <p className="text-sm text-slate-500">
            SDMetrics QualityReport &amp; DiagnosticReport comparing synthetic models against real training data.
          </p>
        </div>
        <button
          type="button"
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold disabled:opacity-60 cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${runMutation.isPending ? "animate-spin" : ""}`} />
          {runMutation.isPending ? "Running Benchmarks..." : "Run / Refresh Evaluation"}
        </button>
      </div>

      {synthResults.length > 0 && (
        <section className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-base font-semibold text-slate-900 mb-4">Fidelity Comparison (Higher = Better)</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={synthResults}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="model_name" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="quality_overall" name="Overall Quality" fill="#0d9488" radius={[6, 6, 0, 0]} />
                <Bar dataKey="column_shapes" name="Column Shapes" fill="#0f172a" radius={[6, 6, 0, 0]} />
                <Bar dataKey="column_pair_trends" name="Column Pair Trends" fill="#64748b" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <section className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Overall Quality</th>
                <th className="px-4 py-3">Column Shapes</th>
                <th className="px-4 py-3">Pair Trends</th>
                <th className="px-4 py-3">Data Validity</th>
                <th className="px-4 py-3">Data Structure</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-slate-500">
                    Loading evaluation metrics...
                  </td>
                </tr>
              ) : results.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-slate-500">
                    No evaluation results yet. Click "Run / Refresh Evaluation" above.
                  </td>
                </tr>
              ) : (
                results.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-3 font-semibold text-slate-900">{r.model_name}</td>
                    <td className="px-4 py-3">{r.quality_overall.toFixed(4)}</td>
                    <td className="px-4 py-3">{r.column_shapes.toFixed(4)}</td>
                    <td className="px-4 py-3">{r.column_pair_trends.toFixed(4)}</td>
                    <td className="px-4 py-3">{r.data_validity.toFixed(4)}</td>
                    <td className="px-4 py-3">{r.data_structure.toFixed(4)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
