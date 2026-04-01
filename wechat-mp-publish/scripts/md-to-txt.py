#!/usr/bin/env python3
"""
Convert a markdown file to plain text, reject tables, and write the result to a temp file.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strip markdown formatting, remove empty lines, and write plain text to a temp file."
    )
    parser.add_argument("input_path", help="Path to the markdown file")
    return parser.parse_args()


def detect_table(text: str) -> bool:
    lines = text.splitlines()
    for idx in range(len(lines) - 1):
        line = lines[idx].strip()
        next_line = lines[idx + 1].strip()
        if "|" not in line or "|" not in next_line:
            continue
        if re.fullmatch(r"\|?[\s:-]+\|[\s|:-]*", next_line):
            return True
    if "<table" in text.lower() or "</table>" in text.lower():
        return True
    return False


def strip_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n")

    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)

    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*\n]+)\*", r"\1", text)
    text = re.sub(r"_([^_\n]+)_", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)

    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    text = re.sub(r"^\s*---+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*___+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\*\*\*+\s*$", "", text, flags=re.MULTILINE)
    text = collapse_cross_script_spaces(text)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def is_ascii_letter(char: str) -> bool:
    return ("A" <= char <= "Z") or ("a" <= char <= "z")


def collapse_cross_script_spaces(text: str) -> str:
    chars = list(text)
    result: list[str] = []
    for idx, char in enumerate(chars):
        if char != " ":
            result.append(char)
            continue
        if idx == 0 or idx == len(chars) - 1:
            result.append(char)
            continue

        left = chars[idx - 1]
        right = chars[idx + 1]
        left_is_letter = is_ascii_letter(left)
        right_is_letter = is_ascii_letter(right)
        if left_is_letter != right_is_letter and left != "\n" and right != "\n":
            continue

        result.append(char)
    return "".join(result)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    source = input_path.read_text(encoding="utf-8")
    if detect_table(source):
        print("Markdown contains a table. Refusing to convert.", file=sys.stderr)
        sys.exit(1)

    plain_text = strip_markdown(source)
    fd, tmp_path = tempfile.mkstemp(prefix="md-to-txt-", suffix=".txt")
    os.close(fd)
    Path(tmp_path).write_text(plain_text, encoding="utf-8")
    print(tmp_path)


if __name__ == "__main__":
    main()
