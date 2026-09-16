import api from "./api";

export const getSessions = async () => {
  const response = await api.get("/chat/sessions");
  return response.data;
};

export const deleteSession = async (sessionId) => {
  const response = await api.delete(`/chat/sessions/${sessionId}`);
  return response.data;
};

export const getMessages = async (sessionId) => {
  const response = await api.get(`/chat/sessions/${sessionId}/messages`);
  return response.data;
};

export const sendMessage = async (message, provider, sessionId = null) => {
  const payload = {
    message,
    provider: provider || "offline",
    session_id: sessionId,
  };
  const response = await api.post("/chat", payload);
  return response.data;
};
