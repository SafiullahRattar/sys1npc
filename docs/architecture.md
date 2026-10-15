# Architecture

> Status: **foundation, v0.1.** The shared decision core below is implemented
> and offline-tested. The FireRed adapter is a separate, unimplemented
> milestone (see [firered-hook.md](firered-hook.md)).

## Goal

Replace the hardcoded trainer AI in Pokémon FireRed (Gen 3) with a remote,
System One-style decision model — **without** disturbing dialogue, animations,
or the game's own mechanics. The model is asked one question per decision and
answers with a single chosen action.

## Scope and boundary

- **Linux-first, emulator-first.** mGBA is the assumed emulator; its exact
  version is to be verified during the hook spike.
- **Trainer battles only.** The decision seam is `battle.action`.
- **The boundary is one decision:** the game asks "what should this trainer do
  now?", offers the complete set of legal actions, and the core returns one
  action id — or "no decision", which the game turns into its original AI.

## Components

```
  ┌───────────────┐  DecisionRequest    ┌──────────────┐  choose()   ┌────────────┐
  │  Game adapter │ ──────────────────▶ │ Coordinator  │ ──────────▶ │  Provider  │
  │  (FireRed)    │ ◀────────────────── │  (shared,    │ ◀────────── │  (scripted │
  │               │       Decision      │ mechanics-   │ ProviderResult │ / jev)  │
  └───────────────┘                     │    free)     │              └────────────┘
        │ owns: legality, state          └──────────────┘
        │ decoding, observed-information        │ owns: validation, bounded
        │ policy, fallback to original AI       │ provider call, correlation
```

- **Adapter** (game-specific, unimplemented): decodes live battle state from
  the running game, computes the complete set of legal actions, applies the
  observed-information policy, and executes the returned action. On `action_id
  is None`, it falls back to the game's original AI.
- **Coordinator** (shared, implemented): knows no Pokémon mechanics. Validates
  requests, bounds provider time, validates answers, returns a `Decision`.
- **Provider** (interchangeable): scripted (offline, deterministic) or Jev
  (TypeSafe, over HTTPS). One provider is chosen at construction time.

## Contracts (`src/sys1npc/contracts.py`)

- `ActionOffer` — an opaque `id` plus a `description` the provider judges.
- `DecisionRequest` — `session_id` + `request_id`, `game` + `actor`, `decision`
  (kind), an opaque `observation`, a non-empty tuple of unique `offers`, and an
  optional `deadline_ms`.
- `ProviderResult` — a chosen `action_id`, optional `model`, `latency_ms`, and
  an optional `request_id` for correlation.
- `Decision` — the validated outcome; `action_id is None` means "fall back to
  the game's original AI".

Action ids are **opaque to the core**. The FireRed adapter will use ids such as
`move:<slot>:<target>`, `switch:<slot>`, and `item:<id>:<target>`; the core only
checks that the chosen id was offered.

## Coordinator responsibilities

1. **Validate the request**: non-empty `session_id`/`request_id`, non-empty
   offers, unique and non-empty offer ids. Malformed requests raise
   `InvalidRequest` (a caller bug).
2. **Bound the provider call**: waits at most `min(max_wait_ms,
   request.deadline_ms)` for a provider; on timeout the call fails. This is a
   *soft* budget for the Python side — it does **not** guarantee the game-side
   watchdog (see below).
3. **Validate the answer**: the chosen action must be among the offered ids
   (membership), and a provider that echoes a `request_id` must match
   (correlation). Anything else is treated as a failure.
4. **Fall back**: on provider failure or invalid answer, try the fallback
   provider (scripted by default); if that also fails, return
   `action_id=None`.

## Provider protocol (`src/sys1npc/providers/base.py`)

A provider is any object with a `name` and a synchronous
`choose(request) -> ProviderResult`. It raises `ProviderError` on failure. The
scripted provider is the offline "before" picture; the Jev provider maps one
`DecisionRequest` to a single Jev `choice` question whose `criteria` is the
action-id → description map (see [jev.py](../src/sys1npc/providers/jev.py)).

The model is asked a **single choice over complete legal actions** — move +
target, switch slot, item + target — not a two-call classification hierarchy.
The adapter computes legality and damage; the model only judges.

## Observed-information policy (default)

The running game is authoritative for live HP/PP/status/party/inventory; static
trainer metadata (movesets, teams) is supplemental. The adapter applies the
visibility policy. The **default ("Jev") policy is full own state plus only
permitted or revealed opponent information** — no hidden-info leakage. An
optional omniscient policy may come later.

## Failure and the game-side watchdog

The core bounds provider time and falls back, but it **cannot** guarantee the
emulator keeps moving if the Python process or the bridge dies mid-decision.
That guarantee belongs to the game integration: the patched ROM must bound its
own waiting and fall back to the original AI when the bridge stops answering.
The request's `session_id`/`request_id` exist so a bridge can reject stale
responses; the core alone cannot enforce cross-process staleness.

## Non-goals (explicitly out of scope)

- No whole-emulator integration, CLI, services, plugin marketplace, universal
  game ontology, or Rust rewrite.
- No confidence gates, personality systems, retries, or lifecycle envelopes.
- No claim that Python timeouts solve the game-side watchdog.
- The in-game trainer-select menu (all / selected / one trainer) is a future,
  explicit deliverable — not an overlay or CLI.

## Repository layout

```
src/sys1npc/{contracts,coordinator}.py
src/sys1npc/providers/{base,scripted,jev}.py
tests/                 # offline mocks/fixtures
docs/                  # this file, firered-hook.md, acceptance.md
```
