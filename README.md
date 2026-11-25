# Analyseur Projet Gaia 0.1

Ouvrir coups.md pour la liste calculée du coup 61. Le couple (q, r) identifie une case de la carte BGA. Chaque ligne regroupe les préparations qui conduisent à la même action, sur la même cible, par le même mode. Les différentes actions spéciales de mine sont comptées séparément.

Le fichier analyse.py est la source modifiable en Python 3.10 ou supérieur, sans dépendance. Le fichier coup61.json permet de reproduire les calculs.

    python analyse.py coup61.json > coups.md
    python verifier.py

## Couverture de cette version

Nevlas avec institut construit et visite du Crépuscule. Les conversions sont explorées avant le choix principal. Le calcul privilégie un témoin court et omet les dépenses superflues. Les 2 crédits obtenus contre un jeton représentent deux conversions groupées par le pouvoir Nevlas. Les paiements possibles qui aboutissent à des stocks différents ne sont pas tous listés. Le code n'applique pas encore les réactions adverses, les nouveaux revenus ni les gains en chaîne.

Pour cette position, les structures valent ensemble 6 pour une fédération (1 + 2 + 3), le minimum est 7. Aucun gaiaformeur disponible. Zéro PV pour une nouvelle exploration qui en demande 5. L’action de laboratoire du Crépuscule est occupée et son action de réactivation demande une tuile Alliance déjà acquise. Le booster 5, les plateaux et les technologies personnelles n’ajoutent aucune autre action spéciale active. Le coup de passage prévoit trois boosters disponibles.

L'identification des pièces et des actions suit les modules publics BGA gpj-actions.js, gpj-map.js, gpj-ui.js, gpj-bonusTiles.js et gpj-factions.js de la version 260921-2211. La correspondance avec les choix acceptés par le serveur reste à vérifier. Les gardes de périmètre servent à éviter une extrapolation aux autres factions. Ces gardes ne constituent pas un validateur de toute position future des Nevlas.

## Références

- Jeu de base : https://www.feuerland-spiele.de/fileadmin/game/Gaia_Project/GAIA_PROJECT_EN_rules_Web.pdf
- Extension : https://www.boardgamehelpers.com/GaiaProject/Images/GP_Exp_Rule_EN_V1_Web.pdf
- Adaptation BGA : https://x.boardgamearena.net/data/themereleases/current/games/gaiaproject/260921-2211/modules/gpj-actions.js
