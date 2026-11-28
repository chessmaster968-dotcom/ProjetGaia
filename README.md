# Analyseur Projet Gaia

Ouvrir coups.md pour la liste calculée du coup 61. Le couple (q, r) identifie une case de la carte BGA. Chaque ligne regroupe les préparations qui conduisent à la même action, sur la même cible, par le même mode. Les différentes actions spéciales de mine sont comptées séparément.

Le fichier analyse.py est la source modifiable en Python 3.10 ou supérieur, sans dépendance. Le fichier coup61.json permet de reproduire les calculs.

    python analyse.py coup61.json > coups.md
    python verifier.py

## Couverture de cette version

Le moteur sélectionne la faction avec le champ BGA `raceId`. La commande accepte les exports bruts ; le cas témoin anonymisé reste fourni. Les tests couvrent les dix-huit factions sur des positions construites, et la régression des 78 choix du coup 61. Lancer aussi `python verifier_factions.py`.

| Faction | Calculs spécifiques |
|---|---|
| Terraniens | Conversions de puissance Gaia et retour en bol II lors de leur décision de phase Gaia |
| Lantides | Cohabitation, coût et connaissance de l’institut selon l’extension et le nombre de joueurs |
| Xenos | Placement initial à la demande de BGA, seuil d’alliance de six avec institut, conversion du minerai en jeton III avec extension |
| Gleens | Coût des planètes Gaia, gain de PV, conversion de QIC limitée par l’académie, tuile Alliance de l’institut et action de portée |
| Taklons | Valeur de dépense de la pierre-esprit, charge passive et ordre d’ajout du jeton avec institut |
| Ambas | Échange de l’institut avec une mine |
| Hadsch Hallas | Paiement des conversions en crédits avec institut |
| Ivits | Institut initial, station spatiale comme origine de portée et placement de station |
| Géodens | Gain de connaissances sur un nouveau type après construction de l’institut |
| Bal T’aks | Conversion de gaiaformeur, verrou de navigation avant institut, coût d’exploration et académie |
| Firaks | Rétrogradation du laboratoire, disponibilité du comptoir et progression de recherche |
| Bescods | Action de recherche au plus bas niveau, arbre des améliorations et puissance sur planète natale |
| Nevlas | Conversion d’un jeton III en connaissance, pouvoir de dépense doublé avec institut |
| Itars | Sacrifice vers Gaia et décision de technologie pour quatre jetons Gaia avec institut |
| Tinkéroïdes | Institut initial, plateau de terraformation personnel, choix de période et action de la tuile active |
| Darkaniens | Coût des planètes et prime de premier établissement dans un secteur avec institut |
| Moweyds | Plateau de terraformation personnel, navette initiale lue dans l’export, anneau et valeur de bâtiment |
| Géants de l’espace | Deux étapes sur les planètes standard, action spéciale de construction, technologie lors de la construction de l’institut |

La sortie énumère des choix à un coup, avec un témoin de paiement. L’export fournit déjà les positions initiales, les revenus et les actions utilisées. Les phases d’installation suivent le joueur actif désigné par BGA. Les alliances proposées par le moteur sont limitées aux groupes déjà connectés ; le routage des satellites et l’extension d’une alliance Ivits restent à implémenter. Les transformations de ressources, les interactions avec les vaisseaux, l’Automa, les revenus futurs et les décisions consécutives ne constituent pas un moteur de partie intégral.

Pour cette position, les structures valent ensemble 6 pour une fédération (1 + 2 + 3), le minimum est 7. Aucun gaiaformeur disponible. Zéro PV pour une nouvelle exploration qui en demande 5. L’action de laboratoire du Crépuscule est occupée et son action de réactivation demande une tuile Alliance déjà acquise. Le booster 5, les plateaux et les technologies personnelles n’ajoutent aucune autre action spéciale active. Le coup de passage prévoit trois boosters disponibles.

L'identification des pièces et des actions suit les modules publics BGA gpj-actions.js, gpj-map.js, gpj-ui.js, gpj-bonusTiles.js et gpj-factions.js de la version 260921-2211. La correspondance avec les choix acceptés par le serveur reste à vérifier.

## Références

- Jeu de base : https://www.feuerland-spiele.de/fileadmin/game/Gaia_Project/GAIA_PROJECT_EN_rules_Web.pdf
- Extension : https://www.boardgamehelpers.com/GaiaProject/Images/GP_Exp_Rule_EN_V1_Web.pdf
- Adaptation BGA : https://x.boardgamearena.net/data/themereleases/current/games/gaiaproject/260921-2211/modules/gpj-actions.js

## Objectifs et technologies

La page lit également objectifs.json. Après une modification des règles ou de la position témoin, régénérer les deux sorties et exécuter les tests.

    python analyse.py coup61.json > coups.md
    python objectifs.py coup61.json > objectifs.json
    python verifier.py

Le module objectifs.py lit les 13 objectifs de manche, les 9 objectifs finaux et les technologies avancées du jeu de base et de La Flotte perdue. La projection de classement utilise les compteurs actuels des joueurs humains. Les PV indiqués sur les coups couvrent les bonus de manche et de technologie. Les conditions affichées concernent un joueur déjà autorisé à gagner une technologie. Une action de laboratoire fournit cette occasion dans le générateur de coups. La simulation d'une partie complète, l'Automa et l'énumération des alliances restent hors du périmètre testé.

## Charge de puissance

Le rapport indique les bols après la charge du joueur actif et, pour chaque voisin humain d’une construction, la charge qu’il peut accepter, la quantité offerte et le coût maximal en PV. Un voisin peut toujours décliner. Les offres se calculent à distance deux en prenant son bâtiment de valeur maximale. Les stations spatiales et satellites sont exclus.

Le module `puissance.py` conserve les bols, la zone Gaia et la position de la pierre-esprit. `Bols.charger` renvoie l’état obtenu et la charge effective. `reactions` énumère les choix et leur coût. `appliquer_reaction` renvoie le nouvel état du joueur avec ses PV. `revenus` énumère les résultats distincts des ordres de perception des lots. Les phases de décision utilisent en priorité les lots encore proposés par BGA.

Le générateur applique la charge après la préparation du paiement retenue. Il traite les paliers de recherche, l’action de la technologie standard 9, les Tinkéroïdes, les Lantides, les navettes et les phases de revenus. Les constructions ordinaires, les améliorations, la rétrogradation Firaks et les placements de mine bonus ou de planète perdue utilisent le même calcul de voisinage. Les gains de jetons et les sacrifices sont des opérations distinctes de la charge.

En Python, `analyze(export, projections)` remplit un dictionnaire initialement vide, indexé par famille et libellé du coup. Le champ `bols` contient les issues calculées pour la charge, et `offres` les montants proposés par adversaire. Pour une réaction, appliquer le choix retenu avec `appliquer_reaction`. Les effets en plusieurs décisions sont calculés dans la phase correspondante (par exemple au choix de la case de la planète perdue). Les revenus futurs nécessitent les lots de la nouvelle position.

    python verifier_puissance.py
