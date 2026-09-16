import { useEffect, useState, useRef } from "react";
import { getSessions, deleteSession, getMessages, sendMessage } from "../../services/chatService";

export default function ChatPage() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [provider, setProvider] = useState("local");
  const [loading, setLoading] = useState(false);
  const [selectedSecuritySummary, setSelectedSecuritySummary] = useState(null);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  async function loadSessions() {
    try {
      const data = await getSessions();
      setSessions(data);
      if (data.length > 0 && !currentSessionId) {
        setCurrentSessionId(data[0].id);
        const p = data[0].provider;
        setProvider(p === "offline" ? "local" : (p || "local"));
      }
    } catch (error) {
      console.error("Failed to load threads:", error);
    }
  }

  async function loadMessages(sessionId) {
    try {
      const data = await getMessages(sessionId);
      setMessages(data);
    } catch (error) {
      console.error("Failed to load messages:", error);
    }
  }

  async function handleSend(e) {
    e.preventDefault();
    if (!inputText.trim() || loading) return;

    const userText = inputText;
    setInputText("");
    setLoading(true);

    // Optimistically add user message to list
    setMessages((prev) => [...prev, { sender: "user", content: userText }]);

    try {
      const res = await sendMessage(userText, provider, currentSessionId);
      
      // If we created a new session, reload session list and select it
      if (!currentSessionId) {
        await loadSessions();
      } else {
        await loadMessages(currentSessionId);
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      alert("Error generating response: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteSession(sessionId, e) {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this chat thread?")) return;
    try {
      await deleteSession(sessionId);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }
      await loadSessions();
    } catch (error) {
      console.error("Delete thread failed:", error);
    }
  }

  function handleNewChat() {
    setCurrentSessionId(null);
    setMessages([]);
  }

  return (
    <div className="chat-container">
      <div className="chat-history-sidebar">
        <button className="new-chat-btn" onClick={handleNewChat}>
          ➕ New Thread
        </button>
        <div className="thread-list">
          {sessions.map((sess) => (
            <button
              key={sess.id}
              className={`thread-item ${currentSessionId === sess.id ? "active" : ""}`}
              onClick={() => {
                setCurrentSessionId(sess.id);
                setProvider(sess.provider || "offline");
              }}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                💬 {sess.title || "Untitled Conversation"}
              </span>
              <span
                className="delete-thread-btn"
                onClick={(e) => handleDeleteSession(sess.id, e)}
              >
                🗑️
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="chat-main">
        <div className="chat-top-bar">
          <span style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>
            Active Session: <strong style={{ color: "#fff" }}>{currentSessionId ? "Thread Loaded" : "New Conversation"}</strong>
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Model Provider:</span>
            <select
              className="provider-select"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="local">🧠 Smart Local Engine (Built-in On-Device)</option>
              <option value="ollama">🦙 Ollama / Local LLM (OpenAI-Compatible)</option>
              <option value="openai">⚡ OpenAI GPT-4o (Cloud API)</option>
              <option value="gemini">✨ Google Gemini 1.5 (Cloud API)</option>
              <option value="anthropic">🔮 Anthropic Claude 3.5 (Cloud API)</option>
            </select>
          </div>
        </div>

        <div className="chat-messages-area">
          {messages.length === 0 ? (
            <div className="chat-empty-state">
              <h3>Secure AI Workspace</h3>
              <p>SentinelGuard AI acts as a secure reverse proxy gateway between you and the LLM models. Ask questions, retrieve facts, and verify security explanations.</p>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isAi = msg.sender === "ai";
              const decision = msg.security_decision;
              return (
                <div key={index} className={`message-bubble ${msg.sender} ${decision ? decision.toLowerCase() : ""}`}>
                  <div className="message-sender">
                    {msg.sender === "user" 
                      ? "You" 
                      : decision && decision !== "ALLOW" 
                        ? `SentinelGuard AI (${decision.replace('_', ' ')})` 
                        : "SentinelGuard AI"}
                  </div>
                  <div className="message-content">
                    {msg.content}
                  </div>

                  {isAi && decision && (
                    <button
                      className={`security-badge ${decision}`}
                      onClick={() => {
                        setSelectedSecuritySummary({
                          decision: decision,
                          risk_score: msg.risk_score,
                        });
                      }}
                    >
                      🛡️ {decision.replace('_', ' ')} {msg.risk_score !== undefined && msg.risk_score !== null ? `(Risk: ${Math.round(msg.risk_score * 100)}%)` : ""}
                    </button>
                  )}
                </div>
              );
            })
          )}
          {loading && (
            <div className="message-bubble ai">
              <div className="message-sender">Gateway Processing</div>
              <div className="message-content">Generating secure response...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSend} className="chat-input-bar">
          <input
            type="text"
            className="chat-input-field"
            placeholder="Query internal knowledge base..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="btn-send" disabled={loading}>
            ✈️
          </button>
        </form>
      </div>

      {selectedSecuritySummary && (
        <div className="modal-overlay" onClick={() => setSelectedSecuritySummary(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Security Inspection Verdict</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <strong>Mitigation Decision:</strong>
                <span className={`status-pill ${selectedSecuritySummary.decision.toLowerCase()}`} style={{ marginLeft: 8 }}>
                  {selectedSecuritySummary.decision}
                </span>
              </div>
              <div>
                <strong>Weighted Hybrid Risk:</strong> {Math.round(selectedSecuritySummary.risk_score * 100)}%
                <div className="risk-indicator-bar">
                  <div
                    className={`risk-indicator-fill ${
                      selectedSecuritySummary.risk_score < 0.2
                        ? "LOW"
                        : selectedSecuritySummary.risk_score < 0.5
                        ? "MEDIUM"
                        : selectedSecuritySummary.risk_score < 0.8
                        ? "HIGH"
                        : "CRITICAL"
                    }`}
                    style={{ width: `${selectedSecuritySummary.risk_score * 100}%` }}
                  />
                </div>
              </div>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                The SentinelGuard Gateway inspected this response for semantic leaks, numerical/currency context mismatches, PII, and probing behavior. Matched rules are written to the admin audit log.
              </p>
            </div>
            <div className="modal-actions">
              <button className="btn-primary" onClick={() => setSelectedSecuritySummary(null)}>
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
