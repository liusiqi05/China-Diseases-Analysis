<template>
  <div class="fusion-container">
    <div ref="chartRef" class="map-chart"></div>
  <New5 />
    <div class="sales-panel">
      <div class="panel-header">病例数</div>
      <div class="panel-body">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>地区</th>
              <th>病例数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in salesData" :key="item.name">
              <td>{{ item.name }}</td>
              <td>{{ formatNumber(item.cases ?? getCasesValue(item) ?? 0) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import New5 from './new5.vue'

const chartRef = ref(null)
let chart = null
const salesData = ref([])
let resizeHandler = null
let animFrame = null
let animState = null
let animCompleted = false

const DEFAULT_DATA = [
  { name: '深圳', value: [114.271522, 22.753644], Sales: '2台' },
  { name: '南京', value: [118.46, 32.02], Sales: '2台' },
  { name: '重庆', value: [106.54, 29.59], Sales: '1台' },
  { name: '北京', value: [116.24, 39.55], Sales: '3台' },
  { name: '荆州', value: [112.24, 30.33], Sales: '2台' },
]

// 简单的英名 -> 中文省份映射（可扩展）用于把数据库里的英文省名映射到 ECharts 地图使用的中文省名
const PROVINCE_NAME_MAP = {
  'Beijing': '北京',
  'Shanghai': '上海',
  'Guangdong': '广东',
  'Guangxi': '广西',
  'Jiangsu': '江苏',
  'Zhejiang': '浙江',
  'Sichuan': '四川',
  'Henan': '河南',
  'Hunan': '湖南',
  'Hubei': '湖北',
  'Shandong': '山东',
  'Yunnan': '云南',
  'Jiangxi': '江西',
  'Hebei': '河北',
  'Liaoning': '辽宁',
  'Heilongjiang': '黑龙江',
  'Anhui': '安徽',
  'Fujian': '福建',
  'Chongqing': '重庆',
  'Shaanxi': '陕西',
  'Inner Mongolia': '内蒙古',
  'Nei Mongol': '内蒙古',
  'Tianjin': '天津',
  'Gansu': '甘肃',
  'Guizhou': '贵州',
  'Xinjiang': '新疆',
  'Ningxia': '宁夏',
  'Qinghai': '青海',
  'Hainan': '海南',
  'Jilin': '吉林',
  'Shanxi': '山西',
  'Taiwan': '台湾',
  'Hong Kong': '香港',
  'Macau': '澳门'
}

function mapProvinceName(name) {
  if (!name) return name
  // 如果已经是中文，直接返回
  if (/[-]*[\u4e00-\u9fa5]+/.test(name)) return name
  // 直接匹配完整键
  if (PROVINCE_NAME_MAP[name]) return PROVINCE_NAME_MAP[name]
  // 忽略大小写尝试匹配
  const keys = Object.keys(PROVINCE_NAME_MAP)
  const lower = name.toLowerCase()
  for (const k of keys) {
    if (k.toLowerCase() === lower) return PROVINCE_NAME_MAP[k]
  }
  // 尝试按前缀匹配（如 'Nei Mongol' vs 'Inner Mongolia' 情形）
  for (const k of keys) {
    if (k.toLowerCase().includes(lower) || lower.includes(k.toLowerCase())) return PROVINCE_NAME_MAP[k]
  }
  return name // 未匹配则原样返回
}

// 格式化数字为千位分隔符字符串
function formatNumber(v) {
  if (v === null || v === undefined) return ''
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString()
}

// Helper to get cases value (only cases used now; Sales removed)
function getCasesValue(item) {
  if (!item) return null
  return (item.cases !== undefined && item.cases !== null) ? item.cases : null
}

async function loadChinaGeoJSON() {
  // 优先尝试使用 public/mapdetail/chain.js 提供的高精度底图
  try {
    const geoFromChain = await loadGeoFromChainScript()
    if (geoFromChain) return geoFromChain
  } catch (_) {}
  // 回退到本地与远端 GeoJSON
  const urls = [
    '/echarts-assets/china.json',
    'https://geo.datav.aliyun.com/areas_v3/bound/geojson?code=100000',
  ]
  for (const url of urls) {
    try {
      const res = await fetch(url)
      if (res.ok) return await res.json()
    } catch (_) {}
  }
  throw new Error('无法加载中国地图 GeoJSON')
}

// 动态注入 chain.js 并从中获取已注册的 'china' 地图，再以独立名称重注册
function loadGeoFromChainScript() {
  return new Promise(async (resolve, reject) => {
    try {
      // 让 UMD 脚本可访问到全局 echarts
      if (typeof window !== 'undefined') {
        // @ts-ignore
        window.echarts = echarts
      }
      const existing = echarts.getMap && echarts.getMap('china')
      if (existing && existing.geoJSON) {
        return resolve(existing.geoJSON)
      }
      // 防止重复插入
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
        // 已存在脚本，稍等注册完成
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

async function loadSales() {
  // 优先从后端 API 获取：先尝试省级疾病数据 /api/china_disease（返回 {name, cases}），
  // 若返回带坐标的点数据也可兼容。回退到旧的 /api/sales 或本地静态。
  try {
    const res1 = await fetch('/api/china_disease')
    if (res1.ok) {
      const data1 = await res1.json()
      if (Array.isArray(data1) && data1.length) {
        return data1
      }
    }
  } catch (_) {}

  try {
    const apiRes = await fetch('/api/sales')
    if (apiRes.ok) {
      const apiData = await apiRes.json()
      if (Array.isArray(apiData) && apiData.length) {
        // 已是标准结构：{ name, value: [lng,lat], Sales }
        return apiData
      }
    }
  } catch (_) {}
  // 回退到本地 JSON
  try {
    const res = await fetch('/json/RobotSales.json')
    if (res.ok) return await res.json()
  } catch (_) {}
  return DEFAULT_DATA
}

function buildOption(dataValue) {
  return {
    backgroundColor: 'transparent',
    tooltip: { show: true, triggerOn: 'click' },
    geo: {
      map: 'china_trend', roam: true, zoom: 1.2, center: [105, 36],
      // 固定投影，避免不同系列默认值差异导致微小形变
      projection: null,
      // 维持合适的长宽比（默认 0.75），可微调以匹配你资源
      aspectScale: 0.75,
      itemStyle: { areaColor: '#f5f2f2', borderColor: '#666', borderWidth: 1.2 },
      // 提升地名可读性：文字描边 + 轻微阴影
      label: {
        show: true,
        fontSize: 12,
        color: '#1f1f1f',
        fontWeight: 600,
        textBorderColor: 'rgba(255,255,255,0.9)',
        textBorderWidth: 2,
        textShadowColor: 'rgba(0,0,0,0.25)',
        textShadowBlur: 2,
      },
      emphasis: {
        itemStyle: { areaColor: '#d0a3a3' },
        label: { show: true, color: '#000', textBorderWidth: 0 }
      },
    },
    series: [
      // 省界边线层（透明填充，只画边界，更清晰）
      {
        name: '省界',
        type: 'map',
        map: 'china_trend',
        geoIndex: 0,
        roam: false,
        silent: true,
        zlevel: 2,
        itemStyle: {
          areaColor: 'rgba(0,0,0,0)',
          borderColor: '#333',
          borderWidth: 1.5,
        },
        emphasis: { itemStyle: { areaColor: 'rgba(0,0,0,0)', borderColor: '#000', borderWidth: 1.8 } },
        label: { show: false },
      },
      // 点位层（如果 dataValue 含坐标）——仅显示名称与坐标，不展示销量/价格信息
      {
        name: '位置',
        type: 'scatter',
        coordinateSystem: 'geo',
        data: dataValue,
        symbolSize: 10,
        itemStyle: { color: '#4fc3f7', shadowBlur: 4, shadowColor: 'rgba(0,0,0,0.4)' },
        tooltip: {
          trigger: 'item',
          formatter: (params) => {
            const d = params.data || {}
            const val = Array.isArray(d.value) ? d.value.join(', ') : (d.value ?? '')
            const cases = getCasesValue(d) ?? (d.cases ?? '')
            return `${d.name || params.name}<br/>坐标: ${val}${cases ? `<br/>病例数: ${cases}` : ''}`
          }
        }
      },
      {
        name: '位置高亮',
        type: 'effectScatter',
        coordinateSystem: 'geo',
        data: dataValue,
        symbolSize: 8,
        showEffectOn: 'render',
        rippleEffect: { brushType: 'stroke', period: 6, scale: 6 },
        label: { formatter: '{b}', position: 'top', show: false },
        itemStyle: { color: '#4fc3f7' },
        zlevel: 3,
      }
    ],
  }
}

async function init() {
  const geojson = await loadChinaGeoJSON()
  // 使用独立的地图名，避免与其他组件或外部脚本注册的 'china' 发生冲突
  echarts.registerMap('china_trend', geojson)

  const origin = await loadSales()
  // 规范化省份名为中文，避免表格显示英文或不一致名称
  salesData.value = origin.map(item => ({ ...item, name: mapProvinceName(item.name) }))

  // 判断数据是否包含坐标
  const hasCoords = origin.some(item => Array.isArray(item.value) && item.value.length >= 2)

  chart = echarts.init(chartRef.value)

  if (!hasCoords) {
    // 省级 choropleth：origin items 应为 { name, cases }
  const mapData = origin.map(item => ({ name: mapProvinceName(item.name), value: getCasesValue(item) ?? 0 }))
  const maxVal = Math.max(...mapData.map(d => d.value)) || 100
  // 固定下限为 5000，以增强高值区间的可视化对比度
  const visualMin = 5000
  const dataMin = Math.min(...mapData.map(d => d.value)) || 0
    const opt = {
      backgroundColor: 'transparent',
      title: { text: '省级病例数', left: 'center', textStyle: { color: '#fff' } },
      tooltip: { trigger: 'item', formatter: params => `${params.name}<br/>病例数: ${params.value || 0}` },
      visualMap: { min: visualMin, max: maxVal, left: 'left', top: 'bottom', text: ['高','低'], calculable: true, inRange: { color: ['#fff7bc', '#fdae61', '#d7191c'] } },
      series: [ { name: '病例数', type: 'map', map: 'china_trend', roam: false, label: { show: true }, data: mapData } ]
    }
    chart.setOption(opt)

    // --- visualMap 动画：在 visualMin (5000) 与 6524 之间往返平滑过渡 ---
    // 动画采用 requestAnimationFrame，使用 ease-in-out (cosine) 缓动
  const animFrom = 5000
  const animTo = 6524
  const animDuration = 4000 // 向上平滑耗时(ms)
  let animTimeout = null

    function startVisualAnimation() {
      if (!chart) return
      if (animFrame || animCompleted) return // 已在运行或已完成一次跳变
      animState = { phase: 'rising', start: null }

      const step = (timestamp) => {
        if (!animState) return
        if (!animState.start) animState.start = timestamp
        const elapsed = timestamp - animState.start

        try {
          const t = Math.min(1, elapsed / animDuration)
          // ease-out-ish for 上升段（平滑增加）
          const eased = 1 - Math.pow(1 - t, 3)
          const current = animFrom + (animTo - animFrom) * eased
          chart.setOption({ visualMap: { min: Math.round(current), max: maxVal } })

          if (t >= 1) {
            // 显示一次跳变到 animTo（高亮），短暂停留后恢复为按照实际人数分布的范围
            try { chart.setOption({ visualMap: { min: animTo, max: maxVal } }) } catch (e) {}
            // 短暂展示顶部高亮，然后恢复为 dataMin..maxVal 以正确反映人数分布
            animTimeout = setTimeout(() => {
              try { chart.setOption({ visualMap: { min: dataMin, max: maxVal } }) } catch (e) {}
              animCompleted = true
              stopVisualAnimation()
            }, 600)
            return
          }
        } catch (e) {
          stopVisualAnimation()
          return
        }

        animFrame = requestAnimationFrame(step)
      }

      animFrame = requestAnimationFrame(step)
    }

    function stopVisualAnimation() {
      if (animFrame) {
        cancelAnimationFrame(animFrame)
        animFrame = null
      }
      animState = null
    }

    // 鼠标悬停时暂停动画，离开时恢复
    const dom = chartRef.value
    function pauseOnHover() { stopVisualAnimation() }
    function resumeOnLeave() { startVisualAnimation() }
    if (dom && dom.addEventListener) {
      // 保存引用以便卸载时可以正确移除
      dom.__trend_pause = pauseOnHover
      dom.__trend_resume = resumeOnLeave
      dom.addEventListener('mouseenter', dom.__trend_pause)
      dom.addEventListener('mouseleave', dom.__trend_resume)
    }

    // 启动动画
    startVisualAnimation()
  } else {
    const dataValue = origin.map(item => ({ name: mapProvinceName(item.name), value: item.value }))
    chart.setOption(buildOption(dataValue))
  }

  chart.on('click', (param) => {
    const data = param.data
    if (data) {
      const coords = Array.isArray(data.value) ? data.value.join(', ') : data.value
      const cases = getCasesValue(data) ?? (data.cases ?? '-')
      console.log(`地区：${data.name}; 坐标：${coords}; 病例数：${cases}`)
    }
  })

  resizeHandler = () => {
    if (chart) try { chart.resize() } catch (e) {}
  }
  window.addEventListener('resize', resizeHandler)
}

onMounted(() => { init().catch(err => console.error('初始化失败:', err)) })
onBeforeUnmount(() => {
  // 停止并清理动画
  try {
    if (animFrame) cancelAnimationFrame(animFrame)
  } catch (e) {}
  animFrame = null
  animState = null
  try {
    if (typeof animTimeout !== 'undefined' && animTimeout) {
      clearTimeout(animTimeout)
      animTimeout = null
    }
  } catch (e) {}

  // 移除悬停事件监听（如果有）
  try {
    const dom = chartRef.value
    if (dom && dom.removeEventListener) {
      if (dom.__trend_pause) dom.removeEventListener('mouseenter', dom.__trend_pause)
      if (dom.__trend_resume) dom.removeEventListener('mouseleave', dom.__trend_resume)
      delete dom.__trend_pause
      delete dom.__trend_resume
    }
  } catch (e) {}

  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (chart) chart.dispose()
})
</script>

<style scoped>
.fusion-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 80vh; /* 给地图和 sankey 更多垂直空间 */
  background-color: transparent;
}
.map-chart {
  position: relative;
  width: 100%;
  height: 55%; /* 地图部分占上方 55% 高度 */
}
.sales-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 300px;
  max-height: calc(100vh - 32px);
  background: rgba(0,0,0,0.35);
  color: #fff;
  border-radius: 8px;
  overflow: hidden;
  backdrop-filter: blur(2px);
}
.panel-header {
  padding: 10px 12px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255,255,255,0.15);
}
.panel-body {
  padding: 8px 12px;
  max-height: calc(100vh - 64px);
  overflow: auto;
}
table { width: 100%; color: #fff; }
th, td { padding: 6px 8px; font-size: 12px; }
thead th { position: sticky; top: 0; background: rgba(0,0,0,0.45); }
/* 浮动饼图已移除 */

.sankey-chart {
  position: relative;
  width: calc(100% - 48px);
  height: 40%;
  margin: 12px 24px;
  background: rgba(255,255,255,0.95);
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.12);
  padding: 8px;
  z-index: 10;
}
</style>