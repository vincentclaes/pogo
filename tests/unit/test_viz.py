from pathlib import Path

import pandas as pd

from pogo.viz import generate_plots


def test_generate_plots(tmp_path: Path):
    df = pd.DataFrame({"group": ["A", "B"], "value": [1, 2]})
    plots = generate_plots(df, tmp_path)
    assert plots
    assert all(p.path.exists() for p in plots)
