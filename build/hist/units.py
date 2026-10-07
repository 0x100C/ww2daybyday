"""Political units and powers.

One id space (0..255) serves both rasters:
  country  the de facto political unit a cell belongs to (drives the
           national border lines)
  control  the power whose forces hold the cell (drives the fill colour)

Each unit carries a faction timeline. The renderer colours a cell by the
faction of its controller on the displayed date, so a country that
changes sides (Italy 1940 and 1943, Romania 1944 ...) recolours without
any territorial event.

Factions
  neutral   pale beige
  axis      grey olive (Germany and its European allies)
  vichy     light grey olive (Vichy France and its empire)
  allied    blue (Western Allies and allied governments)
  allied_c  light blue (Allied colonies, mandates, dependencies)
  soviet    terracotta
  partisan  light red (Yugoslav partisans, communist resistance zones)
"""

UNITS = []
BY_CODE = {}


def U(code, name, factions, kind="state"):
    uid = len(UNITS) + 1
    u = {"id": uid, "code": code, "name": name, "factions": factions, "kind": kind}
    UNITS.append(u)
    BY_CODE[code] = u
    return uid


N = [("1939-09-01", "neutral")]

# ---- Axis -----------------------------------------------------------------
GER = U("GER", "German Reich", [("1939-09-01", "axis")])
PRO = U("PRO", "Protectorate of Bohemia and Moravia", [("1939-09-01", "axis")], "protectorate")
GG = U("GG", "General Government", [("1939-10-26", "axis")], "occupation")
ITA = U("ITA", "Italy", [("1939-09-01", "neutral"), ("1940-06-10", "axis"), ("1943-09-08", "allied")])
RSI = U("RSI", "Italian Social Republic", [("1943-09-23", "axis")], "puppet")
ALB = U("ALB", "Albania", [("1939-09-01", "neutral"), ("1940-06-10", "axis"), ("1943-09-08", "axis")], "protectorate")
LBY = U("LBY", "Libya", [("1939-09-01", "neutral"), ("1940-06-10", "axis"), ("1943-02-10", "allied_c")], "colony")
DOD = U("DOD", "Italian Dodecanese", [("1939-09-01", "neutral"), ("1940-06-10", "axis")], "colony")
SVK = U("SVK", "Slovakia", [("1939-09-01", "axis")])
HUN = U("HUN", "Hungary", [("1939-09-01", "neutral"), ("1940-11-20", "axis")])
ROU = U("ROU", "Romania", [("1939-09-01", "neutral"), ("1940-11-23", "axis"), ("1944-08-23", "allied")])
BGR = U("BGR", "Bulgaria", [("1939-09-01", "neutral"), ("1941-03-01", "axis"), ("1944-09-09", "allied")])
FIN = U("FIN", "Finland", [("1939-09-01", "neutral"),
                           ("1941-06-25", "axis"), ("1944-09-19", "neutral")])
CRO = U("CRO", "Independent State of Croatia", [("1941-04-10", "axis")], "puppet")
VIC = U("VIC", "Vichy France", [("1940-06-25", "vichy")], "state")
MNE = U("MNE", "Montenegro (Italian governorate)", [("1941-04-17", "axis")], "occupation")
SRB = U("SRB", "Serbia (German military administration)", [("1941-04-17", "axis")], "occupation")

