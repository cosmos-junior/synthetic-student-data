import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { listEvaluations } from "../api";

export function PrivacyPage({ token }: { token: string }) {
  const { data: results = [], isLoading } = useQuery({
    queryKey: ["evaluations"],
    queryFn: () => listEvaluations(token),
  });

  const synthResults = results.filter((r) => r.model_name !== "Real Baseline (TRTR)");

  function riskBadge(label: string) {
    if (label.includes("Low")) return "bg-emerald-50 text-emerald-700";
    if (label.includes("Moderate")) return "bg-amber-50 text-amber-700";
    return "bg-rose-50 text-rose-700";
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Privacy Risk Analysis</h1>
        <p className="text-sm text-slate-500">
          Empirical disclosure, nearest-neighbour distance (DCR), and duplicate indicators across synthetic models.
        </p>
      </div>

      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3 text-xs text-amber-900">
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <strong>Methodological Limitation:</strong> These metrics are empirical privacy-risk indicators (higher{" "}
          <code>NewRowSynthesis</code>, <code>DCRBaselineProtection</code>, and <code>DisclosureProtection</code> indicate
          lower observed risk; lower <code>Membership Inference Risk</code> and duplicate rates are better). They do{" "}
          <strong>not</strong> constitute formal Differential Privacy guarantees.
        </div>
      </div>

      {synthResults.length > 0 && (
        <section className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-base font-semibold text-slate-900 mb-4">Privacy Protection Indicators</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={synthResults}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="model_name" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="new_row_synthesis" name="New Row Synthesis" fill="#0d9488" radius={[6, 6, 0, 0]} />
                <Bar dataKey="dcr_baseline_protection" name="DCR Protection" fill="#0f172a" radius={[6, 6, 0, 0]} />
                <Bar dataKey="disclosure_protection" name="Disclosure Protection" fill="#0284c7" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <section className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase">
              <tr>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Risk Band</th>
                <th className="px-4 py-3">New Row Synth</th>
                <th className="px-4 py-3">DCR Prot.</th>
                <th className="px-4 py-3">Disclosure Prot.</th>
                <th className="px-4 py-3">DCR Mean / Min</th>
                <th className="px-4 py-3">Near-Dup Rate</th>
                <th className="px-4 py-3">MIA Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-slate-500">
                    Loading privacy metrics...
                  </td>
                </tr>
              ) : (
                synthResults.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-3 font-semibold text-slate-900">{r.model_name}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full font-medium ${riskBadge(r.privacy_risk_label)}`}>
                        {r.privacy_risk_label || "Moderate observed risk"}
                      </span>
                    </td>
                    <td className="px-4 py-3">{r.new_row_synthesis?.toFixed(4) ?? "—"}</td>
                    <td className="px-4 py-3">{r.dcr_baseline_protection?.toFixed(4) ?? "—"}</td>
                    <td className="px-4 py-3">{r.disclosure_protection?.toFixed(4) ?? "—"}</td>
                    <td className="px-4 py-3">
                      {r.dcr_mean?.toFixed(3) ?? "—"} / {r.dcr_min?.toFixed(3) ?? "—"}
                    </td>
                    <td className="px-4 py-3">{r.near_duplicate_rate?.toFixed(4) ?? "—"}</td>
                    <td className="px-4 py-3">{r.membership_inference_risk?.toFixed(4) ?? "—"}</td>
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
