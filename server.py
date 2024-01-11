import asyncio
import math
from typing import List, Literal

import cv2
import numpy
import websockets
import websockets.exceptions
from bitstring import BitArray
from loguru import logger

# 存储所有连接的客户端
clients = set()


async def start(host: str, port: int):
    logger.success(f"WS server listen on {host}, port {port}")
    async with websockets.serve(server, host, port):
        await asyncio.Future()


# 启动WebSocket服务器
async def server(websocket):
    logger.info(f"add websocket client {websocket}")
    clients.add(websocket)  # 添加客户端到集合中
    try:
        async for message in websocket:
            logger.info(f"Received message from {websocket}: {message}")
            await websocket.send("pong")

    except websockets.exceptions.ConnectionClosedError:
        # 客户端关闭连接
        logger.info(f"Remove websocket client {websocket}.")
        clients.remove(websocket)
    finally:
        pass


def package_images_result(percent_value: int,
                          images: List[tuple[Literal["webp", "jpg", "null"], numpy.array]]) -> bytes:
    """
    WebSocket 二进制包
                          |-------------------循环出现-------------------|
    | 百分比     | 图片数量 | 图片格式 | 图片长度        | 图片二进制         |
    | percent   | images  | format  | Content-Length | Binary of images |
    | 16bit     | 16bit   | 32bit   | 32bit          | val              |
    """
    byte_of_percent = 2
    byte_of_count = 2
    byte_of_format = 4
    byte_of_content_length = 4

    empty = 0x00

    binary_list = []
    for fmt, image in images:
        # 添加图片格式字段
        binary_list.append(fmt.encode("ascii").zfill(byte_of_format))
        if image is None:
            # 无图片，添加0作为长度
            binary_list.append(empty.to_bytes(byte_of_content_length, "big"))
        else:
            conv_result, coded_image = cv2.imencode(f".{fmt}", image)
            if not conv_result:
                # 转换失败，添加0作为长度
                logger.error("Image convert failed!")
                binary_list.append(empty.to_bytes(byte_of_content_length, "big"))
            else:
                # 转换成功，添加真实长度和二进制
                image_bin = coded_image.tobytes()
                image_len = len(image_bin).to_bytes(byte_of_content_length, "big")
                logger.info(f"Picture length: {image_len}")
                binary_list.append(image_len)
                binary_list.append(image_bin)

    logger.info(f"Add meta, image cnt: {len(images)}, percent: {percent_value}")
    binary_list.insert(0, len(images).to_bytes(byte_of_count, "big"))
    binary_list.insert(0, percent_value.to_bytes(byte_of_percent, "big"))
    image_bin_seq = b''.join(binary_list)
    return image_bin_seq


async def send_predict_result(percent_value: int, origin_img: numpy.array, masked_img: numpy.array):
    if percent_value is None:
        logger.error("Argument percent can not be None.")

    packet_bin = package_images_result(percent_value, [("jpg", origin_img), ("webp", masked_img)])

    logger.info(f"packet data, len:{len(packet_bin)}")

    for client in clients:
        try:
            logger.info(f"send message to {client.id}.")
            await client.send(packet_bin)
        except websockets.exceptions.ConnectionClosedError:
            # 处理连接已关闭的异常
            pass
