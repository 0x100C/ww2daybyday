"""Partition of Poland, October - November 1939.

 8/26 Oct 1939  Reich annexes western Poland (Danzig-West Prussia, Wartheland,
                East Upper Silesia, the Zichenau district and the Suwalki
                triangle); the rest of the German zone becomes the
                General Government (decree of 12 Oct, in force 26 Oct).
 10/28 Oct 1939 Vilnius and its region handed by the USSR to Lithuania
                (treaty 10 Oct, Lithuanian army enters 27-28 Oct).
 1-2 Nov 1939   USSR annexes the occupied east (Western Ukraine 1 Nov,
                Western Belarus 2 Nov).
"""
import numpy as np

from core import world, river
from c1939_poland import soviet_zone_ring, BUG

# Reich annexation boundary (north-east on the Soviet line, then west along
# the Bug, Narew and Vistula, then south along the Wartheland / Upper Silesia
# border with the General Government to the Slovak border).
ANNEX_LINE_SOUTH = [
    (52.33, 19.95), (52.20, 19.85), (52.05, 19.70), (51.95, 19.75), (51.85, 19.85), (51.75, 19.85),
    (51.60, 19.75), (51.45, 19.50), (51.25, 19.30), (51.10, 19.10), (51.00, 19.05), (50.85, 19.00),
    (50.70, 19.15), (50.55, 19.40), (50.45, 19.60), (50.30, 19.65), (50.15, 19.55), (50.00, 19.60),
    (49.95, 19.55), (49.85, 19.60), (49.75, 19.65), (49.60, 19.60), (49.48, 19.55),
]

VILNIUS_TRANSFER = [
    (55.05, 25.05), (55.08, 25.45), (54.95, 25.75), (54.72, 25.80), (54.45, 25.65), (54.22, 25.35),
    (54.12, 24.95), (54.20, 24.65), (54.45, 24.50), (54.70, 24.62), (54.88, 24.78),
]


def annex_ring():
    north = [(55.5, 24.0), (54.05, 23.47), (53.0, 22.6), (52.72, 22.06)]
    bug = river(BUG, (52.72, 22.06), (52.48, 21.10))
    narew = river("Narew", (52.48, 21.06), (52.43, 20.72))
    vist = river("Vistula", (52.42, 20.70), (52.38, 20.10))
    return north + bug + narew + vist + ANNEX_LINE_SOUTH + [(49.0, 19.5), (49.0, 14.0), (55.5, 14.0)]


def build(tl):
    W = world()
    sov = lambda: W.poly(soviet_zone_ring())  # noqa: E731
    annex = lambda: W.poly(annex_ring()) & ~sov()  # noqa: E731
    tl.political("1939-10-26", annex, "GER", where=["POL"], dur=1.0, label="Western Poland annexed to the Reich")
    tl.political("1939-10-26", lambda: ~sov(), "GG", where=["POL"], dur=1.0, label="General Government")
    tl.political("1939-10-28", lambda: W.poly(VILNIUS_TRANSFER), "LTU", where=["POL"], dur=1.5,
                 label="Vilnius region to Lithuania")
    tl.political("1939-11-02", sov, "SOV", where=["POL"], dur=2.0, label="Soviet annexation of eastern Poland")
    tl.caption("1939-10-06", "Polish resistance comes to an end at Kock")
    tl.caption("1939-10-26", "Western Poland is annexed to the Reich; the rest becomes the General Government")
    tl.caption("1939-10-28", "Lithuanian troops enter Vilnius")
    tl.caption("1939-11-02", "The Soviet Union annexes eastern Poland")
