<template>
  <div class="analysis-page container-fluid">
    <div class="page-header mb-3">
      <h1 class="display-5">地区疾病分析展示</h1>
      <p class="text-muted">按地区（四川、河南、北京、上海、广东）展示年龄/性别/季节/临床/社会活动等统计信息，支持单独或多选比较。</p>
    </div>

    <div class="row">
      <div class="col-12">
        <div class="card mb-3">
          <div class="card-body p-3">
            <div class="d-flex gap-2 align-items-center mb-2">
              <label class="mb-0">选择要展示的地区：</label>
              <div v-for="r in regionsList" :key="r" class="form-check form-check-inline">
                <input class="form-check-input" type="checkbox" :id="`chk-${r}`" v-model="activeRegions" :value="r">
                <label class="form-check-label" :for="`chk-${r}`">{{ r }}</label>
              </div>
              <button class="btn btn-sm btn-outline-primary ms-2" @click="selectAll">全选</button>
              <button class="btn btn-sm btn-outline-secondary ms-1" @click="clearAll">清除</button>
            </div>
            <small class="text-muted">点击下面任一地区卡片可以聚焦该地区（单独展示）。</small>
          </div>
        </div>
      </div>
    </div>

    <div class="row">
      <div v-for="reg in regionsList" :key="reg" class="col-lg-2 col-md-4 col-sm-6 mb-3">
        <div class="card h-100 region-card" @click="focusRegion(reg)">
          <div class="card-body">
            <h5 class="card-title">{{ reg }}</h5>
            <p class="card-text">总样本：<strong>{{ summaryByRegion[reg]?.total ?? '-' }}</strong></p>
            <p class="small text-muted">年龄/性别/季节/临床/社会因子统计</p>
            <div class="d-flex gap-1">
              <button class="btn btn-sm btn-outline-success" @click.stop="toggleInclude(reg)">{{ activeRegions.includes(reg) ? '移除' : '加入' }}</button>
              <button class="btn btn-sm btn-outline-primary" @click.stop="focusRegion(reg)">单独显示</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="row mt-3">
      <div class="col-12">
        <div class="card">
          <div class="card-body p-2">
            <New3 :regions-data="regionsData" :selected-regions.sync="activeRegions" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import New3 from '../components/new3.vue'

const regionsList = ['四川','河南','北京','上海','广东']
const activeRegions = ref([...regionsList])
const regionsData = ref([])
const summaryByRegion = reactive({})

function selectAll(){ activeRegions.value = [...regionsList] }
function clearAll(){ activeRegions.value = [] }

function toggleInclude(r){
  const idx = activeRegions.value.indexOf(r)
  if (idx === -1) activeRegions.value.push(r)
  else activeRegions.value.splice(idx,1)
}

function focusRegion(r){
  activeRegions.value = [r]
}

async function fetchAnalysis(){
  try{
    const q = regionsList.join(',')
    const res = await fetch(`/api/region_analysis?regions=${encodeURIComponent(q)}`)
    if (!res.ok) throw new Error('no')
    const data = await res.json()
    // backend may return English region names (e.g. 'Sichuan').
    // map them back to the Chinese labels used in the UI so selection/focus works.
    const enToCn = {
      'Sichuan':'四川','Henan':'河南','Beijing':'北京','Shanghai':'上海','Guangdong':'广东',
      'Jiangsu':'江苏','Zhejiang':'浙江','Shandong':'山东','Hunan':'湖南','Hubei':'湖北'
    }
    const normalized = (Array.isArray(data) ? data : (data.data || [])).map(item => {
      const r = item.region || item.region === 0 ? item.region : null
      const cn = enToCn[r] || r
      return { ...item, region: cn }
    })
    regionsData.value = normalized
    // build summary map keyed by Chinese region name
    for(const item of normalized){
      summaryByRegion[item.region] = item
    }
  }catch(e){
    console.warn('获取区域分析失败',e)
  }
}

onMounted(()=>{
  fetchAnalysis()
})
</script>

<style scoped>
.analysis-page { padding-bottom: 2rem }
.page-header { padding: 0.75rem 0 }
.region-card { cursor: pointer }
.region-card .card-body { min-height: 120px }
</style>