"""
AmarWave — Main async client.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlencode

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

from .channel import Channel
from .crypto  import generate_uid, hmac_sha256
from .emitter import EventEmitter
from .types   import CLUSTERS, ConnectionState

logger = logging.getLogger("amarwave")


class AmarWave(EventEmitter):
    """
    AmarWave async real-time client.

    Example::

        import asyncio
        from amarwave import AmarWave

        async def main():
            aw = AmarWave(app_key="KEY", app_secret="SECRET")

            ch = await aw.subscribe("public-chat")
            ch.bind("message", lambda d: print(d["user"], d["text"]))

            await ch.publish("message", {"user": "Ali", "text": "Hello!"})
            await aw.listen()   # keep alive forever

        asyncio.run(main())
    """

    def __init__(
        self,
        *,
        app_key:             str,
        app_secret:          str   = "",
        cluster:             str   = "default",
        auth_endpoint:       str   = "/broadcasting/auth",
        auth_headers:        dict[str, str] | None = None,
        reconnect_delay:     float = 1.0,
        max_reconnect_delay: float = 30.0,
        max_retries:         int   = 5,
        activity_timeout:    float = 120.0,
        pong_timeout:        float = 30.0,
    ) -> None:
        super().__init__()

        self.app_key    = app_key
        self.app_secret = app_secret
        self.cluster    = cluster

        cluster_cfg    = CLUSTERS.get(cluster.lower(), CLUSTERS["default"])
        # Use plain ws:// for local, wss:// for all cloud clusters
        self._ws_base  = cluster_cfg["ws"] if cluster.lower() == "local" else cluster_cfg["wss"]
        self._api_base = cluster_cfg["api"]

        self.auth_endpoint = auth_endpoint
        self.auth_headers  = auth_headers or {}

        self.reconnect_delay     = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.max_retries         = max_retries
        self.activity_timeout    = activity_timeout
        self.pong_timeout        = pong_timeout

        # Public state
        self.socket_id: str | None   = None
        self.state: ConnectionState  = "initialized"

        # Internal
        self._ws:        Any                 = None
        self._channels:  dict[str, Channel]  = {}
        self._retries:   int                 = 0
        self._stop:      bool                = False
        self._connected: asyncio.Event       = asyncio.Event()
        self._recv_task: asyncio.Task | None = None

    # ─── URLs ─────────────────────────────────────────────────────────────────

    def _ws_url(self) -> str:
        params = urlencode({"app_key": self.app_key})
        return f"{self._ws_base}/ws?{params}"

    def _api_url(self) -> str:
        return f"{self._api_base}/api/v1/trigger"

    # ─── Connect ──────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open the WebSocket connection (called automatically by subscribe)."""
        self._stop = False
        await self._open()

    async def _open(self) -> None:
        """Internal — open socket and start receive loop."""
        self._set_state("connecting")
        try:
            self._ws = await websockets.connect(self._ws_url())
            logger.info("[AmarWave] WebSocket opened → %s", self._ws_url())
            self._recv_task = asyncio.create_task(self._recv_loop())
        except Exception as e:
            logger.warning("[AmarWave] Connect failed: %s", e)
            self._emit("error", e)
            await self._schedule_reconnect()

    async def _recv_loop(self) -> None:
        """Receive messages until the socket closes."""
        try:
            async for raw in self._ws:
                await self._handle_raw(raw)
        except ConnectionClosed as e:
            logger.warning("[AmarWave] Connection closed: %s", e)
        except Exception as e:
            logger.warning("[AmarWave] Receive error: %s", e)
        finally:
            await self._on_close()

    async def _handle_raw(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        # data field may be a JSON string itself
        if isinstance(msg.get("data"), str):
            try:
                msg["data"] = json.loads(msg["data"])
            except json.JSONDecodeError:
                pass

        await self._handle_message(msg)

    async def _handle_message(self, msg: dict) -> None:
        event   = msg.get("event", "")
        channel = msg.get("channel", "")
        data    = msg.get("data")

        if event == "amarwave:connection_established":
            self.socket_id = data.get("socket_id") if isinstance(data, dict) else None
            self._retries  = 0
            self._set_state("connected")
            self._connected.set()
            logger.info("[AmarWave] Connected — socket_id=%s", self.socket_id)
            # Re-subscribe all channels (handles reconnect)
            for ch in self._channels.values():
                ch.subscribed = False
                await self._do_subscribe(ch)

        elif event == "amarwave:error":
            msg_text = data.get("message", str(data)) if isinstance(data, dict) else str(data)
            logger.error("[AmarWave] Server error: %s", msg_text)
            self._emit("error", Exception(msg_text))

        elif event == "amarwave:pong":
            pass  # keepalive acknowledged

        elif event == "amarwave_internal:subscription_succeeded":
            ch = self._channels.get(channel)
            if ch:
                ch.subscribed = True
                ch._emit("subscribed", data)
                await ch._flush_queue()
                logger.info("[AmarWave] Subscribed → %s", channel)

        elif event == "amarwave_internal:subscription_error":
            ch = self._channels.get(channel)
            if ch:
                ch._emit("error", data)
                logger.warning("[AmarWave] Subscription error on %s: %s", channel, data)

        else:
            # Dispatch to channel listeners
            if channel and channel in self._channels:
                self._channels[channel]._emit(event, data)
            # Also bubble to instance listeners
            self._emit(event, {"channel": channel, "data": data})

    async def _on_close(self) -> None:
        self.socket_id = None
        self._connected.clear()
        for ch in self._channels.values():
            ch.subscribed = False
        self._set_state("disconnected")
        if not self._stop:
            await self._schedule_reconnect()

    async def _schedule_reconnect(self) -> None:
        if self.max_retries > 0 and self._retries >= self.max_retries:
            logger.warning("[AmarWave] Max retries reached — giving up.")
            return
        delay = min(self.reconnect_delay * (2 ** self._retries), self.max_reconnect_delay)
        self._retries += 1
        logger.info("[AmarWave] Reconnecting in %.1fs (attempt %d)…", delay, self._retries)
        await asyncio.sleep(delay)
        if not self._stop:
            await self._open()

    # ─── Disconnect ───────────────────────────────────────────────────────────

    async def disconnect(self) -> None:
        """Close the connection. No auto-reconnect after this."""
        self._stop = True
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws:
            await self._ws.close()
        self._set_state("disconnected")

    # ─── Subscribe ────────────────────────────────────────────────────────────

    async def subscribe(self, channel_name: str) -> Channel:
        """
        Subscribe to a channel. Auto-connects if needed.
        Returns a Channel — safe to bind events and publish immediately.

        Example::

            ch = await aw.subscribe("public-chat")
            ch.bind("message", lambda data: print(data))
        """
        if channel_name in self._channels:
            return self._channels[channel_name]

        ch = Channel(channel_name, self)
        self._channels[channel_name] = ch

        if self.state != "connected":
            if self.state == "initialized":
                asyncio.create_task(self._open())
            await self._connected.wait()

        await self._do_subscribe(ch)
        return ch

    async def unsubscribe(self, channel_name: str) -> None:
        """Unsubscribe from a channel."""
        if channel_name not in self._channels:
            return
        await self._raw_send({"event": "amarwave:unsubscribe", "data": {"channel": channel_name}})
        del self._channels[channel_name]

    def channel(self, channel_name: str) -> Channel | None:
        """Get an existing subscribed channel by name."""
        return self._channels.get(channel_name)

    # ─── Publish ──────────────────────────────────────────────────────────────

    async def publish(self, channel_name: str, event: str, data: Any = None) -> bool:
        """
        Top-level publish shortcut — no need to hold a channel reference.

        Example::

            await aw.publish("public-chat", "message", {"user": "Ali", "text": "Hi"})
        """
        return await self._http_publish(channel_name, event, data)

    async def _http_publish(self, channel: str, event: str, data: Any) -> bool:
        """Internal HTTP POST to /api/v1/trigger."""
        body = {
            "app_key":    self.app_key,
            "app_secret": self.app_secret,
            "channel":    channel,
            "event":      event,
            "data":       data,
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(self._api_url(), json=body, timeout=10.0)
            if res.status_code >= 400:
                logger.warning("[AmarWave] Publish failed %d: %s", res.status_code, res.text)
                return False
            return True
        except Exception as e:
            logger.warning("[AmarWave] Publish error: %s", e)
            return False

    # ─── Subscribe helpers ────────────────────────────────────────────────────

    async def _do_subscribe(self, ch: Channel) -> None:
        name    = ch.name
        payload: dict[str, Any] = {"event": "amarwave:subscribe", "data": {"channel": name}}

        try:
            if name.startswith("presence-"):
                if self.app_secret:
                    cd  = json.dumps({"user_id": generate_uid(), "user_info": {}})
                    sig = hmac_sha256(self.app_secret, f"{self.socket_id}:{name}:{cd}")
                    payload["data"]["auth"]         = f"{self.app_key}:{sig}"
                    payload["data"]["channel_data"] = cd
                else:
                    await self._server_auth(ch, payload)

            elif name.startswith("private-"):
                if self.app_secret:
                    sig = hmac_sha256(self.app_secret, f"{self.socket_id}:{name}")
                    payload["data"]["auth"] = f"{self.app_key}:{sig}"
                else:
                    await self._server_auth(ch, payload)

        except Exception as e:
            ch._emit("error", str(e))
            return

        await self._raw_send(payload)

    async def _server_auth(self, ch: Channel, payload: dict) -> None:
        """Fetch auth token from server auth_endpoint."""
        headers = {"Content-Type": "application/json", **self.auth_headers}
        body    = {"socket_id": self.socket_id, "channel_name": ch.name}
        async with httpx.AsyncClient() as client:
            res = await client.post(self.auth_endpoint, json=body, headers=headers, timeout=10.0)
        if res.status_code >= 400:
            raise Exception(f"Auth failed: {res.status_code}")
        payload["data"].update(res.json())

    # ─── Keepalive ────────────────────────────────────────────────────────────

    async def listen(self) -> None:
        """
        Block forever, keeping the connection alive with periodic pings.
        Call this at the end of your main() to prevent the program from exiting.

        Example::

            await aw.listen()
        """
        while not self._stop:
            await asyncio.sleep(self.activity_timeout)
            if self._ws and self.state == "connected":
                await self._raw_send({"event": "amarwave:ping", "data": {}})

    # ─── Utilities ────────────────────────────────────────────────────────────

    async def _raw_send(self, payload: dict) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps(payload))
            except Exception as e:
                logger.warning("[AmarWave] Send error: %s", e)

    def _set_state(self, state: ConnectionState) -> None:
        self.state = state
        self._emit(state)
