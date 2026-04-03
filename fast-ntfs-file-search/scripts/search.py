import sys
import requests


def search_everything(
    query,
    base_url="http://127.0.0.1:7788",
    limit=50,
    match="name",
    type_filter="file",
):
    params = {
        "q": query,
        "limit": limit,
        "mode": match,
        "type": type_filter,
    }
    try:
        response = requests.get(f"{base_url.rstrip('/')}/search", params=params, timeout=20)
        response.raise_for_status()
        return [line.strip() for line in response.text.splitlines() if line.strip()]
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return []


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Usage: python scripts/search.py <query> [--limit N] [--match name|path|all] [--type file|dir|all] [--addr URL]")
        sys.exit(1)

    query_parts = []
    limit = 50
    match = "name"
    type_filter = "file"
    addr = "http://127.0.0.1:7788"

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
            continue
        if arg == "--match" and i + 1 < len(sys.argv):
            match = sys.argv[i + 1]
            i += 2
            continue
        if arg == "--type" and i + 1 < len(sys.argv):
            type_filter = sys.argv[i + 1]
            i += 2
            continue
        if arg == "--addr" and i + 1 < len(sys.argv):
            addr = sys.argv[i + 1]
            i += 2
            continue

        query_parts.append(arg)
        i += 1

    query = " ".join(query_parts).strip()
    if not query:
        print("Error: empty query", file=sys.stderr)
        sys.exit(1)

    paths = search_everything(query, base_url=addr, limit=limit, match=match, type_filter=type_filter)

    for path in paths:
        print(path)
