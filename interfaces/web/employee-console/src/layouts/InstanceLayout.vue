<template>
  <SystemLayout />
</template>

<script setup>
// SystemLayout 同时承担 system / instance 两种 scope —— 根据 route.path 自动切换侧栏。
// InstanceLayout 这里是 vue-router 的 parent 标记，仅用于路由结构分组。
import SystemLayout from './SystemLayout.vue'
</script>
