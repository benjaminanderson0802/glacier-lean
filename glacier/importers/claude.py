"""Parser for a Claude data export conversation list."""

from . import common


def _extract(conversation: dict):
    source_id = str(conversation.get("uuid") or "")
    title = str(conversation.get("name") or "")
    created = common.format_date(conversation.get("created_at"))
    messages = []
    chat_messages = conversation.get("chat_messages")
    if isinstance(chat_messages, list):
        for message in chat_messages:
            if not isinstance(message, dict):
                continue
            sender = message.get("sender")
            if sender not in {"human", "assistant"}:
                continue
            text = common.clean_text(message.get("text"))
            if not text and isinstance(message.get("content"), list):
                text = "\n".join(
                    item["text"].strip()
                    for item in message["content"]
                    if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip()
                )
            if text:
                messages.append(("user" if sender == "human" else "assistant", text))
    return source_id, title, created, messages


def parse(conversations_json_text: str):
    return common.make_notes("claude", common.load_conversations(conversations_json_text), _extract)
