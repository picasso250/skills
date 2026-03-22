---
name: read-document-files
description: Read local document files into plain text with a reusable Python script. Use when Codex needs to inspect or summarize PDF, DOCX, XLSX, or PPTX files, convert them into text for downstream analysis, or extract embedded DOCX images so they can be analyzed separately.
---

# Read Document Files

Use the bundled script to convert supported documents into UTF-8 `.txt` files that are easier to read, summarize, diff, or feed into downstream tooling.

Prefer this skill before writing ad hoc one-off extraction code.

## Quick Start

Run the extractor on a local file:

```powershell
python .\scripts\extract_to_txt.py C:\path\to\file.docx
```

Print the extracted text to stdout instead of reading the output file afterward:

```powershell
python .\scripts\extract_to_txt.py C:\path\to\slides.pptx --stdout
```

## Supported Formats

- `docx`: extract paragraph text and tables from OOXML; also extract files under `word/media/`
- `xlsx`: extract workbook text sheet by sheet
- `pptx`: extract slide text in slide order
- `pdf`: extract text when `pypdf` or `PyPDF2` is installed

Legacy binary Office formats such as `xls` are not parsed directly by this script. Convert them to `xlsx` first or install a dedicated converter when needed.

## Workflow

1. Run `scripts/extract_to_txt.py` on the target file.
2. Read the generated `.txt` file for summarization, search, or downstream transformation.
3. If the output metadata says a DOCX contains images, inspect the exported files under `<stem>_assets\images\`.
4. If those images matter to the task, hand them to a vision-capable step or image-analysis workflow instead of ignoring them.

## Output Contract

The script writes:

- `<stem>.txt`: extracted plain text
- `<stem>.meta.json`: format, warnings, and extracted asset metadata
- `<stem>_assets\images\...`: only when embedded DOCX images exist

The metadata file includes a guidance note when embedded images were exported so another agent can continue with image analysis explicitly.

## Notes

- Keep the original source file; this skill is for reading, not editing.
- For scanned PDFs without embedded text, OCR is still required. The script will not invent text.
- For huge spreadsheets, extract once and search the `.txt` result instead of reopening the workbook repeatedly.
- Read [format-notes.md](./references/format-notes.md) only when you need details on format coverage, fallbacks, or output layout.
