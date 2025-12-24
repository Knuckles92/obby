import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    hmr: {
      port: 3001,
      host: 'localhost',
    },
    watch: {
      usePolling: false,
      interval: 100,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
        ws: true, // Enable WebSocket proxying
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, res) => {
            // Handle proxy errors gracefully for SSE streams
            if (res && !res.headersSent) {
              res.writeHead(500, {
                'Content-Type': 'text/plain',
              })
              res.end('Proxy error: ' + err.message)
            }
          })
          proxy.on('proxyReq', (proxyReq, req, res) => {
            // Set longer timeout for SSE streams
            if (req.url?.includes('/stream') || req.url?.includes('/events')) {
              proxyReq.setTimeout(0) // No timeout for SSE streams
            } else {
              proxyReq.setTimeout(300000) // 5 minutes for regular requests
            }
          })
        },
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData',
        'dist/'
      ]
    }
  }
})