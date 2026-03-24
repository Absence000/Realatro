import pygame, cv2, textwrap, random, math, zipfile, os
import numpy as np
from cardCreationAndRecognition.finalArcuoTracking import pygameDisplayFoundCards
from subscripts.consumableCards import getConsumableSellPrice
from subscripts.handFinderAndPointsAssigner import findBestHand
from PIL import Image
from cardCreationAndRecognition.cardImageCreator import createImageFromCard, createPackImage, getConsumableImageByCoords
from subscripts.cardUtils import Card
from subscripts.planetCards import Planet
from subscripts.packs import Pack
from subscripts.tarotCards import Tarot
from subscripts.jokers import Joker
from subscripts.spectralCards import Spectral
from subscripts.spacesavers import *

def drawWebcamAndReturnFoundCards(cap, lookupTable, screen, backupDetectedCardsScan, backupDetectedCardsScanTime,
                                  currentTime, save, frame, cutoff):

    printedCards = openjson("printedCards")
    sentToPrinter = openjson("sentToPrinter")
    if frame is None:
        ret, frame = cap.read()
    rawFrame = frame.copy()
    frame, sortedDetectedCards = pygameDisplayFoundCards(lookupTable, frame, save, printedCards, sentToPrinter)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # idk why I need to mirror and rotate it but whatever
    frame = np.fliplr(frame)
    frame = np.rot90(frame, k=1)

    # resizes to 540p
    # idk why this is height x width instead of width x height
    frame = cv2.resize(frame, (540, 960))
    if cutoff == "top":
        frame = frame[0:960, 0:180]
    elif cutoff == "middle":
        frame = frame[0:960, 0:360]

    surface = pygame.surfarray.make_surface(frame)
    screen.blit(surface, (320, 0))

    # it's easier to see where to put the cards if I draw lines on top
    drawRect(screen, (0, 0, 0), (320, 180, 960, 3))
    drawRect(screen, (0, 0, 0), (320, 360, 960, 3))

    foundIDs = []
    for section in ["upper", "middle", "lower"]:
        for card in sortedDetectedCards[section]:
            foundIDs.append(getCardAndJokerTrackingID(card))

    # this is really confusing sorry
    # anti flicker:
    # checks bottom, middle, and top separately against old reference scan
    for section in ["upper", "middle", "lower"]:
        oldSection = backupDetectedCardsScan[section]
        newSection = sortedDetectedCards[section]
        # if the old reference scan has more cards and is less than 3 seconds old:
        if len(newSection) < len(oldSection):
            if currentTime - backupDetectedCardsScanTime[section] < 3:
                # to prevent a missing card being moved to a different section "ghosting" as part of the anti flicker:
                # it checks if the old cards' IDs are anywhere else in the new scan
                # if they are it uses the new scan instead
                # if they aren't it uses the old one
                oldIDs = {getCardAndJokerTrackingID(c) for c in oldSection}
                newIDs = {getCardAndJokerTrackingID(c) for c in newSection}
                oldIDsNotInSection = list(oldIDs - newIDs)
                lostCardFoundInOtherSection = False
                for lostID in oldIDsNotInSection:
                    if lostID in foundIDs:
                        lostCardFoundInOtherSection = True
                if not lostCardFoundInOtherSection:
                    sortedDetectedCards[section] = backupDetectedCardsScan[section]
        else:
            # makes a new backup scan
            backupDetectedCardsScan[section] = sortedDetectedCards[section]
            backupDetectedCardsScanTime[section] = currentTime

    # anti card-appearing-in-multiple-sections +
    # if a card is showing up in multiple sections now after anti flicker we delete it from the top down
    previousSectionIDs = []
    currentSectionIDs = []
    for section in ["upper", "middle", "lower"]:
        newSection = sortedDetectedCards[section]
        for card in newSection:
            trackingID = getCardAndJokerTrackingID(card)
            # anti playing-card-appearing-as-joker:
            # if a playing card is appearing up top it gets moved to the middle
            if section == "upper":
                if isinstance(card, Card):
                    sortedDetectedCards["upper"].remove(card)
                    sortedDetectedCards["middle"].append(card)
                else:
                    currentSectionIDs.append(trackingID)
            else:
                if trackingID in previousSectionIDs:
                    sortedDetectedCards[section].remove(card)
                else:
                    currentSectionIDs.append(trackingID)

        previousSectionIDs = currentSectionIDs





    # draws the extra stuff on top if needed
    for section, sublist in sortedDetectedCards.items():
        for card in sublist:
            if cutoff != "top":
                # why did I make it have both the unpaired tags and the cards
                # whatever
                if isinstance(card, Card):
                    debuffed = False
                    if card not in save.deck or card.debuffed:
                        debuffed = True
                    if card.enhancement not in [None, "stone"] or card.edition is not None or card.seal is not None or debuffed:
                        overlayStuffOnCard(card, debuffed, screen)
                elif isinstance(card, Joker):
                    if card.edition is not None or card.debuffed:
                        overlayStuffOnCard(card, card.debuffed, screen)




    return sortedDetectedCards, backupDetectedCardsScan, backupDetectedCardsScanTime, rawFrame

def openCamera(index):
    cap = cv2.VideoCapture(index)
    # right now it does 1080p but I might change this idk
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    return cap

