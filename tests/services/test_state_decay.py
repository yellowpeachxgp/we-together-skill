from datetime import UTC, datetime, timedelta
import json
import sqlite3

import pytest

from we_together.db.bootstrap import bootstrap_project
from we_together.services.state_decay_service import (
    decay_states,
    _decay_confidence,
    _parse_policy,
)


def _seed_state(
    db_path,
    *,
    state_id,
    confidence,
    decay_policy,
    age_days,
    state_type="mood",
    scope_id="scene_decay",
):
    conn = sqlite3.connect(db_path)
    updated_at = (datetime.now(UTC) - timedelta(days=age_days)).isoformat()
    conn.execute(
        """
        INSERT INTO states(
            state_id, scope_type, scope_id, state_type, value_json,
            confidence, is_inferred, decay_policy, source_event_refs_json,
            created_at, updated_at
        ) VALUES(?, 'scene', ?, ?, ?, ?, 1, ?, '[]', ?, ?)
        """,
        (state_id, scope_id, state_type, json.dumps({"mood": "x"}), confidence,
         decay_policy, updated_at, updated_at),
    )
    conn.commit()
    conn.close()


def test_parse_policy_linear():
    kind, params = _parse_policy("linear:per_day=0.02")
    assert kind == "linear"
    assert params == {"per_day": 0.02}


def test_parse_policy_none():
    assert _parse_policy(None) == ("none", {})
    assert _parse_policy("none") == ("none", {})


def test_decay_confidence_linear():
    assert _decay_confidence(0.8, age_days=10, policy="linear:per_day=0.05") == pytest.approx(0.3)


def test_decay_confidence_exponential_halflife():
    assert _decay_confidence(1.0, age_days=14, policy="exponential:half_life_days=14") == 0.5


def test_decay_confidence_step():
    assert _decay_confidence(0.9, age_days=15, policy="step:after_days=30,to=0.1") == 0.9
    assert _decay_confidence(0.9, age_days=45, policy="step:after_days=30,to=0.1") == 0.1


def test_decay_states_updates_confidence(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_state(
        db_path, state_id="state_dec1", confidence=0.9,
        decay_policy="linear:per_day=0.05", age_days=10,
    )

    result = decay_states(db_path)
    assert result["decayed_count"] == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT confidence FROM states WHERE state_id = 'state_dec1'").fetchone()
    conn.close()
    assert row[0] < 0.9


def test_decay_states_records_low_confidence(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_state(
        db_path, state_id="state_dec_low", confidence=0.2,
        decay_policy="linear:per_day=0.1", age_days=5,
    )

    result = decay_states(db_path, threshold=0.1)
    assert "state_dec_low" in result["deactivated_state_ids"]


def test_decay_states_skips_none_policy(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_state(
        db_path, state_id="state_stable", confidence=0.5,
        decay_policy=None, age_days=100,
    )

    result = decay_states(db_path)
    assert result["decayed_count"] == 0
