# Format Notes

## Coverage

- `docx`: parsed from the OOXML zip package with `zipfile` and `xml.etree.ElementTree`
- `xlsx`: prefers `openpyxl` when available, otherwise falls back to direct OOXML parsing
- `pptx`: parsed from the OOXML zip package and slide XML
- `pdf`: requires `pypdf` or `PyPDF2`

## DOCX Images

DOCX is a zip container. Embedded images usually live under `word/media/`.

The extractor copies those images into the output assets folder and records them in the metadata file. When images are present, treat the `.txt` output as incomplete semantic coverage and explicitly inspect the extracted images if charts, screenshots, handwritten notes, or scanned inserts may matter.

## XLSX Output Shape

Each worksheet is emitted in its own section. Rows are flattened as `col=value` pairs when headers exist; otherwise the row is emitted as a tab-joined line.

This is intentionally text-first, not round-trip faithful. The goal is readable analysis, not spreadsheet reconstruction.

## PDF Limits

If the PDF is image-only, encrypted, or malformed, plain-text extraction may fail or return partial text. The metadata file records warnings so the next step can decide whether OCR or a different tool is required.
