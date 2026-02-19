from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .intent import Intent
from .semantic_sketch import SemanticSketch


@dataclass
class QueryPlan:
    sql: str
    description: str
    tables: List[str]


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _find_primary_table(profiles: Dict[str, int]) -> str:
    return max(profiles, key=lambda key: profiles[key])


def _find_column_by_role(sketch: SemanticSketch, role_set: set, mentions: List[str]) -> str | None:
    for m in mentions:
        if m in role_set:
            return m
    for col in role_set:
        return col
    return None


def _find_preferred_numeric(sketch: SemanticSketch, mentions: List[str]) -> str | None:
    preferred = ["count", "counts", "value", "expression", "amount"]
    for m in mentions:
        if m in sketch.numeric_columns:
            return m
    for name in preferred:
        for col in sketch.numeric_columns:
            if name in col.lower():
                return col
    for col in sketch.numeric_columns:
        return col
    return None


def _find_de_table(sketch: SemanticSketch) -> Tuple[str, str, str] | None:
    for table, cols in sketch.tables.items():
        col_names = {c.lower(): c for c in cols.keys()}
        if "log2fc" in col_names and ("gene_id" in col_names or "gene" in col_names):
            gene_col = col_names.get("gene_id") or col_names.get("gene")
            log2fc_col = col_names.get("log2fc")
            if gene_col and log2fc_col:
                return table, gene_col, log2fc_col
    return None


def _find_gene_column(sketch: SemanticSketch) -> str | None:
    for table, cols in sketch.tables.items():
        for col in cols.keys():
            if col.lower() in {"gene_id", "gene", "symbol"}:
                return col
    return None


def _find_table_for_column(sketch: SemanticSketch, col: str) -> str | None:
    tables = sketch.column_to_tables.get(col)
    if tables:
        return tables[0]
    return None


def _find_join_key(sketch: SemanticSketch, left: str, right: str) -> str | None:
    left_cols = set(sketch.tables[left].keys())
    right_cols = set(sketch.tables[right].keys())
    shared = list(left_cols.intersection(right_cols))
    if not shared:
        return None
    for col in shared:
        if col in sketch.id_columns:
            return col
    return shared[0]


def generate_sql(intent: Intent, sketch: SemanticSketch, table_row_counts: Dict[str, int]) -> QueryPlan:
    primary = _find_primary_table(table_row_counts)

    if intent.type == "overview":
        sql = f"select * from {_q(primary)} limit 20"
        return QueryPlan(sql=sql, description="Preview top rows", tables=[primary])

    if intent.type == "count_by_category":
        category = _find_column_by_role(sketch, sketch.category_columns, intent.mentions)
        if not category:
            sql = f"select * from {_q(primary)} limit 20"
            return QueryPlan(sql=sql, description="Preview top rows", tables=[primary])
        table = _find_table_for_column(sketch, category) or primary
        sql = (
            f"select {_q(category)} as category, count(*) as n "
            f"from {_q(table)} group by {_q(category)} order by n desc limit 20"
        )
        return QueryPlan(sql=sql, description="Count by category", tables=[table])

    if intent.type == "differential":
        de_info = _find_de_table(sketch)
        if de_info:
            de_table, gene_col, log2fc_col = de_info
            sql = (
                f"select {_q(gene_col)} as gene, {_q(log2fc_col)} as log2fc "
                f"from {_q(de_table)} order by log2fc desc limit 20"
            )
            return QueryPlan(sql=sql, description="Top differential genes", tables=[de_table])

    if intent.type == "gene_lookup":
        gene_col = _find_gene_column(sketch)
        if gene_col and intent.entity:
            table = _find_table_for_column(sketch, gene_col) or primary
            sql = (
                f"select * from {_q(table)} where {_q(gene_col)} = '{intent.entity}' limit 50"
            )
            return QueryPlan(sql=sql, description="Gene lookup", tables=[table])

    if intent.type in {"compare_groups", "differential"}:
        category = _find_column_by_role(sketch, sketch.category_columns, intent.mentions)
        numeric = _find_preferred_numeric(sketch, intent.mentions)
        if not category or not numeric:
            sql = f"select * from {_q(primary)} limit 20"
            return QueryPlan(sql=sql, description="Preview top rows", tables=[primary])

        table_cat = _find_table_for_column(sketch, category) or primary
        table_num = _find_table_for_column(sketch, numeric) or primary

        if table_cat == table_num:
            sql = (
                f"select {_q(category)} as category, avg({_q(numeric)}) as mean_value "
                f"from {_q(table_num)} group by {_q(category)} order by mean_value desc limit 20"
            )
            return QueryPlan(sql=sql, description="Compare groups", tables=[table_num])

        join_key = _find_join_key(sketch, table_num, table_cat)
        if not join_key:
            sql = f"select * from {_q(primary)} limit 20"
            return QueryPlan(sql=sql, description="Preview top rows", tables=[primary])

        sql = (
            f"select b.{_q(category)} as category, avg(a.{_q(numeric)}) as mean_value "
            f"from {_q(table_num)} a join {_q(table_cat)} b on a.{_q(join_key)} = b.{_q(join_key)} "
            f"group by b.{_q(category)} order by mean_value desc limit 20"
        )
        return QueryPlan(sql=sql, description="Compare groups", tables=[table_num, table_cat])

    sql = f"select * from {_q(primary)} limit 20"
    return QueryPlan(sql=sql, description="Preview top rows", tables=[primary])
