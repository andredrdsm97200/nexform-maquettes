# Bowen 28 au 1:19 – kit d'impression v25.4, montage sans colle

`./construire.sh` reconstruit tout le kit (`./construire.sh --notice` ajoute la notice illustrée).
Résultat : `Bowen28_kit_impression_v25.4.zip` (104 pièces sur 10 plateaux + l'éprouvette P00, environ 830 g de PLA).

**v25.4** (livrée le 26 novembre 2026) : socle d'un seul morceau, noir, avec KANPAÏ 2.O et Nexform 3D Marine
(P10) ; SeaDek en taupe avec les coussins (P09), le plateau teck ne garde que le volant (P08) ; les 6 coussins de
plat-bord suivent la paroi courbe du cockpit au jeu de 0,1 mm et s'impriment debout (`v25/combler25.py`).

**Vision 3D d'abord** : avant de fabriquer le kit d'une nouvelle version, `python3 bowen28/vision3d.py` écrit
`bowen28/sorties/vision3d/` (la page et son modèle, à pleine résolution), publiée comme artefact
« Bowen 28 · KANPAÏ 2.O · vision 3D ». André y demande ses modifications et valide la version ; le kit, la notice
et la place dans la marina Nexform viennent ensuite.

## Comment c'est construit

| Fichier | Rôle |
|---|---|
| `model.py` | La maquette elle-même : coque, pont, console, moteurs, taud, coussins… (cotes en mètres réels, échelle 1:19) |
| `fit.py`, `v25/fit25.py` | Les emboîtements : tenons ronds, tenons losange, logements, **jeu de 0,1 mm** (`C` dans `fit25.py`) ; côtes d'écrasement des petites pièces : `../commun/emboitements.py` |
| `pieces.py`, `cushions.py` | Découpe en pièces imprimables, orientation sur le plateau |
| `v25/s2_coques.py` | Les 2 moitiés de coque : clés de jonction, tenons losange, logements des pièces |
| `v25/s1_pieces.py` | Toutes les autres pièces (moteurs, volant, filets noirs, cadres…) |
| `v25/roof25.py` | Le toit rigide du taud, arceaux intégrés, imprimé à l'envers sans support |
| `v25/poste25.py` | v25 : le caisson des fauteuils (25 mm, à 23 mm de la console) ; change les cotes de `model.py` pour toute la chaîne |
| `v25/echelle25.py` | v25 : l'échelle de bain repliée, tournée de 90°, et la tôle larmée refaite dessous |
| `v25/pare_battages25.py` | v25 : les 4 pare-battages (œil pour la ficelle), leurs 4 anneaux encastrés dans les parois du cockpit et (v25.2) leurs 4 crochets alu |
| `v25/moteur25.py` | v25.3 : la partie grise de chaque moteur en 3 pièces imprimées à plat (bloc, embase, hélice) et la cheville du capot |
| `v25/socle25.py` | v25.4 : le socle d'un seul morceau (les 2 berceaux reliés par une poutre), noir, le nom du bateau en Exo 2 Black italique et le logo Nexform en relief de 0,8 mm sur les 2 flancs ; seul sur le plateau P10 |
| `vision3d.py`, `vision3d.html` | La vision 3D à faire valider par André (page, modèle, carnet de demandes) |
| `v25/s4_coussins.py` | Les 20 coussins, recalés sur les coques |
| `v25/combler25.py` | v25.4 : les coussins de plat-bord avancés jusqu'à 0,1 mm de la paroi courbe (sans toucher la coque déjà imprimée), sans gêner leur pose, et posés debout pour l'impression |
| `v25/s3_assemblage.py` | La maquette assemblée, avec contrôle de tous les chevauchements |
| `v25/s3b_chemins.py` | Les chemins de pose ([ligne de conduite](../LIGNE_DE_CONDUITE.md), règle 1) : chaque pièce se pose sans obstacle, dans l'ordre de la notice |
| `v25/s3c_maintien.py` | Le maintien (règle 2) : les petites pièces accrochées à la console tiennent par leurs côtes d'écrasement |
| `v25/s5_eprouvette.py` | L'éprouvette de réglage P00 |
| `v25/s6_kit.py` … `s9_lisezmoi.py` | STL par couleur, plateaux 3MF, aperçus, fiche d'impression, LISEZMOI |
| `nf25_*.py` | La notice de montage (12 étapes, images et PDF) |
| `v25/s10_controle.py` | Le contrôle final du kit |

Données d'origine (ne pas modifier à la main) : `v23/v23b.pkl` (maquette assemblée v23), `v24/coques_soudees.pkl`
(coques v23 réparées), `v24/coque_coussins.pkl` (orientation d'impression des coussins), `donnees/eclate.json`
(vue éclatée de la notice), `fonts/` (polices DM Sans, DM Mono, Exo 2, Bricolage, licence libre OFL), `v24/nxlogo.svg`.

## Couleurs

Blanc (coques, capots, clés) · Gris alu (cadres, moteurs, échelle) · Noir (toit, filets, écrans, pare-battages, socle) ·
Teck (volant) · Taupe (coussins, fauteuils, SeaDek). Bobines prévues : Bambu Lab ; équivalents chez
Caraïbes 3D Productions : PLA Basic Blanc, PLA+ Gris, PLA Basic Noir, PLA+ Beige, PLA+ Brun (Landu3D).
