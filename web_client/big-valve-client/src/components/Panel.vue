<template>
  <v-container>
    <v-card>
      <v-card-title>
        实时状态
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col :cols="6">
            <v-sheet border>
              <v-img width="100%" :src="this.originImageUrl"></v-img>
            </v-sheet>
          </v-col>
          <v-divider vertical=""></v-divider>
          <v-col :cols="6">
            <v-sheet border>
              <v-img width="100%" :src="this.maskedImageUrl"></v-img>
            </v-sheet>
          </v-col>
        </v-row>
        <v-row>
          <v-col :cols="8">
            <v-card title="阀门状态">
              <v-card-text>
                <p class="text-body-1">闭合度：{{ percent / 10 }} %</p>
                <v-progress-linear color="primary" rounded :model-value="percent/10" :height="24"></v-progress-linear>
                <v-divider :thickness="2" class="my-2"></v-divider>
                <p class="text-body-1">当前状态：
                  <v-icon>{{ status_table[valveStatus]['icon'] }}</v-icon>
                  {{ status_table[valveStatus]['text'] }}
                </p>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col :cols="4">
            <v-card title="数据状态">
              <v-card-text>
                <p class="text-body-1">message count: {{ msgCounter }}</p>
                <p class="text-body-1">origin Content-Length: {{ originImageLen }}</p>
                <p class="text-body-1">masked Content-Length: {{ maskedImageLen }}</p>
                <p>sys time: {{ new Date().toLocaleTimeString()}}</p>
              </v-card-text>
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
      percent: 0,
      msgCounter: 0,
      originImageLen: 0,
      maskedImageLen: 0,
      originImageUrl: '',
      maskedImageUrl: '',
      status_table: [
        {text: '闭合', icon: 'mdi-valve-closed'},
        {text: '半开', icon: 'mdi-valve'},
        {text: '全开', icon: 'mdi-valve-open'}]
    };
  },
  computed: {
    valveStatus() {
      if (this.percent < 550)
        return 2;
      else if (this.percent > 850)
        return 0;
      else
        return 1;
    }
  },
  mounted() {
    this.initWebSocket();
  },
  methods: {
    handleBinaryMessage(event) {
      this.msgCounter++;
      if (event.data instanceof Blob) {
        let binaryData;
        const reader = new FileReader();
        reader.onload = () => {
          binaryData = reader.result;

          const binaryView = new DataView(binaryData);
          this.percent = binaryView.getUint16(0);
          this.originImageLen = binaryView.getUint32(2); // 0+16=16/8=2
          this.maskedImageLen = binaryView.getUint32(6); // 16+32=48/8=6

          const originImageBin = binaryData.slice(10, this.originImageLen); // 48+32=80/8=10
          const maskedImageBin = binaryData.slice(this.originImageLen + 10, this.originImageLen + 10 + this.maskedImageLen);

          const originImage = new Blob([originImageBin], {type: 'image/jpeg'});
          const maskedImage = new Blob([maskedImageBin], {type: 'image/jpeg'});

          if (this.originImageUrl) {
            URL.revokeObjectURL(this.originImageUrl);
          }
          if (this.maskedImageUrl) {
            URL.revokeObjectURL(this.maskedImageUrl);
          }

          this.originImageUrl = URL.createObjectURL(originImage);
          this.maskedImageUrl = URL.createObjectURL(maskedImage);

          console.log("originUrl:" + this.originImageUrl);
          console.log("maskedUrl:" + this.maskedImageUrl);
        };
        reader.readAsArrayBuffer(event.data);
      }
    },

    initWebSocket() {
      const socketUrl = `ws://localhost:${this.websocketPort}`;
      this.socket = new WebSocket(socketUrl);

      this.socket.addEventListener("open", (event) => {
        console.log("WebSocket连接已打开", event);
        this.socket.send("hello")
      });

      this.socket.addEventListener("message", this.handleBinaryMessage);

      this.socket.addEventListener("close", (event) => {
        console.log("WebSocket连接已关闭", event);
      });

      this.socket.addEventListener("error", (event) => {
        console.error("WebSocket连接发生错误", event);
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