def getCardAndJokerTrackingID(card):
    # TODO: Change the id for playing cards to tracking ID it's a mess rn
    if isinstance(card, Card):
        return card.id
    elif isinstance(card, Joker):
        return card.trackingID

def overlayStuffOnCard(card, debuffed, screen):
    x, y = getFixedCardCenter(card.coords)
    # TODO: I thought for sure I'd need to cache the images but somehow this godawful shit is fine for
    #  performance, but if there's lag later it'll probably be caused by this
    rawImg = createImageFromCard(card, True, debuffed)
    fixedImg = pygame.image.frombytes(rawImg.tobytes(), (690, 966), "RGBA")
    scalingFactor = 0.0045
    scale = card.scale * scalingFactor
    fixedImg = pygame.transform.scale(fixedImg, (int(scale * 690), int(scale * 966)))
    x -= int(scale * 350)
    y -= int(scale * 500)
    screen.blit(fixedImg, (x, y))

def drawBlindInfoScreen(save, blindInfo, screen, colors, font, origin, mode, chipSymbol):
    # TODO: Fix this it's dumb
    blindName = blindInfo[0]
    blindIndexList = ["Small Blind", "Big Blind", "Boss Blind"]
    blindIndex = blindIndexList.index(blindName)
    blindColor = colors.blindColors[blindIndex]

    x, y = origin
    thickness = 300
    blindNameCoords = (x + 150, y + 10)
    blindNameSize = 40
    blindNameThickness = 40
    blindNameColor = colors.uiOutline

    blindSpriteSize = (50, 50)
    blindSpritePosition = (x + 10, y + 105)

    rewardPanelX = x + 70
    rewardPanelY = y + 100
    rewardPanelThickness = 220
    rewardTextX = rewardPanelX + 35

    if mode == "selection":
        thickness = 150
        blindNameCoords = (x + 75, y + 10)
        blindNameSize = 30
        blindNameThickness = 30
        blindNameColor = blindColor

        blindSpriteSize = (70, 70)
        blindSpritePosition = (x + 40, y + 40)

        rewardPanelX = x
        rewardPanelY = y + 120
        rewardPanelThickness = 150
        rewardTextX = rewardPanelX + 20
    else:
        drawRect(screen, colors.darkUI, (x, y, thickness, 170), round=5)
        drawRect(screen, blindColor, (x + 5, y + 50, thickness - 10, 115), round=5)
    drawRect(screen, blindNameColor, (x + 5, y + 5, thickness - 10, blindNameThickness), round=5)
    drawText(screen, blindName, font, colors.white, blindNameCoords, "center", blindNameSize)

    screen.blit(getBlindSprite(blindName, blindSpriteSize), blindSpritePosition)

    drawRect(screen, colors.darkUI, (rewardPanelX, rewardPanelY, rewardPanelThickness, 60), round=5)
    drawText(
        screen, "Score at least", font, colors.white, (rewardTextX, rewardPanelY + 2),
        "left", 20)
    smallerChipSymbol = pygame.transform.scale(chipSymbol, (20, 20))
    screen.blit(smallerChipSymbol, (rewardPanelX + 5, rewardPanelY + 20))
    requiredScore = str(save.baseChips * blindInfo[1])
    drawText(screen, requiredScore, font, colors.red, (rewardPanelX + 30, rewardPanelY + 20), "left",
             getOptimalTextSize(requiredScore, 30, 180))
    drawText(screen, "Reward:", font, colors.white, (rewardPanelX + 5, rewardPanelY + 43), "left", 15)
    blindReward = blindInfo[2]
    dollarText = "$" * blindReward
    drawText(screen, dollarText, font, colors.yellow, (rewardPanelX + 55, rewardPanelY + 40), "left", 20)

