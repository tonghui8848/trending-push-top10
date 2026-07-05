#!/usr/bin/env python3
"""
GitHub Trending Daily Push
每天推送 GitHub 热榜到微信（通过 Server酱）
包含中文项目描述
"""

import re
import urllib.request
import urllib.parse
import json
import sys
import time
from datetime import date

# ─── 配置 ──────────────────────────────────────────────────
SENDKEY = ""  # 从环境变量读取，不在代码里硬编码
TRENDING_URL = "https://github.com/trending"
LANGUAGE = ""       # 留空 = 全部；可选: python, javascript, go, rust, c++
_SINCE = "daily"   # daily / weekly / monthly
TOP_N = 10
TRANSLATE_DESC = True
# ───────────────────────────────────────────────────────────


def get_sendkey():
    """优先读环境变量，再读本地配置文件"""
    import os
    key = os.environ.get("SENDKEY", "")
    if key:
        return key
    # 本地调试时从 sendkey.txt 读取
    try:
        with open(os.path.join(os.path.dirname(__file__), "sendkey.txt")) as f:
            return f.read().strip()
    except Exception:
        return ""


def fetch_trending(language="", since="daily"):
    url = TRENDING_URL
    params = []
    if language:
        params.append(f"l={urllib.parse.quote(language)}")
    if since:
        params.append(f"since={since}")
    if params:
        url += "?" + "&".join(params)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    return parse_trending_html(html)


def parse_trending_html(html):
    articles = re.findall(
        r'<article class="Box-row">(.*?)</article>', html, re.DOTALL
    )
    repos = []
    for article in articles:
        links = re.findall(r'href="(/[^"]+)"', article)
        repo_link = None
        for link in links:
            parts = link.strip("/").split("/")
            if len(parts) == 2 and parts[0] not in (
                "login", "settings", "notifications", "sponsors",
                "site", "explore", "trending", "apps", "org",
            ):
                repo_link = "/" + parts[0] + "/" + parts[1]
                break
        if not repo_link:
            continue
        full_name = repo_link.strip("/")

        repo = {"full_name": full_name}

        desc_m = re.search(
            r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', article, re.DOTALL
        )
        if desc_m:
            desc = re.sub(r"<[^>]+>", "", desc_m.group(1))
            repo["description"] = desc.strip()
        else:
            repo["description"] = ""

        lang_m = re.search(r'itemprop="programmingLanguage">(.*?)<', article, re.DOTALL)
        repo["language"] = lang_m.group(1).strip() if lang_m else ""

        stars_m = re.search(r'/stargazers"[^>]*>(.*?)</a>', article, re.DOTALL)
        if stars_m:
            stars_text = re.sub(r"<[^>]+>", "", stars_m.group(1))
            stars_text = re.sub(r"[^\d,]", "", stars_text).replace(",", "")
            repo["stars"] = stars_text or "0"
        else:
            repo["stars"] = "0"

        today_m = re.search(r'([\d,]+)\s+stars?\s+today', article, re.IGNORECASE)
        repo["today_stars"] = today_m.group(1).strip().replace(",", "") if today_m else "0"

        repo["url"] = f"https://github.com/{full_name}"
        repos.append(repo)

    return repos


_translate_cache = {}


def translate_to_zh(text):
    if not text or not TRANSLATE_DESC:
        return ""
    if text in _translate_cache:
        return _translate_cache[text]

    text = " ".join(text.split())

    # Google 免费翻译接口
    try:
        encoded = urllib.parse.quote(text[:500])
        url = (
            f"https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=en&tl=zh-CN&dt=t&q={encoded}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            segments = data[0]
            result = "".join(seg[0] for seg in segments if seg[0])
            if result:
                _translate_cache[text] = result.strip()
                return result.strip()
    except Exception:
        pass

    # 降级：MyMemory
    try:
        encoded = urllib.parse.quote(text[:400])
        url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair=en|zh"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result = data.get("responseData", {}).get("translatedText", "")
            if result and result != text:
                result = result.strip()
                _translate_cache[text] = result
                return result
    except Exception:
        pass

    return ""


def format_markdown(repos, since="daily"):
    today = date.today().strftime("%Y-%m-%d")
    since_label = {"daily": "今日", "weekly": "本周", "monthly": "本月"}.get(since, "今日")

    lines = []
    lines.append(f"## GitHub {since_label}热榜 · {today}")
    lines.append("")
    lines.append(f"> 按 {since_label} Star 增量排序，共 {len(repos)} 个项目")
    lines.append("")

    for i, repo in enumerate(repos, 1):
        lang = f"`{repo['language']}` " if repo["language"] else ""
        desc_zh = repo.get("description_zh", "")
        desc_en = repo.get("description", "")
        today_s = repo.get("today_stars", "0")
        stars = repo.get("stars", "0")

        lines.append(f"**{i}. [{repo['full_name']}]({repo['url']})**")
        if desc_zh:
            lines.append(f"　{desc_zh}")
        elif desc_en:
            lines.append(f"　{desc_en}")
        lines.append(f"{lang}⭐ {stars} | 📈 +{today_s}")
        lines.append("")

    lines.append("---")
    lines.append("📊 数据：[GitHub Trending](https://github.com/trending)")
    lines.append("🤖 WorkBuddy 自动推送")

    return "\n".join(lines)


def send_to_wechat(title, content, sendkey):
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    sendkey = get_sendkey()
    if not sendkey:
        print("❌ 未找到 SENDKEY，请设置环境变量或在 sendkey.txt 中配置")
        sys.exit(1)

    print("[1/4] 抓取 GitHub Trending...")
    sys.stdout.flush()

    try:
        repos = fetch_trending(language=LANGUAGE, since=_SINCE)
    except Exception as e:
        print(f"抓取失败: {e}")
        sys.exit(1)

    if not repos:
        print("未抓取到任何仓库")
        sys.exit(1)

    print(f"[2/4] 共抓取到 {len(repos)} 个项目")
    sys.stdout.flush()

    repos.sort(key=lambda r: int(r.get("today_stars", "0") or 0), reverse=True)
    top_repos = repos[:TOP_N]

    if TRANSLATE_DESC:
        print("[3/4] 翻译项目描述...")
        sys.stdout.flush()
        for i, repo in enumerate(top_repos):
            desc = repo.get("description", "")
            print(f"  [{i+1}/{len(top_repos)}] {repo['full_name']}")
            sys.stdout.flush()
            if desc:
                repo["description_zh"] = translate_to_zh(desc)
            else:
                repo["description_zh"] = ""
            time.sleep(0.4)

    since_label = {"daily": "今日", "weekly": "本周", "monthly": "本月"}.get(_SINCE, "今日")
    title = f"GitHub {since_label}热榜 · {date.today().strftime('%m-%d')}"
    content = format_markdown(top_repos, _SINCE)

    print("[4/4] 推送到微信...")
    sys.stdout.flush()
    try:
        result = send_to_wechat(title, content, sendkey)
        if result.get("code") == 0:
            print(f"✅ 推送成功！PushID: {result['data']['pushid']}")
        else:
            print(f"❌ 推送失败: {result}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
