"""Balkans 1940-1945: Greco-Italian war, Yugoslavia and Greece (April 1941),
Crete, the partition of Yugoslavia, the Partisan war and liberation.

Sources: M. van Creveld, "Hitler's Strategy 1940-41: The Balkan Clue"
(1973); G. Blau, "The German Campaigns in the Balkans (Spring 1941)",
DA Pam 20-260 (1953); J. Tomasevich, "War and Revolution in Yugoslavia:
Occupation and Collaboration" (2001) - partition map; W. R. Roberts,
"Tito, Mihailovic and the Allies" (1973); Military History Institute
Belgrade, partisan liberated-territory maps (1941-45).
Partisan-held areas are generalised: their boundaries were fluid and are
shown at the extent of the major liberated territories (Uzice republic
Sep-Nov 1941, Bihac republic Nov 1942 - Jan 1943, after the Italian
capitulation Sep 1943, mid-1944, liberation Oct 1944 - May 1945).
"""
from core import world
from ctools import blob, J, circle
from places import P

# ------------------------------------------------------------------ Albania front 1940-41
ITA_EPIRUS = {   # Italian-held Greek Epirus (Nov 1940)
    "1940-10-28 06": [blob([(39.70, 20.00), (39.85, 20.22), (40.05, 20.60), (39.95, 20.05)], seed=1)],
    "1940-11-05 00": [blob([(39.45, 20.25), (39.62, 20.45), (39.95, 20.75), (40.12, 20.90), (40.15, 20.60),
                            (39.95, 20.05), (39.60, 20.05)], seed=2)],
    "1940-11-12 00": [blob([(39.42, 20.25), (39.60, 20.45), (39.90, 20.70), (40.10, 20.85), (40.15, 20.60),
                            (39.95, 20.05), (39.60, 20.05)], seed=3)],
    "1940-11-22 00": [blob([(39.75, 20.05), (39.85, 20.35), (40.00, 20.45), (39.98, 20.05)], seed=4)],
}
GRC_ALB = {      # Greek-held southern Albania (counter-offensive)
    "1940-11-22 00": [blob([(40.35, 20.55), (40.75, 20.70), (40.85, 21.05), (40.45, 21.10), (40.10, 20.80)], seed=5)],
    "1940-12-08 00": [blob([(39.70, 19.98), (40.10, 20.05), (40.30, 20.25), (40.55, 20.40), (40.90, 20.60),
                            (40.95, 21.05), (40.45, 21.10), (39.95, 20.60), (39.70, 20.20)], seed=6)],
    "1940-12-30 00": [blob([(39.70, 19.98), (40.05, 19.75), (40.25, 20.05), (40.35, 20.30), (40.60, 20.45),
                            (40.95, 20.60), (40.95, 21.05), (40.45, 21.10), (39.95, 20.60), (39.70, 20.20)], seed=7)],
    "1941-01-15 00": [blob([(39.70, 19.98), (40.15, 19.62), (40.28, 20.05), (40.35, 20.30), (40.62, 20.45),
                            (40.97, 20.62), (40.95, 21.05), (40.45, 21.10), (39.95, 20.60), (39.70, 20.20)], seed=8)],
    "1941-04-12 00": [blob([(39.70, 19.98), (40.15, 19.62), (40.28, 20.05), (40.35, 20.30), (40.62, 20.45),
                            (40.97, 20.62), (40.95, 21.05), (40.45, 21.10), (39.95, 20.60), (39.70, 20.20)], seed=8)],
    "1941-04-18 00": [blob([(39.70, 19.98), (40.00, 20.05), (40.20, 20.35), (40.50, 20.55), (40.75, 20.80),
                            (40.70, 21.05), (40.40, 21.05), (39.95, 20.60), (39.70, 20.20)], seed=9)],
}

