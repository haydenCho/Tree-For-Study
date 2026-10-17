// E2E 공용 helper. 시간 경과는 실제로 기다리지 않고, 테스트 하네스가 E2E 전용 DB의
// 세션 시각을 과거로 옮겨 흉내 낸다(운영 API에는 시간 조작 기능이 없다).
import pg from 'pg'
import { expect } from '@playwright/test'

export const PASSWORD = 'e2e-member-password-1'
export const OP = { email: process.env.OP_EMAIL, password: process.env.OP_PASSWORD }
export const INVITE = process.env.INVITE_CODE

function dsn() {
  return (process.env.DATABASE_URL || '').replace('postgresql+asyncpg://', 'postgresql://')
}

export async function sql(text, params = []) {
  const client = new pg.Client({ connectionString: dsn() })
  await client.connect()
  try {
    return (await client.query(text, params)).rows
  } finally {
    await client.end()
  }
}

// 진행 중 세션의 시작/구간/목표 시각을 seconds만큼 과거로 이동.
// 완료 워커가 중간 상태를 보지 않도록 두 UPDATE를 한 트랜잭션으로 묶는다.
export async function backdateSession(sessionId, seconds) {
  const iv = `${seconds} seconds`
  const client = new pg.Client({ connectionString: dsn() })
  await client.connect()
  try {
    await client.query('BEGIN')
    await client.query(
      `UPDATE focus_sessions SET started_at = started_at - $2::interval,
         current_interval_started_at = current_interval_started_at - $2::interval,
         target_end_at = target_end_at - $2::interval WHERE id = $1`,
      [sessionId, iv],
    )
    await client.query(
      `UPDATE focus_intervals SET started_at = started_at - $2::interval WHERE session_id = $1 AND ended_at IS NULL`,
      [sessionId, iv],
    )
    await client.query('COMMIT')
  } finally {
    await client.end()
  }
}

export async function login(page, email, password = PASSWORD) {
  await page.goto('/login')
  await page.getByLabel('이메일').fill(email)
  await page.getByLabel('비밀번호').fill(password)
  await page.getByRole('button', { name: '로그인', exact: true }).last().click()
  await expect(page).not.toHaveURL(/\/login$/)
}

export async function logoutViaMyPage(page) {
  await page.goto('/me')
  await page.getByRole('button', { name: '로그아웃' }).click()
  await expect(page).toHaveURL(/\/login$/)
}

export async function register(page, { email, realName }) {
  await page.goto('/register')
  await page.getByLabel('초대 코드').fill(INVITE)
  await page.getByLabel('이메일 (로그인 ID)').fill(email)
  await page.getByLabel(/^실명/).fill(realName)
  await page.getByLabel(/^비밀번호 \(/).fill(PASSWORD)
  await page.getByLabel('비밀번호 확인').fill(PASSWORD)
  await page.getByRole('button', { name: '가입 신청' }).click()
  await expect(page.getByText('가입 신청이 접수되었어요.')).toBeVisible()
}

export async function approve(page, email) {
  await login(page, OP.email, OP.password)
  await expect(page.getByRole('heading', { name: /오늘의 집중이/ })).toBeVisible()
  await page.goto('/admin')
  const row = page.locator('.admin-row', { hasText: email }).first()
  await row.getByRole('button', { name: '승인' }).click()
  await expect(page.getByText('승인했어요.')).toBeVisible()
  await logoutViaMyPage(page)
}

// 숲의 빈 칸을 n개 선택(행 우선)
export async function pickCells(page, n, skip = 0) {
  const tiles = page.locator('.forest button.tile:not([disabled])[aria-label$="빈 칸"]')
  for (let i = 0; i < n; i += 1) await tiles.nth(skip).click()
}

export async function setMinutes(page, minutes) {
  await page.getByLabel('공부(분)').fill(String(minutes))
}

export function sessionIdFromUrl(page) {
  return page.url().split('/focus/')[1]
}

// 문서 전체에 가로 스크롤이 생기지 않는지
export async function expectNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)
}
