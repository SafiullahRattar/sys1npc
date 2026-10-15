"""sys1npc — a small, mechanics-free decision core for game NPCs.

The foundation for a FireRed trainer-battle AI. The core never interprets game
state or action ids; it only guarantees a safe, validated decision. See
``docs/architecture.md``.
"""

from __future__ import annotations

from .contracts import ActionOffer, Decision, DecisionRequest, ProviderResult
from .coordinator import Coordinator, InvalidRequest
from .providers import (
    JevProvider,
    Provider,
    ProviderError,
    ProviderTimeout,
    ScriptedProvider,
)

__all__ = [
    "ActionOffer",
    "Coordinator",
    "Decision",
    "DecisionRequest",
    "InvalidRequest",
    "JevProvider",
    "Provider",
    "ProviderError",
    "ProviderResult",
    "ProviderTimeout",
    "ScriptedProvider",
]

__version__ = "0.1.0"
