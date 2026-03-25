from subscripts.spacesavers import *
from subscripts.jokers import Joker
from subscripts.cardUtils import Card
from subscripts.planetCards import Planet
from subscripts.tarotCards import Tarot
from subscripts.shop import Shop, createShopFromDict

anteBaseChipsList = [100, 300, 800, 2000, 5000, 11000, 20000, 35000, 50000, 110000, 560000, 72000000, 300000000,
                     47000000000, 2.9E+13, 7.7E+16, 8.6E+20, 4.2E+25, 9.2E+30, 9.2E+36, 4.3E+43, 9.7E+50, 1.0E+59,
                     5.8E+67, 1.6E+77, 2.4E+87, 1.9E+98, 8.4E+109, 2.0E+122, 2.7E+135, 2.1E+149, 9.9E+163, 2.7E+179,
                     4.4E+195, 4.4E+212, 2.8E+230, 1.1E+249, 2.7E+268, 4.5E+288, 4.8E+309]

class Save:
    def __init__(self, saveDict):
        deck = []
        for card in saveDict["deck"]:
            deck.append(Card(card))
        self.deck = deck
        self.ante = saveDict["ante"]
        self.blindIndex = saveDict["blindIndex"]
        self.state = saveDict["state"]
        self.hands = saveDict["hands"]
        self.handLimit = saveDict["handLimit"]
        self.discards = saveDict["discards"]
        self.shop = createShopFromDict(saveDict["shop"])
        self.money = saveDict["money"]
        self.handLevels = saveDict["handLevels"]
        self.illegalHandsDiscovered = saveDict["illegalHandsDiscovered"]
        consumables = []
        # TODO: Make a consumable base class or something idk this is dumb
        for consumable in saveDict["consumables"]:
            if consumable["type"] == "planet":
                consumables.append(Planet(consumable["name"], consumable["negative"]))
            if consumable["type"] == "tarot":
                consumables.append(Tarot(consumable["name"], consumable["negative"]))
        self.consumables = consumables
        self.consumablesLimit = saveDict["consumablesLimit"]
        self.hand = saveDict["hand"]
        jokers = []
        for joker in saveDict["jokers"]:
            jokers.append(Joker(joker))
        self.jokers = jokers

        jokersInPlay = []
        for joker in saveDict["jokersInPlay"]:
            jokersInPlay.append(Joker(joker))
        self.jokersInPlay = jokersInPlay

        self.jokerLimit = saveDict["jokerLimit"]
        self.blindInfo = saveDict["blindInfo"]
        self.baseChips = anteBaseChipsList[self.ante]
        self.requiredScore = self.baseChips * self.blindInfo[1]

        discardedCards = []
        for card in saveDict["discardedCards"]:
            discardedCards.append(Card(card))
        self.discardedCards = discardedCards

        playedCards = []
        for card in saveDict["playedCards"]:
            playedCards.append(Card(card))
        self.playedCards = playedCards
        self.score = saveDict["score"]
        self.round = saveDict["round"]
        self.irl = saveDict["irl"]
        lastUsedTarotOrPlanetDict = saveDict["lastUsedTarotOrPlanet"]
        if lastUsedTarotOrPlanetDict is not None:
            if lastUsedTarotOrPlanetDict["type"] == "planet":
                lastUsedTarotOrPlanet = Planet(lastUsedTarotOrPlanetDict["name"], lastUsedTarotOrPlanetDict["negative"])
            else:
                lastUsedTarotOrPlanet = Tarot(lastUsedTarotOrPlanetDict["name"], lastUsedTarotOrPlanetDict["negative"])
        else:
            lastUsedTarotOrPlanet = None
        self.lastUsedTarotOrPlanet = lastUsedTarotOrPlanet
        # TODO: find a smarter way to store the images I need to load for card packs
        self.images = {}
        self.startingHands = saveDict["startingHands"]
        self.startingDiscards = saveDict["startingDiscards"]
        self.ectoUses = saveDict["ectoUses"]
        self.firstShopEncountered = saveDict["firstShopEncountered"]
        self.addPreviouslyPrintedCards = saveDict["addPreviouslyPrintedCards"]


    def toDict(self):
        # turns the jokers, consumables, and deck into dicts
        consumables = []
        for consumable in self.consumables:
            consumables.append(consumable.toDict())
        jokers = []
        for joker in self.jokers:
            jokers.append(joker.toDict())

        jokersInPlay = []
        for joker in self.jokersInPlay:
            jokersInPlay.append(joker.toDict())

        deck = []
        for card in self.deck:
            deck.append(card.toDict())

        hand = []
        for card in self.hand:
            hand.append(card.toDict())

        discardedCards = []
        for card in self.discardedCards:
            discardedCards.append(card.toDict())

        playedCards = []
        for card in self.playedCards:
            playedCards.append(card.toDict())

        if self.lastUsedTarotOrPlanet is None:
            lastUsedTarotOrPlanet = None
        else:
            lastUsedTarotOrPlanet = self.lastUsedTarotOrPlanet.toDict()

        saveDict = {
            "deck": deck,
            "ante": self.ante,
            "blindIndex": self.blindIndex,
            "state": self.state,
            "hands": self.hands,
            "discards": self.discards,
            "shop": self.shop.toDict(),
            "money": self.money,
            "handLevels": self.handLevels,
            "illegalHandsDiscovered": self.illegalHandsDiscovered,
            "consumables": consumables,
            "consumablesLimit": self.consumablesLimit,
            "hand": hand,
            "handLimit": self.handLimit,
            "jokers": jokers,
            "jokersInPlay": jokersInPlay,
            "jokerLimit": self.jokerLimit,
            "requiredScore": self.requiredScore,
            "blindInfo": self.blindInfo,
            "discardedCards": discardedCards,
            "playedCards": playedCards,
            "score": self.score,
            "round": self.round,
            "irl": self.irl,
            "lastUsedTarotOrPlanet": lastUsedTarotOrPlanet,
            "startingHands": self.startingHands,
            "startingDiscards": self.startingDiscards,
            "ectoUses": self.ectoUses,
            "firstShopEncountered": self.firstShopEncountered,
            "addPreviouslyPrintedCards": self.addPreviouslyPrintedCards
        }
        return saveDict

    def hasJoker(self, name):
        for joker in self.jokersInPlay:
            if joker.name == name:
                return True
        return False

    def nextBlind(self):
        if self.blindIndex == 2:
            self.ante += 1
            self.blindIndex = 0
            self.baseChips = anteBaseChipsList[self.ante]
            self.blindInfo = ("Small Blind", 1, 3)
        else:
            self.blindIndex += 1
            self.blindInfo = [("Small Blind", 1, 3), ("Big Blind", 1.5, 4), ("Boss Blind", 2, 5)][self.blindIndex]
        self.requiredScore = self.baseChips * self.blindInfo[1]

    def replaceCardInDeck(self, oldCard, newCard):
        for i, card in enumerate(self.deck):
            if (card.number == oldCard.number and
                    card.suit == oldCard.suit and
                    card.enhancement == oldCard.enhancement and
                    card.edition == oldCard.edition and
                    card.seal == oldCard.seal):
                if newCard is not None:
                    if newCard.suit != oldCard.suit or newCard.number != oldCard.number:
                        newCard.id = None
                    self.deck[i] = newCard
                    return
                else:
                    cardIndex = i
        # TODO: have some sort of error handling here idk
        del self.deck[cardIndex]

