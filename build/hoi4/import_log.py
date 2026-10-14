"""Import a HOI4 campaign recorded by the WW2 Day by Day logger mod.

Usage:
    python3 build/hoi4/import_log.py "<path to>/Hearts of Iron IV/logs/game.log" [out.json]

Reads every line containing "WW2DBD|" (other game.log noise is ignored),
and writes a campaign file (default data/hoi4_campaign.json) with:

  countries   tag -> {name, flag}
  events      dated list (wars, capitulations, peace, annexations, factions,
              invasions, nukes) in the same shape as data/events.json
  control     dated state-control changes  [t, state, from, to]
  snapshots   monthly full state-control snapshots {t: {state: tag}}
  stats       weekly strength per country at war
  combats     battles won/lost per general
  divisions   every 3 days: per country per state, lower bounds of divisions, armour divisions, men
  casualties  weekly total casualties (thousands) and war support per country
  leaders     weekly per general: units, in combat, offensive/defensive, types, battle plans
  factions    monthly alliance pairs and faction leaders; capitals per country
  probe       what the division-scope probe could print (guides logger v0.2)

Dates are converted to days since the first logged date, like the
historical timeline. Placing states on the map needs the HOI4 map files
(map/definition.csv, map/provinces.bmp, history/states) from your install;
that step is not part of this importer yet.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

LINE = re.compile(r"WW2DBD\|([^\n\r]*)")


def parse_date(s):
    # [GetDate] -> YYYY.MM.DD.HH
    p = [int(x) for x in s.split(".")]
    while len(p) < 4:
        p.append(0)
    return datetime(p[0], p[1], p[2], p[3])


def kv(fields):
    out, pos = {}, []
    for f in fields:
        if "=" in f:
            k, v = f.split("=", 1)
            out[k] = v
        else:
            pos.append(f)
    return pos, out


def clean(s):
    """GetFlag/GetName can carry non-printing text-icon markers (e.g. \\x12GER)."""
    return "".join(c for c in s if c.isprintable()).strip()


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


EVENT_TEXT = {
    "DECLARE_WAR": ("breakthrough", "{0} declares war on {1}"),
    "CAPITULATION": ("collapse", "{0} capitulates to {1}"),
    "ANNEX": ("capital", "{1} is annexed by {0}"),
    "PUPPET": ("capital", "{0} becomes a puppet of {1}"),
    "PEACE_START": ("collapse", "Peace conference: {0} imposes terms on {1}"),
    "NAVAL_INVASION": ("breakthrough", "{0} naval invasion"),
    "PARADROP": ("breakthrough", "{0} airborne landing"),
    "NUKE": ("collapse", "{0} drops a nuclear bomb"),
    "FACTION_JOIN": ("capital", "{0} joins the faction of {1}"),
    "CIVIL_WAR_END": ("collapse", "{0} wins the civil war against {1}"),
}


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "..", "data", "hoi4_campaign.json")
    rows = []
    with open(src, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LINE.search(line)
            if not m:
                continue
            parts = m.group(1).strip().split("|")
            if len(parts) < 2:
                continue
            try:
                d = parse_date(parts[0])
            except ValueError:
                continue
            rows.append((d, parts[1], parts[2:]))
    if not rows:
        sys.exit("no WW2DBD lines found - is the logger mod enabled?")
    rows.sort(key=lambda r: r[0])
    t0 = rows[0][0]
    T = lambda d: round((d - t0).total_seconds() / 86400.0, 4)  # noqa: E731

    countries, events, control, stats, combats = {}, [], [], defaultdict(list), []
    snapshots = defaultdict(dict)
    div_rows = {}
    casualties, leaders, capitals, fac_leaders, allies = defaultdict(list), [], {}, {}, {}
    probe = Counter()
    probe_samples = []
    for d, kind, f in rows:
        t = T(d)
        f = [clean(x) for x in f]
        pos, kw = kv(f)
        if kind == "COUNTRY" and pos:
            countries[pos[0]] = {"name": pos[1] if len(pos) > 1 else pos[0], "flag": pos[2] if len(pos) > 2 else pos[0]}
        elif kind in ("DIV", "DIVARM", "MAN") and len(pos) >= 3:
            # lower bounds for one country in one state: divisions, armour divisions, men (every 3 days)
            key = (t, pos[0], pos[1])
            row = div_rows.setdefault(key, {"t": t, "state": pos[0], "tag": pos[1], "n": 0, "armor": 0, "men": 0})
            row[{"DIV": "n", "DIVARM": "armor", "MAN": "men"}[kind]] = int(float(pos[2]))
        elif kind == "CASUALTIES" and pos:
            casualties[pos[0]].append({"t": t, **{k: num(v) for k, v in kw.items()}})
        elif kind == "LEADER" and len(pos) >= 2:
            leaders.append({"t": t, "tag": pos[0], "name": pos[1], **{k: num(v) for k, v in kw.items()}})
        elif kind == "CAPITAL" and len(pos) >= 2:
            capitals[pos[0]] = pos[1]
        elif kind == "FACTION_LEADER" and pos:
            fac_leaders.setdefault(t, []).append(pos[0])
        elif kind == "ALLY" and len(pos) >= 2:
            allies.setdefault(t, {}).setdefault(pos[0], []).append(pos[1])
        elif kind == "STATE_CONTROL" and len(pos) >= 2:
            snapshots[t][pos[0]] = pos[1]
        elif kind == "CONTROL" and len(pos) >= 3:
            control.append([t, pos[0], pos[1], pos[2]])
        elif kind == "STATS" and pos:
            stats[pos[0]].append({"t": t, **{k: num(v) for k, v in kw.items()}})
        elif kind in ("COMBAT_WON", "COMBAT_LOST") and pos:
            combats.append({"t": t, "won": kind == "COMBAT_WON", "tag": pos[0],
                            "leader": pos[1] if len(pos) > 1 else "", "in_combat": num(kw.get("in_combat"))})
        elif kind in ("DIVPROBE", "DIVSTR", "DIVTYPE"):
            probe[kind] += 1
            if len(probe_samples) < 20:
                probe_samples.append("|".join([kind] + f))
        if kind in EVENT_TEXT:
            typ, fmt = EVENT_TEXT[kind]
            names = [countries.get(x, {}).get("name", x) for x in pos] + ["", ""]
            events.append({"id": f"{kind.lower()}_{len(events)}", "type": typ, "t": t, "kind": kind,
                           "title": fmt.format(*names), "tags": pos, **kw, "src": "HOI4 campaign log"})

    camp = {
        "format": "ww2dbd-hoi4-campaign/0.1",
        "start": t0.strftime("%Y-%m-%d %H"),
        "end": rows[-1][0].strftime("%Y-%m-%d %H"),
        "countries": countries,
        "events": events,
        "control": control,
        "snapshots": [{"t": t, "states": s} for t, s in sorted(snapshots.items())],
        "stats": stats,
        "combats": combats,
        "divisions": sorted(div_rows.values(), key=lambda r: (r["t"], r["tag"], r["state"])),
        "casualties": casualties,
        "leaders": leaders,
        "capitals": capitals,
        "factions": [{"t": t, "leaders": fac_leaders.get(t, []), "allies": a} for t, a in sorted(allies.items())],
        "probe": {"counts": dict(probe), "samples": probe_samples},
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(camp, f, ensure_ascii=False, indent=0)
    print(f"{len(rows)} log lines, {len(countries)} countries, {len(events)} events, {len(control)} control changes, "
          f"{len(camp['snapshots'])} snapshots, {sum(len(v) for v in stats.values())} stat rows, "
          f"{len(combats)} combats, {len(div_rows)} force rows, {len(leaders)} general rows, {len(allies)} faction snapshots -> {out}")
    if probe:
        print("division probe:", dict(probe))
        for s in probe_samples[:5]:
            print("  ", s)


if __name__ == "__main__":
    main()
