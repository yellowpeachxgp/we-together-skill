# Service Inventory (v0.14.0, Phase 36 audit)

**Date**: 2026-04-19
**目标**：对 `src/we_together/services/` 下 60+ 个服务逐个审计引用密度与职责，识别重复/死代码。

## 方法
按 "reference_count" = `grep -rln <module> src/we_together tests scripts` 的 distinct file 数。注意这是粗略数，不是调用频次。

## 服务审计表

### 导入层（Ingestion）
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| ingestion_service | 15+ | narration 导入主入口 | 🟢 热路径 |
| email_ingestion_service | 8+ | .eml 文件 | 🟢 热路径 |
| file_ingestion_service | 6+ | 通用文件导入 | 🟢 热路径 |
| directory_ingestion_service | 5+ | 目录扫描 | 🟢 热路径 |
| auto_ingestion_service | 5+ | narration/text_chat 判别 | 🟢 热路径 |
| ingestion_helpers | 10+ | 共用 SQL | 🟢 核心 |
| evidence_dedup_service | 3+ | 去重 | 🟡 次路径 |
| onboarding_flow | 3+ | 首次体验 | 🟡 次路径 |

### Patch 核心
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| patch_service | 20+ | patch 构造/推理 | 🟢 核心 |
| patch_applier | 15+ | 落库唯一入口 | 🟢 核心 |
| patch_batch | 3+ | 批量 | 🟡 次路径 |
| patch_transactional | 3+ | 事务包裹 | 🟡 次路径 |

### 身份 & 融合
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| identity_fusion_service | 8+ | 身份融合评分 | 🟢 核心 |
| identity_link_service | 6+ | 跨平台身份映射 | 🟢 核心 |
| fusion_service | 7+ | 候选升级为主图 | 🟢 核心 |
| candidate_store | 6+ | 候选中间层 CRUD | 🟢 核心 |
| branch_resolver_service | 5+ | local_branch 自动 resolve | 🟢 核心 |
| retire_person_service | 2 | person 退场 | 🟡 低频 |
| merge_duplicates (CLI) | 2 | CLI 入口 | 🟡 低频 |

### Retrieval / Runtime
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| memory_recall_service | 6 | 规则检索（type/relevance/overlap） | 🟢 核心 |
| embedding_recall | 7 | embedding 检索 + filter_person_ids | 🟢 核心 |
| associative_recall | 5 | 关联检索（跨 memory） | 🟡 次路径 |
| vector_similarity | 10+ | encode/decode/cosine/top_k | 🟢 核心 |
| vector_index | 4 | flat_python / sqlite_vec / faiss backend | 🟢 核心 |
| embedding_cache | 3 | LRU | 🟡 次路径 |

**三条 recall 职责划分**：
- `memory_recall_service`：**纯结构化规则**（type × relevance × confidence × recency × overlap × scene_match）。**无 embedding**。
- `embedding_recall`：**向量语义相似**。支持 `filter_person_ids` 做层级。
- `associative_recall`：**跨 memory 关联图**（同事件/同 scene）。**与 embedding 正交**。
- **结论**：三者职责不重叠，无需合流。运行时由 runtime/sqlite_retrieval 按需组合。

### Relation 演化
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| relation_drift_service | 11 | 按 event 窗口重算 strength | 🟢 核心 |
| relation_conflict_service | 6 | 两条 relation 同对同向时合并 | 🟡 次路径 |
| relation_history_service | 4 | 变更时间线 | 🟡 次路径 |

**三条 relation 职责**：
- `drift`：**连续量**（strength ±0.03..0.05）
- `conflict`：**结构冲突**（同对同向多条）
- `history`：**读视图**（不写）
- 结论：不重叠。

### Memory 生命周期
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| memory_cluster_service | 5 | 聚簇（embedding-first / Jaccard fallback） | 🟢 核心 |
| memory_condenser_service | 4 | 多条压缩成一条 | 🟡 次路径 |
| memory_archive_service | 6 | 冷藏（status=cold） | 🟡 次路径 |
| cold_memory (CLI + ???) | 8 | 冷藏搜索+CLI | 🟡 次路径 |

### 演化/Tick
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| state_decay_service | 5+ | confidence 衰减 | 🟢 核心 |
| time_simulator | 3（新）| 编排 tick | 🟢 新核心 |
| tick_sanity | 2（新）| 合理性评估 | 🟢 新核心 |
| self_activation_service | 4 | 内心独白 | 🟡 次路径 |
| scene_transition_service | 3 | 下一 scene 推荐 | 🟡 次路径 |
| persona_drift_service | 3 | 人格漂移 | 🟡 次路径 |

### 主动 / 元认知 / 多模态（v0.13 新增）
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| proactive_agent | 3（新） | Trigger + Intent | 🟢 核心 |
| proactive_prefs | 3（新） | mute/consent | 🟢 核心 |
| contradiction_detector | 2（新） | embedding + LLM 判矛盾 | 🟢 核心 |

### 媒体（v0.14 新增）
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| media_asset_service | 3（新） | register / list / link / visibility | 🟢 核心 |
| ocr_service | 1（新） | vision → memory / audio → event | 🟢 核心 |

### 基础设施 / 杂项
| 服务 | refs | 职责 | 状态 |
|------|:----:|------|------|
| chat_service | 10+ | 对话 run_turn | 🟢 核心 |
| dialogue_service | 8+ | 对话事件 record | 🟢 核心 |
| agent_loop_service | 3 | 多轮 loop | 🟡 次路径 |
| scene_service | 8+ | scene CRUD | 🟢 核心 |
| group_service | 5+ | group CRUD | 🟢 核心 |
| event_service | 4 | event CRUD | 🟢 核心 |
| event_causality_service | 4 | event → event 因果 | 🟡 低热，保留 |
| perceived_memory_service | 3 | 多视角 memory | 🟡 低热，保留 |
| federation_service | 3 | 联邦 stub | 🟡 stub |
| federation_fetcher | 3 | 远端 fetch | 🟡 stub |
| hot_reload | 3 | 配置热重载 | 🟡 stub |
| rbac_service | 2 | 权限 stub | 🟡 stub |
| tenant_router | 2 | 多租户 stub | 🟡 stub |
| graph_analytics | 4 | 度/密度/孤立 | 🟡 次路径 |
| graph_serializer | 3 | canonical JSON | 🟡 次路径 |
| obsidian_exporter | 2 | Obsidian 导出 | 🟡 工具 |
| cache_warmer | 2 | retrieval_cache 预热 | 🟡 工具 |
| narrative_service | 5 | 章节聚合 | 🟢 核心 |
| event_bus_service | 5 | NATS/Redis/mock | 🟢 核心 |

## 结论

- **无完全 dead 服务**（所有都有 ≥1 调用）。
- **12 个 🟡 次路径或 stub** 的可移除性评估留给 v0.15（需要真的走过真部署后再判断）。
- **recall / relation 三条路径各自独立，不合流**。
- **cold_memory / memory_archive_service 可能有重叠**，本阶段暂不动，留 v0.15 细审。

## 给 v0.15 的建议
1. `federation_service` + `federation_fetcher` + `federation_protocol.md` RFC 合一再审
2. `rbac_service` / `tenant_router` 若未在 Phase 33 Skill 宿主落地中激活，可以降级到 `docs/future/` 目录或删除
3. `cache_warmer` 若 runtime cache hit_rate 稳定 >80% 可删
