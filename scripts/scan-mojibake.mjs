import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const roots = [
  "frontend/src",
  "backend/apps",
  "backend/config",
  "backend/.env",
  "backend/.env.example",
  "scripts",
  "README.md",
  "AGENTS.md",
];

const extensions = new Set([".vue", ".ts", ".py", ".css", ".mjs", ".md", ".env", ".example"]);
const ignoredDirectories = new Set(["node_modules", "dist", ".venv", "media", "perf_results", ".git", "__pycache__"]);
const ignorePatterns = [/utils[\\/]mojibake\.ts$/, /scripts[\\/]scan-mojibake\.mjs$/];
const sensitiveFilePattern = /(?:^|[\\/])\.env(?:\.|$)/;

const mojibakeMarkerPattern =
  /閸掗攱鏌妡閺傛澘|缂傛牞|閸掔娀|娣囨繂|閸欐牗|閸忔娊|閹笛唡鏉╂劘|閻樿埖|閻滎垰|楠炲啿|鐠囬攱|閸濆秴|閺傝|鐠侯垰|閻劋|閹恒儱|閸︾儤|濡€硘閼宠棄|閸氬秶|閹兼粎|閺嗗倹|閺堚偓|閹存劕|婢惰精|閺冪姵|鏉╂柨|妫ｆ牠|妞ょ敻|閸旂姾|瀵倸|闁|鐠囧嘲|绾喛|閹绘劕|閺佺増|缂佹挻|閼版|闁挎瑨|鐎电厧|閸氼垳|閸嬫粎|锟絴脙|脗|鍒锋柊|鏂板|缂栬|鍒犻|淇濆|鍙栨|鍏抽|鎵ц|杩愯|鐘舶|鐘舵|鐜|骞冲|璇锋|鍝嶅|鏂规|璺|鐢ㄤ|鎺ュ|鍦烘|妯″|鑳藉|鍚嶇|鎼滅|鏆傛|鏈€|鎴愬|澶辫|鏃犳|杩斿|棣栭|椤甸|鍔犺|寮傚|閫夋|璇峰|纭|鎻愬|鏁版|缁撴|鑰楁|閿欒|瀵煎|鍚|鍋滅|闁板秶|鐠佺偓|娴犲懘|脙|脗|Ã|Â|�/;

const questionPlaceholderPattern = /^\s*(?:#|\/\/|\/\*|\*|<!--).*\?{3,}/;

const walk = (target, files = []) => {
  const absoluteTarget = path.resolve(repoRoot, target);
  if (!fs.existsSync(absoluteTarget)) return files;
  const stat = fs.statSync(absoluteTarget);
  if (stat.isFile()) {
    files.push(absoluteTarget);
    return files;
  }

  for (const entry of fs.readdirSync(absoluteTarget, { withFileTypes: true })) {
    const fullPath = path.join(absoluteTarget, entry.name);
    if (entry.isDirectory()) {
      if (!ignoredDirectories.has(entry.name)) walk(fullPath, files);
      continue;
    }
    const ext = path.extname(entry.name) || entry.name;
    if (extensions.has(ext)) files.push(fullPath);
  }
  return files;
};

const findings = [];

for (const root of roots) {
  for (const file of walk(root)) {
    if (ignorePatterns.some((pattern) => pattern.test(file))) continue;
    const text = fs.readFileSync(file, "utf8");
    text.split(/\r?\n/).forEach((line, index) => {
      const hit = mojibakeMarkerPattern.test(line) || questionPlaceholderPattern.test(line);
      if (!hit) return;
      findings.push({
        file,
        line: index + 1,
        text: sensitiveFilePattern.test(file) ? "[masked env line]" : line.trim().slice(0, 180),
      });
    });
  }
}

if (findings.length) {
  console.error(`Mojibake scan found ${findings.length} suspicious line(s):`);
  for (const item of findings.slice(0, 120)) {
    console.error(`${item.file}:${item.line} ${item.text}`);
  }
  if (findings.length > 120) console.error(`... ${findings.length - 120} more line(s) omitted`);
  process.exit(1);
}

console.log("Mojibake scan passed.");
