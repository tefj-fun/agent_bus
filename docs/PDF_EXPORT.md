# PDF Export (Pandoc)

This repo includes a batch renderer that converts all generated `.md` artifacts into A4 print-ready PDFs.

## Requirements
- `pandoc`
- `weasyprint` (default PDF engine)

You can override the PDF engine by setting `PANDOC_PDF_ENGINE`.

## Usage

```bash
./scripts/render_pdfs.sh /path/to/outputs /path/to/outputs_pdfs
```

Defaults:
- Input: `./outputs`
- Output: `./outputs_pdfs`

## PDF Preview in UI

The UI can preview PDFs via `GET /api/artifacts/pdf/{artifact_id}`.
This endpoint serves PDFs from the directory configured by `ARTIFACT_PDF_OUTPUT_DIR`
(default `./outputs_pdfs`). Generate PDFs first, then the preview will render.

## Styling

Template and CSS:
- `scripts/pandoc/template.html`
- `scripts/pandoc/a4-print.css`

The CSS enforces A4 page size and a print-friendly typographic layout.
