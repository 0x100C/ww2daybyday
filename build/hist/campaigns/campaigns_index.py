"""Registry of campaign and political modules, in chronological order."""
import importlib

MODULES = [
    "c1939_poland",
    "p1939_partition",
    "c1939_winter_war",
    "c1940_scandinavia",
    "c1940_west",
    "p1940_changes",
    "b_balkans",
    "a_africa",
    "m_mideast",
    "e1941",
    "e_finland",
    "e1942",
    "e1943",
    "e1944",
    "e1945",
    "i_italy",
    "w1944_west",
    "p1945_changes",
]


def build_all(tl, only=None):
    for name in MODULES:
        if only and not any(o in name for o in only):
            continue
        importlib.import_module(name).build(tl)