# ------------------------------------------------------------------ Yugoslavia & Greece, April 1941
YUG_AXIS = {
    "1941-04-06 06": [blob([(42.20, 22.80), (42.30, 22.40), (41.95, 22.20), (41.60, 22.70), (41.40, 23.10)], seed=11),
                      blob([(46.40, 16.30), (46.55, 15.60), (46.35, 15.30), (46.15, 15.90)], seed=12)],
    "1941-04-08 18": [blob([(42.60, 22.40), (42.35, 21.60), (41.90, 21.25), (41.40, 21.60), (41.15, 22.50),
                            (41.40, 23.10), (42.20, 22.90)], seed=13),
                      blob([(46.50, 16.40), (46.65, 15.20), (46.30, 14.80), (45.95, 15.40), (46.10, 16.20)], seed=14),
                      blob([(43.45, 22.30), (43.30, 22.00), (43.10, 22.30), (43.25, 22.75)], seed=15)],
    "1941-04-10 18": [blob([(43.40, 22.40), (43.30, 21.80), (42.60, 21.30), (42.00, 20.70), (41.40, 20.60),
                            (41.10, 21.30), (41.15, 22.50), (41.40, 23.10), (42.30, 22.95), (43.10, 22.80)], seed=16),
                      blob([(46.60, 16.60), (46.70, 14.40), (46.20, 13.70), (45.60, 14.20), (45.40, 15.20),
                            (45.60, 16.20), (45.90, 17.00), (46.20, 17.00)], seed=17),
                      blob([(46.15, 19.80), (46.10, 18.90), (45.70, 18.90), (45.65, 19.50)], seed=18)],
    "1941-04-13 00": [blob([(46.20, 20.30), (45.80, 18.80), (45.60, 16.90), (45.95, 16.50), (46.70, 16.20),
                            (46.70, 14.40), (46.20, 13.70), (45.40, 14.00), (44.90, 14.80), (44.40, 15.50),
                            (44.40, 16.60), (44.70, 17.80), (44.50, 19.30), (44.20, 20.30), (43.70, 20.80),
                            (43.20, 21.30), (42.60, 21.30), (42.00, 20.60), (41.10, 20.60), (41.10, 22.50),
                            (41.40, 23.10), (42.30, 22.95), (43.20, 22.70), (44.00, 22.70), (44.60, 22.30),
                            (45.10, 21.50), (45.70, 20.80)], seed=19)],
    "1941-04-17 18": None,  # whole of Yugoslavia
}
GRC_AXIS = {
    "1941-04-06 06": [blob([(41.40, 23.10), (41.35, 24.40), (41.10, 25.80), (40.90, 25.70), (41.05, 24.20)], seed=21)],
    "1941-04-09 18": [blob([(41.40, 23.10), (41.35, 24.40), (41.20, 26.40), (40.80, 25.90), (40.85, 24.40),
                            (40.55, 23.70), (40.50, 22.80), (40.95, 22.40), (41.15, 22.60)], seed=22)],
    "1941-04-14 00": [blob([(41.40, 23.10), (41.35, 24.40), (41.20, 26.40), (40.80, 25.90), (40.85, 24.40),
                            (40.30, 23.90), (40.20, 22.70), (40.30, 21.70), (40.70, 21.20), (41.00, 21.20),
                            (41.15, 22.60)], seed=23)],
    "1941-04-20 00": [blob([(41.40, 23.10), (41.35, 24.40), (41.20, 26.40), (40.80, 25.90), (40.85, 24.40),
                            (39.90, 23.40), (39.40, 23.00), (39.50, 22.20), (39.90, 21.40), (40.40, 20.80),
                            (40.80, 21.00), (41.15, 22.60)], seed=24)],
    "1941-04-25 00": [blob([(41.40, 23.10), (41.35, 24.40), (41.20, 26.40), (40.80, 25.90), (40.85, 24.40),
                            (39.50, 23.30), (38.85, 22.90), (38.75, 22.40), (38.90, 21.40), (39.30, 20.50),
                            (39.90, 20.10), (40.40, 20.80), (41.15, 22.60)], seed=25)],
    "1941-04-28 00": [blob([(41.40, 23.10), (41.35, 24.40), (41.20, 26.40), (40.80, 25.90), (40.85, 24.40),
                            (38.40, 24.20), (37.80, 24.10), (37.80, 23.30), (38.10, 22.40), (38.30, 21.30),
                            (39.30, 20.30), (39.90, 20.10), (40.40, 20.80), (41.15, 22.60)], seed=26)],
    "1941-04-30 18": None,
}
CRETE_AXIS = {
    "1941-05-20 08": [blob(circle(35.53, 23.83, 9, 10), seed=31), blob(circle(35.37, 24.47, 6, 10), seed=32),
                      blob(circle(35.34, 25.18, 7, 10), seed=33)],
    "1941-05-23 00": [blob([(35.55, 23.70), (35.55, 23.95), (35.45, 23.95), (35.45, 23.70)], seed=34),
                      blob(circle(35.37, 24.47, 6, 10), seed=32), blob(circle(35.34, 25.18, 7, 10), seed=33)],
    "1941-05-28 00": [blob([(35.65, 23.55), (35.55, 24.20), (35.30, 24.15), (35.30, 23.55)], seed=35),
                      blob(circle(35.37, 24.47, 9, 10), seed=32), blob(circle(35.34, 25.18, 10, 10), seed=33)],
    "1941-06-01 12": None,
}

