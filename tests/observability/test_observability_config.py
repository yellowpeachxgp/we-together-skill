import io
import json
import logging

from we_together.config.loader import WeTogetherConfig, load_config
from we_together.errors import (
    ConfigError,
    IngestError,
    PatchError,
    RetrievalError,
    SchemaVersionError,
    WeTogetherError,
)
from we_together.observability.logger import (
    _JsonFormatter,
    bind_trace_id,
    get_logger,
    get_trace_id,
    log_event,
)
from we_together.observability.metrics import (
    counter_inc,
    export_prometheus_text,
    gauge_set,
    get_counter,
    get_gauge,
    reset,
)


# --- Logger ---

def test_trace_id_bind_and_get():
    tid = bind_trace_id("abc123")
    assert tid == "abc123"
    assert get_trace_id() == "abc123"


def test_logger_outputs_json_with_trace_id():
    bind_trace_id("tid_test")
    log = get_logger("module_x")
    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(_JsonFormatter())
    log.addHandler(h)
    log_event(log, "test_event", value=42)
    line = stream.getvalue().strip().split("\n")[-1]
    payload = json.loads(line)
    assert payload["trace_id"] == "tid_test"
    assert payload["event"] == "test_event"
    assert payload["value"] == 42


# --- Metrics ---

def test_counter_increment_and_export():
    reset()
    counter_inc("patches_applied", labels={"op": "create_memory"})
    counter_inc("patches_applied", labels={"op": "create_memory"})
    counter_inc("patches_applied", labels={"op": "update_entity"})
    assert get_counter("patches_applied", {"op": "create_memory"}) == 2.0
    text = export_prometheus_text()
    assert 'patches_applied{op="create_memory"} 2.0' in text


def test_gauge_set():
    reset()
    gauge_set("cache_size", 42)
    assert get_gauge("cache_size") == 42
    text = export_prometheus_text()
    assert "cache_size 42" in text


# --- Errors ---

def test_error_hierarchy():
    assert issubclass(IngestError, WeTogetherError)
    assert issubclass(RetrievalError, WeTogetherError)
    assert issubclass(PatchError, WeTogetherError)
    assert issubclass(ConfigError, WeTogetherError)
    assert issubclass(SchemaVersionError, WeTogetherError)


# --- Config ---

def test_load_config_defaults_with_no_file():
    cfg = load_config(None)
    assert isinstance(cfg, WeTogetherConfig)
    assert cfg.llm_provider == "mock"


def test_load_config_from_toml(tmp_path, monkeypatch):
    p = tmp_path / "we_together.toml"
    p.write_text(
        "[llm]\nprovider = 'openai_compat'\n"
        "[runtime]\ncache_ttl_seconds = 120\n"
        "[storage]\ntenant_id = 'alpha'\n"
    )
    monkeypatch.delenv("WE_TOGETHER_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("WE_TOGETHER_CACHE_TTL", raising=False)
    monkeypatch.delenv("WE_TOGETHER_TENANT_ID", raising=False)
    cfg = load_config(p)
    assert cfg.llm_provider == "openai_compat"
    assert cfg.cache_ttl_seconds == 120
    assert cfg.tenant_id == "alpha"


def test_env_overrides_toml(tmp_path, monkeypatch):
    p = tmp_path / "we_together.toml"
    p.write_text("[llm]\nprovider = 'mock'\n")
    monkeypatch.setenv("WE_TOGETHER_LLM_PROVIDER", "anthropic")
    cfg = load_config(p)
    assert cfg.llm_provider == "anthropic"