# TODO: when it's the boss blind the outlines change to the color of the boss blind
def drawLeftBar(save, font, screen, colors, handType, level, score, chips, mult, camIndex):
    screenHeight = screen.height
    rawChipSymbol = pygame.image.load("sprites/chips.png").subsurface(0, 0, 58, 58)
    chipSymbol = pygame.transform.scale(rawChipSymbol, (30, 30))

    leftBarOrigin = 20
    leftBarThickness = 300
    drawRect(screen, colors.lightUI, (leftBarOrigin, 0, leftBarThickness, screenHeight), colors.uiOutline)


    if save.state == "playing":
        drawBlindInfoScreen(save, save.blindInfo, screen, colors, font, (20, 20), "leftBar", chipSymbol)


    # round score display
    roundScoreRectHeight = 200
    roundScoreRectThickness = 50
    drawRect(screen, colors.darkUI, (leftBarOrigin, roundScoreRectHeight, leftBarThickness, roundScoreRectThickness), round=5)
    drawText(screen, "Round\nscore", font, colors.white, (leftBarOrigin + 20, roundScoreRectHeight + 2), "left")
    innerRoundScoreRectOrigin = leftBarOrigin + 100
    innerRoundScoreRectThickness = leftBarThickness - 120
    drawRect(screen, colors.lightUI, (
    innerRoundScoreRectOrigin, roundScoreRectHeight + 5, innerRoundScoreRectThickness, roundScoreRectThickness - 10),
             round=5)
    screen.blit(chipSymbol, (innerRoundScoreRectOrigin + 5, roundScoreRectHeight + 10))

    score = str(score)

    drawText(screen, score, font, colors.white, (innerRoundScoreRectOrigin + 40, roundScoreRectHeight + 10),
             "left", getOptimalTextSize(score, 40, innerRoundScoreRectThickness - 40))

    # chips, mult, hand type, and level
    chipsXMultHeight = 260
    chipsXMultThickness = 150

    drawRect(screen, colors.darkUI, (leftBarOrigin, chipsXMultHeight, leftBarThickness, chipsXMultThickness), round=5)
    # hand type + level
    drawText(screen, handType, font, colors.white, (leftBarOrigin + 10, chipsXMultHeight + 20), "left",
             getOptimalTextSize(handType, 50, 250))
    # TODO: this changes color depending on the level
    if level != "":
        drawText(screen, f"lvl.{level}", font, colors.white, (leftBarOrigin + 260, chipsXMultHeight + 20),
                 "left")

    # chips and mult
    drawRect(screen, colors.blue, (leftBarOrigin + 10, chipsXMultHeight + 80, 120, 60), round=5)
    chips = str(chips)
    drawText(screen, chips, font, colors.white, (leftBarOrigin + 20, chipsXMultHeight + 90), "left",
             getOptimalTextSize(chips, 50, 110))

    drawRect(screen, colors.red, (leftBarOrigin + 170, chipsXMultHeight + 80, 120, 60), round=5)
    mult = str(mult)
    drawText(screen, mult, font, colors.white, (leftBarOrigin + 180, chipsXMultHeight + 90), "left",
             getOptimalTextSize(mult, 50, 110))

    drawText(screen, "X", font, colors.red, (leftBarOrigin + 150, chipsXMultHeight + 95), "center", 50)

    infoXOffset = leftBarOrigin + 100

    infoYOffset = 420
    # hands left
    handContainerX = infoXOffset + 10
    handContainerY = infoYOffset + 10
    drawRect(screen, colors.darkUI, (handContainerX, handContainerY, 80, 80), round=5)
    drawText(screen, "Hands", font, colors.white, (handContainerX + 40, handContainerY + 5), "center")
    drawRect(screen, colors.lightUI, (handContainerX + 10, handContainerY + 30, 60, 40), round=5)
    handsLeft = str(save.hands)
    drawText(screen, handsLeft, font, colors.blue, (handContainerX + 40, handContainerY + 35), "center",
             40)

    # discards left
    discardContainerX = handContainerX + 100
    drawRect(screen, colors.darkUI, (discardContainerX, handContainerY, 80, 80), round=5)
    drawText(screen, "Discards", font, colors.white, (discardContainerX + 40, handContainerY + 10),
             "center", size=20)
    drawRect(screen, colors.lightUI, (discardContainerX + 10, handContainerY + 30, 60, 40), round=5)
    discardsLeft = str(save.discards)
    drawText(screen, discardsLeft, font, colors.red, (discardContainerX + 40, handContainerY + 35), "center",
             40)

    # money
    moneyContainerY = handContainerY + 90
    drawRect(screen, colors.darkUI, (handContainerX, moneyContainerY, 180, 80), round=5)
    drawRect(screen, colors.lightUI, (handContainerX + 10, moneyContainerY + 5, 160, 70), round=5)
    money = f"${save.money}"
    drawText(screen, money, font, colors.yellow, (handContainerX + 90, moneyContainerY + 15), "center",
             getOptimalTextSize(money, 70, 160))

    # ante
    lastRowY = moneyContainerY + 90
    drawRect(screen, colors.darkUI, (handContainerX, lastRowY, 80, 80), round=5)
    drawText(screen, "Ante", font, colors.white, (handContainerX + 40, lastRowY + 10),
             "center", size=20)
    drawRect(screen, colors.lightUI, (handContainerX + 10, lastRowY + 30, 60, 40), round=5)
    ante = str(save.ante)
    drawText(screen, ante, font, colors.yellow, (handContainerX + 25, lastRowY + 35), "center",
             40)
    drawText(screen, "/8", font, colors.white, (handContainerX + 40, lastRowY + 40), "left")

    # round
    lastRowY = moneyContainerY + 90
    drawRect(screen, colors.darkUI, (discardContainerX, lastRowY, 80, 80), round=5)
    drawText(screen, "Round", font, colors.white, (discardContainerX + 40, lastRowY + 10),
             "center", size=20)
    drawRect(screen, colors.lightUI, (discardContainerX + 10, lastRowY + 30, 60, 40), round=5)
    round = str(save.round)
    drawText(screen, round, font, colors.yellow, (discardContainerX + 40, lastRowY + 35), "center",
             40)

    # run info
    # TODO: once everything else is done add functionality to this
    drawRect(screen, colors.red, (leftBarOrigin + 10, infoYOffset, 80, 130), round=5)
    drawText(screen, "Run\nInfo\n(event-\nually)", font, colors.white, (leftBarOrigin + 50, infoYOffset + 20),
             "center")

    # camera switching
    drawRect(screen, colors.darkUI, (leftBarOrigin + 10, infoYOffset + 140, 80, 130), round=5)
    drawText(screen, f"Cam {camIndex}", font, colors.white, (leftBarOrigin + 20, infoYOffset + 150),
             "left")

    camAddRect = (leftBarOrigin + 20, infoYOffset + 180, 60, 35)
    drawRect(screen, colors.yellow, camAddRect, round=5)
    drawText(screen, "+", font, colors.white, (leftBarOrigin + 43, infoYOffset + 183), "left", size=40)

    camSubRect = (leftBarOrigin + 20, infoYOffset + 225, 60, 35)
    drawRect(screen, colors.red, camSubRect, round=5)
    drawText(screen, "-", font, colors.white, (leftBarOrigin + 43, infoYOffset + 228), "left", size=40)

    return [{"name": "+",
             "rect": camAddRect},
            {"name": "-",
             "rect": camSubRect}]

