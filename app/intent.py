from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List

from .semantic_sketch import SemanticSketch


@dataclass
class Intent:
    type: str
    mentions: List[str]
    confidence: float
    raw: str
    entity: str | None = None


KEYWORDS = {
    "overview": ["overview", "summary", "describe", "profile"],
    "differential": ["upregulated", "downregulated", "differential", "fold change"],
    "compare_groups": ["compare", "difference", "between"],
    "count_by_category": ["how many", "count", "counts"],
    "gene_lookup": ["gene"],
}


def _extract_mentions(text: str, sketch: SemanticSketch) -> List[str]:
    mentions = []
    text_lower = text.lower()
    for col in sketch.column_to_tables.keys():
        if col.lower() in text_lower:
            mentions.append(col)
    return mentions


def _extract_entity(text: str) -> str | None:
    match = re.search(r"gene\s+([A-Za-z0-9_.-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def infer_intent(user_text: str, sketch: SemanticSketch) -> Intent:
    text_lower = user_text.lower()
    intent_type = "overview"
    for name, words in KEYWORDS.items():
        if any(word in text_lower for word in words):
            intent_type = name
            break

    mentions = _extract_mentions(user_text, sketch)
    entity = _extract_entity(user_text)

    confidence = 0.45
    if mentions:
        confidence += 0.25
    if intent_type != "overview":
        confidence += 0.1
    if entity:
        confidence += 0.1
    confidence = min(confidence, 0.95)

    return Intent(type=intent_type, mentions=mentions, confidence=confidence, raw=user_text, entity=entity)
