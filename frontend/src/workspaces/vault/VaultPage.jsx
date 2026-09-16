import { useEffect, useState } from "react";
import { getDocuments, uploadDocument, processDocument, deleteDocument } from "../../services/documentService";

export default function VaultPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Upload Modal State
  const [selectedFile, setSelectedFile] = useState(null);
  const [department, setDepartment] = useState("Finance");
  const [classification, setClassification] = useState("INTERNAL");
  const [sensitivity, setSensitivity] = useState("MEDIUM");
  const [owner, setOwner] = useState("");
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      setLoading(true);
      const data = await getDocuments();
      setDocuments(data);
    } catch (error) {
      console.error("Failed to load documents:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      setUploading(true);
      await uploadDocument(selectedFile, {
        department,
        classification,
        sensitivity,
        owner: owner || "System Admin",
      });
      setIsModalOpen(false);
      setSelectedFile(null);
      setOwner("");
      await loadDocuments();
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Failed to upload document: " + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  }

  async function handleProcess(docId) {
    try {
      await processDocument(docId);
      await loadDocuments();
    } catch (error) {
      console.error("Failed to trigger processing:", error);
      alert("Failed to process document.");
    }
  }

  async function handleDelete(docId) {
    if (!window.confirm("Are you sure you want to delete this document from the vault? This will also remove its vectors from FAISS.")) return;
    try {
      await deleteDocument(docId);
      await loadDocuments();
    } catch (error) {
      console.error("Deletion failed:", error);
      alert("Failed to delete document.");
    }
  }

  return (
    <div className="workspace-page">
      <div className="vault-controls">
        <p style={{ color: "var(--text-secondary)" }}>Manage secure training corpora and corporate documents mapped to security classification tags.</p>
        <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
          Upload Document
        </button>
      </div>

      <div className="glass-card table-container">
        <table className="vault-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Classification</th>
              <th>Department</th>
              <th>Status</th>
              <th>Owner</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="6" style={{ textAlign: "center", color: "var(--text-secondary)" }}>Loading vault data...</td>
              </tr>
            ) : documents.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: "center", color: "var(--text-secondary)" }}>No documents uploaded yet.</td>
              </tr>
            ) : (
              documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.original_filename || doc.filename}</td>
                  <td>
                    <span className={`class-pill ${doc.classification}`}>
                      {doc.classification}
                    </span>
                  </td>
                  <td>
                    <span className="dept-badge">{doc.department}</span>
                  </td>
                  <td>
                    <span className={`status-pill ${doc.status?.toLowerCase()}`}>
                      {doc.status}
                    </span>
                  </td>
                  <td style={{ color: "var(--text-secondary)" }}>{doc.owner || "System"}</td>
                  <td style={{ textAlign: "right" }}>
                    <div className="action-group" style={{ justifyContent: "flex-end" }}>
                      {doc.status !== "READY" && (
                        <button
                          className="btn-icon"
                          onClick={() => handleProcess(doc.id)}
                          title="Process Text & Vector Index"
                        >
                          ⚙️
                        </button>
                      )}
                      <button
                        className="btn-icon delete"
                        onClick={() => handleDelete(doc.id)}
                        title="Delete Document"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Upload Secure Document</h3>
            <form onSubmit={handleUpload}>
              <div className="file-dropzone">
                <input
                  type="file"
                  id="vault-file"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  style={{ display: "none" }}
                  required
                />
                <label htmlFor="vault-file" style={{ cursor: "pointer" }}>
                  {selectedFile ? (
                    <div className="dropzone-filename">📄 {selectedFile.name}</div>
                  ) : (
                    <div className="dropzone-label">Drag & drop or Click to choose CSV, XLSX, TXT file</div>
                  )}
                </label>
              </div>

              <div className="form-group">
                <label>Department Access Restriction</label>
                <select value={department} onChange={(e) => setDepartment(e.target.value)}>
                  <option value="Finance">Finance</option>
                  <option value="HR">HR</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Platform">Platform</option>
                </select>
              </div>

              <div className="form-group">
                <label>Security Classification Level</label>
                <select value={classification} onChange={(e) => setClassification(e.target.value)}>
                  <option value="PUBLIC">PUBLIC (Everyone)</option>
                  <option value="INTERNAL">INTERNAL (Internal Employees)</option>
                  <option value="CONFIDENTIAL">CONFIDENTIAL (Restricted Department)</option>
                  <option value="HIGHLY_CONFIDENTIAL">HIGHLY CONFIDENTIAL (Key Leads Only)</option>
                  <option value="RESTRICTED">RESTRICTED (Exclusive Admin)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Sensitivity Tier</label>
                <select value={sensitivity} onChange={(e) => setSensitivity(e.target.value)}>
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                </select>
              </div>

              <div className="form-group">
                <label>Document Owner</label>
                <input
                  type="text"
                  placeholder="e.g. Finance Lead"
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-text" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={uploading}>
                  {uploading ? "Uploading..." : "Save to Vault"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}