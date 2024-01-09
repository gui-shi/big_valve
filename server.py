import asyncio
import math
import cv2
import numpy
import websockets
import websockets.exceptions
from bitstring import BitArray
from loguru import logger

# 存储所有连接的客户端
sockets = set()


async def start(host: str, port: int):
    logger.success(f"WS server listen on {host}, port {port}")
    async with websockets.serve(server, host, port):
        await asyncio.Future()


# 启动WebSocket服务器
async def server(websocket):
    # 添加新连接的客户端到集合中
    logger.info(f"add websocket client {websocket}")
    sockets.add(websocket)
    try:
        # 循环监听客户端消息
        async for message in websocket:
            # 在服务器端打印接收到的消息
            logger.info(f"Received message from {websocket}: {message}")
            await websocket.send("pong")
            # 如果有需要，可以在这里处理接收到的消息

    except websockets.exceptions.ConnectionClosedError:
        # 从集合中移除已关闭连接的客户端
        logger.info(f"remove websocket client {websocket}.")
        sockets.remove(websocket)
    finally:
        pass


async def send_predict_result(percent: float, origin_img: numpy.array, masked_img: numpy.array):
    percent_in_int = math.floor(percent * 1000 + 0.5)

    """
    | 百分比     | 原图长度                      | 掩码图长度                 | 原图二进制 | 掩码图二进制 |
    | percent   | Content-Length of origin     | Content-Length of masked  | origin    | masked    |
    | 16bit     | 32bit                        | 32bit                     | val     | val        |
    """

    bit_of_percent = 16
    bit_of_content_length = 32

    origin_convert, origin_img_bin = cv2.imencode(".jpg", origin_img)
    masked_convert, masked_img_bin = cv2.imencode(".jpg", masked_img)

    if not origin_convert:
        logger.error(f"origin image convert failed!")
    if not masked_convert:
        logger.error(f"masked image convert failed!")

    origin_img_bin = origin_img_bin.tobytes()
    masked_img_bin = masked_img_bin.tobytes()

    # with open('output.jpg', 'wb') as file:
    #     file.write(masked_img_bin)

    origin_img_len = len(origin_img_bin)
    masked_img_len = len(masked_img_bin)

    if origin_img_len == 0:
        logger.error("origin image size 0")
        return
    if masked_img_len == 0:
        logger.error("masked image size 0")

    metadata_bin = BitArray(
        (f'int:{bit_of_percent}={percent_in_int}, '
         f'int:{bit_of_content_length}={origin_img_len}, '
         f'int:{bit_of_content_length}={masked_img_len}'))

    # logger.info(f"metadata: {metadata_bin.bin}")

    packet_bin = (metadata_bin + BitArray(bytes=origin_img_bin) + BitArray(bytes=masked_img_bin)).tobytes()

    logger.info(f"packet data, len:{len(packet_bin)}")

    # 遍历所有连接的客户端，发送消息
    logger.info(f"send message to {len(sockets)} clients.")
    for client in sockets:
        try:
            await client.send(packet_bin)
        except websockets.exceptions.ConnectionClosedError:
            # 处理连接已关闭的异常
            pass
