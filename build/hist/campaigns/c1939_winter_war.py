"""Winter War, 30 November 1939 - 13 March 1940, and the Moscow peace.

Soviet-held areas inside Finland at each key. Sources: A. F. Upton,
"Finland 1939-40" (1974); W. R. Trotter, "A Frozen Hell" (1991); Finnish
General Staff campaign maps. The Isthmus advance reached the Mannerheim
Line by 6-7 Dec; the breakthrough at Summa came on 11-13 Feb; the Finns
fell back to the intermediate line (15-17 Feb) and the rear line (26-28
Feb); Soviet troops crossed the ice of Viipuri bay from 4 Mar. North of
Ladoga the Soviets reached the Kollaa and Tolvajarvi in early December
and were thrown back from Tolvajarvi to Aglajarvi (12-22 Dec). The
Suomussalmi and Raate road divisions were destroyed 7 Dec - 8 Jan; the
Kuhmo motti held out until the armistice. Petsamo was taken on 2 Dec and
returned to Finland under the peace treaty.

The ceded area of the Moscow peace treaty (12 Mar, in force 13 Mar
11:00) coincides with today's Finnish-Russian border south of Petsamo.
"""
import numpy as np

from core import world
from ctools import blob, J
import borders as B

ISTHMUS_OLD = [(60.42, 30.95), (60.38, 30.60), (60.33, 30.28), (60.23, 30.14), (60.16, 30.02), (60.13, 29.95)]


def isthmus(front):
    """Soviet-held isthmus: front from the Gulf (west) to Ladoga (east), old border back."""
    return J(front, amp=2.0, seg=6, seed=3) + ISTHMUS_OLD + [(60.05, 29.6), (60.05, 28.3)]


LADOGA_OLD = [(62.65, 31.95), (62.40, 32.40), (62.10, 32.72), (61.80, 32.80), (61.50, 32.62), (61.22, 32.30)]


def ladoga(front):
    return J(front, amp=2.0, seg=6, seed=4) + LADOGA_OLD + [(61.0, 32.0)]


KEYS = {
    "1939-11-30 12": dict(
        ist=[(60.08, 29.30), (60.20, 29.55), (60.28, 29.85), (60.35, 30.15), (60.40, 30.55), (60.42, 30.90)],
        lad=[(61.25, 32.05), (61.45, 32.30), (61.75, 32.45), (62.05, 32.45), (62.35, 32.20), (62.60, 31.95)],
        pets=[(69.90, 31.75), (69.60, 31.70), (69.40, 31.30), (69.40, 31.95)],
    ),
    "1939-12-03 00": dict(
        ist=[(60.15, 28.95), (60.30, 29.20), (60.40, 29.50), (60.45, 29.85), (60.48, 30.20), (60.50, 30.55)],
        lad=[(61.33, 31.80), (61.55, 31.75), (61.80, 31.85), (62.05, 31.90), (62.30, 31.90), (62.55, 31.85)],
        pets=[(69.95, 31.30), (69.60, 31.00), (69.40, 30.80), (69.20, 31.20), (69.25, 31.90)],
        suo=[(65.05, 29.95), (64.95, 29.45), (64.90, 29.10), (64.80, 29.40), (64.75, 30.05)],
        sal=[(67.20, 29.60), (67.00, 29.15), (66.80, 29.15), (66.60, 29.60)],
    ),
    "1939-12-07 12": dict(
        ist=[(60.33, 28.62), (60.48, 28.78), (60.56, 28.95), (60.57, 29.20), (60.60, 29.45), (60.58, 29.75),
             (60.55, 30.05), (60.51, 30.45)],
        lad=[(61.58, 31.45), (61.63, 31.28), (61.85, 31.35), (62.05, 31.55), (62.20, 31.55), (62.28, 31.50),
             (62.45, 31.80), (62.60, 31.90)],
        pets=[(69.95, 31.10), (69.65, 30.40), (69.35, 30.10), (69.05, 29.95), (69.00, 30.50), (69.25, 31.90)],
        suo=[(65.10, 29.95), (65.02, 29.20), (64.90, 28.88), (64.80, 29.20), (64.78, 30.05)],
        sal=[(67.20, 29.60), (67.05, 28.70), (66.85, 28.55), (66.65, 28.90), (66.55, 29.60)],
        kuh=[(64.20, 30.10), (64.12, 29.85), (64.00, 30.05), (64.00, 30.35)],
    ),
    "1939-12-17 00": dict(
        ist=[(60.33, 28.60), (60.48, 28.77), (60.555, 28.94), (60.565, 29.20), (60.595, 29.45), (60.58, 29.75),
             (60.55, 30.05), (60.51, 30.45)],
        lad=[(61.58, 31.45), (61.64, 31.27), (61.86, 31.36), (62.05, 31.58), (62.18, 31.62), (62.30, 31.85),
             (62.45, 31.95), (62.60, 31.95)],
        pets=[(69.95, 31.00), (69.60, 30.20), (69.20, 29.70), (68.95, 29.30), (68.90, 30.00), (69.25, 31.90)],
        suo=[(65.10, 29.95), (65.03, 29.15), (64.92, 28.85), (64.80, 29.10), (64.78, 30.05)],
        sal=[(67.20, 29.60), (67.05, 28.40), (66.85, 28.20), (66.62, 28.60), (66.55, 29.60)],
        kuh=[(64.22, 30.10), (64.15, 29.75), (64.02, 29.95), (64.00, 30.35)],
    ),
    "1939-12-27 00": dict(
        ist=[(60.33, 28.60), (60.48, 28.77), (60.555, 28.94), (60.565, 29.20), (60.595, 29.45), (60.58, 29.75),
             (60.55, 30.05), (60.51, 30.45)],
        lad=[(61.58, 31.45), (61.64, 31.27), (61.86, 31.36), (62.05, 31.60), (62.20, 31.80), (62.35, 32.05),
             (62.50, 32.05), (62.62, 31.98)],
        pets=[(69.95, 31.00), (69.60, 30.20), (69.20, 29.70), (68.95, 29.30), (68.90, 30.00), (69.25, 31.90)],
        suo=[(65.08, 29.85), (65.00, 29.40), (64.90, 29.30), (64.82, 29.60), (64.80, 30.05)],
        sal=[(67.20, 29.60), (67.05, 28.95), (66.85, 28.85), (66.65, 29.05), (66.55, 29.60)],
        kuh=[(64.22, 30.10), (64.15, 29.75), (64.02, 29.95), (64.00, 30.35)],
    ),
    "1940-01-08 00": dict(
        ist=[(60.33, 28.60), (60.48, 28.77), (60.555, 28.94), (60.565, 29.20), (60.595, 29.45), (60.58, 29.75),
             (60.55, 30.05), (60.51, 30.45)],
        lad=[(61.58, 31.45), (61.64, 31.27), (61.86, 31.36), (62.05, 31.60), (62.20, 31.80), (62.35, 32.05),
             (62.50, 32.05), (62.62, 31.98)],
        pets=[(69.95, 31.00), (69.60, 30.20), (69.20, 29.70), (68.95, 29.30), (68.90, 30.00), (69.25, 31.90)],
        sal=[(67.20, 29.60), (67.05, 28.95), (66.85, 28.85), (66.65, 29.05), (66.55, 29.60)],
        kuh=[(64.22, 30.10), (64.15, 29.75), (64.02, 29.95), (64.00, 30.35)],
    ),
    "1940-02-12 00": None,  # same as 8 Jan (repeated below)
    "1940-02-16 12": dict(
        ist=[(60.36, 28.55), (60.50, 28.72), (60.60, 28.90), (60.63, 29.15), (60.64, 29.45), (60.60, 29.75),
             (60.55, 30.05), (60.51, 30.45)],
    ),
    "1940-02-28 00": dict(
        ist=[(60.45, 28.40), (60.58, 28.62), (60.66, 28.80), (60.70, 29.10), (60.68, 29.50), (60.62, 29.85),
             (60.56, 30.10), (60.51, 30.45)],
    ),
    "1940-03-13 11": dict(
        ist=[(60.45, 28.30), (60.60, 28.50), (60.66, 28.70), (60.70, 28.82), (60.74, 28.95), (60.72, 29.30),
             (60.68, 29.60), (60.60, 29.90), (60.55, 30.20), (60.50, 30.42)],
    ),
}


