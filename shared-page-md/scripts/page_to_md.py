import argparse
import asyncio
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from playwright.async_api import async_playwright


BROWSER_ENDPOINT = "http://127.0.0.1:9222"
INLINE_MAIN_MD_MAX_BYTES = 4 * 1024


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def visible_text_length(node: Tag) -> int:
    return len(collapse_ws(node.get_text(" ", strip=True)))


def has_hidden_attr(node: Tag) -> bool:
    attrs = getattr(node, "attrs", None)
    if not isinstance(attrs, dict):
        return False

    if "hidden" in attrs:
        return True

    if str(attrs.get("aria-hidden", "")).strip().lower() == "true":
        return True

    style = str(attrs.get("style", "")).replace(" ", "").lower()
    return "display:none" in style or "visibility:hidden" in style


def is_noise_tag(node: Tag) -> bool:
    name = getattr(node, "name", None)
    if not isinstance(name, str):
        return False
    return name.lower() in {"nav", "header", "footer", "aside", "iframe"}


def find_main_root(soup: BeautifulSoup) -> Tag:
    body = soup.body or soup

    for selector in ("main", "article"):
        candidate = body.select_one(selector)
        if isinstance(candidate, Tag) and visible_text_length(candidate) >= 80:
            return candidate

    return body


def has_explicit_main_root(soup: BeautifulSoup) -> bool:
    body = soup.body or soup
    for selector in ("main", "article"):
        candidate = body.select_one(selector)
        if isinstance(candidate, Tag) and visible_text_length(candidate) >= 80:
            return True
    return False


def is_button_like(node: Tag) -> bool:
    name = node.name.lower()
    if name == "a":
        return False
    if name == "button":
        return True
    return str(node.get("role", "")).strip().lower() == "button"


def find_labeled_text(node: Tag) -> str:
    node_id = str(node.get("id", "")).strip()
    if node_id:
        root = node if node.parent is None else node.parent
        while isinstance(root, Tag) and root.parent is not None:
            root = root.parent
        if isinstance(root, Tag):
            label = root.find("label", attrs={"for": node_id})
            if isinstance(label, Tag):
                text = collapse_ws(label.get_text(" ", strip=True))
                if text:
                    return text

    parent = node.parent
    while isinstance(parent, Tag):
        if parent.name and parent.name.lower() == "label":
            text = collapse_ws(parent.get_text(" ", strip=True))
            if text:
                return text
        parent = parent.parent

    aria_label = collapse_ws(str(node.get("aria-label", "")))
    if aria_label:
        return aria_label

    labelledby = str(node.get("aria-labelledby", "")).strip()
    if labelledby:
        root = node if node.parent is None else node.parent
        while isinstance(root, Tag) and root.parent is not None:
            root = root.parent
        if isinstance(root, Tag):
            parts = []
            for ref_id in labelledby.split():
                label_node = root.find(id=ref_id)
                if isinstance(label_node, Tag):
                    text = collapse_ws(label_node.get_text(" ", strip=True))
                    if text:
                        parts.append(text)
            if parts:
                return collapse_ws(" ".join(parts))

    for attr in ("name", "id"):
        text = collapse_ws(str(node.get(attr, "")))
        if text:
            return text

    return ""


def input_to_md(node: Tag) -> str:
    input_type = str(node.get("type", "text")).strip().lower()
    if input_type in {"hidden", "submit", "button", "image", "reset", "file"}:
        return ""

    if input_type in {"checkbox", "radio"}:
        checked = node.has_attr("checked")
        marker = ("(*)" if checked else "( )") if input_type == "radio" else ("[x]" if checked else "[ ]")
        label = find_labeled_text(node)
        return f"{marker} {label}".strip()

    if input_type == "password":
        value = collapse_ws(str(node.get("value", "")))
        return "[_******_]" if value else "[password]"

    value = collapse_ws(str(node.get("value", "")))
    placeholder = collapse_ws(str(node.get("placeholder", "")))
    if value:
        return f"[_{value}_]"
    if placeholder:
        return f"[{placeholder}]"
    return "[______]"


def inline_children_to_md(node: Tag, skip_form_controls: bool = False) -> str:
    parts = []
    for child in node.children:
        if skip_form_controls and isinstance(child, Tag) and child.name and child.name.lower() in {"input", "textarea", "select"}:
            continue
        parts.append(inline_to_md(child))
    return collapse_ws("".join(parts))


def inline_to_md(node) -> str:
    if isinstance(node, Comment):
        return ""

    if isinstance(node, NavigableString):
        return str(node)

    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    content = "".join(inline_to_md(child) for child in node.children)
    content = re.sub(r"[ \t\r\f\v]+", " ", content)

    if name in {"script", "style", "noscript"} or is_noise_tag(node) or has_hidden_attr(node):
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
    if name == "input":
        return input_to_md(node)
    if name == "textarea":
        text = collapse_ws(node.get_text(" ", strip=True) or str(node.get("placeholder", "")))
        return f"[{text}]" if text else "[______]"
    if name == "select":
        selected = node.find("option", selected=True)
        if selected is None:
            selected = node.find("option")
        text = collapse_ws(selected.get_text(" ", strip=True)) if isinstance(selected, Tag) else ""
        return f"[{text}]" if text else "[______]"
    if is_button_like(node):
        text = collapse_ws(content)
        return f"[[{text}]]" if text else ""
    if name == "label":
        return inline_children_to_md(node, skip_form_controls=True)

    return content


