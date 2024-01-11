import asyncio
import math
import os
import cv2
import ffmpeg
import numpy as np
from loguru import logger
from ultralytics import YOLO

import image_utils
import server

model_path = os.path.split(os.path.realpath(__file__))

model = YOLO(os.path.join('models/best.pt'))

ORIGIN_WIDTH, ORIGIN_HIGH = 1920, 1080
CROP_WIDTH, CROP_HIGH = 1080, 1080
TARGET_WIDTH, TARGET_HIGH = 640, 640


async def predict_stream(url: str, debug=False):
    frame_seq = 0

    # process = (ffmpeg
    #            .input(filename=url, rtsp_transport='tcp', re=None)
    #            .filter('select', 'eq(pict_type,I)')
    #            .filter('scale', ORIGIN_WIDTH, ORIGIN_HIGH)
    #            .filter('crop', CROP_WIDTH, CROP_HIGH, (ORIGIN_WIDTH - CROP_WIDTH) / 2,
    #                    (ORIGIN_HIGH - CROP_HIGH) / 2)
    #            .filter('scale', TARGET_WIDTH, TARGET_HIGH)
    #            .output('pipe:', format='rawvideo', pix_fmt='bgr24')
    #            .run_async(pipe_stdout=True, pipe_stderr=True))

    stream = ffmpeg \
        .input(filename=url, re=None) \
        .filter('select', 'eq(pict_type,I)') \
        .filter('scale', ORIGIN_WIDTH, ORIGIN_HIGH) \
        .filter('crop', CROP_WIDTH, CROP_HIGH, (ORIGIN_WIDTH - CROP_WIDTH) / 2,
                (ORIGIN_HIGH - CROP_HIGH) / 2) \
        .filter('scale', TARGET_WIDTH, TARGET_HIGH) \
        .output('pipe:', vframes=1, format='rawvideo', pix_fmt='bgr24', loglevel='error')
    while True:
        frame_seq += 1

        # frame, err = await asyncio.to_thread(process.communicate)
        # frame = process.stdout.read(TARGET_WIDTH * TARGET_HIGH * 3)

        # err = process.stderr.readline()
        # if err:
        # logger.error(err)
        # process.stdout.seek(TARGET_WIDTH * TARGET_HIGH * 3)

        frame, err = stream.run(capture_stdout=True)

        if err:
            logger.error(err)
        if not frame:
            logger.error("No frame received!")
            continue
        logger.info(f"frame size {len(frame)}, target size {TARGET_HIGH * TARGET_WIDTH * 3}")

        np_image = np.frombuffer(frame, np.uint8).reshape([TARGET_HIGH, TARGET_WIDTH, 3])

        # cv2.imshow("ffmpeg output frame", np_image)
        # cv2.waitKey()

        mask = await predict_np_image_to_mask(np_image)
        percent_value = 1100

        if mask is None:
            await server.send_predict_result(percent_value, np_image, None)

        percent, color_mask_image = await result(mask)

        if percent is not None:
            percent_value = math.floor(percent * 1000 + 0.5)

        await server.send_predict_result(percent_value, np_image, color_mask_image)

        logger.info(f"frame:{frame_seq}, percent:{percent}")
        await asyncio.sleep(0.5)


async def result(mask: np.array, debug=False) -> (float or None, np.array):
    mask_pixel_cnt = np.count_nonzero(mask)

    # 计算轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) <= 0:
        logger.error("No counters found.")
        return None, None
    else:
        largest_contour = max(contours, key=cv2.contourArea)
        largest_contour = largest_contour.squeeze()
        # 根据轮廓计算外接圆
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        mask_whit_round = mask.copy()
        # 在图形上绘制外接圆
        cv2.circle(mask_whit_round, (int(x), int(y)), int(radius), 1, 2)
        color_mask_image = image_utils.binarized_to_color(mask_whit_round, [0xF2, 0xEB, 0xB2], [0xBB, 0xC5, 0x39])
        # if debug:
        #     cv2.imwrite(f"test/_result.jpg", color_mask_image)
        # 计算外接圆的面积
        circle_area = np.pi * (radius ** 2)
        percent = mask_pixel_cnt / circle_area
        # cv2.imshow("test", best_result.plot())
        # cv2.waitKey()
        logger.success(f"Open percent is: {percent:.3%}")
        return percent, color_mask_image


async def predict_np_image_to_mask(image: np.array) -> np.array or None:
    results = model.predict(image, conf=0.6, stream=True)

    # 过滤推理结果
    result_list = []
    for predict_result in results:
        result_list.append(predict_result)

    if len(result_list) == 0:
        logger.warning("No valve detected.")
        return None
    elif len(result_list) != 1:
        logger.warning(f"Detected mult({len(result_list)}) result.")

    best_result = sorted(result_list, key=lambda sig_result: sig_result.boxes.conf, reverse=True)[0]

    # 过滤结果中的掩膜
    result_masks = best_result.masks  # 分割掩码输出的 Masks 对象
    if result_masks is None:
        logger.warning("No valve mask in result.")
        return None

    # 掩膜对象
    mask = result_masks.data.cpu().numpy()[0].astype(np.uint8)

    return mask
