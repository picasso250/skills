import argparse
import asyncio
import json
import re
from urllib.request import urlopen

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def topic_url(topic_id: str) -> str:
    return f"https://v2ex.com/t/{topic_id}#reply0"


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def resolve_ws_endpoint(host: str, port: int) -> str:
    version_url = f"http://{host}:{port}/json/version"
    with urlopen(version_url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    ws_endpoint = payload.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise RuntimeError(f"Missing webSocketDebuggerUrl in {version_url}")
    return ws_endpoint


def extract_structured_topic_data(soup: BeautifulSoup) -> dict:
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text()
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "DiscussionForumPosting":
            stats = {}
            for item in data.get("interactionStatistic", []) or []:
                if not isinstance(item, dict):
                    continue
                kind = item.get("interactionType", "")
                count = str(item.get("userInteractionCount", ""))
                if kind.endswith("ViewAction"):
                    stats["clicks"] = count
                elif kind.endswith("LikeAction"):
                    stats["favorites"] = count
                elif kind.endswith("ReplyAction"):
                    stats["replies"] = count
            return {
                "node": collapse_ws((data.get("isPartOf") or {}).get("name", "")),
                "clicks": stats.get("clicks", ""),
                "favorites": stats.get("favorites", ""),
                "replies": stats.get("replies", ""),
                "topic_meta": collapse_ws(data.get("datePublished", "")),
            }
    return {}


def to_markdown(soup: BeautifulSoup, url: str) -> str:
    title_node = soup.select_one("h1")
    title = collapse_ws(title_node.get_text(" ", strip=True)) if title_node else "(no title)"

    body_node = soup.select_one("div.topic_content")
    body_text = body_node.get_text("\n", strip=True) if body_node else ""

    structured = extract_structured_topic_data(soup)
    meta_text = collapse_ws(soup.get_text(" ", strip=True))
    clicks_match = re.search(r"(\d+)\s*次点击", meta_text)
    favs_match = re.search(r"(\d+)\s*人收藏", meta_text)
    replies_match = re.search(r"(\d+)\s*条回复", meta_text)

    clicks = structured.get("clicks") or (clicks_match.group(1) if clicks_match else "?")
    favorites = structured.get("favorites") or (favs_match.group(1) if favs_match else "0")
    replies = structured.get("replies") or (
        replies_match.group(1) if replies_match else ("0" if "目前尚无回复" in meta_text else "?")
    )
    node = structured.get("node", "")

    lines = [
        f"# {title}",
        "",
        f"链接：{url}",
        f"节点：{node or '(unknown)'}",
        f"点击：{clicks}",
        f"收藏：{favorites}",
        f"回复：{replies}",
    ]

    topic_meta = structured.get("topic_meta", "")
    if topic_meta:
        lines.append(f"创建时间：{topic_meta}")

    lines.extend(["", "## 正文", "", body_text or "(empty)", "", "## 回复", ""])

    reply_blocks = []
    for block in soup.select("div[id^='r_']"):
        user_node = block.select_one("strong a")
        user = collapse_ws(user_node.get_text(" ", strip=True)) if user_node else "(unknown)"
        no_node = block.select_one(".no")
        floor = collapse_ws(no_node.get_text(" ", strip=True)).lstrip("#") if no_node else ""
        meta_node = block.select_one(".ago")
        when = collapse_ws(meta_node.get_text(" ", strip=True)) if meta_node else ""
        content_node = block.select_one(".reply_content")
        content = content_node.get_text("\n", strip=True) if content_node else ""
        if content:
            header_parts = []
            if floor:
                header_parts.append(f"#{floor}")
            header_parts.append(user)
            if when:
                header_parts.append(when)
            header = " | ".join(header_parts)
            reply_blocks.append(f"### {header}\n\n{content}")

    if reply_blocks:
        for index, block in enumerate(reply_blocks):
            if index > 0:
                lines.extend(["", "---", ""])
            lines.extend([block, ""])
    else:
        lines.append("(暂无回复)")

    return "\n".join(lines).strip() + "\n"


async def fetch_html(url: str, ws_endpoint: str, refresh: bool) -> str:
    playwright = await async_playwright().start()
    created_context = None
    try:
        browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
        page = None
        for context in browser.contexts:
            for existing_page in context.pages:
                if f"/t/" in existing_page.url and url.split("#")[0] in existing_page.url:
                    page = existing_page
                    break
            if page:
                break

        if page is None:
            if browser.contexts:
                context = browser.contexts[0]
            else:
                context = await browser.new_context()
                created_context = context
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        else:
            await page.bring_to_front()
            if page.url == "about:blank":
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            elif refresh:
                await page.reload(wait_until="domcontentloaded", timeout=15000)
            else:
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass

        try:
            return await page.evaluate(
                """
                () => {
                  const clone = document.documentElement.cloneNode(true);
                  return '<!DOCTYPE html>\\n' + clone.outerHTML;
                }
                """
            )
        except Exception:
            return await page.content()
    finally:
        if created_context:
            await created_context.close()
        await playwright.stop()


async def main() -> int:
    parser = argparse.ArgumentParser(description="通过 9222 CDP 读取 V2EX 主题帖并导出 Markdown 快照")
    parser.add_argument("-t", "--topic", required=True, help="V2EX 主题 ID，例如 1206255")
    parser.add_argument("--host", default="127.0.0.1", help="Chrome DevTools host")
    parser.add_argument("--port", type=int, default=9222, help="Chrome DevTools port")
    parser.add_argument("--refresh", action="store_true", help="复用已有标签页时先刷新再抓取")
    args = parser.parse_args()

    url = topic_url(args.topic)
    ws_endpoint = resolve_ws_endpoint(args.host, args.port)
    html = await fetch_html(url, ws_endpoint, args.refresh)

    soup = BeautifulSoup(html, "html.parser")
    markdown = to_markdown(soup, url)
    print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
