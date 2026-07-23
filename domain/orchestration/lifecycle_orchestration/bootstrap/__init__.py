"""Bootstrap rules for a concrete digital-life instance."""

from __future__ import annotations

import json
from typing import Iterable, Optional


LIFE_AFFAIR_GOAL = "维持数字生命运行，主动推进目标。"
LIFE_AFFAIR_PRIORITY = 10


def parse_meta_json(raw: str | None) -> dict:
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


def is_life_affair_meta(meta: dict) -> bool:
    return bool(meta.get("life"))


def find_life_affair_id(rows: Iterable) -> Optional[str]:
    """Find the first affair row marked as the digital-life root affair."""
    for row in rows:
        meta = parse_meta_json(row["meta_json"])
        if is_life_affair_meta(meta):
            return row["affair_id"]
    return None


def life_affair_metadata(now_iso: str) -> dict:
    return {"life": True, "created_by": "init_life", "born_at": now_iso}


__all__ = [
    "LIFE_AFFAIR_GOAL",
    "LIFE_AFFAIR_PRIORITY",
    "find_life_affair_id",
    "is_life_affair_meta",
    "life_affair_metadata",
    "parse_meta_json",
]