# ---- Western Allies and their dependencies --------------------------------
GBR = U("GBR", "United Kingdom", [("1939-09-01", "allied")])
FRA = U("FRA", "France", [("1939-09-01", "allied")])
POL = U("POL", "Poland", [("1939-09-01", "allied")])
WAL = U("WAL", "Western Allies (field armies)", [("1939-09-01", "allied")], "force")
CYP = U("CYP", "Cyprus", [("1939-09-01", "allied_c")], "colony")
MLT = U("MLT", "Malta", [("1939-09-01", "allied_c")], "colony")
GIB = U("GIB", "Gibraltar", [("1939-09-01", "allied_c")], "colony")
EGY = U("EGY", "Egypt", [("1939-09-01", "allied_c")], "client")
PAL = U("PAL", "Palestine", [("1939-09-01", "allied_c")], "mandate")
TRJ = U("TRJ", "Transjordan", [("1939-09-01", "allied_c")], "mandate")
IRQ = U("IRQ", "Iraq", [("1939-09-01", "allied_c"), ("1941-04-01", "axis"), ("1941-05-31", "allied_c")], "client")
KWT = U("KWT", "Kuwait", [("1939-09-01", "allied_c")], "protectorate")
GULF = U("GULF", "British Gulf protectorates", [("1939-09-01", "allied_c")], "protectorate")
ADEN = U("ADEN", "Aden", [("1939-09-01", "allied_c")], "protectorate")
DZA = U("DZA", "Algeria", [("1939-09-01", "allied_c"), ("1940-06-25", "vichy"), ("1942-11-11", "allied_c")], "colony")
TUN = U("TUN", "Tunisia", [("1939-09-01", "allied_c"), ("1940-06-25", "vichy"), ("1943-05-13", "allied_c")], "protectorate")
MAR = U("MAR", "French Morocco", [("1939-09-01", "allied_c"), ("1940-06-25", "vichy"), ("1942-11-11", "allied_c")], "protectorate")
SYR = U("SYR", "Syria", [("1939-09-01", "allied_c"), ("1940-06-25", "vichy"), ("1941-07-14", "allied_c")], "mandate")
LBN = U("LBN", "Lebanon", [("1939-09-01", "allied_c"), ("1940-06-25", "vichy"), ("1941-07-14", "allied_c")], "mandate")
FWA = U("FWA", "French West Africa", [("1939-09-01", "allied_c"), ("1940-06-25", "vichy"), ("1942-11-23", "allied_c")], "colony")
BEL = U("BEL", "Belgium", N + [("1940-05-10", "allied")])
NLD = U("NLD", "Netherlands", N + [("1940-05-10", "allied")])
LUX = U("LUX", "Luxembourg", N + [("1940-05-10", "allied")])
NOR = U("NOR", "Norway", N + [("1940-04-09", "allied")])
DNK = U("DNK", "Denmark", N + [("1940-04-09", "allied")])
YUG = U("YUG", "Yugoslavia", N + [("1941-04-06", "allied")])
GRC = U("GRC", "Greece", N + [("1940-10-28", "allied")])
ISL = U("ISL", "Iceland", N + [("1940-05-10", "allied_c")])
FRO = U("FRO", "Faroe Islands", N + [("1940-04-12", "allied_c")])
GRL = U("GRL", "Greenland", N)
FFR = U("FFR", "Free France", [("1940-06-18", "allied")], "force")
PAR = U("PAR", "Yugoslav Partisans", [("1941-07-07", "partisan")], "force")
USA = U("USA", "United States", [("1941-12-08", "allied")], "force")

# ---- Soviet sphere --------------------------------------------------------
SOV = U("SOV", "Soviet Union", [("1939-09-01", "soviet")])

# ---- Neutrals -------------------------------------------------------------
LTU = U("LTU", "Lithuania", N)
LVA = U("LVA", "Latvia", N)
EST = U("EST", "Estonia", N)
DAN = U("DAN", "Free City of Danzig", [("1939-09-01", "axis")], "free city")
SWE = U("SWE", "Sweden", N)
CHE = U("CHE", "Switzerland", N)
LIE = U("LIE", "Liechtenstein", N)
ESP = U("ESP", "Spain", N)
PRT = U("PRT", "Portugal", N)
AND = U("AND", "Andorra", N)
IRL = U("IRL", "Ireland", N)
TUR = U("TUR", "Turkey", N)  # declared war 23 Feb 1945 (nominal); kept neutral as in the reference
IRN = U("IRN", "Iran", N + [("1943-09-09", "allied_c")])
SAU = U("SAU", "Saudi Arabia", N)
SMA = U("SMA", "Spanish Morocco", N, "protectorate")
SSA = U("SSA", "Spanish Sahara and Ifni", N, "colony")
TNG = U("TNG", "Tangier International Zone", N, "zone")
MCO = U("MCO", "Monaco", N)
SMR = U("SMR", "San Marino", N)
VAT = U("VAT", "Vatican City", N)
OMN = U("OMN", "Oman", N)
SOVC = U("SOVC", "Soviet Central Asia", [("1939-09-01", "soviet")])
AUT = U("AUT", "Austria", [("1945-04-27", "allied_c")], "occupied")
CSR = U("CSR", "Czechoslovakia", [("1945-04-04", "allied")])

assert len(UNITS) < 255


def faction_on(code_or_id, date):
    u = UNITS[code_or_id - 1] if isinstance(code_or_id, int) else BY_CODE[code_or_id]
    f = None
    for d, fac in u["factions"]:
        if d <= date:
            f = fac
    return f
