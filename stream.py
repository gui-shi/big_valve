import ffmpeg
import cv2
import numpy as np
from loguru import logger


def stream_to_result(url: str):
    frame_num = 0

    # .filter('select', 'gte(n,{})'.format(frame_num)) \

    while True:
        stream = ffmpeg \
            .input(filename=url, skip_frame='nokey', re=None) \
            .filter('select', 'eq(pict_type,I)') \
            .output('pipe:', vframes=1, format='rawvideo', pix_fmt='rgb24')
        frame, err = stream.run(capture_stdout=True)
        if not frame:
            logger.error("Not frame!")
            frame_num += 1
            break

        logger.info("Get frame here!")
        np_image = np.frombuffer(frame, np.uint8).reshape([720, 1280, 3])

        cv2.imshow("show", np_image)
        cv2.waitKey()

        frame_num += 1
