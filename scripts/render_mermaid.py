#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from pathlib import Path


MERMAID_BLOCK_RE = re.compile(r"```mermaid\\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def render_mermaid_block(mmd: str, out_dir: Path) -> str:
    digest = hashlib.sha256(mmd.encode("utf-8")).hexdigest()[:12]
    mmd_path = out_dir / f"diagram_{digest}.mmd"
    svg_path = out_dir / f"diagram_{digest}.svg"
    mmd_path.write_text(mmd, encoding="utf-8")
    subprocess.run(
        ["mmdc", "-i", str(mmd_path), "-o", str(svg_path), "-b", "transparent"],
        check=True,
    )
    return svg_path.name


def main() -> None:
    parser = argparse.ArgumentParser(description="Render mermaid code fences to SVGs.")
    parser.add_argument("input_md", help="Input markdown file")
    parser.add_argument("output_md", help="Output markdown file")
    parser.add_argument("assets_dir", help="Directory to write SVG assets")
    args = parser.parse_args()

    input_path = Path(args.input_md)
    output_path = Path(args.output_md)
    assets_dir = Path(args.assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    content = input_path.read_text(encoding="utf-8")
    replacements = []

    for match in MERMAID_BLOCK_RE.finditer(content):
        block = match.group(1).strip()
        if not block:
            continue
        svg_name = render_mermaid_block(block, assets_dir)
        replacements.append((match.span(), f"![]({svg_name})"))

    if replacements:
        # Apply replacements from end to start to preserve indices
        new_content = content
        for (start, end), replacement in reversed(replacements):
            new_content = new_content[:start] + replacement + new_content[end:]
        output_path.write_text(new_content, encoding="utf-8")
    else:
        output_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
