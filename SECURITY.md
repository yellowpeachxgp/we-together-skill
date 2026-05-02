# Security Policy

## 支持版本

| 版本 | 支持中 |
|------|:----:|
| 0.17.x | ✅ |
| 0.16.x | ✅（仅安全补丁）|
| < 0.16 | ❌ |

## 报告漏洞

**请不要在 GitHub issue 中公开报告安全漏洞**。

通过 GitHub Security Advisories 或发邮件到 maintainer：
- 漏洞描述与影响
- 重现步骤
- 影响的版本
- 如有，建议的修复

**响应时间**：
- 确认：72 小时内
- 修复进度更新：每周
- 公告 + CVE：修复发布后

## 公开披露

修复后 **30 天**我们会：
1. 发布补丁版本
2. 公开披露细节（CVE + advisory）
3. 致谢报告者（除非选匿名）

## 当前已知的边界

### 联邦 v1.1（Bearer token）
- 鉴权为 Bearer token hash 对比
- 无 mTLS（留 v0.18+）
- 默认 localhost/VPC 部署；暴露公网必须自行加 TLS 终端

### PII 处理
- `mask_email` / `mask_phone` 为启发式正则
- 极端场景可能漏过（如视觉伪装的邮箱）
- 生产建议叠加：外部 DLP 扫描

### Plugin 加载
- entry_points 自动发现并 load
- **plugin 安装即信任**——恶意 plugin 可访问 db
- 只从可信来源 `pip install` plugin

## 安全设计不变式

相关不变式（见 ADR）：
- **#18** 主动写入必须经预算 + 偏好门控
- **#22** 写入对称撤销
- **#23** 扩展点必须 plugin registry 注册
- **#25** 跨图谱出口必须 PII mask + visibility 过滤
