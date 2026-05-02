"""Phase 49 — i18n + 可观测时序 (UX slices)。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


# --- i18n ---

def test_detect_lang_zh():
    from we_together.runtime.prompt_i18n import detect_lang
    assert detect_lang("你好世界") == "zh"


def test_detect_lang_en():
    from we_together.runtime.prompt_i18n import detect_lang
    assert detect_lang("Hello world") == "en"


def test_detect_lang_ja():
    from we_together.runtime.prompt_i18n import detect_lang
    assert detect_lang("こんにちは") == "ja"
    assert detect_lang("カタカナ") == "ja"


def test_detect_lang_empty():
    from we_together.runtime.prompt_i18n import detect_lang, DEFAULT_LANG
    assert detect_lang("") == DEFAULT_LANG
    assert detect_lang(None) == DEFAULT_LANG


def test_normalize_lang_aliases():
    from we_together.runtime.prompt_i18n import normalize_lang
    assert normalize_lang("zh_CN") == "zh"
    assert normalize_lang("en-US") == "en"
    assert normalize_lang("JA") == "ja"
    assert normalize_lang("fr") == "zh"  # fallback 默认


def test_get_prompt_all_languages():
    from we_together.runtime.prompt_i18n import get_prompt
    zh = get_prompt("scene_reply.system", lang="zh", scene_id="s1")
    en = get_prompt("scene_reply.system", lang="en", scene_id="s1")
    ja = get_prompt("scene_reply.system", lang="ja", scene_id="s1")
    assert "s1" in zh
    assert "s1" in en
    assert "s1" in ja
    # 三语确实不同
    assert zh != en != ja


def test_get_prompt_unknown_key():
    import pytest
    from we_together.runtime.prompt_i18n import get_prompt
    with pytest.raises(KeyError, match="unknown prompt key"):
        get_prompt("nonexistent_key", lang="zh")


def test_register_prompt_for_plugin():
    from we_together.runtime.prompt_i18n import get_prompt, register_prompt
    register_prompt("custom.hello", {"zh": "你好 {name}", "en": "Hi {name}"})
    assert get_prompt("custom.hello", lang="zh", name="Alice") == "你好 Alice"
    assert get_prompt("custom.hello", lang="en", name="Alice") == "Hi Alice"


def test_coverage_completeness():
    from we_together.runtime.prompt_i18n import coverage, SUPPORTED_LANGS
    cov = coverage()
    # 至少 scene_reply / self_activation / contradiction 在三语下全覆盖
    core_keys = ["scene_reply.system", "self_activation.prompt", "contradiction.judge"]
    for k in core_keys:
        assert k in cov
        for lang in SUPPORTED_LANGS:
            assert cov[k].get(lang) is True, f"{k} missing {lang}"


# --- SVG 时序 ---

def test_render_sparkline_empty():
    from we_together.observability.time_series_svg import render_sparkline_svg
    svg = render_sparkline_svg([])
    assert "<svg" in svg
    assert "no data" in svg


def test_render_sparkline_with_points():
    from we_together.observability.time_series_svg import render_sparkline_svg
    svg = render_sparkline_svg(
        [("d1", 5), ("d2", 10), ("d3", 3)],
        title="test"
    )
    assert "<svg" in svg
    assert "polyline" in svg
    assert "test" in svg


def test_memory_growth_trend(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.observability.time_series_svg import memory_growth_trend
    import sqlite3
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    for i in range(3):
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', 'x', 0.7, 0.7, 1, 'active', '{}',
               datetime('now'), datetime('now'))""",
            (f"m_trend_{i}",),
        )
    conn.commit()
    conn.close()

    r = memory_growth_trend(db, days=30)
    assert len(r) >= 1
    total = sum(v for _, v in r)
    assert total >= 3


def test_trend_bundle(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.observability.time_series_svg import trend_bundle
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    b = trend_bundle(db, days=7)
    assert "memory_svg" in b
    assert "events_svg" in b
    assert "<svg" in b["memory_svg"]


# --- Webhook alert ---

def test_alert_rule_evaluate():
    from we_together.observability.webhook_alert import AlertRule
    r = AlertRule(metric="x", op=">", threshold=10, url="http://x")
    assert r.evaluate(15) is True
    assert r.evaluate(5) is False


def test_evaluate_returns_matches():
    from we_together.observability.webhook_alert import AlertRule, evaluate
    rules = [
        AlertRule(metric="events_per_day", op=">", threshold=100,
                  url="http://hook", name="high_events"),
        AlertRule(metric="integrity_issues", op=">", threshold=5,
                  url="http://hook2"),
    ]
    m = evaluate({"events_per_day": 200, "integrity_issues": 3}, rules)
    names = {x["rule_name"] for x in m}
    assert "high_events" in names
    assert len(m) == 1


def test_dispatch_dry_run():
    from we_together.observability.webhook_alert import dispatch
    matches = [{
        "rule_name": "r1", "metric": "x", "value": 10,
        "threshold": 5, "op": ">", "url": "http://nonexistent",
    }]
    r = dispatch(matches, dry_run=True)
    assert len(r["sent"]) == 1
    assert r["sent"][0]["dry_run"] is True
    assert r["failed"] == []


def test_parse_rules_from_config():
    from we_together.observability.webhook_alert import parse_rules
    raw = [
        {"metric": "m1", "op": ">", "threshold": 10, "url": "http://x"},
        {"metric": "m2", "op": "<=", "threshold": 0, "url": "http://y",
         "name": "low"},
    ]
    rules = parse_rules(raw)
    assert len(rules) == 2
    assert rules[1].name == "low"
