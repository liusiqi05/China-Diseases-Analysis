<template>
  <div class="chat-panel">
    <div class="chat-header">
      <h5>细节感知</h5>
      <small class="text-muted">对于2019-2023年这十个省份发生的传染病问题可以问我哦！</small>
    </div>

    <div class="chat-body" ref="bodyRef">
      <div v-for="(m, idx) in messages" :key="idx" :class="['msg', m.role]">
        <div class="msg-content">{{ m.text }}</div>
      </div>
    </div>

    <div class="chat-controls">
      <textarea v-model="input" placeholder="在此输入要发送给系统小助手的问题" rows="3"></textarea>
      <div class="controls-row">
        <button class="btn btn-sm btn-primary" :disabled="sending || !input.trim()" @click="send">发送</button>
        <button class="btn btn-sm btn-secondary" @click="clear">清除</button>
        <label style="margin-left:8px; display:flex; align-items:center; gap:6px;">
          <input type="checkbox" v-model="autoExecute" /> 自动执行模型生成的 SQL
        </label>
        <div class="spinner" v-if="sending">发送中…</div>
      </div>
      <div class="hint text-muted">小管家会一直陪着您</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'

const props = defineProps({ selectedPlace: { type: Object, default: null } })

const messages = ref([])
const input = ref('')
const sending = ref(false)
const autoExecute = ref(true) // 是否自动执行模型生成的 SQL
const bodyRef = ref(null)
const currentContext = ref(null)

