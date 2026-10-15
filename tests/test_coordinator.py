"""Coordinator validation, fallback, and deadline behavior — all offline."""

from __future__ import annotations

import pytest

from sys1npc.contracts import ActionOffer
from sys1npc.coordinator import Coordinator, InvalidRequest
from sys1npc.providers.base import ProviderError
from sys1npc.providers.scripted import ScriptedProvider


def test_valid_complete_action_selection(make_request, make_stub):
    decision = Coordinator(provider=make_stub("move:b")).decide(make_request())
    assert decision.action_id == "move:b"
    assert decision.source == "stub"
    assert decision.error is None
    assert decision.session_id == "session-1"
    assert decision.request_id == "request-1"


def test_empty_offers_rejected(make_request):
    with pytest.raises(InvalidRequest):
        Coordinator().decide(make_request(offers=()))


def test_duplicate_offers_rejected(make_request):
    with pytest.raises(InvalidRequest):
        Coordinator().decide(
            make_request(offers=(ActionOffer("move:a", "x"), ActionOffer("move:a", "y")))
        )


def test_empty_request_id_rejected(make_request):
    with pytest.raises(InvalidRequest):
        Coordinator().decide(make_request(request_id=""))


def test_unoffered_action_falls_back_to_scripted(make_request, make_stub):
    decision = Coordinator(provider=make_stub("item:999")).decide(make_request())
    assert decision.action_id == "move:a"  # scripted picks first offer
    assert decision.source == "scripted"
    assert decision.error is None


def test_stale_response_rejected(make_request, make_stub):
    coord = Coordinator(provider=make_stub("move:b", request_id="other-request"))
    decision = coord.decide(make_request())
    assert decision.action_id == "move:a"  # rejected, fell back
    assert decision.source == "scripted"


def test_provider_error_falls_back(make_request, make_stub):
    coord = Coordinator(provider=make_stub(error=ProviderError("boom")))
    decision = coord.decide(make_request())
    assert decision.action_id == "move:a"
    assert decision.source == "scripted"


def test_provider_timeout_falls_back(make_request, make_stub):
    coord = Coordinator(provider=make_stub("move:b", delay=0.3), max_wait_ms=50)
    decision = coord.decide(make_request())
    assert decision.action_id == "move:a"
    assert decision.source == "scripted"


def test_deadline_bounds_call(make_request, make_stub):
    # The request's deadline (shorter than max_wait) bounds the provider call.
    coord = Coordinator(provider=make_stub("move:b", delay=0.3), max_wait_ms=10_000)
    decision = coord.decide(make_request(deadline_ms=50))
    assert decision.action_id == "move:a"
    assert decision.source == "scripted"


def test_all_providers_fail_returns_no_action(make_request, make_stub):
    coord = Coordinator(provider=make_stub(error=ProviderError("down")), fallback=None)
    decision = coord.decide(make_request())
    assert decision.action_id is None
    assert decision.source == "none"
    assert "down" in decision.error


def test_no_provider_uses_scripted_default(make_request):
    decision = Coordinator().decide(make_request())
    assert decision.action_id == "move:a"
    assert decision.source == "scripted"


def test_explicit_fallback_chain(make_request, make_stub):
    coord = Coordinator(
        provider=make_stub(error=ProviderError("down")),
        fallback=ScriptedProvider(),
    )
    decision = coord.decide(make_request())
    assert decision.action_id == "move:a"
    assert decision.source == "scripted"
