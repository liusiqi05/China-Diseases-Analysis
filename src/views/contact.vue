<template>
  <div class="row mb-4">
  <div class="col-12">
      <div class="card border-0 shadow-sm mb-4">
        <div class="card-header bg-white">
          <h5 class="mb-0">十省犯病人数总览</h5>
        </div>
        <div class="card-body">
          <TrendChart />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import TrendChart from '../components/TrendChart.vue'
</script>

<style scoped>
/* minimal styles retained if needed */
.card { background: transparent }
</style>