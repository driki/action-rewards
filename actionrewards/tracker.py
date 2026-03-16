"""Lightweight action-reward strategy learner. RL without the ML."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB = Path.home() / ".action-rewards" / "actions.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    action_subtype TEXT,
    action_key TEXT NOT NULL,
    context_json TEXT,
    taken_at TEXT NOT NULL,
    outcome TEXT DEFAULT 'pending',
    outcome_at TEXT,
    reward_score REAL,
    outcome_detail TEXT,
    metrics_before_json TEXT,
    metrics_after_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_pending ON actions(outcome, action_type)
    WHERE outcome = 'pending';
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    condition_json TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    source TEXT DEFAULT 'manual',
    created_at TEXT NOT NULL,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
);
"""


class Tracker:
    """Track automated actions, evaluate outcomes, learn strategy rules."""

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    # ── Record & Resolve ────────────────────────────────────────

    def record(self, action_type, action_key, subtype=None,
               context=None, metrics_before=None):
        """Record an action taken. Returns action ID."""
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO actions (action_type, action_subtype, action_key, "
            "context_json, taken_at, metrics_before_json) VALUES (?,?,?,?,?,?)",
            (action_type, subtype, action_key,
             json.dumps(context) if context else None,
             datetime.now().isoformat(),
             json.dumps(metrics_before) if metrics_before else None),
        )
        conn.commit()
        aid = cur.lastrowid
        conn.close()
        return aid

    def resolve(self, action_id, outcome, reward, detail=None, metrics_after=None):
        """Resolve a pending action with its outcome.

        outcome: success, failure, neutral, reverted
        reward: -1.0 (harmful) to 1.0 (great)
        """
        conn = self._conn()
        conn.execute(
            "UPDATE actions SET outcome=?, outcome_at=?, reward_score=?, "
            "outcome_detail=?, metrics_after_json=? WHERE id=?",
            (outcome, datetime.now().isoformat(), reward, detail,
             json.dumps(metrics_after) if metrics_after else None, action_id),
        )
        conn.commit()
        conn.close()

    def pending(self, action_type=None, max_age_days=7):
        """Get pending actions needing evaluation."""
        conn = self._conn()
        q = "SELECT id, action_type, action_subtype, action_key, context_json, " \
            "taken_at, metrics_before_json FROM actions WHERE outcome='pending'"
        params = []
        if action_type:
            q += " AND action_type=?"
            params.append(action_type)
        if max_age_days:
            cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
            q += " AND taken_at>=?"
            params.append(cutoff)
        rows = conn.execute(q, params).fetchall()
        conn.close()
        return [{"id": r[0], "type": r[1], "subtype": r[2], "key": r[3],
                 "context": json.loads(r[4]) if r[4] else {},
                 "taken_at": r[5],
                 "metrics_before": json.loads(r[6]) if r[6] else {}}
                for r in rows]

    # ── Strategy Weights ────────────────────────────────────────

    def weights(self, action_type):
        """Success rates by subtype. The core learning output."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT action_subtype, outcome, reward_score FROM actions "
            "WHERE action_type=? AND outcome!='pending'", (action_type,),
        ).fetchall()
        conn.close()

        buckets = {}
        for subtype, outcome, reward in rows:
            subtype = subtype or "unknown"
            if subtype not in buckets:
                buckets[subtype] = {"successes": 0, "failures": 0, "n": 0, "reward": 0.0}
            b = buckets[subtype]
            b["n"] += 1
            b["reward"] += reward or 0
            if outcome == "success":
                b["successes"] += 1
            elif outcome in ("failure", "reverted"):
                b["failures"] += 1

        return {
            sub: {
                "success_rate": round(b["successes"] / b["n"], 3) if b["n"] else 0,
                "avg_reward": round(b["reward"] / b["n"], 3) if b["n"] else 0,
                "n": b["n"],
            }
            for sub, b in buckets.items()
        }

    # ── Strategy Rules ──────────────────────────────────────────

    def save_rule(self, action_type, rule_name, condition, action, confidence=0.5):
        """Save or update a strategy rule."""
        conn = self._conn()
        existing = conn.execute(
            "SELECT id FROM rules WHERE action_type=? AND rule_name=?",
            (action_type, rule_name),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE rules SET condition_json=?, recommended_action=?, "
                "confidence=?, created_at=? WHERE id=?",
                (json.dumps(condition), action, confidence,
                 datetime.now().isoformat(), existing[0]),
            )
        else:
            conn.execute(
                "INSERT INTO rules (action_type, rule_name, condition_json, "
                "recommended_action, confidence, created_at) VALUES (?,?,?,?,?,?)",
                (action_type, rule_name, json.dumps(condition), action,
                 confidence, datetime.now().isoformat()),
            )
        conn.commit()
        conn.close()

    def get_rules(self, action_type):
        """Get active rules, highest confidence first."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT rule_name, condition_json, recommended_action, confidence, "
            "success_count, failure_count FROM rules "
            "WHERE action_type=? AND active=1 ORDER BY confidence DESC",
            (action_type,),
        ).fetchall()
        conn.close()
        return [{"name": r[0], "condition": json.loads(r[1]), "action": r[2],
                 "confidence": r[3], "successes": r[4], "failures": r[5]}
                for r in rows]

    def record_rule_outcome(self, action_type, rule_name, success):
        """Update rule stats. Auto-deactivates bad rules."""
        conn = self._conn()
        col = "success_count" if success else "failure_count"
        conn.execute(
            f"UPDATE rules SET {col}={col}+1 WHERE action_type=? AND rule_name=?",
            (action_type, rule_name),
        )
        conn.execute(
            "UPDATE rules SET active=0 WHERE action_type=? AND rule_name=? "
            "AND (success_count+failure_count)>=5 "
            "AND CAST(success_count AS REAL)/(success_count+failure_count)<0.15",
            (action_type, rule_name),
        )
        conn.commit()
        conn.close()

    def match_rule(self, action_type, context):
        """Find the best matching rule for a context. Returns (name, action, confidence) or None."""
        for rule in self.get_rules(action_type):
            match = all(
                (context.get(k) in v if isinstance(v, list) else context.get(k) == v)
                for k, v in rule["condition"].items()
            )
            if match and rule["confidence"] >= 0.3:
                return rule["name"], rule["action"], rule["confidence"]
        return None

    # ── Summary ─────────────────────────────────────────────────

    def summary(self):
        """Overall stats across all action types."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT action_type, outcome, COUNT(*), AVG(reward_score) "
            "FROM actions GROUP BY action_type, outcome"
        ).fetchall()
        rule_count = conn.execute(
            "SELECT COUNT(*) FROM rules WHERE active=1"
        ).fetchone()[0]
        conn.close()

        by_type = {}
        for atype, outcome, count, avg_reward in rows:
            if atype not in by_type:
                by_type[atype] = {}
            by_type[atype][outcome] = {"count": count, "avg_reward": round(avg_reward or 0, 3)}

        return {"by_type": by_type, "active_rules": rule_count}
