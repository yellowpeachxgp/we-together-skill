"""examples/plugin_example_minimal/__init__.py — 最小示例 plugin。

要注册到 entry_points，需要在 pyproject.toml 里加:

  [project.entry-points."we_together.importers"]
  example_echo_importer = "plugin_example_minimal:ExampleEchoImporter"

  [project.entry-points."we_together.hooks"]
  example_tick_counter = "plugin_example_minimal:ExampleTickCounter"
"""
from __future__ import annotations


class ExampleEchoImporter:
    """最小 importer：什么都不 import，返回 echo。"""
    name = "example_echo_importer"
    plugin_api_version = "1"

    def run(self, *, source, db_path):
        return {
            "plugin": self.name,
            "source": source,
            "db_path": str(db_path),
            "events_created": 0,
            "note": "example only",
        }


class ExampleTickCounter:
    """最小 hook：统计 tick 次数。"""
    name = "example_tick_counter"
    event_type = "tick.after"
    plugin_api_version = "1"
    _count = 0

    def handle(self, payload: dict) -> None:
        ExampleTickCounter._count += 1

    @classmethod
    def count(cls) -> int:
        return cls._count
