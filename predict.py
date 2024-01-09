import asyncio
import hashlib
import os
import cv2
import ffmpeg
import numpy as np
from loguru import logger
from ultralytics import YOLO

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

    while True:
        frame_seq += 1

        # frame, err = await asyncio.to_thread(process.communicate)
        # frame = process.stdout.read(TARGET_WIDTH * TARGET_HIGH * 3)

        # err = process.stderr.readline()
        # if err:
        # logger.error(err)
        # process.stdout.seek(TARGET_WIDTH * TARGET_HIGH * 3)

        frame, err = ffmpeg \
            .input(filename=url, re=None) \
            .filter('select', 'eq(pict_type,I)') \
            .filter('scale', ORIGIN_WIDTH, ORIGIN_HIGH) \
            .filter('crop', CROP_WIDTH, CROP_HIGH, (ORIGIN_WIDTH - CROP_WIDTH) / 2,
                    (ORIGIN_HIGH - CROP_HIGH) / 2) \
            .filter('scale', TARGET_WIDTH, TARGET_HIGH) \
            .output('pipe:', vframes=1, format='rawvideo', pix_fmt='bgr24', loglevel='error') \
            .run(capture_stdout=True)

        if not frame:
            logger.error("Not frame!")
            continue

        logger.info(hashlib.md5(frame).hexdigest())

        np_image = np.frombuffer(frame, np.uint8).reshape([TARGET_HIGH, TARGET_WIDTH, 3])

        # cv2.imshow("ffmpeg output frame", np_image)
        # cv2.waitKey()

        percent = await predict_np_image(np_image, frame_seq, debug=debug)

        logger.info(f"frame:{frame_seq}, percent:{percent}")
        await asyncio.sleep(1)


async def predict_np_image(image: np.array, frame_id=-1, debug=False) -> float or None:
    results = model.predict(image, conf=0.6, stream=True)

    result_list = []
    for result in results:
        result_list.append(result)

    if len(result_list) == 0:
        logger.warning("No valve detected.")
    elif len(result_list) != 1:
        logger.warning(f"Detected mult({len(result_list)}) result.")
    else:
        best_result = sorted(result_list, key=lambda sig_result: sig_result.boxes.conf, reverse=True)[0]

        masks = best_result.masks  # 分割掩码输出的 Masks 对象

        if masks is None:
            logger.warning("No valve mask in result.")
            return None

        valve_mask = masks.data.cpu().numpy()[0].astype(np.uint8)

        mask_pixel = np.count_nonzero(valve_mask)

        # 计算轮廓
        contours, _ = cv2.findContours(valve_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) < 0:
            logger.error("No counters found.")
        else:
            # logger.info(f"contours = {len(contours)}")

            largest_contour = max(contours, key=cv2.contourArea)
            largest_contour = largest_contour.squeeze()
            # 根据轮廓计算外接圆
            (x, y), radius = cv2.minEnclosingCircle(largest_contour)
            valve_mask_result = valve_mask.copy() * 255
            # 在图形上绘制外接圆
            cv2.circle(valve_mask_result, (int(x), int(y)), int(radius), 255, 2)
            if debug:
                cv2.imwrite(f"test/{frame_id}_result.bmp", valve_mask_result)
                cv2.imwrite(f"test/{frame_id}.bmp", image)
            # 计算外接圆的面积
            circle_area = np.pi * (radius ** 2)
            percent = mask_pixel / circle_area

            # cv2.imshow("test", best_result.plot())
            # cv2.waitKey()

            await server.send_predict_result(percent, best_result.orig_img, valve_mask_result)

            logger.success(f"Open percent is: {percent:.3%}")

            return percent
