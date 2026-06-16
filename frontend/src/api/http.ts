import axios, { AxiosRequestConfig, AxiosResponse } from "axios";
import { ElMessage } from "element-plus";
import router from "@/router";

declare module "axios" {
  export interface AxiosRequestConfig {
    cache?: boolean | number;
    cacheKey?: string;
    toast?: boolean;
  }
}

interface CacheEntry {
  expiresAt: number;
  response: AxiosResponse;
}

const DEFAULT_GET_CACHE_TTL = 60_000;
const cacheStore = new Map<string, CacheEntry>();
const pendingStore = new Map<string, Promise<AxiosResponse>>();
let forceRefreshDepth = 0;
let userRefreshUntil = 0;
const cacheDebugEnabled = () => localStorage.getItem("ns_http_cache_debug") === "1";
let lastErrorToast = { text: "", time: 0 };
const SUCCESS_CODE = 0;
const BUSINESS_WARNING_CODES = new Set([40000, 42200, 42900]);

export const http = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  withCredentials: true,
});

const stableStringify = (value: unknown): string => {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  return `{${Object.entries(value as Record<string, unknown>)
    .filter(([, item]) => item !== undefined)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
    .join(",")}}`;
};

const isCacheableGet = (config: AxiosRequestConfig) => {
  if (config.cache === false) return false;
  const method = (config.method || "get").toLowerCase();
  if (method !== "get") return false;
  if (config.responseType && config.responseType !== "json") return false;
  return true;
};

const cacheTtl = (config: AxiosRequestConfig) => (typeof config.cache === "number" ? config.cache : DEFAULT_GET_CACHE_TTL);

const buildCacheKey = (config: AxiosRequestConfig) => {
  if (config.cacheKey) return config.cacheKey;
  const method = (config.method || "get").toUpperCase();
  const url = `${config.baseURL || ""}${config.url || ""}`;
  return `${method} ${url}?${stableStringify(config.params || {})}`;
};

const cloneResponse = (response: AxiosResponse): AxiosResponse => ({
  ...response,
  data: typeof structuredClone === "function" ? structuredClone(response.data) : response.data === undefined ? undefined : JSON.parse(JSON.stringify(response.data)),
});

const resourcePrefix = (url = "") => {
  const cleanUrl = url.replace(/^\/+/, "");
  const match = cleanUrl.match(/^([^/?]+)\//);
  return match ? `GET ${http.defaults.baseURL}/${match[1]}/` : "";
};

export const clearHttpCache = (prefix?: string) => {
  for (const key of cacheStore.keys()) {
    if (!prefix || key.startsWith(prefix)) cacheStore.delete(key);
  }
  for (const key of pendingStore.keys()) {
    if (!prefix || key.startsWith(prefix)) pendingStore.delete(key);
  }
};

export const cachedGet = <T = unknown>(url: string, config: AxiosRequestConfig = {}) =>
  http.get<T>(url, { ...config, cache: config.cache ?? DEFAULT_GET_CACHE_TTL });

export const forceRefresh = async <T>(callback: () => T | Promise<T>) => {
  forceRefreshDepth += 1;
  try {
    return await callback();
  } finally {
    forceRefreshDepth -= 1;
  }
};

if (typeof window !== "undefined") {
  const markUserRefreshIntent = () => {
    userRefreshUntil = Date.now() + 1200;
  };
  window.addEventListener(
    "click",
    (event) => {
      const target = event.target as HTMLElement | null;
      const button = target?.closest?.("button");
      if (button) markUserRefreshIntent();
    },
    true,
  );
  window.addEventListener("change", markUserRefreshIntent, true);
}

let refreshPromise: Promise<AxiosResponse> | null = null;

http.interceptors.request.use((config) => config);

http.interceptors.response.use(
  (response) => {
    const envelope = normalizeEnvelope(response.data);
    if (!envelope) return response;
    if (envelope.code === SUCCESS_CODE) {
      response.data = envelope.data;
      return response;
    }
    const error = new Error(envelope.message || "请求处理失败，请检查后重试。");
    Object.assign(error, { response, config: response.config, businessCode: envelope.code });
    if (response.config?.toast !== false) showBusinessToast(envelope.code, envelope.message);
    return Promise.reject(error);
  },
  async (error) => {
    const message = extractErrorMessage(error);
    if (message) error.message = message;
    const originalConfig = error?.config || {};
    if (
      error?.response?.status === 401 &&
      !originalConfig.__isRetryRequest &&
      !String(originalConfig.url || "").includes("/auth/login") &&
      !String(originalConfig.url || "").includes("/auth/refresh")
    ) {
      try {
        originalConfig.__isRetryRequest = true;
        refreshPromise = refreshPromise || rawPost("/auth/refresh/", {}, { toast: false, cache: false });
        await refreshPromise;
        refreshPromise = null;
        return http(originalConfig);
      } catch {
        refreshPromise = null;
      }
    }
    if (!axios.isCancel(error) && error?.config?.toast !== false) {
      showBusinessToast(error?.response?.data?.code, message);
    }
    if (error?.response?.status === 401 && router.currentRoute.value.path !== "/login") {
      router.push({ path: "/login", query: { redirect: router.currentRoute.value.fullPath } });
    }
    return Promise.reject(error);
  },
);

const normalizeEnvelope = (data: unknown): { code: number; message: string; data: unknown; errors?: unknown } | null => {
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  const value = data as Record<string, unknown>;
  if (typeof value.code !== "number" || !("message" in value) || !("data" in value)) return null;
  return {
    code: value.code,
    message: typeof value.message === "string" ? value.message : String(value.message || ""),
    data: value.data,
    errors: value.errors,
  };
};

const extractErrorMessage = (error: any) => {
  const data = error?.response?.data;
  const envelope = normalizeEnvelope(data);
  if (envelope?.message) return envelope.message;
  if (typeof data === "string") return data;
  if (data?.message) return data.message;
  if (data?.detail) return data.detail;
  if (data?.non_field_errors?.[0]) return data.non_field_errors[0];
  if (data?.errors) {
    const first = firstErrorText(data.errors);
    if (first) return first;
  }
  if (error?.code === "ECONNABORTED") return "请求超时，请稍后重试。";
  if (error?.message === "Network Error") return "网络异常或服务不可用，请检查服务状态。";
  return error?.message || "请求失败，请稍后重试。";
};

const firstErrorText = (value: unknown): string => {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(firstErrorText).find(Boolean) || "";
  if (typeof value === "object") {
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      const text = firstErrorText(item);
      if (text) return ["detail", "message", "non_field_errors"].includes(key) ? text : `${key}: ${text}`;
    }
  }
  return "";
};

