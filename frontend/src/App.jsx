import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import LoginPage from "./workspaces/auth/LoginPage";
import ChatPage from "./workspaces/chat/ChatPage";
import VaultPage from "./workspaces/vault/VaultPage";
import SecurityExplanationPage from "./workspaces/security-explanation/SecurityExplanationPage";
import "./styles/app.css";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [activeWorkspace, setActiveWorkspace] = useState("chat");

  if (!token) {
    return <LoginPage onLoginSuccess={() => setToken(localStorage.getItem("token"))} />;
  }

  return (
    <div className="app-layout">
      <Sidebar
        activeWorkspace={activeWorkspace}
        onWorkspaceChange={setActiveWorkspace}
      />

      <main className="main-content">
        <Header activeWorkspace={activeWorkspace} />
        
        {activeWorkspace === "chat" && <ChatPage />}
        {activeWorkspace === "vault" && <VaultPage />}
        {activeWorkspace === "logs" && <SecurityExplanationPage />}
      </main>
    </div>
  );
}