def createSaveFromDict(saveDict):
    return Save(saveDict)

def saveGame(save):
    savejson("save", save.toDict())

def createBlankSave(deck):
    handLevels = {
        "High Card": {"level": 1, "chips": 5, "mult": 1},
        "Pair": {"level": 1, "chips": 10, "mult": 2},
        "Two Pair": {"level": 1, "chips": 20, "mult": 2},
        "Three Of A Kind": {"level": 1, "chips": 30, "mult": 3},
        "Straight": {"level": 1, "chips": 30, "mult": 4},
        "Flush": {"level": 1, "chips": 35, "mult": 4},
        "Full House": {"level": 1, "chips": 40, "mult": 4},
        "Four Of A Kind": {"level": 1, "chips": 60, "mult": 7},
        "Straight Flush": {"level": 1, "chips": 100, "mult": 8},
        "Royal Flush": {"level": 1, "chips": 100, "mult": 8},
        "Five Of A Kind": {"level": 1, "chips": 120, "mult": 12},
        "Flush House": {"level": 1, "chips": 140, "mult": 14},
        "Flush Five": {"level": 1, "chips": 160, "mult": 16}
    }
    deck = openjson("decks")[deck]
    return Save({
        "deck": deck,
        "ante": 1,
        "blindIndex": 0,
        "state": "selectingBlind",
        "hands": 4,
        "discards": 4,
        "shop": {
            "cards": [[None, None], [None, None]],
            "packs": [[None, None], [None, None]],
            "vouchers": [None],
            "rerollCost": 0
        },
        "money": 4,
        "handLevels": handLevels,
        "illegalHandsDiscovered": [],
        "consumables": [],
        "consumablesLimit": 2,
        "hand": [],
        "handLimit": 8,
        "jokersInPlay": [],
        "jokers": [],
        "jokerLimit": 5,
        "requiredScore": 0,
        "blindInfo": [
            "Small Blind",
            1,
            3
        ],
        "discardedCards": [],
        "playedCards": [],
        "score": 0,
        "round": 1,
        "irl": True,
        "lastUsedTarotOrPlanet": None,
        "startingHands": 4,
        "startingDiscards": 3,
        "ectoUses": 0,
        "firstShopEncountered": True,
        "addPreviouslyPrintedCards": False
    })

def addToJokerAttribute(save, jokerName, attribute, amount, override=False):
    for joker in save.jokersInPlay:
        if joker.name == jokerName:
            if attribute not in joker.data:
                raise ValueError(f"{jokerName} doesn't have {attribute}")
            if override:
                joker.data[attribute] = amount
            else:
                joker.data[attribute] += amount
            return

    raise ValueError(f"{jokerName} not found")