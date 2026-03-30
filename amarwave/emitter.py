"""
AmarWave — EventEmitter base class.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .types import EventCallback, GlobalCallback


class EventEmitter:
    """
    Simple synchronous event emitter.
    Used as the base class for both AmarWave and Channel.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[EventCallback]] = defaultdict(list)
        self._globals:   list[GlobalCallback]           = []

    # ── Bind / unbind ─────────────────────────────────────────────────────────

    def bind(self, event: str, fn: EventCallback) -> "EventEmitter":
        """Register a listener for `event`. Returns self for chaining."""
        self._listeners[event].append(fn)
        return self

    def on(self, event: str, fn: EventCallback) -> "EventEmitter":
        """Alias for bind()."""
        return self.bind(event, fn)

    def unbind(self, event: str, fn: EventCallback | None = None) -> "EventEmitter":
        """
        Remove a listener.
        If `fn` is omitted, all listeners for `event` are removed.
        """
        if fn is None:
            self._listeners.pop(event, None)
        else:
            self._listeners[event] = [f for f in self._listeners[event] if f is not fn]
        return self

    def off(self, event: str, fn: EventCallback | None = None) -> "EventEmitter":
        """Alias for unbind()."""
        return self.unbind(event, fn)

    def bind_global(self, fn: GlobalCallback) -> "EventEmitter":
        """Listen to every event emitted on this emitter."""
        self._globals.append(fn)
        return self

    def unbind_global(self, fn: GlobalCallback | None = None) -> "EventEmitter":
        """Remove a global listener (or all if fn is omitted)."""
        if fn is None:
            self._globals.clear()
        else:
            self._globals = [f for f in self._globals if f is not fn]
        return self

    # ── Emit ──────────────────────────────────────────────────────────────────

    def _emit(self, event: str, data: Any = None) -> None:
        """Fire all listeners for `event` with `data`."""
        for fn in list(self._listeners.get(event, [])):
            fn(data)
        for fn in list(self._globals):
            fn(event, data)
