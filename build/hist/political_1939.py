"""De facto political map of Europe, North Africa and the Middle East on
1 September 1939 (before the first shots at Westerplatte).

Built by painting modern Natural Earth units with their 1939 owner and
then repainting the territories whose 1939 border differs from today's
(see borders.py). Each override is conditioned on the modern unit it
modifies, so the authored polygons only need to be precise along the
historical line itself.
"""
import numpy as np

from core import world, river
import borders as B
from units import BY_CODE

ID = {c: u["id"] for c, u in BY_CODE.items()}

MODERN = {
    "DEU": "GER", "AUT": "GER", "CZE": "GER", "SVK": "SVK", "POL": "GER", "HUN": "HUN",
    "ROU": "ROU", "BGR": "BGR", "SRB": "YUG", "HRV": "YUG", "SVN": "YUG", "BIH": "YUG",
    "MNE": "YUG", "MKD": "YUG", "KOS": "YUG", "GRC": "GRC", "ALB": "ALB", "ITA": "ITA",
    "SMR": "SMR", "VAT": "VAT", "FRA": "FRA", "MCO": "MCO", "BEL": "BEL", "NLD": "NLD",
    "LUX": "LUX", "CHE": "CHE", "LIE": "LIE", "DNK": "DNK", "NOR": "NOR", "SWE": "SWE",
    "FIN": "FIN", "ALD": "FIN", "EST": "EST", "LVA": "LVA", "LTU": "LTU", "RUS": "SOV",
    "BLR": "SOV", "UKR": "SOV", "MDA": "ROU", "GEO": "SOV", "ARM": "SOV", "AZE": "SOV",
    "KAZ": "SOV", "UZB": "SOV", "TKM": "SOV", "GBR": "GBR", "IMN": "GBR", "JEY": "GBR",
    "GGY": "GBR", "IRL": "IRL", "ISL": "ISL", "FRO": "FRO", "GRL": "GRL", "ESP": "ESP",
    "PRT": "PRT", "AND": "AND", "GIB": "GIB", "MLT": "MLT", "CYP": "CYP", "CYN": "CYP",
    "ESB": "CYP", "WSB": "CYP", "CNM": "CYP", "TUR": "TUR", "SYR": "SYR", "LBN": "LBN",
    "ISR": "PAL", "PSX": "PAL", "JOR": "TRJ", "IRQ": "IRQ", "IRN": "IRN", "SAU": "SAU",
    "KWT": "KWT", "QAT": "GULF", "ARE": "GULF", "BHR": "GULF", "OMN": "OMN", "EGY": "EGY",
    "LBY": "LBY", "TUN": "TUN", "DZA": "DZA", "MAR": "MAR", "SAH": "SSA", "MRT": "FWA",
    "MLI": "FWA",
}


def poland_1939_ring():
    """Interwar Poland west of the Riga line, as a ring covering the parts of
    modern Poland that were Polish (applied to modern Polish cells only)."""
    danzig_inner = B.DANZIG[:12]  # coast at Orlowo .. Piekel on the Vistula
    return (
        list(B.GER_POL_WEST)
        + [(49.0, 18.3), (49.0, 25.0), (55.0, 25.0)]
        + list(reversed(B.EPR_POL))
        + list(reversed(danzig_inner))
        + [(54.55, 18.70), (54.65, 18.85), (54.95, 18.85), (54.95, 18.03)]
    )


