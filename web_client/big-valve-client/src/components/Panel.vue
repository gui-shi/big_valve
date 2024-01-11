<template>
  <v-container>
    <v-card>
      <v-card-title class="bg-cyan">
        <v-icon>mdi-chart-box-outline</v-icon>
        实时图像
      </v-card-title>
      <v-card-text class="my-4">
        <v-row>
          <v-col v-for="url in imageUrlList" :cols="6">
            <v-sheet border>
              <v-img width="100%" :src="url"></v-img>
            </v-sheet>
          </v-col>
        </v-row>
        <v-row style="height: 240px">
          <v-col :cols="8">
            <v-card height="100%">
              <v-card-title :class="status_table[valveStatus]['color']">
                <v-icon>{{ status_table[valveStatus]['icon'] }}</v-icon>
                阀门状态
              </v-card-title>
              <v-card-text class="my-2">
                <div v-if="websocketConnected">
                  <p class="text-body-1">闭合度：{{ percent / 10 }} %</p>
                  <v-progress-linear color="teal" rounded :model-value="percent/10" :height="24"></v-progress-linear>
                  <v-divider :thickness="2" class="my-2"></v-divider>
                  <p class="text-body-1">当前状态：
                    {{ status_table[valveStatus]['text'] }}
                  </p>
                </div>
                <div v-else>
                  <v-alert
                    icon="mdi-lan-disconnect"
                    title="未知状态"
                    text="当前未建立连接，无法获取"
                    type="warning"
                  ></v-alert>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col :cols="4">
            <v-card height="100%">
              <v-card-title :class="connectedColor">
                <v-icon>{{ connectedIcon }}</v-icon>
                交互状态
              </v-card-title>
              <v-card-text>
                <p class="text-body-1">Message Count: {{ msgCounter }} times predict</p>
                <p class="text-body-1">Origin Content-Length: {{ originImageLen }} bytes</p>
                <p class="text-body-1">Masked Content-Length: {{ maskedImageLen }} bytes</p>
                <p class="text-body-1">WebSocket: {{ websocketConnected ? "connected" : "disconnected" }}</p>
              </v-card-text>
              <v-card-actions>
                <v-btn variant="flat" @click="handleConnectClick()" :disabled="websocketConnected" color="blue"
                       append-icon="mdi-connection">连接
                </v-btn>
                <v-btn variant="flat" @clickh="handleDisconnectClick()" :disabled="!websocketConnected" color="warning"
                       append-icon="mdi-close">断开
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
export default {
  name: "Panel",
  data() {
    return {
      socket: null,
      websocketPort: 9331,
      websocketConnected: false,
      percent: 1101, // 1000 到 1150 是没有数据
      msgCounter: 0,
      originImageLen: 0,
      maskedImageLen: 0,
      imageUrlList: ['/PM5544.webp', '/PM5544.webp'],
      originImageUrl: '/PM5544.webp',
      maskedImageUrl: '/PM5544.webp',
      status_table: [
        {text: '全开', icon: 'mdi-valve-open', color: 'bg-red'},
        {text: '大开', icon: 'mdi-valve-closed', color: 'bg-blue'},
        {text: '小开', icon: 'mdi-valve', color: 'bg-cyan'},
        {text: '闭合', icon: 'mdi-valve-closed', color: 'bg-green'},
        {text: '未知', icon: 'mdi-cloud-question', color: 'bg-deep-orange'}]
    };
  },
  computed: {
    connectedIcon() {
      if (this.websocketConnected)
        return "mdi-lan-connect"
      else
        return "mdi-lan-disconnect"
    },
    connectedColor() {
      if (this.websocketConnected)
        return "bg-green"
      else
        return "bg-deep-orange"
    },
    valveStatus() {
      return Math.floor((this.percent - 450) / 150);
    }
  },
  mounted() {
    this.initWebSocket();
  },
  methods: {
    handleConnectClick() {
      this.initWebSocket();
    },
    handleDisconnectClick() {
      this.socket.close();
    },
    handleDisconnect() {
      this.websocketConnected = false;
      this.originImageUrl = 'PM5544.webp';
      this.maskedImageUrl = 'PM5544.webp';
    },
    handleBinaryMessage(event) {
      this.msgCounter++;
      if (event.data instanceof Blob) {
        let binaryData = new ArrayBuffer(0);
        const reader = new FileReader();
        reader.onload = () => {
          binaryData = reader.result;
          /*
          * WebSocket 二进制包 / gui-shi protocol packet format.
          *                          |-------------------循环出现-------------------|
          *    | 百分比     | 图片数量 | 图片格式 | 图片长度        | 图片二进制         |
          *    | percent   | images  | format  | Content-Length | Binary of images |
          *    | 16bit     | 16bit   | 32bit   | 32bit          | val              |
          *    | 2byte     | 2byte   | 4byte   | 4byte          | val              |
          * */

          console.log(`Receive data from ws, length: ${binaryData.byteLength}`)

          // 解码头数据
          const binaryView = new DataView(binaryData);
          this.percent = binaryView.getUint16(0);
          const imageCount = binaryView.getUint16(2);

          console.log(`Unpacked. percent: ${this.percent}, image cnt: ${imageCount}`);

          // 解码第一个图片
          const decoder = new TextDecoder('ascii');

          const imageList = [];

          let seek = 4; // 跳过推理结果和图片数量字段

          for (let i = 0; i < imageCount; i++) {
            const imageFormat = decoder.decode(binaryData.slice(seek, seek += 4));
            const imageLength = binaryView.getUint32(seek);
            seek += 4;
            let imageBlob = null;

            if (imageLength !== 0) {
              imageBlob = this.binaryToBlobImage(
                binaryData, seek, imageLength, imageFormat
              );
            }

            seek += imageLength;
            imageList.push({length: imageLength, image: imageBlob});
          }

          this.originImageLen = imageList[0].length
          this.maskedImageLen = imageList[0].length

          for (let i = 0; i < imageList.length; i++) {
            if (imageList[i].length === 0) {
              continue;
            }

            if (this.imageUrlList[i].startsWith("blob")) {
              URL.revokeObjectURL(this.imageUrlList[i])
            }

            this.imageUrlList[i] = URL.createObjectURL(imageList[i].image);
          }
        };
        reader.readAsArrayBuffer(event.data);
      }
    },
    binaryToBlobImage(binaryData, offset, length, type) {
      const imageBin = binaryData.slice(offset, offset + length);
      return new Blob([imageBin], {type: `image/${type}`});
    },
    initWebSocket() {
      const socketUrl = `ws://localhost:${this.websocketPort}`;
      this.socket = new WebSocket(socketUrl);

      this.socket.addEventListener("open", (event) => {
        console.log("WebSocket连接已打开", event);
        this.socket.send("hello");
        this.websocketConnected = true;
      });

      this.socket.addEventListener("message", this.handleBinaryMessage);

      this.socket.addEventListener("close", (event) => {
        console.log("WebSocket连接已关闭", event);
        this.handleDisconnect()
      });

      this.socket.addEventListener("error", (event) => {
        console.error("WebSocket连接发生错误", event);
        this.handleDisconnect()
      });
    }
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.close();
    }
  },
};
</script>
