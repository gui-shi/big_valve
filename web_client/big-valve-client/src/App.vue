<template>
  <v-app>
    <v-app-bar color="teal" :elevation="2">
      <v-app-bar-nav-icon>
        <v-icon>mdi-ghost</v-icon>
        <v-icon>mdi-emoticon-poop</v-icon>
      </v-app-bar-nav-icon>
      <v-app-bar-title>阀门状态监测终端</v-app-bar-title>
    </v-app-bar>
    <v-main>
      <Panel/>
    </v-main>
    <v-footer :elevation="2">
      <span class="text-body-1">B<span class="text-purple">iiiiiiii</span>g valve powered by 小店王 & 緒山かやね</span>
    </v-footer>
  </v-app>
</template>

<script setup>
//
import Panel from "@/components/Panel.vue";
</script>
