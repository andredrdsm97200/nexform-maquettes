# Boston Whaler 17 Montauk au 1:12

Le modèle du BAT v2 (coque classique 1976-2002, moteur Suzuki DF90A sans marquage), tel qu'il est affiché
dans la vitrine Nexform.

- `model.py` : la maquette (cotes en mètres réels : constructeur + relevés sur les photos du client).
- `build.py` : implantation (banquettes, console, trappes…) et export.
- `export.py` : format de la vitrine Nexform.

`python3 build.py` écrit `sorties/whaler.json`, identique au modèle publié dans la vitrine.

Pas encore de kit d'impression : pour en faire un, reprendre la méthode du Bowen 28 (pièces, emboîtements
sans colle, plateaux, fiche, notice). Les photos du client ne sont pas dans ce dépôt.
