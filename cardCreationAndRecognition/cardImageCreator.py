import random

from PIL import Image, ImageChops, ImageFilter, ImageEnhance
from cardCreationAndRecognition.fiducialRecognizerTest import generateBoardForCard
from subscripts.spacesavers import *
import colorsys

enhancersWidth = 69
enhancersHeight = 93
enhancersPixelGap = 2

# the origin is the top left
enhancersCoordsDict = {
    "base": [2, 1],
    "gold seal": [3, 1],
    "stone": [6, 1],
    "gold": [7, 1],
    "bonus": [2, 2],
    "mult": [3, 2],
    "wild": [4, 2],
    "lucky": [5, 2],
    "glass": [6, 2],
    "steel": [7, 2],
    "purple seal": [5, 5],
    "red seal": [6, 5],
    "blue seal": [7, 5],
}

editionsCoordsDict = {
    "foil": [2, 1],
    "holographic": [3, 1],
    "polychrome": [4, 1],
    "debuffed": [5, 1]
}

def createImageFromCard(card, forPygame=False, debuffed=False):
    # stupid circular imports making me do this instead of isinstance()
    cardType = type(card).__name__
    if cardType == "Card":
        cardImage = selectPlayingCardBackground(card, forPygame)
        if card.enhancement != "stone":
            # if it's for pygame it only gives the base card image if the enhancement is one of the ones that covers
            # the suit+number
            if not forPygame or card.enhancement not in [None, "wild", "bonus", "mult"]:
                cardValueImage = returnCroppedImageByName("playing", card.number, card.suit)
                cardImage.paste(cardValueImage, (0, 0), cardValueImage)

        if card.edition is not None or debuffed:
            edition = card.edition
            if debuffed:
                edition = "debuffed"
            cardEditionImage = returnCroppedImageByName("playing", edition)
            if edition == "polychrome":
                # reduces opacity if it's on glass
                if card.enhancement == "glass":
                    cardEditionImage = setOpacity(cardEditionImage, 0.5)
                # overlays only on nonwhite pixels
                r, g, b, a = cardImage.split()
                mask = ImageChops.invert(Image.merge("RGB", (r, g, b))).convert("L")
                cardImage.paste(cardEditionImage, (0, 0), mask)
            elif edition == "debuffed":
                cardEditionImage = setOpacity(cardEditionImage, 2)
                cardImage.paste(cardEditionImage, (0, 0), cardEditionImage)
            else:
                # cardEditionImage = setOpacity(cardEditionImage, 0.5)
                cardImage.paste(cardEditionImage, (0, 0), cardEditionImage)
        if card.seal != None:
            sealImage = returnCroppedImageByName("playing", card.seal + " seal", forPygame=forPygame)
            cardImage.paste(sealImage, (0, 0), sealImage)

    elif cardType == "Tarot":
        # tarots are in order on a 10 wide image
        tarotDict = openjson("consumables/tarotDict")
        tarotIndex = list(tarotDict.keys()).index(card.name)
        x = tarotIndex % 10
        y = tarotIndex // 10
        cardImage =  getConsumableImageByCoords(x, y, card)
    elif cardType == "Planet":
        # the secret ones are in weird spots but the others are all on the same row in order
        regularOrder = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
        secretPosDict = {
            "Eris": 3,
            "Ceres": 8,
            "Planet X": 9
        }
        if card.name in regularOrder:
            x = regularOrder.index(card.name)
            y = 3
        else:
            x = secretPosDict[card.name]
            y = 2
        cardImage = getConsumableImageByCoords(x, y, card)
    elif cardType == "Spectral":
        regularOrder = ["Black Hole", "Familiar", "Grim", "Incantation", "Talisman", "Aura", "Wraith", "Sigil",
                        "Ouija", "Ectoplasm", "Immolate", "Ankh", "Deja Vu", "Hex", "Trance", "Medium", "Cryptid"]
        if card.name in regularOrder:
            # black hole is at index 39
            correctedIndex = regularOrder.index(card.name) + 39
            x = correctedIndex % 10
            y = correctedIndex // 10
            cardImage = getConsumableImageByCoords(x, y, card)
        else:
            # it's the soul and I have to do some weird stuff
            baseSoulImage = getConsumableImageByCoords(2, 2, card)

            baseImage = Image.open("sprites/enhancers.png")
            topLeftX = 1
            topLeftY = enhancersHeight + enhancersPixelGap + 1
            crop = baseImage.crop((topLeftX, topLeftY, topLeftX + enhancersWidth, topLeftY + enhancersHeight))
            baseSoulImage.paste(crop, (0, 0), crop)
            cardImage = baseSoulImage
    elif cardType == "Joker":
        jokerDict = openjson("jokerDict")
        x, y = jokerDict[card.name]["position"]
        cardImage = getConsumableImageByCoords(x, y, card)
        # handles editions
        edition = card.edition
        if card.debuffed:
            edition = "debuffed"
        if edition is not None and edition != "negative":
            cardEditionImage = returnCroppedImageByName("playing", edition)
            r, g, b, a = cardImage.split()
            if edition == "polychrome":
                # overlays only on nonwhite pixels with an alpha greater than 0
                rgbMask = ImageChops.invert(Image.merge("RGB", (r, g, b))).convert("L")
                alphaMask = a.point(lambda x: 255 if x > 0 else 0)
                mask = ImageChops.multiply(rgbMask, alphaMask)
                cardImage.paste(cardEditionImage, (0, 0), mask)
            elif edition == "debuffed":
                cardEditionImage = setOpacity(cardEditionImage, 2)
                cardImage.paste(cardEditionImage, (0, 0), cardEditionImage)
            else:
                # overlays only on pixels with an alpha greater than 0
                r2, g2, b2, a2 = cardEditionImage.split()
                mask = ImageChops.multiply(a, a2)
                cardImage.paste(cardEditionImage, (0, 0), mask)

        # hologram has a secondary position, all the legendaries have the faces under it
        if card.name == "Hologram":
            x2, y2 = jokerDict["Hologram"]["secondaryPosition"]
            secondaryImage = getConsumableImageByCoords(x2, y2, card, "secondary")

            secondaryImage = prepareHologramPicture(secondaryImage, 5, 20, 1,
                                                    (260, 242, 242), (0, 250, 255))
            cardImage.paste(secondaryImage, (0, 0), secondaryImage)

        if card.rarity == "Legendary":
            x2 = x
            y2 = y + 1
            secondaryImage = getConsumableImageByCoords(x2, y2, card, "secondary")
            cardImage.paste(secondaryImage, (0, 0), secondaryImage)

    # resizing

    cardImage = cardImage.resize((690, 966), Image.Resampling.NEAREST)
    # I have to handle the wee joker stuff here bc if I resized it earlier it would have messed up the scaling
    if hasattr(card, "name") and card.name == "Wee Joker":
        resize = cardImage.resize((345, 483), Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (690, 966), (0, 0, 0, 0))
        # this is half a pixel out of center but who cares lmao
        topLeftCorner = (172, 241)

        canvas.paste(resize, topLeftCorner, resize)
        cardImage = canvas

    # caches it at runtime
    if forPygame:
        debuffedStr = ""
        if debuffed:
            debuffedStr = "Debuffed "
        cardImage.save(f"imageCache/{debuffedStr}{card.toString()}.png")

    return cardImage

