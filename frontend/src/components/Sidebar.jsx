import { getCurrentUser, logout } from "../services/authService";

const menuItems = [
  { id: "chat", label: "💬 Secure AI Chat" },
  { id: "vault", label: "🗄️ Knowledge Vault" },
  { id: "logs", label: "🛡️ Security Gateway Logs" }
];

export default function Sidebar({ activeWorkspace, onWorkspaceChange }) {
  const user = getCurrentUser();

  return (
    <aside className="sidebar">
      <div className="logo">
        <h2>SentinelGuard AI</h2>
      </div>

      <nav>
        {menuItems.map((item) => (
          <button
            key={item.id}
            className={`nav-button ${activeWorkspace === item.id ? "active" : ""}`}
            onClick={() => onWorkspaceChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {user && (
        <div className="user-profile-section">
          <div className="profile-info">
            <span className="profile-name">👤 {user.full_name || "User"}</span>
            <span className="profile-role-badge">{user.role || "Analyst"}</span>
          </div>
          <button className="logout-button" onClick={logout}>
            Sign Out
          </button>
        </div>
      )}
    </aside>
  );
}