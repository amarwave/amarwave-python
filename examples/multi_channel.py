"""
AmarWave Python — Multiple Channels Example
Subscribe to several channels simultaneously.
"""
import asyncio
from amarwave import AmarWave


async def main() -> None:
    aw = AmarWave(
        app_key = "YOUR_APP_KEY",
        app_secret = "YOUR_APP_SECRET",
        cluster = "default",
    )

    # Subscribe to multiple channels
    chat     = await aw.subscribe("public-chat")
    news     = await aw.subscribe("public-news")
    orders   = await aw.subscribe("private-orders")

    # Bind events on each channel independently
    chat.bind("message",      lambda d: print(f"[Chat] {d['user']}: {d['text']}"))
    news.bind("article",      lambda d: print(f"[News] {d['title']}"))
    orders.bind("new-order",  lambda d: print(f"[Order] #{d['id']} — ${d['total']}"))

    # Publish to a specific channel
    await chat.publish("message", {"user": "Bot", "text": "Server online!"})

    # Or use the top-level shortcut
    await aw.publish("public-news", "article", {"title": "Breaking news!"})

    await aw.listen()


asyncio.run(main())