def getConsumableImageByCoords(x, y, card, secondary=None):
    # stupid circular imports making me do this instead of isinstance()
    cardType = type(card).__name__
    if cardType == "Joker":
        imagePath = "sprites/jokers.png"
    else:
        imagePath = "sprites/consumables.png"
    baseImage = Image.open(imagePath)
    topLeftX = (x * enhancersWidth) + (x * enhancersPixelGap) + 1
    topLeftY = (y * enhancersHeight) + (y * enhancersPixelGap) + 1
    crop = baseImage.crop((topLeftX, topLeftY, topLeftX + enhancersWidth, topLeftY + enhancersHeight))

    # enhancement handling
    if cardType == "Joker":
        if secondary is None:
            if card.edition == "negative":
                crop = turnNegative(crop)
    else:
        if card.negative:
            crop = turnNegative(crop)
    return crop

def prepareHologramPicture(cutout, blur_radius=20, intensity=2.0, glow_opacity=0.5, glow_color=None, tintColor=None):
    # Separate RGBA
    r, g, b, a = cutout.split()
    rgb = Image.merge("RGB", (r, g, b))

    # tint the image
    tintLayer = Image.new("RGB", rgb.size, tintColor)
    rgb = ImageChops.multiply(rgb, tintLayer)

    # Optional: tint the glow
    if glow_color:
        tint = Image.new("RGB", cutout.size, glow_color)
        rgb = ImageChops.multiply(rgb, tint)

    # Brighten image to amplify glow effect
    bright = ImageEnhance.Brightness(rgb).enhance(intensity)

    # Blur to create the bloom
    bloom = bright.filter(ImageFilter.GaussianBlur(blur_radius))

    # Convert to RGBA with desired opacity
    bloom_alpha = a.filter(ImageFilter.GaussianBlur(blur_radius))  # blur alpha for fadeout
    bloom_alpha = bloom_alpha.point(lambda x: int(x * glow_opacity))  # reduce opacity

    bloom_rgba = Image.merge("RGBA", (*bloom.split(), bloom_alpha))

    # Create a result image and composite bloom UNDER original cutout
    result = Image.new("RGBA", cutout.size, (0, 0, 0, 0))
    result = Image.alpha_composite(result, bloom_rgba)
    result = Image.alpha_composite(result, cutout)

    return result

