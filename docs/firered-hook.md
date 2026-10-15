# FireRed hook / patch / bridge — feasibility milestone

> **Status: NOT IMPLEMENTED.** This document records the plan and the open
> unknowns. Nothing here ships; there is no ROM patch, no bridge, and no
> working game integration. It exists so the next spike starts from a clear,
> honest picture.

## Goal

Drive **trainer** decision-making in Pokémon FireRed (Gen 3) through the shared
decision core (`battle.action`), while preserving the game's dialogue,
animations, and mechanics untouched. The first spike only has to prove **move
selection for one trainer** — not switching, items, or forced replacement.

## Emulator and patch target

- **Emulator:** mGBA, Linux-first. The exact mGBA version is **to be verified**
  — its Lua/memory APIs and the right build flags are not yet confirmed.
- **Patch target:** the pret/pokefirered decompilation. The enemy trainer's
  move selection lives in `src/battle_ai_main.c`
  (`BattleAI_ChooseMoveOrAction`), which currently runs synchronously inside
  the ROM.

## The idea: a RAM mailbox hook

Add a small hook behind a WRAM flag so the ROM can hand off a decision to an
external process and wait, while still falling back to vanilla AI:

```text
gRemoteBrainEnabled : u8     # off = vanilla AI
gRemoteBrainRequest : u32    # incremented when a decision is requested
gRemoteBrainState   : u8[]   # serialized observation written by the ROM
gRemoteBrainChoice  : u8     # chosen action index written by the bridge
gRemoteBrainAck     : u32    # incremented by the bridge to confirm
```

Flow per enemy decision:

1. `BattleAI_ChooseMoveOrAction` sees the flag and serializes the observation.
2. It bumps `gRemoteBrainRequest` and **waits, bounded**, for an ack.
3. The Lua bridge (thin) polls the request counter via mGBA's memory API and
   forwards it to the Python app.
4. The FireRed adapter builds a `DecisionRequest` (decoding live state into the
   observation, computing legal actions), the coordinator answers, and the
   bridge writes the chosen index back and bumps the ack.
5. If the bridge/process dies or the wait expires, the ROM **falls back to the
   original AI**. This watchdog lives in the game, not in Python.

## Boundaries and ownership

- **Adapter owns** action legality, battle-state decoding, and the
  observed-information policy (default: full own state, permitted/revealed
  opponent info only).
- **The game is authoritative** for live HP/PP/status/party/inventory; static
  trainer metadata is supplemental.
- **One central hook** with configuration for all / selected / one trainer —
  added later; the in-game menu is an explicit deliverable, not an overlay/CLI.
- **Single choice over complete legal actions** — move + target, switch slot,
  item + target, forced replacement — not a two-call classification hierarchy.

## Staleness and identity

Each request carries `session_id` + `request_id`. The bridge must match them
when writing the choice back, so a late answer from a previous turn can never be
accepted. The core echoes the ids, but enforcing this across process boundaries
is the bridge's responsibility.

## Open unknowns (to resolve in the spike)

- Exact mGBA version and the reliable Lua memory-read/write API.
- Whether the mailbox needs to live in WRAM or can reuse an existing free
  region without clobbering the game.
- How the patched ROM safely serializes/deserializes a full battle observation
  within the RAM budget, and the realistic per-decision latency of that round
  trip vs. Jev's 70–500 ms.
- Whether `BattleAI_ChooseMoveOrAction` is the only call site for trainer
  moves, or whether rivals/gym leaders take additional paths.
- Exact pret/pokefirered commit to patch against (pins the RAM symbols).

## Non-goals

- No ROMs, save files, Nintendo graphics, or copyrighted patch assets in this
  repository. The patch is source-level (a diff against pret/pokefirered).
- No claim that any of this currently works.
