import { useState, type DragEvent } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { FileUp, ShieldAlert } from "lucide-react";
import { uploadDataset } from "../api";

const uploadSchema = z.object({
  name: z.string().min(2, "Dataset name is required."),
  description: z.string().optional(),
  category: z.enum(["student_academic", "institutional_generic", "research_benchmark"]),
  authorization_confirmed: z.literal(true, {
    message: "You must confirm institutional authorization before uploading.",
  }),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

export function UploadDatasetPage({ token }: { token: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      category: "student_academic",
    },
  });

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  }

  async function onSubmit(values: UploadFormValues) {
    if (!file) {
      setServerError("Please select a CSV file to upload.");
      return;
    }
    setServerError(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", values.name);
      formData.append("description", values.description ?? "");
      formData.append("category", values.category);
      formData.append("authorization_confirmed", "true");

      const created = await uploadDataset(token, formData);
      await queryClient.invalidateQueries({ queryKey: ["datasets"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      navigate(`/explorer?dataset=${created.id}`);
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Upload Institutional Dataset</h1>
        <p className="text-sm text-slate-500">
          Upload an authorized CSV file for automated validation, profiling, and SDV metadata detection.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition ${
            dragging ? "border-teal-500 bg-teal-50/50" : "border-slate-300 bg-slate-50"
          }`}
        >
          <FileUp className="w-8 h-8 text-teal-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-800">
            Drag and drop your CSV file here, or browse from disk
          </p>
          <p className="text-xs text-slate-500 mt-1">Maximum file size: 25 MB · UTF-8 / Latin-1 CSV</p>
          <label className="inline-block mt-4 px-4 py-2 rounded-lg bg-white border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer">
            Browse Files
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          {file && (
            <div className="mt-3 text-xs font-medium text-teal-700">
              Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Dataset Name</label>
            <input
              type="text"
              {...register("name")}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              placeholder="e.g. 2025 BSc Cohort Records"
            />
            {errors.name && <p className="text-xs text-rose-600 mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Dataset Category</label>
            <select
              {...register("category")}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
            >
              <option value="student_academic">Student Academic</option>
              <option value="institutional_generic">Institutional Generic</option>
              <option value="research_benchmark">Research Benchmark</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
          <textarea
            rows={3}
            {...register("description")}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
            placeholder="Describe source cohort, preprocessing, and intended research use..."
          />
        </div>

        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <label className="flex items-start gap-2.5 text-xs text-amber-900 cursor-pointer">
            <input type="checkbox" {...register("authorization_confirmed")} className="mt-0.5" />
            <span>
              I confirm that I am authorized to process this institutional dataset and that handling complies with
              institutional governance and applicable data protection obligations.
            </span>
          </label>
        </div>
        {errors.authorization_confirmed && (
          <p className="text-xs text-rose-600">{errors.authorization_confirmed.message}</p>
        )}

        {serverError && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
            {serverError}
          </div>
        )}

        <button
          type="submit"
          disabled={uploading}
          className="px-5 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold disabled:opacity-60 cursor-pointer"
        >
          {uploading ? "Validating & Profiling..." : "Upload & Profile Dataset"}
        </button>
      </form>
    </div>
  );
}
