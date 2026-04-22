PRUNE_SELECTORS = [
    "aside",
    "footer",
    "[role='dialog']",
    "[data-testid*='share']",
    "[data-testid*='subscribe']",
    "[class*='share']",
    "[class*='subscribe']",
]


async def ready_hint(page, timeout_ms: int = 15000) -> None:
    try:
        await page.wait_for_function(
            """
            () => {
              const article = document.querySelector('article');
              return !!article && (article.innerText || '').trim().length > 120;
            }
            """,
            timeout=timeout_ms,
        )
    except Exception:
        return


def prune(soup) -> None:
    for selector in PRUNE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()