# ------------------------------------------------------------------ Yugoslav Partisans (controller PAR)
# Partisan / insurgent-held areas, generalised from published liberated-territory maps (see the module docstring).
# Rings are (lat, lon); blob() adds an irregular edge. No rectangular masks: every edge follows geography
# (rivers, ridges, the Srem front) or is a hand-drawn irregular line.
MNE_RISING = blob([(43.35, 19.15), (43.30, 19.55), (43.10, 19.90), (42.90, 20.05), (42.60, 20.00), (42.40, 19.70),
                   (42.35, 19.30), (42.45, 19.00), (42.60, 18.80), (42.85, 18.65), (43.10, 18.70), (43.28, 18.90)], seed=40)
MNE_RISING_LATE = blob([(43.05, 19.20), (43.00, 19.60), (42.80, 19.75), (42.70, 19.35), (42.85, 19.10)], seed=41)
KRAJINA_JUL41 = [blob([(44.80, 15.45), (44.70, 16.15), (44.45, 16.80), (44.10, 17.15), (43.75, 17.25), (43.70, 16.85),
                       (43.95, 16.45), (44.20, 15.95), (44.45, 15.35)], seed=42),            # Lika - Grmec - Drvar - Glamoc strip
                 blob([(45.45, 16.25), (45.42, 16.62), (45.22, 16.58), (45.15, 16.20), (45.30, 16.02)], seed=43),   # Banija
                 blob([(45.28, 15.50), (45.30, 15.95), (45.10, 15.98), (45.05, 15.58)], seed=44)]                 # Kordun
KRAJINA_AUG41 = [blob([(44.95, 15.70), (44.85, 16.40), (44.55, 17.00), (44.20, 17.25), (43.80, 17.30), (43.65, 16.90),
                       (43.85, 16.40), (44.15, 15.90), (44.35, 15.30), (44.70, 15.30)], seed=45),
                 blob([(45.50, 16.20), (45.48, 16.70), (45.20, 16.65), (45.10, 16.15), (45.25, 15.95)], seed=46),
                 blob([(45.30, 15.45), (45.35, 16.00), (45.10, 16.05), (45.00, 15.55)], seed=47)]
SERBIA_AUG41 = [blob([(44.62, 19.10), (44.62, 19.75), (44.30, 19.95), (44.05, 19.80), (44.00, 19.30), (44.25, 19.10)], seed=48),   # Podrinje
                blob([(44.20, 20.35), (44.20, 20.75), (43.90, 20.80), (43.80, 20.45), (43.95, 20.30)], seed=49)]                   # Sumadija
UZICE = blob([(44.55, 19.30), (44.62, 19.80), (44.50, 20.30), (44.18, 20.55), (43.85, 20.55), (43.58, 20.30), (43.42, 19.95),
              (43.45, 19.55), (43.68, 19.30), (44.02, 19.25), (44.30, 19.18)], seed=50)
