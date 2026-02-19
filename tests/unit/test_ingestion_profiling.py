from pathlib import Path

from pogo.ingestion import load_dataset
from pogo.profiling import profile_dataset


def test_ingestion_and_profiling(tmp_path: Path):
    data = tmp_path / "data.csv"
    data.write_text("id,group,value\n1,A,10\n2,A,12\n3,B,7\n")

    con, tables = load_dataset(data)
    assert len(tables) == 1
    assert tables[0].name == "data"

    profiles = profile_dataset(con, [tables[0].name])
    profile = profiles[tables[0].name]
    assert profile.row_count == 3
    assert "id" in profile.columns
    assert "group" in profile.columns
    assert "value" in profile.columns
