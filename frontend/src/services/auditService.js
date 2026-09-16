import api from "./api";

export const getAuditLogs = async (filters = {}) => {
  const params = {
    skip: filters.skip || 0,
    limit: filters.limit || 100,
  };
  if (filters.decision) {
    params.decision = filters.decision;
  }
  if (filters.risk_level) {
    params.risk_level = filters.risk_level;
  }
  const response = await api.get("/audit/logs", { params });
  return response.data;
};
