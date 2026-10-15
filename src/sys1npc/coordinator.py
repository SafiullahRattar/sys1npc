"""The shared coordinator: requests in, validated decisions out.

The coordinator is deliberately ignorant of Pokemon mechanics. It does not read
``observation``, does not decode action ids, and has no type chart. Its whole
job is to return a *safe* decision:

1. validate the request (non-empty ids, non-empty and unique offers);
2. ask the primary provider within a bounded time budget;
3. on failure, ask the fallback provider (scripted by default);
4. validate the answer (membership and correlation) and return it;
5. if nothing produced a legal action, return ``action_id=None`` so the adapter
   falls back to the game's original AI.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from .contracts import Decision, DecisionRequest, ProviderResult
from .providers.base import Provider, ProviderError
from .providers.scripted import ScriptedProvider

_DEFAULT_FALLBACK = object()


class InvalidRequest(ValueError):
    """The request is malformed (empty ids, empty offers, or duplicate offer ids)."""


class Coordinator:
    def __init__(
        self,
        provider: Provider | None = None,
        *,
        fallback: object = _DEFAULT_FALLBACK,
        max_wait_ms: int = 1500,
    ):
        self.provider = provider
        # Default fallback is the deterministic scripted provider: the offline
        # "before" picture and the safety net when a model provider fails.
        self.fallback = ScriptedProvider() if fallback is _DEFAULT_FALLBACK else fallback
        self.max_wait_ms = max_wait_ms

    # -- public ------------------------------------------------------------

    def decide(self, request: DecisionRequest) -> Decision:
        """Return a validated ``Decision`` for ``request``.

        Never raises on a provider failure; only ``InvalidRequest`` propagates
        (a malformed request is a caller bug, not a recoverable runtime event).
        """
        self._validate(request)

        last_error: str | None = None
        for provider, source in self._chain():
            result, error = self._bounded(provider, request)
            if error is not None:
                last_error = error
                continue
            reject = self._reject_reason(request, result)
            if reject is not None:
                last_error = reject
                continue
            return Decision(
                session_id=request.session_id,
                request_id=request.request_id,
                action_id=result.action_id,
                source=source,
                model=result.model,
                latency_ms=result.latency_ms,
            )

        return Decision(
            session_id=request.session_id,
            request_id=request.request_id,
            action_id=None,
            source="none",
            error=last_error or "no provider configured",
        )

    # -- internals ---------------------------------------------------------

    def _chain(self):
        if self.provider is not None:
            yield self.provider, self.provider.name
        if self.fallback is not None and self.fallback is not self.provider:
            yield self.fallback, self.fallback.name

    def _validate(self, request: DecisionRequest) -> None:
        if not request.session_id or not request.request_id:
            raise InvalidRequest("session_id and request_id must be non-empty")
        if not request.offers:
            raise InvalidRequest("offers must be non-empty")
        ids = [offer.id for offer in request.offers]
        if len(ids) != len(set(ids)):
            raise InvalidRequest("offer ids must be unique")
        if any(not offer_id for offer_id in ids):
            raise InvalidRequest("offer ids must be non-empty")

    def _reject_reason(self, request: DecisionRequest, result: ProviderResult) -> str | None:
        if result.request_id is not None and result.request_id != request.request_id:
            return f"stale response (request_id {result.request_id!r} != {request.request_id!r})"
        if result.action_id not in {offer.id for offer in request.offers}:
            return f"provider chose unoffered action {result.action_id!r}"
        return None

    def _timeout_s(self, request: DecisionRequest) -> float | None:
        caps = [c for c in (self.max_wait_ms, request.deadline_ms) if c is not None and c > 0]
        return min(caps) / 1000 if caps else None

    def _bounded(
        self, provider: Provider, request: DecisionRequest
    ) -> tuple[ProviderResult | None, str | None]:
        timeout_s = self._timeout_s(request)
        if timeout_s is None:
            return self._call(provider, request)

        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._call, provider, request)
            return future.result(timeout=timeout_s)
        except FutureTimeout:
            return None, f"{provider.name} timed out after {timeout_s:.2f}s"
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _call(provider: Provider, request: DecisionRequest):
        try:
            return provider.choose(request), None
        except ProviderError as exc:
            return None, f"{provider.name} failed: {exc}"
        except Exception as exc:  # any provider bug must still fall back safely
            return None, f"{provider.name} raised {type(exc).__name__}: {exc}"
