# IDEFIX
**Team shell1**

## Architecture
Le fichier `aseba.py` contient la classe permettant de faire la liaison entre le code python et le robot.

Le fichier `main.py` contient la classe et le main représentant tout le code, c’est le fichier à exécuter.

Le fichier `Stitch-Sync_0.png` et `Stitch-Sync_0.playground` représentent le circuit par défaut (celui donné sur Discord)

Le fichier `Stitch-Sync_custom.png` et `Stitch-Sync_ custom.playground` représentent le circuit qu’on a fait nous-même, un circuit ultra challengeant.


Pour lancer le code, il faut :
- Lancer le simulateur, avec un playground Stitch-Sync
- Ouvrir un terminal et exécuter la commande : `asebamedulla "tcp:localhost;33333" -p 8080`
- Ouvrir un autre terminal dans le dossier ‘src’ et exécuter la commande : `python3 main.py`
- Placer le robot avec une orientation plus ou moins bonne (trop à droite si possible) sur une
zone sans code et sans intersection.
