from pogo.intent import Intent
from pogo.semantic_sketch import SemanticSketch
from pogo.sql_generator import generate_sql


def test_generate_sql_count_by_category():
    sketch = SemanticSketch(
        tables={"t": {"group": {"dtype": "TEXT", "role": "category", "distinct": 2, "non_null": 3}, "value": {"dtype": "INTEGER", "role": "numeric", "distinct": 3, "non_null": 3}}},
        category_columns={"group"},
        numeric_columns={"value"},
        datetime_columns=set(),
        id_columns=set(),
        column_to_tables={"group": ["t"], "value": ["t"]},
    )
    intent = Intent(type="count_by_category", mentions=["group"], confidence=0.8, raw="count")
    sql_plan = generate_sql(intent, sketch, {"t": 3})
    assert "group" in sql_plan.sql
    assert "count" in sql_plan.sql.lower()


def test_generate_sql_compare_groups():
    sketch = SemanticSketch(
        tables={"t": {"group": {"dtype": "TEXT", "role": "category", "distinct": 2, "non_null": 3}, "value": {"dtype": "INTEGER", "role": "numeric", "distinct": 3, "non_null": 3}}},
        category_columns={"group"},
        numeric_columns={"value"},
        datetime_columns=set(),
        id_columns=set(),
        column_to_tables={"group": ["t"], "value": ["t"]},
    )
    intent = Intent(type="compare_groups", mentions=["group", "value"], confidence=0.8, raw="compare")
    sql_plan = generate_sql(intent, sketch, {"t": 3})
    assert "avg" in sql_plan.sql.lower()
