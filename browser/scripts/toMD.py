import argparse
import asyncio
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from playwright.async_api import async_playwright


BROWSER_ENDPOINT = "http://127.0.0.1:9222"
MAIN_HINT_RE = re.compile(r"\b(main|content|article|post|entry|markdown)\b", re.IGNORECASE)


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def visible_text_length(node: Tag) -> int:
    return len(collapse_ws(node.get_text(" ", strip=True)))


def find_main_root(soup: BeautifulSoup) -> Tag:
    body = soup.body or soup

    for selector in ("main", "article"):
        candidate = body.select_one(selector)
        if isinstance(candidate, Tag) and visible_text_length(candidate) >= 80:
            return candidate

    candidates: list[tuple[int, Tag]] = []
    for node in body.find_all(["div", "section", "article"], limit=200):
        if not isinstance(node, Tag):
            continue

        attrs = " ".join(
            str(node.get(key, ""))
            for key in ("id", "class", "role", "data-testid", "aria-label")
        )
        if not MAIN_HINT_RE.search(attrs):
            continue

        text_len = visible_text_length(node)
        if text_len < 120:
            continue

        candidates.append((text_len, node))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    return body


def inline_to_md(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)

    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    content = "".join(inline_to_md(child) for child in node.children)
    content = re.sub(r"[ \t\r\f\v]+", " ", content)

    if name in {"script", "style", "noscript"}:
        return ""
    if name == "br":
        return "  \n"
    if name in {"strong", "b"}:
        return f"**{content.strip()}**" if content.strip() else ""
    if name in {"em", "i"}:
        return f"*{content.strip()}*" if content.strip() else ""
    if name == "code":
        text = content.strip().replace("`", "\\`")
        return f"`{text}`" if text else ""
    if name == "a":
        href = (node.get("href") or "").strip()
        text = collapse_ws(content)
        if href and text:
            return f"[{text}]({href})"
        return text or href
    if name == "img":
        alt = collapse_ws(node.get("alt", ""))
        src = (node.get("src") or "").strip()
        if src:
            return f"![{alt}]({src})"
        return alt

    return content


def block_to_md(node, indent: int = 0) -> str:
    if isinstance(node, NavigableString):
        text = collapse_ws(str(node))
        return f"{text}\n\n" if text else ""

    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name in {"script", "style", "noscript"}:
        return ""

    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(name[1])
        text = collapse_ws("".join(inline_to_md(child) for child in node.children))
        return f"{'#' * level} {text}\n\n" if text else ""

    if name == "p":
        text = collapse_ws("".join(inline_to_md(child) for child in node.children))
        return f"{text}\n\n" if text else ""

    if name == "blockquote":
        text = "".join(block_to_md(child, indent) for child in node.children).strip()
        if not text:
            text = collapse_ws("".join(inline_to_md(child) for child in node.children))
        if not text:
            return ""
        quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in text.splitlines())
        return f"{quoted}\n\n"

    if name in {"ul", "ol"}:
        lines = []
        index = 1
        for child in node.children:
            if not isinstance(child, Tag) or child.name.lower() != "li":
                continue
            prefix = f"{index}. " if name == "ol" else "- "
            lines.append(list_item_to_md(child, prefix, indent))
            index += 1
        return "\n".join(line for line in lines if line).rstrip() + "\n\n" if lines else ""

    if name == "pre":
        text = node.get_text("\n").strip("\n")
        return f"```\n{text}\n```\n\n" if text else ""

    if name == "table":
        return table_to_md(node)

    if name in {"article", "section", "main", "body", "div"}:
        parts = []
        for child in node.children:
            if isinstance(child, Tag) and child.name.lower() in {"div", "section"} and not child.get_text(strip=True):
                continue
            parts.append(block_to_md(child, indent))
        text = "".join(parts)
        if text.strip():
            return text
        inline_text = collapse_ws("".join(inline_to_md(child) for child in node.children))
        return f"{inline_text}\n\n" if inline_text else ""

    if name == "hr":
        return "---\n\n"

    if name == "li":
        return list_item_to_md(node, "- ", indent) + "\n\n"

    text = collapse_ws("".join(inline_to_md(child) for child in node.children))
    return f"{text}\n\n" if text else ""


