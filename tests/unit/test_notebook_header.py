from pathlib import Path

from pogo.notebook_builder import NotebookBuilder, NotebookRecorder


def test_header_inserts_sections(tmp_path: Path):
    builder = NotebookBuilder(title="Demo")
    builder.add_title_block()
    builder.add_header(
        tldr="Short summary",
        summary="Longer summary",
        prompts=[("What?", "Answer")],
        steps=["Step one", "Step two"],
        title="Custom Title",
    )

    assert builder.cells[0]["source"][0].startswith("# Custom Title")
    texts = ["".join(cell.get("source", [])) for cell in builder.cells]
    assert any("## TL;DR" in t for t in texts)
    assert any("## Summary" in t for t in texts)
    assert any("## Prompts Used" in t for t in texts)
    assert any("## Steps to Run" in t for t in texts)


def test_finalize_paths_renames_file(tmp_path: Path):
    path = tmp_path / "session.ipynb"
    recorder = NotebookRecorder(path=path, title="session")
    recorder.builder.write(path)
    recorder.append_header(
        tldr="t",
        summary="s",
        prompts=[("p", "a")],
        steps=["run"],
        title="My New Title",
    )
    new_path = recorder.finalize_paths()
    assert new_path.name == "my-new-title.ipynb"
    assert new_path.exists()
