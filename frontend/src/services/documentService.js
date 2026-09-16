import api from "./api";

export const getDocuments = async () => {
  const response = await api.get("/documents");
  return response.data;
};

export const uploadDocument = async (file, metadata) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("department", metadata.department);
  formData.append("classification", metadata.classification);
  formData.append("sensitivity", metadata.sensitivity);
  formData.append("owner", metadata.owner || "System");

  const response = await api.post("/documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const processDocument = async (documentId) => {
  const response = await api.post(`/documents/${documentId}/process`);
  return response.data;
};

export const deleteDocument = async (documentId) => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};