def build():
    W = world()
    C = np.zeros(W.land.shape, np.uint8)

    for code, unit in MODERN.items():
        if code in W.adm0_index:
            C[W.unit(code)] = ID[unit]

    def paint(mask, unit, within=None):
        m = mask if within is None else (mask & within)
        C[m] = ID[unit]

    # --- Bessarabia and Transnistria (Romania held Bessarabia 1918-1940) ---
    paint(W.prov("MDA", "Stîngă Nistrului", "Transnistria", "Camenca", "Grigoriopol"), "SOV")
    paint(W.poly(B.BUDJAK), "ROU", W.unit("UKR"))
    # the Bender municipality straddles the Dniester: its left bank (Tiraspol) was Soviet
    left_bank = river("Dniester", (47.00, 29.40), (46.65, 29.75)) + [(46.6, 30.2), (47.05, 30.2)]
    paint(W.poly(left_bank), "SOV", W.prov("MDA", "Bender"))
    paint(W.prov("UKR", "Chernivtsi"), "ROU")          # Northern Bukovina, Hertsa, Hotin
    paint(W.prov("UKR", "Transcarpathia"), "HUN")      # Carpatho-Ukraine, annexed March 1939

    # --- Interwar Poland ---
    pol_modern = W.unit("POL")
    paint(W.poly(poland_1939_ring()), "POL", pol_modern)
    paint(W.prov("UKR", "Volyn", "Rivne", "L'viv", "Ivano-Frankivs'k", "Ternopil'"), "POL")
    paint(W.prov("BLR", "Grodno", "Brest"), "POL")
    paint(W.poly(B.RIGA_BELARUS), "POL", W.unit("BLR"))
    paint(W.poly(B.VILNIUS_REGION), "POL", W.unit("LTU"))
    paint(W.poly(B.ZAOLZIE), "POL", W.unit("CZE"))
    paint(W.poly(B.DANZIG), "DAN", pol_modern)

    # --- German Reich (1937 borders + Austria, Sudetenland, Memel) ---
    paint(W.unit("RUS") & W.prov("RUS", "Kaliningrad"), "GER")
    paint(W.poly(B.MEMEL), "GER", W.unit("LTU"))
    czech = W.unit("CZE") & (C != ID["POL"])
    paint(W.poly(B.PROTECTORATE), "PRO", czech)

    # --- Hungary's gains from Czechoslovakia (Nov 1938, Mar 1939) ---
    paint(W.poly(B.HUN_SLOVAK_1939), "HUN", W.unit("SVK"))

    # --- Finland, Estonia, Latvia: territory lost to the USSR after 1940 ---
    rus = W.unit("RUS")
    paint(W.poly(B.FIN_KARELIA_1920), "FIN", rus)
    paint(W.poly(B.FIN_SALLA_1920), "FIN", rus)
    paint(W.poly(B.FIN_PETSAMO), "FIN", rus)
    for isl in B.FIN_GULF_ISLANDS:
        paint(W.poly(isl), "FIN", rus)
    paint(W.poly(B.EST_PETSERI), "EST", rus)
    paint(W.poly(B.EST_NARVA_EAST), "EST", rus)
    paint(W.poly(B.LVA_ABRENE), "LVA", rus)

    # --- Italy: Julian March, Fiume, Zara, Lagosta, Dodecanese ---
    paint(W.prov("SVN", *B.ITA_SLOVENIA_MUNIS), "ITA")
    paint(W.prov("HRV", "Istarska"), "ITA")
    hrv = W.unit("HRV")
    for ring in (B.ITA_LIBURNIA, B.ITA_CRES_LOSINJ, B.ITA_ZARA, B.ITA_LAGOSTA):
        paint(W.poly(ring), "ITA", hrv)
    paint(W.poly(B.DODECANESE), "DOD", W.unit("GRC"))

    # --- Romania's Southern Dobruja (to Bulgaria in September 1940) ---
    paint(W.prov("BGR", "Dobrich", "Silistra"), "ROU")

    # --- Spanish zones in Morocco ---
    mar = W.unit("MAR")
    paint(W.poly(B.SPANISH_MOROCCO), "SMA", mar)
    paint(W.poly(B.TANGIER), "TNG", mar)
    paint(W.poly(B.CAPE_JUBY), "SSA", mar)
    paint(W.poly(B.IFNI), "SSA", mar)

    return C


def fill_coast(C, land):
    """Give every cell the id of the nearest land cell so that the renderer can
    colour the high resolution coastline of the basemap without gaps."""
    from scipy import ndimage
    known = land & (C > 0)
    idx = ndimage.distance_transform_edt(~known, return_distances=False, return_indices=True)
    return C[idx[0], idx[1]]


if __name__ == "__main__":
    import sys
    C = build()
    W = world()
    print("unassigned land cells:", int((W.land & (C == 0)).sum()), file=sys.stderr)
