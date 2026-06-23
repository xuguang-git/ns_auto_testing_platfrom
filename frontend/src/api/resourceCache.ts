interface ResourceCacheEntry<T> {
  expiresAt: number;
  value: T;
}

const DEFAULT_TTL = 5 * 60 * 1000;
const resourceCache = new Map<string, ResourceCacheEntry<unknown>>();
const pendingRequests = new Map<string, Promise<unknown>>();

const cloneValue = <T>(value: T): T => {
  if (typeof structuredClone === "function") return structuredClone(value);
  return value === undefined ? value : JSON.parse(JSON.stringify(value));
};

export const getOrLoadResource = async <T>(key: string, loader: () => Promise<T>, ttl = DEFAULT_TTL, force = false): Promise<T> => {
  const now = Date.now();
  const cached = resourceCache.get(key) as ResourceCacheEntry<T> | undefined;
  if (!force && cached && cached.expiresAt > now) return cloneValue(cached.value);

  const pending = pendingRequests.get(key) as Promise<T> | undefined;
  if (!force && pending) return cloneValue(await pending);

  const request = loader().then((value) => {
    resourceCache.set(key, { value: cloneValue(value), expiresAt: Date.now() + ttl });
    return value;
  }).finally(() => pendingRequests.delete(key));
  pendingRequests.set(key, request);
  return cloneValue(await request);
};

export const invalidateResource = (key?: string) => {
  if (!key) {
    resourceCache.clear();
    pendingRequests.clear();
    return;
  }
  for (const item of resourceCache.keys()) {
    if (item === key || item.startsWith(`${key}:`)) resourceCache.delete(item);
  }
  for (const item of pendingRequests.keys()) {
    if (item === key || item.startsWith(`${key}:`)) pendingRequests.delete(item);
  }
};
