import { defineStore } from "pinia";

import { accountApi } from "@/api/account";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as any,
    token: localStorage.getItem("ns_token") || sessionStorage.getItem("ns_token") || "",
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    permissions: (state) => new Set<string>(state.user?.permissions || []),
  },
  actions: {
    async login(payload: { username: string; password: string; remember_me: boolean }) {
      const { data } = await accountApi.login(payload);
      this.token = data.token;
      this.user = data.user;
      const storage = payload.remember_me ? localStorage : sessionStorage;
      storage.setItem("ns_token", data.token);
      if (payload.remember_me) sessionStorage.removeItem("ns_token");
      else localStorage.removeItem("ns_token");
      return data;
    },
    async loadMe() {
      if (!this.token) return null;
      const { data } = await accountApi.me();
      this.user = data;
      return data;
    },
    async logout() {
      try {
        if (this.token) await accountApi.logout();
      } finally {
        this.user = null;
        this.token = "";
        localStorage.removeItem("ns_token");
        sessionStorage.removeItem("ns_token");
      }
    },
    has(code: string) {
      return this.user?.is_superuser || (this.user?.permissions || []).includes(code);
    },
  },
});
