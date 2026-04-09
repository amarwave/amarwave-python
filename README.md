# amarwave

Official Python client for [AmarWave](https://amarwave.com) real-time messaging — async, typed, zero boilerplate.

[![PyPI version](https://img.shields.io/pypi/v/amarwave)](https://pypi.org/project/amarwave/)
[![Python](https://img.shields.io/pypi/pyversions/amarwave)](https://pypi.org/project/amarwave/)
[![License](https://img.shields.io/pypi/l/amarwave)](LICENSE)

---

## Installation

```bash
pip install amarwave
```

---

## Quick Start

```python
import asyncio
from amarwave import AmarWave

async def main():
    aw = AmarWave(
        app_key    = "YOUR_APP_KEY",
        app_secret = "YOUR_APP_SECRET",
    )

    ch = await aw.subscribe("public-chat")
    ch.bind("message", lambda data: print(data["user"], data["text"]))

    await ch.publish("message", {"user": "Ali", "text": "Hello!"})
    await aw.listen()  # keep alive forever

asyncio.run(main())
```

---

## Configuration

| Parameter             | Type  | Default          | Description                                    |
|-----------------------|-------|------------------|------------------------------------------------|
| `app_key`             | str   | —                | Your app key **(required)**                    |
| `app_secret`          | str   | `""`             | App secret for HMAC channel auth               |
| `cluster`             | str   | `"default"`      | `"default"` \| `"eu"` \| `"us"` \| `"ap1"` \| `"ap2"` |
| `auth_endpoint`       | str   | `"/broadcasting/auth"` | Server auth URL for private/presence channels |
| `auth_headers`        | dict  | `{}`             | Headers sent to the auth endpoint              |
| `reconnect_delay`     | float | `1.0`            | Base reconnect delay in seconds                |
| `max_reconnect_delay` | float | `30.0`           | Max reconnect delay in seconds                 |
| `max_retries`         | int   | `5`              | Max reconnect attempts (0 = infinite)          |
| `activity_timeout`    | float | `120.0`          | Seconds between keepalive pings                |
| `pong_timeout`        | float | `30.0`           | Seconds to wait for pong before reconnecting   |

### Clusters

All clusters connect to `amarwave.com`. The `cluster` parameter is reserved for future regional routing.

| Cluster   | WebSocket                  | API                        |
|-----------|----------------------------|----------------------------|
| `default` | `wss://amarwave.com`       | `https://amarwave.com`     |
| `eu`      | `wss://amarwave.com`       | `https://amarwave.com`     |
| `us`      | `wss://amarwave.com`       | `https://amarwave.com`     |
| `ap1`     | `wss://amarwave.com`       | `https://amarwave.com`     |
| `ap2`     | `wss://amarwave.com`       | `https://amarwave.com`     |

```python
aw = AmarWave(app_key="KEY", app_secret="SECRET", cluster="eu")
```

---

## Channel API

```python
ch = await aw.subscribe("public-chat")

ch.bind("message", handler)           # listen for event
ch.bind_global(lambda e, d: ...)      # listen for all events on this channel
ch.unbind("message", handler)         # remove listener
await ch.publish("message", data)     # publish via HTTP API → bool
await aw.publish("ch", "ev", data)    # top-level publish shortcut

ch.name        # "public-chat"
ch.subscribed  # True when server confirmed subscription
```

---

## Connection Events

```python
aw.bind("connecting",   lambda _: print("Connecting…"))
aw.bind("connected",    lambda _: print(f"Connected: {aw.socket_id}"))
aw.bind("disconnected", lambda _: print("Disconnected"))
aw.bind("error",        lambda e: print(f"Error: {e}"))
```

---

## Private & Presence Channels

```python
# Client-side HMAC auth (app_secret required)
aw = AmarWave(app_key="KEY", app_secret="SECRET")
ch = await aw.subscribe("private-orders")    # auto-signed
ch = await aw.subscribe("presence-room-1")  # auto-signed

# Server-side auth (omit app_secret, provide auth_endpoint)
aw = AmarWave(
    app_key       = "KEY",
    auth_endpoint = "https://yourapp.com/api/broadcasting/auth",
    auth_headers  = {"Authorization": f"Bearer {token}"},
)
ch = await aw.subscribe("private-orders")
```

---

## Django Integration

```python
import asyncio
from amarwave import AmarWave

# One-shot publish from a sync Django view
def notify_user(user_id: int, message: str) -> bool:
    async def _publish() -> bool:
        aw = AmarWave(app_key="KEY", app_secret="SECRET")
        return await aw.publish(f"private-user-{user_id}", "notification", {"message": message})
    return asyncio.run(_publish())
```

---

## FastAPI Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from amarwave import AmarWave

aw = AmarWave(app_key="KEY", app_secret="SECRET")

@asynccontextmanager
async def lifespan(app: FastAPI):
    ch = await aw.subscribe("public-updates")
    ch.bind("message", lambda d: print(d))
    yield
    await aw.disconnect()

app = FastAPI(lifespan=lifespan)

@app.post("/notify")
async def notify(message: str):
    await aw.publish("public-updates", "message", {"text": message})
    return {"ok": True}
```

---

## Requirements

- Python 3.10+
- `websockets >= 12.0`
- `httpx >= 0.27.0`

---

## License

MIT © AmarWave
