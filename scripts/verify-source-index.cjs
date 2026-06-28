const fs = require("node:fs");
const path = require("node:path");

const indexPath = path.join(__dirname, "..", "index.html");
const html = fs.readFileSync(indexPath, "utf8");

const forbiddenPatterns = [
  /(?:src|href)=["']\.\/assets\/index-[^"']+\.(?:js|css)["']/i,
  /crossorigin\s+src=["']\.\/assets\//i,
  /href=["']\.\/assets\//i,
];

const hasSourceEntry = html.includes('<script type="module" src="/src/main.tsx"></script>');
const hasRoot = html.includes('<div id="root"></div>');
const hasTitle = html.includes("<title>所依</title>");
const hasForbiddenDistAsset = forbiddenPatterns.some((pattern) => pattern.test(html));

if (!hasTitle || !hasRoot || !hasSourceEntry || hasForbiddenDistAsset) {
  console.error(
    [
      "源码 index.html 必须保持 Vite 入口形态，不能引用 dist/assets 构建产物。",
      '需要包含：<title>所依</title>、<div id="root"></div>、<script type="module" src="/src/main.tsx"></script>',
      "请检查是否误把 dist/index.html 或 app.asar 内的 dist/index.html 写回了项目根 index.html。",
    ].join("\n"),
  );
  process.exit(1);
}
