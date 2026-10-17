// 운영 빌드 스모크 테스트 설정. 배포된 주소(PROD_BASE_URL)에 대해 읽기 위주로 확인한다.
//   PROD_BASE_URL=https://tree.example.com OP_EMAIL=... OP_PASSWORD=... npx playwright test --config prod.config.js
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './prod',
  workers: 1,
  timeout: 60_000,
  reporter: [['list']],
  use: {
    baseURL: process.env.PROD_BASE_URL || 'https://localhost',
    // 로컬 점검(Caddy 내부 CA 인증서)용. 실제 도메인에서는 정상 인증서라 영향 없음.
    ignoreHTTPSErrors: true,
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
  },
  outputDir: './test-results-prod',
})
