"""Onboarding 状态机：引导新用户从 0 到"跑起来第一个 skill"。

五个步骤：
  WELCOME          介绍 we-together
  IMPORT_CHOICE    问用户选择哪个数据源（narration / text_chat / email / skip）
  IMPORT_EXEC      执行导入（dry-run 下只打印命令）
  SCENE_SETUP      创建第一个 scene
  FIRST_TURN       跑一次 dialogue_turn
  DONE             收尾 + graph_summary

状态是纯数据对象，CLI 层负责交互；此模块只做"给定当前 state + 输入 → 下一个 state"。
"""
from __future__ import annotations

from dataclasses import dataclass, field

STEP_ORDER = [
    "WELCOME", "IMPORT_CHOICE", "IMPORT_EXEC", "SCENE_SETUP", "FIRST_TURN", "DONE",
]


@dataclass
class OnboardingState:
    step: str = "WELCOME"
    data: dict = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)


PROMPTS = {
    "WELCOME": "欢迎使用 we-together-skill。按回车继续。",
    "IMPORT_CHOICE": "选择首批数据源：1) narration 文本 2) text_chat 对话 3) email 4) skip",
    "IMPORT_EXEC": "执行导入（dry-run 下只打印命令）。按回车。",
    "SCENE_SETUP": "给你的第一个 scene 起个名字（默认: my-first-scene）。",
    "FIRST_TURN": "给场景里的人物说点什么？（默认: hi）",
    "DONE": "完成！跑 `we-together graph-summary` 查看图谱。",
}


def next_step(state: OnboardingState, answer: str | None = None) -> OnboardingState:
    answer = (answer or "").strip()
    cur = state.step

    if cur == "WELCOME":
        return OnboardingState(step="IMPORT_CHOICE", data=dict(state.data),
                                messages=state.messages + ["start"])
    if cur == "IMPORT_CHOICE":
        choice = answer or "skip"
        mapping = {"1": "narration", "2": "text_chat", "3": "email",
                   "4": "skip", "narration": "narration", "text_chat": "text_chat",
                   "email": "email", "skip": "skip"}
        mode = mapping.get(choice, "skip")
        data = dict(state.data); data["import_mode"] = mode
        return OnboardingState(step="IMPORT_EXEC", data=data,
                                messages=state.messages + [f"chose {mode}"])
    if cur == "IMPORT_EXEC":
        data = dict(state.data); data["import_done"] = True
        return OnboardingState(step="SCENE_SETUP", data=data,
                                messages=state.messages + ["import stage done"])
    if cur == "SCENE_SETUP":
        name = answer or "my-first-scene"
        data = dict(state.data); data["scene_name"] = name
        return OnboardingState(step="FIRST_TURN", data=data,
                                messages=state.messages + [f"scene name {name}"])
    if cur == "FIRST_TURN":
        text = answer or "hi"
        data = dict(state.data); data["first_input"] = text
        return OnboardingState(step="DONE", data=data,
                                messages=state.messages + [f"first turn input '{text}'"])
    if cur == "DONE":
        return state
    raise ValueError(f"unknown step: {cur}")


def run_all(answers: list[str | None]) -> OnboardingState:
    """一次性喂完所有答案（用于测试 / dry-run）。"""
    state = OnboardingState()
    for ans in answers:
        state = next_step(state, ans)
        if state.step == "DONE":
            break
    # 如果答案不足，再推一次
    if state.step != "DONE":
        while state.step != "DONE":
            state = next_step(state, None)
    return state