def turnNegative(image):
    # Split into RGB and Alpha
    r, g, b, a = image.split()

    # Merge RGB and invert
    rgb_image = Image.merge("RGB", (r, g, b))

    # this part sucks
    # apparently balatro inverts the brightness if it's low saturation,
    # inverts and offsets the hue, and blends it with (79, 99, 103)

    pixels = rgb_image.load()
    width, height = rgb_image.size
    blend_r, blend_g, blend_b = 79, 99, 103
    blendIntensity = 0.8

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

            # if [r, g, b] == [150, 170, 203]:
            #     print(s)

            if s <= 0.27:
                v_new = 1.0 - v
            else:
                v_new = v

            h_new = 0.2 - h


            # Convert back to RGB
            r_new, g_new, b_new = colorsys.hsv_to_rgb(h_new, s, v_new)
            r_new = int(r_new * 255)
            g_new = int(g_new * 255)
            b_new = int(b_new * 255)

            # Additively blend with (79, 99, 103)
            r_final = min(r_new + int((blendIntensity * blend_r)), 255)
            g_final = min(g_new + int((blendIntensity * blend_g)), 255)
            b_final = min(b_new + int((blendIntensity * blend_b)), 255)

            pixels[x, y] = (r_final, g_final, b_final)


    # Add original alpha channel back
    r2, g2, b2 = rgb_image.split()
    inverted_image = Image.merge("RGBA", (r2, g2, b2, a))

    return inverted_image

def selectPlayingCardBackground(card, forPygame):
    if card.enhancement is None:
        return returnCroppedImageByName("playing", "base", forPygame=forPygame)
    else: return returnCroppedImageByName("playing", card.enhancement, forPygame=forPygame)

nonIntCoordsDict = {
    "H": 1,
    "C": 2,
    "D": 3,
    "S": 4,
    "J": 10,
    "Q": 11,
    "K": 12,
    "A": 13
}

def returnCroppedImageByName(subset, name, suit=None, forPygame=False):
    if subset == "playing":
        if suit is not None:
            baseImageName = "sprites/playing.png"
            if name.isdigit():
                xCoord = int(name) - 1
            else:
                xCoord = nonIntCoordsDict[name]
            coords = [xCoord, nonIntCoordsDict[suit]]

        else:
            if name in ["polychrome", "holographic", "foil", "debuffed"]:
                baseImageName = "sprites/editions.png"
                coordsDict = editionsCoordsDict
            else:
                baseImageName = "sprites/enhancers.png"
                coordsDict = enhancersCoordsDict
            coords = coordsDict[name]
        baseImage = Image.open(baseImageName)
        topLeftX = ((coords[0] - 1) * enhancersWidth) + ((coords[0] - 1) * enhancersPixelGap) + 1
        topLeftY = ((coords[1] - 1) * enhancersHeight) + ((coords[1] - 1) * enhancersPixelGap) + 1
        crop = baseImage.crop((topLeftX, topLeftY, topLeftX + enhancersWidth, topLeftY + enhancersHeight))

        if forPygame:
            # removes all white/border pixels
            pixels = crop.load()
            for x in range(enhancersWidth):
                for y in range(enhancersHeight):
                    r, g, b, a = pixels[x, y]
                    if (r, g, b) == (255, 255, 255) or (r, g, b) == (192, 200, 214):
                        pixels[x, y] = (0, 0, 0, 0)

        return crop


def fixGlass(image):
    baseImage = returnCroppedImageByName("playing", "base")
    baseImage.paste(image, (0, 0), image)
    pixels = baseImage.load()
    width, height = baseImage.size

    for x in range(width):
        for y in range(height):
            r, g, b, a = pixels[x, y]
            if a == 136:
                pixels[x, y] = (209, 230, 232, 255)

    return baseImage

