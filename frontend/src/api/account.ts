import { http } from "@/api/http";

export const accountApi = {
  login: (payload: Record<string, unknown>) => http.post("/auth/login/", payload),
  logout: () => http.post("/auth/logout/"),
  me: () => http.get("/auth/me/"),
  profile: () => http.get("/profile/"),
  updateProfile: (payload: Record<string, unknown>) => http.put("/profile/", payload),
  changePassword: (payload: Record<string, unknown>) => http.put("/profile/password/", payload),
  users: (params?: Record<string, unknown>) => http.get("/users/", { params }),
  createUser: (payload: Record<string, unknown>) => http.post("/users/", payload),
  updateUser: (id: number, payload: Record<string, unknown>) => http.patch(`/users/${id}/`, payload),
  enableUser: (id: number) => http.post(`/users/${id}/enable/`),
  disableUser: (id: number) => http.post(`/users/${id}/disable/`),
  resetPassword: (id: number, payload: Record<string, unknown>) => http.post(`/users/${id}/reset-password/`, payload),
  forceLogout: (id: number) => http.post(`/users/${id}/force-logout/`),
  roles: (params?: Record<string, unknown>) => http.get("/roles/", { params }),
  createRole: (payload: Record<string, unknown>) => http.post("/roles/", payload),
  updateRole: (id: number, payload: Record<string, unknown>) => http.patch(`/roles/${id}/`, payload),
  deleteRole: (id: number) => http.delete(`/roles/${id}/`),
  permissions: () => http.get("/permissions/"),
  auditLogs: (params?: Record<string, unknown>) => http.get("/audit-logs/", { params }),
  loginAttempts: (params?: Record<string, unknown>) => http.get("/login-attempts/", { params }),
};
