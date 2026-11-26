import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw, Trash2, XCircle } from "lucide-react";
import { cancelJob, deleteJob, listJobs, rerunJob } from "../api";

export function ExperimentsPage({ token }: { token: string }) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs(token),
  });

  const rerunMutation = useMutation({
    mutationFn: (id: string) => rerunJob(token, id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => cancelJob(token, id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteJob(token, id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const compared = jobs.filter((j) => selectedIds.includes(j.id));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Experiment Tracking</h1>
        <p className="text-sm text-slate-500">
          Inspect past generation runs, compare configurations and metrics side-by-side, or re-run experiments.
        </p>
      </div>

      <section className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase">
              <tr>
                <th className="px-3 py-3">Compare</th>
                <th className="px-3 py-3">Model</th>
                <th className="px-3 py-3">Dataset</th>
                <th className="px-3 py-3">Rows / Seed</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Duration</th>
                <th className="px-3 py-3">Quality</th>
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-slate-500">
                    Loading experiments...
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-slate-500">
                    No experiments recorded yet.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50">
                    <td className="px-3 py-2.5">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(job.id)}
                        onChange={(e) =>
                          setSelectedIds((prev) =>
                            e.target.checked ? [...prev, job.id] : prev.filter((x) => x !== job.id)
                          )
                        }
                      />
                    </td>
                    <td className="px-3 py-2.5 font-semibold text-slate-900">{job.model_type_display}</td>
                    <td className="px-3 py-2.5 text-slate-600">{job.dataset_name}</td>
                    <td className="px-3 py-2.5">
                      {job.num_rows} / seed {job.random_seed}
                    </td>
                    <td className="px-3 py-2.5">{job.status}</td>
                    <td className="px-3 py-2.5">{job.duration_seconds ? `${job.duration_seconds}s` : "—"}</td>
                    <td className="px-3 py-2.5">{job.evaluation_json?.fidelity?.quality_overall ?? "—"}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => rerunMutation.mutate(job.id)}
                          className="p-1.5 rounded text-teal-600 hover:bg-teal-50 cursor-pointer"
                          title="Re-run experiment"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                        </button>
                        {(job.status === "pending" || job.status === "running") && (
                          <button
                            type="button"
                            onClick={() => cancelMutation.mutate(job.id)}
                            className="p-1.5 rounded text-amber-600 hover:bg-amber-50 cursor-pointer"
                            title="Cancel"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => deleteMutation.mutate(job.id)}
                          className="p-1.5 rounded text-rose-600 hover:bg-rose-50 cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
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

      {compared.length > 0 && (
        <section className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="text-base font-semibold text-slate-900">Side-by-Side Experiment Comparison</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {compared.map((j) => (
              <div key={j.id} className="border border-slate-200 rounded-lg p-4 space-y-1.5">
                <div className="font-bold text-sm">{j.model_type_display}</div>
                <div className="text-slate-500">ID: {j.id.slice(0, 8)}… · SDV {j.sdv_version || "N/A"}</div>
                <div>Quality: {j.evaluation_json?.fidelity?.quality_overall ?? "—"}</div>
                <div>DCR Protection: {String(j.evaluation_json?.privacy?.dcr_baseline_protection ?? "—")}</div>
                <div>Privacy Label: {String(j.evaluation_json?.privacy?.privacy_risk_label ?? "—")}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
