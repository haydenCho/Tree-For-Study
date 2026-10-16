import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 서버가 /api를 백엔드로 프록시한다. 그래서 브라우저는 운영(Caddy)과 동일하게
// 같은 출처의 VITE_API_BASE_URL=/api를 사용한다.
const backendOrigin = process.env.BACKEND_ORIGIN || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: backendOrigin,
        changeOrigin: true,
      },
    },
  },
})