def setOpacity(image, amnt):
    image.putalpha(image.split()[3].point(lambda x: int(x * amnt)))
    return image


def createTaggedCardImage(card, lookupTable):
    cardImage = createImageFromCard(card)
    alreadyPrinted = openjson("printedCards")

    iterator = 0
    cardBinary = card.toBinary()
    for binary in lookupTable:
        if binary == cardBinary and iterator not in alreadyPrinted:
            lookupIndex = iterator
            break
        iterator += 1

    # should never return an error, right?
    generateBoardForCard(lookupIndex)

    fiducialImage = Image.open("testBoard.png")

    cardImage.paste(fiducialImage, (564, 50))
    fiducialImage = fiducialImage.rotate(180)
    cardImage.paste(fiducialImage, (30, 720))

    # this is an invisible square because sometimes windows messes with the orientation when you're trying to print a bunch at once
    background = Image.new("RGBA", (966, 966), (0, 0, 0, 0))

    img_width, img_height = cardImage.size
    paste_x = (966 - img_width) // 2
    paste_y = (966 - img_height) // 2

    # the tarots and some of the jokers have some gaps so this fills them in without painting the invisible sides black too
    cardType = type(card).__name__
    if cardType != "Card":
        gapFillerImage = Image.new("RGBA", (690, 966), (0, 0, 0, 255))
        background.paste(gapFillerImage, (paste_x, paste_y), gapFillerImage)
        cardName = card.toString(mode="name")
    else:
        cardName = card.toString()

    background.paste(cardImage, (paste_x, paste_y), cardImage)
    background.save(f"print/{cardName}.png")

    sentToPrinter = openjson("sentToPrinter")
    if lookupIndex not in sentToPrinter:
        sentToPrinter.append(lookupIndex)
        savejson("sentToPrinter", sentToPrinter)

packCoordsDict = {
    "arcana": {
        "normal": [(0, 0), (1, 0), (2, 0), (3, 0)],
        "jumbo": [(0, 2), (1, 2)],
        "mega": [(2, 2), (3, 2)]
    },
    "celestial": {
        "normal": [(0, 1), (1, 1), (2, 1), (3, 1)],
        "jumbo": [(0, 3), (1, 3)],
        "mega": [(2, 3), (3, 3)]
    },
    "spectral": {
        "normal": [(0, 4), (1, 4)],
        "jumbo": [(2, 4)],
        "mega": [(3, 4)]
    },
    "standard": {
        "normal": [(0, 6), (1, 6), (2, 6), (3, 6)],
        "jumbo": [(0, 7), (1, 7)],
        "mega": [(2, 7), (3, 7)]
    },
    "buffoon": {
        "normal": [(0, 8), (1, 8)],
        "jumbo": [(2, 8)],
        "mega": [(3, 8)]
    }
}

packX = 69
packY = 93

def createPackImage(pack):
    baseImage = Image.open("sprites/packs.png")
    validCoords = packCoordsDict[pack.subset][pack.size]
    if len(validCoords) > 1:
        random.shuffle(validCoords)
    x, y = validCoords[0]

    # there's a 1 pixel gap around them and 2 pixels in between each one
    fixedX = 1 + (packX * x) + (2 * (x - 1))
    fixedY = 1 + (packY * y) + (2 * (y - 1))
    packImage = baseImage.crop((fixedX, fixedY, fixedX + packX, fixedY + packY))
    packImage = packImage.resize((690, 930))
    return packImage

# def generateCardPairingList():
#     iterator = 0
#     # pairList = openjson("cardToArcuo final.json", True)
#     pairList = []
#     # playing cards (8320, 160/card)
#     for suit in ["S", "C", "H", "D"]:
#         for number in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]:
#             for i in range(160):
#                         card = Card({
#                             "suit": suit,
#                             "number": number
#                         })
#                         pairList.append(card.toBinary())
#     # jokers (8/joker, 1200)
#     jokerDict = openjson("jokerDict")
#     for jokerData in jokerDict.items():
#         for i in range(8):
#             joker = Joker(jokerData, edition)
#             pairList.append(joker.toBinary())
#
#     # stone cards (480)
#     for i in range(480):
#             card = Card({
#                 "suit": "A",
#                 "number": "S",
#                 "enhancement": "stone"
#             })
#             pairList.append(card.toBinary())
#     savejson("cardToArcuo final.json", pairList, True)
