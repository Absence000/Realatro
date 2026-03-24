import cv2
import numpy as np


def generateBoardForCard(num):
    num = str(num).zfill(4)
    idArray = [num[:2], num[2:]]

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
    # 1 row 2 column grid board
    board = cv2.aruco.GridBoard(size=(1, 2),
                                markerLength=.04,
                                markerSeparation=.01,
                                dictionary=aruco_dict,
                                ids=np.array(idArray, dtype=np.int32))

    boardImage = board.generateImage(outSize=(400, 900), marginSize=0)

    # the margins are being annoying so I just made them have a margin size of 0 and added the border manually
    borderSize = 40
    boardImage = cv2.copyMakeBorder(
        boardImage,
        top=borderSize,
        bottom=borderSize,
        left=borderSize,
        right=borderSize,
        borderType=cv2.BORDER_CONSTANT,
        value=(255, 255, 255)
    )

    boardImage = cv2.resize(boardImage, (96, 196))
    # TODO: eventually change this to turn the cv2 into pil automatically but idk how to do that
    cv2.imwrite("testBoard.png", boardImage)

def correctID(id):
    if id == 0:
        return "00"
    else:
        return str(id).zfill(2)