<template>
  <div class="new3-wrapper">
    <div class="toolbar mb-2 d-flex gap-2 align-items-center">
      <label class="mb-0">维度：</label>
      <select v-model="dim" class="form-select form-select-sm" style="width:160px">
        <option value="age">年龄分布</option>
        <option value="gender">性别</option>
        <option value="season">季节</option>
        <option value="clinical">临床结果</option>
  <option value="social">社会活动因素</option>
  <option value="death_rate">死亡率（Death/总数）</option>
  <option value="recovery_rate">康复率（Recovered/总数）</option>
  <option value="hospitalized_rate">住院率（Hospitalized/总数）</option>
  <option value="combined_rates">住院/死亡/康复 率汇总</option>
  <option value="vaccinated">接种影响（Vaccinated %）</option>
  <option value="travel_history">旅行史影响（Travel_History %）</option>
  <option value="quarantined">隔离影响（Quarantined %）</option>
  <option value="symptom_fever">发热比例（Symptom_Fever %）</option>
  <option value="symptom_cough">咳嗽比例（Symptom_Cough %）</option>
  <option value="symptom_rash">皮疹比例（Symptom_Rash %）</option>
  <option value="days_hospitalized">平均住院天数（Days_Hospitalized）</option>
  <option value="symptoms_and_days">症状与平均住院天数对比（发热/咳嗽/皮疹 + 平均住院天数）</option>
  <option value="urban_rural">城乡差异（Urban_Rural）</option>
  <option value="time_trend">按月/年时间趋势（Month/Year）</option>
      </select>

      <label class="mb-0 ms-3">显示模式：</label>
      <select v-model="mode" class="form-select form-select-sm" style="width:140px">
        <option value="overlay">叠加对比</option>
        <option value="facet">并列展示</option>
      </select>

      <label class="mb-0 ms-3">病种：</label>
      <select v-model="disease" class="form-select form-select-sm" style="width:180px">
        <option :value="null">全部病种</option>
        <option v-for="d in diseaseList" :key="d" :value="d">{{ displayDiseaseName(d) }}</option>
      </select>

      <!-- 当选择平均住院天数维度时，允许在矩形树图与旭日图之间切换 -->
      <div v-if="dim === 'days_hospitalized'" class="ms-3 d-flex align-items-center">
        <label class="mb-0 me-2">展示：</label>
        <div class="btn-group btn-group-sm" role="group">
          <button :class="['btn', daysViewMode === 'treemap' ? 'btn-primary' : 'btn-outline-secondary']" @click.prevent="setDaysView('treemap')">矩形树图</button>
          <button :class="['btn', daysViewMode === 'sunburst' ? 'btn-primary' : 'btn-outline-secondary']" @click.prevent="setDaysView('sunburst')">旭日图</button>
        </div>
      </div>

      <div class="ms-auto">
        <button class="btn btn-sm btn-outline-secondary me-1" @click="resetView">重置视图</button>
      </div>
    </div>

    <div ref="chartEl" class="chart" style="height:420px"></div>
    <div v-if="tablePreview" class="preview-table mt-3">
      <div style="overflow:auto; max-width:100%">
        <table class="table table-sm table-bordered">
          <thead>
            <tr>
              <th style="white-space:nowrap">地区 \ 病种</th>
              <th v-for="d in tablePreview.diseases" :key="d" style="white-space:nowrap">{{ displayDiseaseName(d) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in tablePreview.rows" :key="r.region">
              <td style="white-space:nowrap">{{ r.region }}</td>
              <td v-for="cell in r.cells" :key="cell" style="white-space:nowrap">
                <div>{{ cell.num }}</div>
                <div style="color:rgba(0,0,0,0.5); font-size:0.85em">
                  <!-- when tablePreview.isTimeTrend is true, show raw number instead of percent -->
                  <span v-if="tablePreview.isTimeTrend">{{ cell.pct }}</span>
                  <span v-else>{{ cell.pct }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { computed } from 'vue'
import * as echarts from 'echarts'

// Register a 'vintage' theme based on `vintage.project.json` to apply colors/background globally.
const VINTAGE_THEME = {
  color: [
    '#d87c7c', '#919e8b', '#d7ab82', '#6e7074', '#61a0a8', '#efa18d', '#787464', '#cc7e63', '#724e58', '#4b565b'
  ],
  backgroundColor: 'rgba(254,248,239,1)',
  textStyle: { color: '#333' },
  title: { textStyle: { color: '#333333' }, subtextStyle: { color: '#aaaaaa' } },
  legend: { textStyle: { color: '#333333' } },
  visualMap: { color: ['#bf444c','#d88273','#f6efa6'] }
}
try{ echarts.registerTheme && echarts.registerTheme('vintage', VINTAGE_THEME) }catch(e){ /* ignore if already registered */ }

// 疾病英文->中文映射，用于在 UI 中显示中文病名
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

function displayDiseaseName(key){
  if (!key) return key
  if (DISEASE_NAME_MAP[key]) return DISEASE_NAME_MAP[key]
  // try case-insensitive match
  const lower = String(key).toLowerCase()
  for (const k of Object.keys(DISEASE_NAME_MAP)){
    if (k.toLowerCase() === lower) return DISEASE_NAME_MAP[k]
  }
  return key
}

// 季节英文->中文映射
const SEASON_NAME_MAP = { 'Winter': '冬季', 'Spring': '春季', 'Summer': '夏季', 'Autumn': '秋季', 'Fall': '秋季' }
function displaySeasonName(k){
  if (!k) return k
  if (SEASON_NAME_MAP[k]) return SEASON_NAME_MAP[k]
  const upper = String(k).charAt(0).toUpperCase() + String(k).slice(1)
  return SEASON_NAME_MAP[upper] || String(k)
}

// tooltip formatter helper: show raw/total when available
function makeTooltipFormatter() {
  return function (params) {
    // axis tooltip: params is array
    if (Array.isArray(params)) {
      let out = ''
      for (const p of params) {
        const name = p.seriesName || p.name
        const data = p.data || p
        if (data && data.raw != null && data.total != null) {
          const pct = data.total ? ((data.raw / data.total) * 100).toFixed(1) : '0.0'
          out += `${name} — ${p.name}: ${data.raw}/${data.total} (${pct}%)<br/>`
        } else {
          out += `${name} — ${p.name}: ${p.value || 0}<br/>`
        }
      }
      return out
    }
    // item tooltip: params is object
    const p = params
    const name = p.seriesName || p.name
    const data = p.data || p
    if (data && data.raw != null && data.total != null) {
      const pct = data.total ? ((data.raw / data.total) * 100).toFixed(1) : '0.0'
      return `${name} — ${p.name}: ${data.raw}/${data.total} (${pct}%)`
    }
    return `${name} — ${p.name}: ${p.value || 0}`
  }
}

const props = defineProps({
  regionsData: { type: Array, required: true },
  selectedRegions: { type: Array, required: true }
})

const chartEl = ref(null)
let chart = null
const dim = ref('age')
const mode = ref('overlay')
const disease = ref(null)
const diseaseList = ref([])
  const tablePreview = ref(null)
const daysViewMode = ref('treemap')

function setDaysView(m){ daysViewMode.value = m; try{ update() }catch(e){} }

// normalized form of selected regions (array of region name strings) for robust matching
const selectedRegionsNormalized = ref([])

// helper: prefer backend-provided per-disease total when available,
// otherwise fall back to summing the distribution buckets
function getBucketTotal(r, diseaseSel, dist) {
  if (diseaseSel && r && r.by_disease && r.by_disease[diseaseSel] && typeof r.by_disease[diseaseSel].total !== 'undefined') {
    return Number(r.by_disease[diseaseSel].total) || 0
  }
  return Object.values(dist || {}).reduce((s, v) => s + (Number(v) || 0), 0)
}

function resetView(){ if (chart) chart.dispatchAction({type:'restore'}) }

function buildOption(regions, dim, mode, diseaseSel){
  if(!regions || regions.length===0) return { title: {text:'无数据'} }

  // helper: fuzzy key lookup (case-insensitive) inside an object
  function pickKey(obj, candidates){
    if (!obj || typeof obj !== 'object') return undefined
    const keys = Object.keys(obj)
    const lowerKeys = keys.reduce((m,k)=>{ m[k.toLowerCase()] = k; return m }, {})
    for (const c of candidates){
      if (!c) continue
      const lk = String(c).toLowerCase()
      if (lowerKeys[lk]) return obj[lowerKeys[lk]]
    }
    return undefined
  }

  // Get per-disease metric for a single region. Tries multiple places (by_disease[d], then top-level fields)
  function getRegionDiseaseMetric(region, diseaseKey, metricCandidates){
    try{
      if (!region) return { num:0, denom:0 }
      // per-disease object
      const by = region.by_disease && (region.by_disease[diseaseKey] || region.by_disease[String(diseaseKey)])
      // use null to represent "not found" so we don't confuse with an actual zero value
      let num = null
      let denom = by && (by.total || by.total_cases || by.totalCount) ? Number(by.total || by.total_cases || by.totalCount) : null

      // try to find numerator inside per-disease record
      if (by) {
        const v = pickKey(by, metricCandidates)
        if (typeof v === 'number' || (!isNaN(Number(v)) && v !== null)) num = Number(v)

        // sometimes clinical/social buckets hold the metric
        if (num == null && by.clinical) {
          const vv = pickKey(by.clinical, metricCandidates)
          if (typeof vv === 'number' || (!isNaN(Number(vv)) && vv !== null)) num = Number(vv)
        }
        if (num == null && by.social) {
          const vv = pickKey(by.social, metricCandidates)
          if (typeof vv === 'number' || (!isNaN(Number(vv)) && vv !== null)) num = Number(vv)
        }

        // special-case: travel_history / quarantined fields are objects mapping categories to counts
        // prefer the 'Yes' count when computing rates
        // IMPORTANT: only use these fallbacks when the requested metric candidates indicate
        // we're actually looking for travel_history or quarantined, otherwise they may
        // accidentally be used for other metrics and cause different dims to appear identical.
        try {
          const lcCandidates = (Array.isArray(metricCandidates) ? metricCandidates : []).map(c => String(c || '').toLowerCase())
          const wantsTravel = lcCandidates.some(c => c.includes('travel'))
          const wantsQuarant = lcCandidates.some(c => c.includes('quarant') || c.includes('is_quarant'))

          if (num == null && wantsTravel && by.travel_history && typeof by.travel_history === 'object'){
            if (by.travel_history['Yes'] != null) num = Number(by.travel_history['Yes'])
            else if (by.travel_history['yes'] != null) num = Number(by.travel_history['yes'])
          }
          if (num == null && wantsQuarant && by.quarantined && typeof by.quarantined === 'object'){
            if (by.quarantined['Yes'] != null) num = Number(by.quarantined['Yes'])
            else if (by.quarantined['yes'] != null) num = Number(by.quarantined['yes'])
          }
        } catch(e) { /* defensive: if something odd happens, don't break rendering */ }

        // symptoms: if metricCandidates reference a specific symptom (fever/cough/rash), check by.symptoms
        if (num == null && by.symptoms && typeof by.symptoms === 'object'){
          // look for symptom keys among metricCandidates
          for (const cand of metricCandidates){
            if (!cand) continue
            const lk = String(cand).toLowerCase()
            if (lk.includes('fever') && by.symptoms['fever'] != null){ num = Number(by.symptoms['fever']); break }
            if (lk.includes('cough') && by.symptoms['cough'] != null){ num = Number(by.symptoms['cough']); break }
            if (lk.includes('rash') && by.symptoms['rash'] != null){ num = Number(by.symptoms['rash']); break }
          }
        }

        // days_hospitalized: if per-disease days_hospitalized is an object with sum/count/avg, use avg or sum/count
        if (num == null && by.days_hospitalized && typeof by.days_hospitalized === 'object'){
          const dh = by.days_hospitalized
          if (dh.avg != null) {
            num = Number(dh.avg)
            // set denom to 1 so callers treat it as a scalar average
            denom = 1
          } else if (dh.sum != null && dh.count != null && dh.count > 0){
            num = Number(dh.sum)
            denom = Number(dh.count)
          }
        }
      }

      // fallback to region-level fields grouped by disease (rare)
      if (num == null && region[ diseaseKey ] && typeof region[diseaseKey] === 'object'){
        const maybe = pickKey(region[diseaseKey], metricCandidates)
        if (typeof maybe === 'number' || (!isNaN(Number(maybe)) && maybe !== null)) num = Number(maybe)
      }

      // region-level travel/quarantine/symptom/days fallbacks: prefer standardized 'Yes' keys or symptom buckets on region
      // IMPORTANT: when we're computing per-disease metrics (diseaseKey provided), do NOT fall back to region-level
      // aggregates because that would make per-disease comparisons show identical region totals. Only use these
      // fallbacks when no specific diseaseKey was requested.
      if (!diseaseKey) {
        if (num == null && region && region.travel_history && typeof region.travel_history === 'object'){
          if (region.travel_history['Yes'] != null) num = Number(region.travel_history['Yes'])
          else if (region.travel_history['yes'] != null) num = Number(region.travel_history['yes'])
        }
        if (num == null && region && region.quarantined && typeof region.quarantined === 'object'){
          if (region.quarantined['Yes'] != null) num = Number(region.quarantined['Yes'])
          else if (region.quarantined['yes'] != null) num = Number(region.quarantined['yes'])
        }
        if (num == null && region && region.symptoms && typeof region.symptoms === 'object'){
          for (const cand of metricCandidates){
            if (!cand) continue
            const lk = String(cand).toLowerCase()
            if (lk.includes('fever') && region.symptoms['fever'] != null){ num = Number(region.symptoms['fever']); break }
            if (lk.includes('cough') && region.symptoms['cough'] != null){ num = Number(region.symptoms['cough']); break }
            if (lk.includes('rash') && region.symptoms['rash'] != null){ num = Number(region.symptoms['rash']); break }
          }
        }
        if (num == null && region && region.days_hospitalized && typeof region.days_hospitalized === 'object'){
          const dh = region.days_hospitalized
          if (dh.avg != null){ num = Number(dh.avg); denom = 1 }
          else if (dh.sum != null && dh.count != null && dh.count > 0){ num = Number(dh.sum); denom = Number(dh.count) }
        }
      }

      // ultimate fallback: top-level aggregated columns on region
      // ONLY use top-level region aggregates when no specific diseaseKey was requested.
      // If we allow this when diseaseKey is provided, every disease may end up
      // showing the same region-level number (making per-disease comparison identical).
      if (num == null && !diseaseKey){
        const top = pickKey(region, metricCandidates)
        if (typeof top === 'number' || (!isNaN(Number(top)) && top !== null)) num = Number(top)
      }

      // denom fallback: if per-disease total not present, use per-disease buckets sum or region.by_disease[d].total computed earlier
      if (!denom){
        if (by) {
          // try sum of distributions if available
          const distKeys = ['age_distribution','gender','season','clinical','social']
          let s = 0
          for (const k of distKeys) {
            if (by[k] && typeof by[k] === 'object') {
              s = Object.values(by[k]).reduce((a,b)=>a + (Number(b)||0), 0)
              if (s>0) break
            }
          }
          if (s>0) denom = s
        }
      }
      // final fallback: region.total
      if (!denom) denom = Number(region.total || region.cnt || 0)

      // normalize null -> 0 for return
      return { num: Number(num==null?0:num), denom: Number(denom||0) }
    }catch(e){ return { num:0, denom:0 } }
  }

  // helper: collect union of diseases present in selected regions
  function collectDiseases(regions){
    const s = new Set()
    for (const r of regions){
      if (r.by_disease && typeof r.by_disease === 'object') Object.keys(r.by_disease).forEach(d=>s.add(d))
      if (Array.isArray(r.disease_list)) r.disease_list.forEach(d=>s.add(d))
    }
    return Array.from(s)
  }

  // helper: get distribution for a region and dimension
  const getDist = (r, dname, diseaseSel) => {
    // If a specific disease is selected, prefer per-disease buckets
    if (diseaseSel && r.by_disease && r.by_disease[diseaseSel]){
      const b = r.by_disease[diseaseSel]
      if (dname==='age' && b.age_distribution) return b.age_distribution
      if (dname==='gender' && b.gender) return b.gender
      if (dname==='season' && b.season) return b.season
      if (dname==='clinical' && b.clinical) return b.clinical
      if (dname==='social' && b.social) return b.social
    }

    // If no specific disease selected, attempt to aggregate across all diseases
    if (!diseaseSel && r.by_disease && typeof r.by_disease === 'object'){
      const agg = {}
      for (const kd of Object.keys(r.by_disease)){
        const b = r.by_disease[kd]
        let src = null
        if (dname==='age' && b.age_distribution) src = b.age_distribution
        if (dname==='gender' && b.gender) src = b.gender
        if (dname==='season' && b.season) src = b.season
        if (dname==='clinical' && b.clinical) src = b.clinical
        if (dname==='social' && b.social) src = b.social
        if (!src) continue
        for (const k of Object.keys(src)){
          agg[k] = (agg[k] || 0) + (Number(src[k]) || 0)
        }
      }
      // if we have aggregated values, return them
      if (Object.keys(agg).length) return agg
    }

    // fallbacks to precomputed aggregate buckets on region
    if (dname==='age' && r.age_distribution) return r.age_distribution
    if (dname==='gender' && r.gender) return r.gender
    if (dname==='season' && r.season) return r.season
    if (dname==='clinical' && r.clinical) return r.clinical
    if (dname==='social' && r.social) return r.social
    return {}
  }

  if(dim==='clinical'){
    // 新样式：两个南丁格尔玫瑰图（Yes 的一个，No 的一个），按病种为切片，保留按省份查看功能
    const diseases = collectDiseases(regions)
    if (diseases.length === 0) return { title:{ text:'无病种数据' } }

    const yesData = []
    const noData = []
    for (const d of diseases){
      let yesSum = 0, noSum = 0
      for (const r of regions){
        const by = r.by_disease && (r.by_disease[d] || r.by_disease[String(d)])
        if (by && by.clinical && typeof by.clinical === 'object'){
          yesSum += Number(by.clinical['Yes'] || by.clinical['yes'] || 0)
          noSum += Number(by.clinical['No'] || by.clinical['no'] || 0)
        }
      }
      yesData.push({ value: Math.max(0, Number(yesSum||0)), name: displayDiseaseName(d) })
      noData.push({ value: Math.max(0, Number(noSum||0)), name: displayDiseaseName(d) })
    }

    const series = [
      { name: 'Yes', type: 'pie', radius: [40, 160], center: ['25%', '50%'], roseType: 'area', data: yesData, label: { show: true } },
      { name: 'No', type: 'pie', radius: [40, 160], center: ['75%', '50%'], roseType: 'area', data: noData, label: { show: true } }
    ]
    return { tooltip:{ trigger:'item' }, legend:{ bottom:0, data: diseases.map(d=>displayDiseaseName(d)) }, series }
  }

  // ---- age dimension (fixed 4 buckets) ----
  if (dim === 'age'){
    // 年龄分布：极坐标柱状图（每个 region 一条 series，angleAxis 为固定年龄段）
    const fixedAgeLabels = ['0-14','15-24','25-44','45+']
    // 收集每个 region 对应的数值（绝对值），为 polar 图构建 series
    const series = regions.map(r=>{
      const dist = getDist(r,'age', diseaseSel)
      const data = fixedAgeLabels.map(l=>{
        let val = Number(dist[l] || 0)
        if (l === '45+' && val === 0) val = Number(dist['45-64'] || 0) + Number(dist['65+'] || 0)
        return Math.max(0, Number(val||0))
      })
      return { name: r.region, type: 'bar', data, coordinateSystem: 'polar', stack: 'age' }
    })

    return {
      tooltip: { trigger: 'item', formatter: function(params){
        if (Array.isArray(params)) return params.map(p=>`${p.seriesName} — ${fixedAgeLabels[p.dataIndex]}: ${p.data}`).join('\n')
        return `${params.seriesName} — ${fixedAgeLabels[params.dataIndex]}: ${params.data}`
      }},
      legend: { data: regions.map(r=>r.region) },
      angleAxis: { type: 'category', data: fixedAgeLabels },
      radiusAxis: { },
      polar: { radius: [30, '75%'] },
      series
    }
  }

  if(dim==='gender'){
    const series = []
    if (mode === 'facet'){
      // vertical stacking of pies
      const step = Math.max(1, Math.floor(80 / Math.max(1, regions.length)))
      for(let i=0;i<regions.length;i++){
        const r = regions[i]
        const dist = getDist(r,'gender', diseaseSel)
        const total = getBucketTotal(r, diseaseSel, dist)
        const data = Object.keys(dist || {}).map(k=>({name:k, value: total ? (Number(dist[k]||0) / total) : 0, raw: Number(dist[k]||0), total }))
        series.push({ name: r.region, type: 'pie', radius: 50, center: ['50%', `${10 + i*step}%`], data })
      }
    } else {
      // overlay/horizontal layout (original behavior)
      const step = Math.max(1, Math.floor(80 / Math.max(1, regions.length)))
      for(let i=0;i<regions.length;i++){
        const r = regions[i]
        const dist = getDist(r,'gender', diseaseSel)
        const total = getBucketTotal(r, diseaseSel, dist)
        const data = Object.keys(dist || {}).map(k=>({name:k, value: total ? (Number(dist[k]||0) / total) : 0, raw: Number(dist[k]||0), total }))
        series.push({ name: r.region, type: 'pie', radius: 60, center: [`${10 + i*step}%`, '50%'], data })
      }
    }
    return { tooltip:{ trigger:'item', formatter: makeTooltipFormatter() }, legend:{ show:false }, series }
  }

  if(dim==='season'){
    // 新样式：折线图，横轴为月份（若 regions 中包含 monthly 数据则使用），纵轴为病例百分数
    // fallback: 原有 season 行为
    // collect months from monthly fields (prefer), otherwise fall back to season buckets
    const monthsSet = new Set()
    for (const r of regions){
      if (r.by_disease){
        for (const d of Object.keys(r.by_disease)){
          const per = r.by_disease[d]
          if (per && per.monthly && typeof per.monthly === 'object') Object.keys(per.monthly).forEach(m=>monthsSet.add(m))
        }
      }
      if (r.monthly && typeof r.monthly === 'object') Object.keys(r.monthly).forEach(m=>monthsSet.add(m))
    }
    const monthsRaw = Array.from(monthsSet)
    // if we have monthly data, render as a gradient stacked area chart (per your example)
    if (monthsRaw.length>0){
      function parseMonthKey(k){
        if (!k) return NaN
        const iso = String(k).trim()
        const cleaned = iso.replace(/年|\s+/g,'-').replace(/月/g,'').replace(/\//g,'-')
        try{ if (/\d{4}-\d{1,2}(?:-\d{1,2})?$/.test(cleaned)){ const d=new Date(cleaned); if(!isNaN(d)) return d.getTime() } }catch(e){}
        const parsed = Date.parse(iso)
        if (!isNaN(parsed)) return parsed
        const m = iso.match(/(\d{4}).*?(\d{1,2})/)
        if (m){ const y=Number(m[1]), mo=Number(m[2]); if(!isNaN(y)&&!isNaN(mo)) return new Date(y,mo-1,1).getTime() }
        return NaN
      }
      const monthObjs = monthsRaw.map(m => ({ raw: m, ts: parseMonthKey(m) }))
      const sortable = monthObjs.filter(x=> !isNaN(x.ts)).sort((a,b)=> a.ts - b.ts).map(x=>x.raw)
      const unsortable = monthObjs.filter(x=> isNaN(x.ts)).map(x=>x.raw)
      const monthArr = sortable.concat(unsortable)

      // colors (re-use palette from example, repeat/cycle if more regions)
      const baseColors = ['#80FFA5', '#00DDFF', '#37A2FF', '#FF0087', '#FFBF00']
      const series = regions.map((r, idx)=>{
        const vals = monthArr.map(m=>{
          let s = 0
          // 如果选择了具体病种，则优先使用该病种的 per-disease monthly 数据
          if (diseaseSel) {
            const per = r.by_disease && (r.by_disease[diseaseSel] || r.by_disease[String(diseaseSel)])
            if (per && per.monthly && typeof per.monthly === 'object') {
              s = Number(per.monthly[m] || 0)
            } else if (r.monthly && typeof r.monthly === 'object') {
              // 若该 region 没有按病种的 monthly，则回退到 region 级别的 monthly
              s = Number(r.monthly[m] || 0)
            }
          } else {
            // 未选择病种：聚合所有病种的 monthly（保留原有行为）
            for (const d of Object.keys(r.by_disease || {})){
              const per = r.by_disease[d]
              if (per && per.monthly && typeof per.monthly === 'object') s += Number(per.monthly[m] || 0)
            }
            if (r.monthly && typeof r.monthly === 'object') s += Number(r.monthly[m] || 0)
          }
          return s
        })
        const colorIdx = idx % baseColors.length
        // create a simple gradient per series by rotating base colors
        const g1 = baseColors[colorIdx]
        const g2 = baseColors[(colorIdx+1) % baseColors.length]
        return {
          name: r.region,
          type: 'line',
          stack: 'Total',
          smooth: true,
          lineStyle: { width: 0 },
          showSymbol: false,
          areaStyle: {
            opacity: 0.8,
            color: new echarts.graphic.LinearGradient(0,0,0,1,[{ offset:0, color: g1 }, { offset:1, color: g2 }])
          },
          emphasis: { focus: 'series' },
          data: vals
        }
      })

      return {
        color: baseColors,
        tooltip:{ trigger:'axis', axisPointer: { type:'cross', label: { backgroundColor: '#6a7985' } }, formatter: makeTooltipFormatter() },
        legend: { data: regions.map(r=>r.region) },
        xAxis: { type:'category', boundaryGap: false, data: monthArr },
        yAxis: { type:'value' },
        series
      }
    }

    // otherwise fallback to season buckets (percent)
    const keySet = new Set()
    for (const r of regions){ const d = getDist(r,'season', diseaseSel); Object.keys(d||{}).forEach(k=>keySet.add(k)) }
    const keysRaw = Array.from(keySet)
    const labels = keysRaw.map(k=> displaySeasonName(k))
    // fallback: use stacked bars per season (each region is a stacked series)
    const series = regions.map(r=>{
      const dist = getDist(r,'season',diseaseSel)
      const data = keysRaw.map(k=> Number(dist[k] || 0) )
      return { name: r.region, type: 'bar', stack: 'regions', data }
    })
    return { tooltip:{ trigger:'axis', formatter: makeTooltipFormatter() }, legend:{ data: regions.map(r=>r.region) }, xAxis:{ type: 'category', data: labels }, yAxis: { type: 'value', name: '病例数' }, series }
  }



  if(dim==='social'){
    // 新样式：两个极坐标图（Yes 的一个，No 的一个），极坐标轴为疾病（百分数/数值），保留按省份查看功能
    const diseases = collectDiseases(regions)
    if (diseases.length === 0) return { title:{ text:'无病种数据' } }

    const yesSeriesVals = []
    const noSeriesVals = []
    for (const d of diseases){
      let yesSum = 0, noSum = 0
      for (const r of regions){
        const by = r.by_disease && (r.by_disease[d] || r.by_disease[String(d)])
        if (by && by.social && typeof by.social === 'object'){
          yesSum += Number(by.social['Yes'] || by.social['yes'] || 0)
          noSum += Number(by.social['No'] || by.social['no'] || 0)
        }
      }
      yesSeriesVals.push(Math.max(0, Number(yesSum||0)))
      noSeriesVals.push(Math.max(0, Number(noSum||0)))
    }

    const option = {
      polar: { radius: [30, '80%'] },
      angleAxis: { type: 'category', data: diseases.map(d=>displayDiseaseName(d)) },
      radiusAxis: { axisLabel: { formatter: v => v } },
      tooltip: {},
      series: [
        { type: 'bar', data: yesSeriesVals, coordinateSystem: 'polar', name: 'Yes', label: { show: true } },
        { type: 'bar', data: noSeriesVals, coordinateSystem: 'polar', name: 'No', label: { show: true } }
      ],
      legend: { data: ['Yes','No'] }
    }
    return option
  }

  // ----- 新增维度: 基于 per-disease 指标的对比图（按病种为 X 轴，按所选区域为 series） -----
  const perDiseaseDims = ['death_rate','recovery_rate','hospitalized_rate','vaccinated','travel_history','quarantined','symptom_fever','symptom_cough','symptom_rash','days_hospitalized']
  // 合并显示症状(发热/咳嗽/皮疹)与平均住院天数的专用维度
  if (dim === 'symptoms_and_days'){
    // Prefer direct aggregation from per-disease `by_disease[d]` when available.
    // For each disease we sum per-region per-disease symptom raw counts and per-disease totals
    // to compute a combined fraction. For days_hospitalized we compute a weighted average
    // by converting avg -> sum using per-disease total when necessary.
    const diseases = collectDiseases(regions)
    if (diseases.length === 0) return { title:{ text:'无病种数据' } }

    const feverData = []
    const coughData = []
    const rashData = []
    const daysData = []

    for (const d of diseases){
      let fever_num = 0, fever_den = 0
      let cough_num = 0, cough_den = 0
      let rash_num = 0, rash_den = 0
      let days_sum = 0, days_count = 0

      for (const reg of regions){
        const by = reg && reg.by_disease && (reg.by_disease[d] || reg.by_disease[String(d)])

        if (by){
          const per_total = Number(by.total || by.total_cases || by.totalCount) || 0
          // symptoms
          if (by.symptoms && typeof by.symptoms === 'object'){
            fever_num += Number(by.symptoms.fever || by.symptoms.Fever || 0)
            cough_num += Number(by.symptoms.cough || by.symptoms.Cough || 0)
            rash_num += Number(by.symptoms.rash || by.symptoms.Rash || 0)
            // use per-disease total as denominator contribution when available
            if (per_total > 0){
              fever_den += per_total
              cough_den += per_total
              rash_den += per_total
            }
          } else {
            // fallback to helper which tries other places (keeps backward compatibility)
            const f = getRegionDiseaseMetric(reg, d, ['Symptom_Fever','symptom_fever','fever'])
            const c = getRegionDiseaseMetric(reg, d, ['Symptom_Cough','symptom_cough','cough'])
            const rsh = getRegionDiseaseMetric(reg, d, ['Symptom_Rash','symptom_rash','rash'])
            fever_num += Number(f.num || 0); fever_den += Number(f.denom || 0)
            cough_num += Number(c.num || 0); cough_den += Number(c.denom || 0)
            rash_num += Number(rsh.num || 0); rash_den += Number(rsh.denom || 0)
          }

          // days_hospitalized: prefer sum/count; if only avg present, convert using per_total when possible
          if (by.days_hospitalized && typeof by.days_hospitalized === 'object'){
            const dh = by.days_hospitalized
            if (dh.sum != null && dh.count != null){
              days_sum += Number(dh.sum || 0)
              days_count += Number(dh.count || 0)
            } else if (dh.avg != null){
              // if we have per_total, treat avg as per-record average across per_total cases
              if (per_total > 0){
                days_sum += Number(dh.avg || 0) * per_total
                days_count += per_total
              } else {
                // no total info: fall back to treating avg as one observation
                days_sum += Number(dh.avg || 0)
                days_count += 1
              }
            }
          } else {
            // fallback: try helper
            const dh2 = getRegionDiseaseMetric(reg, d, ['Days_Hospitalized','days_hospitalized','avg_days_hospitalized','sum_days_hospitalized'])
            if (dh2.denom === 1){
              days_sum += Number(dh2.num || 0); days_count += 1
            } else {
              days_sum += Number(dh2.num || 0); days_count += Number(dh2.denom || 0)
            }
          }
        } else {
          // by_disease missing for this region/disease -> fallback to existing helper
          const f = getRegionDiseaseMetric(reg, d, ['Symptom_Fever','symptom_fever','fever'])
          const c = getRegionDiseaseMetric(reg, d, ['Symptom_Cough','symptom_cough','cough'])
          const rsh = getRegionDiseaseMetric(reg, d, ['Symptom_Rash','symptom_rash','rash'])
          fever_num += Number(f.num || 0); fever_den += Number(f.denom || 0)
          cough_num += Number(c.num || 0); cough_den += Number(c.denom || 0)
          rash_num += Number(rsh.num || 0); rash_den += Number(rsh.denom || 0)
          const dh2 = getRegionDiseaseMetric(reg, d, ['Days_Hospitalized','days_hospitalized','avg_days_hospitalized','sum_days_hospitalized'])
          if (dh2.denom === 1){ days_sum += Number(dh2.num || 0); days_count += 1 }
          else { days_sum += Number(dh2.num || 0); days_count += Number(dh2.denom || 0) }
        }
      }

      const f_frac = fever_den > 0 ? (fever_num / fever_den) : 0
      const c_frac = cough_den > 0 ? (cough_num / cough_den) : 0
      const r_frac = rash_den > 0 ? (rash_num / rash_den) : 0
      const avg_days = days_count > 0 ? (days_sum / days_count) : 0

      feverData.push({ value: Number(f_frac||0), raw: Number(fever_num||0), total: Number(fever_den||0) })
      coughData.push({ value: Number(c_frac||0), raw: Number(cough_num||0), total: Number(cough_den||0) })
      rashData.push({ value: Number(r_frac||0), raw: Number(rash_num||0), total: Number(rash_den||0) })
      daysData.push({ value: Number(avg_days||0), raw: Number(days_sum||0), total: Number(days_count||0) })
    }

    const labels = diseases.map(d=> displayDiseaseName(d))
    const series = [
      { name: '发热 %', type: 'bar', data: feverData },
      { name: '咳嗽 %', type: 'bar', data: coughData },
      { name: '皮疹 %', type: 'bar', data: rashData },
      { name: '平均住院天数', type: 'line', yAxisIndex: 1, data: daysData }
    ]

    return {
      tooltip: { trigger: 'axis', formatter: makeTooltipFormatter() },
      legend: { data: ['发热 %','咳嗽 %','皮疹 %','平均住院天数'] },
      xAxis: { type: 'category', data: labels },
      yAxis: [ { type: 'value', name: '百分比(%)', axisLabel: { formatter: v => (v*100).toFixed(0) + '%' } }, { type: 'value', name: '天数' } ],
      series
    }
  }
  if (perDiseaseDims.includes(dim)){
    // diseases on x axis, one series per region
    const diseases = collectDiseases(regions)
    if (diseases.length===0) return { title:{ text:'无病种数据' } }
    // define metric key candidates per dim
    const metricMap = {
      death_rate: ['Deaths','deaths','death','death_count','deaths_count'],
      recovery_rate: ['Recovered','recovered','recoveries','recovered_count'],
      hospitalized_rate: ['Hospitalized','hospitalized','hospitalisation','hospitalized_count'],
      vaccinated: ['Vaccinated','vaccinated','vaccination','vaccinated_count'],
      travel_history: ['Travel_History','travel_history','travelhistory','travel'],
      quarantined: ['Quarantined','quarantined','is_quarantined'],
      symptom_fever: ['Symptom_Fever','symptom_fever','fever'],
      symptom_cough: ['Symptom_Cough','symptom_cough','cough'],
      symptom_rash: ['Symptom_Rash','symptom_rash','rash'],
      days_hospitalized: ['Days_Hospitalized','days_hospitalized','avg_days_hospitalized','sum_days_hospitalized']
    }
    const candidates = metricMap[dim] || []
    // If we have a tablePreview built, prefer it as the authoritative source for per-disease numbers
    let series = []
      // Special-case: symptom dims should use direct per-disease symptom counts from the API when available
      if (dim && String(dim).toLowerCase().startsWith('symptom_')){
        const symptomKey = String(dim).toLowerCase().replace('symptom_','') // 'fever' | 'cough' | 'rash'
        series = regions.map(r=>{
          const values = diseases.map(d=>{
            const by = r.by_disease && (r.by_disease[d] || r.by_disease[String(d)])
            const num = by && by.symptoms && (by.symptoms[symptomKey] != null) ? Number(by.symptoms[symptomKey]) : 0
            // denom: prefer per-disease total, fallback to region.total
            const denom = by && (by.total || by.total_cases || by.totalCount) ? Number(by.total || by.total_cases || by.totalCount) : Number(r.total || r.cnt || 0)
            const frac = denom>0 ? (num/denom) : 0
            return { value: Number(frac||0), raw: Number(num||0), total: Number(denom||0) }
          })
          return { name: r.region, type: 'bar', data: values }
        })
        const labels = diseases.map(d=> displayDiseaseName(d))
        return {
          tooltip: { trigger: 'axis', formatter: makeTooltipFormatter() },
          legend: { data: regions.map(r=>r.region) },
          xAxis: { type: 'category', data: labels },
          yAxis: { type:'value', name:'百分比(%)', axisLabel: { formatter: v => (v*100).toFixed(0) + '%' } },
          series
        }
      }
    if (tablePreview && tablePreview.value && tablePreview.value.diseases && tablePreview.value.rows && tablePreview.value.diseases.length>0){
      // build series from tablePreview: rows correspond to regions in same order as `regions` filtered earlier
      const tp = tablePreview.value
      // ensure disease ordering matches `diseases`
      const tpDiseases = tp.diseases
      // map disease name -> index in tpDiseases
      const tpIndex = {}
      for (let i=0;i<tpDiseases.length;i++) tpIndex[tpDiseases[i]] = i
      series = regions.map(r=>{
        // find matching row for region
        const row = tp.rows.find(x=> x.region === (r.region || r.name || r.region_name || ''))
        const data = []
        for (const d of diseases){
          const idx = tpIndex[d]
          if (row && idx != null && row.cells && row.cells[idx]){
            const c = row.cells[idx]
            // value stored in pct as percent number (0-100) for preview; convert to fraction
            const frac = (typeof c.pct === 'number') ? (c.pct/100) : (c.total>0? (c.num/c.total) : 0)
            data.push({ value: Number(frac||0), raw: Number(c.num||0), total: Number(c.total||0) })
          } else {
            data.push({ value: 0, raw: 0, total: 0 })
          }
        }
        return { name: r.region, type: 'bar', data }
      })
    } else {
      series = regions.map(r=>{
        const values = diseases.map(d=>{
          const { num, denom } = getRegionDiseaseMetric(r, d, candidates)
          if (dim==='days_hospitalized'){
            if (denom>0) {
              const avg = (num/denom) || 0
              return { value: avg, raw: Number(num||0), total: Number(denom||0) }
            }
            return { value: 0, raw: Number(num||0), total: Number(denom||0) }
          }
          const frac = denom>0 ? (num/denom) : 0
          return { value: Number(frac||0), raw: Number(num||0), total: Number(denom||0) }
        })
        return { name: r.region, type: 'bar', data: values }
      })
    }
    // DEBUG: 输出用于绘图的疾病列表与每个 region 的前十个数据点，便于浏览器控制台比对
  // no-op debug removed in production build
    const labels = diseases.map(d=> displayDiseaseName(d))
    // If the selected metric is average days hospitalized, render either a treemap or a sunburst
    if (dim === 'days_hospitalized') {
      // compute weighted average days per disease across selected regions
      const treemapData = []
      for (const d of diseases) {
        let sum = 0
        let count = 0
        for (const r of regions) {
          const { num, denom } = getRegionDiseaseMetric(r, d, candidates)
          // getRegionDiseaseMetric for days may return num=sum and denom=count or avg with denom=1
          // We will treat denom==1 and num being avg as a single-observation avg only when no better info
          if (denom === 1 && num && r.by_disease && r.by_disease[d] && r.by_disease[d].days_hospitalized && r.by_disease[d].days_hospitalized.avg != null) {
            // this num is avg; try to recover per-disease total if available
            const per_total = Number((r.by_disease[d] && (r.by_disease[d].total || r.by_disease[d].total_cases || r.by_disease[d].totalCount)) || 0)
            if (per_total > 0) {
              sum += Number(r.by_disease[d].days_hospitalized.avg || 0) * per_total
              count += per_total
            } else {
              // no count info, count as single sample
              sum += Number(num || 0)
              count += 1
            }
          } else {
            sum += Number(num || 0)
            count += Number(denom || 0)
          }
        }
        const avg = count > 0 ? (sum / count) : 0
        treemapData.push({ name: displayDiseaseName(d), value: avg, raw: sum, total: count })
      }

      // If user selected treemap view
      if (daysViewMode && daysViewMode.value === 'treemap') {
        const tmOption = {
          title: { text: '平均住院天数（按病种）', left: 'center' },
          tooltip: { formatter: function(info){ const d = info.data || {}; return `${info.name}<br/>平均天数: ${Number(d.value||0).toFixed(2)} 天<br/>样本数: ${d.total||0}` } },
          series: [{
            name: '平均住院天数',
            type: 'treemap',
            roam: false,
            nodeClick: false,
            breadcrumb: { show: false },
            label: { show: true, formatter: '{b}\n{c} 天' },
            data: treemapData
          }]
        }
        return tmOption
      }

      // Otherwise render a sunburst using the same computed averages
      const sunburstChildren = treemapData.map(d => ({ name: d.name, value: Math.max(0, Number(d.value || 0)), raw: d.raw, total: d.total }))
      const sbOption = {
        title: { text: '平均住院天数（按病种） - 旭日图', left: 'center' },
        tooltip: { formatter: function(info){ const d = info.data || {}; return `${info.name}<br/>平均天数: ${Number(d.value||0).toFixed(2)} 天<br/>样本数: ${d.total||0}` } },
        series: [{
          type: 'sunburst',
          data: [{ name: '病种', children: sunburstChildren }],
          radius: [0, '75%'],
          label: { rotate: 'radial' }
        }]
      }
      return sbOption
    }

    // base option
    const opt = {
      tooltip: { trigger: 'axis', formatter: makeTooltipFormatter() },
      legend: { data: regions.map(r=>r.region) },
      xAxis: { type: 'category', data: labels },
      yAxis: (dim==='days_hospitalized') ? { type:'value', name:'天数' } : { type:'value', name:'百分比(%)', axisLabel: { formatter: v => (v*100).toFixed(0) + '%' } },
      series
    }

    // Add dynamic bar animation for specific binary/flag dims to match new4.vue example
    if (['travel_history','quarantined','vaccinated'].includes(dim)){
      // attach animationDelay per series (staggered by series index) and set easing/update behavior
      opt.series = opt.series.map((s, si) => ({
        ...s,
        animationDelay: function(idx){ return idx * 10 + si * 100 }
      }))
      opt.animationEasing = 'elasticOut'
      opt.animationDelayUpdate = function(idx){ return idx * 5 }
    }

    return opt
  }

  // combined_rates: combine hospitalized, recovery and death rates into one chart per disease
  if (dim === 'combined_rates'){
    const diseases = collectDiseases(regions)
    if (diseases.length === 0) return { title:{ text:'无病种数据' } }

    // metric candidate lists
    const metricMapLocal = {
      death_rate: ['Deaths','deaths','death','death_count','deaths_count'],
      recovery_rate: ['Recovered','recovered','recoveries','recovered_count'],
      hospitalized_rate: ['Hospitalized','hospitalized','hospitalisation','hospitalized_count']
    }

    const hospVals = []
    const recVals = []
    const deathVals = []

    for (const d of diseases){
      // aggregate across selected regions
      let hosp_num = 0, hosp_den = 0
      let rec_num = 0, rec_den = 0
      let death_num = 0, death_den = 0
      for (const r of regions){
        const h = getRegionDiseaseMetric(r, d, metricMapLocal.hospitalized_rate)
        const re = getRegionDiseaseMetric(r, d, metricMapLocal.recovery_rate)
        const de = getRegionDiseaseMetric(r, d, metricMapLocal.death_rate)
        hosp_num += Number(h.num || 0); hosp_den += Number(h.denom || 0)
        rec_num += Number(re.num || 0); rec_den += Number(re.denom || 0)
        death_num += Number(de.num || 0); death_den += Number(de.denom || 0)
      }
      // compute fractions (use denom when available, otherwise try to use total aggregated denom)
      const hosp_frac = (hosp_den>0) ? (hosp_num / hosp_den) : 0
      const rec_frac = (rec_den>0) ? (rec_num / rec_den) : 0
      const death_frac = (death_den>0) ? (death_num / death_den) : 0

      // push percentage numbers (0-100). Use negative for deaths to show leftward bars.
      hospVals.push(Number((hosp_frac*100).toFixed(2)))
      recVals.push(Number((rec_frac*100).toFixed(2)))
      deathVals.push(Number(( -death_frac*100 ).toFixed(2)))
    }

    const labels = diseases.map(d=> displayDiseaseName(d))
    const option = {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: function(params){
        // params is an array
        let out = ''
        for (const p of params){
          const val = p.value
          const name = p.seriesName
          // show absolute percent with sign for death
          out += `${name} — ${p.name}: ${Math.abs(Number(val)).toFixed(2)}%<br/>`
        }
        return out
      }},
      legend: { data: ['住院率','康复率','死亡率'] },
      xAxis: [{ type: 'value', axisLabel: { formatter: v => `${v}` } }],
      yAxis: [{ type: 'category', axisTick: { show: false }, data: labels }],
      series: [
        { name: '住院率', type: 'bar', label: { show: true, position: 'inside' }, emphasis: { focus: 'series' }, data: hospVals },
        { name: '康复率', type: 'bar', stack: 'Total', label: { show: true }, emphasis: { focus: 'series' }, data: recVals },
        { name: '死亡率', type: 'bar', stack: 'Total', label: { show: true, position: 'left' }, emphasis: { focus: 'series' }, data: deathVals }
      ]
    }
    return option
  }

  // urban_rural: show urban vs rural ratio per disease (stacked bars per disease)
  if (dim === 'urban_rural'){
    const diseases = collectDiseases(regions)
    if (diseases.length===0) return { title:{ text:'无病种数据' } }
    // NOTE: urban_rural should come from per-disease data (r.by_disease[d].urban_rural).
    // Do NOT fall back to region-level `r.urban_rural` here — that would mix province-level
    // aggregates into per-disease comparisons.
    const urbSeries = regions.map(r=>{
      const values = diseases.map(d=>{
        // read urban/rural distribution ONLY from per-disease bucket
        const by = r.by_disease && (r.by_disease[d] || r.by_disease[String(d)])
        let urb = 0, rur = 0, total = 0
        if (by && by.urban_rural){
          urb = Number(by.urban_rural.Urban || by.urban_rural.urban || by.urban_rural['城镇'] || 0)
          rur = Number(by.urban_rural.Rural || by.urban_rural.rural || by.urban_rural['农村'] || 0)
          total = urb + rur
        }
        return total>0 ? +( (urb/total)*100 ).toFixed(2) : 0
      })
      return { name: r.region, type:'bar', stack: 'urban', data: values }
    })
    const rurSeries = regions.map((r,i)=>{
      const values = diseases.map(d=>{
        const by = r.by_disease && (r.by_disease[d] || r.by_disease[String(d)])
        let urb = 0, rur = 0, total = 0
        if (by && by.urban_rural){
          urb = Number(by.urban_rural.Urban || by.urban_rural.urban || by.urban_rural['城镇'] || 0)
          rur = Number(by.urban_rural.Rural || by.urban_rural.rural || by.urban_rural['农村'] || 0)
          total = urb + rur
        }
        return total>0 ? +( (rur/total)*100 ).toFixed(2) : 0
      })
      return { name: r.region + ' (Rural)', type:'bar', stack: 'urban', data: values }
    })
    const series = [...urbSeries, ...rurSeries]
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: series.map(s=>s.name) },
      xAxis: { type:'category', data: collectDiseases(regions).map(d=>displayDiseaseName(d)) },
      yAxis: { type:'value', name:'%'},
      series
    }
  }

  // time_trend: aggregate monthly/yearly counts per disease across selected regions
  if (dim === 'time_trend'){
    // collect months/years from regions' by_disease breakdown or top-level monthly
    // and sort them chronologically (support multiple common formats)
    const monthsSet = new Set()
    const diseases = collectDiseases(regions)
    for (const r of regions){
      if (r.by_disease){
        for (const d of Object.keys(r.by_disease)){
          const per = r.by_disease[d]
          if (per && per.monthly && typeof per.monthly === 'object') Object.keys(per.monthly).forEach(m=>monthsSet.add(m))
        }
      }
      if (r.monthly && typeof r.monthly === 'object') Object.keys(r.monthly).forEach(m=>monthsSet.add(m))
    }
    // normalize and sort months: try to parse to Date; if parsing fails, keep original order
    const monthsRaw = Array.from(monthsSet)
    if (monthsRaw.length===0) return { title:{ text:'无时间序列数据' } }

    function parseMonthKey(k){
      if (!k) return NaN
      // try ISO-like YYYY-MM or YYYY-MM-DD or YYYY/MM
      const iso = String(k).trim()
      // replace Chinese '年'/'月' and slashes with hyphen, remove whitespace
      const cleaned = iso.replace(/年|\s+/g,'-').replace(/月/g,'').replace(/\//g,'-')
      // try Date parse for cleaned string
      try{
        if (/\d{4}-\d{1,2}(?:-\d{1,2})?$/.test(cleaned)){
          const d = new Date(cleaned)
          if (!isNaN(d)) return d.getTime()
        }
      }catch(e){}
      const parsed = Date.parse(iso)
      if (!isNaN(parsed)) return parsed
      // try to extract YYYY and MM
      const m = iso.match(/(\d{4}).*?(\d{1,2})/)
      if (m){
        const y = Number(m[1]), mo = Number(m[2])
        if (!isNaN(y) && !isNaN(mo)) return new Date(y, mo-1, 1).getTime()
      }
      return NaN
    }

    const monthObjs = monthsRaw.map(m => ({ raw: m, ts: parseMonthKey(m) }))
    // keep sortable entries first, then append unsortable in stable order
    const sortable = monthObjs.filter(x=> !isNaN(x.ts)).sort((a,b)=> a.ts - b.ts).map(x=>x.raw)
    const unsortable = monthObjs.filter(x=> isNaN(x.ts)).map(x=>x.raw)
    const monthArr = sortable.concat(unsortable)

    // Build series data per disease
    const series = diseases.map(d=>{
      const vals = monthArr.map(m=>{
        let s = 0
        for (const r of regions){
          if (r.by_disease && r.by_disease[d] && r.by_disease[d].monthly && typeof r.by_disease[d].monthly === 'object'){
            s += Number(r.by_disease[d].monthly[m] || 0)
          } else if (r.monthly && typeof r.monthly === 'object'){
            s += Number(r.monthly[m] || 0)
          }
        }
        return s
      })
      return { name: displayDiseaseName(d), type:'line', data: vals }
    })

    return { tooltip:{ trigger:'axis' }, legend:{ data: series.map(s=>s.name) }, xAxis:{ type:'category', data: monthArr }, yAxis:{ type:'value' }, series }
  }

  return { title:{ text:'暂不支持的维度' } }
}

function update(){
  if(!chart) return
  // If selectedRegions is provided and explicitly empty -> show blank/placeholder
  let selNames = []
  if (Array.isArray(props.selectedRegions)){
    if (props.selectedRegions.length === 0){
      // explicit empty selection -> still build tablePreview so user can inspect raw data,
      // but keep chart as placeholder
      try{ tablePreview.value = buildTablePreview(props.regionsData, dim.value, disease.value) }catch(e){ tablePreview.value = null }
      // normalize selected for debugging
      selectedRegionsNormalized.value = []
      chart.setOption({ title: { text: '未选择任何地区' }, series: [] }, { notMerge: true })
      return
    }
    // support selectedRegions as array of strings OR objects ({ region: 'Sichuan' })
    selNames = props.selectedRegions.map(s => (typeof s === 'string' ? s : (s && (s.region || s.name || s.region_name) ? (s.region || s.name || s.region_name) : String(s))))
  } else {
    selNames = (props.regionsData || []).map(r=>r.region)
  }
  selectedRegionsNormalized.value = selNames
  const rd = props.regionsData.filter(d=> selNames.includes(d.region))
  const opt = buildOption(rd, dim.value, mode.value, disease.value)
  chart.setOption(opt, { notMerge: true })
  // build table preview for current selection/dim
  try{
  tablePreview.value = buildTablePreview(rd, dim.value, disease.value)
  }catch(e){ tablePreview.value = null }
}

// build a small table data structure: diseases[], rows: [{ region, cells:[{num, denom}] }]
function buildTablePreview(regions, dimName, diseaseSel){
  // only meaningful when there are regions
  if (!regions || regions.length===0) return null
  // we support per-disease style dims and also symptom dims
  const perDiseaseDims = ['death_rate','recovery_rate','hospitalized_rate','vaccinated','travel_history','quarantined','symptom_fever','symptom_cough','symptom_rash','days_hospitalized']
  // collect diseases
  const diseases = collectDiseases(regions)
  if (diseases.length===0) return null

  // metricMap same as in buildOption
  const metricMap = {
    death_rate: ['deaths','Deaths','death','death_count','deaths_count'],
    recovery_rate: ['Recovered','recovered','recoveries','recovered_count'],
    hospitalized_rate: ['Hospitalized','hospitalized','hospitalisation','hospitalized_count'],
    vaccinated: ['Vaccinated','vaccinated','vaccination','vaccinated_count'],
    travel_history: ['Travel_History','travel_history','travelhistory','travel'],
    quarantined: ['Quarantined','quarantined','is_quarantined'],
    symptom_fever: ['Symptom_Fever','symptom_fever','fever'],
    symptom_cough: ['Symptom_Cough','symptom_cough','cough'],
    symptom_rash: ['Symptom_Rash','symptom_rash','rash'],
    days_hospitalized: ['Days_Hospitalized','days_hospitalized','avg_days_hospitalized','sum_days_hospitalized']
  }
  const candidates = metricMap[dimName] || []

  const rows = regions.map(r => {
    const cells = diseases.map(d => {
      const { num, denom } = getRegionDiseaseMetric(r, d, candidates)
      const pct = denom>0 ? (num/denom)*100 : (denom===1? num : 0)
      return { num: Number(num||0), denom: Number(denom||0), pct: Number((isFinite(pct)?pct:0).toFixed(2)) }
    })
    return { region: r.region || r.name || r.region_name || '', cells }
  })

  // Special-case: when dimName is time_trend, produce a table with diseases as rows and months as columns
  if (dimName === 'time_trend'){
    // collect months same as buildOption
    const monthsSet = new Set()
    for (const r of regions){
      if (r.by_disease){
        for (const d of Object.keys(r.by_disease)){
          const per = r.by_disease[d]
          if (per && per.monthly && typeof per.monthly === 'object') Object.keys(per.monthly).forEach(m=>monthsSet.add(m))
        }
      }
      if (r.monthly && typeof r.monthly === 'object') Object.keys(r.monthly).forEach(m=>monthsSet.add(m))
    }
    const monthsRaw = Array.from(monthsSet)
    function parseMonthKey(k){
      if (!k) return NaN
      const iso = String(k).trim()
      const cleaned = iso.replace(/年|\s+/g,'-').replace(/月/g,'').replace(/\//g,'-')
      try{ if (/\d{4}-\d{1,2}(?:-\d{1,2})?$/.test(cleaned)){ const d=new Date(cleaned); if(!isNaN(d)) return d.getTime() } }catch(e){}
      const parsed = Date.parse(iso)
      if (!isNaN(parsed)) return parsed
      const m = iso.match(/(\d{4}).*?(\d{1,2})/)
      if (m){ const y=Number(m[1]), mo=Number(m[2]); if(!isNaN(y)&&!isNaN(mo)) return new Date(y,mo-1,1).getTime() }
      return NaN
    }
    const monthObjs = monthsRaw.map(m=>({ raw:m, ts: parseMonthKey(m) }))
    const sortable = monthObjs.filter(x=> !isNaN(x.ts)).sort((a,b)=>a.ts-b.ts).map(x=>x.raw)
    const unsortable = monthObjs.filter(x=> isNaN(x.ts)).map(x=>x.raw)
    const monthArr = sortable.concat(unsortable)

    // build rows: one row per disease, cells per month
    const tRows = diseases.map(d=>{
      const cells = monthArr.map(m=>{
        let s = 0
        for (const r of regions){
          if (r.by_disease && r.by_disease[d] && r.by_disease[d].monthly && typeof r.by_disease[d].monthly === 'object'){
            s += Number(r.by_disease[d].monthly[m] || 0)
          } else if (r.monthly && typeof r.monthly === 'object'){
            s += Number(r.monthly[m] || 0)
          }
        }
        return { num: Number(s||0), denom: 0, pct: Number(s||0) }
      })
      return { region: displayDiseaseName(d), cells }
    })
    return { diseases: monthArr, rows: tRows, isTimeTrend: true }
  }

  return { diseases, rows }
}

onMounted(()=>{
  // initialize chart with the registered 'vintage' theme so colors/background apply
  try{
    chart = echarts.init(chartEl.value, 'vintage')
  }catch(e){
    // fallback if theme registration failed for any reason
    chart = echarts.init(chartEl.value)
  }
  // compute disease list from provided data and initialize
  function computeDiseaseList(){
    const list = new Set()
    for (const r of props.regionsData || []){
      if (r.by_disease && typeof r.by_disease === 'object'){
        Object.keys(r.by_disease).forEach(d=>list.add(d))
      }
      if (Array.isArray(r.disease_list)) r.disease_list.forEach(d=>list.add(d))
    }
    const arr = Array.from(list)
    diseaseList.value = arr
    if (arr.length && !disease.value) disease.value = arr[0]
  }
  computeDiseaseList()
  update()
  window.addEventListener('resize', ()=>chart && chart.resize())
})

watch(()=>[props.regionsData, props.selectedRegions, dim.value, mode.value, disease.value, daysViewMode.value], ()=>{
  // recompute disease list when regionsData changes
  const prev = diseaseList.value.slice()
  const list = new Set()
  for (const r of props.regionsData || []){
    if (r.by_disease && typeof r.by_disease === 'object') Object.keys(r.by_disease).forEach(d=>list.add(d))
    if (Array.isArray(r.disease_list)) r.disease_list.forEach(d=>list.add(d))
  }
  const arr = Array.from(list)
  diseaseList.value = arr
  // Only auto-select a default disease if the current selection is not explicitly null
  // (null is our sentinel for "全部病种" and should not be overwritten).
  if (arr.length && (disease.value !== null && !arr.includes(disease.value))) disease.value = arr[0]
  update()
}, { deep:true })
</script>

<style scoped>
.new3-wrapper { width: 100% }
.chart { width: 100%; }
.toolbar { padding: 6px }
</style>
<style scoped>
.preview-table { padding: 6px 0 }
</style>
