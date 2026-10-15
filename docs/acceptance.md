# Acceptance tests and extension responsibilities

> The core acceptance tests are implemented and offline (`tests/`). The
> one-trainer acceptance tests below depend on the FireRed hook
> ([firered-hook.md](firered-hook.md)) and are **not yet runnable**.

## Core acceptance (already covered by `tests/`)

These run fully offline with mocks/fixtures:

1. Valid complete action selection — a provider's in-offer choice is returned
   with the request's ids echoed.
2. Empty offer set → `InvalidRequest`.
3. Duplicate offer ids → `InvalidRequest`.
4. Provider returns an unoffered action → scripted fallback.
5. Stale response (mismatched `request_id`) → rejected, fallback.
6. Provider error → scripted fallback.
7. Provider timeout → scripted fallback.
8. Request deadline shorter than `max_wait_ms` bounds the call.
9. All providers fail and fallback is disabled → `action_id is None`.
10. Jev payload shape and response parsing pinned to the verified wire format.

## One-trainer acceptance (next milestone, game-side)

These prove move selection for a single trainer through the real hook:

1. In a scripted battle against one trainer, the ROM requests a decision and
   blocks until the bridge answers, with a bounded wait.
2. The returned action is a **legal move** for the active Pokémon (the game
   accepts it without desync).
3. Killing the bridge mid-turn makes the ROM fall back to the original AI and
   resume — no softlock.
4. A stale response (wrong `session_id`/`request_id`) is ignored by the bridge.
5. Offline: the scripted provider drives the same battle deterministically.
6. Jev (with explicit authorization and a key) drives the same battle and logs
   chosen action ids against the offered set.

## Extension responsibilities (who owns what)

| Piece | Owner | Notes |
| --- | --- | --- |
| Action legality + complete action set | FireRed adapter | move/target, switch, item/target, forced replace |
| Battle-state decoding (live HP/PP/status/party/inventory) | FireRed adapter | running game is authoritative |
| Observed-information policy | FireRed adapter | default: full own, permitted/revealed opponent |
| Request/session identity + staleness rejection | bridge + coordinator | core echoes ids; bridge enforces across processes |
| Game-side watchdog + fallback to original AI | patched ROM | core cannot guarantee this |
| Trainer-select config (all / selected / one) | patched ROM + adapter | explicit in-game menu, not overlay/CLI |
| Coordinator validation + bounded call | shared coordinator | mechanics-free by construction |
| Providers | providers package | scripted (offline), Jev (verified), future additions |

## When the hook spike lands

Add the adapter and bridge under a FireRed-specific package, keep the
coordinator and contracts unchanged, and wire the one-trainer acceptance tests
above into CI where they are runnable headlessly.
