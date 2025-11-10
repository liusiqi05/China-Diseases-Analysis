<template>
  <div class="page-fullscreen">
    <div class="page-split">
      <div class="left-panel">
          <MapPieChart @place-selected="onPlaceSelected" />
      </div>
      <div class="right-panel">
          <ChatPanel :selected-place="selectedPlace" />
      </div>
    </div>
  </div>
</template>

<script setup>
  import MapPieChart from '../components/MapPieChart.vue'
  import ChatPanel from '../components/ChatPanel.vue'
  import { ref } from 'vue'

  // 父组件维护 selectedPlace 并传递给 ChatPanel；MapPieChart 会触发 place-selected 事件
  const selectedPlace = ref(null)
  function onPlaceSelected(p) { selectedPlace.value = p }
</script>

<style scoped>
.page-fullscreen {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  /* Background image (placed in public/echarts-assets). Replace path if you add a custom image. */
  background-image: url('/echarts-assets/test2.jpg');
  background-size: cover;
  background-position: center center;
  background-repeat: no-repeat;
}
.page-split {
  position: absolute;
  inset: 0;
  display: flex;
  z-index: 1;
}
.left-panel {
  flex: 1 1 auto;
  min-width: 600px; /* ensure map has room */
  height: 100%;
  padding: 12px;
}
.right-panel {
  width: 360px; /* reserved area for chat */
  height: 100%;
  padding: 12px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

/* a subtle dark overlay so charts and UI remain readable */
.page-fullscreen::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(20,20,20,0.45);
  z-index: 0;
}
</style>