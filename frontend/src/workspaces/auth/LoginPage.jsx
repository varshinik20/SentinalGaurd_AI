import { useState } from "react";
import { login } from "../../services/authService";

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      onLoginSuccess();
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 
        "Failed to authenticate. Please check your credentials."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleQuickCreds() {
    setEmail("admin@sentinelguard.ai");
    setPassword("AdminPass123!");
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-logo">SentinelGuard AI</h1>
        <p className="login-subtitle">Enterprise AI Security Gateway</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              placeholder="admin@sentinelguard.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="login-error">⚠️ {error}</div>}

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? "Authenticating..." : "Sign In to Gateway"}
          </button>

          <button
            type="button"
            className="quick-creds-btn"
            onClick={handleQuickCreds}
          >
            Pre-fill Default Admin Credentials
          </button>
        </form>
      </div>
    </div>
  );
}
