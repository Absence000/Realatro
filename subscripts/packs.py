from subscripts.cardUtils import Card, generateWeightedRandomCards
import random

class Pack:
    def __init__(self, subset, size):
        self.subset = subset
        self.size = size
        length = packWeightDict[subset]["sizes"][sizes.index(size)]
        self.length = length
        self.cardType = packTypeToCardTypeDict[self.subset]
        self.pickAmount = 1
        if self.size == "mega":
            self.pickAmount = 2

    # returns the proper amount of cards if opened
    # TODO: I think standard packs can have duplicates but the rest I'm not sure
    def open(self, save):
        return generateWeightedRandomCards(self.cardType, save, self.length, generateSpecialSpectrals=True)

    def toString(self, mode=None):
        if mode == "name":
            return f"{self.size.capitalize()} {self.subset.capitalize()} Pack"
        if mode == "description":
            return f"Choose {self.pickAmount} of up to {self.length} {self.cardType.capitalize()} Cards"

    def needsHandToUse(self):
        if self.subset in ["arcana", "spectral"]:
            return True
        return False

    def toDict(self):
        return {
            "subset": self.subset,
            "size": self.size
        }


packTypeToCardTypeDict = {
    "arcana": "tarot",
    "celestial": "planet",
    "standard": "playing",
    "buffoon": "joker",
    "spectral": "spectral"
}

packWeightDict = {
    "standard": {
        "weights": [4, 2, 0.5],
        "sizes": [3, 5, 5]
    },
    "arcana": {
        "weights": [4, 2, 0.5],
        "sizes": [3, 5, 5]
    },
    "celestial": {
        "weights": [4, 2, 0.5],
        "sizes": [3, 5, 5]
    },
    "buffoon": {
        "weights": [1.2, 0.6, 0.15],
        "sizes": [2, 4, 4]
    },
    "spectral": {
        "weights": [0.6, 0.3, 0.07],
        "sizes": [2, 4, 4]
    },
}

sizes = ["normal", "jumbo", "mega"]
addedPacks = ["standard", "arcana", "celestial", "buffoon", "spectral"]

# TODO: add support for buffoon and spectral packs
def generatePackForSale():
    packOptions = []
    packWeights = []
    for subset in addedPacks:
        for size in sizes:
            packOptions.append(Pack(subset=subset, size=size))
            packWeights.append(packWeightDict[subset]["weights"][sizes.index(size)])
    return random.choices(packOptions, packWeights)[0]