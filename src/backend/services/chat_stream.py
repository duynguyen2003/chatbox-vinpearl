from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


class ChatStreamCancelled(Exception):
    """Stop request-scoped generation after the client disconnects."""


@dataclass(frozen=True)
class ChatStreamSink:
    emit: Callable[[dict], None]
    is_cancelled: Callable[[], bool]


_current_sink: ContextVar[ChatStreamSink | None] = ContextVar(
    "chat_stream_sink",
    default=None,
)


@contextmanager
def bind_chat_stream(sink: ChatStreamSink) -> Iterator[None]:
    token = _current_sink.set(sink)
    try:
        yield
    finally:
        _current_sink.reset(token)


def chat_stream_active() -> bool:
    return _current_sink.get() is not None


def _emit(event: dict) -> None:
    sink = _current_sink.get()
    if sink is None:
        return
    if sink.is_cancelled():
        raise ChatStreamCancelled()
    sink.emit(event)


def emit_chat_status(stage: str) -> None:
    _emit({"type": "status", "stage": stage})


def emit_chat_delta(text: str) -> None:
    if text:
        _emit({"type": "delta", "text": text})


def encode_ndjson(event: dict) -> bytes:
    return (
        json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")

