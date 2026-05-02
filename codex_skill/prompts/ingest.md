# 导入态提示

适用于：

- `导入材料`
- `初始化图谱`
- `bootstrap`
- `导入 narration / text / email / file / directory`

执行顺序：

1. 读取 `references/local-runtime.md`
2. 在 `repo_root` 中执行对应脚本
3. 优先脚本：
   - `scripts/bootstrap.py`
   - `scripts/import_auto.py`
   - `scripts/import_file_auto.py`
   - `scripts/import_narration.py`
   - `scripts/import_text_chat.py`
   - `scripts/import_email_file.py`
   - `scripts/import_directory.py`
4. 导入后优先给出：
   - 导入结果
   - 图谱摘要
   - 必要时 retrieval/scene 建议
