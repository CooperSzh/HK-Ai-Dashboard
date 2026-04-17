# HK-Ai-Dashboard
HK-Ai-Dashboard# 🚢 LogPulse — 全球物流政策情报看板

> 自动抓取全球物流、航运、贸易政策动态，每日更新，部署到 GitHub Pages

[![Daily Fetch](https://github.com/YOUR_USERNAME/logpulse/actions/workflows/daily_fetch.yml/badge.svg)](https://github.com/YOUR_USERNAME/logpulse/actions/workflows/daily_fetch.yml)
![License](https://img.shields.io/badge/license-MIT-blue)

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🔍 RSS 自动抓取 | 每天 09:00（北京时间）抓取 12 个全球物流信息源 |
| 📊 可视化看板 | 实时展示政策动态、风险预警、地区分布、趋势图表 |
| 🔔 风险分级 | 高/中/低三级风险自动标注 |
| 🌏 多源覆盖 | IMO、WTO、中国海关、美国贸易代表署、主要港口 |
| 📱 响应式设计 | 支持桌面和移动端浏览 |
| 🤖 全自动部署 | GitHub Actions 每日运行，无需人工干预 |

## 📡 数据来源

### 国际组织
- 🌐 **IMO** 国际海事组织
- 🌐 **WTO** 世界贸易组织

### 中国政策
- 🇨🇳 中国海关总署
- 🇨🇳 中国商务部

### 美欧贸易
- 🇺🇸 美国贸易代表署 (USTR)
- 🇪🇺 欧盟贸易委员会

### 主要港口
- 🚢 新加坡港务局
- 🚢 鹿特丹港务局
- 🚢 洛杉矶港

### 行业媒体
- 📰 Lloyd's List
- 📰 Splash247 航运新闻
- 📊 FreightWaves

## 🚀 快速部署

### 1. Fork 本仓库

点击右上角 **Fork** 按钮

### 2. 开启 GitHub Pages

进入仓库 **Settings → Pages**：
- Source: `gh-pages` 分支
- 保存后获得访问地址：`https://YOUR_USERNAME.github.io/logpulse/`

### 3. 开启 GitHub Actions

进入 **Actions** 标签页，点击 **"I understand my workflows, go ahead and enable them"**

### 4. 手动触发首次抓取（可选）

进入 **Actions → 🚢 LogPulse** → **Run workflow**

完成！之后每天北京时间 09:00 自动更新。

## 📁 项目结构

```
logpulse/
├── index.html              # 主看板页面
├── data/
│   └── news.json           # 自动生成的新闻数据
├── scripts/
│   └── fetch_rss.py        # RSS 抓取脚本
├── .github/
│   └── workflows/
│       └── daily_fetch.yml # GitHub Actions 配置
└── README.md
```

## 🛠 本地运行

```bash
# 安装依赖
pip install feedparser requests

# 运行抓取脚本
python scripts/fetch_rss.py

# 用浏览器打开看板
open index.html
```

## ⚙️ 自定义配置

在 `scripts/fetch_rss.py` 中可以：
- 添加新的 RSS 源（`RSS_SOURCES` 列表）
- 修改关键词过滤（`KEYWORDS`）
- 调整风险评估规则（`PRIORITY_KEYWORDS`）

在 `.github/workflows/daily_fetch.yml` 中可以：
- 修改运行时间（`cron` 表达式）
- 添加通知配置（Email、Slack 等）

## 📄 License

MIT License — 自由使用和修改