UZICE_NOV = blob([(44.10, 19.50), (44.15, 20.00), (43.85, 20.15), (43.55, 19.95), (43.50, 19.60), (43.80, 19.45)], seed=51)
FOCA42 = blob([(43.85, 18.55), (43.85, 19.10), (43.60, 19.35), (43.30, 19.00), (43.25, 18.60), (43.50, 18.40)], seed=52)
BIHAC = blob([(45.25, 15.70), (45.18, 16.40), (44.85, 16.95), (44.45, 17.30), (44.05, 17.20), (43.85, 16.75), (43.90, 16.20),
              (44.20, 15.60), (44.60, 15.25), (44.95, 15.35)], seed=53)
KORDUN_43 = [blob([(45.35, 15.60), (45.32, 16.20), (45.10, 16.20), (45.05, 15.65)], seed=54),          # Kordun / Banija hills
             blob([(44.75, 15.60), (44.65, 16.20), (44.40, 16.25), (44.35, 15.70)], seed=55),          # Lika / Grmec
             blob([(43.20, 18.55), (43.20, 19.20), (42.90, 19.25), (42.85, 18.65)], seed=56)]          # Sutjeska / Durmitor
PART_SEP43 = [blob([(45.45, 14.90), (45.35, 15.80), (45.20, 16.50), (44.85, 17.45), (44.40, 18.00), (43.90, 18.00),
                    (43.30, 17.60), (43.00, 17.30), (43.20, 16.60), (43.55, 16.10), (44.00, 15.45), (44.40, 15.15),
                    (44.95, 14.75)], seed=57),                                                       # Lika, Dalmatia, W Bosnia
              blob([(43.30, 18.60), (43.30, 19.60), (42.95, 19.95), (42.45, 19.50), (42.35, 18.90), (42.80, 18.60)], seed=58),   # Montenegro
              blob([(46.05, 14.40), (46.00, 15.20), (45.65, 15.35), (45.50, 14.80), (45.60, 14.35)], seed=59)]  # Slovenia/Bela krajina
PART_NOV43 = [blob([(45.30, 15.55), (45.30, 16.30), (45.05, 16.50), (44.60, 17.50), (44.25, 17.60), (43.90, 17.45),
                    (43.75, 16.90), (43.95, 16.30), (44.30, 15.65), (44.75, 15.30)], seed=60),      # W Bosnia (Jajce, Bihac, Drvar)
              blob([(43.60, 16.50), (43.50, 17.10), (43.25, 17.00), (43.30, 16.55)], seed=61),         # Hvar / Brac / Vis
              blob([(43.20, 18.60), (43.15, 19.30), (42.85, 19.30), (42.85, 18.65)], seed=62)]
PART_JUN44 = [blob([(45.35, 15.45), (45.25, 16.40), (45.00, 16.60), (44.60, 17.55), (44.30, 17.70), (43.95, 17.60),
                    (43.65, 17.05), (43.55, 16.40), (43.95, 16.00), (44.40, 15.55), (44.85, 15.25)], seed=63),
              blob([(43.55, 16.30), (43.50, 17.15), (43.25, 17.20), (43.28, 16.45)], seed=64),         # islands
              blob([(43.60, 18.55), (43.65, 19.45), (43.15, 19.90), (42.50, 19.55), (42.35, 18.95), (42.85, 18.60)], seed=65),
              blob([(45.80, 14.50), (45.82, 15.30), (45.50, 15.35), (45.45, 14.65)], seed=66)]
# Oct 1944: Serbia liberated up to the Srem front with the Red Army; Montenegro / Macedonia / Kosovo follow in Nov
PART_OCT44 = [blob([(45.35, 15.40), (45.25, 16.40), (45.00, 16.65), (44.60, 17.60), (44.20, 17.80), (43.85, 17.60),
                    (43.30, 17.50), (43.40, 16.55), (43.95, 16.00), (44.40, 15.55), (44.85, 15.25)], seed=67),
              blob([(44.95, 19.30), (45.05, 20.40), (44.60, 21.40), (44.20, 22.45), (43.60, 22.60), (43.10, 21.90),
                    (43.00, 20.90), (43.35, 19.95), (43.70, 19.40), (44.20, 19.25)], seed=68)]      # Serbia west of the Morava, Belgrade
