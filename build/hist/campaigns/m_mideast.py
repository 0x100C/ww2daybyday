"""Middle East 1941: Anglo-Iraqi war, Syria-Lebanon, Anglo-Soviet invasion of
Iran; Dodecanese 1943.

Sources: Playfair, "The Mediterranean and Middle East" vol. II (1956),
maps of Iraq and Syria; R. Stewart, "Sunrise at Abadan" (1988) for the
Iran occupation zones (Soviet north, British south-west, neutral belt
around Tehran as agreed in the January 1942 Tripartite Treaty);
J. Holland, "Burning Blue" / P. Smith & E. Walker, "War in the Aegean"
(1974) for Kos, Leros and Samos.
"""
from ctools import blob, circle

IRAQ = {
    "1941-04-02 00": [circle(33.37, 43.57, 6, 10), circle(30.50, 47.70, 18, 12)],
    "1941-04-19 00": [circle(33.37, 43.57, 6, 10), blob([(31.0, 47.3), (31.0, 48.2), (29.9, 48.6), (30.2, 47.3)], seed=501)],
    "1941-05-06 18": [circle(33.37, 43.57, 14, 12), blob([(31.1, 47.2), (31.1, 48.3), (29.9, 48.6), (30.2, 47.2)], seed=502)],
    "1941-05-19 18": [blob([(33.55, 43.20), (33.45, 43.85), (33.30, 43.85), (33.20, 43.25)], seed=503),
                      blob([(31.2, 47.0), (31.3, 48.3), (29.9, 48.6), (30.2, 47.0)], seed=504),
                      blob([(33.3, 40.5), (33.5, 41.6), (32.6, 42.0), (32.4, 40.6)], seed=505)],
    "1941-05-28 00": [blob([(33.70, 42.70), (33.65, 44.10), (33.10, 44.10), (33.05, 42.80)], seed=506),
                      blob([(31.5, 46.6), (31.6, 48.3), (29.9, 48.6), (30.2, 46.6)], seed=507),
                      blob([(34.5, 40.5), (34.4, 42.6), (32.4, 42.8), (32.2, 40.4)], seed=508)],
}

SYRIA = {
    "1941-06-08 18": [[(33.35, 35.0), (33.30, 35.6), (33.15, 36.0), (32.95, 36.4), (32.60, 36.9), (32.30, 37.5),
                       (31.9, 37.5), (31.9, 35.0)]],
    "1941-06-15 00": [[(33.45, 35.0), (33.45, 35.6), (33.40, 36.15), (33.10, 36.6), (32.90, 37.2), (32.60, 38.0),
                       (31.9, 38.0), (31.9, 35.0)]],
    "1941-06-21 12": [[(33.50, 35.0), (33.55, 35.6), (33.65, 36.3), (33.60, 36.6), (33.30, 37.5), (33.20, 38.5),
                       (31.9, 38.5), (31.9, 35.0)], [(34.8, 40.5), (34.8, 41.6), (34.0, 41.6), (34.0, 40.5)]],
    "1941-07-03 12": [[(33.60, 35.0), (33.60, 35.6), (33.75, 36.3), (33.90, 36.8), (34.60, 37.8), (35.00, 38.8),
                       (35.40, 40.2), (35.50, 41.4), (34.0, 41.6), (31.9, 38.5), (31.9, 35.0)]],
    "1941-07-10 12": [[(33.72, 35.0), (33.75, 35.6), (34.00, 36.2), (34.40, 36.6), (34.90, 37.6), (35.30, 39.5),
                       (36.30, 40.3), (36.80, 41.5), (34.0, 41.6), (31.9, 38.5), (31.9, 35.0)]],
}

SOV_IRAN = [(39.8, 44.0), (38.3, 44.2), (37.0, 44.9), (36.6, 45.6), (36.6, 47.2), (36.3, 48.8), (36.1, 50.0),
            (35.9, 51.0), (35.8, 52.5), (35.6, 54.0), (35.4, 56.0), (34.6, 58.0), (34.2, 60.5), (39.8, 60.5)]
GBR_IRAN = [(35.4, 45.4), (35.0, 46.4), (34.5, 48.5), (34.0, 50.0), (33.2, 51.5), (31.8, 53.5), (30.2, 56.5),
            (28.5, 58.5), (27.0, 60.5), (24.0, 60.5), (24.0, 47.5), (29.5, 47.5), (31.0, 47.6), (32.5, 46.2),
            (33.6, 45.5)]


def build(tl):
    iq = tl.layer("iraq-1941", "GBR", within=["IRQ"], order=46)
    for d, r in IRAQ.items():
        iq.key(d, *r)
    iq.end("1941-05-31 12")

    sy = tl.layer("syria-1941", "GBR", within=["SYR", "LBN"], order=47)
    for d, r in SYRIA.items():
        sy.key(d, *r)
    sy.end("1941-07-14 12")

    so = tl.layer("iran-soviet", "SOV", within=["IRN"], order=48)
    so.key("1941-08-25 06", blob([(39.5, 44.5), (39.6, 47.8), (38.6, 48.8), (38.3, 46.0)], seed=511),
           blob([(37.6, 53.6), (38.1, 57.0), (37.3, 59.0), (36.9, 55.0)], seed=512))
    so.key("1941-08-28 00", blob([(39.5, 44.2), (39.6, 48.2), (38.0, 49.2), (37.2, 49.8), (36.6, 50.6),
                                  (36.9, 47.0), (37.9, 45.0)], seed=513),
           blob([(37.8, 53.3), (38.1, 57.5), (37.0, 59.5), (36.3, 59.0), (36.6, 54.5)], seed=514))
    so.key("1941-09-02 00", SOV_IRAN)
    gb = tl.layer("iran-british", "GBR", within=["IRN"], order=49)
    gb.key("1941-08-25 06", blob([(30.9, 48.0), (31.3, 49.0), (30.2, 49.6), (29.9, 48.4)], seed=515),
           circle(34.45, 45.9, 18, 10))
    gb.key("1941-08-28 00", blob([(32.5, 47.4), (32.3, 49.6), (30.0, 50.4), (29.9, 48.3), (31.5, 47.6)], seed=516),
           blob([(34.6, 45.5), (34.4, 47.2), (33.8, 47.0), (34.0, 45.7)], seed=517))
    gb.key("1941-09-02 00", GBR_IRAN)

    dd = tl.layer("dodecanese-1943", "GBR", within=["DOD", "GRC"], order=50)
    kos, leros, samos = circle(36.82, 27.15, 26, 14), circle(37.15, 26.85, 9, 12), circle(37.73, 26.85, 24, 14)
    dd.key("1943-09-14 00", kos, leros, samos, span=1.5)
    dd.key("1943-10-03 18", leros, samos, span=0.6)
    dd.key("1943-11-16 18", samos, span=1.0)
    dd.end("1943-11-22 12")

    for d, t in [("1941-04-02", "Rashid Ali seizes power in Iraq"),
                 ("1941-05-02", "Fighting breaks out at RAF Habbaniya"),
                 ("1941-05-31", "The Anglo-Iraqi War ends with an armistice"),
                 ("1941-06-08", "British, Commonwealth and Free French forces invade Vichy Syria and Lebanon"),
                 ("1941-06-21", "Damascus is taken"),
                 ("1941-07-14", "The Armistice of Saint Jean d'Acre ends the Syria-Lebanon campaign"),
                 ("1941-08-25", "British and Soviet forces invade Iran"),
                 ("1943-09-14", "British forces land on Kos, Leros and Samos"),
                 ("1943-11-16", "Leros falls to German forces")]:
        tl.caption(d, t)
