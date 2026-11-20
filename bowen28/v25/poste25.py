"""Poste de pilotage v25 (remarque d'Andre du 20 novembre 2026, d'apres les photos du bateau) :

  - caisson des fauteuils : 25 mm d'avant en arriere (37,9 mm en v24) et 23 mm entre la face arriere de la
    console et le caisson (9,5 mm en v24). Sa face arriere (et le filet) recule de 0,6 mm, sa face avant de 13,5 mm ;
  - fauteuils recules de 2,1 mm : leur embase alu (13,7 mm de long) reste entierement sur le caisson.

A importer AVANT de construire quoi que ce soit avec model.py (coques, fauteuils, embases, filet du caisson) :
on change les cotes de model.py pour toute la chaine. Les cotes v24 restent dans V24_PLAT_X et V24_SEAT_X
(la coque d'origine, v24/coques_soudees.pkl, a encore le caisson v24 : s2_coques.py le refait).
"""
import model as M

V24_PLAT_X, V24_SEAT_X = M.PLAT_X, M.SEAT_X
CAISSON_MM = 25.0            # profondeur du caisson (avant -> arriere), mm de maquette
ECART_MM = 23.0              # de la face arriere de la console au caisson, mm de maquette
EMBASE_DEMI = 0.1306         # demi-longueur de l'embase alu d'un fauteuil (m reels, mesuree sur la v24)
MARGE_MM = 0.5               # l'embase s'arrete a 0,5 mm du bord avant du caisson

if not getattr(M, '_POSTE25', False):
    _av = M.CON_AFT_X - ECART_MM / M.MM
    M.PLAT_X = (_av - CAISSON_MM / M.MM, _av)
    M.SEAT_X = round(min(V24_SEAT_X, _av - MARGE_MM / M.MM - EMBASE_DEMI), 3)
    M._POSTE25 = True
PLAT_X, SEAT_X = M.PLAT_X, M.SEAT_X
