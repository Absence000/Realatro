from subscripts.inputHandling import alreadyHasConsumable
from subscripts.jokers import generateRandomWeightedJokers
from subscripts.planetCards import generateShuffledListOfUnlockedPlanetCards
from subscripts.spacesavers import *
from subscripts.inputHandling import CLDisplayHand, clearPrintFolder, prepareCardForPrinting
from subscripts.spectralCards import Spectral
import random


class Tarot:
    def __init__(self, name, negative=None):
        self.name = name
        self.negative = negative
        self.coords = None

    def toString(self, mode=None):
        isNegative = ""
        if self.negative:
            isNegative = "Negative "
        if mode is None:
            return f"{isNegative}{self.name}: {openjson('consumables/tarotDict')[self.name]['description']}"
        elif mode == "name":
            return f"{isNegative}{self.name}"
        elif mode == "description":
            return openjson('consumables/tarotDict')[self.name]['description']

    def toDict(self):
        return{
            "name": self.name,
            "negative": self.negative,
            "type": "Tarot"
        }

    def toBinary(self):
        nameIndex = list(openjson('consumables/tarotDict').keys()).index(self.name)
        negativeBit = "0"
        if self.negative:
            negativeBit = "1"
        binaryEncoder = "011" + str(format(nameIndex, '05b')) + negativeBit + "00000000"
        return int(binaryEncoder, 2)

def generateShuffledListOfFinishedTarotCards(save, amount, generateSpecialSpectrals):
    finishedTarots = list(openjson("consumables/tarotDict").keys())
    soul = Spectral("Soul")

    viableTarotCards = []

    if save.hasJoker("Showman"):
        for i in range(amount):
            if generateSpecialSpectrals and random.randint(1, 1000) <= 3:
                viableTarotCards.append(soul)
            else:
                viableTarotCards.append(Tarot(random.choice(finishedTarots)))
    else:
        # no duplicates!
        random.shuffle(finishedTarots)
        for tarot in finishedTarots:
            if generateSpecialSpectrals and random.randint(1, 1000) <= 3:
                tarotObj = soul
            else:
                tarotObj = Tarot(tarot)
            if not alreadyHasConsumable(save, tarotObj):
                viableTarotCards.append(tarotObj)
                if len(viableTarotCards) == amount:
                    break

    return viableTarotCards

def useTarotCard(card, otherCards, save, inConsumables = False):
    # unlike cards or jokers I can get away with using tarot card dictionaries since all this stuff is immutable for
    # all of them
    tarotCardInfo = openjson("consumables/tarotDict")[card.name]
    tarotType = tarotCardInfo["type"]

    # if the tarot card needs you to select cards from your hand (most of them)
    if tarotType == "handModifier":
        maxCardSelectAmount = tarotCardInfo["amnt"]

        if otherCards is None or otherCards == []:
            return False, "No cards to use!"

        if len(otherCards) > maxCardSelectAmount:
            return False, "Too many cards!"

        if card.name == "Death (XIII)" and len(otherCards) == 1:
            return False, "Not enough cards!"

        # suit converters (star, moon, sun, world)
        subModifier = tarotCardInfo["modifier"]
        if subModifier == "suit":
            clearPrintFolder()
            for card in otherCards:
                newCard = card.copy()
                newCard.suit = tarotCardInfo["suit"]
                save.replaceCardInDeck(card, newCard)
                prepareCardForPrinting(newCard, keep=True)
            return True, "Success!"


        # enhancer converters (magician, empress, hierophant, lovers, chariot, justice, devil, tower)
        elif subModifier == "enhancer":
            for card in otherCards:
                newCard = card.copy()
                newCard.enhancement = tarotCardInfo["enhancement"]
                if newCard.enhancement == "stone":
                    newCard.id = None
                    prepareCardForPrinting(newCard, keep=True)
                save.replaceCardInDeck(card, newCard)
            return True, "Success!"

        # rank converter (strength)
        elif subModifier == "rank":
            clearPrintFolder()
            for card in otherCards:
                newCard = card.copy()
                newCard.number = increaseCardVal(card.number)
                save.replaceCardInDeck(card, newCard)
                prepareCardForPrinting(newCard, keep=True)
            return True, "Success!"

        # destroy converter (hanged man)
        elif subModifier == "destroy":
            for card in otherCards:
                save.replaceCardInDeck(card, None)
            return True, "Success!"

        # convert converter (death)
        elif subModifier == "convert":
            newCard = otherCards[1].copy()
            prepareCardForPrinting(newCard)
            save.replaceCardInDeck(otherCards[0], newCard)
            return True, "Success!"

    # consumable/joker creators
    # yeah I'm doing the possibility checks inside each subfunction now instead of at the top deal with it
    elif tarotType == "creator":
        subset = tarotCardInfo["subset"]
        # fool
        if subset == "last":
            if save.lastUsedTarotOrPlanet is not None:
                    if len(save.consumables) < save.consumablesLimit or inConsumables:
                        save.consumables.append(save.lastUsedTarotOrPlanet)
                        return True, "Success!"
            return False, "Did nothing!"

        # judgement
        if subset == "joker":
            if len(save.jokersInPlay) < save.jokerLimit:
                save.jokersInPlay.append(generateRandomWeightedJokers(save, 1))
                return True, "Success!"
            return False, "Not enough space!"

        # high priestess/emperor
        else:
            maxAmnt = tarotCardInfo["amnt"]
            spaceLeft = save.consumablesLimit - len(save.consumables)
            amountToGenerate = min(maxAmnt, spaceLeft)

            if inConsumables:
                amountToGenerate += 1

            if amountToGenerate == 0: return False, "Not enough space!"

            if subset == "planet":
                save.consumables += generateShuffledListOfUnlockedPlanetCards(save, amountToGenerate, False)
            elif subset == "tarot":
                save.consumables += generateShuffledListOfFinishedTarotCards(save, amountToGenerate, False)

            return True, "Success!"

    # hermit/temperance
    # ik the way I store the modifiers isn't easily scalable I should have had a unified system but whatever
    elif tarotType == "monetary":
        if tarotCardInfo["modifier"] == "mult":
            moneyToAdd = min(save.money, 20)
            save.money += moneyToAdd
            return True, "Success!"

        elif tarotCardInfo["modifier"] == "jokerSellValue":
            sellValue = 0
            for joker in save.jokersInPlay:
                sellValue += joker.getSellValue()
            save.money += min(sellValue, 40)
            return True, "Success!"

    # the wheel
    elif tarotType == "meme":
        if len(save.jokersInPlay) > 0:
            # see it really is 1 in 4!
            if random.randint(1, 4) == 1:
                # random.shuffle will mess with the joker order, I need to modify a specific joker in place
                # ik there's a better way to do this but I forget how
                # TODO: fix this later
                jokerModifyIndex = random.randint(0, len(save.jokersInPlay) - 1)
                editions = ["foil", "holographic", "polychrome"]
                weights = [12.5, 8.75, 3.75]
                save.jokersInPlay[jokerModifyIndex].edition = random.choices(editions, weights)[0]
                return True, "Success!"
            else:
                return True, "Nope!"
        return False, "Not enough jokers!"



def increaseCardVal(oldVal):
    face_cards = {"J": 11, "Q": 12, "K": 13, "A": 14}
    reverse_face_cards = {v: k for k, v in face_cards.items()}

    if oldVal in face_cards:
        value = face_cards[oldVal]
    else:
        value = int(oldVal)

    new_value = value + 1

    if new_value > 14:  # Reset after Ace (A)
        return "2"  # Wrap around back to 2
    return reverse_face_cards.get(new_value, str(new_value))
