#!/usr/bin/env python3
"""
Create a deterministic English workspace for WeChat article production.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

DEFAULT_BASE_DIR = Path.home() / "Documents" / "wechat-post-workbench"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a topic workspace for the WeChat article workflow."
    )
    parser.add_argument("--topic", required=True, help="Article topic, inspiration, or brief.")
    parser.add_argument(
        "--slug",
        help="ASCII folder name. If omitted, a timestamped English-safe slug is generated.",
    )
    parser.add_argument(
        "--base-dir",
        default=str(DEFAULT_BASE_DIR),
        help=f"Base directory for workspaces. Default: {DEFAULT_BASE_DIR}",
    )
    return parser.parse_args()


def slugify_topic(topic: str) -> str:
    ascii_topic = topic.encode("ascii", "ignore").decode("ascii").lower()
    ascii_topic = re.sub(r"[^a-z0-9]+", "-", ascii_topic).strip("-")
    if not ascii_topic:
        ascii_topic = "topic"
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{ascii_topic}-{timestamp}"


def main() -> None:
    args = parse_args()
    base_path = Path(args.base_dir).expanduser().resolve()
    workspace_slug = args.slug or slugify_topic(args.topic)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", workspace_slug):
        raise RuntimeError("Slug must contain only lowercase letters, digits, and hyphens.")

    workspace = base_path / workspace_slug
    workspace.mkdir(parents=True, exist_ok=True)

    meta = {
        "topic": args.topic,
        "slug": workspace_slug,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    (workspace / "workspace.json").write_text(
        json.dumps(meta, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (workspace / "brief.md").write_text(
        f"# Topic Brief\n\n{args.topic}\n",
        encoding="utf-8",
    )

    print(str(workspace))
    print(str(workspace / "brief.md"))
    print(str(workspace / "workspace.json"))


if __name__ == "__main__":
    main()
