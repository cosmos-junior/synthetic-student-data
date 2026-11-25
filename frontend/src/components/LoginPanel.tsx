import { useState, type FormEvent } from "react";
import { login } from "../api";

interface LoginPanelProps {
  onAuthenticated: (token: string, username: string) => void;
}

export function LoginPanel({ onAuthenticated }: LoginPanelProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login(username.trim(), password);
      onAuthenticated(token, username.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrapper">
      <div className="card">
        <h2>Sign in to Synthetic Student Data Platform</h2>
        <p className="topbar-sub" style={{ marginBottom: "1rem" }}>
          Authorized researchers can generate datasets and inspect comparative evaluations.
        </p>
        <form onSubmit={handleSubmit} className="field" style={{ gap: "0.85rem" }}>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. admin"
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
        {error && <div className="alert alert-error">{error}</div>}
      </div>
    </div>
  );
}
