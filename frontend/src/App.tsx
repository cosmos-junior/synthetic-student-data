import { useState } from "react";
import { EvaluationPanel } from "./components/EvaluationPanel";
import { GeneratePanel } from "./components/GeneratePanel";
import { LoginPanel } from "./components/LoginPanel";

type Tab = "generate" | "evaluate";

export function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("auth_token"));
  const [username, setUsername] = useState<string>(() => localStorage.getItem("auth_user") ?? "");
  const [activeTab, setActiveTab] = useState<Tab>("generate");

  function handleAuthenticated(newToken: string, user: string) {
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("auth_user", user);
    setToken(newToken);
    setUsername(user);
  }

  function handleLogout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setToken(null);
    setUsername("");
  }

  if (!token) {
    return <LoginPanel onAuthenticated={handleAuthenticated} />;
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Privacy-Aware Synthetic Student Data Platform</h1>
          <p className="topbar-sub">Signed in as {username || "researcher"}</p>
        </div>
        <nav className="nav-tabs" aria-label="Main navigation">
          <button
            type="button"
            className={`tab-btn ${activeTab === "generate" ? "active" : ""}`}
            onClick={() => setActiveTab("generate")}
          >
            Generate Datasets
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "evaluate" ? "active" : ""}`}
            onClick={() => setActiveTab("evaluate")}
          >
            Evaluation &amp; Reports
          </button>
          <button type="button" className="btn btn-secondary" onClick={handleLogout}>
            Sign Out
          </button>
        </nav>
      </header>
      <main className="container">
        {activeTab === "generate" ? (
          <GeneratePanel token={token} />
        ) : (
          <EvaluationPanel token={token} />
        )}
      </main>
    </>
  );
}

export default App;
