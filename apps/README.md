# apps/

小工具集合。每个子目录是一个独立的 HTML+JS 应用，通过本地 HTTP 服务或 GitHub Pages 访问。

## 工具列表

- **`damage_calculator/`** — 伤害计算器：5 个模块（攻击方/防御方/技能/全局状态/结果），支持精灵名自动填入种族值、按显示威力或按技能名称两种模式、属性差技能（闪击/鸣沙陷阱）阶梯、隐藏乘区（顺风/破空/风起）、防御技能减伤、中毒/灼烧/冰冻 DoT 与冻结斩杀

---

## 本地调试

在项目根目录运行：

```bash
./apps/serve.sh          # 默认 8000 端口
./apps/serve.sh 8080     # 指定端口
```

然后在浏览器打开：`http://localhost:8000/apps/damage_calculator/`

脚本本质是 `python3 -m http.server`，无任何依赖。改了代码或 `data/raw/*.json` 后刷新浏览器即可生效。

**为什么不能直接双击打开 HTML？** 浏览器限制 `file://` 协议下的 `fetch()` 请求，无法读本地 JSON。

---

## GitHub Pages 部署

仓库 Settings → Pages → 选 `main` 分支 `/` 目录即可。访问路径：

```
https://<user>.github.io/<repo>/apps/damage_calculator/
```

部署后工具会通过相对路径 `../../data/raw/pokemon.json` 加载最新数据，无需重新打包。

---

## 设计原则

- **单文件**：每个工具一个 `index.html`，便于分发
- **零依赖**：不引用外部 CDN
- **数据共享**：所有工具通过 `fetch('../../data/raw/*.json')` 读取项目数据，一次维护多处复用
- **响应式**：移动端和桌面端都能用
