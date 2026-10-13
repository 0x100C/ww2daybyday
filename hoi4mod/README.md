# WW2 Day by Day – HOI4 campaign logger (v0.1)

A read-only Hearts of Iron IV mod. It writes campaign events to `game.log`, so a campaign can be replayed on the WW2 Day by Day map. It changes nothing in the game.

## Install

1. Copy `ww2dbd_logger.mod` and the `ww2dbd_logger` folder into `Documents/Paradox Interactive/Hearts of Iron IV/mod/`.
2. Enable "WW2 Day by Day – Campaign Logger" in the launcher's playset.
3. Optionally, for full save snapshots (see "Save files" below), close the game and set `save_as_binary=no` in `Documents/Paradox Interactive/Hearts of Iron IV/settings.txt`.

Like any mod, it changes the game checksum, so achievements are disabled. It works in Ironman games.

## What v0.1 records

Each line in `logs/game.log` has the form `WW2DBD|<date>|<KIND>|...`. The hooks used are those documented on the HOI4 modding wiki (On actions, Scopes and Localisation pages).

| Kind | When | Fields |
|---|---|---|
| `START`, `COUNTRY`, `STATE_OWNER`, `STATE_CONTROL` | New game start | Every country's tag, name and flag; owner and controller of every state |
| `STATE_CONTROL` | 1st of each month | Controller of every state (a full snapshot) |
| `CONTROL` | Whenever a state changes controller | state id, old controller, new controller, state name |
| `DECLARE_WAR`, `AT_WAR`, `JOIN_WAR` | Wars begin or widen | attacker, defender |
| `CAPITULATION`, `UNCAPITULATION`, `PEACE_START`, `PEACE_END`, `PEACE`, `ANNEX`, `PUPPET`, `LIBERATE`, `RELEASE`, `CIVIL_WAR_END` | Endings | winner and loser tags |
| `FACTION_CREATE`, `FACTION_JOIN`, `FACTION_LEAVE`, `GOVERNMENT` | Diplomacy and politics | tags |
| `NAVAL_INVASION`, `PARADROP` | Landings | invader, target state, origin state |
| `COMBAT_WON`, `COMBAT_LOST` | Every battle a general wins or loses | country, general, units in combat |
| `STATS` | Weekly, for every country at war | divisions, battalions, deployed manpower (k), manpower (k), states controlled, surrender progress |
| `DIVPROBE`, `DIVSTR`, `DIVTYPE` | Weekly | **Experimental.** See "Division probe" below. |
| `NUKE` | Nuclear strike | launcher, state |

## Division probe (please send me the result)

The wiki documents division scopes (`every_state_division`, `every_country_division`) and division triggers (`unit_strength`, `unit_organization`, `division_has_majority_template`). It does not say which names and values can be *printed* from a division scope.

The probe tries the most likely ones each week:
- the division name;
- the owner's tag;
- a strength bucket;
- a type (armor, motorized or infantry).

All of these are tied to the state the division is in.

To check the results:
1. Start a new game with the mod enabled (it can be non-Ironman) and play a few in-game weeks with some units on the map.
2. Run `python3 build/hoi4/import_log.py "<...>/logs/game.log"`. It prints what the probe captured.
3. Also check `logs/error.log` for lines mentioning `ww2dbd`.
4. Send me both outputs.

v0.2 will then log every division whose identity and location can be printed, which drives the division markers.

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

Placing HOI4 states on the map also needs `map/definition.csv`, `map/provinces.bmp` and `history/states/` from your HOI4 install. That step comes next, together with the world map.
