import os
import cv2
import numpy as np
from loguru import logger
from ultralytics import YOLO

model_path = os.path.split(os.path.realpath(__file__))

model = YOLO(os.path.join('models/best.pt'))


def get_valve_percent(image: np.array, debug=False) -> float:
    results = model.predict(image, show=debug)
    if debug:
        cv2.waitKey()

    if len(results) == 0:
        logger.warning("No valve detected.")
    else:
        logger.info(f"Detected {len(results)} result.")

        boxes = results[0].boxes  # 边界框输出的 Boxes 对象
        masks = results[0].masks  # 分割掩码输出的 Masks 对象
        key_points = results[0].keypoints  # 姿态输出的 Keypoints 对象
        probs = results[0].probs  # 分类输出的 Probs 对象

        all_mask = masks.data.cpu().numpy()

        valve_mask = all_mask[0].astype(np.uint8) * 255

        mask_pixel = np.count_nonzero(valve_mask)
        cv2.imwrite("result.bmp", valve_mask)

        contours, _ = cv2.findContours(valve_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) < 0:
            logger.error("No counters found.")
        else:
            logger.info(f"contours = {len(contours)}")

            largest_contour = max(contours, key=cv2.contourArea)
            largest_contour = largest_contour.squeeze()
            # 拟合外接圆
            (x, y), radius = cv2.minEnclosingCircle(largest_contour)

            result_image = valve_mask.copy()
            cv2.circle(result_image, (int(x), int(y)), int(radius), 128, 2)
            cv2.imwrite("result2.bmp", result_image)

            # 计算外接圆的面积
            circle_area = np.pi * (radius ** 2)
            percent = mask_pixel / circle_area
            logger.info(f"阀门的总像素是{circle_area}")

            logger.info(f"阀门占比是{percent}")

            return percent
