# biosignal

Dataset-agnostic generative BI app for bioinformatics.

## Quickstart
```bash
uv sync --dev
python -m app.cli --dataset tests/fixtures/airway --prompt "Give me an overview of the data." --out output/session
```

## Tests
```bash
pytest tests/test_e2e_airway.py
```
