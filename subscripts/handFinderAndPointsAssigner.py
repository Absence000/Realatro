from collections import Counter
from subscripts.cardUtils import cardCountsAsFaceCard, addTarotCardIfRoom
from subscripts.planetCards import upgradeHandLevel
from subscripts.spacesavers import *
from subscripts.jokers import Joker
from subscripts.saveUtils import addToJokerAttribute
from subscripts.eventChainManagement import *
import random


# figures out what poker hand the player has, and specifies what cards to add the points to
# TODO: add an override for the joker that changes how many cards that get scored points
def findBestHand(hand):
    handValueList = []
    handSuitList = []
    handLength = 0
    for card in hand:
        if card.enhancement != "stone":
            handValueList.append(card.number)
            if card.enhancement == "wild":
                handSuitList.append("W")
            else:
                handSuitList.append(card.suit)
            handLength += 1
    straight = handIsStraight(handValueList)
    flush = handIsFlush(handSuitList)
    countList = numberOfMatchingCards(handValueList)


    #illegal hands
    if handLength == 5:
        if len(countList) == 1 and flush:
            return "Flush Five", "all"
        if len(countList) == 2 and flush:
            notAFourOfAKind = True
            for count in countList:
                if count[1] == 4:
                    notAFourOfAKind = False
            if notAFourOfAKind:
                return "Flush House", "all"
        if len(countList) == 1:
            return "Five Of A Kind", "all"


    # legal hands
    if straight and flush:
        return ("Royal Flush", "all") if "10" in handValueList and "A" in handValueList else ("Straight Flush", "all")
    for count in countList:
        if count[1] == 4:
            return "Four Of A Kind", [count[0]]
    if handLength == 5 and len(countList) == 2:
        return "Full House", "all"
    if flush:
        return "Flush", "all"
    if straight:
        return "Straight", "all"
    for count in countList:
        if count[1] == 3:
            return "Three Of A Kind", [count[0]]
    pairCount = 0
    pairCards = []
    for count in countList:
        if count[1] == 2:
            pairCount += 1
            pairCards.append(count[0])
    if pairCount == 2:
        return "Two Pair", pairCards
    if pairCount == 1:
        return "Pair", pairCards

    #all stone card error handling
    try:
        highestCard = [turnNumberBackIntoPlayingCardValue(turnHandValueIntoNumbersAndSort(handValueList)[-1])]
    except:
        highestCard = "all"
    return "High Card", highestCard


# returns true if the hand is a straight (all the numbers are in a row)
# aces can be either 1 or 14 in this but not both
# TODO: Add overrides for the hand value length requirement joker
def handIsStraight(handValueList):
    if len(handValueList) == 5:
        testLists = [turnHandValueIntoNumbersAndSort(handValueList), turnHandValueIntoNumbersAndSort(handValueList, 1)]
        for testList in testLists:
            if valuesAreConsecutive(testList):
                return True
    return False


# checks if all the values in the list are consecutive
# TODO: add something for the shortcut joker to work
def valuesAreConsecutive(testList):
    return all(testList[i] + 1 == testList[i + 1] for i in range(len(testList) - 1))


# returns true if the hand is a flush (all the suits are the same)
# works with wild cards
# TODO: add hand limit stuff
def handIsFlush(handSuitList):
    if len(handSuitList) == 5:
        if "W" not in handSuitList:
            return len(set(handSuitList)) == 1
        elif len(set(handSuitList)) <= 2:
            return True


# reformats the card number list as a list of [number, timesInHand]
# used in four of a kind, full house, three of a kind, two pair, and pair
def numberOfMatchingCards(handValueList):
    countDict = Counter(handValueList)
    return [[num, count] for num, count in countDict.items()]

faceCardValueDict = {
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14
}

# turns the list of hand values into a list of numbers sorted bottom to top
def turnHandValueIntoNumbersAndSort(handValueList, aceOverride=False):
    sortedNumList = []
    for number in handValueList:
        try:
            sortedNumList.append(int(number))
        except:
            if aceOverride and number == "A":
                sortedNumList.append(1)
            else:
                sortedNumList.append(faceCardValueDict[number])
    sortedNumList.sort()
    return sortedNumList


