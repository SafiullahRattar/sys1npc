"""Typed request/response contracts for a game decision.

These types are the only thing a game adapter and a provider must agree on.
They are deliberately small and mechanics-free: the coordinator never reads the
observation and never interprets an action id beyond checking that a chosen id
was actually offered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionOffer:
    """One legal action, offered to the provider as an opaque id + description.

    ``id`` is opaque to the core; the adapter owns its meaning (``move:2``,
    ``switch:1``, ``item:13``, ``forced-replace:0``, ...). The provider picks by
    reading ``description``; the coordinator only checks membership.
    """

    id: str
    description: str


@dataclass(frozen=True)
class DecisionRequest:
    """One decision the game needs right now.

    ``observation`` is game-specific and opaque to the coordinator and to any
    provider that is not game-aware. It carries only what the actor is allowed
    to know — the adapter owns the observed-information policy.

    ``offers`` are the complete set of legal actions. They must be non-empty and
    have unique ids; the coordinator validates both and refuses otherwise.

    ``deadline_ms`` is the game's desired upper bound on a provider answer. It
    is advisory: the coordinator will not wait longer than this (or its own
    cap), but a deadline is not a game-side watchdog (see ``docs/architecture.md``).
    """

    session_id: str
    request_id: str
    game: str
    actor: str
    decision: str
    observation: Any
    offers: tuple[ActionOffer, ...]
    deadline_ms: int | None = None


@dataclass(frozen=True)
class ProviderResult:
    """What a provider returned for one request.

    ``request_id`` is optional so a provider that cannot echo the id (a plain
    HTTP call) stays usable; when present it must equal the request's id, or the
    coordinator rejects the result as stale.
    """

    action_id: str
    model: str | None = None
    latency_ms: int = 0
    request_id: str | None = None


@dataclass(frozen=True)
class Decision:
    """The coordinator's answer to a ``DecisionRequest``.

    ``action_id is None`` means "no decision": no provider produced a legal
    action, so the adapter must fall back to the game's original AI. ``error``
    records why.
    """

    session_id: str
    request_id: str
    action_id: str | None
    source: str  # provider name ("jev", "scripted", ...) or "none"
    error: str | None = None
    model: str | None = None
    latency_ms: int = 0
