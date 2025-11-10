<template>
  <Layout />
</template>

<script setup>
import Layout from './components/Layout.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  width: 100%;
  height: 100%;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f8f9fa;
  position: relative;
}

#app {
  width: 100vw !important;
  height: 100vh !important;
  margin: 0 !important;
  padding: 0 !important;
  position: relative !important;
  max-width: none !important;
  display: block !important;
  grid-template-columns: none !important;
}

body {
  display: block !important;
  place-items: initial !important;
}

/* Bootstrap 覆盖样式 */
.container-fluid {
  max-width: none;
  padding: 0;
}

.row {
  margin: 0;
  width: 100%;
}

[class*="col-"] {
  padding-left: 15px;
  padding-right: 15px;
}
</style>