# used for returning the value of the card that was affected by the play
def turnNumberBackIntoPlayingCardValue(number):
    if 2 <= number <= 10:
        return str(number)
    else:
        return [key for key, value in faceCardValueDict.items() if value == number][0]


chips = 0
mult = 0

# now that we identified the hand and the cards that need to be assigned the points, we can figure out how many points
# to add!
# TODO: this is where most of the joker effects come in oh god
def calcPointsFromHand(hand, handData, unselectedHand, save):
    # gets the base chips and mult
    handType = handData[0]
    affectedCards = handData[1]

    global chips
    global mult

    chips = 0
    mult = 0

    # royal and straight flushes are treated the same but they get displayed differently
    displayHandType = handType
    if handType == "Royal Flush":
        handType = "Straight Flush"

    handInfo = save.handLevels
    baseChips = handInfo[handType]["chips"]
    baseMult = handInfo[handType]["mult"]

    chips = baseChips
    mult = baseMult

    chain = EventChain()

    # print(f"{displayHandType} lvl {save.handLevels[handType]['level']}")
    # print(f"Triggered cards: {affectedCards}")


    # if an illegal hand has been played it updates the save
    if handType in ["Flush Five", "Flush House", "Five Of A Kind"]:
        if handType not in save.illegalHandsDiscovered:
            save.illegalHandsDiscovered.append(handType)
            # print(f"Discovered {handType}!")

    # iterates through each card in the hand to award points
    for card in hand:
        if affectedCards == "all" or card.number in affectedCards or card.enhancement == "stone":
            if card.debuffed:
                chain.add("mult", "Debuffed!", card, chips, mult)
            else:
                triggerCard(card, save, chain)


    # here comes most of the joker logic in the game oh boy
    for joker in save.jokers:
        if joker.debuffed:
            chain.add("mult", "Debuffed!", joker, chips, mult)
        else:
            jokerName = joker.name
            jokerData = joker.data

            if "condition" in jokerData:
                condition = jokerData["condition"]
            else:
                condition = None

            # we gotta put the upgrading jokers first or their upgrades won't be added when they count for the score

            # card count dependent end-of-hand check jokers (half joker, square joker)
            if condition == "cardCount":
                if jokerName == "Half Joker":
                    if len(hand) <= 3:
                        jokerMult = jokerData["mult"]
                        mult += jokerMult
                        chain.add("mult", jokerMult, joker, chips, mult)
            if jokerName == "Square Joker":
                if len(hand) == 4:
                    addToJokerAttribute(save, "Square Joker", "chip", 4)
                    chain.add("visual", "+4 chips", joker, chips, mult)

            # hand dependent end-of-hand check jokers (spare trousers, runner)
            if jokerName in ["Spare Trousers", "Runner"]:
                if handType == jokerData["hand"] or jokerData["hand"] in handContainerDict[handType]:
                    if jokerName == "Spare Trousers":
                        addToJokerAttribute(save, "Spare Trousers", "mult", 2)
                        chain.add("visual", "+2 mult", joker, chips, mult)
                    else:
                        addToJokerAttribute(save, "Runner", "chips", 2)
                        chain.add("visual", "+15 chips", joker, chips, mult)



            # always active end-of-hand check jokers:
            # joker, misprint, gros michel, ice cream, cavendish, square joker, vampire, hologram, fortune teller,
            # lucky cat, bull, flash card, popcorn, spare trousers, castle, campfire, swashbuckler, glass joker,
            # wee joker, hit the road, stuntman, bootstraps, canio, yorick
            if condition == "active":
                # weird ones
                if jokerName == "Misprint":
                    jokerMult = random.randint(0, 23)
                    mult += jokerMult
                    chain.add("mult", jokerMult, joker, chips, mult)
                elif jokerName == "Bull":
                    # does nothing if you have 0 or less money
                    money = save.money
                    if money > 0:
                        jokerChips = jokerData["chip"] * money
                        chips += jokerChips
                        chain.add("chip", jokerChips, joker, chips, mult)
                # TODO: Combine bull and bootstraps at some point so code reviewers online don't yell at you
                elif jokerName == "Bootstraps":
                    money = save.money
                    if money > 0:
                        jokerMult = (money // 5) * 2
                        mult += jokerMult
                        chain.add("mult", jokerMult, joker, chips, mult)

                elif jokerName == "Swashbuckler":
                    combinedSellVal = 0
                    for secondIterationJoker in save.jokers:
                        combinedSellVal += secondIterationJoker.getSellValue

                    mult += combinedSellVal
                    chain.add("mult", combinedSellVal, joker, chips, mult)

                # simple(ish) ones
                else:
                    if "mult" in jokerData:
                        jokerMult = jokerData["mult"]
                        mult += jokerMult
                        chain.add("mult", jokerMult, joker, chips, mult)
                    if "chip" in jokerData:
                        jokerChips = jokerData["chip"]
                        chips += jokerChips
                        chain.add("chip", jokerChips, joker, chips, mult)
                    if "multmult" in jokerData:
                        jokerMultMult = jokerData["multmult"]
                        mult *= jokerMultMult
                        chain.add("multmult", jokerMultMult, joker, chips, mult)
                    # TODO: Remember to make Gros Michel and Cavendish possibly go extinct at the end of the round
                    # TODO: Add a card entering deck check for Hologram
                    # TODO: Remember to make Ice Cream and Popcorn decrease at the end of every round
                    # TODO: Add a reroll counter in the save for Flash Card
                    # TODO: Make Ramen decrease on discard and destroy itself once it reaches 1 mult
                    # TODO: Add Castle's functionality for discards
                    # TODO: Add Campfire's functionality for selling cards and resetting when defeating the boss blind
                    # TODO: Get blind skips working for Throwback
                    # TODO: Get glass joker working for glass breaking checks
                    # TODO: Get Jack discard working for hit the road
                    # TODO: -2 hand size for Stuntman
                    # TODO: Add a face card destruction check for Canio
                    # TODO: Add a discard check for Yorick

            # always active hand-containing-dependent jokers:
            # jolly, zany, mad, crazy, droll, sly, wily, clever, devious, crafty, runner, seance (eventually)
            # duo, trio, family, order, tribe
            if condition == "hand":
                if handType == jokerData["hand"] or jokerData["hand"] in handContainerDict[handType]:
                    if jokerData["type"] == "mult":
                        jokerMult = jokerData["mult"]
                        mult += jokerMult
                        chain.add("mult", jokerMult, joker, chips, mult)
                    elif jokerData["type"] == "chip":
                        jokerChips = jokerData["chip"]
                        chips += jokerChips
                        chain.add("chip", jokerChips, joker, chips, mult)
                    elif jokerData["type"] == "multmult":
                        jokerMultMult = jokerData["multmult"]
                        mult *= jokerMultMult
                        chain.add("multmult", jokerMultMult, joker, chips, mult)
                    # elif jokerName == "Seance":
                        # TODO: Add seance functionality here once spectrals are added

            # joker slot dependent end-of-hand check jokers (joker stencil, abstract joker)
            if condition == "jokerSlot":
                if jokerName == "Joker Stencil":
                    # joker stencil counts itself as an empty slot
                    emptySlots = save.jokerLimit - len(save.jokers) + 1
                    # TODO: Figure out if this is added to the multmult or it executes immediately
                    mult *= emptySlots
                    chain.add("multmult", emptySlots, joker, chips, mult)
                elif jokerName == "Abstract Joker":
                    jokerMult = (len(save.jokers) * 3)
                    mult += jokerMult
                    chain.add("mult", jokerMult, joker, chips, mult)

            # end-of-hand check hand retrigerrer (mime)
            # the blue seal and gold card retriggering is done in the end of round check, this just handles steel cards
            # TODO: Make Mime work with the other jokers and stuff, and add the chain once it's finished
            # if jokerName == "Mime":
            #     for card in unselectedHand:
            #         if card.enhancement == "steel":
            #             steelCardMult *= triggerSteelCard(card)

            # TODO: end-of-hand check discard/hand amount jokers (banner, mythic summit, green),
            #  make the save to update per hand so I can track it

            # TODO: Every 6 hands played check (Loyalty Card)

            # TODO: Final hand check (Dusk, Acrobat)

            # end-of-hand check lowest rank (raised fist)
            if jokerName == "Raised Fist":
                # if there's no cards in your unselected hand it does nothing
                if len(unselectedHand) != 0:
                    lowestRank = 13
                    for card in unselectedHand:
                        realValue = card.getValue()
                        if realValue < lowestRank:
                            lowestRank = realValue
                    jokerMult = lowestRank * 2
                    mult += jokerMult
                    chain.add("mult", jokerMult, joker, chips, mult)

            # TODO: # of times poker hand has been played tracking (Supernova)

            # TODO: Consecutive hand played without a scoring face card tracking (Ride The Bus)

            # end-of-hand check hand upgrader (space joker)
            if jokerName == "Space Joker":
                if random.randint(1, 4) == 1:
                    # TODO: Reformat the planet dict or something idk this is stupid
                    planetDict = openjson("consumables/planetDict")
                    for planet, info in planetDict.items():
                        if info["hand"] == handType:
                            additionInfo = info["addition"]
                    upgradeHandLevel(handType, 1, additionInfo[1], additionInfo[0], save)
                    chain.add("visual", f"+1 lvl!", joker, chips, mult)

            # end-of-hand check unselected hand suit checker (blackboard)
            # this is weird bc it's actually only if there's no hearts or diamonds contrary to the description
            # also wild cards work with this apparently
            if jokerName == "Blackboard":
                blackboardActive = True
                for card in unselectedHand:
                    if card.suit in ["H", "D"]:
                        blackboardActive = False
                if blackboardActive:
                    mult *= 3
                    chain.add("multmult", 3, joker, chips, mult)

            # TODO: end-of-hand first round single card check (DNA, sixth sense)

            # end-of-hand remaining deck check (blue joker)
            if jokerName == "Blue Joker":
                cardsRemaining = len(save.deck) - len(save.playedCards)
                jokerChips = jokerData["chip"] * cardsRemaining
                chips += jokerChips
                chain.add("chips", jokerChips, joker, chips, mult)

            # TODO: Planet card use check (constellation)

            # TODO: Card score use check (hiker)

            # end-of-hand ace and straight check (superposition)
            if jokerName == "Superposition":
                hasAce = False
                for card in hand:
                    if card.number == "A":
                        hasAce = True
                if hasAce and handType == "Straight":
                    tarotCardAdded = addTarotCardIfRoom(save)
                    if tarotCardAdded:
                        chain.add("visual", "+1 tarot", joker, chips, mult)

            # end-of-hand exclusive hand dependent jokers (to do list)
            # TODO: make to do list's hand change at the end of the round
            if jokerName == "To Do List":
                if handType == jokerData["hand"]:
                    jokerMoney = jokerData["money"]
                    save.money += jokerMoney
                    chain.add("visual", f"+${jokerMoney}", joker, chips, mult)

            # TODO: Check if poker hand has been played this round (Card Sharp, Obelisk)

            # end-of-hand money check (vagabond)
            if jokerName == "Vagabond":
                if save.money <= 4:
                    tarotCardAdded = addTarotCardIfRoom(save)
                    if tarotCardAdded:
                        chain.add("visual", "+1 tarot", joker, chips, mult)

            # end-of-hand king check (baron)
            if jokerName == "Baron":
                for card in unselectedHand:
                    if card.number == "K":
                        mult *= 1.5
                        chain.add("multmult", 1.5, joker, chips, mult)

            # end-of-hand face cards in hand check (reserved parking)
            if jokerName == "Reserved Parking":
                for card in unselectedHand:
                    if cardCountsAsFaceCard(card, save):
                        if random.randint(1, 2) == 1:
                            save.money += 1
                            chain.add("visual", "Triggered!", joker, chips, mult)
                            chain.add("visual", "+$1", card, chips, mult)

            # end-of-hand stone card checking throughout the deck (stone joker)
            # this is dumb but idk how else to do it
            if jokerName == "Stone Joker":
                jokerChips = 0
                for card in save.deck:
                    if card.enhancement == "stone":
                        jokerChips += jokerData["chips"]
                if jokerChips > 0:
                    chips += jokerChips
                    chain.add("chip", jokerChips, joker, chips, mult)

            # end-of-hand uncommon joker check (baseball card)
            if jokerName == "Baseball Card":
                for secondaryJoker in save.jokers:
                    if secondaryJoker[1]["rarity"] == "Uncommon":
                        jokerMultMult = jokerData["multmult"]
                        mult *= jokerMultMult
                        chain.add("multmult", jokerMultMult, joker, chips, mult)

            # end-of-hand all suits check (flower pot)
            # TODO: how does this work with wild cards? Idk
            if jokerName == "Flowerpot":
                requiredSuits = {"H", "D", "C", "S"}
                suitsInHand = [card.suit for card in hand]
                if requiredSuits.issubset(suitsInHand):
                    jokerMultMult = jokerData["multmult"]
                    mult *= jokerMultMult
                    chain.add("multmult", jokerMultMult, joker, chips, mult)

            # TODO: Figure out how to check for a scoring club card + another scoring suit card for seeing double

            # end-of-hand queen checks (shoot the moon)
            # TODO: Make shoot the moon work with boss blind debuffs
            if jokerName == "Shoot The Moon":
                for card in unselectedHand:
                    if card.number == "Q":
                        jokerMult = jokerData["mult"]
                        mult += jokerMult
                        chain.add("visual", "Triggered!", joker, chips, mult)
                        chain.add("mult", jokerMult, card, chips, mult)

            # end-of-hand enhanced cards in deck checks (driver's license)
            if jokerName == "Driver's License":
                enhancedCardCount = 0
                for card in hand + unselectedHand + save.deck:
                    if card.enhancement is not None:
                        enhancedCardCount += 1
                if enhancedCardCount >= 16:
                    jokerMultMult = jokerData["multmult"]
                    mult *= jokerMultMult
                    chain.add("multmult", jokerMultMult, joker, chips, mult)
            # after the effects come the editions
            if joker.edition is not None:
                if joker.edition == "foil":
                    chips += 50
                    chain.add("chips", 50, joker, chips, mult)
                if joker.edition == "holographic":
                    mult += 10
                    chain.add("mult", 10, joker, chips, mult)
                elif joker.edition == "polychrome":
                    mult = mult * 1.5
                    chain.add("multmult", 1.5, joker, chips, mult)


    # now does the same for steel cards in the unselected hand to multiply the multiplier independently of the multmult

    for card in unselectedHand:
        # TODO: Mime stuff here
        if card.enhancement == "steel":
            triggerTimes = 1
            if card.seal == "red":
                triggerTimes = 2
            for i in range(triggerTimes):
                mult *= 1.5
                chain.add("multmult", 1.5, card, chips, mult)

    # resets all the retrig checks for each card
    for card in hand + unselectedHand + save.deck:
        card.retriggeredBy = []

    # TODO: fix this weird stuff that I did for command line testing
    for cardIndex in range(len(hand) - 1, -1, -1):
        save.playedCards.append(hand[cardIndex])
        if hand[cardIndex].enhancement == "glass":
            if hand[cardIndex].number in affectedCards or affectedCards == "all":
                if random.randint(1, 4) == 1:
                    chain.add("visual", "Broke!", hand[cardIndex], chips, mult)
                    # TODO: Glass joker stuff here
                    save.replaceCardInDeck(hand[cardIndex], None)

    # print(f"{chips} X {mult}")
    return chips * mult, chain, hand


def triggerCard(card, save, chain):
    # A = 11 chips, face cards = 10 chips, all numbered cards are = their value
    global chips
    global mult

    if card.seal == "gold":
        save.money += 3
        chain.add("visual", "+$3", card, chips, mult)
        # print("Earned $3 from a gold seal!")

    if card.enhancement != "stone":
        try:
            baseCardChipAmount = int(card.number)
        except:
            if card.number == "A":
                baseCardChipAmount = 11
            else:
                baseCardChipAmount = 10
    else:
        baseCardChipAmount = 50


    chips += baseCardChipAmount
    chain.add("chip", baseCardChipAmount, card, chips, mult)

    enhancementBonusChips = 0
    enhancementBonusMult = 0
    # TODO: put all the card effect stuff here
    if card.enhancement == "bonus":
        enhancementBonusChips = 30
    elif card.enhancement == "mult":
        enhancementBonusMult = 4
    elif card.enhancement == "lucky":
        luckyCardTriggered = False
        if random.randint(1, 5) == 1:
            enhancementBonusMult = 20
            # print("+20 mult from lucky card!")
            luckyCardTriggered = True
        if random.randint(1, 15) == 1:
            save.money += 20
            # print("Won $20 with a lucky card!")
            chain.add("visual", "+$20", card, chips, mult)
            luckyCardTriggered = True
        # On lucky card trigger (lucky cat)
        if luckyCardTriggered and save.hasJoker("Lucky Cat"):
            addToJokerAttribute(save, "Lucky Cat", "multmult", 0.25)
    elif card.enhancement == "glass":
        mult = mult * 2
        chain.add("multmult", 2, card, chips, mult)

    if enhancementBonusChips > 0:
        chips += enhancementBonusChips
        chain.add("chip", enhancementBonusChips, card, chips, mult)
    if enhancementBonusMult > 0:
        mult += enhancementBonusMult
        chain.add("mult", enhancementBonusMult, card, chips, mult)

    # edition checks
    if card.edition == "foil":
        chips += 50
        chain.add("chip", 50, card, chips, mult)
    elif card.edition == "holographic":
        mult += 10
        chain.add("mult", 10, card, chips, mult)
    elif card.edition == "polychrome":
        mult = mult * 1.5
        chain.add("multmult", 1.5, card, chips, mult)

    # card scoring check jokers
    for joker in save.jokers:
        #TODO: fix the joker formatting this is dumb
        jokerName = joker.name
        jokerData = joker.data
        if "condition" in jokerData:
            condition = jokerData["condition"]
        else:
            condition = None
        # card suit check jokers (greedy, lusty, wrathful, gluttonous)
        # also weird ones like ancient joker, rough gem, bloodstone, arrowhead, onyx agate
        # TODO: Make ancient joker's suit change at the end of the round
        if condition == "suit":
            if card.suit == jokerData["suit"]:
                if jokerName == "Bloodstone":
                    if random.randint(1, 2) == 1:
                        mult *= 1.5
                        chain.add("multmult", 1.5, joker, chips, mult)
                elif jokerName == "Rough Gem":
                    save.money += 1
                    chain.add("visual", "+$1", joker, chips, mult)
                elif "mult" in jokerData:
                    multToAdd = jokerData["mult"]
                    mult += multToAdd
                    chain.add("mult", multToAdd, joker, chips, mult)
                elif "multmult" in jokerData:
                    jokerMultMult = jokerData["multmult"]
                    mult *= jokerMultMult
                    chain.add("multmult", jokerMultMult, joker, chips, mult)
                elif "chip" in jokerData:
                    chipsToAdd = jokerData["chip"]
                    chips += chipsToAdd
                    chain.add("chip", chipsToAdd, joker, chips, mult)

        # number check (fibonacci, even steven, odd todd, scholar, walkie talkie, hack, wee joker, 8 ball)
        if jokerName == "Wee Joker":
            if card.number == "2":
                addToJokerAttribute(save, "Wee Joker", "chip", 8)
                chain.add("visual", "+8", joker, chips, mult)
        if condition == "numbers":
            if card.number in jokerData["numbers"]:
                # can't use elif bc of walkie talkie
                if "mult" in jokerData:
                    multToAdd = jokerData["mult"]
                    mult += multToAdd
                    chain.add("mult", multToAdd, joker, chips, mult)
                if "chip" in jokerData:
                    chipsToAdd = jokerData["chip"]
                    chips += chipsToAdd
                    chain.add("chip", chipsToAdd, joker, chips, mult)
                # hack is weird since it retrigs
                if jokerData["type"] == "retrig":
                    if "hack" not in card.retriggeredBy:
                        card.retriggeredBy.append("hack")
                        chain.add("visual", "Retriggered!", joker, chips, mult)
                        triggerCard(card, save, chain)

                if jokerName == "8 Ball":
                    if random.randint(1, 4) == 1:
                        addTarotCardIfRoom(save)

        # face check (scary face, business, smiley face)
        if condition == "face":
            if cardCountsAsFaceCard(card, save):
                if jokerName == "Business Card":
                    if random.randint(1, 2) == 1:
                        moneyToAdd = jokerData["money"]
                        save.money += moneyToAdd
                        chain.add("visual", f"+${moneyToAdd}", joker, chips, mult)
                else:
                    if "chip" in jokerData:
                        chipsToAdd = jokerData["chip"]
                        chips += chipsToAdd
                        chain.add("chip", chipsToAdd, joker, chips, mult)
                    if "mult" in jokerData:
                        multToAdd = jokerData["mult"]
                        mult += multToAdd
                        chain.add("mult", multToAdd, joker, chips, mult)

        # retrig check (seltzer)
        #TODO: make Seltzer destroy itself after 10 rounds
        if jokerName == "Seltzer":
            if "seltzer" not in card.retriggeredBy:
                card.retriggeredBy.append("seltzer")
                chain.add("visual", "Retriggered!", joker, chips, mult)
                triggerCard(card, save, chain)

        # I could combine seltzer and sock and buskin but whatever
        if jokerName == "Sock and Buskin":
            if cardCountsAsFaceCard(card, save):
                if "sockAndBuskin" not in card.retriggeredBy:
                    card.retriggeredBy.append("sockAndBuskin")
                    chain.add("visual", "Retriggered!", joker, chips, mult)
                    triggerCard(card, save, chain)

        # enhancement check/remover (vampire)
        # unlike regular balatro stone card values aren't tracked so when it removes a stone card enhancement it gives
        # it a random value
        if jokerName == "Vampire":
            if card.enhancement is not None:
                card.enhancement = None
                chain.add("visual", "Unenhanced!", card, chips, mult)
                addToJokerAttribute(save, "Vampire", "multmult", 0.1)
                chain.add("visual", "+0.1", joker, chips, mult)

        # Face Cards turn to gold (Midas)
        if jokerName == "Midas Mask":
            if cardCountsAsFaceCard(card, save):
                card.enhancement = "gold"
                chain.add("visual", "Triggered!", joker, chips, mult)
                chain.add("visual", "Gold!", card, chips, mult)


        # TODO: Put some sort of first face card indicator in the save for photograph and similar for hanging chad

        # gold enhancement check (Golden Ticket)
        # I could combine vampire and golden ticket but who cares this is easier to read
        if jokerName == "Golden Ticket":
            if card.enhancement == "gold":
                save.money += 4
                chain.add("visual", "+$4", joker, chips, mult)

        # specific suit and number check (idol)
        # TODO: Make the idol change every round
        if jokerName == "The Idol":
            if card.suit == jokerData["suit"] and card.number == jokerData["number"]:
                jokerMultMult = jokerData["multmult"]
                mult *= jokerMultMult
                chain.add("multmult", jokerMultMult, joker, chips, mult)

        # I could combine these but nah

        # kings and queens check (triboulet)
        if jokerName == "Triboulet":
            if card.number in ["K", "Q"]:
                jokerMultMult = jokerData["multmult"]
                mult *= jokerMultMult
                chain.add("multmult", jokerMultMult, joker, chips, mult)

    if card.seal == "red":
        if "red seal" not in card.retriggeredBy:
            card.retriggeredBy.append("red seal")
            # print(f"Retriggering {card.number}!")
            chain.add("visual", "Retriggered!", card, chips, mult)
            triggerCard(card, save, chain)


handContainerDict = {
    "High Card": [],
    "Pair": [],
    "Two Pair": ["Pair"],
    "Three Of A Kind": ["Pair"],
    "Straight": [],
    "Flush": [],
    "Full House": ["Pair", "Two Pair", "Three Of A Kind"],
    "Four Of A Kind": ["Pair", "Two Pair", "Three Of A Kind"],
    "Straight Flush": ["Flush", "Straight"],
    "Five Of A Kind": ["Pair", "Two Pair", "Three Of A Kind", "Four Of A Kind"],
    "Flush House": ["Pair", "Two Pair", "Three Of A Kind", "Full House", "Flush"],
    "Flush Five": ["Pair", "Two Pair", "Three Of A Kind", "Four Of A Kind", "Five Of A Kind", "Flush"],
}