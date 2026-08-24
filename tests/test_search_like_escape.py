"""SQL LIKE wildcards in user input must be matched literally.

Searching for "15%" or "case_1" used to be interpreted by Postgres as a
wildcard pattern, returning a superset of the intended results.
"""

from enferno.utils.search_utils import SearchUtils, escape_like


def compiled(q, cls):
    return SearchUtils(q, cls).get_query().compile()


def patterns(compiled_stmt):
    return [v for v in compiled_stmt.params.values() if isinstance(v, str)]


def test_escape_like_escapes_wildcards_and_backslash():
    assert escape_like("15%") == r"15\%"
    assert escape_like("case_1") == r"case\_1"
    assert escape_like(r"a\b") == r"a\\b"
    assert escape_like("plain") == "plain"


def test_bulletin_originid_escapes_percent():
    stmt = compiled([{"originid": "15%"}], "bulletin")
    assert r"%15\%%" in patterns(stmt)
    assert "ESCAPE" in str(stmt)


def test_actor_originid_escapes_underscore():
    stmt = compiled([{"originid": "case_1"}], "actor")
    assert r"%case\_1%" in patterns(stmt)
    assert "ESCAPE" in str(stmt)


def test_incident_text_search_escapes_underscore():
    stmt = compiled({"tsv": "case_1"}, "incident")
    assert r"%case\_1%" in patterns(stmt)
    assert "ESCAPE" in str(stmt)
