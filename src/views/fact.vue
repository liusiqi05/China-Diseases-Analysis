<template>
  <div class="details-page">
    <div class="page-header mb-4">
      <h1 class="display-4 mb-2">
        <i class="bi bi-info-circle text-warning"></i>
        细节展示
      </h1>
      <p class="lead text-muted">展示 TransUNet 的模块细节、注意事项与中间特征图</p>
    </div>

    <div class="row">
      <div class="col-6">
        <div class="card border-0 shadow-sm mb-4">
          <div class="card-header bg-white">
            <h5 class="mb-0">Transformer 编码器细节</h5>
          </div>
          <div class="card-body">
            <p class="text-muted">展示每个 Transformer block 的注意力头数、维度与残差连接结构。</p>
            <pre class="small bg-light p-3">{ "num_layers": 12, "hidden_dim": 768, "num_heads": 12 }</pre>
          </div>
        </div>
      </div>
      <div class="col-6">
        <div class="card border-0 shadow-sm mb-4">
          <div class="card-header bg-white">
            <h5 class="mb-0">UNet 解码器细节</h5>
          </div>
          <div class="card-body">
            <p class="text-muted">展示 skip-connections、上采样方式以及每层通道数。</p>
            <pre class="small bg-light p-3">{ "decoder_channels": [512,256,128,64] }</pre>
          </div>
        </div>
      </div>
    </div>

    <div class="row">
      <div class="col-12">
        <div class="card border-0 shadow-sm">
          <div class="card-header bg-white d-flex align-items-center justify-content-between">
            <h5 class="mb-0">交互式推理演示</h5>
            <div>
              <button class="btn btn-outline-secondary btn-sm" @click="resetState" :disabled="loading">重置</button>
            </div>
          </div>
          <div class="card-body">
            <p class="text-muted">上传一张医学图像（PNG/JPG），后端将调用已训练的 TransUNet 模型进行分割，并返回叠加可视化。</p>

            <div class="mb-3">
              <input type="file" class="form-control" accept="image/*" @change="onFileChange" />
            </div>

                    <div class="d-flex gap-4 flex-wrap align-items-start three-previews">
                      <div class="preview-card">
                        <h6 class="text-muted">原图</h6>
                        <img v-if="inputUrl" :src="inputUrl" alt="input" class="img-fluid border" />
                        <div v-else class="placeholder">未选择图片</div>
                      </div>
                      <div class="preview-card">
                        <h6 class="text-muted">分割叠加</h6>
                        <div v-if="loading" class="text-secondary small"><i class="bi bi-hourglass-split"></i> 推理中…</div>
                        <img v-if="overlayUrl" :src="overlayUrl" alt="overlay" class="img-fluid border" />
                        <div v-else-if="!loading" class="placeholder">等待推理</div>
                      </div>
                      <div class="preview-card">
                        <h6 class="text-muted">图例 / 掩码示意</h6>
                        <img src="/assets/mask_legend.png" alt="mask legend" class="img-fluid border" />
                      </div>
                    </div>

            <div v-if="error" class="alert alert-danger mt-3">{{ error }}</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const inputUrl = ref('')
const overlayUrl = ref('')
const loading = ref(false)
const error = ref('')

function resetState() {
  inputUrl.value = ''
  overlayUrl.value = ''
  maskUrl.value = ''
  error.value = ''
}

async function onFileChange(e) {
  error.value = ''
  const file = e.target.files?.[0]
  if (!file) return
  inputUrl.value = URL.createObjectURL(file)

  const form = new FormData()
  form.append('file', file)
  loading.value = true
    try {
    const resp = await axios.post('/model/predict', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    overlayUrl.value = resp.data.overlay_data_url
  } catch (err) {
    error.value = '推理失败，请确认模型服务已启动并可用（后端 /model/predict）'
    console.error(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.details-page { padding-bottom: 2rem }
.page-header { background: linear-gradient(135deg,#ffd6a5 0%, #fdffb6 100%); color:#333; padding:1.25rem; border-radius:8px }
pre { overflow:auto }
.preview-card { min-width: 320px }
.placeholder { width:320px; height:200px; border:1px dashed #ccc; display:flex; align-items:center; justify-content:center; color:#999 }

/* Keep two preview cards visually consistent */
.two-previews .preview-card { min-width: 320px; max-width: 320px }
.two-previews .preview-card img { max-width: 100%; height: auto; display: block }

/* three previews layout */
.three-previews .preview-card { min-width: 320px; max-width: 320px }
.three-previews .preview-card img { max-width: 100%; height: auto; display: block }
</style>