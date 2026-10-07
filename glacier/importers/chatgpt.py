"""Parser for a ChatGPT conversations.json export."""

from . import common


def _extract(conversation: dict):
    source_id = str(conversation.get("id") or conversation.get("conversation_id") or "")
    title = str(conversation.get("title") or "")
    created = common.format_date(conversation.get("create_time"))
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        mapping = {}
    node_id = conversation.get("current_node")
    messages = []
    seen = set()
    while node_id in mapping and node_id not in seen:
        seen.add(node_id)
        node = mapping[node_id]
        if not isinstance(node, dict):
            break
        message = node.get("message")
        if isinstance(message, dict):
            author = message.get("author")
            role = author.get("role") if isinstance(author, dict) else None
            content = message.get("content")
            parts = content.get("parts", []) if isinstance(content, dict) else []
            text = common.clean_text(parts)
            if role == "user" and text:
                messages.append(("user", text))
            elif role == "assistant" and text:
                messages.append(("assistant", text))
        node_id = node.get("parent")
    messages.reverse()
    return source_id, title, created, messages


def parse(conversations_json_text: str):
    return common.make_notes("chatgpt", common.load_conversations(conversations_json_text), _extract)
