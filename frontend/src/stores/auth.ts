import { defineStore } from "pinia";

import { accountApi } from "@/api/account";
import { clearHttpCache } from "@/api/http";
import { encryptPassword } from "@/utils/loginCrypto";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as any,
    checked: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user),
    permissions: (state) => new Set<string>(state.user?.permissions || []),
  },
  actions: {
    async login(payload: { username: string; password: string; remember_me: boolean }) {
      clearHttpCache();
      localStorage.removeItem("ns_token");
      sessionStorage.removeItem("ns_token");
      const { data: cryptoConfig } = await accountApi.loginCrypto();
      let loginPayload: Record<string, unknown>;
      try {
        const passwordCipher = await encryptPassword(cryptoConfig.public_key, payload.password);
        loginPayload = {
          username: payload.username,
          password_cipher: passwordCipher,
          key_id: cryptoConfig.key_id,
          nonce: cryptoConfig.nonce,
          remember_me: payload.remember_me,
        };
      } catch (error) {
        if (!canFallbackToPlainPassword()) throw error;
        loginPayload = {
          username: payload.username,
          password: payload.password,
          remember_me: payload.remember_me,
        };
      }
      const { data } = await accountApi.login(loginPayload);
      this.user = data.user;
      this.checked = true;
      return data;
    },
    async loadMe() {
      try {
        const { data } = await accountApi.me();
        this.user = data;
        return data;
      } finally {
        this.checked = true;
      }
    },
    async logout() {
      try {
        await accountApi.logout();
      } finally {
        this.clearSession();
      }
    },
    clearSession() {
      clearHttpCache();
      localStorage.removeItem("ns_token");
      sessionStorage.removeItem("ns_token");
      this.user = null;
      this.checked = true;
    },
    has(code: string) {
      return this.user?.is_superuser || (this.user?.permissions || []).includes(code);
    },
  },
});

const isLocalDebugHttp = () => {
  const host = window.location.hostname;
  return window.location.protocol === "http:" && (
    host === "localhost" ||
    host === "127.0.0.1" ||
    host.startsWith("192.168.") ||
    host.startsWith("10.") ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(host)
  );
};

const canFallbackToPlainPassword = () => isLocalDebugHttp();
