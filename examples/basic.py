"""
AmarWave Python — Basic Example
Subscribe to a public channel and send a message.
"""
import asyncio
from amarwave import AmarWave


async def main() -> None:
    # 1. Create client
    aw = AmarWave(
        app_key    = "YOUR_APP_KEY",
        app_secret = "YOUR_APP_SECRET",
    )

    # 2. Connection lifecycle events (optional)
    aw.bind("connecting",   lambda _: print("Connecting…"))
    aw.bind("connected",    lambda _: print(f"Connected — socket_id: {aw.socket_id}"))
    aw.bind("disconnected", lambda _: print("Disconnected"))
    aw.bind("error",        lambda e: print(f"Error: {e}"))

    # 3. Subscribe — auto-connects
    ch = await aw.subscribe("public-chat")

    # 4. Listen for events
    def on_message(data: dict) -> None:
        print(f"[{data['user']}] {data['text']}")

    ch.bind("subscribed", lambda _: print("Joined channel"))
    ch.bind("message",    on_message)

    # 5. Publish a message
    await ch.publish("message", {"user": "Ali", "text": "Hello from Python!"})

    # 6. Keep alive
    await aw.listen()


asyncio.run(main())
