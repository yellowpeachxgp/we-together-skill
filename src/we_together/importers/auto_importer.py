import re


CHAT_LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+[^:：]+[:：]\s*.+$", re.MULTILINE)


def detect_import_mode(text: str) -> str:
    if CHAT_LINE_RE.search(text):
        return "text_chat"
    return "narration"
