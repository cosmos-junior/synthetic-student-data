import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { logoutUser } from "./api";
import { Layout } from "./components/Layout";
import { LoginPanel } from "./components/LoginPanel";
import { DatasetExplorerPage } from "./pages/DatasetExplorerPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { GeneratePage } from "./pages/GeneratePage";
import { MlUtilityPage } from "./pages/MlUtilityPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { ReportsPage } from "./pages/ReportsPage";
import { ProfilePage, SettingsPage } from "./pages/SettingsAndProfilePages";
import { UploadDatasetPage } from "./pages/UploadDatasetPage";

export function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("auth_token"));
  const [username, setUsername] = useState<string>(() => localStorage.getItem("auth_user") ?? "");

  function handleAuthenticated(newToken: string, user: string) {
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("auth_user", user);
    setToken(newToken);
    setUsername(user);
  }

  async function handleLogout() {
    if (token) {
      try {
        await logoutUser(token);
      } catch {
        // Clear local session even if token already expired
      }
    }
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setToken(null);
    setUsername("");
  }

  if (!token) {
    return <LoginPanel onAuthenticated={handleAuthenticated} />;
  }

  return (
    <BrowserRouter>
      <Layout username={username} onLogout={() => void handleLogout()}>
        <Routes>
          <Route path="/" element={<OverviewPage token={token} />} />
          <Route path="/datasets" element={<DatasetsPage token={token} />} />
          <Route path="/upload" element={<UploadDatasetPage token={token} />} />
          <Route path="/explorer" element={<DatasetExplorerPage token={token} />} />
          <Route path="/generate" element={<GeneratePage token={token} />} />
          <Route path="/evaluation" element={<EvaluationPage token={token} />} />
          <Route path="/privacy" element={<PrivacyPage token={token} />} />
          <Route path="/ml-utility" element={<MlUtilityPage token={token} />} />
          <Route path="/experiments" element={<ExperimentsPage token={token} />} />
          <Route path="/reports" element={<ReportsPage token={token} />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/profile" element={<ProfilePage token={token} onLogout={() => void handleLogout()} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