def build(tl):
    W = world()
    sov = tl.layer("winter-war", "SOV", within=["FIN"], order=40)
    prev = None
    kuhmo_pocket = blob([(64.20, 30.12), (64.16, 29.88), (64.06, 29.95), (64.05, 30.25)], seed=5)
    for d in sorted(KEYS):
        k = KEYS[d]
        if k is None:
            k = prev
        merged = dict(prev or {})
        merged.update(k)
        if d >= "1940-01-08":
            merged.pop("suo", None)
        rings = [isthmus(merged["ist"]), ladoga(merged["lad"])]
        if "pets" in merged:
            rings.append(blob(merged["pets"] + [(70.2, 32.0), (70.2, 30.5)], seed=6))
        if "suo" in merged:
            rings.append(blob(merged["suo"], seed=7))
        if "sal" in merged:
            rings.append(blob(merged["sal"], seed=8))
        if "kuh" in merged:
            rings.append(kuhmo_pocket if d >= "1940-01-28" else blob(merged["kuh"], seed=9))
        sov.key(d, *rings, src="Trotter 1991; Upton 1974")
        prev = merged

    # Moscow peace: ceded territory becomes Soviet; Soviet troops leave Petsamo
    # and the parts of Salla and Kuhmo outside the new border.
    rus = W.unit("RUS")
    ceded = lambda: (W.poly(B.FIN_KARELIA_1920) | W.poly(B.FIN_SALLA_1920) |  # noqa: E731
                     W.polys(*B.FIN_GULF_ISLANDS) | W.poly([(69.95, 31.75), (69.95, 32.2), (69.70, 32.2), (69.70, 31.75)])) & rus
    tl.political("1940-03-15", ceded, "SOV", where=["FIN"], dur=2.0, label="Moscow peace treaty")
    sov.end("1940-03-25")
    # Hanko naval base leased to the USSR (22 Mar 1940 - evacuated 2 Dec 1941)
    hanko = tl.layer("hanko", "SOV", within=["FIN"], order=41)
    hanko.key("1940-03-22", blob([(59.93, 22.75), (59.93, 23.20), (59.78, 23.20), (59.78, 22.75)], amp=0.6, seed=10))
    hanko.end("1941-12-02 12")
    tl.caption("1939-11-30", "The Soviet Union attacks Finland in what would become known as the Winter War")
    tl.caption("1939-12-12", "Finnish victory at Tolvajarvi")
    tl.caption("1940-01-08", "Two Soviet divisions are destroyed at Suomussalmi and on the Raate road")
    tl.caption("1940-02-13", "The Red Army breaks through the Mannerheim Line at Summa")
    tl.caption("1940-03-13", "Finland agrees to peace, giving up significant territory")
