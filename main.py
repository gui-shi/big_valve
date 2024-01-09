import predict

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    STREAM_ADDR = "rtsp://192.168.23.23:8554/stream0"

    predict.predict_stream(STREAM_ADDR)
