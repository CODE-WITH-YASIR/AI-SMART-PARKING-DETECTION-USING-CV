"""
util.py
Recreated exactly from the logic found in Copy_of_priject_2.ipynb
(cells: "Load SVM model" / "Find parking slot regions" / predict_slot()).

Do NOT change the connectivity (8), the resize target (15,15,3),
or the label convention (0 = Empty, 1 = Occupied) — these must match
the model.p that was trained on this exact pipeline.
"""

import os
import pickle
import cv2
import numpy as np
from skimage.transform import resize

EMPTY = 0
NOT_EMPTY = 1

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.p")

# ---- Load SVM model (exactly as in the notebook) ----
with open(MODEL_PATH, "rb") as f:
    MODEL = pickle.load(f)


def get_parking_spots_bboxes(mask_path):
    """
    Reproduces the notebook's "Find parking slot regions" cell:
        mask = cv2.imread(mask_path, 0)
        connected_components = cv2.connectedComponentsWithStats(mask, 8)
    Returns a list of [x, y, w, h] boxes, one per parking slot.
    """
    mask = cv2.imread(mask_path, 0)

    connected_components = cv2.connectedComponentsWithStats(mask, 8)
    totalLabels, label_ids, values, centroid = connected_components

    parking_slots = []
    for i in range(1, totalLabels):
        x = int(values[i, cv2.CC_STAT_LEFT])
        y = int(values[i, cv2.CC_STAT_TOP])
        w = int(values[i, cv2.CC_STAT_WIDTH])
        h = int(values[i, cv2.CC_STAT_HEIGHT])
        parking_slots.append([x, y, w, h])

    return parking_slots


def empty_or_not(slot_img):
    """
    Reproduces the notebook's predict_slot() function.
    slot_img: BGR crop of a single parking spot (numpy array, HxWx3).
    Returns EMPTY (0) or NOT_EMPTY (1).
    """
    img_resized = resize(slot_img, (15, 15, 3))
    features = np.array([img_resized.flatten()])

    prediction = MODEL.predict(features)

    if prediction[0] == 0:
        return EMPTY
    else:
        return NOT_EMPTY
