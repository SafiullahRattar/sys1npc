"""Jev provider — TypeSafe's System One model.

Wire format, verified against first-party docs (2026-10-15):

    POST https://api.typesafe.ai/v1/systemone
    Authorization: Bearer <TYPESAFE_API_KEY>
    Content-Type: application/json
    body:
      {
        "state": <request.observation>,
        "model": <model>,
        "questions": {
          <request.decision>: {
            "type": "choice",
            "instructions": "...",
            "criteria": {<action_id>: <description>, ...}
          }
        }
      }

Response: ``{"model": ..., "answers": {<decision>: {"type": "choice",
"choice": <action_id>, "probabilities": {...}, "confidence": ...}},
"usage": {...}}``.

The default model is pinned to ``jev-1.13.0``, the versioned stable release the
``jev-latest`` alias currently points at. The alias itself moves with releases,
so do not rely on it; override via the ``model=`` constructor argument.
``jev-1.14.0`` is a newer preview and is not the default.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..contracts import DecisionRequest, ProviderResult
from .base import ProviderError

DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-1.13.0"  # pinned stable; alias "jev-latest" -> "jev-1.13.0" (2026-10-15)


class JevProvider:
    name = "jev"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    def payload(self, request: DecisionRequest) -> dict[str, Any]:
        return {
            "state": request.observation,
            "model": self.model,
            "questions": {
                request.decision: {
                    "type": "choice",
                    "instructions": (
                        f"Choose the best action for {request.actor} "
                        f"({request.game}) at decision point {request.decision}."
                    ),
                    "criteria": {offer.id: offer.description for offer in request.offers},
                }
            },
        }

    def parse_choice(self, data: dict[str, Any], request: DecisionRequest) -> tuple[str, str]:
        """Return ``(action_id, model)`` from a Jev response body."""
        answer = (data.get("answers") or {}).get(request.decision)
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise ProviderError(f"jev response missing choice answer for {request.decision!r}")
        action_id = answer.get("choice")
        if not action_id:
            raise ProviderError("jev response missing 'choice'")
        return str(action_id), str(data.get("model") or self.model)

    def choose(self, request: DecisionRequest) -> ProviderResult:
        started = time.perf_counter()
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            resp = client.post(
                f"{self.base_url}/v1/systemone",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=self.payload(request),
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"jev request failed: {exc}") from exc
        finally:
            if self._client is None:
                client.close()

        if resp.status_code != 200:
            detail = resp.text[:300]
            raise ProviderError(f"jev HTTP {resp.status_code}: {detail}")

        action_id, model = self.parse_choice(resp.json(), request)
        return ProviderResult(
            action_id=action_id,
            model=model,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
