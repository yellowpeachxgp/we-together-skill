# Docker 部署

## 构建

```bash
docker build -t we-together:0.9.0 -f docker/Dockerfile .
```

或用 compose 同时起起 app + metrics（9100）+ branch-console（8765）：

```bash
cd docker
docker compose up --build
```

## 基本用法

单命令：

```bash
docker run --rm -v wt-data:/data we-together:0.9.0 bootstrap --root /data
docker run --rm -v wt-data:/data we-together:0.9.0 seed-demo --root /data
docker run --rm -v wt-data:/data we-together:0.9.0 graph-summary --root /data
```

## 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `WE_TOGETHER_LLM_PROVIDER` | `mock` / `anthropic` / `openai_compat` | `mock` |
| `WE_TOGETHER_DB_ROOT` | 数据目录 | `/data` |
| `WE_TOGETHER_TENANT_ID` | 租户隔离 | `default` |
| `ANTHROPIC_API_KEY` | Anthropic provider key | — |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | OpenAI-compat provider | — |

## 端口

- `9100`: Prometheus `/metrics`
- `8765`: Branch 冲突裁决 console

## 卷

`wt-data` 持久化 `db/main.sqlite3` 与快照/缓存。

## 故障排查

- 首次启动请先跑 `bootstrap` + `seed-demo`，否则 graph-summary 会 exit 非 0
- 需要 LLM 时记得传 `-e ANTHROPIC_API_KEY=...` 或 `-e WE_TOGETHER_LLM_PROVIDER=anthropic`
