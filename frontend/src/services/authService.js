import api from "./api";

export const login = async (email, password) => {
  const response = await api.post("/auth/login", { email, password });
  const data = response.data;
  if (data.access_token) {
    localStorage.setItem("token", data.access_token);
    // Fetch profile info
    const profile = await getMe();
    localStorage.setItem("user", JSON.stringify(profile));
  }
  return data;
};

export const logout = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.location.reload();
};

export const getMe = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

export const getCurrentUser = () => {
  const user = localStorage.getItem("user");
  return user ? JSON.parse(user) : null;
};
