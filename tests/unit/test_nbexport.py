import base64
import json
from pathlib import Path

from app.nbexport import export_markdown_with_images

_MIN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


def _write_min_notebook(path: Path) -> None:
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": 1,
                "id": "cell-1",
                "outputs": [
                    {
                        "output_type": "display_data",
                        "data": {"image/png": base64.b64encode(_MIN_PNG).decode("ascii")},
                        "metadata": {},
                    }
                ],
                "source": ["# image output\n"],
            }
        ],
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb))


def test_export_markdown_with_images(tmp_path: Path):
    ipynb = tmp_path / "in.ipynb"
    md = tmp_path / "out.md"
    _write_min_notebook(ipynb)

    export_markdown_with_images(ipynb, md)
    assert md.exists()

    images_dir = tmp_path / "_md_images"
    assert images_dir.exists()
    assert any(p.suffix == ".png" for p in images_dir.iterdir())

    content = md.read_text()
    assert "_md_images/" in content
