import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Activity, CheckCircle2, Database, FlaskConical, PlayCircle, XCircle } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchDashboardSummary } from "../api";

export function OverviewPage({ token }: { token: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => fetchDashboardSummary(token),
  });

  if (isLoading) {
    return <div className="text-sm text-slate-500">Loading live overview metrics...</div>;
  }
  if (error || !data) {
    return (
      <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
        {error instanceof Error ? error.message : "Unable to load dashboard summary."}
      </div>
    );
  }

  const statCards = [
    { label: "Uploaded Datasets", value: data.total_datasets, icon: Database, color: "text-teal-600 bg-teal-50" },
    { label: "Total Experiments", value: data.total_experiments, icon: FlaskConical, color: "text-slate-700 bg-slate-100" },
    { label: "Completed Jobs", value: data.completed_jobs, icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50" },
    { label: "Failed Jobs", value: data.failed_jobs, icon: XCircle, color: "text-rose-600 bg-rose-50" },
  ];

  const chartData = data.latest_evaluations.filter((e) => e.model_name !== "Real Baseline (TRTR)");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Research Overview</h1>
          <p className="text-sm text-slate-500">
            Live experiment status, dataset inventory, and comparative model benchmarks.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/upload"
            className="px-4 py-2 rounded-lg border border-slate-300 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Upload Dataset
          </Link>
          <Link
            to="/generate"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold"
          >
            <PlayCircle className="w-4 h-4" />
            Quick Generate
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4">
              <div className={`p-3 rounded-xl ${card.color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-medium text-slate-500">{card.label}</div>
                <div className="text-2xl font-bold text-slate-900">{card.value}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-900">Latest Model Quality Comparison</h2>
            <Link to="/evaluation" className="text-xs font-semibold text-teal-600 hover:underline">
              Full Evaluation →
            </Link>
          </div>
          {chartData.length === 0 ? (
            <p className="text-sm text-slate-500">
              No comparative evaluations stored yet. Visit Model Evaluation to run benchmarks.
            </p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="model_name" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="quality_overall" name="Quality" fill="#0d9488" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="status_macro_f1" name="Macro-F1" fill="#0f172a" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>

        <section className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-900">Recent Audit Activity</h2>
            <Activity className="w-4 h-4 text-slate-400" />
          </div>
          {data.recent_activity.length === 0 ? (
            <p className="text-sm text-slate-500">No recorded activity yet.</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {data.recent_activity.map((log) => (
                <li key={log.id} className="py-2.5 flex items-center justify-between gap-2">
                  <div>
                    <span className="font-medium text-slate-800">{log.action.replace(/_/g, " ")}</span>
                    <span className="text-slate-500"> · {log.resource_type}</span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
