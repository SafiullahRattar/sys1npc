"""Provider protocol and shared error types.

A provider maps a ``DecisionRequest`` to a single chosen action id — an opaque
id already present in ``request.offers``. Providers are synchronous and, except
for game-aware ones, must not interpret game mechanics: generic providers judge
the offered descriptions against the observation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts import DecisionRequest, ProviderResult


class ProviderError(RuntimeError):
    """A provider could not answer (network, auth, timeout, bad reply)."""


class ProviderTimeout(ProviderError):
    """The provider exceeded the coordinator's time budget."""


@runtime_checkable
class Provider(Protocol):
    name: str

    def choose(self, request: DecisionRequest) -> ProviderResult: ...
