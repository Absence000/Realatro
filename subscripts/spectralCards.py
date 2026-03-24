from subscripts.inputHandling import prepareCardForPrinting, alreadyHasConsumable
from subscripts.jokers import generateShuffledListOfFinishedJokersByRarity
from subscripts.spacesavers import *
import random


# lots of unnecessary modifiers in spectralDict.json but if they add more spectrals later I want
# to differentiate them
class Spectral:
    def __init__(self, name, negative=None):
        self.name = name
        self.negative = negative
        self.coords = None

    def toString(self, mode=None):
        isNegative = ""
        if self.negative:
            isNegative = "Negative "
        if mode is None:
            return f"{isNegative}{self.name}: {openjson('consumables/spectralDict')[self.name]['description']}"
        elif mode == "name":
            return f"{isNegative}{self.name}"
        elif mode == "description":
            return openjson('consumables/spectralDict')[self.name]['description']

    def toDict(self):
        return{
            "name": self.name,
            "negative": self.negative,
            "type": "Spectral"
        }

    def toBinary(self):
        nameIndex = list(openjson('consumables/spectralDict').keys()).index(self.name)
        negativeBit = "0"
        if self.negative:
            negativeBit = "1"
        binaryEncoder = "101" + str(format(nameIndex, '05b')) + negativeBit + "00000000"
        return int(binaryEncoder, 2)

