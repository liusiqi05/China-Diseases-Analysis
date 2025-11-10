<template>
  <div class="map-pie-wrapper">
    <div class="controls">
      <div class="controls-title">选择要展示的疾病（勾选）：</div>
      <div class="checkbox-list">
        <label v-for="cat in diseaseCategories" :key="cat" class="checkbox-item">
          <input type="checkbox" v-model="selectedMap[cat]" />
          <span class="swatch" :style="{ background: getColor(cat) }"></span>
          <span class="cat-label">{{ displayDiseaseName(cat) }}</span>
        </label>
      </div>
      <div class="controls-actions">
        <button @click="selectAll">全选</button>
        <button @click="clearAll">清除</button>
        <button @click="resetView">重置视图</button>
        <label style="display:inline-flex;align-items:center;gap:8px;margin-left:6px;">
          <input type="checkbox" v-model="showWaterQuality" @change="onWqToggle" />
          <span style="color:#fff;font-size:13px">显示水质热力图</span>
        </label>
      </div>
    </div>

    <div ref="chartRef" class="map-pie-chart"></div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
const emit = defineEmits(['place-selected'])
import * as echarts from 'echarts'
import Papa from 'papaparse'

// 可配置的后端接口，期望返回的数据结构见下方注释
const DATA_URL = '/api/disease_locations' // <- 请根据后端实际接口调整
const GEO_JSON_URLS = [
  '/echarts-assets/china.json',
  'https://geo.datav.aliyun.com/areas_v3/bound/geojson?code=100000'
]

const chartRef = ref(null)
let chart = null
let resizeHandler = null
const mapFeatureCenters = ref({})
const mapFeatureNameIndex = ref({})
const showWaterQuality = ref(false)
const waterScores = ref({})
// 预设颜色（支持至少 20 种类别），可以替换为项目设计色
const DEFAULT_COLORS = [
  '#4fc3f7','#f57171','#ffd666','#73d13d','#9254de','#ff85c0','#ffa39e','#bae637','#69c0ff','#ff7a45',
  '#a0d911','#ffec3d','#ffbb96','#ff85c0','#2f54eb','#13c2c2','#faad14','#722ed1','#eb2f96','#52c41a'
]

  // 点击选中时的放大配置（便于调整）
  const SELECTED_RADIUS_MULTIPLIER = 3
  const SELECTED_RADIUS_MIN = 48
  const SELECTED_MAP_ZOOM = 6

function computePalette(categories) {
  const pal = []
  for (let i = 0; i < categories.length; i++) pal.push(DEFAULT_COLORS[i % DEFAULT_COLORS.length])
  return pal
}

function hexToRgba(hex, a = 0.45) {
  if (!hex) return `rgba(0,0,0,${a})`
  const h = hex.replace('#','')
  const bigint = parseInt(h.length === 3 ? h.split('').map(c=>c+c).join('') : h, 16)
  const r = (bigint >> 16) & 255
  const g = (bigint >> 8) & 255
  const b = bigint & 255
  return `rgba(${r},${g},${b},${a})`
}

