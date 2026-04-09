"""
AmarWave — Type definitions.
"""

from __future__ import annotations

from typing import Any, Callable, Literal

# ── Connection state ──────────────────────────────────────────────────────────

ConnectionState = Literal["initialized", "connecting", "connected", "disconnected"]

# ── Callback types ────────────────────────────────────────────────────────────

EventCallback = Callable[[Any], None]
GlobalCallback = Callable[[str, Any], None]

# ── Cluster map ───────────────────────────────────────────────────────────────

ClusterName = Literal["default", "local", "eu", "us", "ap1", "ap2"]

CLUSTERS: dict[str, dict[str, str]] = {
    "default": {
        "ws": "ws://amarwave.com",
        "wss": "wss://amarwave.com",
        "api": "https://amarwave.com",
    },
    "local": {
        "ws": "ws://amarwave.com",
        "wss": "wss://amarwave.com",
        "api": "https://amarwave.com",
    },
    "eu": {"ws": "ws://amarwave.com", "wss": "wss://amarwave.com", "api": "https://amarwave.com"},
    "us": {"ws": "ws://amarwave.com", "wss": "wss://amarwave.com", "api": "https://amarwave.com"},
    "ap1": {"ws": "ws://amarwave.com", "wss": "wss://amarwave.com", "api": "https://amarwave.com"},
    "ap2": {"ws": "ws://amarwave.com", "wss": "wss://amarwave.com", "api": "https://amarwave.com"},
}
