# Sunfish 25 cm (1:16,8)

Coque de 13'9" × 4'1" (4,19 × 1,24 m) ramenée à 250 mm ; environ 33 cm de haut sur son support.

## Ce qu'il y a ici

- `pieces_v3/` : les 19 pièces imprimées de la version 3 (voile à bandes), en STL étanches, **en position
  de maquette assemblée** (millimètres). Elles viennent de la visionneuse publiée
  (https://claude.ai/artifact/4cgnJsJqzX3YuC6bwLXywY), au dixième de micron près.
- `pieces_v3.json` : pour chaque pièce, son nom, sa couleur, son orientation d'impression, sa taille sur le
  plateau, son éclaté, et les 2 coloris de voile (bleu et blanc, jaune bleu et blanc).

Le kit d'impression prêt à l'emploi (`Sunfish_25cm_v3.zip`, pièces déjà orientées, notice) a été envoyé dans la
discussion « Sunfish boat 3D model » du 11 octobre 2026.

## Le programme d'origine

Il a été écrit pas à pas dans cette discussion (https://claude.ai/chat/399a5243-3e7b-4d15-a84b-21bba2482aa0) :
`geom.py` (formes de coque, relevées sur les captures du configurateur SERO), `parts_rig.py` (gréement, dérive,
safran), `build.py` (assemblage, orientation d'impression), `preview.py`, `render.py`, `export_viewer.py`,
plus de nombreuses retouches successives. Pour le reconstituer, une discussion dédiée relit ces 8 échanges et
rejoue chaque fichier ; les captures du configurateur peuvent être remplacées par la forme relevée sur
`pieces_v3/coque.stl`.

À noter : cette version 3 utilise encore de la colle et des goupilles en filament. Pour la passer en montage
sans colle, reprendre les règles du Bowen 28.
