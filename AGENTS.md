# Repository guidance for agents and contributors

## What this is

A small, mechanics-free decision core for game NPCs. The target is a FireRed
trainer-battle AI, but the game hook is **not implemented**. Do not claim it is.

## Hard boundaries

- **Never commit credentials.** `.env` is git-ignored. Read secrets only as
  needed; never write them into files, logs, or commit messages.
- **Never call a paid API** (Jev/TypeSafe) without explicit authorization.
- **No ROMs, save files, Nintendo graphics, or copyrighted patch assets** may be
  committed. Assume any ROM-related artifact is copyrighted.
- The shared coordinator must stay **mechanics-free**: it may not read the
  observation or decode action ids.
- Do not add a CLI, services, plugin marketplaces, or a universal game
  ontology. Keep the foundation small.

## Commands

    pip install -e '.[dev]'
    pytest -q
    ruff check .

## Status landmarks

- `docs/architecture.md` — the design.
- `docs/firered-hook.md` — the unimplemented FireRed hook/patch/bridge milestone.
- `docs/acceptance.md` — next one-trainer acceptance tests and who owns what.
