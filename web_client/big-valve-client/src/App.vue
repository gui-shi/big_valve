<template>
  <v-app>
    <v-app-bar color="primary" :elevation="2">
      <v-app-bar-nav-icon>
        <v-icon>mdi-valve</v-icon>
      </v-app-bar-nav-icon>
      <v-app-bar-title>阀门状态监测终端</v-app-bar-title>
    </v-app-bar>
    <v-main>
      <Panel/>
    </v-main>
    <v-footer>LICENSE under GPLv3, github.com/gui-shi/big_valve</v-footer>
  </v-app>
</template>

<script setup>
//
import Panel from "@/components/Panel.vue";
</script>
