import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { listEvaluations } from "../api";

export function MlUtilityPage({ token }: { token: string }) {
  const { data: results = [], isLoading } = useQuery({
    queryKey: ["evaluations"],
    queryFn: () => listEvaluations(token),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Downstream ML Utility (TRTR vs. TSTR)</h1>
        <p className="text-sm text-slate-500">
          Leak-free evaluation: synthesizers are trained strictly on the real training split and evaluated on the
          untouched real test partition across repeated seeds.
        </p>
      </div>

      {results.length > 0 && (
        <section className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-base font-semibold text-slate-900 mb-4">TRTR Baseline vs. TSTR Synthetic Models</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={results}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="model_name" tick={{ fontSize: 12 }} />
                <YAxis domain={[-0.4, 1]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="status_accuracy" name="Accuracy" fill="#0d9488" radius={[6, 6, 0, 0]} />
                <Bar dataKey="status_macro_f1" name="Macro-F1" fill="#0f172a" radius={[6, 6, 0, 0]} />
                <Bar dataKey="final_score_r2" name="Score R²" fill="#0284c7" radius={[6, 6, 0, 0]} />
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
                <th className="px-4 py-3">Status Accuracy</th>
                <th className="px-4 py-3">Status Macro-F1</th>
                <th className="px-4 py-3">Final Score R²</th>
                <th className="px-4 py-3">Final Score RMSE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-slate-500">
                    Loading ML utility results...
                  </td>
                </tr>
              ) : (
                results.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-3 font-semibold text-slate-900">{r.model_name}</td>
                    <td className="px-4 py-3">{r.status_accuracy.toFixed(4)}</td>
                    <td className="px-4 py-3">{r.status_macro_f1.toFixed(4)}</td>
                    <td className="px-4 py-3">{r.final_score_r2.toFixed(4)}</td>
                    <td className="px-4 py-3">{r.final_score_rmse.toFixed(4)}</td>
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
