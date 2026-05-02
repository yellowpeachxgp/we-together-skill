# Intent Examples

## Positive

- `看一下 we-together 当前状态`
- `读取 we-together 交接文档并继续推进`
- `继续 we-together 的 Phase 72`
- `查一下 we-together 的不变式`
- `给我 we-together 图谱摘要`
- `帮我导入一段 we-together 材料`

## Negative

- `看一下当前状态`
- `解释一下 ADR 是什么`
- `scene 是什么意思`
- `memory 表怎么设计`
- `帮我写个 Python 脚本`
- `聊聊社会图谱理论`

## Ambiguous

- `这个 skill 的状态如何`
- `这个图谱现在怎么样`
- `我想继续做这个项目`

仅当上下文已经明确指向 `we-together` 时，router 才应接管 `Ambiguous` 类请求。
