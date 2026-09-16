import { getCurrentUser } from "../services/authService";

const workspaceTitles = {
  chat: "Secure AI Gateway Workspace",
  vault: "Secure Knowledge Vault",
  logs: "Security Gateway Explanation Workspace"
};

export default function Header({ activeWorkspace }) {
  const user = getCurrentUser();

  return (
    <header className="header">
      <h1>{workspaceTitles[activeWorkspace] || "SentinelGuard AI"}</h1>
      {user && (
        <div className="header-meta">
          <span className="dept-badge">Department: {user.department || "General"}</span>
        </div>
      )}
    </header>
  );
}