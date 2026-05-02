# Obsidian vault 集成示例

Obsidian 笔记 ↔ we-together 图谱双向同步。

## 导入（vault → 图谱）

```python
from pathlib import Path
from we_together.importers.obsidian_md_importer import import_obsidian_vault

result = import_obsidian_vault(Path("~/Documents/MyVault").expanduser())
# result = {"identity_candidates": [...], "event_candidates": [...],
#          "relation_clues": [...]}
```

约定：

- 每个 `.md` 文件名 = person primary_name
- 文件 frontmatter `type: skip` 可排除
- `[[wikilink]]` 自动建立 mention 类 relation_clue

后续走 `fusion_service.fuse_all` 把 candidates 升级为主图实体。

## 导出（图谱 → vault）

```python
from we_together.services.obsidian_exporter import export_to_obsidian_vault

export_to_obsidian_vault(
    Path("path/db/main.sqlite3"),
    Path("~/Documents/we_vault").expanduser(),
)
```

每个 active person 产一个 `<name>.md`，含 persona / style / 关联 memory 列表。

## 场景

- 把日记 / 工作笔记导入，一次性建立人物网络
- 把图谱 persona 导出到 Obsidian 当成"人物字典"

## 与 Logseq 的差别

Logseq 的 block reference 语法不同（`((blockid))`），当前 importer 只处理 `[[wikilink]]`。Logseq 支持可在 Phase 22+ 加。