def block_to_md(node, indent: int = 0) -> str:
    if isinstance(node, Comment):
        return ""

    if isinstance(node, NavigableString):
        text = collapse_ws(str(node))
        return f"{text}\n\n" if text else ""

    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name in {"script", "style", "noscript"} or is_noise_tag(node) or has_hidden_attr(node):
        return ""

    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(name[1])
        text = inline_children_to_md(node)
        return f"{'#' * level} {text}\n\n" if text else ""

    if name == "p":
        text = inline_children_to_md(node)
        return f"{text}\n\n" if text else ""

    if name == "label":
        controls = []
        for child in node.children:
            if isinstance(child, Tag) and child.name and child.name.lower() in {"input", "textarea", "select"}:
                rendered = inline_to_md(child)
                if rendered:
                    controls.append(rendered)
        if controls:
            return "\n".join(controls) + "\n\n"
        return ""

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

    if name in {"input", "textarea", "select"}:
        text = inline_to_md(node)
        return f"{text}\n\n" if text else ""

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

    explicit_main = has_explicit_main_root(soup)

    if not only_main or not explicit_main:
        for tag in soup.find_all(["nav", "header", "footer", "aside", "iframe"]):
            tag.decompose()

        for tag in list(soup.find_all(True)):
            if has_hidden_attr(tag):
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


def normalize_match_url(raw_url: str) -> str | None:
    raw_url = (raw_url or "").strip()
    if not raw_url:
        return None

    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"http", "https"}:
        return None

    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), path, parsed.query, ""))


def url_matches(candidate: str, target: str) -> bool:
    candidate_normalized = normalize_match_url(candidate)
    target_normalized = normalize_match_url(target)
    if not candidate_normalized or not target_normalized:
        return False
    return candidate_normalized == target_normalized


async def fetch_html(url: str, timeout_seconds: int, refresh: bool = False) -> str:
    timeout_ms = timeout_seconds * 1000
    playwright = await async_playwright().start()
    browser = None
    page = None
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
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        else:
            await page.bring_to_front()
            if page.url == "about:blank":
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            else:
                if refresh:
                    await page.reload(wait_until="domcontentloaded", timeout=timeout_ms)
                else:
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                    except Exception:
                        pass

        try:
            return await page.evaluate(
                """
                () => {
                  const clone = document.documentElement.cloneNode(true);

                  const syncByIndex = (selector, updater) => {
                    const liveNodes = Array.from(document.querySelectorAll(selector));
                    const clonedNodes = Array.from(clone.querySelectorAll(selector));
                    const count = Math.min(liveNodes.length, clonedNodes.length);
                    for (let i = 0; i < count; i += 1) {
                      updater(liveNodes[i], clonedNodes[i]);
                    }
                  };

                  syncByIndex('input', (live, copied) => {
                    const type = (live.getAttribute('type') || '').toLowerCase();
                    if (type === 'checkbox' || type === 'radio') {
                      if (live.checked) {
                        copied.setAttribute('checked', 'checked');
                      } else {
                        copied.removeAttribute('checked');
                      }
                      return;
                    }
                    copied.setAttribute('value', live.value || '');
                  });

                  syncByIndex('textarea', (live, copied) => {
                    copied.textContent = live.value || '';
                  });

                  syncByIndex('select', (live, copied) => {
                    const liveOptions = Array.from(live.options);
                    const copiedOptions = Array.from(copied.options);
                    const optionCount = Math.min(liveOptions.length, copiedOptions.length);
                    for (let i = 0; i < optionCount; i += 1) {
                      if (liveOptions[i].selected) {
                        copiedOptions[i].setAttribute('selected', 'selected');
                      } else {
                        copiedOptions[i].removeAttribute('selected');
                      }
                    }
                  });

                  return '<!DOCTYPE html>\\n' + clone.outerHTML;
                }
                """
            )
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
        if created_context:
            await created_context.close()
        if playwright:
            await playwright.stop()


async def main() -> int:
    parser = argparse.ArgumentParser(description="通过 CDP 获取页面 DOM/HTML 并转换为 Markdown")
    parser.add_argument("--url", required=True, help="目标页面 URL")
    parser.add_argument("--timeout", type=int, default=15, help="页面加载超时，单位秒")
    parser.add_argument("--refresh", action="store_true", help="复用已有标签页时先刷新再抓取")
    args = parser.parse_args()

    try:
        html = await fetch_html(args.url, args.timeout, refresh=args.refresh)
        full_markdown = html_to_markdown(html, only_main=False)
        main_markdown = html_to_markdown(html, only_main=True)

        output_dir = Path(tempfile.mkdtemp(prefix="toMD-"))
        full_path = output_dir / "full.md"
        main_path = output_dir / "main.md"
        html_path = output_dir / "page.html"

        full_path.write_text(full_markdown, encoding="utf-8")
        main_path.write_text(main_markdown, encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")

        inline_main_markdown = main_path.stat().st_size <= INLINE_MAIN_MD_MAX_BYTES
        if inline_main_markdown:
            print(main_markdown, end="" if main_markdown.endswith("\n") else "\n")

        print(f"full_md={full_path}")
        if not inline_main_markdown:
            print(f"main_md={main_path}")
        print(f"html={html_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