def list_item_to_md(node: Tag, prefix: str, indent: int) -> str:
    child_blocks = []
    for child in node.children:
        if isinstance(child, Tag) and child.name.lower() in {"ul", "ol"}:
            nested = block_to_md(child, indent + 2).rstrip()
            if nested:
                child_blocks.append(nested)

    inline_parts = []
    for child in node.children:
        if isinstance(child, Tag) and child.name.lower() in {"ul", "ol"}:
            continue
        inline_parts.append(inline_to_md(child))
    inline_text = collapse_ws("".join(inline_parts))

    line = (" " * indent) + prefix + inline_text if inline_text else (" " * indent) + prefix.rstrip()
    if not child_blocks:
        return line

    nested = "\n".join(child_blocks)
    nested = "\n".join((" " * (indent + 2)) + item if item.strip() else "" for item in nested.splitlines())
    return f"{line}\n{nested}"


def table_to_md(table: Tag) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        rows.append([collapse_ws(cell.get_text(" ", strip=True)) for cell in cells])

    if not rows:
        return ""

    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = normalized[0]
    separator = ["---"] * width
    body = normalized[1:] or [[""] * width]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n\n"


def html_to_markdown(html: str, only_main: bool = True) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    root = find_main_root(soup) if only_main else (soup.body or soup)
    parts = [block_to_md(child) for child in root.children]
    markdown = "".join(parts)
    return normalize_blank_lines(markdown)


async def get_ws_url() -> str | None:
    try:
        with urllib.request.urlopen(f"{BROWSER_ENDPOINT}/json/version", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("webSocketDebuggerUrl")
    except Exception:
        return None


def url_matches(candidate: str, target: str) -> bool:
    candidate = (candidate or "").rstrip("/")
    target = target.rstrip("/")
    return candidate == target or target in candidate


async def fetch_html(url: str, timeout_seconds: int) -> str:
    timeout_ms = timeout_seconds * 1000
    playwright = await async_playwright().start()
    browser = None
    page = None
    created_page = False
    created_context = None

    try:
        ws_url = await get_ws_url()
        browser = await playwright.chromium.connect_over_cdp(ws_url or BROWSER_ENDPOINT)

        for context in browser.contexts:
            for existing_page in context.pages:
                if url_matches(existing_page.url, url):
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
            created_page = True
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        else:
            await page.bring_to_front()
            if page.url == "about:blank":
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            else:
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                except Exception:
                    pass

        client = await page.context.new_cdp_session(page)
        await client.send("DOM.enable")
        try:
            document = await client.send("DOM.getDocument", {"depth": -1, "pierce": True})
            html = await client.send("DOM.getOuterHTML", {"nodeId": document["root"]["nodeId"]})
            return html["outerHTML"]
        except Exception:
            return await page.content()
    finally:
        if created_page and page:
            await page.close()
        if created_context:
            await created_context.close()
        if playwright:
            await playwright.stop()


async def main() -> int:
    parser = argparse.ArgumentParser(description="通过 CDP 获取页面 DOM/HTML 并转换为 Markdown")
    parser.add_argument("--url", required=True, help="目标页面 URL")
    parser.add_argument("--timeout", type=int, default=15, help="页面加载超时，单位秒")
    args = parser.parse_args()

    try:
        html = await fetch_html(args.url, args.timeout)
        full_markdown = html_to_markdown(html, only_main=False)
        main_markdown = html_to_markdown(html, only_main=True)

        output_dir = Path(tempfile.mkdtemp(prefix="toMD-"))
        full_path = output_dir / "full.md"
        main_path = output_dir / "main.md"

        full_path.write_text(full_markdown, encoding="utf-8")
        main_path.write_text(main_markdown, encoding="utf-8")

        print(f"full_md={full_path}")
        print(f"main_md={main_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