blindImageDict = {
    "Small Blind": 0,
    "Big Blind": 1,
    "Boss Blind": 30
}

def getBlindSprite(name, imageSize):
    blindSprites = Image.open("sprites/blindChips.png")
    blindImageIndex = blindImageDict[name]
    size = 68
    topLeftY = blindImageIndex * size
    bottomRightY = (blindImageIndex + 1) * size
    croppedImage = blindSprites.crop((0, topLeftY, size, bottomRightY))
    formattedImage = pygame.image.frombytes(croppedImage.tobytes(), (size, size), "RGBA")
    return pygame.transform.scale(formattedImage, imageSize)

def drawButtons(save, screen, colors, font):
    buttonY = 580

    playRect = (370, 580, 200, 100)
    drawRect(screen, colors.darkUI, (370, buttonY+5, 202, 102), round=8)
    drawRect(screen, colors.blue, playRect, colors.lightUI, round=8)
    drawText(screen, "Play hand\nUse", font, colors.white, (380, buttonY + 10), "left", 40)

    discardX = 580
    discardRect = (discardX, 580, 200, 100)
    drawRect(screen, colors.darkUI, (discardX, buttonY + 5, 202, 102), round=8)
    drawRect(screen, colors.red, discardRect, colors.lightUI, round=8)
    drawText(screen, "Discard\nSell", font, colors.white, (discardX + 10, buttonY + 10), "left", 40)

    return [{"name": "play",
             "rect": playRect},
            {"name": "discard",
             "rect": discardRect}]

def drawConsumables(save, screen, colors, font, mousePos):
    hoveredConsumable = None
    maxWidth = 280
    drawRect(screen, colors.darkUI, (1000, 0, maxWidth, 220), round=8)
    center = 1140
    amnt = len(save.consumables)
    if amnt > 0:
        spacing = int(maxWidth / amnt)
        currentPos = center - ((amnt-1) * spacing)
        for consumable in save.consumables:
            consumableImage = createImageFromCard(consumable)
            fixedImg = pygame.image.frombytes(consumableImage.tobytes(), (690, 966), "RGBA")
            fixedImg = pygame.transform.scale(fixedImg, (136, 190))
            screen.blit(fixedImg, (currentPos - 68, 5))
            if pygame.Rect((currentPos - 68, 5, 136, 190)).collidepoint(mousePos):
                hoveredConsumable = [consumable, currentPos]
                consumable.coords = (currentPos + 68, 95)

            currentPos += spacing

    drawText(screen, f"{amnt}/{save.consumablesLimit}", font, colors.white, (center, 200), size=20)
    # if overlap draw on top of others
    if hoveredConsumable is not None:
        consumable, currentPos = hoveredConsumable
        drawDescription(screen, font, save, colors, currentPos - 68, 5, 160, consumable)
        useRect = (currentPos - 60, 5, 120, 90)
        drawRect(screen, colors.green, useRect, round=8)
        drawText(screen, "Use", font, colors.white, (currentPos, 50), size=20)
        sellRect = (currentPos - 60, 95, 120, 90)
        drawRect(screen, colors.red, sellRect, round=8)
        drawText(screen, f"Sell (${getConsumableSellPrice(consumable, save)})", font, colors.white,
                 (currentPos, 110), size=20)
        return [{"name": "use",
                 "rect": useRect},
                {"name": "sell",
                 "rect": sellRect}], consumable
    return [], None

