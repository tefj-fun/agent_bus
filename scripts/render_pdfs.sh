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

# Render all markdown-like artifacts. Some agents write markdown to .txt (e.g. pm_review.txt),
# while feature_tree*.txt contains JSON/mermaid payloads that we wrap into code fences.
find "${INPUT_DIR}" -type f \( -name "*.md" -o -name "*.txt" \) | while read -r md_file; do
  rel_path="${md_file#${INPUT_DIR}/}"
  base_name="$(basename "${rel_path}")"
  base_name="${base_name%.*}"
  out_dir="${OUTPUT_DIR}/$(dirname "${rel_path}")"
  mkdir -p "${out_dir}"
  out_pdf="${out_dir}/${base_name}.pdf"

  artifact_type="${base_name}"
  if [[ "${artifact_type}" =~ ^(.+)_v[0-9]+$ ]]; then
    artifact_type="${BASH_REMATCH[1]}"
  fi

  tmp_dir="$(mktemp -d)"
  tmp_md="${tmp_dir}/${base_name}.md"
  tmp_src="${tmp_dir}/${base_name}_src.md"
  assets_dir="${tmp_dir}/assets"
  mkdir -p "${assets_dir}"

  src_file="${md_file}"
  if [[ "${md_file}" == *.txt ]]; then
    if [[ "${base_name}" == feature_tree_graph* ]]; then
      printf "```mermaid\n%s\n```\n" "$(cat "${md_file}")" > "${tmp_src}"
      src_file="${tmp_src}"
    elif [[ "${base_name}" == feature_tree* ]]; then
      printf "```json\n%s\n```\n" "$(cat "${md_file}")" > "${tmp_src}"
      src_file="${tmp_src}"
    else
      # Treat arbitrary .txt artifacts as markdown (common for pm_review.txt).
      src_file="${md_file}"
    fi
  fi

  python3 "${MERMAID_RENDER}" "${src_file}" "${tmp_md}" "${assets_dir}"

  extra_meta=()
  # The cover page is useful for large docs, but for short review artifacts it looks like a blank first page.
  if [[ "${artifact_type}" == "pm_review" ]]; then
    extra_meta+=(--metadata no_cover=true)
  fi

  pandoc "${tmp_md}" \
    --from gfm+pipe_tables+yaml_metadata_block \
    --to html5 \
    --template "${TEMPLATE}" \
    --css "${CSS}" \
    --standalone \
    --resource-path "${assets_dir}:${tmp_dir}:${INPUT_DIR}" \
    --metadata title="${base_name}" \
    --metadata artifact_type="${artifact_type}" \
    --metadata date="$(date '+%Y-%m-%d')" \
    --metadata footer_left="agent_bus PRD" \
    --metadata status="Draft" \
    --metadata owner="agent_bus" \
    --metadata target_release="TBD" \
    --metadata last_updated="$(date '+%Y-%m-%d')" \
    "${extra_meta[@]}" \
    --pdf-engine "${PDF_ENGINE}" \
    -o "${out_pdf}"

  rm -rf "${tmp_dir}"

  echo "Generated ${out_pdf}"
done
