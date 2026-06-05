export interface ExtractResult {
  ok: boolean;
  value: unknown;
  message: string;
}

type Token = string | number | "*";

export const extractJsonPath = (input: unknown, expression: string): ExtractResult => {
  const path = expression.trim();
  if (!path) return { ok: false, value: undefined, message: "提取路径不能为空" };
  if (path === "$") return { ok: true, value: input, message: "OK" };
  if (!path.startsWith("$.")) return { ok: false, value: undefined, message: "路径需要以 $. 开头" };

  const tokens = tokenizePath(path);
  if (!tokens.length) return { ok: false, value: undefined, message: "路径格式不正确" };

  const values = walk([input], tokens);
  if (!values.length) return { ok: false, value: undefined, message: "未匹配到数据" };
  return { ok: true, value: values.length === 1 ? values[0] : values, message: `匹配 ${values.length} 项` };
};

export const formatExtractValue = (value: unknown) => {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
};

const tokenizePath = (path: string): Token[] => {
  const content = path.slice(2);
  const tokens: Token[] = [];
  let current = "";

  for (let index = 0; index < content.length; index += 1) {
    const char = content[index];
    if (char === ".") {
      pushKey(tokens, current);
      current = "";
      continue;
    }
    if (char === "[") {
      pushKey(tokens, current);
      current = "";
      const closeIndex = content.indexOf("]", index);
      if (closeIndex === -1) return [];
      const rawIndex = content.slice(index + 1, closeIndex).trim();
      if (rawIndex === "*") tokens.push("*");
      else if (/^\d+$/.test(rawIndex)) tokens.push(Number(rawIndex));
      else return [];
      index = closeIndex;
      continue;
    }
    current += char;
  }
  pushKey(tokens, current);
  return tokens;
};

const pushKey = (tokens: Token[], key: string) => {
  const trimmed = key.trim();
  if (trimmed) tokens.push(trimmed);
};

const walk = (values: unknown[], tokens: Token[]) => {
  let current = values;
  for (const token of tokens) {
    const next: unknown[] = [];
    for (const value of current) {
      if (token === "*") {
        if (Array.isArray(value)) next.push(...value);
        continue;
      }
      if (typeof token === "number") {
        if (Array.isArray(value) && token < value.length) next.push(value[token]);
        continue;
      }
      if (value && typeof value === "object" && token in (value as Record<string, unknown>)) {
        next.push((value as Record<string, unknown>)[token]);
      }
    }
    current = next;
    if (!current.length) break;
  }
  return current;
};

