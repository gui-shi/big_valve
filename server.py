import asyncio
import math
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


def package_images_result(percent_value: float, origin_img: numpy.array, masked_img: numpy.array) -> bytes:
    """
    Websocket 二进制包
    | 百分比     | 原图长度                      | 掩码图长度                 | 原图二进制 | 掩码图二进制 |
    | percent   | Content-Length of origin     | Content-Length of masked  | origin    | masked    |
    | 16bit     | 32bit                        | 32bit                     | val     | val        |
    """
    bit_of_percent = 16
    bit_of_content_length = 32
    origin_convert, origin_img_bin = cv2.imencode(".jpg", origin_img)
    masked_convert, masked_img_bin = cv2.imencode(".webp", masked_img)

    if not origin_convert:
        logger.error(f"origin image convert failed!")
    if not masked_convert:
        logger.error(f"masked image convert failed!")

    origin_img_bin = origin_img_bin.tobytes()
    masked_img_bin = masked_img_bin.tobytes()

    origin_img_len = len(origin_img_bin)
    masked_img_len = len(masked_img_bin)

    if origin_img_len == 0:
        logger.warning("origin image size 0")
    if masked_img_len == 0:
        logger.warning("masked image size 0")

    metadata_bin = BitArray(
        (f'int:{bit_of_percent}={percent_value},'
         f'int:{bit_of_content_length}={origin_img_len},'
         f'int:{bit_of_content_length}={masked_img_len}'))

    packet_bin = (metadata_bin + BitArray(bytes=origin_img_bin) + BitArray(bytes=masked_img_bin)).tobytes()
    return packet_bin


async def send_predict_result(percent_value: int, origin_img: numpy.array, masked_img: numpy.array):
    if percent_value is None:
        logger.error("Argument percent can not be None.")

    packet_bin = package_images_result(percent_value, origin_img, masked_img)

    logger.info(f"packet data, len:{len(packet_bin)}")

    for client in clients:
        try:
            logger.info(f"send message to {client.id}.")
            await client.send(packet_bin)
        except websockets.exceptions.ConnectionClosedError:
            # 处理连接已关闭的异常
            pass