def drawCardCounter(save, font, screen, colors, foundCards):
    prunedFoundCards = foundCards.copy()
    del prunedFoundCards["unpairedTags"]

    xOrigin = 890
    yOrigin = 550

    drawRect(screen, colors.lightUI, (xOrigin - 10, yOrigin - 10, 420, 180))
    drawRect(screen, colors.darkUI, (xOrigin - 5, yOrigin - 5, 410, 170), round=8)

    mode = "handFinder"
    ind = 0
    handCards = prunedFoundCards["middle"]
    otherCards = []

    for card in handCards:
        cardType = type(card).__name__
        if cardType != "Card":
            mode = "analysis"
            cardToAnalyze = card
        else: otherCards.append(card)
        ind += 1

    # probably should have called them these from the start but I probably would forget
    subsetDict = {
        "upper": "Jokers",
        "middle": "Selection",
        "lower": "Hand"
    }

    iterator = 0
    for subset, cards in prunedFoundCards.items():
        trackedCardsInThirdOfScreen = []
        for card in cards:
            trackedCardsInThirdOfScreen.append(card.toString(mode="fancy"))
        formattedTrackedCardsInThirdOfScreen = '\n'.join(trackedCardsInThirdOfScreen)
        finishedMessage = f"{subsetDict[subset]}\n{formattedTrackedCardsInThirdOfScreen}"
        yOffset = 0
        overflowTrackedCardsAmount = len(trackedCardsInThirdOfScreen) - 7
        if overflowTrackedCardsAmount > 0:
            yOffset = 20 * (overflowTrackedCardsAmount)
            drawRect(screen, colors.darkUI, (xOrigin + iterator - 5, yOrigin-yOffset - 5, 143, yOffset + 5), round=8)

        drawText(screen, finishedMessage, font, colors.white, (xOrigin + iterator, yOrigin - yOffset), "left",
                 getOptimalTextSize(finishedMessage, 20, 133))
        iterator += 133

    if mode == "analysis":
        return cardToAnalyze, otherCards
    else:
        handType = findBestHand(handCards)[0]
        handInfo = save.handLevels[handType]
        return handType, handInfo

def drawAnalysisPopup(save, font, screen, colors, cardToAnalyze):
    xOrigin = 450
    yOrigin = 30

    drawRect(screen, colors.lightUI, (xOrigin - 10, yOrigin-10, 220, 220), round=7)
    drawRect(screen, colors.darkUI, (xOrigin - 5, yOrigin - 5, 210, 210), round=7)
    sellRect = (xOrigin - 10, yOrigin + 210, 220, 50)
    drawRect(screen, colors.red, sellRect, round=7)
    drawText(screen, f"Sell (${cardToAnalyze.getSellValue()})", font, colors.white, (550, 250))
    message = textwrap.fill(cardToAnalyze.toString(), 20)
    drawText(screen, message, font, colors.white, (xOrigin, yOrigin), "left")
    return [{"name": "sellJoker", "rect": sellRect}]

# TODO: Figure out a way to get this displaying correctly if there's duplicate cards
def displayChainEvent(event, screen, font):
    card = event.card
    if isinstance(event.card, tuple):
        topLeftX, topLeftY = card
        newX = topLeftX + 57
        newY = topLeftY + 80
        rect = (newX - 60, newY - 20, 120, 40)

    else:
        cardOrigin = card.coords
        newX, newY = getFixedCardCenter(cardOrigin)
        rect = (newX - 20, newY - 20, 40, 40)

    drawRect(screen, event.color, rect, round=7)
    drawText(screen, event.text, font, (255, 255, 255), (newX, newY-10), "center")


def drawBlindSelectScreen(save, font, screen, colors):
    blindButtons = []
    blindIndexToBlindInfo = [("Small Blind", 1, 3), ("Big Blind", 1.5, 4), ("Boss Blind", 2, 5)]
    def drawBlindPopup(save, font, screen, colors, startX, selectionStatus, color, blindInfo):
        y = 300
        selectButtonColor = colors.yellow
        if selectionStatus != "Select":
            y = 350
            selectRect = (startX + 30, y + 25, 140, 30)
            selectButtonColor = colors.darkUI
            if selectionStatus == "Defeated":
                color = colors.darkUI
        else:
            selectRect = (startX + 30, y + 25, 140, 30)
            blindButtons.append({
                "name": "select",
                "rect": selectRect
            })

        drawRect(screen, color, (startX, y, 200, 500), round=8)
        drawRect(screen, colors.lightUI, (startX + 5, y + 5, 190, 490), round=8)
        drawRect(screen, colors.lighterUI, (startX + 10, y + 10, 180, 250), round=8)
        drawRect(screen, colors.lightUI, (startX + 15, y + 15, 170, 240), round=8)

        drawRect(screen, selectButtonColor, selectRect, round=8)
        drawText(screen, selectionStatus, font, colors.white, (startX + 100, y + 27))

        drawBlindInfoScreen(
            save, blindInfo, screen, colors, font, (startX + 25, y + 55), "selection",
            pygame.image.load("sprites/chips.png").subsurface(0, 0, 58, 58))

        if blindInfo[0] == "Boss Blind":
            drawText(screen, "Up The Ante", font, colors.yellow, (startX + 100, y + 265), size=30)
            drawText(screen, "Raise All Blinds", font, colors.white, (startX + 100, y + 290))
            drawText(screen, "Refresh Blinds", font, colors.white, (startX + 100, y + 315))
        else:
            drawText(screen, "or", font, colors.white, (startX + 100, y + 260))
            drawRect(screen, colors.darkUI, (startX + 20, y + 290, 160, 50), round=8)
            skipRect = (startX + 60, y + 295, 115, 40)
            if selectionStatus == "Select":
                skipButtonColor = colors.red
                blindButtons.append({
                    "name": "skip",
                    "rect": skipRect
                })
            else:
                skipButtonColor = colors.lightUI
            drawRect(screen, skipButtonColor, skipRect, round=8)
            drawText(screen, "Skip Blind", font, colors.white, (startX + 75, y + 303), "left")


    startX = 350

    for i in range(3):
        selectionStatus = "Upcoming"
        if i == save.blindIndex:
            selectionStatus = "Select"
        elif i < save.blindIndex:
            selectionStatus = "Defeated"
        drawBlindPopup(save, font, screen, colors, startX, selectionStatus, colors.blindColors[i],
                       blindIndexToBlindInfo[i])
        startX += 220

    return blindButtons


