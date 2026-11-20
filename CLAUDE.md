# Consignes pour Claude – dépôt nexform-maquettes

Propriétaire : André, Nexform 3D Marine (Martinique). Lui répondre en français, en le vouvoyant.
Les textes de l'Atelier Nexform réservés au propriétaire le tutoient.

## Le principe

Ce dépôt est la source unique du programme des maquettes : **on fabrique ici, on regarde dans Nexform**
(Atelier « Nexform 3D Marine » : https://claude.ai/artifact/FnKuZfor6XjY6fRcNLKVUq). Toujours partir du
programme existant, jamais de zéro. Lire `README.md`, puis le `README.md` du bateau concerné.

## Construire et vérifier

- Python 3.11+ (testé en 3.13). Module manquant : `pip install --break-system-packages -r requirements.txt`.
  Garder trimesh 5.2.1 : le kit sort alors identique au fichier près d'une construction à l'autre.
- Bowen 28 : `./bowen28/construire.sh` (environ 30 s) → `bowen28/Bowen28_kit_impression_v24.zip`.
  `--notice` ajoute la notice illustrée (30 à 40 min : lancer en arrière-plan).
- Whaler 17 : `python3 whaler17/build.py` → `whaler17/sorties/whaler.json` (format de la vitrine Nexform).
- Sunfish : seulement les pièces finales v3 (`sunfish/pieces_v3/`) ; le programme est à reconstituer
  (voir `sunfish/README.md`).
- Avant de livrer, dans la sortie de `construire.sh` : `s3_assemblage.py` doit afficher
  « interferences > 0,02 mm3 : 0 » (aucun chevauchement dans la maquette assemblée) et `s10_controle.py`
  « ERREURS : aucune » (pièces étanches d'un seul tenant, plateaux 256 mm avec 8 mm de marge et 5 mm entre
  pièces, aucune mention de colle). Regarder les aperçus des plateaux et des pièces modifiées avant d'annoncer
  un résultat.
- `bowen28/v25/` est la chaîne de fabrication actuelle ; le kit qu'elle produit s'appelle « v24 » côté client.
  Nouvelle version livrée : remplacer « v24 » dans `construire.sh`, `nf25_*.py` et `v25/*.py`
  (`grep -rn v24 bowen28`), sauf les chemins vers `bowen28/v24/` (données d'origine, à ne pas modifier).

## Les règles de fabrication

- Montage sans colle, PLA ou PLA+, accessible à tous : jeu `C = 0,10 mm` par côté (`v25/fit25.py`).
  Tenon rond si la pièce s'imprime debout, tenon losange (carré à 45°) si elle s'imprime couchée,
  clés en os pour joindre deux pièces de coque, éprouvette P00 à imprimer en premier.
- Bambu Lab A1 : plateau 256 × 256 mm, une couleur par plateau, 5 mm entre pièces, 8 mm au bord, sans supports
  autant que possible.
- Un kit = STL par couleur, plateaux 3MF, fiche d'impression PDF, LISEZMOI, notice de montage, contrôle.

## Enregistrer

- Après chaque modification validée : `git commit` sur `main` avec un message clair en français, puis `git push`.
- Les fichiers recalculés ne sont pas versionnés (`.gitignore`) : livrer le zip et les PDF à André comme fichiers.
- Jamais dans le dépôt : photos de clients, adresses e-mail, numéros de téléphone, logos ou décors de marques.
  Fichiers de données sous 50 Mo.

## Clients

Rien n'est envoyé à un client et la vitrine Nexform n'est mise à jour qu'après validation d'André.
Les clients voient le modèle 3D, jamais les fichiers sources.
