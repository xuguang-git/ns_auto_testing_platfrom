export interface ParsedCurl {
  method: string;
  url: string;
  path: string;
  headers: Array<{ enabled: boolean; key: string; value: string; description: string }>;
  query_params: Array<{ enabled: boolean; key: string; value: string; description: string }>;
  body: unknown;
  bodyText: string;
}

const stripQuotes = (value: string) => {
  const trimmed = value.trim();
  if ((trimmed.startsWith("'") && trimmed.endsWith("'")) || (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
};

const optionValue = (token: string, next?: string) => {
  const equalIndex = token.indexOf("=");
  if (equalIndex > -1) return stripQuotes(token.slice(equalIndex + 1));
  return next ? stripQuotes(next) : "";
};

const hasInlineValue = (token: string) => token.includes("=");

const addHeader = (headers: ParsedCurl["headers"], rawHeader: string) => {
  const header = stripQuotes(rawHeader);
  const index = header.indexOf(":");
  if (index > -1) {
    headers.push({ enabled: true, key: header.slice(0, index).trim(), value: header.slice(index + 1).trim(), description: "" });
  }
};

export const parseCurl = (input: string): ParsedCurl => {
  const tokens = tokenize(input.replace(/\\\r?\n/g, " "));
  if (!tokens.length || tokens[0].toLowerCase() !== "curl") throw new Error("请输入有效的 curl 命令");

  let method = "";
  let url = "";
  const headers: ParsedCurl["headers"] = [];
  let bodyText = "";

  for (let i = 1; i < tokens.length; i += 1) {
    const token = tokens[i];
    const next = tokens[i + 1];
    if (!token.startsWith("-") && !url) {
      url = stripQuotes(token);
      continue;
    }
    if ((token === "-X" || token === "--request" || token.startsWith("--request=")) && (next || hasInlineValue(token))) {
      method = optionValue(token, next).toUpperCase();
      if (!hasInlineValue(token)) i += 1;
      continue;
    }
    if ((token === "-H" || token === "--header" || token.startsWith("--header=")) && (next || hasInlineValue(token))) {
      addHeader(headers, optionValue(token, next));
      if (!hasInlineValue(token)) i += 1;
      continue;
    }
    if ((token === "-b" || token === "--cookie" || token.startsWith("--cookie=")) && (next || hasInlineValue(token))) {
      const cookie = optionValue(token, next);
      if (cookie) headers.push({ enabled: true, key: "Cookie", value: cookie, description: "" });
      if (!hasInlineValue(token)) i += 1;
      continue;
    }
    if ((["-d", "--data", "--data-raw", "--data-binary", "--data-urlencode"].includes(token) || /^--data(?:-raw|-binary|-urlencode)?=/.test(token)) && (next || hasInlineValue(token))) {
      bodyText = optionValue(token, next);
      if (!method) method = "POST";
      if (!hasInlineValue(token)) i += 1;
    }
  }

  if (!url) throw new Error("curl 中未找到 URL");
  const parsedUrl = new URL(url);
  const query_params = Array.from(parsedUrl.searchParams.entries()).map(([key, value]) => ({ enabled: true, key, value, description: "" }));
  const path = `${parsedUrl.pathname}${parsedUrl.search || ""}`;
  let body: unknown = {};
  if (bodyText) {
    try {
      body = JSON.parse(bodyText);
    } catch {
      body = bodyText;
    }
  }

  return {
    method: method || "GET",
    url,
    path,
    headers,
    query_params,
    body,
    bodyText: bodyText || "{}",
  };
};

const tokenize = (input: string) => {
  const tokens: string[] = [];
  let current = "";
  let quote = "";
  let escaped = false;
  for (const char of input.trim()) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }
    if (char === "\\") {
      escaped = true;
      continue;
    }
    if (quote) {
      if (char === quote) quote = "";
      else current += char;
      continue;
    }
    if (char === "'" || char === '"') {
      quote = char;
      continue;
    }
    if (/\s/.test(char)) {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }
    current += char;
  }
  if (current) tokens.push(current);
  return tokens;
};
