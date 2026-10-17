import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 서버가 /api를 백엔드로 프록시한다. 그래서 브라우저는 운영(Caddy)과 동일하게
// 같은 출처의 VITE_API_BASE_URL=/api를 사용한다.
const backendOrigin = process.env.BACKEND_ORIGIN || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  // 이모지 데이터(약 900KB)는 선택기를 열 때만 지연 로드되는 의도된 큰 청크다.
  build: { chunkSizeWarningLimit: 1000 },
  server: {
    host: true,
    port: 5173,
    // 개발 전용: compose 네트워크의 E2E 컨테이너가 http://frontend:5173 으로 접속한다.
    allowedHosts: ['localhost', 'frontend'],
    proxy: {
      '/api': {
        target: backendOrigin,
        changeOrigin: true,
      },
    },
  },
})
