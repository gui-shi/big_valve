import os
import cv2
import ffmpeg
import numpy as np
from loguru import logger
from ultralytics import YOLO

model_path = os.path.split(os.path.realpath(__file__))

model = YOLO(os.path.join('models/best.pt'))

ORIGIN_WIDTH, ORIGIN_HIGH = 1920, 1080
CROP_WIDTH, CROP_HIGH = 960, 960
TARGET_WIDTH, TARGET_HIGH = 640, 640


def predict_stream(url: str, debug=False):
    frame_seq = 0

    while True:
        frame_seq += 1

        frame, err = ffmpeg \
            .input(filename=url, skip_frame='nokey', re=None) \
            .filter('select', 'eq(pict_type,I)') \
            .filter('scale', ORIGIN_WIDTH, ORIGIN_HIGH) \
            .filter('crop', CROP_WIDTH, CROP_HIGH, (ORIGIN_WIDTH - CROP_WIDTH) / 2,
                    (ORIGIN_HIGH - CROP_HIGH) / 2) \
            .filter('scale', TARGET_WIDTH, TARGET_HIGH) \
            .output('pipe:', vframes=1, format='rawvideo', pix_fmt='bgr24', loglevel="quiet") \
            .run(capture_stdout=True)
        if not frame:
            logger.error("Not frame!")
            continue

        # logger.info("Get frame here!")
        np_image = np.frombuffer(frame, np.uint8).reshape([TARGET_HIGH, TARGET_WIDTH, 3])

        #  cv2.imshow("show", np_image)
        #  cv2.waitKey()
        percent = predict.predict_np_image(np_image, frame_seq, debug=True)

        logger.info(f"frame:{frame_seq}, percent:{percent}")

        if percent is None:
            continue
        if percent < 0.55:
            logger.info("阀门全开")
        elif percent > 0.85:
            logger.info("阀门全闭")
        else:
            logger.info("阀门半开")


def predict_np_image(image: np.array, frame_id=-1, debug=False) -> float or None:
    results = model.predict(image, conf=0.6)

    if len(results) == 0:
        logger.warning("No valve detected.")
    elif len(results) != 1:
        logger.warning(f"Detected mult({len(results)}) result.")
    else:
        best_result = sorted(results, key=lambda result: result.boxes.conf, reverse=True)[0]

        masks = best_result.masks  # 分割掩码输出的 Masks 对象

        if masks is None:
            logger.warning("No valve mask in result.")
            return None

        all_mask = masks.data.cpu().numpy()

        valve_mask = all_mask[0].astype(np.uint8)

        mask_pixel = np.count_nonzero(valve_mask)
        # cv2.imwrite("result.bmp", valve_mask)

        contours, _ = cv2.findContours(valve_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) < 0:
            logger.error("No counters found.")
        else:
            # logger.info(f"contours = {len(contours)}")

            largest_contour = max(contours, key=cv2.contourArea)
            largest_contour = largest_contour.squeeze()
            # 拟合外接圆
            (x, y), radius = cv2.minEnclosingCircle(largest_contour)

            if debug:
                result_image = valve_mask.copy() * 255
                cv2.circle(result_image, (int(x), int(y)), int(radius), 128, 2)
                cv2.imwrite(f"test/{frame_id}_test_result.bmp", result_image)
                cv2.imwrite(f"test/{frame_id}_test.bmp", image)
            # 计算外接圆的面积
            circle_area = np.pi * (radius ** 2)
            percent = mask_pixel / circle_area

            # logger.info(f"阀门占比是{percent}")

            return percent
