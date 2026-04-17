#!/usr/bin/env python3
"""
LogPulse RSS Fetcher
全球物流政策情报 RSS 抓取脚本
自动抓取 IMO / WTO / 中国海关 / 美欧贸易 / 主要港口 政策新闻
"""

import json
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# --- 依赖检查 ---
try:
    import feedparser
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "feedparser"])
    import feedparser

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ===================== RSS 源配置 =====================
RSS_SOURCES = [
    # --- 国际组织 ---
    {
        "id": "imo",
        "name": "IMO 国际海事组织",
        "url": "https://www.imo.org/en/MediaCentre/Pages/WhatsNew-rss.aspx",
        "category": "imo",
        "region": "global",
        "icon": "🌐",
        "src_class": "src-imo",
        "cat_class": "cat-imo-bg",
    },
    {
        "id": "wto",
        "name": "WTO 世界贸易组织",
        "url": "https://www.wto.org/english/news_e/news_e.rss",
        "category": "imo",
        "region": "global",
        "icon": "🌐",
        "src_class": "src-imo",
        "cat_class": "cat-imo-bg",
    },
    # --- 中国政策 ---
    {
        "id": "china_customs",
        "name": "中国海关总署",
        "url": "http://www.customs.gov.cn/customs/xwfb/index_rss.xml",
        "category": "china",
        "region": "asia",
        "icon": "🇨🇳",
        "src_class": "src-china",
        "cat_class": "cat-china-bg",
    },
    {
        "id": "mofcom",
        "name": "中国商务部",
        "url": "http://www.mofcom.gov.cn/article/zt_jjsb/rss.xml",
        "category": "china",
        "region": "asia",
        "icon": "🇨🇳",
        "src_class": "src-china",
        "cat_class": "cat-china-bg",
    },
    # --- 美欧贸易 ---
    {
        "id": "ustr",
        "name": "美国贸易代表署",
        "url": "https://ustr.gov/rss.xml",
        "category": "us",
        "region": "america",
        "icon": "🇺🇸",
        "src_class": "src-us",
        "cat_class": "cat-us-bg",
    },
    {
        "id": "eu_trade",
        "name": "EU 欧盟贸易委员会",
        "url": "https://ec.europa.eu/trade/policy/in-focus/rss.xml",
        "category": "us",
        "region": "europe",
        "icon": "🇪🇺",
        "src_class": "src-us",
        "cat_class": "cat-us-bg",
    },
    # --- 主要港口 ---
    {
        "id": "port_singapore",
        "name": "新加坡港务局",
        "url": "https://www.mpa.gov.sg/rss/newsroom",
        "category": "port",
        "region": "asia",
        "icon": "🚢",
        "src_class": "src-port",
        "cat_class": "cat-port-bg",
    },
    {
        "id": "port_rotterdam",
        "name": "鹿特丹港务局",
        "url": "https://www.portofrotterdam.com/en/news-and-press-releases/rss",
        "category": "port",
        "region": "europe",
        "icon": "🚢",
        "src_class": "src-port",
        "cat_class": "cat-port-bg",
    },
    {
        "id": "port_la",
        "name": "洛杉矶港",
        "url": "https://www.portoflosangeles.org/newsroom/rss",
        "category": "port",
        "region": "america",
        "icon": "🚢",
        "src_class": "src-port",
        "cat_class": "cat-port-bg",
    },
    # --- 行业媒体 ---
    {
        "id": "lloyds",
        "name": "Lloyd's List",
        "url": "https://lloydslist.com/rss",
        "category": "port",
        "region": "global",
        "icon": "📰",
        "src_class": "src-port",
        "cat_class": "cat-port-bg",
    },
    {
        "id": "splash247",
        "name": "Splash247 航运新闻",
        "url": "https://splash247.com/feed/",
        "category": "imo",
        "region": "global",
        "icon": "📰",
        "src_class": "src-imo",
        "cat_class": "cat-imo-bg",
    },
    {
        "id": "freightwaves",
        "name": "FreightWaves",
        "url": "https://www.freightwaves.com/news/feed",
        "category": "us",
        "region": "america",
        "icon": "📊",
        "src_class": "src-us",
        "cat_class": "cat-us-bg",
    },
]

# 物流/航运关键词过滤（提高精准度）
KEYWORDS = [
    "shipping", "logistics", "port", "customs", "tariff", "trade",
    "maritime", "freight", "container", "vessel", "cargo", "supply chain",
    "航运", "物流", "港口", "海关", "关税", "贸易", "集装箱", "供应链",
    "IMO", "WTO", "RCEP", "sanctions", "制裁", "emission", "排放",
    "policy", "regulation", "政策", "法规"
]

PRIORITY_KEYWORDS = {
    "high": ["sanction", "制裁", "tariff war", "关税战", "ban", "禁令",
             "emergency", "紧急", "critical", "重大"],
    "medium": ["policy", "政策", "regulation", "法规", "update", "更新",
               "new rule", "新规", "agreement", "协议"],
}


def clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text or '').strip()


def assess_priority(title: str, summary: str) -> str:
    """Assess news priority based on keywords."""
    content = (title + " " + summary).lower()
    for kw in PRIORITY_KEYWORDS["high"]:
        if kw.lower() in content:
            return "high"
    for kw in PRIORITY_KEYWORDS["medium"]:
        if kw.lower() in content:
            return "medium"
    return "low"


def is_relevant(title: str, summary: str) -> bool:
    """Check if the article is relevant to logistics/shipping."""
    content = (title + " " + summary).lower()
    return any(kw.lower() in content for kw in KEYWORDS)


def format_time(entry) -> str:
    """Format RSS entry published time."""
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - dt
            hours = int(delta.total_seconds() // 3600)
            if hours < 1:
                return "刚刚"
            elif hours < 24:
                return f"{hours}小时前"
            else:
                return f"{delta.days}天前"
    except Exception:
        pass
    return "近期"


def fetch_source(source: dict) -> list:
    """Fetch and parse a single RSS source."""
    items = []
    try:
        print(f"  → 抓取: {source['name']} ...")
        feed = feedparser.parse(
            source["url"],
            request_headers={"User-Agent": "LogPulse/1.0 RSS Reader"},
        )
        for entry in feed.entries[:10]:  # Max 10 per source
            title = clean_html(getattr(entry, 'title', ''))
            summary = clean_html(getattr(entry, 'summary', getattr(entry, 'description', '')))
            link = getattr(entry, 'link', '#')

            if not title:
                continue
            if not is_relevant(title, summary):
                continue

            item_id = hashlib.md5((source["id"] + title).encode()).hexdigest()[:12]
            items.append({
                "id": item_id,
                "category": source["category"],
                "priority": assess_priority(title, summary),
                "source": source["name"],
                "title": title,
                "summary": summary[:200] if summary else title,
                "link": link,
                "time": format_time(entry),
                "region": source["region"],
                "icon": source["icon"],
                "srcClass": source["src_class"],
                "catClass": source["cat_class"],
                "tags": extract_tags(title, summary),
            })

        print(f"     ✓ 获取 {len(items)} 条相关动态")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
    return items


def extract_tags(title: str, summary: str) -> list:
    """Extract relevant tags from content."""
    content = title + " " + summary
    tag_map = {
        "港口": "港口", "port": "港口",
        "关税": "关税", "tariff": "关税",
        "排放": "减排", "emission": "减排", "carbon": "碳减排",
        "制裁": "制裁", "sanction": "制裁",
        "自动化": "自动化", "automation": "自动化",
        "供应链": "供应链", "supply chain": "供应链",
        "集装箱": "集装箱", "container": "集装箱",
        "LNG": "LNG", "绿色": "绿色航运", "green": "绿色航运",
        "RCEP": "RCEP", "WTO": "WTO", "IMO": "IMO",
    }
    tags = []
    for kw, label in tag_map.items():
        if kw.lower() in content.lower() and label not in tags:
            tags.append(label)
        if len(tags) >= 3:
            break
    return tags if tags else ["物流政策"]


def generate_stats(items: list) -> dict:
    """Generate summary statistics."""
    return {
        "total": len(items),
        "high_risk": len([i for i in items if i["priority"] == "high"]),
        "by_category": {
            "port": len([i for i in items if i["category"] == "port"]),
            "imo": len([i for i in items if i["category"] == "imo"]),
            "china": len([i for i in items if i["category"] == "china"]),
            "us": len([i for i in items if i["category"] == "us"]),
        },
        "by_region": {
            "asia": len([i for i in items if i["region"] == "asia"]),
            "europe": len([i for i in items if i["region"] == "europe"]),
            "america": len([i for i in items if i["region"] == "america"]),
            "global": len([i for i in items if i["region"] == "global"]),
        },
        "sources_count": len(RSS_SOURCES),
    }


def main():
    print("=" * 50)
    print("🚢 LogPulse RSS 抓取器启动")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   信息源: {len(RSS_SOURCES)} 个")
    print("=" * 50)

    all_items = []
    for source in RSS_SOURCES:
        items = fetch_source(source)
        all_items.extend(items)

    # Deduplicate by id
    seen = set()
    unique_items = []
    for item in all_items:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique_items.append(item)

    # Sort: high priority first, then by time
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique_items.sort(key=lambda x: priority_order.get(x["priority"], 2))

    # Limit to 50 most relevant
    unique_items = unique_items[:50]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": generate_stats(unique_items),
        "items": unique_items,
    }

    # Write output
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "news.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"✅ 完成！共抓取 {len(unique_items)} 条相关动态")
    print(f"   高风险: {output['stats']['high_risk']} 条")
    print(f"   输出: {out_file}")
    print("=" * 50)


if __name__ == "__main__":
    main()
