"""Contract shape tests (no providers, no network)."""

from __future__ import annotations

from sys1npc.contracts import ActionOffer, DecisionRequest


def test_action_offer_fields():
    offer = ActionOffer(id="move:2", description="Rock Throw")
    assert offer.id == "move:2"
    assert offer.description == "Rock Throw"


def test_request_fields(make_request):
    req = make_request()
    assert isinstance(req, DecisionRequest)
    assert req.session_id == "session-1"
    assert req.request_id == "request-1"
    assert req.game == "pokemon-firered"
    assert req.actor == "brock"
    assert req.decision == "battle.action"
    assert req.observation["turn"] == 3
    assert [o.id for o in req.offers] == ["move:a", "move:b", "switch:1"]


def test_offers_are_opaque_to_core():
    # The core never interprets ids: it only sees opaque strings.
    req = DecisionRequest(
        session_id="s",
        request_id="r",
        game="g",
        actor="a",
        decision="battle.action",
        observation={},
        offers=(ActionOffer("item:13", "Use a Potion on Geodude"),),
    )
    assert req.offers[0].id == "item:13"
