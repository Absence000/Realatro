from subscripts.consumableCards import consumableCanBeUsedImmediately, sellConsumable, useImmediateConsumable, \
useConsumable
from subscripts.handFinderAndPointsAssigner import calcPointsFromHand
from subscripts.inputHandling import prepareSelectedCards, prepareCardForPrinting
from subscripts.pygameSubfunctions import *
from subscripts.saveUtils import *
from subscripts.colorManagement import Colors
from subscripts.eventChainManagement import EventChain, Event
from subscripts.packs import Pack
from subscripts.cardUtils import Card, addTarotCardIfRoom
from subscripts.jokers import Joker
from subscripts.planetCards import Planet, usePlanetCard
from subscripts.shop import newItemIsConsumable
from subscripts.tarotCards import Tarot, useTarotCard
from subscripts.spectralCards import Spectral, useSpectralCard
import pygame, time

def main():
    pygame.init()
    screenWidth = 1280
    screenHeight = 720
    screen = pygame.Surface((screenWidth, screenHeight))

    screenInfo = pygame.display.Info()
    actualWidth = screenInfo.current_w
    actualHeight = screenInfo.current_h

    actualScreen = pygame.display.set_mode((actualWidth, actualHeight), pygame.RESIZABLE)

    pygame.display.set_caption("Realatro")
    font = pygame.font.Font("sprites/font/balatro.otf")
    clock = pygame.time.Clock()

    lookupTable = openjson("cardCreationAndRecognition/cardToArcuo final.json", True)
    save = Save(openjson("save"))
    if save.state == "dead":
        save = createBlankSave("standard")

    # temp blank save stuff
    # save = createBlankSave("standard", True)
    # save.blindInfo = blindIndexToBlindInfo[save.blindIndex]
    # save.requiredScore = anteBaseChipsList[save.ante] * save.blindInfo[1]
    # save.state = "playing"
    # save.discardedCards = []
    # save.playedCards = []
    # save.discards = 4
    # save.hands = 4
    # save.score = 0

    jokerDict = openjson("jokerDict")

    backupDetectedCardsScan = {
        "upper": [],
        "middle": [],
        "lower": [],
        "unpairedTags": []
    }
    backupDetectedCardsScanTime = {
        "upper": time.time(),
        "middle": time.time(),
        "lower": time.time()
    }

    # TODO: The outline changes color depending on the game state
    # TODO: Turn this into an object with all the colors as attributes
    colors = Colors()

    buttons = []
    pressedButton = ""
    canInteract = True
    currentlyUsingConsumable = False

    camIndex = 1
    cap = openCamera(camIndex)

    chain = EventChain()
    askingAboutImmediateUse = False
    running = True
    inGame = False

    menuPoints = generateStartingMenuPoints()

    while running:
        rawMouseX, rawMouseY = pygame.mouse.get_pos()
        scaleX = screenWidth / actualWidth
        scaleY = screenHeight / actualHeight
        mousePos = [rawMouseX * scaleX, rawMouseY * scaleY]
        currentTime = time.time()
        colors.switchOutline(save)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    if pygame.Rect(button["rect"]).collidepoint(mousePos):
                        pressedButton = button["name"]
                        pressedButtonInfo = button
                        # I need these for like every state so they're up here
                        if pressedButton == "+":
                            pressedButton = ""
                            camIndex += 1
                            cap.release()
                            cap = openCamera(camIndex)
                            if not cap.isOpened():
                                camIndex -= 1
                                cap = openCamera(camIndex)

                        elif pressedButton == "-":
                            pressedButton = ""
                            if camIndex > 0:
                                camIndex -= 1
                                cap.release()
                                cap = openCamera(camIndex)
                                if not cap.isOpened():
                                    camIndex += 1
                                    cap = openCamera(camIndex)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    inGame=False

        # menu
        if not inGame:
            screen.fill([0, 0, 255])
            menuPoints = drawMenuSpiral(screen, menuPoints)
            buttons += drawMenu(screen, font, colors)
            if pressedButton == "exit":
                pressedButton = ""
                running=False
            elif pressedButton == "load":
                pressedButton = ""
                inGame=True
            elif pressedButton == "new":
                pressedButton = ""
                save = createBlankSave("standard")
                inGame=True
            elif pressedButton == "extract":
                pressedButton = ""
                extractBalatroSprites()
        # game
        else:
            screen.fill(colors.backgroundColor)
            if save.state == "selectingBlind":
                if not canInteract:
                    freezeFrame = rawFrame
                else:
                    freezeFrame = None

                buttons = drawLeftBar(save, font, screen, colors, "", "", 0, 0, 0, camIndex)

                foundCards, backupDetectedCardsScan, backupDetectedCardsScanTime, rawFrame = (
                    drawWebcamAndReturnFoundCards(cap, lookupTable, screen, backupDetectedCardsScan,
                                                  backupDetectedCardsScanTime, currentTime, save, freezeFrame, "middle"))

                buttons += drawBlindSelectScreen(save, font, screen, colors)

                consumableButtons, selectedConsumable = drawConsumables(save, screen, colors, font, mousePos)
                buttons += consumableButtons

                handType, handInfo = drawCardCounter(save, font, screen, colors, foundCards)
                handTypeType = type(handType).__name__
                if handTypeType == "Joker":
                    # analysis mode, draws a popup saying what the joker does
                    analysisMode = True
                    selectedJoker = handType
                    buttons += drawAnalysisPopup(save, font, screen, colors, handType)
                else:
                    selectedJoker = None

                if canInteract:
                    if pressedButton == "select":
                        pressedButton = ""
                        save.state = "playing"
                        save.discardedCards = []
                        save.playedCards = []
                        save.discards = save.startingDiscards
                        save.hands = save.startingHands
                        save.score = 0

                    elif pressedButton == "skip":
                        pressedButton = ""
                        save.nextBlind()

                    elif pressedButton == "use":
                        pressedButton = ""
                        if consumableCanBeUsedImmediately(selectedConsumable):
                            useImmediateConsumable(selectedConsumable, save)


                    elif pressedButton == "sell":
                        pressedButton = ""
                        sellConsumable(selectedConsumable, save)

                    elif pressedButton == "sellJoker":
                        pressedButton = ""
                        jokerInPlay = False
                        for joker in save.jokersInPlay:
                            if selectedJoker.id == joker.id:
                                jokerInPlay = True
                        if jokerInPlay:
                            save.money += selectedJoker.getSellValue()
                        save.jokersInPlay = [joker for joker in save.jokersInPlay if joker.id != selectedJoker.id]


            elif save.state == "playing":
                if not canInteract:
                    freezeFrame = rawFrame
                else:
                    freezeFrame = None

                # this is really confusing but it draws the webcam
                foundCards, backupDetectedCardsScan, backupDetectedCardsScanTime, rawFrame = (
                    drawWebcamAndReturnFoundCards(cap, lookupTable, screen, backupDetectedCardsScan,
                                                  backupDetectedCardsScanTime, currentTime, save, freezeFrame, None))

                buttons = []

                if not canInteract:
                    # this part took so long to figure out holy shit
                    # iterates through the event chain until there's nothing left to display
                    if currentTime - lastEventTime > 0.5:
                        chainIndex += 1
                        lastEventTime = currentTime
                    if len(chain.events) > chainIndex:
                        chainLink = chain.events[chainIndex]
                        displayChainEvent(chainLink, screen, font)
                        displayChips = chainLink.chips
                        displayMult = chainLink.mult
                        chainEndTime = currentTime
                    else:
                        if not analysisMode:
                            if currentTime - chainEndTime < 1:
                                handType = str(points)
                                displayChips = 0
                                displayMult = 0
                            else:
                                if currentlyUsingConsumable:
                                    currentlyUsingConsumable = False
                                else:
                                    # end of action check stuff
                                    save.score += points
                                    save.hands -= 1
                                    if save.score >= save.requiredScore:
                                        # blue seals
                                        planetDict = openjson("consumables/planetDict")
                                        for card in foundCards["lower"]:
                                            if card.seal == "blue":
                                                planetFound = None
                                                if len(save.consumables) < save.consumablesLimit:
                                                    for planet, info in planetDict.items():
                                                        if info["hand"] == lastPlayedHandName:
                                                            planetFound = planet

                                                    save.consumables.append(Planet(planetFound))

                                        # advances to the next round
                                        baseReward = save.blindInfo[2]
                                        save.nextBlind()
                                        totalReward = baseReward + save.hands
                                        interest = min(save.money // 5, 5)
                                        save.money += totalReward + interest
                                        save.state = "shop"
                                        save.shop = Shop(cards=[None, None], packs=[None, None], vouchers=[None], rerollCost=5)
                                        save.shop.rollCards(save)
                                        save.shop.rollPacks(save)
                                        saveGame(save)
                                    elif save.hands <= 0:
                                        # mr bones logic goes here
                                        save.state = "dead"
                                        saveGame(save)

                                    canInteract = True
                                    saveGame(save)
                        else:
                            canInteract = True
                            saveGame(save)
                else:
                    handType, handInfo = drawCardCounter(save, font, screen, colors, foundCards)
                    handTypeType = type(handType).__name__
                    if handTypeType == "Joker":
                        # analysis mode, draws a popup saying what the joker does
                        analysisMode = True
                        buttons += drawAnalysisPopup(save, font, screen, colors, handType)
                        selectedJoker = handType
                        otherCards = handInfo
                        handType = ""
                        level = ""
                        score = save.score
                        displayChips = 0
                        displayMult = 0
                    else:
                        consumable = None
                        otherCards = None
                        analysisMode = False
                        level = handInfo["level"]
                        score = save.score
                        displayChips = handInfo["chips"]
                        displayMult = handInfo["mult"]

                buttons += drawLeftBar(save, font, screen, colors, handType, level, score, displayChips, displayMult, camIndex)

                buttons += drawButtons(save, screen, colors, font)
                consumableButtons, selectedConsumable = drawConsumables(save, screen, colors, font, mousePos)
                buttons += consumableButtons
                if canInteract:
                    if pressedButton == "play":
                        pressedButton = ""
                        if not analysisMode:
                            selectedHand = prepareSelectedCards(save, foundCards)
                            if 0 < len(selectedHand) <= 5:
                                canInteract = False
                                lastPlayedHandName = handType
                                points, chain, selectedHand = (
                                    calcPointsFromHand(selectedHand, findBestHand(selectedHand), save.hand, save))
                                lastEventTime = currentTime
                                chainIndex = 0
                    elif pressedButton == "discard":
                        if not analysisMode:
                            if save.discards >= 1:
                                selectedHand = prepareSelectedCards(save, foundCards)
                                if len(selectedHand) <= 5:
                                    # TODO: Discard check stuff here
                                    for card in selectedHand:
                                        if card.seal == "purple":
                                            if len(save.consumables) < save.consumablesLimit:
                                                save.consumables.append(addTarotCardIfRoom(save))
                                    pressedButton = ""
                                    save.discardedCards += selectedHand
                                    save.discards -= 1

                    elif pressedButton == "use":
                        pressedButton = ""
                        currentlyUsingConsumable = True
                        canInteract, lastEventTime, chain, chainIndex = useConsumable(
                            selectedConsumable, foundCards, save, currentTime, canInteract,
                            lastEventTime, chain, chainIndex)

                    elif pressedButton == "sell":
                        pressedButton = ""
                        sellConsumable(selectedConsumable, save)

                    elif pressedButton == "sellJoker":
                        pressedButton = ""
                        jokerInPlay = False
                        for joker in save.jokersInPlay:
                            if selectedJoker.id == joker.id:
                                jokerInPlay = True
                        if jokerInPlay:
                            save.money += selectedJoker.getSellValue()
                        save.jokersInPlay = [joker for joker in save.jokersInPlay if joker.id != selectedJoker.id]

            elif save.state == "shop":
                buttons = drawLeftBar(save, font, screen, colors, "", "", 0, 0, 0, camIndex)

                if not canInteract:
                    freezeFrame = rawFrame
                else:
                    freezeFrame = None

                foundCards, backupDetectedCardsScan, backupDetectedCardsScanTime, rawFrame = (
                    drawWebcamAndReturnFoundCards(cap, lookupTable, screen, backupDetectedCardsScan,
                                                  backupDetectedCardsScanTime, currentTime, save, freezeFrame, "top"))

                handType, handInfo = drawCardCounter(save, font, screen, colors, foundCards)
                handTypeType = type(handType).__name__
                if handTypeType == "Joker":
                    # analysis mode, draws a popup saying what the joker does
                    analysisMode = True
                    selectedJoker = handType
                    buttons += drawAnalysisPopup(save, font, screen, colors, handType)
                else:
                    selectedJoker = None

                if askingAboutImmediateUse: buttons += drawImmediateUsePopup(save, font, screen, colors, item)
                else: buttons += drawShop(save, font, screen, colors, mousePos)

                if len(chain.events) > 0:
                    if currentTime - lastEventTime < 0.25:
                        displayChainEvent(chain.events[0], screen, font)
                    else:
                        del chain.events[0]
                else:
                    canInteract = True

                # TODO: Non hand-requiring consumables should be usable here
                consumableButtons, selectedConsumable = drawConsumables(save, screen, colors, font, mousePos)
                buttons += consumableButtons
                if canInteract:
                    if not askingAboutImmediateUse:
                        if pressedButton == "Reroll":
                            pressedButton = ""
                            if save.money >= save.shop.rerollCost:
                                save.money -= save.shop.rerollCost
                                save.shop.rollCards(save)
                                save.shop.rerollCost += 1
                        if pressedButton == "Next Round":
                            pressedButton = ""
                            # TODO: end of shop checks go here
                            save.state = "selectingBlind"
                        if pressedButton == "buy":
                            pressedButton = ""
                            buyStatus = save.shop.buyItem(pressedButtonInfo["type"], pressedButtonInfo["index"], save)
                            if isinstance(buyStatus, str):
                                chain.add("visual", buyStatus, pressedButtonInfo["coords"], 0, 0)
                                canInteract = False
                            else:
                                chain.add("visual", "Bought!", pressedButtonInfo["coords"], 0, 0)
                                canInteract = False
                                item = buyStatus
                                if isinstance(item, Pack):
                                    save.state = "openingPack"
                                    pickAmount = item.pickAmount
                                    doneOpeningPack = False
                                    canInteract = True
                                    items = item.open(save)
                                elif newItemIsConsumable(item):
                                    # TODO: when consumable usage is implemented finish this
                                    if consumableCanBeUsedImmediately(item):
                                        askingAboutImmediateUse = True
                                    else:
                                        save.consumables.append(item)
                                else:
                                    if isinstance(item, Card):
                                        save.deck.append(item)
                                    else:
                                        save.jokersInPlay.append(item)
                                    prepareCardForPrinting(item, keep=True)

                            lastEventTime = currentTime
                        elif pressedButton == "use":
                            pressedButton = ""
                            if consumableCanBeUsedImmediately(selectedConsumable):
                                useImmediateConsumable(selectedConsumable, save)

                        elif pressedButton == "sell":
                            pressedButton = ""
                            sellConsumable(selectedConsumable, save)

                        elif pressedButton == "sellJoker":
                            pressedButton = ""
                            jokerInPlay = False
                            for joker in save.jokersInPlay:
                                if selectedJoker.id == joker.id:
                                    jokerInPlay = True
                            if jokerInPlay:
                                save.money += selectedJoker.getSellValue()
                            save.jokersInPlay = [joker for joker in save.jokersInPlay if joker.id != selectedJoker.id]
                    else:
                        if pressedButton == "yes":
                            pressedButton = ""
                            askingAboutImmediateUse = False
                            # TODO: Move this to a separate function once you figure out the circular import stuff
                            if isinstance(item, Card):
                                save.deck.append(item)
                                prepareCardForPrinting(item, keep=True)
                            elif isinstance(item, Joker):
                                save.jokersInPlay.append(item)
                                prepareCardForPrinting(item, keep=True)
                            elif isinstance(item, Tarot):
                                useTarotCard(item, None, save, False)
                                save.lastUsedTarotOrPlanet = item
                            elif isinstance(item, Planet):
                                usePlanetCard(item, save)
                                save.lastUsedTarotOrPlanet = item
                            elif isinstance(item, Spectral):
                                useSpectralCard(item, None, save, False)
                        elif pressedButton == "no":
                            askingAboutImmediateUse = False
                            pressedButton = ""
                            save.consumables.append(item)
            elif save.state in ["openingPack", "openingPackFromTag"]:
                buttons = drawLeftBar(save, font, screen, colors, "", "", 0, 0, 0, camIndex)

                if not canInteract:
                    freezeFrame = rawFrame
                else:
                    freezeFrame = None

                foundCards, backupDetectedCardsScan, backupDetectedCardsScanTime, rawFrame = (
                    drawWebcamAndReturnFoundCards(cap, lookupTable, screen, backupDetectedCardsScan,
                                                  backupDetectedCardsScanTime, currentTime, save, freezeFrame, cutoff=None))

                handType, handInfo = drawCardCounter(save, font, screen, colors, foundCards)
                handTypeType = type(handType).__name__
                if handTypeType == "Joker":
                    # analysis mode, draws a popup saying what the joker does
                    analysisMode = True
                    selectedJoker = handType
                    buttons += drawAnalysisPopup(save, font, screen, colors, handType)
                else:
                    selectedJoker = None

                if len(chain.events) > 0:
                    if currentTime - lastEventTime < 0.25:
                        displayChainEvent(chain.events[0], screen, font)
                    else:
                        del chain.events[0]
                        canInteract = True
                else:
                    if doneOpeningPack:
                        if save.state == "openingPack":
                            save.state = "shop"
                        elif save.state == "openingPackFromTag":
                            save.state = "selectingBlind"

                buttons += drawPackButtons(save, items, pickAmount, font, screen, colors, mousePos)
                consumableButtons, selectedConsumable = drawConsumables(save, screen, colors, font, mousePos)
                buttons += consumableButtons
                if canInteract:
                    if pressedButton == "skip":
                        # red card logic goes here
                        pressedButton = ""
                        doneOpeningPack = True
                    elif pressedButton == "buy":
                        pressedButton = ""
                        chosenItemIndex = pressedButtonInfo["index"]
                        chosenCard = items[chosenItemIndex]

                        if isinstance(chosenCard, Planet):
                            usePlanetCard(chosenCard, save)
                            save.lastUsedTarotOrPlanet = chosenCard
                            del items[chosenItemIndex]
                            pickAmount -= 1
                        elif isinstance(chosenCard, Tarot):
                            selectedHand = prepareSelectedCards(save, foundCards)
                            success, successMessage = useTarotCard(chosenCard, selectedHand, save, False)
                            canInteract = False
                            lastEventTime = currentTime
                            if success:
                                chain.add("chips", successMessage, chosenCard, 0, 0)
                                pickAmount -= 1
                                del items[chosenItemIndex]
                                save.lastUsedTarotOrPlanet = chosenCard
                            else:
                                chain.add("mult", successMessage, chosenCard, 0, 0)
                        elif isinstance(chosenCard, Spectral):
                            selectedHand = prepareSelectedCards(save, foundCards)
                            success, successMessage = useSpectralCard(chosenCard, selectedHand, save, False)
                            canInteract = False
                            lastEventTime = currentTime
                            if success:
                                chain.add("chips", successMessage, chosenCard, 0, 0)
                                pickAmount -= 1
                                del items[chosenItemIndex]
                            else:
                                chain.add("mult", successMessage, chosenCard, 0, 0)
                        else:
                            # ik this looks dumb but I think I did it like this bc playing cards and jokers are the only
                            # printable things
                            if isinstance(chosenCard, Card):
                                save.deck.append(chosenCard)
                            else:
                                save.jokersInPlay.append(chosenCard)
                            prepareCardForPrinting(chosenCard, keep=True)
                            del items[chosenItemIndex]
                            pickAmount -= 1
                        if pickAmount <= 0:
                            doneOpeningPack = True

                    elif pressedButton == "use":
                        pressedButton = ""
                        canInteract, lastEventTime, chain, chainIndex = useConsumable(
                            selectedConsumable, foundCards, save, currentTime, canInteract,
                            lastEventTime, chain, chainIndex)

                    elif pressedButton == "sell":
                        pressedButton = ""
                        sellConsumable(selectedConsumable, save)

                    elif pressedButton == "sellJoker":
                        pressedButton = ""
                        jokerInPlay = False
                        for joker in save.jokersInPlay:
                            if selectedJoker.id == joker.id:
                                jokerInPlay = True
                        if jokerInPlay:
                            save.money += selectedJoker.getSellValue()
                        save.jokersInPlay = [joker for joker in save.jokersInPlay if joker.id != selectedJoker.id]

            elif save.state == "dead":
                inGame = False
        scaled = pygame.transform.smoothscale(screen, (actualWidth, actualHeight))
        actualScreen.blit(scaled, (0, 0))
        clock.tick(60)
        pygame.display.flip()

main()