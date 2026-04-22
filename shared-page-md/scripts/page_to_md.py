import argparse
import asyncio
import importlib.util
import inspect
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
ADAPTERS_DIR = Path(__file__).resolve().parent / "adapters"


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def normalize_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    stripped = text.strip()
    return f"{stripped}\n" if stripped else ""


def dedupe_adjacent_short_phrase_line(line: str) -> str:
    match = re.match(r"^(\s*(?:[-*+] |\d+\. |#+ )?)(.*?)(\s*)$", line)
    if not match:
        return line

    prefix, content, suffix = match.groups()
    content = collapse_ws(content)
    if not content or len(content) > 80:
        return line
    if any(char in content for char in "[]()|`"):
        return line

    words = content.split(" ")
    if len(words) < 2:
        return line

    max_phrase_words = min(6, len(words) // 2)
    for phrase_words in range(1, max_phrase_words + 1):
        if len(words) % phrase_words != 0:
            continue

        phrase = words[:phrase_words]
        repeats = len(words) // phrase_words
        if repeats < 2:
            continue

        phrase_text = " ".join(phrase)
        if len(phrase_text) < 8 and phrase_words < 2:
            continue

        if all(words[index:index + phrase_words] == phrase for index in range(0, len(words), phrase_words)):
            return f"{prefix}{phrase_text}{suffix}"

    return line


def dedupe_adjacent_short_phrases(text: str) -> str:
    return "\n".join(dedupe_adjacent_short_phrase_line(line) for line in text.splitlines())


def needs_inline_space(left: str, right: str) -> bool:
    if not left or not right:
        return False

    left_char = left[-1]
    right_char = right[0]

    if left_char.isspace() or right_char.isspace():
        return False
    if left.endswith("  \n") or right.startswith("\n"):
        return False
    if left_char in "([{/":
        return False
    if right_char in ")]}.,;:!?%/":
        return False

    return True


def join_inline_fragments(parts) -> str:
    joined = []
    for part in parts:
        if not part:
            continue
        if joined and needs_inline_space(joined[-1], part):
            joined.append(" ")
        joined.append(part)
    return "".join(joined)


def normalize_adapter_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def iter_adapter_names(hostname: str) -> list[str]:
    labels = [label for label in hostname.lower().split(".") if label]
    names = []
    for start in range(len(labels) - 1):
        suffix = ".".join(labels[start:])
        if suffix.count(".") < 1:
            continue
        module_name = normalize_adapter_name(suffix)
        if module_name and module_name not in names:
            names.append(module_name)
    return names


def load_adapter(url: str):
    hostname = (urlsplit(url).hostname or "").strip().lower()
    if not hostname:
        return None

    for module_name in iter_adapter_names(hostname):
        module_path = ADAPTERS_DIR / f"{module_name}.py"
        if not module_path.is_file():
            continue

        spec = importlib.util.spec_from_file_location(f"shared_page_md_{module_name}", module_path)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return None


def find_main_root(soup: BeautifulSoup) -> tuple[str, Tag] | None:
    body = soup.body or soup

    for selector in ("main", "article"):
        candidate = body.select_one(selector)
        if isinstance(candidate, Tag):
            return selector, candidate

    return None


def measure_html_bytes(node) -> int:
    return len(str(node).encode("utf-8"))


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
    return collapse_ws(join_inline_fragments(parts))


def inline_to_md(node) -> str:
    if isinstance(node, Comment):
        return ""

    if isinstance(node, NavigableString):
        return str(node)

    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    content = join_inline_fragments(inline_to_md(child) for child in node.children)
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
    if name in {"script", "style", "noscript"}:
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
            text = collapse_ws(join_inline_fragments(inline_to_md(child) for child in node.children))
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
        inline_text = collapse_ws(join_inline_fragments(inline_to_md(child) for child in node.children))
        return f"{inline_text}\n\n" if inline_text else ""

    if name == "hr":
        return "---\n\n"

    if name == "li":
        return list_item_to_md(node, "- ", indent) + "\n\n"

    text = collapse_ws(join_inline_fragments(inline_to_md(child) for child in node.children))
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
    inline_text = collapse_ws(join_inline_fragments(inline_parts))

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


def prepare_soup(html: str, adapter=None) -> tuple[BeautifulSoup, dict | None]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    body = soup.body or soup
    prune_stats = None
    prune = getattr(adapter, "prune", None) if adapter else None
    if callable(prune):
        before_bytes = measure_html_bytes(body)
        prune(soup)
        after_bytes = measure_html_bytes(soup.body or soup)
        removed_bytes = max(before_bytes - after_bytes, 0)
        removed_ratio = (removed_bytes / before_bytes * 100.0) if before_bytes else 0.0
        if removed_bytes:
            adapter_name = getattr(adapter, "__name__", "")
            prune_stats = {
                "adapter": adapter_name.rsplit(".", 1)[-1] if adapter_name else "adapter",
                "before_bytes": before_bytes,
                "after_bytes": after_bytes,
                "removed_bytes": removed_bytes,
                "removed_ratio": removed_ratio,
            }

    return soup, prune_stats


def markdown_from_root(root: Tag) -> str:
    parts = [block_to_md(child) for child in root.children]
    markdown = "".join(parts)
    markdown = dedupe_adjacent_short_phrases(markdown)
    return normalize_blank_lines(markdown)


def html_to_markdown(html: str, only_main: bool = True, adapter=None) -> str:
    soup, _ = prepare_soup(html, adapter=adapter)
    root_info = find_main_root(soup) if only_main else None
    root = root_info[1] if root_info else (None if only_main else (soup.body or soup))
    if root is None:
        return ""
    return markdown_from_root(root)


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


async def fetch_html(url: str, timeout_seconds: int, refresh: bool = False, adapter=None) -> str:
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
            await page.goto(url, wait_until="commit", timeout=timeout_ms)
        else:
            await page.bring_to_front()
            if page.url == "about:blank":
                await page.goto(url, wait_until="commit", timeout=timeout_ms)
            else:
                if refresh:
                    await page.reload(wait_until="commit", timeout=timeout_ms)

        await page.wait_for_timeout(3000)

        ready_hint = getattr(adapter, "ready_hint", None) if adapter else None
        if callable(ready_hint):
            hinted = ready_hint(page, timeout_ms=timeout_ms)
            if inspect.isawaitable(hinted):
                await hinted

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
    configure_stdio()

    parser = argparse.ArgumentParser(description="通过 CDP 获取页面 DOM/HTML 并转换为 Markdown")
    parser.add_argument("--url", required=True, help="目标页面 URL")
    parser.add_argument("--timeout", type=int, default=15, help="页面加载超时，单位秒")
    parser.add_argument("--refresh", action="store_true", help="复用已有标签页时先刷新再抓取")
    args = parser.parse_args()

    try:
        adapter = load_adapter(args.url)
        html = await fetch_html(args.url, args.timeout, refresh=args.refresh, adapter=adapter)
        soup, prune_stats = prepare_soup(html, adapter=adapter)
        full_markdown = markdown_from_root(soup.body or soup)
        main_root = find_main_root(soup)
        main_markdown = markdown_from_root(main_root[1]) if main_root else ""
        has_main_markdown = bool(main_markdown.strip())

        output_dir = Path(tempfile.mkdtemp(prefix="toMD-"))
        full_path = output_dir / "full.md"
        html_path = output_dir / "page.html"
        main_path = output_dir / "main.md"

        full_path.write_text(full_markdown, encoding="utf-8")
        if has_main_markdown:
            main_path.write_text(main_markdown, encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")

        selected_markdown = main_markdown if has_main_markdown else full_markdown
        if prune_stats:
            print(
                "prune="
                f"{prune_stats['adapter']} "
                f"{prune_stats['before_bytes']}B->{prune_stats['after_bytes']}B "
                f"(-{prune_stats['removed_bytes']}B, {prune_stats['removed_ratio']:.2f}%)"
            )
        if main_root:
            print(f"<!-- {main_root[0]} -->")

        if selected_markdown:
            print(selected_markdown, end="" if selected_markdown.endswith("\n") else "\n")

        print("---")
        print(f"full_md={full_path}")
        print(f"html={html_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