def useSpectralCard(card, otherCards, save, inConsumables = False):
    # unlike cards or jokers I can get away with using spectral card dictionaries since all this stuff is immutable for
    # all of them
    spectralInfo = openjson("consumables/spectralDict")[card.name]
    spectralType = spectralInfo["type"]

    if spectralType == "handModifier":
        maxCardSelectAmount = spectralInfo["amnt"]

        if otherCards is None or otherCards == []:
            return False, "No cards to use!"

        if len(otherCards) > maxCardSelectAmount:
            return False, "Too many cards!"

        # seal givers (talisman, deja vu, hex, trance)
        subModifier = spectralInfo["modifier"]
        if subModifier == "seal":
            for card in otherCards:
                newCard = card.copy()
                newCard.seal = spectralInfo["sealType"]
                save.replaceCardInDeck(card, newCard)
            return True, "Success!"

        # random edition giver (aura)
        elif subModifier == "edition":
            for card in otherCards:
                # edition: "random" is unused
                newCard = card.copy()
                newCard.edition = random.choice(["foil", "holographic", "polychrome"])
                save.replaceCardInDeck(card, newCard)
            return True, "Success!"

        # duper (cryptid)
        elif subModifier == "copy":
            for i in range(spectralInfo["copyAmount"]):
                newCard = otherCards[0].copy()
                newCard.id = None
                save.deck.append(newCard)
                prepareCardForPrinting(newCard, keep=True)
            return True, "Success!"


    # random destroyers and card adders (familiar, grim, incantation, immolate)
    elif spectralType == "destroyRandom":
        indexList = list(range(len(save.hand)))
        random.shuffle(indexList)
        indexesToDestroy = indexList[0:(spectralInfo["destroyAmount"])]
        index = 0
        for card in save.hand:
            if index in indexesToDestroy:
                save.replaceCardInDeck(card, None)
            index += 1

        spectralCardTypeDict = {
            "face": ["J", "Q", "K"],
            "numbered": ["2", "3", "4", "5", "6", "7", "8", "9", "10"],
            "ace": ["A"]
        }
        if spectralInfo["secondaryEffect"] == "addRandomEnhancedCards":
            for i in range(spectralInfo["addAmount"]):
                number = random.choice(spectralCardTypeDict[spectralInfo["enhancementSubset"]])
                suit = random.choice(["S", "C", "D", "H"])
                enhancement = random.choice(["bonus", "mult", "wild", "glass", "steel", "gold", "lucky"])

                # TODO: this is stupid fix this later
                blankCard = card.copy()
                blankCard.seal = None
                blankCard.edition = None
                blankCard.number = number
                blankCard.suit = suit
                blankCard.enhancement = enhancement
                blankCard.id = None

                save.deck.append(blankCard)
                prepareCardForPrinting(blankCard, True)

        # immolate
        elif spectralInfo["secondaryEffect"] == "addMoney":
            save.money += spectralInfo["moneyAmount"]
        return True, "Success!"

    # joker creators (wraith, soul)
    elif spectralType == "jokerCreator":
        jokerToCreate = generateShuffledListOfFinishedJokersByRarity(spectralInfo["rarity"], save)[0]
        if len(save.jokersInPlay) < save.jokerLimit or jokerToCreate.edition == "negative":
            save.jokersInPlay.append(jokerToCreate)
            prepareCardForPrinting(jokerToCreate)
            if "secondaryEffect" in spectralInfo and spectralInfo["secondaryEffect"] == "setMoneyToZero":
                save.money = 0
            return True, "Success!"
        return True, "Did nothing!"

    # hand converters (ouija, sigil)
    elif spectralType == "handConverter":
        if spectralInfo["convertAttribute"] == "randomSuit":
            randomSuit = random.choice(["S", "C", "D", "H"])
            for card in save.hand:
                if card.suit != randomSuit:
                    newCard = card.copy()
                    newCard.id = None
                    newCard.suit = randomSuit
                    save.replaceCardInDeck(card, newCard)
                    prepareCardForPrinting(newCard, keep=True)
        else:
            randomRank = random.choice(["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"])
            for card in save.hand:
                if card.number != randomRank:
                    newCard = card.copy()
                    newCard.id = None
                    newCard.number = randomRank
                    save.replaceCardInDeck(card, newCard)
                    prepareCardForPrinting(newCard, keep=True)
            save.handLimit -= 1

    # joker editors (ecto, ankh, hex)
    elif spectralType == "joker":
        if len(save.jokersInPlay) == 0:
            return False, "No jokers!"
        # random.shuffle will mess with the joker order, I need to modify a specific joker in place
        # ik there's a better way to do this but I forget how
        # TODO: fix this later
        jokerModifyIndex = random.randint(0, len(save.jokersInPlay) - 1)
        if spectralInfo["effect"] == "negative":
            save.jokersInPlay[jokerModifyIndex].edition = spectralInfo["effect"]
            handsToSubtract = 1 + save.ectoUses
            save.startingHands -= handsToSubtract
            save.ectoUses += 1
            return True, "Success!"
        elif spectralInfo["effect"] == "polychrome":
            save.jokersInPlay[jokerModifyIndex].edition = spectralInfo["effect"]

        if spectralInfo["secondaryEffect"] == "destroyOthers":
            # TODO: make this work with eternals when they're added
            # also this is dumb fix it
            for i in range(len(save.jokersInPlay)):
                if i != jokerModifyIndex:
                    save.jokers.remove(save.jokersInPlay[i])

        if spectralInfo["effect"] == "copy":
            jokerToDupe = save.jokersInPlay[jokerModifyIndex].copy()
            jokerToDupe.id = None

            if jokerToDupe.edition == "negative":
                jokerToDupe.edition = None

            if len(save.jokersInPlay) < save.jokerLimit:
                save.jokersInPlay.append(jokerToDupe)
                prepareCardForPrinting(jokerToDupe)
        return True, "Success!"

    # black hole
    elif spectralType == "upgradeAllHands":
        for planet, planetCardInfo in openjson("consumables/planetDict").items():
            hand = planetCardInfo["hand"]
            chipUpgrade = planetCardInfo["addition"][1]
            multUpgrade = planetCardInfo["addition"][0]
            save.handLevels[hand]["level"] += 1
            save.handLevels[hand]["chips"] += chipUpgrade
            save.handLevels[hand]["mult"] += multUpgrade
        return True, "Success!"

def generateShuffledListOfFinishedSpectralCards(save, amount, generateSpecialSpectrals):
    allSpectrals = list(openjson("consumables/spectralDict").keys())
    specialSpectrals = allSpectrals[-2:]
    finishedSpectrals = allSpectrals[:-2]

    viableSpectralCards = []

    if save.hasJoker("Showman"):
        for i in range(amount):
            if generateSpecialSpectrals and random.randint(1, 1000) <= 3:
                viableSpectralCards.append(Spectral(random.choice(specialSpectrals)))
            else:
                viableSpectralCards.append(Spectral(random.choice(allSpectrals)))
    else:
        # no duplicates!
        random.shuffle(finishedSpectrals)
        for spectral in finishedSpectrals:
            if generateSpecialSpectrals and random.randint(1, 1000) <= 3:
                spectralObj = Spectral(random.choice(specialSpectrals))
            else:
                spectralObj = Spectral(spectral)
            if not alreadyHasConsumable(save, spectralObj):
                viableSpectralCards.append(spectralObj)
                if len(viableSpectralCards) == amount:
                    break

    return viableSpectralCards