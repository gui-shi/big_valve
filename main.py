import predict
import server
import asyncio


async def main():
    STREAM_ADDR = "rtsp://192.168.1.101:8554/stream0"

    websocket_service = asyncio.create_task(server.start("0.0.0.0", 9331))
    # predict_service = asyncio.create_task(predict.predict_stream(STREAM_ADDR, debug=True))
    predict_service = asyncio.create_task(predict.predict_stream(STREAM_ADDR))
    try:
        await asyncio.gather(websocket_service, predict_service)
    except KeyboardInterrupt:
        print("Cancelled by user.")
        websocket_service.cancel()
        #    predict_service.cancel()
        #  await asyncio.gather(websocket_service, predict_service, return_exceptions=True)


asyncio.run(main())
