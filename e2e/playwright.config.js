// Playwright 설정. 테스트는 순서대로(직렬) 실행한다: 운영자 승인 → 멤버 흐름이 이어진다.
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  outputDir: './test-results',
})
