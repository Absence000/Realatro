import cv2, traceback
import numpy as np
from subscripts.cardUtils import createCardFromBinary
from subscripts.spacesavers import *
from collections import defaultdict, Counter


def markerIsRightSideUp(corners):
    p1, p2, p3, p4 = corners
    rightSideUp = p1[1] < p3[1]
    return rightSideUp


def get_detected_boards(frame, aruco_dict, parameters):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thirdOfFrameHeight = frame.shape[0]/3

    # Detect markers
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, _ = detector.detectMarkers(gray)

    detected_boards = []
    unpairedTags = []

    if ids is not None and len(ids) >= 2:
        # sorting them from left to right
        ids_list = ids.flatten().tolist()
        corners_list = [c.reshape(-1, 2) for c in corners]
        sorted_markers = sorted(zip(ids_list, corners_list), key=lambda x: np.mean(x[1][:, 0]))

        unsortedBoardTags = []
        # tries to form the boards into 1 x 2 groups
        i = 0
        while i < len(sorted_markers) - 1:
            # I have to find the distance between them which means I have to get the size
            # idk how this works chatGPT made it
            id1, corners1 = sorted_markers[i]
            id2, corners2 = sorted_markers[i + 1]
            center1 = np.mean(corners1, axis=0)
            center2 = np.mean(corners2, axis=0)
            distance_x = abs(center1[0] - center2[0])
            distance_y = abs(center1[1] - center2[1])
            marker_size = np.linalg.norm(corners1[0] - corners1[2])
            normalized_y_distance = distance_y / marker_size if marker_size > 0 else 0

            # orientation doesn't matter as long as the cards face upwards
            if distance_x < distance_y:
                upwards = markerIsRightSideUp(corners1)

                # since it's left to right I have to flip the orientation if the bottom one gets scanned first
                # this took so long to figure out god dammit
                marker1TopLeftY = corners1[0][1]
                marker2TopLeftY = corners2[0][1]
                if marker2TopLeftY < marker1TopLeftY:
                    flipID = not upwards
                else:
                    flipID = upwards


                id1 = correctID(id1)
                id2 = correctID(id2)

                if flipID:
                    combinedID = int(f"{id1}{id2}")
                else:
                    combinedID = int(f"{id2}{id1}")

                if normalized_y_distance < 1.1:
                    # I could do this more accurately but it's way more math so no
                    roughBoardPosition = corners1[0]
                    boardYCenter = roughBoardPosition[1]
                    unsortedBoardTags += [int(id1), int(id2)]

                    if upwards:
                        roughBoardPosition[0] -= 2 * marker_size
                        roughBoardPosition[1] += 3 * marker_size
                    else:
                        roughBoardPosition[0] += 2 * marker_size
                        roughBoardPosition[1] -= 3 * marker_size

                    if boardYCenter < thirdOfFrameHeight:
                        verticalPos = "upper"
                    elif boardYCenter < 2 * thirdOfFrameHeight:
                        verticalPos = "middle"
                    else:
                        verticalPos = "lower"

                    detected_boards.append(
                        {"id": combinedID, "rightSideUp": upwards, "verticalPos": verticalPos,
                         "roughPos": roughBoardPosition, "markerSize": marker_size})
            i += 1

        # stupid python list comprehension removing duplicates too I had to use chatGPT for this
        ids_counter = Counter(ids_list)
        board_counter = Counter(unsortedBoardTags)

        unpaired_counter = ids_counter - board_counter
        unpairedTags = list(unpaired_counter.elements())
    return detected_boards, unpairedTags

def correctID(id):
    if id == 0:
        return "00"
    else:
        return str(id).zfill(2)


# TODO: this was made for the old system where multiple cards could have the same tag but now they all
#  have individual tags so most of the complexity is here for no reason lmao
def arcuoToCard(detected_boards, lookupTable, unpairedTags, save, printedCards, sentToPrinter):
    # this stupid card filtering algorithm took so long jesus
    # not even chatGPT could help
    output = {"upper": [], "middle": [], "lower": [], "unpairedTags": unpairedTags}

    grouped = defaultdict(list)

    for d in detected_boards:
        key = (d['id'], d['verticalPos'])
        grouped[key].append(d)

    # Process each group
    for (cardID, pos), orientations in grouped.items():
        try:
            binaryValue = lookupTable[cardID]
            detectedCard = createCardFromBinary(cardID, binaryValue, save, printedCards, sentToPrinter)
            detectedCard.coords = orientations[0]["roughPos"]
            detectedCard.scale = orientations[0]["markerSize"]
        except Exception as e:
            print(e)
            traceback.print_exc()
            print(f"Unrecognized card! {cardID}, {binaryValue}")
            detectedCard = None
        # rightSideUp = orientations["rightSideUp"]
        trues = [d for d in orientations if d['rightSideUp']]
        falses = [d for d in orientations if not d['rightSideUp']]

        num_pairs = min(len(trues), len(falses))

        # Add one detection per full pair
        for i in range(num_pairs):
            output[pos].append(detectedCard)

        # Add leftover single detections
        leftovers = trues[num_pairs:] + falses[num_pairs:]
        for leftover in leftovers:
            output[pos].append(detectedCard)

    return output

def pygameDisplayFoundCards(lookupTable, frame, save, printedCards, sentToPrinter):
    # opens the webcam frame and draws all the cards and stuff
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
    parameters = cv2.aruco.DetectorParameters()

    detected_boards, unpairedTags = get_detected_boards(frame, aruco_dict, parameters)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    corners, ids, _ = detector.detectMarkers(gray)

    if ids is not None:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

    sortedDetectedCards = arcuoToCard(detected_boards, lookupTable, unpairedTags, save, printedCards, sentToPrinter)

    return frame, sortedDetectedCards