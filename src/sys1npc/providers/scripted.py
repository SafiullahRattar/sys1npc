"""Scripted provider: deterministic, offline, the "before" picture.

Picks an action from ``request.offers`` with a deterministic rule so the whole
core runs and is testable with no network and no keys. It is also the default
fallback the coordinator uses when a model provider fails.
"""

from __future__ import annotations

from collections.abc import Callable

from ..contracts import DecisionRequest, ProviderResult
from .base import ProviderError

Selector = Callable[[DecisionRequest], str]


def first_offer(request: DecisionRequest) -> str:
    """The default rule: pick the first offered action."""
    return request.offers[0].id


class ScriptedProvider:
    name = "scripted"

    def __init__(self, select: Selector = first_offer):
        self._select = select

    def choose(self, request: DecisionRequest) -> ProviderResult:
        action_id = self._select(request)
        if action_id not in {offer.id for offer in request.offers}:
            raise ProviderError(f"scripted selector returned unknown action {action_id!r}")
        return ProviderResult(action_id=action_id, model="scripted")
