"""known_relatives round-trips through ActorProfile like reporters."""

from enferno.admin.models import ActorProfile


def test_known_relatives_roundtrip(session):
    relatives = [{"name": "A", "contact": "+1 555", "relationship": "brother"}]
    profile = ActorProfile().from_json({"mode": 3, "known_relatives": relatives, "reporters": []})
    assert profile.known_relatives == relatives
    assert profile.to_dict()["known_relatives"] == relatives
    assert profile.to_dict()["reporters"] == []
