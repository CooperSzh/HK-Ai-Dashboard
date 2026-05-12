#!/usr/bin/env python3
"""
LogPulse 情报抓取脚本
- 精准抓取 Google News RSS（物流/海关主题）
- 抓取香港海关与中国海关公告页面
- 可维护式站点配置，便于后续扩展
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

try:
    import feedparser
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "feedparser"])
    import feedparser

try:
    import requests
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

# Google News 关键词（可维护）
GOOGLE_NEWS_QUERIES = [
    "Hong Kong logistics customs",
    "港口 物流 海关",
    "shipping tariff trade policy",
    "中國 海關 公告",
]

SOURCE_CONFIG = [
    {
        "id": "hk-customs-press",
        "name": "香港海關 新聞公報",
        "type": "html",
        "url": "https://www.customs.gov.hk/tc/customs-announcement/press-release/index.html",
        "category": "hongkong",
        "region": "hongkong",
        "icon": "🇭🇰",
        "src_class": "src-hk",
        "cat_class": "cat-hk-bg",
        "item_pattern": r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    },
    {
        "id": "hk-customs-whatsnew",
        "name": "香港海關 最新消息",
        "type": "html",
        "url": "https://www.customs.gov.hk/tc/customs-announcement/whats-new/index.html",
        "category": "hongkong",
        "region": "hongkong",
        "icon": "🇭🇰",
        "src_class": "src-hk",
        "cat_class": "cat-hk-bg",
        "item_pattern": r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    },
    {
        "id": "cn-customs-news",
        "name": "中國海關 總署新聞",
        "type": "html",
        "url": "http://www.customs.gov.cn/customs/xwfb34/index.html",
        "category": "china",
        "region": "china",
        "icon": "🇨🇳",
        "src_class": "src-china",
        "cat_class": "cat-china-bg",
        "item_pattern": r'<a[^>]+href="([^"]+)"[^>]*title="([^"]+)"',
    },
]

KEYWORDS = [
    "shipping", "logistics", "port", "customs", "tariff", "trade",
    "maritime", "freight", "container", "cargo", "supply chain",
    "航运", "物流", "港口", "海关", "關稅", "贸易", "海關", "供應鏈",
]

_TRANSLATION_CACHE = {}
_ZH_TW_TRANSLATOR = GoogleTranslator(source="auto", target="zh-TW") if GoogleTranslator else None


def clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def to_absolute_url(base_url: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base_url)
        return (m.group(1) if m else "") + href
    return base_url.rsplit("/", 1)[0] + "/" + href


def translate_to_zh_tw(text: str) -> str:
    if not text or _ZH_TW_TRANSLATOR is None:
        return text
    if text in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[text]
    try:
        translated = _ZH_TW_TRANSLATOR.translate(text)
        result = translated.strip() if translated else text
    except Exception:
        result = text
    _TRANSLATION_CACHE[text] = result
    return result


def is_relevant(title: str, summary: str) -> bool:
    content = (title + " " + summary).lower()
    return any(kw.lower() in content for kw in KEYWORDS)


def assess_priority(title: str, summary: str) -> str:
    content = (title + " " + summary).lower()
    if any(kw in content for kw in ["sanction", "制裁", "禁令", "emergency", "重大"]):
        return "high"
    if any(kw in content for kw in ["policy", "政策", "regulation", "法规", "新规"]):
        return "medium"
    return "low"


def format_recent_time() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_item(source: dict, title: str, summary: str, link: str) -> dict:
    item_id = hashlib.md5((source["id"] + title + link).encode("utf-8")).hexdigest()[:12]
    zh_title = translate_to_zh_tw(title)
    zh_summary = translate_to_zh_tw(summary) if summary else zh_title
    return {
        "id": item_id,
        "category": source["category"],
        "priority": assess_priority(title, summary),
        "source": source["name"],
        "title": zh_title,
        "summary": (zh_summary or zh_title)[:220],
        "link": link,
        "time": format_recent_time(),
        "region": source["region"],
        "icon": source["icon"],
        "srcClass": source["src_class"],
        "catClass": source["cat_class"],
        "tags": ["海关动态"],
    }


def fetch_google_news() -> list:
    print("  → 抓取: Google News 精准主题 ...")
    source = {
        "id": "google-news",
        "name": "Google News",
        "category": "global",
        "region": "global",
        "icon": "🌐",
        "src_class": "src-news",
        "cat_class": "cat-news-bg",
    }
    items = []
    for query in GOOGLE_NEWS_QUERIES:
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=zh-TW&gl=HK&ceid=HK:zh-Hant"
        feed = feedparser.parse(rss_url, request_headers={"User-Agent": "LogPulse/2.0"})
        for entry in feed.entries[:8]:
            title = clean_html(getattr(entry, "title", ""))
            summary = clean_html(getattr(entry, "summary", getattr(entry, "description", "")))
            link = getattr(entry, "link", "#")
            if title and is_relevant(title, summary):
                items.append(build_item(source, title, summary, link))
    print(f"     ✓ 获取 {len(items)} 条")
    return items


def fetch_html_source(source: dict) -> list:
    print(f"  → 抓取: {source['name']} ...")
    items = []
    try:
        resp = requests.get(source["url"], timeout=20, headers={"User-Agent": "LogPulse/2.0"})
        resp.raise_for_status()
        html = resp.text
        matches = re.findall(source["item_pattern"], html, flags=re.IGNORECASE | re.DOTALL)
        for href, raw_title in matches[:60]:
            title = clean_html(raw_title)
            if not title or len(title) < 6:
                continue
            link = to_absolute_url(source["url"], href)
            summary = title
            if is_relevant(title, summary):
                items.append(build_item(source, title, summary, link))
        print(f"     ✓ 获取 {len(items)} 条")
    except Exception as exc:
        print(f"     ✗ 失败: {exc}")
    return items


def generate_stats(items: list, sources_count: int) -> dict:
    return {
        "total": len(items),
        "high_risk": len([i for i in items if i["priority"] == "high"]),
        "by_category": {
            "hongkong": len([i for i in items if i["category"] == "hongkong"]),
            "china": len([i for i in items if i["category"] == "china"]),
            "global": len([i for i in items if i["category"] == "global"]),
        },
        "sources_count": sources_count,
    }


def main():
    print("=" * 50)
    print("🚢 LogPulse 抓取器启动")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    all_items = []
    all_items.extend(fetch_google_news())
    for source in SOURCE_CONFIG:
        all_items.extend(fetch_html_source(source))

    seen = set()
    unique_items = []
    for item in all_items:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique_items.append(item)

    unique_items.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 2))
    unique_items = unique_items[:80]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": generate_stats(unique_items, sources_count=(1 + len(SOURCE_CONFIG))),
        "items": unique_items,
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "news.json"
    out_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 50)
    print(f"✅ 完成！共抓取 {len(unique_items)} 条")
    print(f"   输出: {out_file}")
    print("=" * 50)


if __name__ == "__main__":
    main()
