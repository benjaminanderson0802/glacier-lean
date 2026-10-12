"""Unified conversation API used by the messages screen."""
from __future__ import annotations

import asyncio
import json
import subprocess
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

import messages as service
from routes import assistant_chat

router = APIRouter()


class SendBody(BaseModel):
    text: str = Field(min_length=1, max_length=service.MAX_TEXT)
    model_config = ConfigDict(extra="forbid")


class NewThreadBody(SendBody):
    source: Literal["glacier", "codex", "claude"]


@router.get("/api/messages/threads")
def list_threads(q: str = ""):
    return service.list_threads(q)


@router.get("/api/messages/threads/{thread_id}")
def get_thread(thread_id: str, before: str | None = None,
               limit: int = Query(default=service.PAGE_SIZE, ge=1, le=service.PAGE_SIZE)):
    rows = service.get_messages(thread_id, before=before, limit=limit)
    if rows is None:
        raise HTTPException(404, "Conversation not found")
    return {"id": thread_id, "messages": rows,
            "next_before": rows[-1]["id"] if len(rows) == limit and rows else None}


async def _assistant_send(conversation_id: str, text: str, thread_id: str) -> dict:
    owner_message = service._message(f"{thread_id}:{uuid.uuid4()}", "me", "you", text, service.now())
    service.store.broadcaster.publish({"type": "messages.thread_message", "thread_id": thread_id,
                                       "message": owner_message})
    response = assistant_chat.chat(assistant_chat.ChatRequest(conversation_id=conversation_id, message=text))
    collected = ""
    reply_message_id = str(uuid.uuid4())
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        for line in str(chunk).splitlines():
            if not line.startswith("data: "):
                continue
            try:
                event = json.loads(line[6:])
            except ValueError:
                continue
            if event.get("type") == "TEXT_MESSAGE_START":
                reply_message_id = str(event.get("messageId") or reply_message_id)
            elif event.get("type") == "TEXT_MESSAGE_CONTENT":
                delta = str(event.get("delta", ""))
                collected += delta
                service.store.broadcaster.publish({"type": "messages.thread_delta", "thread_id": thread_id,
                                                   "message_id": reply_message_id, "delta": delta})
            elif event.get("type") == "RUN_ERROR":
                raise RuntimeError(str(event.get("message") or "The assistant could not answer."))
    if not collected:
        raise RuntimeError("The assistant returned no reply.")
    rows = service.get_messages(thread_id, limit=1) or []
    message = next((item for item in rows if item["from"] == "them"), None)
    if message is None:
        message = service._message(reply_message_id, "them", "Glacier", collected, service.now())
    service.store.broadcaster.publish({"type": "messages.thread_message", "thread_id": thread_id, "message": message})
    return message


@router.post("/api/messages/threads/{thread_id}")
async def send_message(thread_id: str, body: SendBody):
    if thread_id.startswith("glacier:"):
        conversation_id = thread_id[len("glacier:"):]
        try:
            assistant_chat._conversation_note(conversation_id)
        except HTTPException as error:
            raise error
        except Exception as error:
            raise HTTPException(404, "Conversation not found") from error
        try:
            message = await _assistant_send(conversation_id, body.text, thread_id)
        except RuntimeError as error:
            raise HTTPException(502, str(error)) from error
        return {"thread_id": thread_id, "message": message}
    if thread_id.startswith("worker:"):
        try:
            message = service._append_worker_note(thread_id, body.text)
        except ValueError as error:
            raise HTTPException(404, str(error)) from error
        return {"thread_id": thread_id, "message": message}
    source = "codex" if thread_id.startswith("codex:") else next(
        (name for name, prefix in service._SOURCE_PREFIX.items() if thread_id.startswith(prefix)), None)
    if source is None:
        raise HTTPException(404, "Conversation not found")
    if source not in {"codex", "claude"}:
        raise HTTPException(403, "This conversation is read-only")
    if service.get_messages(thread_id) is None:
        raise HTTPException(404, "Conversation not found")
    try:
        message = await asyncio.to_thread(service.send_session, thread_id, source, body.text)
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(403, str(error)) from error
    except subprocess.TimeoutExpired as error:
        raise HTTPException(504, "The coding assistant took too long to reply") from error
    except service.SessionResumeError as error:
        raise HTTPException(409, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(502, str(error)) from error
    return {"thread_id": thread_id, "message": message}


@router.post("/api/messages/threads")
async def create_thread(body: NewThreadBody):
    conversation_id = str(uuid.uuid4())
    if body.source == "glacier":
        thread_id = f"glacier:{conversation_id}"
        try:
            message = await _assistant_send(conversation_id, body.text, thread_id)
        except RuntimeError as error:
            raise HTTPException(502, str(error)) from error
        thread = {"id": thread_id, "source": "glacier", "title": service._safe(body.text[:60]),
                  "last_text": message["text"], "last_at": message["at"], "unread": False, "can_send": True}
        return {"thread": thread, "thread_id": thread_id, "message": message}
    try:
        message, native_id = await asyncio.to_thread(service.create_session, body.source, body.text)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(403, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(502, str(error)) from error
    thread_id = service._session_id(body.source, native_id)
    thread = {"id": thread_id, "source": body.source, "title": service._safe(body.text[:60]),
              "last_text": message["text"], "last_at": message["at"], "unread": False, "can_send": True}
    return {"thread": thread, "thread_id": thread_id, "message": message}