function scrollToBottom(){
  nextTick(() => {
    try{ if(bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight }catch(e){}
  })
}

async function send(){
  const text = input.value.trim()
  if(!text) return
  messages.value.push({ role: 'user', text })
  input.value = ''
  sending.value = true
  scrollToBottom()

  // 自动两步流：1) 请求模型生成参数化 SQL；2) 如果返回 sql 则执行并向模型回传结果生成最终回答
  try{
    const genPayload = { question: text, table: 'china_disease_data' }
    if (currentContext.value) genPayload.context = currentContext.value

    messages.value.push({ role: 'system', text: '正在请求模型生成参数化 SQL...' })
    scrollToBottom()
    const genRes = await fetch('/api/ai_generate_sql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(genPayload) })

    if(!genRes.ok){
      // 若生成 SQL 失败，回退到普通聊天代理
      const txt = await genRes.text()
      messages.value.push({ role: 'system', text: '生成 SQL 失败，回退普通对话，原因: ' + genRes.status + ' ' + txt })
      // fallback
      await _fallbackChat(text)
      return
    }

    const genJ = await genRes.json()
    // 期望 { sql: '...', params: {...}, explain: '...'}
    if (!genJ || !genJ.sql){
      messages.value.push({ role: 'system', text: '模型未返回可执行的 SQL，回退普通对话' })
      await _fallbackChat(text)
      return
    }

    messages.value.push({ role: 'system', text: '模型生成 SQL: ' + genJ.sql + ' 参数: ' + JSON.stringify(genJ.params || {}) })
    scrollToBottom()

    // 如果开启自动执行则直接调用 execute_sql，否则显示 SQL 等待用户确认
    if (!autoExecute.value) {
      messages.value.push({ role: 'system', text: '自动执行被禁用。若要执行，请复制 SQL 并通过后端执行接口运行。' })
      return
    }

    // 执行 SQL
    messages.value.push({ role: 'system', text: '正在安全执行 SQL（只读）...' })
    const execPayload = { sql: genJ.sql, params: genJ.params || {}, max_rows: 200 }
    const execRes = await fetch('/api/execute_sql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(execPayload) })
    if(!execRes.ok){
      const t = await execRes.text()
      messages.value.push({ role: 'system', text: '执行 SQL 失败: ' + execRes.status + ' ' + t })
      // consider fallback
      await _fallbackChat(text)
      return
    }
    const execJ = await execRes.json()
    messages.value.push({ role: 'system', text: `查询返回 ${execJ.row_count || (execJ.rows && execJ.rows.length) || 0} 行；正在将结果发送给模型以生成自然语言回答...` })
    scrollToBottom()

    // 把执行结果发送给模型，获得最终回答
    const finalizePayload = { question: text, sql: genJ.sql, params: genJ.params || {}, result: execJ }
    const finRes = await fetch('/api/ai_sql_finalize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(finalizePayload) })
    if(!finRes.ok){
      const t = await finRes.text()
      messages.value.push({ role: 'system', text: '向模型请求最终回答失败: ' + finRes.status + ' ' + t })
      // fallback to chat
      await _fallbackChat(text)
      return
    }
    const finJ = await finRes.json()
    let reply = finJ.reply || (finJ.raw ? JSON.stringify(finJ.raw) : JSON.stringify(finJ))
    messages.value.push({ role: 'assistant', text: reply })

  } catch (e){
    messages.value.push({ role: 'system', text: '自动两步流出错: ' + (e && e.message ? e.message : String(e)) })
    // fallback to simple chat
    await _fallbackChat(text)
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

async function _fallbackChat(text){
  try{
    const payload = { message: text }
    if (currentContext.value) payload.context = currentContext.value
    const res = await fetch('/api/deepseek_chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if(!res.ok){
      const t = await res.text()
      messages.value.push({ role: 'system', text: '回退普通对话失败: ' + res.status + ' ' + t })
    } else {
      const j = await res.json()
      let reply = ''
      if (j.reply) reply = j.reply
      else if (j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content) reply = j.choices[0].message.content
      else reply = JSON.stringify(j)
      messages.value.push({ role: 'assistant', text: reply })
    }
  } catch (e){
    messages.value.push({ role: 'system', text: '回退普通对话请求出错: ' + (e && e.message ? e.message : String(e)) })
  }
}

// 当父组件选中某个地区时，自动把该地区摘要发送给后端 AI 作为上下文
async function sendRegionSummary(place) {
  if (!place) return
  try {
    const counts = place.counts || {}
    const total = Object.values(counts).reduce((s, v) => s + (Number(v) || 0), 0)
    // top 5 diseases
    const top = Object.keys(counts).map(k => ({ k, v: Number(counts[k] || 0) })).sort((a,b)=>b.v-a.v).slice(0,5)
    const summary = {
      name: place.name,
      lng: place.lng,
      lat: place.lat,
      total: total,
      top_diseases: top,
      counts: counts
    }
    messages.value.push({ role: 'system', text: `已选中地区：${place.name}，正在将摘要发送给小助手作为上下文...` })
    scrollToBottom()
  const payload = { message: `载入地区摘要: ${place.name}`, region_summary: summary }
    const res = await fetch('/api/deepseek_chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    if (!res.ok) {
      const t = await res.text()
      messages.value.push({ role: 'system', text: '将地区摘要发送到后端失败: ' + res.status + ' ' + t })
    } else {
      const j = await res.json()
      let reply = ''
      if (j.reply) reply = j.reply
      else if (j.raw) reply = JSON.stringify(j.raw)
      else reply = JSON.stringify(j)
      messages.value.push({ role: 'assistant', text: `助手（基于已载入摘要）: ${reply}` })
    }
    } catch (e) {
    messages.value.push({ role: 'system', text: '发送地区摘要出错: ' + (e && e.message ? e.message : String(e)) })
  } finally {
    // 将当前 context 缓存，后续手动发送问题时会携带该 context
    try { currentContext.value = summary } catch (e) { /* ignore */ }
    scrollToBottom()
  }
}

// 监听父组件传来的 selectedPlace
watch(() => props.selectedPlace, (nv, ov) => {
  if (nv && nv !== ov) sendRegionSummary(nv)
})

function clear(){ messages.value = [] }

onMounted(()=>{ messages.value.push({ role: 'system', text: '欢迎使用小管家对话面板。' }); scrollToBottom() })
</script>

<style scoped>
/* ChatPanel 专用背景样式：使用可自定义的 CSS 变量，默认是深色渐变 + 轻微纹理覆盖。*/
.chat-panel {
  display:flex;
  flex-direction:column;
  height:100%;
  border-radius:6px;
  padding:8px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.4);
  overflow: hidden;
  position: relative; /* for ::before overlay */

  /* 可通过 --chat-bg-image 覆盖背景（支持图片或渐变），示例： --chat-bg-image: url('/src/assets/chat-bg.jpg'); */
  --chat-bg-image: linear-gradient(135deg, rgba(2,12,27,0.72), rgba(12,28,56,0.72));
  background: var(--chat-bg-image);
  background-size: cover;
  background-position: center center;
  color: #eaeff6;
}

/* 轻微纹理/光斑覆盖，增强质感但不影响内容可读性 */
.chat-panel::before{
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  z-index: 0;
  /* 两个低透明度的径向渐变形成柔和光斑 */
  background-image:
    radial-gradient(circle at 10% 10%, rgba(255,255,255,0.02), transparent 12%),
    radial-gradient(circle at 90% 80%, rgba(255,255,255,0.01), transparent 14%);
}

/* 确保内容位于前景（高于 ::before） */
.chat-panel > * { position: relative; z-index: 1 }

.chat-header { padding:6px 8px; border-bottom: 1px solid rgba(255,255,255,0.04) }
.chat-body { flex:1 1 auto; overflow:auto; padding:8px; display:flex; flex-direction:column; gap:8px }
.msg { max-width:100%; padding:8px 10px; border-radius:8px; }
.msg.user { align-self:flex-end; background: rgba(24,144,255,0.14); color: #e6f7ff }
.msg.assistant { align-self:flex-start; background: rgba(0,0,0,0.28); color: #fff }
.msg.system { align-self:center; background: rgba(255,255,255,0.05); color:#ddd }
.chat-controls { padding:8px; border-top: 1px solid rgba(255,255,255,0.04) }
.chat-controls textarea { width:100%; resize:vertical; background: rgba(0,0,0,0.18); color:#fff; border: none; padding:8px; border-radius:4px }
.controls-row { display:flex; gap:8px; align-items:center; margin-top:6px }
.controls-row .spinner { color:#ddd; font-size:12px }
.hint { margin-top:6px; font-size:12px }

/* 可选：在深色背景下微调按钮亮度 */
.btn-primary { background-color: #177ddc; border-color: #177ddc }

</style>