"""Political changes of 1945 within the map's time span.

Restorations follow liberation, not the later peace treaties: Poland's
pre-war western territory returns to Polish administration as the Red
Army passes (the General Government and the annexed Wartheland/Danzig-
West Prussia; dated to the end of the Vistula-Oder operation), Romania's
administration returns to northern Transylvania on 9 March 1945, Austria
is re-established by the Renner government on 27 April and Czechoslovakia
(including the Sudetenland and the areas ceded to Hungary in 1938) on 9 May.
The Oder-Neisse territories passed to Polish administration in the summer
of 1945 and are not changed here; Carpathian Ruthenia is handled in e1944.
"""
import numpy as np
from core import world
from units import BY_CODE



def build(tl):
    W = world()
    POL = BY_CODE["POL"]["id"]
    DAN = BY_CODE["DAN"]["id"]
    prewar_pol = lambda: tl.base_country == POL  # noqa: E731
    tl.political("1945-02-03", lambda: prewar_pol() & ~W.poly([(54.9, 17.0), (54.9, 19.8), (53.6, 19.8), (53.6, 17.0)]),
                 "POL", where=["GG", "GER"], dur=3.0, label="Polish administration restored")
    tl.political("1945-03-31", lambda: prewar_pol() | (tl.base_country == DAN), "POL", where=["GER", "DAN"], dur=2.0)
    tl.political("1945-03-09", lambda: W.unit("ROU"), "ROU", where=["HUN"], dur=2.0,
                 label="Romanian administration returns to northern Transylvania")
    tl.political("1945-04-27", lambda: W.unit("AUT"), "AUT", where=["GER"], dur=1.5, label="Austria re-established")
    tl.political("1945-05-09", lambda: W.unit("CZE") | W.unit("SVK"), "CSR", where=["PRO", "SVK", "GER", "HUN", "POL"],
                 dur=1.5, label="Czechoslovakia restored")
    dd = tl.layer("dodecanese-1945", "GBR", within=["DOD"], order=51)
    dd.key("1945-05-09 12", mask=lambda: np.ones_like(W.land), span=0.6)
