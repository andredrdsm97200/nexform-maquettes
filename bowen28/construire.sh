#!/bin/bash
# Reconstruit le kit d'impression complet du Bowen 28 au 1:19 (v25, montage sans colle) a partir du programme.
#   ./construire.sh            le kit (STL, plateaux 3MF, fiche, LISEZMOI, apercus) : quelques minutes
#   ./construire.sh --notice   idem + la notice de montage illustree : compter 30 a 40 min de plus
# Resultat : bowen28/Bowen28_kit_impression_v25.zip
set -e
cd "$(dirname "$0")"
python3 v25/s2_coques.py          # coques : cles de jonction, tenons losange, logements
python3 v25/s1_pieces.py          # toutes les autres pieces, orientees pour l'impression
python3 v25/s5_eprouvette.py      # eprouvette de reglage P00
python3 v25/s4_coussins.py        # coussins recales sur les coques
python3 v25/s3_assemblage.py      # maquette assemblee + controle des chevauchements
python3 v25/s3b_chemins.py        # chaque piece se pose sans obstacle, dans l'ordre de la notice (LIGNE_DE_CONDUITE.md, regle 1)
python3 v25/s3c_maintien.py       # les petites pieces accrochees tiennent par serrage : cotes d'ecrasement (regle 2)
python3 v25/s6_kit.py             # STL par couleur, plateaux 3MF
python3 v25/s7_apercus.py         # apercus des plateaux
python3 v25/s8a_eprouvette_png.py
python3 v25/s8_fiche.py           # fiche d'impression (PDF)
python3 v25/s9_lisezmoi.py        # LISEZMOI
if [ "$1" == "--notice" ]; then
  python3 nf25_render.py          # images de la notice
  python3 nf25_pdf.py             # notice de montage (PDF)
fi
if [ -f nf25/notice_de_montage_bowen28_v25.pdf ]; then
  cp nf25/notice_de_montage_bowen28_v25.pdf v25/kit/Bowen28_kit_impression_v25/notice_de_montage_v25.pdf
fi
python3 v25/s10_controle.py       # controle final
(cd v25/kit && rm -f ../../Bowen28_kit_impression_v25.zip && zip -qr ../../Bowen28_kit_impression_v25.zip Bowen28_kit_impression_v25)
echo "Kit pret : bowen28/Bowen28_kit_impression_v25.zip"
