import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      },
      '/model': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        // 将 /model/* 重写为 /api/*，例如 /model/predict -> /api/predict
        rewrite: (path) => path.replace(/^\/model/, '/api')
      },
    },
  },
})
