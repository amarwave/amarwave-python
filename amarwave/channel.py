"""
AmarWave — Channel class.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .emitter import EventEmitter

if TYPE_CHECKING:
    from .client import AmarWave


class Channel(EventEmitter):
    """
    Represents a subscription to a named AmarWave channel.

    Obtained via ``aw.subscribe("channel-name")`` — never constructed directly.

    Example::

        ch = aw.subscribe("public-chat")
        ch.bind("message", lambda data: print(data["text"]))
        await ch.publish("message", {"user": "Ali", "text": "Hello!"})
    """

    def __init__(self, name: str, client: "AmarWave") -> None:
        super().__init__()
        self.name:       str       = name
        self._aw:        AmarWave  = client
        self.subscribed: bool      = False
        self._queue:     list[dict[str, Any]] = []

    # ── Publish ───────────────────────────────────────────────────────────────

    async def publish(self, event: str, data: Any = None) -> bool:
        """
        Publish an event to this channel via HTTP API.

        - Safe to call before subscribed — queued and flushed automatically.
        - Returns ``True`` on success, ``False`` on failure.

        Example::

            await ch.publish("message", {"user": "Ali", "text": "Hello!"})
        """
        if not self.subscribed:
            # Queue until subscription is confirmed
            future: asyncio.Future[bool] = asyncio.get_event_loop().create_future()
            self._queue.append({"event": event, "data": data, "future": future})
            return await future

        return await self._aw._http_publish(self.name, event, data)

    async def _flush_queue(self) -> None:
        """Called internally when subscription_succeeded arrives."""
        items, self._queue = self._queue[:], []
        for item in items:
            result = await self._aw._http_publish(self.name, item["event"], item["data"])
            future: asyncio.Future[bool] = item["future"]
            if not future.done():
                future.set_result(result)
