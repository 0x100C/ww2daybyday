# WW2 Day by Day – HOI4 campaign logger (v0.1)

A read-only Hearts of Iron IV mod. It writes campaign events to `game.log`, so a campaign can be replayed on the WW2 Day by Day map. It changes nothing in the game.

## Install

1. Copy `ww2dbd_logger.mod` and the `ww2dbd_logger` folder into `Documents/Paradox Interactive/Hearts of Iron IV/mod/`.
2. Enable "WW2 Day by Day – Campaign Logger" in the launcher's playset.
3. (Mod files: `ww2dbd_logger_core.txt` and `ww2dbd_logger_forces.txt` are both in `ww2dbd_logger/common/on_actions/`. I believe on_actions from several files are combined; if your log shows only one set of kinds, tell me.)
4. Optionally, for full save snapshots (see "Save files" below), close the game and set `save_as_binary=no` in `Documents/Paradox Interactive/Hearts of Iron IV/settings.txt`.

Like any mod, it changes the game checksum, so achievements are disabled. It works in Ironman games.

## What v0.2 records

Each line in `logs/game.log` has the form `WW2DBD|<date>|<KIND>|...`. The mod is split into two files so a mistake in the new logging cannot stop the proven part:

- `ww2dbd_logger_core.txt`: everything v0.1 logged, which worked in a real test game (events, territory, wars, factions, combat, weekly stats).
- `ww2dbd_logger_forces.txt`: **new and not yet tested in the game** (see below).

### Core

| Kind | When | Fields |
|---|---|---|
| `START`, `COUNTRY`, `STATE_OWNER`, `STATE_CONTROL` | New game start | Every country's tag, name and flag; owner and controller of every state |
| `STATE_CONTROL` | 1st of each month | Controller of every state (a full snapshot) |
| `CONTROL` | Whenever a state changes controller | state id, old controller, new controller, state name |
| `DECLARE_WAR`, `AT_WAR`, `JOIN_WAR` | Wars begin or widen | attacker, defender |
| `CAPITULATION`, `UNCAPITULATION`, `PEACE_START`, `PEACE_END`, `PEACE`, `ANNEX`, `PUPPET`, `LIBERATE`, `RELEASE`, `CIVIL_WAR_END`, `SUBJECT_ANNEXED`, `GOV_EXILED` | Endings and changes of status | tags |
| `FACTION_CREATE`, `FACTION_JOIN`, `FACTION_LEAVE`, `GOVERNMENT` | Diplomacy and politics | tags |
| `NAVAL_INVASION`, `PARADROP`, `PARADROP_STATE` | Landings | invader, target state, origin state |
| `COMBAT_WON`, `COMBAT_LOST` | Every battle a general wins or loses | country, general, units in combat |
| `STATS` | Weekly, every country at war | divisions, battalions, deployed manpower (k), manpower (k), states controlled, surrender progress |
| `NUKE` | Nuclear strike | launcher, state |

### Forces (new in v0.2)

| Kind | When | What it gives |
|---|---|---|
| `DIV`, `DIVARM`, `MAN` | Every 3 days | For each country at war in each state where it has divisions: at least N divisions, at least N armour divisions, at least N men. N moves in steps, so these are lower bounds. This is the position and strength of each army, state by state. |
| `CASUALTIES` | Weekly | Each country's total casualties (thousands) and war support. |
| `LEADER` | Weekly | Each general by name: units led, units in combat, offensive and defensive fights, armour/infantry/motorised units, **number of battle plans** and order groups. |
| `COUNTRY`, `CAPITAL` | Monthly | Country names and flags again (so campaigns loaded from a save still work), and capital state. |
| `FACTION_LEADER`, `ALLY` | Monthly | Faction membership: who leads a faction, and each country's allies. |

### What this still cannot give

- **Individual named divisions and their paths.** Scripts can count divisions per state but not name or track one. Names and owners print blank in division scope (confirmed in your test), so positions are per state, every 3 days.
- **Battle plans and offensive arrows themselves.** The mod only sees how many battle plans each general has. The plans' geometry exists only in a plain-text save.
- **Exact casualties per battle or per front.** Only each country's running total.
- **Why the AI did something.**

If you try the plain-text save route (see "Save files"), a save is the only source of named divisions and battle-plan arrows.

## Save files

With `save_as_binary=no`, saves are plain text and contain everything the game state holds, including each division's location and strength. They also include battle plans and front assignments.

Several community sources say Ironman saves stay binary regardless of this setting. To check yours: a plain-text save starts with `HOI4txt`, a binary one with `HOI4bin`. You can see this by opening the `.hoi4` file in a text editor.

## Import

```
python3 build/hoi4/import_log.py "<...>/Hearts of Iron IV/logs/game.log"
```

This writes `data/hoi4_campaign.json`, which contains:
- countries;
- events, in the same format as the map's event timeline;
- state-control changes and monthly snapshots;
- weekly strengths;
- combats;
- the probe summary.

## Placing states on the map

HOI4 states have to be located on the real-world map. Run this once on your PC; it reads your game folder and writes a small file with only ids and pixel positions:

```
node build/hoi4/extract_states.mjs "C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
```

It creates `data/hoi4_states.json` (a few hundred KB). The map viewer for campaigns uses it to put states, divisions and fronts in the right places.
