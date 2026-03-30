"""
AmarWave Python — Django / sync context usage.

In Django views or management commands, wrap async calls with asyncio.run().
For background tasks, use celery or a dedicated asyncio thread.
"""
import asyncio
from amarwave import AmarWave


# ── Option 1: One-shot publish from a sync Django view ────────────────────────

def publish_from_django(channel: str, event: str, data: dict) -> bool:
    """
    Fire-and-forget publish from any sync Django view.
    Creates a temporary AmarWave client just for the HTTP publish.
    """
    async def _publish() -> bool:
        aw = AmarWave(app_key="YOUR_KEY", app_secret="YOUR_SECRET")
        return await aw.publish(channel, event, data)

    return asyncio.run(_publish())


# ── Option 2: Django management command with long-lived connection ────────────

# yourapp/management/commands/amarwave_listener.py
#
# from django.core.management.base import BaseCommand
# from amarwave import AmarWave
# import asyncio
#
# class Command(BaseCommand):
#     help = "Listen to AmarWave events"
#
#     def handle(self, *args, **options):
#         asyncio.run(self._run())
#
#     async def _run(self):
#         aw = AmarWave(app_key="KEY", app_secret="SECRET")
#         ch = await aw.subscribe("public-chat")
#         ch.bind("message", lambda d: self.stdout.write(f"{d['user']}: {d['text']}"))
#         await aw.listen()


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ok = publish_from_django("public-chat", "message", {"user": "Django", "text": "Hello!"})
    print("Published:", ok)
