import type { App } from "vue";

const CJK_MOJIBAKE_MARKERS = /[鍀-龥][\u0080-\u9fff]*[€?]|[鎴鍦鏂鑷娴璇鐜鐘榛鏈鏆閫]|�|Ã|Â/;
const TEXT_ATTRIBUTES = ["title", "placeholder", "aria-label", "alt"];
const COMMON_REPAIRS: Array<[RegExp, string]> = [
  [/鍒锋柊/g, "刷新"],
  [/鏂板/g, "新增"],
  [/缂栬緫/g, "编辑"],
  [/鍒犻櫎/g, "删除"],
  [/淇濆瓨/g, "保存"],
  [/鍙栨秷/g, "取消"],
  [/鍏抽棴/g, "关闭"],
  [/鎵ц/g, "执行"],
  [/杩愯/g, "运行"],
  [/鐘舵€?/g, "状态"],
  [/鐜/g, "环境"],
  [/骞冲彴/g, "平台"],
  [/璇锋眰/g, "请求"],
  [/鍝嶅簲/g, "响应"],
  [/鏂规硶/g, "方法"],
  [/璺緞/g, "路径"],
  [/鐢ㄤ緥/g, "用例"],
  [/鎺ュ彛/g, "接口"],
  [/鍦烘櫙/g, "场景"],
  [/妯″潡/g, "模块"],
  [/鑳藉姏/g, "能力"],
  [/鍚嶇О/g, "名称"],
  [/鎼滅储/g, "搜索"],
  [/鏆傛棤/g, "暂无"],
  [/鏈€杩?/g, "最近"],
  [/鏈繍琛?/g, "未运行"],
  [/鎴愬姛/g, "成功"],
  [/澶辫触/g, "失败"],
  [/鏃犳硶/g, "无法"],
  [/杩斿洖/g, "返回"],
  [/棣栭〉/g, "首页"],
  [/椤甸潰/g, "页面"],
  [/鍔犺浇/g, "加载"],
  [/寮傚父/g, "异常"],
  [/閫夋嫨/g, "选择"],
  [/璇峰厛/g, "请先"],
  [/璇峰～鍐?/g, "请填写"],
  [/纭/g, "确认"],
  [/鎻愬彇/g, "提取"],
  [/鏁版嵁/g, "数据"],
  [/缁撴灉/g, "结果"],
  [/鑰楁椂/g, "耗时"],
  [/閿欒/g, "错误"],
  [/瀵煎嚭/g, "导出"],
  [/鍚敤/g, "启用"],
  [/鍋滅敤/g, "停用"],
];

const decoder = new TextDecoder("utf-8", { fatal: false });

const encodeWindows1252 = (value: string) => {
  const bytes: number[] = [];
  for (const char of value) {
    const code = char.codePointAt(0) || 0;
    if (code <= 0xff) bytes.push(code);
    else return null;
  }
  return new Uint8Array(bytes);
};

const encodeGbkMojibake = (value: string) => {
  const bytes: number[] = [];
  for (const char of value) {
    const encoded = gbkReverseMap.get(char);
    if (!encoded) return null;
    bytes.push(...encoded);
  }
  return new Uint8Array(bytes);
};

export const looksMojibake = (value: string) => CJK_MOJIBAKE_MARKERS.test(value);

export const repairMojibake = (value: string) => {
  if (!value || !looksMojibake(value)) return value;
  const repairedByDictionary = COMMON_REPAIRS.reduce((text, [pattern, replacement]) => text.replace(pattern, replacement), value);
  if (repairedByDictionary !== value && !looksMojibake(repairedByDictionary)) return repairedByDictionary;
  const encodedCandidates: Uint8Array[] = [];
  const gbkBytes = encodeGbkMojibake(value);
  const windows1252Bytes = encodeWindows1252(value);
  if (gbkBytes) encodedCandidates.push(gbkBytes);
  if (windows1252Bytes) encodedCandidates.push(windows1252Bytes);
  const candidates = encodedCandidates.map((bytes) => decoder.decode(bytes));
  return candidates.find((item) => item && !looksMojibake(item)) || repairedByDictionary;
};

const repairTextNode = (node: Text) => {
  const fixed = repairMojibake(node.data);
  if (fixed !== node.data) node.data = fixed;
};

const repairElement = (element: Element) => {
  for (const attr of TEXT_ATTRIBUTES) {
    const value = element.getAttribute(attr);
    if (!value) continue;
    const fixed = repairMojibake(value);
    if (fixed !== value) element.setAttribute(attr, fixed);
  }
};

const repairNode = (node: Node) => {
  if (node.nodeType === Node.TEXT_NODE) repairTextNode(node as Text);
  if (node.nodeType === Node.ELEMENT_NODE) repairElement(node as Element);
};

const repairTree = (root: ParentNode) => {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  repairNode(root as unknown as Node);
  while (walker.nextNode()) repairNode(walker.currentNode);
};

export const installMojibakeGuard = (app: App) => {
  app.config.globalProperties.$repairMojibake = repairMojibake;
  app.directive("mojibake", {
    mounted: (el) => repairTree(el),
    updated: (el) => repairTree(el),
  });
  app.mixin({
    mounted() {
      repairTree(this.$el as ParentNode);
    },
    updated() {
      repairTree(this.$el as ParentNode);
    },
  });
  if (typeof window !== "undefined") {
    window.requestAnimationFrame(() => repairTree(document.body));
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => {
          if (node instanceof Element || node instanceof Text) repairNode(node);
          if (node instanceof Element) repairTree(node);
        });
        if (mutation.type === "characterData") repairNode(mutation.target);
        if (mutation.type === "attributes" && mutation.target instanceof Element) repairElement(mutation.target);
      }
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: TEXT_ATTRIBUTES,
    });
  }
};

const gbkReverseMap = new Map<string, number[]>();
