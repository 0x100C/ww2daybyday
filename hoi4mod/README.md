# WW2 Day by Day – HOI4 campaign logger (v0.2.1)

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
- `ww2dbd_logger_forces.txt`: new in v0.2. **Tested in a real game (Aug–Dec 1939):** divisions, armour, men, casualties, generals, allies and faction leaders all log correctly. The capital line printed garbage and is retried in v0.2.1.

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

### Forces (v0.2)

| Kind | When | What it gives |
|---|---|---|
| `DIV`, `DIVARM`, `MEN` | Every 3 days | For each country at war in each state where it has divisions: at least N divisions, at least N armour divisions, at least N men. N moves in steps, so these are lower bounds. This is the position and strength of each army, state by state. |
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

## Replay a campaign on the map

You need two files: the `game.log` from your campaign and `hoi4_states.json` (see "Placing states on the map" below).

```
python3 build/hoi4/build_campaign.py "<...>/logs/game.log" data/hoi4_states.json
node server.js
```

Then open http://127.0.0.1:3847/?campaign=hoi4

What you get:
- **Territory:** each state's control is painted on the map and changes as it did in your game, as the same smooth advances the historical map uses: states captured by the same country within a few days sweep through as one continuous advance, not one state at a time, and state edges are rounded. Borders, fronts and the white advance band all work.
- **Wars and sides:** wars come from the log; colours follow the faction each country belongs to.
- **Event list** (☰ or E): capitulations, war declarations, landings, annexations, each with a position. Click one to fly there and jump to its date.
- **Front troops:** where two countries at war meet, each front gets one rotated number per side (men near that front, a lower bound from the log), placed on either side of the line and following it as it moves.
- **Show divisions (off by default):** a marker per country per area, sized by manpower and labelled with the country tag; the black badge is the number of divisions and the orange arc is the share that is armoured. Markers cross-fade between the 3-day snapshots. Hover for the country, divisions, armour and men. All of these are lower bounds from the log, and positions are per state.
- **Slow playback:** the speed menu goes down to 0.25 days per second.

The build step needs Python 3 with numpy and scipy. If you do not have Python, send me the two files and I will build it and push it.

Current limits: state shapes are rough unless your `hoi4_states.json` came from the 0.2 extractor (the one that includes the shape grid; re-run it to get exact shapes); the map covers Europe, North Africa and the Middle East only, so fighting elsewhere (China, the Pacific, the Americas) happens off screen until the world map is built.

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

It creates `data/hoi4_states.json` (about 2 MB, including a coarse grid of state shapes). The map viewer for campaigns uses it to put states, divisions and fronts in the right places.
