from __future__ import annotations

import argparse
from datetime import datetime
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update a .env file by collecting values through local Tk dialogs."
    )
    parser.add_argument("--file", required=True, help="Target .env file path.")
    parser.add_argument(
        "--key",
        action="append",
        dest="keys",
        required=True,
        help="Environment variable name to update. Repeat for multiple keys.",
    )
    return parser.parse_args()


def env_quote(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def upsert_env_lines(lines: list[str], updates: dict[str, str]) -> list[str]:
    remaining = dict(updates)
    output: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        replaced = False
        for key in list(remaining):
            if stripped.startswith(f"{key}="):
                indent_len = len(line) - len(stripped)
                indent = line[:indent_len]
                output.append(f"{indent}{key}={env_quote(remaining.pop(key))}\n")
                replaced = True
                break
        if not replaced:
            output.append(line)

    if output and not output[-1].endswith("\n"):
        output[-1] += "\n"

    for key, value in remaining.items():
        output.append(f"{key}={env_quote(value)}\n")

    return output


def prompt_for_values(file_path: Path, keys: list[str], existing_keys: set[str]) -> dict[str, str] | None:
    root = tk.Tk()
    root.title("Update .env")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(
        frame,
        text=f"Target file: {file_path}",
        justify="left",
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    entries: dict[str, ttk.Entry] = {}
    for index, key in enumerate(keys, start=1):
        suffix = "replace existing value" if key in existing_keys else "add new value"
        ttk.Label(frame, text=f"{key} ({suffix})").grid(
            row=index * 2 - 1, column=0, columnspan=2, sticky="w", pady=(0, 2)
        )
        entry = ttk.Entry(frame, width=48, show="*")
        entry.grid(row=index * 2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        entries[key] = entry

    result: dict[str, str] | None = {}

    def submit() -> None:
        nonlocal result
        values = {key: entry.get() for key, entry in entries.items()}
        missing = [key for key, value in values.items() if value == ""]
        if missing:
            messagebox.showerror("Missing value", f"Please enter: {', '.join(missing)}")
            return
        result = values
        root.destroy()

    def cancel() -> None:
        nonlocal result
        result = None
        root.destroy()

    button_row = len(keys) * 2 + 1
    ttk.Button(frame, text="Save", command=submit).grid(row=button_row, column=0, sticky="w")
    ttk.Button(frame, text="Cancel", command=cancel).grid(
        row=button_row, column=1, sticky="e"
    )

    root.protocol("WM_DELETE_WINDOW", cancel)
    if keys:
        entries[keys[0]].focus_set()
    root.mainloop()
    return result


def main() -> int:
    args = parse_args()
    file_path = Path(args.file).expanduser()
    keys = list(dict.fromkeys(args.keys))
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        original_text = file_path.read_text(encoding="utf-8")
        original_lines = original_text.splitlines(keepends=True)
    else:
        original_text = ""
        original_lines = []

    existing_keys = {
        line.split("=", 1)[0].strip()
        for line in original_lines
        if "=" in line and not line.lstrip().startswith("#")
    }

    prompt_values = prompt_for_values(file_path, keys, existing_keys)
    if prompt_values is None:
        print("Cancelled. No changes written.")
        return 1

    updated_lines = upsert_env_lines(original_lines, prompt_values)
    updated_text = "".join(updated_lines)

    if file_path.exists() and updated_text != original_text:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        backup_path = file_path.with_name(f"{file_path.name}.{timestamp}.bak")
        shutil.copy2(file_path, backup_path)

    file_path.write_text(updated_text, encoding="utf-8")

    changed_keys = ", ".join(keys)
    print(f"Updated {file_path} for keys: {changed_keys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
