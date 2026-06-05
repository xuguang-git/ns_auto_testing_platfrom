import axios from "axios";
import router from "@/router";

export const http = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("ns_token") || sessionStorage.getItem("ns_token");
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && router.currentRoute.value.path !== "/login") {
      localStorage.removeItem("ns_token");
      sessionStorage.removeItem("ns_token");
      router.push({ path: "/login", query: { redirect: router.currentRoute.value.fullPath } });
    }
    return Promise.reject(error);
  },
);
