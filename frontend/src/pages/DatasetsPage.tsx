import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { CheckCircle, Search, Trash2, Upload } from "lucide-react";
import { deleteDataset, listDatasets } from "../api";

export function DatasetsPage({ token }: { token: string }) {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();

  const { data: datasets = [], isLoading, error } = useQuery({
    queryKey: ["datasets", search],
    queryFn: () => listDatasets(token, search),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDataset(token, id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Institutional Datasets</h1>
          <p className="text-sm text-slate-500">
            Manage authorized datasets, inspect profiles, and confirm SDV metadata before generation.
          </p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold"
        >
          <Upload className="w-4 h-4" />
          Upload CSV
        </Link>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
        <Search className="w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search datasets by name..."
          className="w-full text-sm focus:outline-none"
        />
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error instanceof Error ? error.message : "Failed to load datasets."}
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Shape</th>
                <th className="px-4 py-3">Metadata</th>
                <th className="px-4 py-3">Uploaded</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-slate-500">
                    Loading datasets...
                  </td>
                </tr>
              ) : datasets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-slate-500">
                    No datasets uploaded yet. Upload a CSV or use the built-in student benchmark in Generate.
                  </td>
                </tr>
              ) : (
                datasets.map((ds) => (
                  <tr key={ds.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">
                      <div>{ds.name}</div>
                      <div className="text-xs text-slate-400">{ds.original_filename}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{ds.category_display}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {ds.row_count} × {ds.column_count}
                    </td>
                    <td className="px-4 py-3">
                      {ds.metadata_confirmed ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
                          <CheckCircle className="w-3 h-3" /> Confirmed
                        </span>
                      ) : (
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
                          Needs Review
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {new Date(ds.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/explorer?dataset=${ds.id}`}
                          className="px-2.5 py-1 rounded-md border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-100"
                        >
                          Explore
                        </Link>
                        <button
                          type="button"
                          onClick={() => deleteMutation.mutate(ds.id)}
                          className="p-1.5 rounded-md text-rose-600 hover:bg-rose-50 cursor-pointer"
                          title="Delete dataset"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
