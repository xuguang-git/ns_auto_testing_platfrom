import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const roots = ["frontend/src", "backend/apps", "backend/config"];
const extensions = new Set([".vue", ".ts", ".py"]);
const markerPattern = /鍒锋柊|鏂板|缂栬|鍒犻|淇濆|鍙栨|鍏抽|鎵ц|杩愯|鐘舵|鐜|骞冲|璇锋|鍝嶅|鏂规|璺|鐢ㄤ|鎺ュ|鍦烘|妯″|鑳藉|鍚嶇|鎼滅|鏆傛|鏈€|鎴愬|澶辫|鏃犳|杩斿|棣栭|椤甸|鍔犺|寮傚|閫夋|璇峰|纭|鎻愬|鏁版|缁撴|鑰楁|閿欒|瀵煎|鍚|鍋滅|�|Ã|Â/;
const ignorePatterns = [/utils[\\/]mojibake\.ts$/];

const walk = (directory, files = []) => {
  directory = path.resolve(repoRoot, directory);
  if (!fs.existsSync(directory)) return files;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(fullPath, files);
    else if (extensions.has(path.extname(entry.name))) files.push(fullPath);
  }
  return files;
};

const findings = [];

for (const root of roots) {
  for (const file of walk(root)) {
    if (ignorePatterns.some((pattern) => pattern.test(file))) continue;
    const text = fs.readFileSync(file, "utf8");
    text.split(/\r?\n/).forEach((line, index) => {
      if (!markerPattern.test(line)) return;
      findings.push({ file, line: index + 1, text: line.trim().slice(0, 180) });
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
