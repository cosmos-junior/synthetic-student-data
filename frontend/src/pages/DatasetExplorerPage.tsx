import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { CheckCircle2, Search } from "lucide-react";
import { confirmDatasetMetadata, listDatasets, previewDataset } from "../api";

const SDTYPE_OPTIONS = ["numerical", "categorical", "ordinal", "datetime", "boolean", "id"];

export function DatasetExplorerPage({ token }: { token: string }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("dataset") ?? "";
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [confirmMsg, setConfirmMsg] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: datasets = [] } = useQuery({
    queryKey: ["datasets", ""],
    queryFn: () => listDatasets(token),
  });

  const activeDataset = datasets.find((d) => d.id === selectedId) ?? datasets[0] ?? null;

  useEffect(() => {
    if (activeDataset) {
      setOverrides(activeDataset.column_overrides ?? {});
    }
  }, [activeDataset?.id]);

  const { data: preview, isLoading: previewLoading } = useQuery({
    queryKey: ["dataset-preview", activeDataset?.id, page, search, sortBy, sortDir],
    queryFn: () =>
      previewDataset(token, activeDataset!.id, {
        page,
        pageSize: 15,
        search,
        sortBy,
        sortDir,
      }),
    enabled: Boolean(activeDataset),
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmDatasetMetadata(token, activeDataset!.id, overrides),
    onSuccess: () => {
      setConfirmMsg("SDV metadata confirmed and saved.");
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
  });

  if (!activeDataset) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 text-sm text-slate-600">
        No uploaded datasets found. Upload a CSV dataset first to explore records, profiles, and metadata.
      </div>
    );
  }

  const profile = activeDataset.profile_json;
  const totalPages = preview ? Math.max(1, Math.ceil(preview.total_rows / preview.page_size)) : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dataset Explorer &amp; Metadata</h1>
          <p className="text-sm text-slate-500">
            Inspect automated statistical profiling, review identifier exclusions, and confirm SDV column types.
          </p>
        </div>
        <select
          value={activeDataset.id}
          onChange={(e) => {
            setSearchParams({ dataset: e.target.value });
            setPage(1);
            setConfirmMsg(null);
          }}
          className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm"
        >
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} ({d.row_count} rows)
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="text-xs text-slate-500">Rows</div>
          <div className="text-xl font-bold">{profile.row_count}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="text-xs text-slate-500">Columns</div>
          <div className="text-xl font-bold">{profile.column_count}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="text-xs text-slate-500">Duplicate Rows</div>
          <div className="text-xl font-bold">{profile.duplicate_rows}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="text-xs text-slate-500">Missing Cells</div>
          <div className="text-xl font-bold">
            {profile.missing_count} ({profile.missing_pct}%)
          </div>
        </div>
      </div>

      <section className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">SDV Metadata &amp; Column Classification</h2>
            <p className="text-xs text-slate-500">
              Columns marked as <strong>id</strong> are excluded from model training and regenerated synthetically.
            </p>
          </div>
          <button
            type="button"
            onClick={() => confirmMutation.mutate()}
            disabled={confirmMutation.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold cursor-pointer"
          >
            <CheckCircle2 className="w-4 h-4" />
            {confirmMutation.isPending ? "Saving..." : "Confirm Metadata"}
          </button>
        </div>

        {confirmMsg && (
          <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs">
            {confirmMsg}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase">
              <tr>
                <th className="px-3 py-2">Column</th>
                <th className="px-3 py-2">SDV Type</th>
                <th className="px-3 py-2">Unique</th>
                <th className="px-3 py-2">Missing</th>
                <th className="px-3 py-2">Flags</th>
                <th className="px-3 py-2">Summary Stats</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {profile.columns.map((col) => (
                <tr key={col.name}>
                  <td className="px-3 py-2 font-medium text-slate-900">{col.name}</td>
                  <td className="px-3 py-2">
                    <select
                      value={overrides[col.name] ?? col.detected_sdtype}
                      onChange={(e) => setOverrides((prev) => ({ ...prev, [col.name]: e.target.value }))}
                      className="px-2 py-1 border border-slate-200 rounded bg-white"
                    >
                      {SDTYPE_OPTIONS.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">{col.unique_count}</td>
                  <td className="px-3 py-2">
                    {col.missing_count} ({col.missing_pct}%)
                  </td>
                  <td className="px-3 py-2 space-x-1">
                    {col.is_identifier && (
                      <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 font-medium">ID</span>
                    )}
                    {col.is_sensitive && (
                      <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-medium">Sensitive</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-500">
                    {col.stats
                      ? `min ${col.stats.min} · mean ${col.stats.mean} · max ${col.stats.max}`
                      : col.top_categories
                      ? Object.keys(col.top_categories).slice(0, 3).join(", ")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-slate-900">Paginated Record Explorer</h2>
          <div className="flex items-center gap-2 border border-slate-200 rounded-lg px-3 py-1.5">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Filter rows..."
              className="text-xs focus:outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
              <tr>
                {(preview?.columns ?? []).map((col) => (
                  <th
                    key={col}
                    onClick={() => {
                      if (sortBy === col) {
                        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                      } else {
                        setSortBy(col);
                        setSortDir("asc");
                      }
                    }}
                    className="px-3 py-2 cursor-pointer hover:bg-slate-100 whitespace-nowrap"
                  >
                    {col} {sortBy === col ? (sortDir === "asc" ? "↑" : "↓") : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {previewLoading ? (
                <tr>
                  <td className="px-3 py-4 text-slate-500">Loading rows...</td>
                </tr>
              ) : (
                (preview?.rows ?? []).map((row, idx) => (
                  <tr key={idx}>
                    {(preview?.columns ?? []).map((col) => (
                      <td key={col} className="px-3 py-2 whitespace-nowrap">
                        {row[col] === null || row[col] === undefined ? "—" : String(row[col])}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            Page {page} of {totalPages} ({preview?.total_rows ?? 0} matching rows)
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 rounded border border-slate-200 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 rounded border border-slate-200 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
