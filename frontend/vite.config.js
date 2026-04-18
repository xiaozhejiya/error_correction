import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  plugins: [
    vue(),
    // 开发模式：将 /auth 和 /app 路径重写到 app.html（SPA 入口）
    {
      name: 'spa-html-rewrite',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const url = req.url?.split('?')[0]
          if (url === '/' || url === '/auth' || url === '/auth/login' || url === '/auth/register' || url === '/app' || url?.startsWith('/app/')) {
            req.url = '/app.html'
          }
          next()
        })
      },
    },
  ],
  test: {
    environment: 'jsdom',
  },
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/download': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/erased': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    manifest: false,
    // 新增多页面入口配置
    rollupOptions: {
      input: {
        app: resolve(__dirname, 'app.html')     // Vue SPA 入口（含落地页路由）
      }
    }
  },
})