const showBusinessToast = (code: unknown, message: string) => {
  const text = message || "请求失败，请稍后重试。";
  const now = Date.now();
  if (lastErrorToast.text === text && now - lastErrorToast.time < 1500) return;
  lastErrorToast = { text, time: now };
  const numericCode = Number(code);
  if (BUSINESS_WARNING_CODES.has(numericCode)) ElMessage.warning(text);
  else ElMessage.error(text);
};

const rawGet = http.get.bind(http);
const rawPost = http.post.bind(http);
const rawPut = http.put.bind(http);
const rawPatch = http.patch.bind(http);
const rawDelete = http.delete.bind(http);

http.get = function getWithCache<T = unknown, R = AxiosResponse<T>, D = unknown>(url: string, config?: AxiosRequestConfig<D>): Promise<R> {
  const requestConfig = { ...(config || {}), method: "get", url, baseURL: config?.baseURL || http.defaults.baseURL };
  if (forceRefreshDepth > 0 || Date.now() < userRefreshUntil) requestConfig.cache = false;
  if (!isCacheableGet(requestConfig)) return rawGet<T, R, D>(url, config);
  const key = buildCacheKey({ ...requestConfig, baseURL: requestConfig.baseURL || http.defaults.baseURL });
  const now = Date.now();
  const cached = cacheStore.get(key);
  if (cached && cached.expiresAt > now) {
    if (cacheDebugEnabled()) console.info("[http-cache] hit", key);
    return Promise.resolve(cloneResponse(cached.response) as R);
  }

  const pending = pendingStore.get(key);
  if (pending) {
    if (cacheDebugEnabled()) console.info("[http-cache] reuse pending", key);
    return pending.then((response) => cloneResponse(response) as R);
  }

  const request = rawGet<T, AxiosResponse<T>, D>(url, config)
    .then((response) => {
      if (cacheDebugEnabled()) console.info("[http-cache] store", key);
      cacheStore.set(key, { expiresAt: Date.now() + cacheTtl(requestConfig), response: cloneResponse(response) });
      return response;
    })
    .finally(() => pendingStore.delete(key));
  pendingStore.set(key, request);
  return request.then((response) => response as R);
};

const invalidateAfter = <R>(url: string, request: Promise<R>) =>
  request.then((response) => {
    clearHttpCache(resourcePrefix(url));
    return response;
  });

http.post = function postAndInvalidate<T = unknown, R = AxiosResponse<T>, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig<D>): Promise<R> {
  return invalidateAfter(url, rawPost<T, R, D>(url, data, config));
};

http.put = function putAndInvalidate<T = unknown, R = AxiosResponse<T>, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig<D>): Promise<R> {
  return invalidateAfter(url, rawPut<T, R, D>(url, data, config));
};

http.patch = function patchAndInvalidate<T = unknown, R = AxiosResponse<T>, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig<D>): Promise<R> {
  return invalidateAfter(url, rawPatch<T, R, D>(url, data, config));
};

http.delete = function deleteAndInvalidate<T = unknown, R = AxiosResponse<T>, D = unknown>(url: string, config?: AxiosRequestConfig<D>): Promise<R> {
  return invalidateAfter(url, rawDelete<T, R, D>(url, config));
};
