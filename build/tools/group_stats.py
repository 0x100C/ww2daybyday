import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hist"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hist", "campaigns"))
import numpy as np
import political_1939, campaigns_index
from core import world
from timeline import Timeline, date_str
from compiler import compile_timeline
W = world()
tl = Timeline(political_1939.fill_coast(political_1939.build(), W.land))
campaigns_index.build_all(tl, only=sys.argv[1].split(",") if len(sys.argv) > 1 else None)
bc, bk, groups, _, _ = compile_timeline(tl, log=open(os.devnull, "w"))
for g in sorted(groups, key=lambda g: -g.idx.size)[:25]:
    print(f"{g.idx.size:9d} kind={g.kind} {date_str(g.t0)}..{date_str(g.t1)} {g.src}")
