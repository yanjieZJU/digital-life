import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const apiBase = process.env.VITE_EMPLOYEE_CONSOLE_API_BASE || '/api/employee'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 用绝对 base `/` 保证 /system、/instance/{iid} 等子路径下都能找到 /assets/*
  // 副作用：开发模式必须挂在根路径 /，server.proxy 提供本地后端转发。
  base: '/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,  // 方便定位运行时错误（建议仅在 dev/调试期开启，生产可关）
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8642',
        changeOrigin: true,
      },
      [apiBase]: {
        target: 'http://127.0.0.1:8642',
        changeOrigin: true,
      }
    }
  }
})

