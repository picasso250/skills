from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen


DEFAULT_ENDPOINT = "http://127.0.0.1:9222"


@dataclass(frozen=True)
class TabInfo:
    context_index: int
    page_index: int
    title: str
    url: str

    def to_dict(self) -> dict[str, object]:
        return {
            "context_index": self.context_index,
            "page_index": self.page_index,
            "title": self.title,
            "url": self.url,
        }


def get_ws_url(endpoint: str) -> str:
    try:
        with urlopen(f"{endpoint}/json/version", timeout=5) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"CDP endpoint not ready at {endpoint}: {exc}") from exc

    ws_url = payload.get("webSocketDebuggerUrl", "")
    if not ws_url:
        raise RuntimeError(f"CDP endpoint did not return webSocketDebuggerUrl: {endpoint}")
    return ws_url


def iter_pages(browser):
    for context_index, context in enumerate(browser.contexts):
        for page_index, page in enumerate(context.pages):
            yield context_index, page_index, page


def collect_tabs(browser) -> list[TabInfo]:
    tabs: list[TabInfo] = []
    for context_index, page_index, page in iter_pages(browser):
        tabs.append(
            TabInfo(
                context_index=context_index,
                page_index=page_index,
                title=page.title(),
                url=page.url,
            )
        )
    return tabs


def find_page_by_exact_url(browser, url: str):
    for _, _, page in iter_pages(browser):
        if page.url == url:
            return page
    raise RuntimeError(f"Exact tab not found for URL: {url}")
