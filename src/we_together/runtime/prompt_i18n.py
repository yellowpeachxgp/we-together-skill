"""prompt_i18n（Phase 49 UX）：多语言 prompt 模板 + 自动识别。

支持语言: zh / en / ja
模板里用 {placeholder} 格式；get_prompt(key, lang, **kwargs) 渲染
"""
from __future__ import annotations

import re
from typing import Literal

SupportedLang = Literal["zh", "en", "ja"]
SUPPORTED_LANGS: tuple[SupportedLang, ...] = ("zh", "en", "ja")
DEFAULT_LANG: SupportedLang = "zh"


PROMPT_TEMPLATES: dict[str, dict[str, str]] = {
    "scene_reply.system": {
        "zh": "你是一个参与当前场景 {scene_id} 的人物智能体。请基于检索包中的人物关系和记忆，给出符合社会一致性的回应。",
        "en": "You are a person-agent participating in scene {scene_id}. Reply consistently with the relations and memories in the retrieval package.",
        "ja": "あなたは場面 {scene_id} に参加している人物エージェントです。関係性と記憶に一貫した返答をしてください。",
    },
    "self_activation.prompt": {
        "zh": "这是 {name} 的内心独白片段，请用第一人称写 1-2 句，反映当下心境。",
        "en": "An inner-monologue snippet of {name}. Write 1-2 first-person sentences reflecting current mood.",
        "ja": "{name} の心の声です。現在の気持ちを一人称で1〜2文で表してください。",
    },
    "contradiction.judge": {
        "zh": "判断两条记忆是否直接矛盾。只输出 JSON。\nA: {a}\nB: {b}",
        "en": "Judge whether two memories directly contradict. JSON only.\nA: {a}\nB: {b}",
        "ja": "二つの記憶が直接矛盾しているかJSONで答えて。\nA: {a}\nB: {b}",
    },
}


# 极简语言检测：按字符集启发式
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
KANA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")


def detect_lang(text: str | None) -> SupportedLang:
    if not text:
        return DEFAULT_LANG
    if KANA_RE.search(text):
        return "ja"
    if CJK_RE.search(text):
        return "zh"
    # 默认英文（ASCII）
    return "en"


def normalize_lang(lang: str | None) -> SupportedLang:
    if lang is None:
        return DEFAULT_LANG
    lang = lang.lower().replace("-", "_")
    # 支持 zh_CN / en_US 等
    prefix = lang.split("_", 1)[0]
    if prefix in SUPPORTED_LANGS:
        return prefix  # type: ignore[return-value]
    return DEFAULT_LANG


def get_prompt(key: str, *, lang: SupportedLang | str = DEFAULT_LANG, **kwargs) -> str:
    lang_norm = normalize_lang(lang)
    templates = PROMPT_TEMPLATES.get(key)
    if not templates:
        raise KeyError(f"unknown prompt key: {key}")
    tmpl = templates.get(lang_norm) or templates.get(DEFAULT_LANG)
    if tmpl is None:
        raise ValueError(f"prompt {key!r} has no template for lang {lang_norm!r}")
    try:
        return tmpl.format(**kwargs)
    except KeyError as exc:
        raise KeyError(
            f"prompt {key!r} ({lang_norm}) missing placeholder: {exc}"
        ) from exc


def register_prompt(key: str, templates: dict[str, str]) -> None:
    """第三方 plugin 可注册新 prompt key。"""
    if not templates:
        raise ValueError("templates must not be empty")
    PROMPT_TEMPLATES[key] = dict(templates)


def list_prompt_keys() -> list[str]:
    return sorted(PROMPT_TEMPLATES.keys())


def coverage() -> dict[str, dict[str, bool]]:
    """每个 key 在每个语言下是否有模板。"""
    return {
        key: {lang: (lang in langs) for lang in SUPPORTED_LANGS}
        for key, langs in PROMPT_TEMPLATES.items()
    }