SRBMKD_DEC44 = blob([(46.10, 19.55), (46.00, 20.60), (45.45, 21.50), (44.95, 22.20), (44.55, 22.80), (43.95, 22.95),
                     (43.30, 22.90), (42.60, 22.95), (41.85, 22.80), (41.45, 22.95), (41.00, 22.60), (41.00, 20.95),
                     (41.50, 20.50), (42.05, 20.10), (42.55, 19.40), (43.00, 19.00), (43.45, 19.20), (43.85, 19.30),
                     (44.35, 19.20), (44.85, 19.20), (45.20, 19.35), (45.50, 19.30), (45.85, 19.20)], seed=69)
WESTBOS_DEC44 = blob([(45.35, 15.50), (45.30, 16.30), (45.00, 16.65), (44.70, 17.30), (44.25, 17.75), (43.95, 17.90),
                      (43.55, 18.10), (43.15, 18.40), (42.80, 18.30), (42.60, 18.15), (42.95, 17.55), (43.35, 16.95),
                      (43.50, 16.40), (43.95, 15.95), (44.35, 15.50), (44.85, 15.25)], seed=70)
PART_DEC44 = [SRBMKD_DEC44, WESTBOS_DEC44]
PART_APR45 = [blob([(46.05, 19.55), (46.00, 20.60), (45.45, 21.50), (44.95, 22.20), (44.55, 22.80), (43.95, 22.95),
                    (43.30, 22.90), (42.60, 22.95), (41.85, 22.80), (41.45, 22.95), (41.00, 22.60), (41.00, 20.95),
                    (41.50, 20.50), (42.05, 20.10), (42.50, 19.40), (42.60, 18.40), (42.95, 17.95), (43.60, 17.55),
                    (44.00, 16.90), (44.50, 16.40), (44.90, 15.80), (45.35, 15.50), (45.55, 16.50), (45.25, 17.30),
                    (45.00, 18.30), (45.15, 18.95), (45.50, 19.30), (45.85, 19.20)], seed=71)]
PART_MAY45 = None  # all of Yugoslavia (+ Trieste, Istria)

ITALIAN_DALMATIA = [(44.30, 14.90), (44.20, 15.60), (43.80, 15.90), (43.55, 16.25), (43.45, 16.55), (43.30, 16.50),
                    (43.00, 16.00), (42.70, 16.50), (42.85, 17.30), (43.35, 16.10), (43.70, 15.60), (44.00, 15.10)]
KOTOR = [(42.55, 18.45), (42.55, 18.85), (42.35, 18.85), (42.35, 18.45)]
LJUBLJANA_PROV = ["Ljubljana", "Kocevje", "Novo Mesto", "Crnomelj", "Metlika", "Grosuplje", "Ribnica", "Cerknica",
                  "Logatec", "Vrhnika", "Ig", "Škofljica", "Velike Lašče", "Dobrepolje", "Ivancna Gorica", "Trebnje",
                  "Žužemberk", "Dolenjske Toplice", "Semic", "Loška dolina", "Loški Potok", "Sodražica", "Bloke",
                  "Borovnica", "Brezovica", "Kostel", "Mirna Pec", "Šentjernej", "Škocjan", "Horjul",
                  "Dobrova-Polhov Gradec", "Medvode", "Dol pri Ljubljani"]
PREKMURJE = ["Moravske Toplice", "Šalovci", "Hodoš", "Gornji Petrovci", "Kuzma", "Lendava", "Dobrovnik", "Kobilje",
             "Rogašovci", "Cankova", "Murska Sobota", "Puconci", "Beltinci", "Turnišče", "Velika Polana",
             "Črenšovci", "Odranci", "Grad"]
