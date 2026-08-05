"""Multi-block advanced search combination (Refine/Extend) - BYNT-1760.

Blocks must be grouped: each block's conditions AND-ed together before the
block's op (and/or) combines it with the accumulated query.
"""

import re

from enferno.utils.search_utils import SearchUtils


def compiled(q, cls):
    stmt = SearchUtils(q, cls).get_query()
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def test_or_groups_block_conditions():
    # Block 2 has two conditions; they must stay AND-ed inside the OR,
    # not be flattened into independent OR operands.
    # AND binds tighter than OR, so correct grouping renders as
    # "id IN (1) OR id IN (2) AND originid ...". The old flattening
    # bug joined originid with OR instead.
    sql = compiled(
        [{"ids": [1]}, {"op": "or", "ids": [2], "originid": "x"}],
        "bulletin",
    )
    assert "AND lower(bulletin.originid)" in sql
    assert "OR lower(bulletin.originid)" not in sql


def test_chained_or_keeps_all_blocks():
    # Regression: the middle OR block used to be silently dropped.
    sql = compiled(
        [{"ids": [1]}, {"op": "or", "ids": [2]}, {"op": "or", "ids": [3]}],
        "actor",
    )
    for n in (1, 2, 3):
        assert f"IN ({n})" in sql


def test_and_after_or_applies_to_combined_result():
    # (block1 OR block2) AND block3
    sql = compiled(
        [{"ids": [1]}, {"op": "or", "ids": [2]}, {"op": "and", "ids": [3]}],
        "bulletin",
    )
    assert re.search(r"\(.*IN \(1\).*OR.*IN \(2\).*\).*AND.*IN \(3\)", sql, re.DOTALL)
