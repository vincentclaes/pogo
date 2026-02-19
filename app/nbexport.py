from __future__ import annotations

import base64
from pathlib import Path
from typing import Tuple

import nbconvert


def export_markdown_with_images(input_path: Path, output_path: Path) -> None:
    exporter = nbconvert.MarkdownExporter()
    body, resources = exporter.from_filename(
        str(input_path),
        resources={"output_files_dir": "_md_images"},
    )

    output_files_dir = resources.get("output_files_dir", "_md_images")
    outputs_dir = output_path.parent / output_files_dir
    outputs_dir.mkdir(parents=True, exist_ok=True)

    attachments = resources.get("outputs", {})
    for name, data in attachments.items():
        rel = Path(name)
        if rel.parts and rel.parts[0] == output_files_dir:
            rel = Path(*rel.parts[1:])
        target = outputs_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            target.write_bytes(data)
        elif isinstance(data, str):
            try:
                target.write_bytes(base64.b64decode(data))
            except Exception:
                target.write_text(data)
        else:
            try:
                target.write_bytes(data)
            except Exception:
                continue

    for name in attachments.keys():
        rel = Path(name)
        if rel.parts and rel.parts[0] == output_files_dir:
            rel = Path(*rel.parts[1:])
        rel_str = str(rel).replace("\\", "/")
        if f"]({name})" in body:
            body = body.replace(f"]({name})", f"]({output_files_dir}/{rel_str})")
        if f"]({rel_str})" in body:
            body = body.replace(f"]({rel_str})", f"]({output_files_dir}/{rel_str})")
        if f'src="{name}"' in body:
            body = body.replace(f'src="{name}"', f'src="{output_files_dir}/{rel_str}"')
        if f'src="{rel_str}"' in body:
            body = body.replace(f'src="{rel_str}"', f'src="{output_files_dir}/{rel_str}"')
    output_path.write_text(body)
