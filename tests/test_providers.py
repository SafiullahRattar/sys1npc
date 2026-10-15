"""Provider wire-format and behavior tests — all offline."""

from __future__ import annotations

import pytest

from sys1npc.contracts import ActionOffer, DecisionRequest
from sys1npc.providers.base import ProviderError
from sys1npc.providers.jev import DEFAULT_MODEL, JevProvider
from sys1npc.providers.scripted import ScriptedProvider


def request(**overrides) -> DecisionRequest:
    base = dict(
        session_id="s1",
        request_id="r1",
        game="pokemon-firered",
        actor="brock",
        decision="battle.action",
        observation={"turn": 5},
        offers=(
            ActionOffer("move:a", "Tackle, ~10 dmg"),
            ActionOffer("move:b", "Ember, would KO"),
        ),
    )
    base.update(overrides)
    return DecisionRequest(**base)


# -- scripted ---------------------------------------------------------------


def test_scripted_defaults_to_first_offer():
    result = ScriptedProvider().choose(request())
    assert result.action_id == "move:a"
    assert result.model == "scripted"


def test_scripted_custom_selector():
    provider = ScriptedProvider(select=lambda req: req.offers[-1].id)
    assert provider.choose(request()).action_id == "move:b"


def test_scripted_rejects_unknown_action():
    provider = ScriptedProvider(select=lambda req: "nope")
    with pytest.raises(ProviderError):
        provider.choose(request())


# -- jev wire format --------------------------------------------------------


def test_jev_payload_shape():
    payload = JevProvider(api_key="k").payload(request())
    assert payload["model"] == DEFAULT_MODEL == "jev-1.13.0"
    assert payload["state"] == {"turn": 5}
    q = payload["questions"]["battle.action"]
    assert q["type"] == "choice"
    assert q["criteria"] == {"move:a": "Tackle, ~10 dmg", "move:b": "Ember, would KO"}


def test_jev_parse_choice():
    provider = JevProvider(api_key="k")
    body = {
        "model": "jev-1.13.0",
        "answers": {
            "battle.action": {
                "type": "choice",
                "choice": "move:b",
                "probabilities": {"move:a": 0.2, "move:b": 0.8},
                "confidence": 0.8,
            }
        },
        "usage": {"input_tokens": 300, "output_tokens": 10},
    }
    action_id, model = provider.parse_choice(body, request())
    assert action_id == "move:b"
    assert model == "jev-1.13.0"


def test_jev_parse_missing_answer():
    provider = JevProvider(api_key="k")
    with pytest.raises(ProviderError):
        provider.parse_choice({"answers": {}}, request())
