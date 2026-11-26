import { useQuery } from "@tanstack/react-query";
import { API_BASE, fetchProfile } from "../api";

export function SettingsPage() {
  const docsUrl = API_BASE.replace(/\/api\/?$/, "/api/docs/");
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Platform Settings</h1>
        <p className="text-sm text-slate-500">
          API configuration, documentation links, and institutional data governance controls.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4 text-sm">
        <div>
          <div className="text-xs font-semibold uppercase text-slate-500">Backend API Base URL</div>
          <code className="block mt-1 px-3 py-2 rounded bg-slate-100 text-slate-800">{API_BASE}</code>
        </div>
        <div>
          <div className="text-xs font-semibold uppercase text-slate-500">OpenAPI / Swagger Documentation</div>
          <a
            href={docsUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-block mt-1 text-teal-600 font-medium hover:underline"
          >
            {docsUrl}
          </a>
        </div>
        <div className="border-t border-slate-100 pt-4 text-xs text-slate-600 space-y-1">
          <p>
            <strong>Data Protection Controls:</strong> Token-authenticated endpoints, per-user dataset &amp; experiment
            ownership isolation, private server-side file storage, CSV formula-injection neutralization, and audit
            logging.
          </p>
        </div>
      </div>
    </div>
  );
}

export function ProfilePage({ token, onLogout }: { token: string; onLogout: () => void }) {
  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: () => fetchProfile(token),
  });

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">User Profile</h1>
        <p className="text-sm text-slate-500">Authenticated researcher account details.</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4 text-sm">
        {isLoading || !profile ? (
          <p className="text-slate-500">Loading profile...</p>
        ) : (
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-slate-500">Username</dt>
              <dd className="font-semibold text-slate-900">{profile.username}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Email</dt>
              <dd className="font-medium text-slate-900">{profile.email || "Not set"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Role</dt>
              <dd className="font-medium text-slate-900">{profile.is_staff ? "Administrator" : "Researcher"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Joined</dt>
              <dd className="text-slate-600">{new Date(profile.date_joined).toLocaleDateString()}</dd>
            </div>
          </dl>
        )}

        <button
          type="button"
          onClick={onLogout}
          className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold cursor-pointer"
        >
          Sign Out &amp; Invalidate Token
        </button>
      </div>
    </div>
  );
}
