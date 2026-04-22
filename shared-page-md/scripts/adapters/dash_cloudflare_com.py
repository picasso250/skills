"""Cloudflare Dashboard adaptor.

Cloudflare's dashboard already exposes a clean, semantic `main` in this case,
so this adaptor is intentionally a no-op placeholder. It marks the domain as
reviewed and gives us a precise place to add domain-specific waits or pruning
later if the UI changes.
"""


async def ready_hint(page, timeout_ms: int = 15000) -> None:
    # No extra wait for now; Cloudflare's DOM is already in good shape here.
    return


def prune(soup) -> None:
    # No pruning for now; the current main output is already acceptably clean.
    return
