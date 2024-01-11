from typing import List
import numpy as np
import cv2


def binarized_to_color(origin_image: np.array, zero_color: List[int], value_color: List[int]) -> np.array:
    color_image = cv2.cvtColor(origin_image, cv2.COLOR_GRAY2RGB)
    color_image[origin_image == 0] = zero_color
    color_image[origin_image == 1] = value_color

    return color_image
