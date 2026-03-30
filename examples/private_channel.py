"""
AmarWave Python — Private Channel Example
Subscribe to a private channel using client-side HMAC auth.
"""
import asyncio
from amarwave import AmarWave


async def main() -> None:
    aw = AmarWave(
        app_key    = "YOUR_APP_KEY",
        app_secret = "YOUR_APP_SECRET",   # signs private channels automatically
        ws_host    = "localhost",
        ws_port    = 3001,
        api_port   = 8000,
    )

    # Private channel — auth is handled automatically using app_secret
    ch = await aw.subscribe("private-orders")

    ch.bind("subscribed",    lambda _: print("✓ Subscribed to private-orders"))
    ch.bind("error",         lambda e: print(f"Auth error: {e}"))
    ch.bind("order-updated", lambda d: print(f"Order update: {d}"))

    await aw.listen()


asyncio.run(main())
