"""Shared fixtures and a controllable stub provider for offline tests."""

from __future__ import annotations

import time

import pytest

from sys1npc.contracts import ActionOffer, DecisionRequest, ProviderResult


class StubProvider:
    """A provider whose behavior is configured per test."""

    name = "stub"

    def __init__(
        self,
        action_id: str | None = None,
        *,
        request_id: str | None = None,
        error: Exception | None = None,
        delay: float = 0.0,
    ):
        self.action_id = action_id
        self.request_id = request_id
        self.error = error
        self.delay = delay
        self.calls = 0

    def choose(self, request: DecisionRequest) -> ProviderResult:
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.error is not None:
            raise self.error
        assert self.action_id is not None, "stub not configured with an action"
        return ProviderResult(action_id=self.action_id, request_id=self.request_id)


@pytest.fixture
def offers() -> tuple[ActionOffer, ...]:
    return (
        ActionOffer("move:a", "Tackle, ~10 dmg, no effect on Rock."),
        ActionOffer("move:b", "Ember, ~15 dmg, would KO the active foe."),
        ActionOffer("switch:1", "Swap to Bulbasaur for a better matchup."),
    )


@pytest.fixture
def make_request(offers):
    def _make(**overrides) -> DecisionRequest:
        base = dict(
            session_id="session-1",
            request_id="request-1",
            game="pokemon-firered",
            actor="brock",
            decision="battle.action",
            observation={"turn": 3, "own": {"active": "geodude", "hp": 14}},
            offers=offers,
        )
        base.update(overrides)
        return DecisionRequest(**base)

    return _make


@pytest.fixture
def make_stub():
    def _make(action_id: str | None = None, **kwargs) -> StubProvider:
        return StubProvider(action_id, **kwargs)

    return _make
