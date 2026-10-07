"""Territorial changes of 1940 outside the main campaigns.

15-17 Jun 1940  Red Army occupies Lithuania (15 Jun), Latvia and Estonia (17 Jun);
                annexation 3 Aug (LTU), 5 Aug (LVA), 6 Aug (EST).
28 Jun-3 Jul    Bessarabia, Northern Bukovina and the Hertsa region occupied by
                the USSR after the ultimatum of 26 Jun.
30 Aug 1940     Second Vienna Award: Northern Transylvania to Hungary; Hungarian
                troops occupy it 5-13 Sep.
7 Sep 1940      Treaty of Craiova: Southern Dobruja to Bulgaria, handed over by 21 Sep.
18 May 1940     Eupen-Malmedy annexed by the Reich.
30 Nov 1940     Alsace and Moselle incorporated de facto into Gaue Baden and Westmark.
30 Aug 1942     Luxembourg incorporated de facto into Gau Moselland.
30 Jun-1 Jul    Channel Islands occupied (until 9 May 1945).
"""
from core import world
from ctools import blob, J

N_TRANSYLVANIA_LINE = [
    (46.92, 21.55), (46.90, 21.90), (46.85, 22.30), (46.80, 22.80), (46.72, 23.20), (46.68, 23.62),
    (46.62, 24.00), (46.48, 24.25), (46.35, 24.55), (46.22, 24.85), (46.05, 25.10), (45.90, 25.38),
    (45.78, 25.72), (45.70, 26.05), (45.85, 26.38), (46.20, 26.28), (46.60, 26.05), (47.00, 25.90),
    (47.30, 25.68), (47.55, 25.20), (47.75, 24.95), (47.97, 24.65),
]

EUPEN_MALMEDY = [(50.76, 5.98), (50.75, 6.28), (50.45, 6.38), (50.13, 6.40), (50.15, 6.05), (50.40, 5.98), (50.62, 6.00)]

CHANNEL_ISLANDS = [
    blob([(49.27, -2.27), (49.27, -2.00), (49.15, -2.00), (49.15, -2.27)], amp=0.3, seed=1),  # Jersey
    blob([(49.52, -2.70), (49.52, -2.48), (49.40, -2.48), (49.40, -2.70)], amp=0.3, seed=2),  # Guernsey
    blob([(49.74, -2.25), (49.74, -2.14), (49.69, -2.14), (49.69, -2.25)], amp=0.2, seed=3),  # Alderney
]


def build(tl):
    W = world()
    # --- Baltic states ---
    for code, date, edge in (("LTU", "1940-06-15", "1940-06-16 12"), ("LVA", "1940-06-17", "1940-06-18 12"),
                             ("EST", "1940-06-17", "1940-06-18 12")):
        L = tl.layer("occupation-" + code, "SOV", within=[code], order=45)
        L.key(date + " 06", J([(60.5, 26.5), (57.0, 25.5), (55.0, 25.0), (53.5, 25.0)], amp=4, seg=10) +
              [(53.5, 32.0), (60.5, 32.0)])
        L.key(edge, mask=lambda: W.land | ~W.land)
    tl.political("1940-08-03", lambda: W.unit("LTU") | W.poly([(56.5, 20.0), (56.5, 27.5), (53.8, 27.5), (53.8, 20.0)]),
                 "SOV", where=["LTU"], dur=1.0, label="Lithuania annexed")
    tl.political("1940-08-05", lambda: W.land | ~W.land, "SOV", where=["LVA"], dur=1.0, label="Latvia annexed")
    tl.political("1940-08-06", lambda: W.land | ~W.land, "SOV", where=["EST"], dur=1.0, label="Estonia annexed")

    # --- Bessarabia, Northern Bukovina, Hertsa ---
    bess = lambda: W.unit("MDA") | W.unit("UKR")  # noqa: E731
    L = tl.layer("bessarabia-1940", "SOV", within=["ROU"], order=45)
    L.key("1940-06-28 14", J([(48.40, 26.4), (47.60, 27.6), (46.90, 29.1), (46.40, 29.9), (46.0, 30.4)],
                               amp=4, seg=10) + [(45.0, 31.0), (49.0, 31.0)])
    L.key("1940-07-03 12", mask=bess)
    tl.political("1940-07-04", bess, "SOV", where=["ROU"], dur=1.0, label="Bessarabia and N. Bukovina to the USSR")
    L.end("1940-07-05")

    # --- Second Vienna Award ---
    nt = lambda: W.poly(J(N_TRANSYLVANIA_LINE, amp=2.5, seg=8, seed=21) + [(48.6, 24.5), (48.6, 21.0), (46.9, 21.0)])  # noqa: E731
    H = tl.layer("n-transylvania", "HUN", within=["ROU"], order=45)
    H.key("1940-09-05 06", J([(47.95, 22.6), (47.6, 22.3), (47.1, 22.1), (46.9, 21.8)], amp=3, seg=8) + [(46.9, 21.0), (48.6, 21.0)])
    H.key("1940-09-13 18", mask=nt)
    tl.political("1940-09-14", nt, "HUN", where=["ROU"], dur=1.0, label="Northern Transylvania to Hungary")
    H.end("1940-09-15")

    # --- Southern Dobruja ---
    dob = lambda: W.prov("BGR", "Dobrich", "Silistra")  # noqa: E731
    D = tl.layer("s-dobruja", "BGR", within=["ROU"], order=45)
    D.key("1940-09-21 06", J([(44.15, 26.9), (43.95, 27.4), (43.75, 28.0), (43.70, 28.6)], amp=2, seg=6) + [(43.2, 28.6), (43.2, 26.9)])
    D.key("1940-10-01 12", mask=dob)
    tl.political("1940-10-02", dob, "BGR", where=["ROU"], dur=1.0, label="Southern Dobruja to Bulgaria")
    D.end("1940-10-03")

    # --- Western annexations ---
    tl.political("1940-05-18", lambda: W.poly(EUPEN_MALMEDY), "GER", where=["BEL"], dur=1.0, label="Eupen-Malmedy annexed")
    tl.political("1940-11-30", lambda: W.prov("FRA", "Bas-Rhin", "Haute-Rhin", "Moselle"), "GER", where=["FRA"], dur=1.0,
                 label="Alsace and Moselle annexed de facto")
    tl.political("1942-08-30", lambda: W.unit("LUX"), "GER", where=["LUX"], dur=1.0, label="Luxembourg annexed de facto")

    # --- Channel Islands ---
    C = tl.layer("channel-islands", "GER", within=["GBR"], order=45)
    C.key("1940-07-01 12", *CHANNEL_ISLANDS)
    C.end("1945-05-09 12")

    tl.caption("1940-06-15", "The Red Army occupies Lithuania; Latvia and Estonia follow on 17 June")
    tl.caption("1940-06-28", "Romania cedes Bessarabia and Northern Bukovina to the Soviet Union")
    tl.caption("1940-08-30", "Second Vienna Award: Northern Transylvania is given to Hungary")
    tl.caption("1940-09-07", "Treaty of Craiova: Southern Dobruja returns to Bulgaria")