// 名称规范化辅助：用于匹配后端名称与 geojson feature 名称
function normalizeNameKey(n) {
  if (!n) return ''
  return String(n)
    .toLowerCase()
    .replace(/[\s\u00A0\-–—·()（）'"，,\.]/g, '')
    .replace(/(省|市|自治区|特别行政区|回族自治区|维吾尔自治区|壮族自治区)$/g, '')
}

function getColor(cat) {
  const idx = Math.max(0, diseaseCategories.value.indexOf(cat))
  return DEFAULT_COLORS[idx % DEFAULT_COLORS.length]
}

// 简单的疾病名称映射（英文 -> 中文），根据需要可继续扩充
const DISEASE_NAME_MAP = {
  'Typhoid': '伤寒',
  'Brucellosis': '布鲁氏菌病',
  'Hepatitis': '肝炎',
  'Hepatitis B': '乙型肝炎',
  'Influenza': '流感',
  'COVID-19': '新冠',
  'Dengue': '登革热',
  'Malaria': '疟疾',
  'Measles': '麻疹',
  'Mumps': '腮腺炎',
  'Cholera': '霍乱',
  'Tuberculosis': '肺结核',
  'HIV': '艾滋病',
  'HIV/AIDS': '艾滋病',
  'Pertussis': '百日咳',
  'Rubella': '风疹',
  'Typhus': '斑疹伤寒',
  'HandFootMouth': '手足口病',
  'Scarlet Fever': '猩红热',
  'Syphilis': '梅毒',
  'Dysentery': '痢疾',
  'Chickenpox': '水痘',
  'Rabies': '狂犬病'
}

function displayDiseaseName(cat) {
  if (!cat) return cat
  if (DISEASE_NAME_MAP[cat]) return DISEASE_NAME_MAP[cat]
  // 忽略大小写匹配
  const lower = cat.toLowerCase()
  for (const k of Object.keys(DISEASE_NAME_MAP)) {
    if (k.toLowerCase() === lower) return DISEASE_NAME_MAP[k]
  }
  return cat
}

// 省份/地区英文 -> 中文 映射（可继续扩充或替换为后端返回中文）
const PROVINCE_NAME_MAP = {
  'Beijing': '北京', 'Shanghai': '上海', 'Guangdong': '广东', 'Guangxi': '广西', 'Jiangsu': '江苏', 'Zhejiang': '浙江',
  'Sichuan': '四川', 'Henan': '河南', 'Hunan': '湖南', 'Hubei': '湖北', 'Shandong': '山东', 'Yunnan': '云南',
  'Jiangxi': '江西', 'Hebei': '河北', 'Liaoning': '辽宁', 'Heilongjiang': '黑龙江', 'Anhui': '安徽', 'Fujian': '福建',
  'Chongqing': '重庆', 'Shaanxi': '陕西', 'Inner Mongolia': '内蒙古', 'Nei Mongol': '内蒙古', 'Tianjin': '天津',
  'Gansu': '甘肃', 'Guizhou': '贵州', 'Xinjiang': '新疆', 'Ningxia': '宁夏', 'Qinghai': '青海', 'Hainan': '海南',
  'Jilin': '吉林', 'Shanxi': '山西', 'Taiwan': '台湾', 'Hong Kong': '香港', 'Macau': '澳门'
}

function mapProvinceName(name) {
  if (!name) return name
  // 规范化：去掉常见后缀并 trim，提升匹配率
  let n = String(name).trim()
  // 去掉常见中文后缀（省/市/自治区/特别行政区 等）以便更容易匹配
  n = n.replace(/(省|市|自治区|特别行政区|回族自治区|维吾尔自治区|壮族自治区)$/g, '')
  // 如果已经包含中文字符，直接返回去除后缀后的名称（更自然地显示）
  if (/[\u4e00-\u9fa5]/.test(n)) return n
  if (PROVINCE_NAME_MAP[n]) return PROVINCE_NAME_MAP[n]
  // 忽略大小写匹配
  const lower = n.toLowerCase()
  for (const k of Object.keys(PROVINCE_NAME_MAP)) {
    if (k.toLowerCase() === lower) return PROVINCE_NAME_MAP[k]
  }
  // 尝试按包含/前缀匹配
  for (const k of Object.keys(PROVINCE_NAME_MAP)) {
    if (k.toLowerCase().includes(lower) || lower.includes(k.toLowerCase())) return PROVINCE_NAME_MAP[k]
  }
  return n
}

// 由后端返回或回退数据：
// 数据格式假设（每项为一个地点）：
// [
//   {
//     name: '深圳',
//     lng: 114.271522,
//     lat: 22.753644,
//     counts: { '病种A': 12, '病种B': 3, ... } // 至少包含 15 类的键
//   },
//   ...
// ]

const locations = ref([]) // 上面结构
const diseaseCategories = ref([]) // 所有发现的疾病类别
const selectedMap = reactive({}) // { '病种A': true, ... }
const selectedPlaceName = ref(null)

// 本地回退示例（用于后端不可用时快速查看效果）
const FALLBACK = [
  { name: '深圳', lng: 114.06, lat: 22.55, counts: { 'A': 20, 'B': 10, 'C': 5 } },
  { name: '北京', lng: 116.4, lat: 39.9, counts: { 'A': 30, 'B': 4, 'C': 9 } },
  { name: '上海', lng: 121.47, lat: 31.23, counts: { 'A': 12, 'B': 24, 'C': 16 } },
]

// 当用户打开水质热力图开关时，按需加载 CSV 并用 PCA 计算省级得分（在浏览器端）
async function loadWaterQualityScores() {
  try {
    const res = await fetch('/china_water_pollution_data.csv')
    if (!res.ok) throw new Error('fetch failed')
    const text = await res.text()
    // 使用 PapaParse 以正确处理带引号/逗号的 CSV 字段
    const parsed = Papa.parse(text, { header: true, skipEmptyLines: true, dynamicTyping: true })
    const rows = parsed.data || []
    if (!rows.length) return {}

    // 识别省份列名
    const headerKeys = Object.keys(rows[0])
    function findProvinceKey(keys) {
      for (const k of keys) {
        if (/province/i.test(k) || /省份|省$/i.test(k)) return k
      }
      // fallback: try common alternatives
      for (const k of keys) {
        if (/prov/i.test(k)) return k
      }
      return null
    }
    const provinceKey = findProvinceKey(headerKeys)

    // 要忽略的列名（大小写不敏感）
    const IGNORE = ['city', 'date', 'monitoring_station', 'latitude', 'longitude', 'lat', 'lon', 'remarks', 'monitoring station']

    // 筛选出数值特征列：排除省份与 IGNORE 列，并要求列至少有一个有效数字
    const numericCandidates = []
    for (const k of headerKeys) {
      if (!k) continue
      if (provinceKey && k === provinceKey) continue
      const lower = k.toLowerCase().trim()
      if (IGNORE.includes(lower)) continue
      // 检查该列是否包含至少一个数值
      let hasNum = false
      for (const r of rows) {
        const v = r[k]
        if (v === null || v === undefined) continue
        if (typeof v === 'number' && Number.isFinite(v)) { hasNum = true; break }
        if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) { hasNum = true; break }
      }
      if (hasNum) numericCandidates.push(k)
    }

    // 如果没有发现多个数值列，回退到查找单独的 Water_Quality_Index / WQI 列
    if (numericCandidates.length === 0) {
      const wqkey = headerKeys.find(k => /water[_ ]?quality|wqi|waterquality|water_quality_index|水质/i.test(k))
      if (wqkey) numericCandidates.push(wqkey)
    }

    if (numericCandidates.length === 0) {
      console.warn('CSV 中未检测到可用于 PCA 的数值列，退回为空得分')
      return {}
    }

    // 构建数据矩阵（rows x numericCandidates），非数字用 NaN
    const matrix = rows.map(r => numericCandidates.map(k => {
      const v = r[k]
      if (v === null || v === undefined) return NaN
      if (typeof v === 'number') return Number.isFinite(v) ? v : NaN
      if (typeof v === 'string') {
        const t = v.trim()
        if (t === '') return NaN
        const n = Number(t)
        return Number.isNaN(n) ? NaN : n
      }
      return NaN
    }))

    // 删除在所有行均为 NaN 的列
    const colKeep = []
    for (let j = 0; j < numericCandidates.length; j++) {
      let any = false
      for (let i = 0; i < matrix.length; i++) {
        if (Number.isFinite(matrix[i][j])) { any = true; break }
      }
      if (any) colKeep.push(j)
    }
    if (colKeep.length === 0) {
      console.warn('所有候选数值列均为空')
      return {}
    }

    const Xclean = matrix.map(row => colKeep.map(j => row[j]))

    // 进一步清理：将 NaN 替换为列均值
    const nRows = Xclean.length
    const nCols = Xclean[0].length
    const colMeans = new Array(nCols).fill(0)
    const colCounts = new Array(nCols).fill(0)
    for (let j = 0; j < nCols; j++) {
      for (let i = 0; i < nRows; i++) {
        const v = Xclean[i][j]
        if (Number.isFinite(v)) { colMeans[j] += v; colCounts[j] += 1 }
      }
      colMeans[j] = colCounts[j] > 0 ? colMeans[j] / colCounts[j] : 0
    }
    const Xfilled = Xclean.map(row => row.map((v, j) => Number.isFinite(v) ? v : colMeans[j]))

    // 在浏览器端实现一个轻量的 PCA（只需第一主成分），避免引入额外无法安装的库。
    // 步骤：对每列标准化 -> 计算协方差矩阵 -> 幂迭代(power iteration)求最大特征向量 -> 计算样本在该方向的投影
    function computeFirstPC(matrix) {
      const n = matrix.length
      if (n === 0) return []
      const p = matrix[0].length
      // 计算列均值与 std
      const means = new Array(p).fill(0)
      const stds = new Array(p).fill(0)
      for (let j = 0; j < p; j++) {
        let sum = 0, cnt = 0
        for (let i = 0; i < n; i++) {
          const v = matrix[i][j]
          if (Number.isFinite(v)) { sum += v; cnt++ }
        }
        means[j] = cnt > 0 ? sum / cnt : 0
        // 计算方差
        let vsum = 0
        for (let i = 0; i < n; i++) {
          const v = matrix[i][j]
          const dv = Number.isFinite(v) ? v - means[j] : 0
          vsum += dv * dv
        }
        stds[j] = Math.sqrt(cnt > 1 ? vsum / (cnt - 1) : vsum === 0 ? 0 : vsum)
        if (stds[j] === 0) stds[j] = 1
      }

      // 标准化矩阵
      const Xstd = new Array(n)
      for (let i = 0; i < n; i++) {
        Xstd[i] = new Array(p)
        for (let j = 0; j < p; j++) {
          const v = matrix[i][j]
          Xstd[i][j] = Number.isFinite(v) ? (v - means[j]) / stds[j] : 0
        }
      }

      // 计算 p x p 协方差矩阵 C = (Xstd^T * Xstd) / (n-1)
      const C = Array.from({ length: p }, () => new Array(p).fill(0))
      for (let j = 0; j < p; j++) {
        for (let k = j; k < p; k++) {
          let s = 0
          for (let i = 0; i < n; i++) s += Xstd[i][j] * Xstd[i][k]
          const v = n > 1 ? s / (n - 1) : s
          C[j][k] = v
          C[k][j] = v
        }
      }

      // 幂迭代求最大特征向量
      let b = new Array(p).fill(0).map(() => Math.random())
      // 归一化初始向量
      let norm = Math.sqrt(b.reduce((s, x) => s + x * x, 0)) || 1
      b = b.map(x => x / norm)
      for (let it = 0; it < 120; it++) {
        const y = new Array(p).fill(0)
        for (let j = 0; j < p; j++) {
          let sum = 0
          for (let k = 0; k < p; k++) sum += C[j][k] * b[k]
          y[j] = sum
        }
        const ny = Math.sqrt(y.reduce((s, x) => s + x * x, 0)) || 1
        for (let j = 0; j < p; j++) b[j] = y[j] / ny
      }

      // 计算每个样本在该方向上的投影（scores）
      const scores = new Array(n)
      for (let i = 0; i < n; i++) {
        let s = 0
        for (let j = 0; j < p; j++) s += Xstd[i][j] * b[j]
        scores[i] = s
      }
      return scores
    }

    let pc1 = null
    try {
      pc1 = computeFirstPC(Xfilled)
    } catch (err) {
      console.warn('PCA 计算失败，退回使用单列均值', err)
      // 退回到使用首个数值列的均值
      const fallbackKey = numericCandidates[0]
      const sums = {}, counts = {}
      for (const r of rows) {
        const prov = (provinceKey && r[provinceKey]) ? String(r[provinceKey]) : 'Unknown'
        const v = r[fallbackKey]
        const num = (typeof v === 'number' ? (Number.isFinite(v) ? v : NaN) : (typeof v === 'string' ? Number(v) : NaN))
        if (!Number.isFinite(num)) continue
        sums[prov] = (sums[prov] || 0) + num
        counts[prov] = (counts[prov] || 0) + 1
      }
      const avg = {}
      for (const k of Object.keys(sums)) avg[k] = sums[k] / counts[k]
      waterScores.value = avg
      return avg
    }

    // 将 pc1（每行）按省分组并取均值
    const provVals = {}
    const provCounts = {}
    for (let i = 0; i < rows.length; i++) {
      const prov = provinceKey && rows[i][provinceKey] ? String(rows[i][provinceKey]) : 'Unknown'
      const v = pc1[i]
      if (!Number.isFinite(v)) continue
      provVals[prov] = (provVals[prov] || 0) + v
      provCounts[prov] = (provCounts[prov] || 0) + 1
    }
    const provMeans = {}
    for (const k of Object.keys(provVals)) {
      const m = provVals[k] / provCounts[k]
      provMeans[k] = m
    }

    // 将原始 PCA 省级均值线性缩放到 [45, 53]（按用户要求）
    const SCALE_MIN = 45
    const SCALE_MAX = 53
    const rawVals = Object.values(provMeans).filter(v => Number.isFinite(v))
    if (rawVals.length === 0) {
      waterScores.value = {}
      return {}
    }
    const rawMin = Math.min(...rawVals)
    const rawMax = Math.max(...rawVals)
    const scaled = {}
    if (rawMax === rawMin) {
      const mid = (SCALE_MIN + SCALE_MAX) / 2
      for (const k of Object.keys(provMeans)) scaled[k] = mid
    } else {
      for (const k of Object.keys(provMeans)) {
        scaled[k] = SCALE_MIN + ((provMeans[k] - rawMin) / (rawMax - rawMin)) * (SCALE_MAX - SCALE_MIN)
      }
    }
    waterScores.value = scaled
    return scaled
  } catch (e) {
    console.warn('加载 water quality csv 失败', e)
    return {}
  }
}

function onWqToggle() {
  // 如果打开且尚未加载数据，则按需加载；否则直接更新图层显示状态
  if (showWaterQuality.value && Object.keys(waterScores.value).length === 0) {
    loadWaterQualityScores().then(() => updateChart()).catch(() => updateChart())
  } else {
    updateChart()
  }
}

async function fetchGeoJSON() {
  // 优先尝试通过注入 chain.js（若存在于 public/mapdetail），因为它通常包含更适配的 topojson/geojson
  const geoFromChain = await loadGeoFromChainScript()
  if (geoFromChain) return geoFromChain

  for (const url of GEO_JSON_URLS) {
    try {
      const res = await fetch(url)
      if (res.ok) return await res.json()
    } catch (e) {
      // ignore and try next
    }
  }
  throw new Error('无法加载地图 GeoJSON')
}

// 动态注入 chain.js 并从中读取已注册的 'china' 地图 JSON（与 TrendChart 中的实现类似）
function loadGeoFromChainScript() {
  return new Promise(async (resolve) => {
    try {
      if (typeof window !== 'undefined') window.echarts = echarts
      const existing = echarts.getMap && echarts.getMap('china')
      if (existing && existing.geoJSON) return resolve(existing.geoJSON)
      const id = 'chain-js-map'
      if (!document.getElementById(id)) {
        const script = document.createElement('script')
        script.id = id
        script.src = '/mapdetail/chain.js'
        script.async = true
        script.onload = () => {
          try {
            const m = echarts.getMap && echarts.getMap('china')
            resolve(m && m.geoJSON ? m.geoJSON : null)
          } catch (e) {
            resolve(null)
          }
        }
        script.onerror = () => resolve(null)
        document.head.appendChild(script)
      } else {
        setTimeout(() => {
          try {
            const m = echarts.getMap && echarts.getMap('china')
            resolve(m && m.geoJSON ? m.geoJSON : null)
          } catch (e) {
            resolve(null)
          }
        }, 200)
      }
    } catch (err) {
      resolve(null)
    }
  })
}

async function fetchLocations() {
  try {
    const res = await fetch(DATA_URL)
    if (!res.ok) throw new Error('no data')
    const data = await res.json()
    if (!Array.isArray(data) || data.length === 0) throw new Error('empty')
    return data
  } catch (e) {
    console.warn('拉取后端 disease 数据失败，使用回退示例', e)
    return FALLBACK
  }
}

function extractCategories(locArray) {
  const set = new Set()
  for (const loc of locArray) {
    if (loc.counts && typeof loc.counts === 'object') {
      for (const k of Object.keys(loc.counts)) set.add(k)
    }
  }
  return Array.from(set)
}

function makePieSeries(loc, selectedCats, radius = 18, greyMode = false, selectedName = null) {
  // 构造饼图 data；为每个 slice 指定 itemStyle.color
  const data = selectedCats.map(cat => {
    const idx = Math.max(0, diseaseCategories.value.indexOf(cat))
    const color = greyMode ? '#bfbfbf' : DEFAULT_COLORS[idx % DEFAULT_COLORS.length]
    return { name: displayDiseaseName(cat), value: Number(loc.counts?.[cat] ?? 0), itemStyle: { color } }
  })
  const isSelected = selectedName && selectedName === loc.name
    const finalRadius = isSelected ? Math.max(radius * SELECTED_RADIUS_MULTIPLIER, SELECTED_RADIUS_MIN) : radius
  return {
    name: loc.name,
    type: 'pie',
    coordinateSystem: 'geo',
    center: [loc.lng, loc.lat],
    radius: finalRadius,
    zlevel: isSelected ? 20 : 10,
    label: { show: false },
    emphasis: { label: { show: true, formatter: '{b}: {c}' } },
    tooltip: { formatter: (params) => {
      // params 为 slice，params.seriesName 为地点名
      const locName = params.seriesName || loc.name
      const cat = params.name
      const val = params.value
      // params.name 已经被替换为中文（displayDiseaseName），但为了保险我们再映射一次
      const dispCat = displayDiseaseName(cat)
      return `${locName}<br/>${dispCat}: ${val}`
    }},
    data
  }
}

function buildOptionForAll(selectedCats, greyMode = false, selectedName = null) {
  const pieSeries = []
  for (const loc of locations.value) {
    pieSeries.push(makePieSeries(loc, selectedCats, 18, greyMode, selectedName))
  }

  // 添加一个无符号的 scatter 系列用于在地图上显示地点名（始终可见）
  // 合并 locations 中的点与 geo feature 的中心点（用于没有饼图的省份仍然显示名称）
  const labelData = []
  const added = new Set()
  for (const p of locations.value) {
    labelData.push({ name: p.name, value: [p.lng, p.lat] })
    added.add(String(p.name))
  }
  // 现在把 mapFeatureCenters 中的省加入（若名称转换后未被 locations 覆盖）
  for (const [fname, center] of Object.entries(mapFeatureCenters.value || {})) {
    const cname = mapProvinceName(fname)
    if (!added.has(String(cname)) && Array.isArray(center) && center.length >= 2) {
      labelData.push({ name: cname, value: [center[0], center[1]] })
      added.add(String(cname))
    }
  }

  const labelSeries = {
    name: '地点标签',
    type: 'scatter',
    coordinateSystem: 'geo',
    data: labelData,
    symbol: 'circle',
    // 不绘制点，仅显示文字
    symbolSize: 0,
    label: {
      show: true,
      formatter: (params) => params.data.name,
      fontSize: 12,
      color: '#fff',
      position: 'right',
      distance: 6,
      backgroundColor: 'rgba(0,0,0,0.45)',
      padding: [2,6],
      borderRadius: 4,
      // 保证常显
      emphasis: { show: true }
    },
    silent: true,
    // 放到最上层，保证文字不会被饼或其他层遮挡
    zlevel: 60
  }

  const legendData = selectedCats.length ? selectedCats : [...diseaseCategories.value]
  const palette = greyMode ? legendData.map(() => '#bfbfbf') : computePalette(legendData)
  // 增加一个透明的 map 系列仅用于绘制省界边线，参考 TrendChart 的样式
  // 先为每个省分配颜色（用于填充）
  // 优先使用从 GeoJSON features 索引到的真实 feature 名称（mapFeatureNameIndex 的值）——
  // 这样可以保证 provinceColorSeries.data.name 与 geoJSON 的 feature.name 精确匹配，避免填色错位。
  const featureNames = Array.from(new Set(Object.values(mapFeatureNameIndex.value || {}).filter(Boolean)))
  let provinces = labelData.map(d => d.name)
  let featureSource = null
  if (featureNames.length) {
    // featureNames 是 geo feature 的真实名称；为了展示顺序和颜色一致，我们使用其对应的中文显示名作为 palette 的输入
    provinces = featureNames.map(fn => mapProvinceName(fn))
    featureSource = featureNames
  }
  const provincePalette = computePalette(provinces)
  const provinceData = []
  if (featureSource) {
    for (let i = 0; i < featureSource.length; i++) {
      const featName = featureSource[i]
      provinceData.push({ name: String(featName), value: 0, itemStyle: { areaColor: hexToRgba(provincePalette[i % provincePalette.length], 0.35) } })
    }
  } else {
    const unmatched = []
    function normalizeNameKey(n) {
      if (!n) return ''
      return String(n).toLowerCase().replace(/[\s\u00A0\-–—·()（）'"，,\.]/g, '').replace(/(省|市|自治区|特别行政区|回族自治区|维吾尔自治区|壮族自治区)$/g, '')
    }
    for (let i = 0; i < provinces.length; i++) {
      const nm = provinces[i]
      const key = normalizeNameKey(nm)
      const mappedGeoName = mapFeatureNameIndex.value[key]
      if (mappedGeoName) {
        provinceData.push({ name: mappedGeoName, value: 0, itemStyle: { areaColor: hexToRgba(provincePalette[i % provincePalette.length], 0.35) } })
      } else {
        provinceData.push({ name: nm, value: 0, itemStyle: { areaColor: hexToRgba(provincePalette[i % provincePalette.length], 0.35) } })
        unmatched.push(nm)
      }
    }
    if (unmatched.length) console.warn('provinceColorSeries 未匹配到 geo feature 的省份（可忽略或用于补充映射表）:', unmatched)
  }
  const provinceColorSeries = {
    name: '省域填色',
    type: 'map',
    map: 'china_pie',
    // 绑定到 geo 组件的 index（geo 在 option 中为第一个 geo），
    // 确保省域填色会跟随 geo 的 center/zoom/roam 一起变换
    geoIndex: 0,
    roam: false,
    silent: true,
    zlevel: 1,
    itemStyle: { borderColor: 'rgba(0,0,0,0)', borderWidth: 0 },
    label: { show: false },
    data: provinceData
  }

  const borderMapSeries = {
    name: '省界',
    type: 'map',
    map: 'china_pie',
    geoIndex: 0,
    roam: false,
    silent: true,
    zlevel: 2,
    itemStyle: {
      areaColor: 'rgba(0,0,0,0)',
      borderColor: '#333',
      borderWidth: 1.2,
    },
    emphasis: { itemStyle: { areaColor: 'rgba(0,0,0,0)', borderColor: '#000', borderWidth: 1.4 } },
    label: { show: false }
  }

  const opt = {
    backgroundColor: 'transparent',
    color: palette,
    tooltip: { trigger: 'item' },
    // 隐藏可能出现在右侧的工具栏/图例/视觉映射控件，避免遮挡地图
    toolbox: { show: false },
    legend: { show: false },
    visualMap: { show: false },
    // 不渲染右侧 legend，颜色说明在左侧 overlay 中
    geo: {
      map: 'china_pie',
      roam: true,
      // 缩紧左右边距，避免为右侧控件留白
      left: '4%',
      right: '4%',
      top: '6%',
      bottom: '6%',
      zoom: 1.2,
      center: [105, 36],
      label: { show: false },
      itemStyle: { areaColor: '#f5f5f5', borderColor: '#666', borderWidth: 1.2 },
      emphasis: { itemStyle: { areaColor: '#ffd1d1' } }
    },
    series: [
      provinceColorSeries,
      ...pieSeries,
      labelSeries,
      borderMapSeries
    ]
  }
  return opt
}

function buildChoroplethOption() {
  // 当后端返回的 counts 只有 { all: n } 时，绘制省级热力图
  const mapData = locations.value.map(loc => ({ name: loc.name, value: Number(loc.counts?.all ?? 0) }))
  const maxVal = Math.max(...mapData.map(d => d.value)) || 100
  return {
    backgroundColor: 'transparent',
    // 隐藏默认的 title/visualMap/legend/toolbox，避免右侧或其他位置出现遮挡控件
    title: { show: false },
    tooltip: { trigger: 'item', formatter: params => `${params.name}<br/>病例数: ${params.value || 0}` },
    toolbox: { show: false },
    legend: { show: false },
    visualMap: { show: false, min: 0, max: maxVal },
    // 更紧的左右边距，避免为控件留空
    geo: { left: '2%', right: '2%', top: '6%', bottom: '6%' },
    series: [{ name: '病例数', type: 'map', map: 'china_pie', roam: false, label: { show: false }, data: mapData }]
  }
}

function buildWaterQualityOverlayOption() {
  // 根据 waterScores 构造 map data，尝试将提供的省名映射到 geo feature 名称
  const scores = waterScores.value || {}
  const data = []
  for (const prov of Object.keys(scores)) {
    const key = normalizeNameKey(prov)
    const mapped = mapFeatureNameIndex.value[key] || mapProvinceName(prov) || prov
    data.push({ name: mapped, value: Number(scores[prov]) })
  }
  const maxV = data.length ? Math.max(...data.map(d => d.value)) : 100
  // 采用 waterScores 的原始值动态设置 visualMap 范围（不对值做固定缩放）
  const vals = Object.values(scores).filter(v => Number.isFinite(v))
  let vmin = vals.length ? Math.min(...vals) : 0
  let vmax = vals.length ? Math.max(...vals) : 1
  if (vmin === vmax) {
    // 防止 visualMap min==max 导致渲染问题，做小偏移
    const delta = Math.abs(vmin) * 0.02 || 0.5
    vmin = vmin - delta
    vmax = vmax + delta
  }
  const visualMap = {
    show: true,
    orient: 'vertical',
    left: 'right',
    top: '18%',
    min: vmin,
    max: vmax,
    inRange: { color: ['#e6f7ff', '#b3e0ff', '#66b3ff', '#0d87ff', '#005bb5'] },
    text: ['高', '低'],
    calculable: true,
    itemWidth: 12,
    itemHeight: 120
  }
  const series = [{
    name: '水质得分',
    type: 'map',
    map: 'china_pie',
    // 绑定到 geo（geo 在 option 中为第一个 geo），保证与 geo 的平移/缩放一致
    geoIndex: 0,
    roam: false,
    silent: true,
    label: { show: false },
    itemStyle: {
      borderColor: 'rgba(0,0,0,0.06)',
      borderWidth: 0.8
    },
    emphasis: { itemStyle: { areaColor: 'rgba(10,78,160,0.25)' } },
    zlevel: 5,
    data
  }]
  return { visualMap, series }
}

function updateChart() {
  if (!chart) return
  // 检测是否所有 location 的 counts 仅含 { all: n }，若是则使用 choropleth
  const onlyAll = locations.value.length > 0 && locations.value.every(loc => {
    const keys = loc.counts ? Object.keys(loc.counts) : []
    return keys.length === 1 && keys[0] === 'all'
  })
  if (onlyAll) {
    const opt = buildChoroplethOption()
    // 若开启水质图层，则在 choropleth 基础上叠加水质图
    if (showWaterQuality.value && Object.keys(waterScores.value).length) {
      const wqOpt = buildWaterQualityOverlayOption()
      // 合并 water quality visualMap/series 到 opt
      opt.visualMap = wqOpt.visualMap
      opt.series = [ ...wqOpt.series, ...(opt.series || []) ]
    }
    chart.setOption(opt, { notMerge: true })
    return
  }

  const selectedCats = diseaseCategories.value.filter(c => selectedMap[c])
  // 如果没有勾选任何病种，显示全部（避免空图）；灰度模式在 makePieSeries 中使用
  const active = selectedCats.length ? selectedCats : [...diseaseCategories.value]
  const opt = buildOptionForAll(active, selectedCats.length === 0, selectedPlaceName.value)
  // 将水质图层插入最前并添加 visualMap（按需）
  if (showWaterQuality.value && Object.keys(waterScores.value).length) {
    const wqOpt = buildWaterQualityOverlayOption()
    opt.visualMap = wqOpt.visualMap
    opt.series = [ ...wqOpt.series, ...(opt.series || []) ]
  }
  chart.setOption(opt, { notMerge: true })
  // 同步 ECharts legend 与左侧复选框（灰度模式下禁用 legend->checkbox 的同步）
  // legend 已移除（颜色说明在左侧），仍保留图例事件解绑以防外部干扰
  chart.off('legendselectchanged')
}

function selectAll() {
  diseaseCategories.value.forEach(c => selectedMap[c] = true)
}
function clearAll() {
  diseaseCategories.value.forEach(c => selectedMap[c] = false)
}

function resetView() {
  if (!chart) return
  chart.setOption({ geo: { zoom: 1.2, center: [105, 36] } })
}

onMounted(async () => {
  chart = echarts.init(chartRef.value)
  chart.showLoading()
  try {
    const geojson = await fetchGeoJSON()
    echarts.registerMap('china_pie', geojson)


    // 提取每个 feature 的 name -> center（优先使用 properties.cp / properties.center，否则用简单平均法近似质心）
    try {
      const features = (geojson && geojson.features) || []
      const centers = {}
      const nameIndex = {}
      for (const f of features) {
        const props = f.properties || {}
        const name = props.name || props.NAME || props.name || (f.id || null)
        if (!name) continue
        let c = null
        if (Array.isArray(props.cp) && props.cp.length >= 2) c = props.cp
        else if (Array.isArray(props.center) && props.center.length >= 2) c = props.center
        else {
          // 估算质心：取第一个环的平均点（适用于常见的多边形geojson）
          try {
            const geom = f.geometry
            if (geom && geom.coordinates) {
              // 支持 Polygon 和 MultiPolygon
              let ring = null
              if (geom.type === 'Polygon') ring = geom.coordinates[0]
              else if (geom.type === 'MultiPolygon') ring = geom.coordinates[0] && geom.coordinates[0][0]
              if (ring && ring.length) {
                let sx = 0, sy = 0, n = 0
                for (const pt of ring) {
                  if (Array.isArray(pt) && pt.length >= 2) { sx += pt[0]; sy += pt[1]; n++ }
                }
                if (n > 0) c = [sx / n, sy / n]
              }
            }
          } catch (e) { /* ignore */ }
        }
        if (c) centers[String(name)] = c
        // 建立规范名索引（同时加入 mapProvinceName 的变体以提高匹配率）
        const key1 = normalizeNameKey(name)
        if (key1) nameIndex[key1] = String(name)
        try {
          const mp = mapProvinceName(name)
          const key2 = normalizeNameKey(mp)
          if (key2) nameIndex[key2] = String(name)
        } catch (e) { /* ignore */ }
      }
      mapFeatureCenters.value = centers
      mapFeatureNameIndex.value = nameIndex
    } catch (err) {
      mapFeatureCenters.value = {}
    }

    const locs = await fetchLocations()
    // ensure numeric lng/lat and counts
    locations.value = locs.map(l => ({
      name: mapProvinceName(l.name || l.city || '未知'),
      lng: Number(l.lng ?? l.longitude ?? (l.value && l.value[0]) ?? NaN),
      lat: Number(l.lat ?? l.latitude ?? (l.value && l.value[1]) ?? NaN),
      counts: l.counts || l.countsByDisease || l.count || {}
    })).filter(x => Number.isFinite(x.lng) && Number.isFinite(x.lat))

    // 为保证绘图使用的类别与 locations.value 中的 counts 键一致，
    // 直接从处理后的 locations.value 提取类别（首选）。
    diseaseCategories.value = extractCategories(locations.value)
    if (diseaseCategories.value.length === 0) {
      // 如果处理后没有提取到（极少数情况），回退到原始 fetch 返回的数据
      diseaseCategories.value = extractCategories(locs)
    }

    // 一次性调试输出：便于在浏览器 Console 比对后端响应与前端解析结果
    try {
      console.log('MapPieChart: fetched sample', locs.slice(0, 2))
      console.log('MapPieChart: parsed locations sample', locations.value.slice(0, 2))
      console.log('MapPieChart: diseaseCategories', diseaseCategories.value)
    } catch (e) { /* 忽略在部分旧浏览器上的 slice 错误 */ }

    // 初始化选择全部
    diseaseCategories.value.forEach(c => selectedMap[c] = true)

    updateChart()

    // 点击缩放或放大饼图：如果点击的是饼图或某个省份（geo 组件），定位并放大。点击同一饼图会切换放大/还原
    chart.on('click', (params) => {
      // 点击 pie 系列时 params.seriesName 为地点名
      if (params && params.seriesType === 'pie') {
        const place = locations.value.find(p => p.name === params.seriesName)
        if (place) {
          // 切换选中状态：再次点击相同地点则取消选中
          if (selectedPlaceName.value === place.name) {
            selectedPlaceName.value = null
            chart.setOption({ geo: { center: [105, 36], zoom: 1.2 } })
          } else {
            selectedPlaceName.value = place.name
            // 放大地图中心并增大 zoom，使点击效果更明显
            chart.setOption({ geo: { center: [place.lng, place.lat], zoom: SELECTED_MAP_ZOOM } })
          }
          // 重新渲染以展示放大效果
          updateChart()
          // 向父组件/外部广播已选中地点，便于与聊天面板等联动
          try { emit('place-selected', place) } catch(e) { /* ignore */ }
        }
        return
      }
      // 点击 geo（省份边界）时，尝试找到该省对应的 location 并居中
      if (params && (params.componentType === 'geo' || params.componentType === 'series' && params.seriesType === 'map' || params.seriesType === 'map')) {
        const province = params.name
        const place = locations.value.find(p => p.name === province)
        if (place) {
          selectedPlaceName.value = place.name
          chart.setOption({ geo: { center: [place.lng, place.lat], zoom: SELECTED_MAP_ZOOM } })
          updateChart()
          try { emit('place-selected', place) } catch(e) { /* ignore */ }
        }
      }
    })

  

  } catch (e) {
    console.error('初始化地图失败', e)
  } finally {
    chart.hideLoading()
  }

  resizeHandler = () => chart && chart.resize()
  window.addEventListener('resize', resizeHandler)
})

onBeforeUnmount(() => {
  if (chart) chart.dispose()
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})

// 当用户切换勾选项时，自动更新图表
watch(() => ({ ...selectedMap }), updateChart, { deep: true })
</script>

<style scoped>
.map-pie-wrapper { position: relative; width: 100%; height: 100vh; }
.controls {
  position: absolute;
  left: 12px;
  top: 12px;
  width: 300px;
  max-height: calc(100vh - 24px);
  padding: 10px;
  background: rgba(18, 24, 35, 0.75);
  color: #fff;
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.4);
  z-index: 30;
  overflow: auto;
}
.controls-title { font-weight: 700; margin-bottom: 8px; color: #fff }
.checkbox-list { display:flex; flex-wrap: wrap; gap:8px }
.checkbox-item { display:flex; align-items:center; gap:6px; font-size:13px; color: #fff }
.swatch { width: 12px; height: 12px; border-radius: 2px; display:inline-block; margin-left:6px; box-shadow: 0 1px 2px rgba(0,0,0,0.4) }
.cat-label { margin-left:6px }
.controls-actions { margin-top: 10px; display:flex; gap:8px }
.map-pie-chart { position: absolute; left: 0; right: 0; top: 0; bottom: 0; background: transparent; }
</style>
