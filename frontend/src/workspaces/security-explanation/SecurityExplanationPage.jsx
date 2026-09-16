import { useEffect, useState } from "react";
import { getAuditLogs } from "../../services/auditService";

export default function SecurityExplanationPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState(null);

  // Filters
  const [decision, setDecision] = useState("");
  const [riskLevel, setRiskLevel] = useState("");

  useEffect(() => {
    loadLogs();
  }, [decision, riskLevel]);

  async function loadLogs() {
    try {
      setLoading(true);
      const data = await getAuditLogs({
        decision: decision || undefined,
        risk_level: riskLevel || undefined,
      });
      setLogs(data);
    } catch (error) {
      console.error("Failed to load audit logs:", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="workspace-page">
      <div className="security-dashboard">
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <select
              className="provider-select"
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
            >
              <option value="">Filter by Decision (All)</option>
              <option value="ALLOW">ALLOW</option>
              <option value="WARN">WARN</option>
              <option value="REWRITE">REWRITE</option>
              <option value="BLOCK">BLOCK</option>
              <option value="HUMAN_REVIEW">HUMAN_REVIEW</option>
            </select>

            <select
              className="provider-select"
              value={riskLevel}
              onChange={(e) => setRiskLevel(e.target.value)}
            >
              <option value="">Filter by Risk Level (All)</option>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div className="glass-card table-container">
            <h4 style={{ marginBottom: 16 }}>Gateway Threat Audit Logs</h4>
            <table className="vault-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Decision</th>
                  <th>Risk Level</th>
                  <th>Risk Score</th>
                  <th style={{ textAlign: "right" }}>Analysis</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: "center", color: "var(--text-secondary)" }}>Loading logs...</td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: "center", color: "var(--text-secondary)" }}>No security events logged yet.</td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      style={{ cursor: "pointer" }}
                    >
                      <td>{new Date(log.created_at).toLocaleString()}</td>
                      <td>
                        <span className={`status-pill ${log.decision?.toLowerCase()}`}>
                          {log.decision}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`status-pill ${
                            log.risk_level === "LOW"
                              ? "ready"
                              : log.risk_level === "MEDIUM"
                              ? "processing"
                              : "failed"
                          }`}
                        >
                          {log.risk_level}
                        </span>
                      </td>
                      <td>{Math.round(log.risk_score * 100)}%</td>
                      <td style={{ textAlign: "right", color: "var(--accent-cyan)", fontWeight: 600 }}>Inspect 🔍</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="glass-card">
            <h4 style={{ marginBottom: 16 }}>Threat Component Analysis</h4>
            {selectedLog ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <strong>Correlation ID:</strong>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 4, fontFamily: "monospace" }}>
                    {selectedLog.request_id}
                  </div>
                </div>

                <div>
                  <strong>Policy Matched:</strong>
                  <div style={{ fontSize: "0.9rem", marginTop: 4, color: "var(--accent-cyan)" }}>
                    {selectedLog.evidence_json?.policy?.name || "DEFAULT_ALLOW"}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 2 }}>
                    {selectedLog.evidence_json?.policy?.description}
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
                  <strong>Security Engines Breakdowns:</strong>
                  
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                      <span>Semantic Similarity</span>
                      <span>{Math.round((selectedLog.evidence_json?.components?.semantic_similarity || 0) * 100)}%</span>
                    </div>
                    <div className="risk-indicator-bar">
                      <div className="risk-indicator-fill HIGH" style={{ width: `${(selectedLog.evidence_json?.components?.semantic_similarity || 0) * 100}%` }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                      <span>Factual Context Overlap</span>
                      <span>{Math.round((selectedLog.evidence_json?.components?.fact_leakage || 0) * 100)}%</span>
                    </div>
                    <div className="risk-indicator-bar">
                      <div className="risk-indicator-fill LOW" style={{ width: `${(selectedLog.evidence_json?.components?.fact_leakage || 0) * 100}%` }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                      <span>Sensitive Information (PII)</span>
                      <span>{Math.round((selectedLog.evidence_json?.components?.sensitive_info || 0) * 100)}%</span>
                    </div>
                    <div className="risk-indicator-bar">
                      <div className="risk-indicator-fill CRITICAL" style={{ width: `${(selectedLog.evidence_json?.components?.sensitive_info || 0) * 100}%` }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem" }}>
                      <span>Stateful Behavior Probes</span>
                      <span>{Math.round((selectedLog.evidence_json?.components?.behavior || 0) * 100)}%</span>
                    </div>
                    <div className="risk-indicator-bar">
                      <div className="risk-indicator-fill MEDIUM" style={{ width: `${(selectedLog.evidence_json?.components?.behavior || 0) * 100}%` }} />
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 12 }}>
                  <strong>Evidence Log JSON:</strong>
                  <div className="json-viewer">
                    {JSON.stringify(selectedLog.evidence_json?.evidence || [], null, 2)}
                  </div>
                </div>
              </div>
            ) : (
              <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>Select a gateway audit log entry from the list to inspect threat breakdowns, components, and matching policy structures.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