ALB_MKD = ["Tetovo", "Gostivar", "Debar", "Struga", "Kičevo", "Jegunovce", "Tearce", "Bogovinje", "Brvenica",
           "Vrapcište", "Želino", "Mavrovo and Rostusa", "Centar župa", "Vevčani", "Zajas", "Oslomej", "Vraneštica",
           "Plasnica", "Drugovo", "Debarca"]


def build(tl):
    W = world()
    allc = lambda: W.land | ~W.land  # noqa: E731
    crete = lambda: W.poly([(35.75, 23.4), (35.75, 26.4), (34.8, 26.4), (34.8, 23.4)])  # noqa: E731

    # --- Greco-Italian war ---
    ie = tl.layer("epirus-italian", "ITA", within=["GRC"], order=80)
    for d, r in ITA_EPIRUS.items():
        ie.key(d, *r)
    ie.end("1940-11-23 12")
    ga = tl.layer("albania-greek", "GRC", within=["ALB"], order=80)
    for d, r in GRC_ALB.items():
        ga.key(d, *r)
    ga.end("1941-04-23 00")

    # --- Yugoslavia, Greece, Crete 1941 ---
    for name, data, within in (("yugoslavia-1941", YUG_AXIS, ["YUG"]), ("greece-1941", GRC_AXIS, ["GRC"]),
                               ("crete-1941", CRETE_AXIS, ["GRC"])):
        L = tl.layer(name, "GER", within=within, order=81 if name != "crete-1941" else 82)
        for d, r in data.items():
            if r is None:
                if name == "crete-1941":
                    L.key(d, mask=crete)
                elif name == "greece-1941":
                    L.key(d, mask=lambda: allc() & ~crete())
                    L.key("1941-06-01 12", mask=allc, span=0.2)
                else:
                    L.key(d, mask=allc)
            else:
                L.key(d, *r)
        if name == "greece-1941":
            gr = L
        if name == "crete-1941":
            L.end("1941-06-01 18", span=0.1)

    # --- Partition of Yugoslavia (de facto, April - July 1941) ---
    hrv_ndh = lambda: ((W.unit("HRV") | W.unit("BIH") | W.prov("SRB", "Sremski")) & ~W.prov("HRV", "Istarska", "Medimurska")  # noqa: E731
                       & ~W.poly(ITALIAN_DALMATIA))
    tl.political("1941-04-15", hrv_ndh, "CRO", where=["YUG"], dur=2.0, label="Independent State of Croatia")
    tl.political("1941-04-20", lambda: W.prov("SRB", "Severno-Backi", "Zapadno-Backi", "Južno-Backi") |  # noqa: E731
                 W.prov("HRV", "Medimurska") | W.prov("SVN", *PREKMURJE) |
                 (W.prov("HRV", "Osjecko-Baranjska") & W.poly([(46.0, 18.3), (46.0, 19.0), (45.62, 19.0), (45.62, 18.3)])),
                 "HUN", where=["YUG", "CRO"], dur=2.0, label="Hungary annexes Backa and Baranja")
    tl.political("1941-05-03", lambda: W.prov("SVN", *LJUBLJANA_PROV), "ITA", where=["YUG"], dur=1.0,
                 label="Province of Ljubljana")
    tl.political("1941-05-18", lambda: W.poly(ITALIAN_DALMATIA) | W.poly(KOTOR) |  # noqa: E731
                 W.poly([(45.25, 14.40), (45.25, 14.90), (44.70, 14.90), (44.70, 14.40)]),
                 "ITA", where=["YUG", "CRO"], dur=1.0, label="Italy annexes Dalmatia")
    tl.political("1941-04-25", lambda: W.unit("SVN"), "GER", where=["YUG"], dur=2.0,
                 label="Northern Slovenia annexed de facto by Germany")
    tl.political("1941-04-25", lambda: W.unit("MKD") & ~W.prov("MKD", *ALB_MKD) | W.prov("SRB", "Pcinjski"),  # noqa: E731
                 "BGR", where=["YUG"], dur=2.0, label="Bulgaria occupies Macedonia")
    tl.political("1941-06-29", lambda: (W.unit("KOS") & ~W.prov("KOS", "Leposavić", "Zubin Potok", "Zvečan",  # noqa: E731
                                                                "Kosovska Mitrovica", "Vučitrn", "Podujevo")) |
                 W.prov("MKD", *ALB_MKD) | W.prov("MNE", "Ulcinj", "Plav", "Rožaje"),
                 "ALB", where=["YUG"], dur=2.0, label="Kosovo and western Macedonia to Albania")
    tl.political("1941-07-12", lambda: W.unit("MNE"), "MNE", where=["YUG"], dur=1.0, label="Montenegro governorate")
    tl.political("1941-05-01", lambda: W.unit("SRB") | W.unit("KOS"), "SRB", where=["YUG"], dur=1.0,
                 label="Military administration in Serbia")
    tl.political("1941-05-14", lambda: W.prov("GRC", "Anatoliki Makedonia kai Thraki") &  # noqa: E731
                 ~W.poly([(41.75, 25.95), (41.75, 26.70), (40.70, 26.70), (40.70, 25.95)]) |
                 (W.prov("GRC", "Kentriki Makedonia") & W.poly([(41.40, 23.25), (41.40, 24.10), (40.75, 24.10), (40.75, 23.25)])),
                 "BGR", where=["GRC"], dur=2.0, label="Bulgaria annexes eastern Macedonia and western Thrace")

    # --- Partisans ---
    pa = tl.layer("partisans", "PAR", within=["CRO", "SRB", "MNE", "YUG", "ITA", "ALB", "BGR", "HUN", "GER"], order=90)
    # 1941: the risings. Montenegro 13 Jul (crushed by the Italians by August), Lika / Bosnian Krajina / Banija /
    # Kordun from 27 Jul, western Serbia from July; Uzice Republic 24 Sep - 29 Nov (German Operation Uzice)
    pa.key("1941-07-13 00", MNE_RISING_LATE)
    pa.key("1941-07-20 00", MNE_RISING, span=5)
    pa.key("1941-07-27 12", MNE_RISING, *KRAJINA_JUL41[:1], span=3)
    pa.key("1941-08-05 00", MNE_RISING_LATE, *KRAJINA_JUL41, span=6)
    pa.key("1941-08-29 00", MNE_RISING_LATE, *KRAJINA_AUG41, *SERBIA_AUG41, span=12)
    pa.key("1941-09-24 00", MNE_RISING_LATE, *KRAJINA_AUG41, UZICE, span=12)
    pa.key("1941-11-20 00", *KRAJINA_AUG41, UZICE, span=20)
    pa.key("1941-11-29 12", *KRAJINA_JUL41, UZICE_NOV, span=8)
    pa.key("1941-12-20 00", *KRAJINA_JUL41[:1], span=20)
    pa.key("1942-03-01 00", FOCA42, *KRAJINA_JUL41[:2], span=30)
    pa.key("1942-08-01 00", FOCA42, *KRAJINA_JUL41, span=30)
    pa.key("1942-11-04 00", BIHAC, FOCA42, span=10)
    pa.key("1943-02-01 00", BIHAC, span=15)
    pa.key("1943-04-10 00", *KORDUN_43, span=20)
    pa.key("1943-09-25 00", *PART_SEP43, span=10)
    pa.key("1943-11-20 00", *PART_NOV43, span=20)
    pa.key("1944-06-15 00", *PART_JUN44, span=25)
    pa.key("1944-10-20 00", *PART_OCT44, span=18)
    pa.key("1944-12-15 00", *PART_DEC44, span=45)
    pa.key("1945-04-15 00", *PART_APR45, span=35)
    yu = lambda: (W.unit("HRV") | W.unit("BIH") | W.unit("SRB") | W.unit("MNE") | W.unit("MKD") |  # noqa: E731
                  W.unit("SVN") | W.unit("KOS") | W.poly([(46.0, 13.4), (46.0, 14.2), (45.4, 14.2), (45.4, 13.4)]))
    pa.key("1945-05-09 18", mask=yu, span=24)
    # Albania: liberated by the partisans in autumn 1944
    al = tl.layer("albania-partisans", "PAR", within=["ALB"], order=91)
    al.key("1944-09-01 00", blob([(40.70, 20.30), (40.60, 20.95), (40.10, 20.70), (39.90, 20.25), (40.30, 19.85)], seed=56))
    al.key("1944-10-25 00", blob([(41.30, 19.70), (41.20, 20.50), (40.60, 21.00), (39.70, 20.30), (40.20, 19.50)], seed=57))
    al.key("1944-11-29 12", mask=lambda: W.unit("ALB"))

    # --- Greece 1943-45: German occupation, withdrawal, British landing ---
    # gr (German, within GRC) holds all of Greece after 30 Apr 1941; liberation:
    gr.key("1944-09-25 00", blob([(41.80, 21.00), (41.80, 26.70), (37.80, 26.70), (37.80, 22.80), (38.60, 21.00)], seed=58),
           mask=lambda: W.poly([(35.75, 23.4), (35.75, 26.4), (34.8, 26.4), (34.8, 23.4)]))
    gr.key("1944-10-14 00", blob([(41.80, 21.00), (41.80, 26.70), (39.30, 26.70), (38.95, 23.40), (39.10, 21.00)], seed=59),
           mask=lambda: W.poly([(35.75, 23.4), (35.75, 26.4), (34.8, 26.4), (34.8, 23.4)]))
    gr.key("1944-11-02 12", blob([(35.62, 23.55), (35.62, 24.25), (35.35, 24.25), (35.30, 23.55)], seed=60),
           mask=lambda: W.poly([(38.0, 23.8), (38.0, 24.2), (37.5, 24.2), (37.5, 23.8)]) & False)
    gr.end("1945-05-09 12")

    # --- 1944-45: Bulgarian withdrawal and re-unification of Yugoslavia ---
    tl.political("1944-10-25", lambda: W.unit("GRC"), "GRC", where=["BGR"], dur=3.0,
                 label="Bulgarian troops leave Greek Macedonia and Thrace")
    tl.political("1944-10-20", lambda: W.unit("MKD") | W.prov("SRB", "Pcinjski"), "YUG", where=["BGR"], dur=3.0)
    trieste = lambda: W.poly([(46.0, 13.4), (46.0, 14.2), (45.4, 14.2), (45.4, 13.4)]) | W.prov("HRV", "Istarska")  # noqa: E731
    tl.political("1945-05-15", lambda: yu() & ~trieste(), "YUG",
                 where=["CRO", "SRB", "MNE", "ITA", "HUN", "GER", "ALB", "BGR"], dur=2.0,
                 label="Yugoslavia restored")
    tl.pocket("1944-11-02 12", "1945-05-09 12", 35.45, 23.90, "Fortress Crete", side="axis")

    for d, t in [("1940-10-28", "Italy invades Greece from Albania"),
                 ("1940-11-14", "The Greek army counter-attacks and drives the Italians back into Albania"),
                 ("1940-12-08", "Greek troops take Argyrokastro"),
                 ("1941-03-09", "The Italian spring offensive in Albania fails"),
                 ("1941-04-06", "Germany invades Yugoslavia and Greece"),
                 ("1941-04-17", "Yugoslavia surrenders"),
                 ("1941-04-27", "German troops enter Athens"),
                 ("1941-05-20", "German paratroopers land on Crete"),
                 ("1941-06-01", "The last Commonwealth troops are evacuated from Crete"),
                 ("1941-09-24", "Tito's Partisans proclaim the Uzice Republic"),
                 ("1942-11-26", "The Partisans form AVNOJ at Bihac"),
                 ("1944-10-14", "German forces leave Athens"),
                 ("1944-11-29", "Albania is liberated by its partisans"),
                 ("1945-04-12", "The Yugoslav army breaks through the Syrmian front")]:
        tl.caption(d, t)
