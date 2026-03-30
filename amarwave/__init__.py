"""
AmarWave Python Client v2.0.0
Real-time WebSocket client for AmarWave servers.

Example::

    import asyncio
    from amarwave import AmarWave

    async def main():
        aw = AmarWave(app_key="YOUR_KEY", app_secret="YOUR_SECRET")

        ch = await aw.subscribe("public-chat")

        ch.bind("message", lambda data: print(data["user"], data["text"]))

        await ch.publish("message", {"user": "Ali", "text": "Hello!"})

        await aw.listen()   # keep alive forever

    asyncio.run(main())
"""

from .client  import AmarWave
from .channel import Channel
from .emitter import EventEmitter
from .types   import ConnectionState, CLUSTERS

__all__ = [
    "AmarWave",
    "Channel",
    "EventEmitter",
    "ConnectionState",
    "CLUSTERS",
]

__version__ = "2.0.0"
