import pytest
from actionrewards.tracker import Tracker

@pytest.fixture
def t(tmp_path):
    return Tracker(db_path=str(tmp_path / "test.db"))

def test_record(t):
    assert t.record("deploy", "v1.2.3") == 1

def test_record_with_context(t):
    aid = t.record("deploy", "v1.2.3", subtype="canary",
                   context={"region": "us-east", "instances": 3})
    assert aid >= 1

def test_resolve(t):
    aid = t.record("deploy", "v1.2.3")
    t.resolve(aid, "success", 0.9, detail="No errors after 1h")
    pending = t.pending("deploy")
    assert len(pending) == 0

def test_pending(t):
    t.record("deploy", "v1")
    t.record("deploy", "v2")
    assert len(t.pending("deploy")) == 2

def test_weights(t):
    for i in range(5):
        aid = t.record("deploy", f"v{i}", subtype="canary")
        t.resolve(aid, "success" if i < 4 else "failure", 0.8 if i < 4 else -0.5)
    w = t.weights("deploy")
    assert w["canary"]["success_rate"] == 0.8
    assert w["canary"]["n"] == 5

def test_save_and_get_rules(t):
    t.save_rule("deploy", "avoid_friday", {"day": "friday"}, "defer_to_monday", 0.8)
    rules = t.get_rules("deploy")
    assert len(rules) == 1
    assert rules[0]["name"] == "avoid_friday"

def test_match_rule(t):
    t.save_rule("deploy", "avoid_friday", {"day": "friday"}, "defer_to_monday", 0.8)
    m = t.match_rule("deploy", {"day": "friday", "region": "us-east"})
    assert m is not None
    assert m[1] == "defer_to_monday"

def test_match_rule_no_match(t):
    t.save_rule("deploy", "avoid_friday", {"day": "friday"}, "defer", 0.8)
    assert t.match_rule("deploy", {"day": "tuesday"}) is None

def test_rule_deactivation(t):
    t.save_rule("deploy", "bad_rule", {"x": "y"}, "skip", 0.5)
    for _ in range(5):
        t.record_rule_outcome("deploy", "bad_rule", success=False)
    assert len(t.get_rules("deploy")) == 0

def test_rule_survives_good_performance(t):
    t.save_rule("deploy", "good_rule", {"x": "y"}, "go", 0.8)
    for _ in range(4):
        t.record_rule_outcome("deploy", "good_rule", success=True)
    t.record_rule_outcome("deploy", "good_rule", success=False)
    assert len(t.get_rules("deploy")) == 1

def test_summary(t):
    aid = t.record("deploy", "v1")
    t.resolve(aid, "success", 0.8)
    s = t.summary()
    assert "deploy" in s["by_type"]
    assert s["active_rules"] == 0
