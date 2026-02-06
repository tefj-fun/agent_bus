#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${ROOT_DIR}/scripts/pandoc/template.html"
CSS="${ROOT_DIR}/scripts/pandoc/a4-print.css"
MERMAID_RENDER="${ROOT_DIR}/scripts/render_mermaid.py"

INPUT_DIR="${1:-${ROOT_DIR}/outputs}"
OUTPUT_DIR="${2:-${ROOT_DIR}/outputs_pdfs}"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "pandoc not found. Install pandoc and wkhtmltopdf to use this script."
  exit 1
fi

DEFAULT_ENGINE="weasyprint"
PDF_ENGINE="${PANDOC_PDF_ENGINE:-$DEFAULT_ENGINE}"

if ! command -v "${PDF_ENGINE}" >/dev/null 2>&1; then
  echo "${PDF_ENGINE} not found. Install it or set PANDOC_PDF_ENGINE to another engine."
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

find "${INPUT_DIR}" -type f -name "*.md" | while read -r md_file; do
  rel_path="${md_file#${INPUT_DIR}/}"
  base_name="$(basename "${rel_path}" .md)"
  out_dir="${OUTPUT_DIR}/$(dirname "${rel_path}")"
  mkdir -p "${out_dir}"
  out_pdf="${out_dir}/${base_name}.pdf"

  tmp_dir="$(mktemp -d)"
  tmp_md="${tmp_dir}/${base_name}.md"
  assets_dir="${tmp_dir}/assets"
  mkdir -p "${assets_dir}"

  python3 "${MERMAID_RENDER}" "${md_file}" "${tmp_md}" "${assets_dir}"

  pandoc "${tmp_md}" \
    --from gfm+pipe_tables+yaml_metadata_block \
    --to html5 \
    --template "${TEMPLATE}" \
    --css "${CSS}" \
    --standalone \
    --resource-path "${assets_dir}:${tmp_dir}:${INPUT_DIR}" \
    --metadata title="${base_name}" \
    --metadata date="$(date '+%Y-%m-%d')" \
    --metadata footer_left="agent_bus PRD" \
    --metadata status="Draft" \
    --metadata owner="agent_bus" \
    --metadata target_release="TBD" \
    --metadata last_updated="$(date '+%Y-%m-%d')" \
    --pdf-engine "${PDF_ENGINE}" \
    -o "${out_pdf}"

  rm -rf "${tmp_dir}"

  echo "Generated ${out_pdf}"
done
