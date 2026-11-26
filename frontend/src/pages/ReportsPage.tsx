import { useQuery } from "@tanstack/react-query";
import { Download, FileText } from "lucide-react";
import { downloadJobCsv, downloadJobPdf, listJobs } from "../api";

export function ReportsPage({ token }: { token: string }) {
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs(token),
  });

  const completed = jobs.filter((j) => j.status === "completed");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Exportable Reports &amp; Datasets</h1>
        <p className="text-sm text-slate-500">
          Download formula-sanitized synthetic CSV datasets and PDF experiment evaluation reports.
        </p>
      </div>

      <section className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Dataset</th>
                <th className="px-4 py-3">Rows</th>
                <th className="px-4 py-3">Completed</th>
                <th className="px-4 py-3">Exports</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-slate-500">
                    Loading completed experiments...
                  </td>
                </tr>
              ) : completed.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-slate-500">
                    No completed experiments available for export yet.
                  </td>
                </tr>
              ) : (
                completed.map((job) => (
                  <tr key={job.id}>
                    <td className="px-4 py-3 font-semibold text-slate-900">{job.model_type_display}</td>
                    <td className="px-4 py-3 text-slate-600">{job.dataset_name}</td>
                    <td className="px-4 py-3">{job.num_rows}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => void downloadJobCsv(token, job.id, `${job.model_type}_${job.num_rows}.csv`)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold cursor-pointer"
                        >
                          <Download className="w-3.5 h-3.5" /> CSV
                        </button>
                        <button
                          type="button"
                          onClick={() => void downloadJobPdf(token, job.id, `experiment_${job.id}.pdf`)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer"
                        >
                          <FileText className="w-3.5 h-3.5" /> PDF Report
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
    </div>
  );
}
