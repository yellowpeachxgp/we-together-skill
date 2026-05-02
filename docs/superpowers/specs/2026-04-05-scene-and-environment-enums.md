# We Together Scene 与环境参数枚举稿

## 1. 文档目标

本文档定义第一阶段建议固定的：

- `scene_type`
- 核心环境参数枚举
- 激活与发言相关的状态枚举

目标是保证第一阶段实现时有统一词表，不让场景与环境字段失控。

## 2. 设计原则

### 2.1 核心枚举固定

第一阶段先固定一批高频枚举值，保证：

- importer 输出统一
- runtime 行为一致
- SQLite 字段可索引

### 2.2 允许扩展

核心枚举之外，允许通过：

- `custom_*`
- `metadata_json`

补充扩展值。

## 3. `scene_type` 建议枚举

第一阶段建议固定：

- `private_chat`
- `group_chat`
- `meeting`
- `work_discussion`
- `family_interaction`
- `intimacy_interaction`
- `casual_social`
- `conflict_event`
- `memory_recall`
- `announcement`
- `co_presence`
- `custom`

## 4. `location_scope` 建议枚举

- `same_room`
- `same_home`
- `same_office`
- `same_city`
- `remote`
- `unknown`
- `custom`

## 5. `channel_scope` 建议枚举

- `face_to_face`
- `private_dm`
- `group_channel`
- `work_channel`
- `family_channel`
- `public_feed`
- `unreachable`
- `unknown`
- `custom`

## 6. `visibility_scope` 建议枚举

- `mutual_visible`
- `group_visible`
- `partial_visible`
- `hidden_from_some`
- `fully_hidden`
- `unknown`
- `custom`

## 7. `time_scope` 建议枚举

- `work_hours`
- `off_hours`
- `late_night`
- `weekend`
- `holiday`
- `realtime`
- `historical_recall`
- `unknown`
- `custom`

## 8. `role_scope` 建议枚举

- `work_identity_active`
- `family_identity_active`
- `intimacy_identity_active`
- `friend_identity_active`
- `public_identity_active`
- `mixed_identity_active`
- `unknown`
- `custom`

## 9. `access_scope` 建议枚举

- `open_to_all_participants`
- `invite_only`
- `direct_participants_only`
- `observers_allowed`
- `restricted`
- `unknown`
- `custom`

## 10. `privacy_scope` 建议枚举

- `private`
- `semi_private`
- `group_private`
- `public_inside_group`
- `public`
- `unknown`
- `custom`

## 11. `activation_barrier` 建议枚举

- `low`
- `medium`
- `high`
- `strict`
- `custom`

## 12. 激活状态枚举

### 12.1 `activation_state`

- `inactive`
- `latent`
- `explicit`

### 12.2 `speak_eligibility`

- `allowed`
- `discouraged`
- `blocked`

### 12.3 `event_visibility_level`

- `visible`
- `latent`
- `internal`

## 13. 关系状态枚举

建议第一阶段固定：

- `active`
- `inactive`
- `merged`
- `resolved`
- `ambiguous`

## 14. 第一阶段使用规则

- 所有 importer 和 runtime 优先使用固定枚举
- 如果出现新值，先落 `custom`
- 等累计到一定程度再提升为正式枚举

## 15. 结论

第一阶段的场景和环境系统不应放任自由文本漂移。

它应被实现为：

> **固定核心枚举 + 可扩展补充字段的双层词表系统。**
