from subscripts.planetCards import usePlanetCard, Planet
from subscripts.priceCalcLogic import calculatePrice
from subscripts.tarotCards import useTarotCard, Tarot
from subscripts.spectralCards import useSpectralCard, Spectral
from subscripts.spacesavers import *
import math
from subscripts.inputHandling import prepareSelectedCards
from subscripts.eventChainManagement import EventChain

def useConsumable(selectedConsumable, foundCards, save, currentTime,
                  canInteract, lastEventTime, chain, chainIndex):
    if isinstance(selectedConsumable, Tarot):
        selectedHand = prepareSelectedCards(save, foundCards)
        success, successMessage = useTarotCard(selectedConsumable, selectedHand, save, True)
        canInteract = False
        lastEventTime = currentTime
        chainIndex = 0
        if success:
            chain.add("chips", successMessage, selectedConsumable, 0, 0)
            save.consumables.remove(selectedConsumable)
            save.lastUsedTarotOrPlanet = selectedConsumable
        else:
            chain.add("mult", successMessage, selectedConsumable, 0, 0)
    if isinstance(selectedConsumable, Spectral):
        selectedHand = prepareSelectedCards(save, foundCards)
        success, successMessage = useSpectralCard(selectedConsumable, selectedHand, save, True)
        canInteract = False
        lastEventTime = currentTime
        chainIndex = 0
        if success:
            chain.add("chips", successMessage, selectedConsumable, 0, 0)
            save.consumables.remove(selectedConsumable)
        else:
            chain.add("mult", successMessage, selectedConsumable, 0, 0)
    elif isinstance(selectedConsumable, Planet):
        usePlanetCard(selectedConsumable, save)
        save.consumables.remove(selectedConsumable)
        save.lastUsedTarotOrPlanet = selectedConsumable
    return canInteract, lastEventTime, chain, chainIndex


def getConsumableSellPrice(consumable, save):
    buyPrice = calculatePrice(consumable, save)
    return math.floor(buyPrice/2)

def sellConsumable(consumable, save):
    sellPrice = getConsumableSellPrice(consumable, save)
    save.money += sellPrice
    save.consumables.remove(consumable)

# consumables that need a hand to work can't be used immediately
def consumableCanBeUsedImmediately(consumable):
    if isinstance(consumable, Tarot):
        if openjson("consumables/tarotDict")[consumable.name]["type"] == "handModifier":
            return False
    elif isinstance(consumable, Spectral):
        if openjson("consumables/tarotDict")[consumable.name]["type"] in ["handModifier", "destroyRandom"]:
            return False
    return True

def useImmediateConsumable(consumable, save):
    if isinstance(consumable, Tarot):
        useTarotCard(consumable, None, save)

    if isinstance(consumable, Planet):
        usePlanetCard(consumable, save)

    elif isinstance(consumable, Spectral):
        useSpectralCard(consumable, None, save)
    save.consumables.remove(consumable)