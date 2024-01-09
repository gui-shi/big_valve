import predict
import server
import asyncio


async def main():
    STREAM_ADDR = "rtsp://v4-cn-bj3.gaein.cn:8554/live/livestream"

    websocket_service = asyncio.create_task(server.start("0.0.0.0", 9331))
    predict_service = asyncio.create_task(predict.predict_stream(STREAM_ADDR))

    try:
        await asyncio.gather(websocket_service, predict_service)
    except KeyboardInterrupt:
        print("Cancelled by user.")
        websocket_service.cancel()
        #    predict_service.cancel()
        #  await asyncio.gather(websocket_service, predict_service, return_exceptions=True)


asyncio.run(main())