def drawShop(save, font, screen, colors, mousePos):
    shop = save.shop

    # backgrounds
    shopOriginX = 350
    shopOriginY = 340
    drawRect(screen, colors.lightUI, (shopOriginX, shopOriginY, 700, 390), colors.uiOutline, round=8)
    drawRect(screen, colors.darkUI, (shopOriginX + 5, shopOriginY + 5, 690, 380), round=8)

    shopItemHeight = 160
    cardForSaleY = shopOriginY + 20
    drawRect(screen, colors.lightUI, (shopOriginX + 210, cardForSaleY, 470, shopItemHeight + 10), round=8)

    vouchersAndPacksY = shopOriginY + 200
    drawRect(screen, colors.lightUI, (shopOriginX + 20, vouchersAndPacksY, 325, shopItemHeight + 10), round=8)
    drawRect(screen, colors.darkUI, (shopOriginX + 25, vouchersAndPacksY + 5, 315, shopItemHeight), round=8)
    drawText(screen, f"ANTE {save.ante} VOUCHER", font, colors.lightUI,
             (shopOriginX + 40, vouchersAndPacksY + 20), "center", 20, 90)

    drawText(screen, "NOT\nIMPLEMENTED\nYET", font, colors.white,
             (shopOriginX + 160, vouchersAndPacksY + 50), "center")

    drawRect(screen, colors.lightUI, (shopOriginX + 355, vouchersAndPacksY, 325, shopItemHeight + 10), round=8)

    # buttons
    shopButtons = []
    nextRoundRect = (shopOriginX + 20, shopOriginY + 20, 180, 80)
    drawRect(screen, colors.red, nextRoundRect, round=8)
    drawText(screen, "Next Round", font, colors.white, (shopOriginX + 50, shopOriginY + 45), "left")
    shopButtons.append({
        "name": "Next Round",
        "rect": nextRoundRect
    })

    rerollRect = (shopOriginX + 20, shopOriginY + 110, 180, 80)
    drawRect(screen, colors.green, rerollRect, round=8)
    drawText(screen, "Reroll", font, colors.white, (shopOriginX + 85, shopOriginY + 120), "left", 20)
    rerollText = f"${shop.rerollCost}"
    drawText(screen, rerollText, font, colors.white, (shopOriginX + 105, shopOriginY + 145), "center", 40)
    shopButtons.append({
        "name": "Reroll",
        "rect": rerollRect
    })

    # TODO: merge generateShopItem and generatePackItem at some point they're super similar
    def generateShopItem(coords, rawImg, price, type, index, mousePos, item):
        x, y = coords
        drawRect(screen, colors.darkUI, (x + 20, y - 30, 74, 40), round=8)
        drawRect(screen, colors.lightUI, (x + 25, y - 25, 64, 25), round=8)
        drawText(screen, f"${price}", font, colors.yellow, (x + 57, y - 25))

        if type == "packs":
            size = (690, 930)
        else:
            size = (690, 966)
        cardImg = pygame.image.frombytes(rawImg.tobytes(), size, "RGBA")
        cardImg = pygame.transform.scale(cardImg, (114, shopItemHeight))
        origin = (x, y + 5)
        screen.blit(cardImg, origin)
        rect = origin + (114, shopItemHeight)
        shopButtons.append({
            "name": "buy",
            "rect": rect,
            "type": type,
            "index": index,
            "coords": coords
        })
        # if the mouse is hovering over the shop item it displays a description
        if pygame.Rect(rect).collidepoint(mousePos):
            drawDescription(screen, font, save, colors, x, y, shopItemHeight, item)

    # cards

    cardCenterX = shopOriginX + 330 + 57
    evenOffset = 0
    amountOfCards = 0
    for item in shop.cards:
        if item is not None:
            amountOfCards += 1
    if amountOfCards % 2 == 0:
        evenOffset = 60
    cardStarterX = cardCenterX - (120 * (amountOfCards // 2)) + evenOffset

    cardIndex = 0
    for shopItem in shop.cards:
        if shopItem is not None:
            card = shopItem.item
            price = shopItem.price
            # idk how much this helps performance since it's not like generating the images is super expensive but whatever
            if card in shop.images.keys():
                rawImage = shop.images[card]
            else:
                rawImage = createImageFromCard(card)
                shop.images[card] = rawImage

            generateShopItem(
                (cardStarterX, cardForSaleY), rawImage, price, "cards", cardIndex, mousePos, card)
            cardStarterX += 120
        cardIndex += 1

    # packs
    packCenterX = shopOriginX + 400 + 57
    evenOffset = 0
    amountOfPacks = 0
    for item in shop.packs:
        if item is not None:
            amountOfPacks += 1
    if amountOfPacks % 2 == 0:
        evenOffset = 60
    packStarterX = packCenterX - (120 * (amountOfPacks // 2 )) + evenOffset
    packIndex = 0

    for shopItem in shop.packs:
        if shopItem is not None:
            pack = shopItem.item
            price = shopItem.price
            if pack in shop.images.keys():
                rawImage = shop.images[pack]
            else:
                rawImage = createPackImage(pack)
                shop.images[pack] = rawImage

            generateShopItem(
                (packStarterX, vouchersAndPacksY), rawImage, price, "packs", packIndex, mousePos, pack)
            packStarterX += 120
        packIndex += 1

    # vouchers (eventually)

    return shopButtons

def drawPackButtons(save, items, pickAmount, font, screen, colors, mousePos):
    packItemHeight = 160
    packButtons = []

    def generatePackItem(coords, rawImg, index, item):
        x, y = coords
        cardImg = pygame.image.frombytes(rawImg.tobytes(), (690, 966), "RGBA")
        cardImg = pygame.transform.scale(cardImg, (114, packItemHeight))
        origin = (x, y)
        screen.blit(cardImg, origin)
        rect = origin + (114, packItemHeight)
        packButtons.append({
            "name": "buy",
            "rect": rect,
            "index": index,
            "coords": coords
        })
        # if the mouse is hovering over the shop item it displays a description
        if pygame.Rect(rect).collidepoint(mousePos):
            drawDescription(screen, font, save, colors, x, y, packItemHeight, item)

    cardCenterX = 600
    evenOffset = 0
    if len(items) % 2 == 0:
        evenOffset = 60
    cardStarterX = cardCenterX - (120 * (len(items) // 2)) + evenOffset
    cardIndex = 0

    for item in items:
        item.coords = (cardStarterX + 50, 550)
        if item in save.images.keys():
            rawImage = save.images[item]
        else:
            rawImage = createImageFromCard(item)
            save.images[item] = rawImage

        generatePackItem((cardStarterX, 550), rawImage, cardIndex, item)
        cardStarterX += 120
        cardIndex += 1

    skipRect = (cardStarterX, 580, 50, 40)
    drawRect(screen, colors.lightUI, skipRect, round=8)
    drawText(screen, "Skip", font, colors.white, (cardStarterX + 25, 590))
    packButtons.append({
        "name": "skip",
        "rect": skipRect
    })
    return packButtons

# TODO: Eventually display editions/seals/enhancements and stuff
# TODO: Spectrals and vouchers support

def drawDescription(screen, font, save, colors, x, y, packItemHeight, item):
    drawRect(screen, colors.lightUI, (x - 210, y + 5, 200, packItemHeight), colors.white, round=8)
    drawText(screen, item.toString(mode="name"), font, colors.white, (x - 105, y + 10))
    drawRect(screen, colors.white, (x - 205, y + 40, 190, packItemHeight - 80), round=8)
    if isinstance(item, Planet):
        descriptionRawText = item.toString("description", save)
        bottomColor = colors.teal
        bottomText = "Planet"
    else:
        descriptionRawText = item.toString("description")
    descriptionText = textwrap.fill(descriptionRawText, 20)
    drawText(screen, descriptionText, font, colors.darkUI, (x - 105, y + 50), size=20)
    if isinstance(item, Pack):
        bottomColor = colors.purple
        bottomText = "Booster"
    elif isinstance(item, Tarot):
        bottomColor = colors.lightPurple
        bottomText = "Tarot"
    elif isinstance(item, Spectral):
        bottomColor = colors.blue
        bottomText = "Spectral"
    elif isinstance(item, Joker):
        bottomText = item.rarity
        if bottomText == "Common":
            bottomColor = colors.blue
        elif bottomText == "Uncommon":
            bottomColor = colors.green
        elif bottomText == "Rare":
            bottomColor = colors.red
        elif bottomText == "Legendary":
            bottomColor = colors.lightPurple
    if not isinstance(item, Card):
        drawRect(screen, bottomColor, (x - 165, y + 130, 110, 25), round=8)
        drawText(screen, bottomText, font, colors.white, (x-105, y + 130))

def drawImmediateUsePopup(save, font, screen, colors, item):
    drawRect(screen, colors.lightUI, (375, 375, 650, 300), colors.uiOutline, round=8)
    drawRect(screen, colors.darkUI, (380, 380, 640, 290), round=8)
    drawText(screen, f"Use {item.toString(mode='name')} immediately?", font, colors.white, (700, 400))

    immediateUseButtons = []
    yesRect = (390, 560, 200, 100)
    drawRect(screen, colors.green, yesRect, round=8)
    drawText(screen, "Yes", font, colors.white, (490, 600), size=40)
    immediateUseButtons.append({
        "name": "yes",
        "rect": yesRect
    })

    if len(save.consumables) < save.consumablesLimit:
        noRect = (810, 560, 200, 100)
        drawRect(screen, colors.red, noRect, round=8)
        drawText(screen, "No", font, colors.white, (920, 600), size=40)
        immediateUseButtons.append({
            "name": "no",
            "rect": noRect
        })

    return immediateUseButtons

def getFixedCardCenter(origin):
    # this is weird since the camera gets halved in size and offset 320 pixels to the right
    newX = int((origin[0] / 2) + 320)
    newY = int(origin[1] / 2)
    return newX, newY

def generateStartingMenuPoints():
    pointList = []
    # radial coords but it's 2pi * 100 for speed
    for i in range(500):
        pointList.append([random.randint(0, 1000), random.randint(0, 620)])
    return pointList

def drawMenuSpiral(screen, menuPoints):
    i = 0
    cartesianPointsAndRadius = []
    for radius, angle in menuPoints:
        if radius <= 1:
            radius = 1000
        normalizedRadius = radius/1000
        radius -= 1
        menuPoints[i][0] = radius

        angle += 3 * (1-normalizedRadius)
        menuPoints[i][1] = angle
        angle = angle/100
        cartesianPointsAndRadius.append([[radius * math.cos(angle) + 640, radius * math.sin(angle) + 360], normalizedRadius])
        i += 1

    for point, normalizedRadius in cartesianPointsAndRadius:
        pygame.draw.circle(screen, [255*normalizedRadius, 0, 255*(1-normalizedRadius)], point, 200*normalizedRadius)

    return menuPoints



def drawMenu(screen, font, colors):
    logo = pygame.image.load("sprites/realatro logo.png")
    scaledLogo = pygame.transform.scale(logo, (1000, 500))
    screen.blit(scaledLogo, (145, 20))

    buttons = []
    drawRect(screen, colors.lightUI, (320, 500, 640, 150), colors.darkUI, 8)

    saveRect = (325, 505, 155, 140)
    drawRect(screen, colors.green, saveRect, round=8)
    drawText(screen, "PLAY", font, colors.white, (405, 540), size=40)
    drawText(screen, "(FROM SAVE)", font, colors.white, (405, 590), size=30)

    buttons.append({
        "name": "load",
        "rect": saveRect
    })

    newSaveRect = (485, 505, 155, 140)
    drawRect(screen, colors.blue, newSaveRect, round=8)
    drawText(screen, "NEW", font, colors.white, (565, 540), size=40)
    drawText(screen, "GAME", font, colors.white, (565, 590), size=30)

    buttons.append({
        "name": "new",
        "rect": newSaveRect
    })

    loadSpritesRect = (645, 505, 155, 140)
    drawRect(screen, colors.yellow, loadSpritesRect, round=8)
    drawText(screen, "LOAD", font, colors.white, (725, 540), size=40)
    drawText(screen, "SPRITES", font, colors.white, (725, 590), size=30)

    buttons.append({
        "name": "extract",
        "rect": loadSpritesRect
    })

    exitRect = (805, 505, 155, 140)
    drawRect(screen, colors.red, exitRect, round=8)
    drawText(screen, "EXIT", font, colors.white, (885, 540), size=40)
    drawText(screen, "GAME", font, colors.white, (885, 590), size=30)

    buttons.append({
        "name": "exit",
        "rect": exitRect
    })

    return buttons

def extractBalatroSprites():
    with open("pathToBalatroExe.txt", 'r') as file:
        path = f"{file.read()}\\Balatro.exe"

    with zipfile.ZipFile(path, 'r') as zf:
        extractImage(zf, "resources/textures/2x/BlindChips.png", "blindChips")
        extractImage(zf, "resources/textures/1x/Tarots.png", "consumables")
        # https://github.com/EFHIII/balatro-calculator/blob/main/assets/Editions.png
        # it has an MIT license don't worry
        extractImage(zf, "resources/textures/1x/Enhancers.png", "enhancers")
        extractImage(zf, "resources/textures/1x/Jokers.png", "jokers")
        extractImage(zf, "resources/textures/1x/boosters.png", "packs")
        extractImage(zf, "resources/textures/1x/8BitDeck_opt2.png", "playing")
        extractImage(zf, "resources/textures/2x/chips.png", "chips")

# idk why but chatGPT says I have to do all this complicated shit to extract it without
# also extracting the subfolders and renaming it
def extractImage(zf, texturePath, newName):
    with zf.open(texturePath) as source:
        output_path = os.path.join("sprites", f"{newName}.png")

        with open(output_path, "wb") as target:
            target.write(source.read())

def drawRect(screen, color, rect, outline=None, round=None):
    if round is not None:
        borderRadius = round
    else:
        borderRadius = 0
    if outline is not None:
        x, y, width, height = rect
        outlineRect = (x-3, y-3, width+6, height+6)
        pygame.draw.rect(screen, outline, outlineRect, border_radius=borderRadius)
    pygame.draw.rect(screen, color, rect, border_radius=borderRadius)

def getOptimalTextSize(text, defaultSize, sizeLimit):
    individualLines = text.split("\n")
    longestLineLength = len(max(individualLines, key=len))
    pixelLength = int(0.45 * defaultSize * longestLineLength)
    if pixelLength <= sizeLimit:
        return defaultSize
    else:
        return int(sizeLimit/(0.45*longestLineLength))

def drawText(screen, text, font, color, coords, centering="center", size=None, rotation=None):
    if size is None:
        label = font.render(text, True, color)
    else:
        font = pygame.font.Font("sprites/font/m6x11.ttf", size)
        label = font.render(text, True, color)

    if rotation is not None:
        label = pygame.transform.rotate(label, rotation)

    textRect = label.get_rect()

    if centering == "left":
        textRect.topleft = coords
    elif centering == "right":
        textRect.topright = coords
    else:
        textRect.midtop = coords

    screen.blit(label, textRect)