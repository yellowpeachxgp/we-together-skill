# Claude Code skill 示例

## 安装

```bash
pip install -e ../../..     # 从仓库根
we-together bootstrap --root ~/.we-together
we-together seed-demo --root ~/.we-together
```

## 打包为 `.weskill.zip`

```bash
we-together package-skill pack --root ../../.. --output ./we-together.weskill.zip
```

产出的 zip 含 `SKILL.md`（本目录）+ db migrations + seeds + scripts + src。

## 验证

```bash
we-together version   # 应输出 we-together 0.9.0
```

## 文件

- `SKILL.md` — Claude Code 读取的 skill 元信息
- `use_cases.md` — 3 个典型用例
- 预期打包后的 `we-together.weskill.zip`（运行上面的 pack 命令生成）
