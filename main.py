from aseba import Aseba
from gi.repository import GObject as gobject

import random

# Class principale de notre robot
class Thymio():
    def __init__(self, aseba):
        self.aseba = aseba
        self.node = "thymio-II"
        
        # Capteurs horizontaux
        self.proxHorizontal = [0, 0, 0, 0, 0, 0, 0]
        # Capteurs aux sol
        self.proxGroundReflected = [0, 0]
        
        # Etat courant
        self.state = 'WAIT_CODE_START'
        # Nombre de pixel avant le changement d'état
        self.count = 1000000000
        # Code couleur lu
        self.code = []
        
        # Quel capteur suis la ligne (0 gauche, 1 droite)
        self.idSensorTrack = 1
        # Vitesse de croisière
        self.speedMax = 50
        # Vitesse actuelle théorique
        self.speed = self.speedMax
        # Vitesse actuelle pratique
        self.realSpeed = 0
        # Vitesse de rotation dans un cas manuel
        self.speedRideLeft = 0
        self.speedRideRight = 0
        
        # 10 dernière valeur du capteur code
        self.sensorList = [1000]*10
        
        # Seul coeficient expérimentale
        self.coef = 2197
        
        # Utiliser pour étalonner le coef
        self.etalon = None
        self.etalonCount = 0

    # Méthode principale
    def main(self):
        # On actualise les valeurs des capteurs
        self.updateSensors()
        
        # On calcule la moyenne sur les 10 dernières valeurs
        colorValue = sum(self.sensorList)/len(self.sensorList)
        # Print de débug MAXI utile pour suivre l'état du robot
        print(self.state, '  |  ', self.count, '  |  ', colorValue)
        
        # Si on cherche à lire un code
        if self.state.startswith('WAIT_CODE'):
            # On suit la ligne
            self.followTrack()
            # Si on est en phase d'étalonnage on stock la valeur du capteur
            # et le nombre de pixel parcouru depuis le debut du code
            if self.etalon is not None:
                self.etalonCount += 84*self.realSpeed/self.coef
                self.etalon.append([self.etalonCount, colorValue])
                
        # On vérifie qu'il n'y a pas d'obstacle devant
        obstacle = self.testObstacle()
        
        # Si on fait doit juste rouler on prolonge le mouvement
        if not obstacle and (self.state == 'RIDE' or self.state.startswith('TURN_') or self.state.startswith('STOP_')):
            self.manualTurn(self.speedRideLeft, self.speedRideRight)
        
        # On update le nombre de pixels parcourus
        self.count -= 84*self.realSpeed/self.coef
        
        
        # Si on a fini l'étalonnage on affiche le coef recalculé
        if self.etalon is not None and max(self.etalon, key=lambda x: x[1])[1] > 910:
            bestIndex = min(self.etalon, key=lambda x: x[1])[0]
            print('##### BEST COEF FOUND IS :', (1-((32-bestIndex)/32))*self.coef)
            self.etalon = None
        
        # Si on cherche un début de code est qu'on en trouve un,
        # on change d'état pour la detection de la première case
        if self.state == 'WAIT_CODE_START':           
            if colorValue <= 800:
                self.state = 'WAIT_CODE_1'
                self.count = 32
                self.speed = 10
                self.etalonCount = 0
                self.etalon = []
        
        # Quand on arrive sur la première case du code, on note la couleur,
        # on change d'état pour la detection de la deuxième case
        if self.state == 'WAIT_CODE_1' and self.count <= 0:
            self.state = 'WAIT_CODE_2'
            self.count = 32
            color = self.valueToColor(colorValue)
            self.code.append(color)
            
            # Si c'est une ligne droite, on arrête de lire le code et on attend le prochain
            if color == 'BLANC':
                self.state = 'WAIT_CODE_START'
                self.count = 1000000000
                self.speed = self.speedMax
                self.code = []
            
        # Quand on arrive sur la deuxième case du code, on note la couleur,
        # on change d'état pour la detection de la troisième case
        if self.state == 'WAIT_CODE_2' and self.count <= 0:
            self.state = 'WAIT_CODE_3'
            self.count = 32
            color = self.valueToColor(colorValue)
            self.code.append(color)
            
        # Quand on arrive sur la troisième case du code, on note la couleur,
        # on change d'état pour la detection de la quatrième case
        if self.state == 'WAIT_CODE_3' and self.count <= 0:
            self.state = 'WAIT_CODE_4'
            self.count = 32
            color = self.valueToColor(colorValue)
            self.code.append(color)
        
        # Quand on arrive sur la quatrième case du code, on note la couleur,
        # on change d'état pour la detection du prochain code
        if self.state == 'WAIT_CODE_4' and self.count <= 0:
            self.state = 'WAIT_CODE_START'
            self.count = 1000000000
            color = self.valueToColor(colorValue)
            self.code.append(color)
            self.speed = self.speedMax
            
            # On traite les codes qui doivent l'être en leurs attribuant le bon état
            
            # START TRI CODE 
            cond1 = self.code == ['BLEU', 'BLANC', 'NOIR', 'BLEU']
            cond2 = self.code == ['BLEU', 'ROUGE', 'BLANC', 'ROUGE']
            if cond1 or cond2:
                self.state = 'TURN_LEFT/STRAIGHT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
                
            cond1 = self.code == ['BLEU', 'BLANC', 'NOIR', 'BLANC']
            cond2 = self.code == ['BLEU', 'BLEU', 'BLANC', 'ROUGE']
            if cond1 or cond2:
                self.state = 'TURN_RIGHT/STRAIGHT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
            
            cond1 = self.code == ['BLEU', 'ROUGE', 'BLANC', 'BLANC']
            cond2 = self.code == ['BLEU', 'BLEU', 'BLANC', 'BLEU']
            if cond1 or cond2:
                self.state = 'TURN_RIGHT/LEFT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
            
            if self.code == ['BLEU', 'BLANC', 'ROUGE', 'NOIR']:
                self.state = 'STOP_TURN_LEFT/STRAIGHT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
                
            if self.code == ['BLEU', 'BLANC', 'BLEU', 'NOIR']:
                self.state = 'STOP_TURN_RIGHT/STRAIGHT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
                
            if self.code == ['BLEU', 'NOIR', 'BLANC', 'NOIR']:
                self.state = 'STOP_TURN_RIGHT/LEFT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
            # END TRI CODE 
            
            # START QUAD CODE
            cond1 = self.code == ['NOIR', 'BLEU', 'BLANC', 'BLANC']
            cond2 = self.code == ['NOIR', 'ROUGE', 'BLANC', 'BLANC']
            cond3 = self.code == ['NOIR', 'BLANC', 'NOIR', 'BLANC']
            if cond1 or cond2 or cond3:
                self.state = 'TURN_RIGHT/LEFT/STRAIGHT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
                
            cond1 = self.code == ['NOIR', 'BLANC', 'ROUGE', 'BLANC']
            cond2 = self.code == ['NOIR', 'BLANC', 'BLEU', 'BLANC']
            cond3 = self.code == ['NOIR', 'NOIR', 'BLANC', 'BLANC']
            cond4 = self.code == ['NOIR', 'BLANC', 'BLANC', 'BLANC']
            if cond1 or cond2 or cond3 or cond4:
                self.state = 'STOP_TURN_RIGHT/LEFT/STRAIGHT'
                self.count = 140
                self.speed = self.speedMax
                self.speedRideLeft = 1
            self.speedRideRight = 1
            # END QUAD CODE 
            
            if self.code[0] == 'ROUGE':
                self.state = 'WAIT_CODE_START'
                self.count = 1000000000
                self.speed = self.speedMax
                
            
            self.code = []
            
            
            
        if self.state.startswith('STOP_') and self.count <= 0:
            self.state = self.state[5:]
            self.count = 50*84/self.coef
            self.speed = 1
            self.speedRideLeft = 1
            self.speedRideRight = 1
        
        # Si il y a un choix à faire on choisi parmi les états possible
        if self.state.startswith('TURN_') and self.count <= 0:
            self.state = random.choice(self.state[5:].split('/'))
        
            if self.state == 'STRAIGHT':
                # STRAIGHT
                self.state = 'RIDE'
                self.count = 710
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 1
                
            if self.state == 'LEFT':
                # BIG LEFT
                self.state = 'RIDE'
                self.count = 902
                self.speed = self.speedMax
                self.speedRideLeft = 0.74
                self.speedRideRight = 1
                
            if self.state == 'RIGHT':
                # SMALL RIGHT
                self.state = 'RIDE'
                self.count = 588
                self.speed = self.speedMax
                self.speedRideLeft = 1
                self.speedRideRight = 0.6
            
        if self.state == 'RIDE' and self.count <= 0:
            self.state = 'WAIT_CODE_START'
            self.count = 1000000000
            self.speed = self.speedMax

        return True

    # Met à jour les capteurs
    def updateSensors(self):
        self.proxHorizontal = self.aseba.get(self.node, "prox.horizontal")
        self.proxGroundReflected = self.aseba.get(self.node, "prox.ground.reflected")
        
        self.sensorList.append(self.proxGroundReflected[1-self.idSensorTrack])
        self.sensorList.pop(0)
    
    # Suis la ligne
    def followTrack(self):
        # Bornes min
        lowest = [150, 150]
        # Bornes max
        highest = [700, 700]
        # Moyenne
        avg = [lowest[0]+(highest[0]-lowest[0])/2, lowest[1]+(highest[1]-lowest[1])/2]
        # Distance max
        dist = [highest[0]-lowest[0], highest[1]-lowest[1]]
        
        # Valeur du capteur
        value = self.proxGroundReflected[self.idSensorTrack]
        value = max(value, lowest[self.idSensorTrack])
        value = min(value, highest[self.idSensorTrack])
        # Décalage par rapport au centre
        delta = (avg[self.idSensorTrack]-value)/(dist[self.idSensorTrack]/2)
        
        # Vitesse avant correction
        speedLeft = self.speed
        speedRight = self.speed
        
        # Correction des vitesses roues droites et gauches
        if delta > 0.5:
            speedLeft -= 2*(delta-0.5)*self.speed
            speedRight -= 2*delta*self.speed
        elif delta >= 0 and delta < 0.5:
            speedRight -= ((2*delta)**3)*self.speed
        elif delta <= 0 and delta > -0.5:
            speedLeft += ((2*delta)**3)*self.speed
        elif delta < -0.5:
            speedLeft += 2*delta*self.speed
            speedRight += 2*(delta+0.5)*self.speed
            
        # Calcul de la vitesse pratique
        self.realSpeed = (speedLeft+speedRight)/2
        
        # Mis à jour de la vitesse des moteurs
        if self.idSensorTrack == 1:
            self.aseba.set(self.node, "motor.left.target", [speedLeft])
            self.aseba.set(self.node, "motor.right.target", [speedRight])
        else: 
            self.aseba.set(self.node, "motor.left.target", [speedRight])
            self.aseba.set(self.node, "motor.right.target", [speedLeft])

    # Seuils de conversion valeur / couleur
    def valueToColor(self, value):
        if value > 910:
            return 'BLANC'
        elif value <= 910 and value > 800:
            return 'BLEU'
        elif value <= 800 and value > 500:
            return 'ROUGE'
        else:
            return 'NOIR'
    
    # Force les rotations (pour les virages non triviaux en intersection)
    def manualTurn(self, percentage1, percentage2):
        if self.idSensorTrack == 1:
            self.aseba.set(self.node, "motor.left.target", [self.speed*percentage1])
            self.aseba.set(self.node, "motor.right.target", [self.speed*percentage2])
        else: 
            self.aseba.set(self.node, "motor.left.target", [self.speed*percentage2])
            self.aseba.set(self.node, "motor.right.target", [self.speed*percentage1])
            
        self.realSpeed = self.speed*max(percentage1, percentage2)
    
    # Vérifie si il y a un obstacle, si oui coupe les moteurs
    def testObstacle(self):
        if max(self.proxHorizontal[:5]) >= 4000:
            self.manualTurn(0, 0)
            return True
        return False
 
 
if __name__ == '__main__':
    # Création d'un objet permétant de faire le lien entre le robot et le code
    aseba = Aseba()
    # Création d'un objet permétant de traiter les capteurs et d'agir en conséquence
    thymio = Thymio(aseba)
    # Call back à 10Hz (Fréquence de mise à jour du robot)
    gobject.timeout_add(100, thymio.main)
    aseba.run()
