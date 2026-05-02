"""MCP (Model Context Protocol) adapter：把 we-together 暴露为 MCP server tool / resource / prompt schema。

Phase 33 扩展（v0.14.0 / ADR 0035）：
- tools 追加 snapshot_list / scene_list / import_narration / proactive_scan
- resources 暴露 graph_summary
- prompts 暴露内置 system prompt 模板
"""
from __future__ import annotations


WE_TOGETHER_MCP_TOOLS = [
    {
        "name": "we_together_run_turn",
        "description": "Run a scene-aware conversation turn.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene_id": {"type": "string"},
                "input": {"type": "string"},
            },
            "required": ["scene_id", "input"],
        },
    },
    {
        "name": "we_together_graph_summary",
        "description": "Return graph summary (person/relation/memory counts).",
        "inputSchema": {
            "type": "object",
            "properties": {"scene_id": {"type": "string"}},
        },
    },
    {
        "name": "we_together_scene_list",
        "description": "List active scenes with participant counts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "we_together_snapshot_list",
        "description": "List recent snapshots.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 10}},
        },
    },
    {
        "name": "we_together_import_narration",
        "description": "Import a narration text into a scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene_id": {"type": "string"},
                "text": {"type": "string"},
                "source_person_id": {"type": "string"},
            },
            "required": ["scene_id", "text"],
        },
    },
    {
        "name": "we_together_proactive_scan",
        "description": "Scan triggers (anniversary/silence) and return candidate intents.",
        "inputSchema": {
            "type": "object",
            "properties": {"daily_budget": {"type": "integer", "default": 3}},
        },
    },
    {
        "name": "we_together_self_describe",
        "description": "Describe the skill itself: ADRs / invariants / services / migrations counts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "we_together_list_invariants",
        "description": "List all invariants with their ADR refs and test coverage.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "we_together_check_invariant",
        "description": "Show a single invariant by id (1..28+).",
        "inputSchema": {
            "type": "object",
            "properties": {"invariant_id": {"type": "integer"}},
            "required": ["invariant_id"],
        },
    },
]


WE_TOGETHER_MCP_RESOURCES = [
    {
        "uri": "we-together://graph/summary",
        "name": "Graph Summary",
        "description": "Current counts of persons/relations/scenes/events/memories.",
        "mimeType": "application/json",
    },
    {
        "uri": "we-together://schema/version",
        "name": "Skill Schema Version",
        "description": "SkillRequest/Response schema version.",
        "mimeType": "text/plain",
    },
]


WE_TOGETHER_MCP_PROMPTS = [
    {
        "name": "we_together_scene_reply",
        "description": "Reply as a scene participant, grounded in retrieval package.",
        "arguments": [
            {"name": "scene_id", "description": "Scene id", "required": True},
            {"name": "user_input", "description": "Latest user message", "required": True},
        ],
    },
]


def build_mcp_tools(extra: list[dict] | None = None) -> list[dict]:
    return list(WE_TOGETHER_MCP_TOOLS) + list(extra or [])


def build_mcp_resources(extra: list[dict] | None = None) -> list[dict]:
    return list(WE_TOGETHER_MCP_RESOURCES) + list(extra or [])


def build_mcp_prompts(extra: list[dict] | None = None) -> list[dict]:
    return list(WE_TOGETHER_MCP_PROMPTS) + list(extra or [])
