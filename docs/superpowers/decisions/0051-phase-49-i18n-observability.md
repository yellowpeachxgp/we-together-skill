---
adr: 0051
title: Phase 49 — i18n prompts + 时序可观测性
status: Accepted
date: 2026-04-19
---

# ADR 0051: Phase 49 — i18n + 时序可观测性

## 状态
Accepted — 2026-04-19

## 背景
整个 prompt 体系一直是中文；跨语言用户无法直接用。Dashboard 是快照型，看不出演化趋势。alerting 零（图谱出异常无机制通知外部）。这三件事一起做。

## 决策

### D1. runtime/prompt_i18n
- 三语支持：zh / en / ja
- `PROMPT_TEMPLATES[key][lang] = template_str`
- 核心 key 三语齐全：scene_reply.system / self_activation.prompt / contradiction.judge
- `get_prompt(key, lang, **kwargs)` 渲染 + fallback 到 DEFAULT_LANG(zh)
- `detect_lang(text)` 启发式：kana → ja、CJK → zh、其他 → en
- `normalize_lang("zh_CN")` → "zh"；`normalize_lang("fr")` → DEFAULT（zh）
- `register_prompt(key, templates)` 让第三方 plugin 动态扩展

### D2. observability/time_series_svg
- `memory_growth_trend(db, days)` / `event_count_trend(db, days)`
- `render_sparkline_svg(points, width, height, stroke, fill, title)` 纯 SVG，可嵌 HTML
- `trend_bundle(db, days)` 同时返 memory + events 两份 SVG + 原数据

### D3. observability/webhook_alert
- `AlertRule(metric, op, threshold, url, name)`
- `evaluate(metrics, rules)` 返回匹配项（支持 `> < >= <= == !=`）
- `dispatch(matches, dry_run)` 真 POST JSON 或 dry_run 返 payload
- `parse_rules(raw)` 从 dict 列表加载

### D4. 无依赖边界
- SVG 渲染用字符串拼接（不依赖 matplotlib）
- webhook 用 stdlib urllib（不依赖 requests）
- prompt 不依赖 jinja（直接 `str.format`）

## 版本锚点
- tests: +17 (test_phase_49_ux.py)
- 文件: `runtime/prompt_i18n.py` / `observability/time_series_svg.py` / `observability/webhook_alert.py`

## 非目标（v0.17）
- 4+ 语言（法语/西语等；加 lang key 即可，不是架构问题）
- 真 LLM 产 i18n 翻译（减翻译债）
- SVG 高级样式（legend / axes）→ 用 matplotlib 或 mkdocs 插件
- alert 去重 / 分级（当前 stateless）
- mkdocs 站点真搭建（当前留 v0.17）

## 拒绝的备选
- gettext / babel：太重；直接 dict 足够
- requests：引入依赖；urllib 够用
- 把 i18n 写进 migration 表：prompt 是代码资产，不放 db
