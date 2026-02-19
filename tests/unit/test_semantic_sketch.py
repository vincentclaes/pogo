from pathlib import Path

from pogo.ingestion import load_dataset
from pogo.profiling import profile_dataset
from pogo.semantic_sketch import build_semantic_sketch


def test_semantic_sketch_roles(tmp_path: Path):
    data = tmp_path / "data.csv"
    data.write_text("sample_id,group,value\nS1,A,10\nS2,A,12\nS3,B,7\n")

    con, tables = load_dataset(data)
    profiles = profile_dataset(con, [t.name for t in tables])
    sketch = build_semantic_sketch(profiles)

    assert "value" in sketch.numeric_columns
    assert "group" in sketch.category_columns
    assert "sample_id" in sketch.id_columns
