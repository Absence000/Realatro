from subscripts.spacesavers import *
from subscripts.inputHandling import alreadyHasConsumable
from subscripts.spectralCards import Spectral

import random


class Planet:
    def __init__(self, name, negative=None):
        self.name = name
        self.negative = negative
        self.coords = None

    def toString(self, mode, save=None):
        isNegative = ""
        if self.negative:
            isNegative = "Negative "
        if mode == "description":
            handType = openjson('consumables/planetDict')[self.name]['hand']
            handInfo = save.handLevels[handType]
            return f"(lvl.{handInfo['level']}) Level up {handType}\n+{handInfo['chips']} Chips\n+{handInfo['mult']} mult"
        else:
            return f"{isNegative}{self.name}"

    def toDict(self):
        return{
            "name": self.name,
            "negative": self.negative,
            "type": "Planet"
        }

    def toBinary(self):
        nameIndex = list(openjson('consumables/planetDict').keys()).index(self.name)
        negativeBit = "0"
        if self.negative:
            negativeBit = "1"
        binaryEncoder = "100" + str(format(nameIndex, '04b')) + negativeBit + "000000000"
        return int(binaryEncoder, 2)


def usePlanetCard(card, save):
    planetCardInfo = openjson("consumables/planetDict")[card.name]
    upgradeHandLevel(planetCardInfo["hand"], 1, planetCardInfo["addition"][1], planetCardInfo["addition"][0], save)


# TODO: make this work with downgrading as well
def upgradeHandLevel(hand, level, chipUpgrade, multUpgrade, save):
    for i in range(level):
        save.handLevels[hand]["level"] += 1
        save.handLevels[hand]["chips"] += chipUpgrade
        save.handLevels[hand]["mult"] += multUpgrade

defaultplanetCards = [Planet("Pluto"),
                      Planet("Mercury"),
                      Planet("Uranus"),
                      Planet("Venus"),
                      Planet("Saturn"),
                      Planet("Jupiter"),
                      Planet("Earth"),
                      Planet("Mars"),
                      Planet("Neptune")]

secretPlanetCardDict = {"Five Of A Kind": Planet("Planet X"),
                        "Flush House": Planet("Ceres"),
                        "Flush Five": Planet("Eris"),}


def generateShuffledListOfUnlockedPlanetCards(save, amount, generateSpecialSpectrals):
    unlockedPlanetCards = defaultplanetCards
    for illegalHand in save.illegalHandsDiscovered:
        unlockedPlanetCards.append(secretPlanetCardDict[illegalHand])
    blackHole = Spectral("Black Hole")

    viablePlanetCards = []
    if save.hasJoker("Showman"):
        for i in range(amount):
            if generateSpecialSpectrals and random.randint(1, 1000) <= 3:
                viablePlanetCards.append(blackHole)
            else:
                viablePlanetCards.append(random.choice(unlockedPlanetCards))
    else:
        # no duplicates!
        random.shuffle(viablePlanetCards)
        for planet in viablePlanetCards:
            if generateSpecialSpectrals and random.randint(1, 1000) <= 3:
                newPlanet = blackHole
            else:
                newPlanet = planet
            if not alreadyHasConsumable(save, newPlanet):
                viablePlanetCards.append(newPlanet)
                if len(viablePlanetCards) == amount:
                    break
    return viablePlanetCards