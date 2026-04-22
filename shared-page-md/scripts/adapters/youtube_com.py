PRUNE_SELECTORS = [
    "tp-yt-app-drawer",
    "ytd-guide-renderer",
    "ytd-mini-guide-renderer",
    "ytd-masthead",
    "ytd-popup-container",
    "tp-yt-paper-dialog",
    "ytd-player-overlay",
    "ytd-engagement-panel-section-list-renderer",
    "ytd-watch-next-secondary-results-renderer",
    "#guide",
    "#masthead-container",
    "#secondary",
    "ytd-comments",
]


async def ready_hint(page, timeout_ms: int = 15000) -> None:
    try:
        await page.wait_for_function(
            """
            () => {
              const root =
                document.querySelector('ytd-browse') ||
                document.querySelector('ytd-watch-flexy') ||
                document.querySelector('ytd-search') ||
                document.querySelector('ytd-page-manager');
              return !!root && (root.innerText || '').trim().length > 80;
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
