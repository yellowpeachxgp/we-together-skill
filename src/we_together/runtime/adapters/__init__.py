"""SkillRequest → 平台特定 payload 的适配器集合。

每个适配器实现 `invoke(request, llm_client=None) -> SkillResponse`。
"""
from we_together.runtime.adapters.claude_adapter import ClaudeSkillAdapter
from we_together.runtime.adapters.openai_adapter import OpenAISkillAdapter

__all__ = ["ClaudeSkillAdapter", "OpenAISkillAdapter"]
