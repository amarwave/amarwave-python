"""
AmarWave WebSocket Full Connection Stability Test — Python SDK
Tests: connect → subscribe → receive event → 5-event burst → re-subscribe → disconnect
"""

import asyncio
import json
import sys
import httpx

sys.path.insert(0, ".")
from amarwave import AmarWave

APP_KEY    = "bb33c993bf087098b7760bd6ea4fbbfb"
APP_SECRET = "0d5e2bdb023758ff57cd544983370dbce4c47f697b218dae1e89dfe3f8a836bd"
CHANNEL    = "ws-stability-test"
API_URL    = "https://amarwave.com/api/v1/trigger"

passed = 0
failed = 0

def ok(label: str):
    global passed
    print(f"  ✅ {label}")
    passed += 1

def fail(label: str, reason: str):
    global failed
    print(f"  ❌ {label}: {reason}")
    failed += 1


async def trigger_event(event_name: str, data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.post(API_URL, json={
            "app_key":    APP_KEY,
            "app_secret": APP_SECRET,
            "channel":    CHANNEL,
            "name":       event_name,
            "data":       data,
        }, timeout=10.0)
    return {"status": res.status_code, "body": res.text}


async def wait_for_channel_event(ch, event: str, timeout: float = 8.0):
    """Wait for a specific event on a channel."""
    fut = asyncio.get_event_loop().create_future()

    def handler(data):
        if not fut.done():
            fut.set_result(data)

    ch.bind(event, handler)
    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"timeout ({timeout}s) waiting for channel event '{event}'")


async def run_tests():
    global passed, failed

    print("\n====================================================")
    print("  AmarWave WebSocket Stability Test (Python SDK)")
    print("====================================================\n")

    aw = AmarWave(app_key=APP_KEY, app_secret=APP_SECRET, cluster="default")

    # ── TEST 1: Connect ────────────────────────────────────────────────────────
    print("[ 1 ] Connect")
    await aw.connect()
    # Wait until actually connected
    for _ in range(50):
        if aw.state == "connected":
            break
        await asyncio.sleep(0.1)
    if aw.state == "connected":
        ok(f"Connected — socket_id: {aw.socket_id}")
    else:
        fail("Connect", f"state = {aw.state}")
        await aw.disconnect()
        return

    # ── TEST 2: Subscribe ──────────────────────────────────────────────────────
    print("\n[ 2 ] Subscribe to channel")
    sub_task = asyncio.create_task(aw.subscribe(CHANNEL))
    ch = await sub_task
    ok(f"Subscribed to '{CHANNEL}'")

    # ── TEST 3: Round-trip event ───────────────────────────────────────────────
    print("\n[ 3 ] Trigger event via HTTP → receive on WebSocket (round-trip)")
    test_payload = {"test": "round-trip", "sdk": "python"}

    recv_task = asyncio.create_task(wait_for_channel_event(ch, "sdk-ping", 8.0))
    api_res = await trigger_event("sdk-ping", test_payload)

    if 200 <= api_res["status"] < 300:
        ok(f"HTTP trigger returned {api_res['status']}: {api_res['body'][:60]}")
    else:
        fail("HTTP trigger", f"HTTP {api_res['status']}: {api_res['body']}")

    try:
        d = await recv_task
        ok("Event 'sdk-ping' received on WebSocket")
        if d.get("test") == "round-trip" and d.get("sdk") == "python":
            ok(f"Payload verified — test: '{d['test']}', sdk: '{d['sdk']}'")
        else:
            fail("Payload match", f"got: {json.dumps(d)}")
    except TimeoutError as e:
        fail("Event receive (round-trip)", str(e))

    # ── TEST 4: Burst — 5 rapid events ────────────────────────────────────────
    print("\n[ 4 ] Send 5 rapid events — verify all received")
    received = []

    def burst_handler(data):
        if isinstance(data, dict) and "seq" in data:
            received.append(data["seq"])

    ch.bind("sdk-burst", burst_handler)

    for i in range(1, 6):
        await trigger_event("sdk-burst", {"seq": i})
        await asyncio.sleep(0.1)

    await asyncio.sleep(3.0)  # let all events arrive

    if len(received) == 5:
        ok(f"All 5 burst events received: {sorted(received)}")
    else:
        fail("Burst events", f"received {len(received)}/5: {received}")

    # ── TEST 5: Connection still alive ────────────────────────────────────────
    print("\n[ 5 ] Connection still open after burst")
    if aw.state == "connected":
        ok('connection.state = "connected"')
    else:
        fail("Connection alive", f"state = {aw.state}")

    # ── TEST 6: Unsubscribe ────────────────────────────────────────────────────
    print("\n[ 6 ] Unsubscribe")
    await aw.unsubscribe(CHANNEL)
    await asyncio.sleep(0.5)
    ok("Unsubscribed successfully")

    # ── TEST 7: Re-subscribe on same connection ────────────────────────────────
    print("\n[ 7 ] Re-subscribe on same connection")
    ch2 = await aw.subscribe(CHANNEL)
    ok("Re-subscribed successfully")

    resub_task = asyncio.create_task(wait_for_channel_event(ch2, "sdk-resub", 8.0))
    await trigger_event("sdk-resub", {"verify": "resub-ok"})
    try:
        d = await resub_task
        ok(f"Event received after re-subscribe — data: {json.dumps(d)}")
    except TimeoutError as e:
        fail("Re-subscribe event receive", str(e))

    # ── TEST 8: Clean disconnect ───────────────────────────────────────────────
    print("\n[ 8 ] Clean disconnect")
    await aw.disconnect()
    await asyncio.sleep(0.5)
    if aw.state == "disconnected":
        ok('Disconnected — state = "disconnected"')
    else:
        fail("Clean disconnect", f"state = {aw.state}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n====================================================")
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("====================================================\n")
    sys.exit(1 if failed > 0 else 0)


asyncio.run(run_tests())
