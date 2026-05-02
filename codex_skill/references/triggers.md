# 触发词矩阵

## 强触发

以下请求可以直接视为 `we-together` 语境：

- `we-together 当前状态`
- `we-together 交接文档`
- `we-together 不变式`
- `we-together ADR`
- `we-together 图谱摘要`
- `we-together 导入材料`
- `继续 we-together 的 Phase`
- `这个 we-together skill`
- `这个社会图谱项目`
- `这个数字人项目`

## 次触发

以下词只有在已经出现明确 `we-together` 项目语境时，才可作为补充判断：

- `当前状态`
- `交接文档`
- `不变式`
- `ADR`
- `图谱摘要`
- `scene`
- `memory`
- `relation`
- `tenant`
- `导入`
- `graph summary`
- `self describe`

## 非触发

以下情况不要触发：

- 泛化社会图谱理论
- 与本仓库无关的代码库开发
- 一般性的 Python / 前端 / 后端问题
- 没有 `we-together` 项目语义的裸词请求，例如单独说 `当前状态`、`ADR`、`scene`、`memory`
