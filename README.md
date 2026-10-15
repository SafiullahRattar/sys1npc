# sys1npc

A small, mechanics-free decision core for game NPCs — the foundation for a
FireRed trainer-battle AI.

> **Status: foundation only.** This repository contains the shared decision
> core, a deterministic offline provider, and a Jev provider whose wire format
> is verified against TypeSafe's first-party docs. The FireRed
> hook/patch/bridge is **not implemented** (see
> [docs/firered-hook.md](docs/firered-hook.md)). There is no working game
> integration and no shipped CLI. Everything here is offline-testable and
> honest about what does not exist yet.

## What this is

A Pokémon trainer battle is a sequence of decisions: pick a move (and target),
switch to another party member, use an item. This project's core boundary is
one such decision — **`battle.action`** — expressed as a small, typed contract:

- the game adapter asks for a decision with a **game-specific observation** and
  a set of **complete, opaque legal actions** (id + description);
- a **provider** (scripted, or Jev over HTTPS) picks one action;
- a **shared coordinator** validates the answer (membership, correlation) and
  bounds how long a provider may take.

The coordinator knows **no Pokémon mechanics**. It never reads the observation
and never decodes an action id; the adapter owns legality, state decoding, and
what the NPC is allowed to observe.

See [docs/architecture.md](docs/architecture.md) for the design and
[docs/acceptance.md](docs/acceptance.md) for the next acceptance tests.

## Layout

```
src/sys1npc/
  contracts.py        # ActionOffer, DecisionRequest, ProviderResult, Decision
  coordinator.py      # validation, bounded provider call, fallback
  providers/
    base.py           # Provider protocol + error types
    scripted.py       # deterministic offline provider (and default fallback)
    jev.py            # TypeSafe Jev provider (verified wire format)
tests/                # fully offline (mocks/fixtures)
docs/                 # architecture, FireRed hook (unimplemented), acceptance
```

## Running the tests (offline, no keys)

```bash
pip install -e '.[dev]'
pytest -q
ruff check .
```

## Eventual UX (not shipped)

The intended end state is a single command that drives a legally-owned ROM:

```text
sys1npc fire-red <ROM>      # does NOT exist yet
```

Do not treat the above as a working command. It is a target and depends on the
FireRed hook milestone in [docs/firered-hook.md](docs/firered-hook.md).

## Secrets

Copy `.env.example` to `.env` and add `TYPESAFE_API_KEY` to use the Jev
provider. `.env` is git-ignored; never commit credentials, and never call a
paid API without explicit authorization.

## License

[MIT](LICENSE). Not affiliated with Nintendo, Game Freak, or TypeSafe. No ROMs,
save files, or copyrighted assets are included.
