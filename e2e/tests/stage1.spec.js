// 1단계 E2E: 가입 → 승인 게이트 → 로그인 → 수종·칸 선택 → 시작 → pause/resume →
// 이탈 guard → 새로고침 복원 → 정상 완료 → 포기 → 일일 기록 공개 전환.
import { expect, test } from '@playwright/test'
import {
  approve,
  backdateSession,
  expectNoHorizontalOverflow,
  login,
  pickCells,
  register,
  sessionIdFromUrl,
  setMinutes,
} from './helpers.js'

const member = { email: `member-${Date.now()}@e2e.local`, realName: '김멤버' }

test.describe.serial('1단계 흐름', () => {
  test('가입 신청은 승인 전까지 대기 화면만 보인다', async ({ page }) => {
    await register(page, member)
    await login(page, member.email)
    await expect(page.getByRole('heading', { name: '운영자 승인을 기다리고 있어요.' })).toBeVisible()
    await page.goto('/plaza')
    await expect(page.getByRole('heading', { name: '운영자 승인을 기다리고 있어요.' })).toBeVisible()
  })

  test('운영자가 승인하면 대시보드에 들어갈 수 있다', async ({ page }) => {
    await approve(page, member.email)
    await login(page, member.email)
    await expect(page.getByRole('heading', { name: /오늘의 집중이/ })).toBeVisible()
    // 공통 헤더 없이 사이드바 D-day가 한 줄로 보인다.
    await expect(page.locator('.sidebar-deadline')).toContainText('시험까지')
  })

  test('세션 시작 → 일시정지/재개 → 이탈 확인 취소 → 새로고침 복원 → 정상 완료', async ({ page }) => {
    await login(page, member.email)
    await setMinutes(page, 40)
    await expect(page.locator('.reward')).toContainText('작은 나무 2그루')
    await page.getByRole('button', { name: '분홍 벚꽃' }).click()
    const start = page.getByRole('button', { name: /칸을 더 선택|집중 시작/ })
    await expect(start).toBeDisabled()
    await pickCells(page, 2)
    await expect(page.getByRole('button', { name: '집중 시작' })).toBeEnabled()
    await page.getByRole('button', { name: '집중 시작' }).click()
    await expect(page).toHaveURL(/\/focus\//)
    const sid = sessionIdFromUrl(page)
    await expect(page.locator('.sidebar')).toHaveCount(0)

    await page.getByRole('button', { name: '일시정지' }).click()
    await expect(page.getByText('잠시 쉬는 중')).toBeVisible()
    await page.getByRole('button', { name: '집중 재개' }).click()
    await expect(page.getByRole('button', { name: '일시정지' })).toBeVisible()

    // 뒤로 가기 → 포기 확인 → 계속 공부하기
    await page.goBack()
    await expect(page.getByRole('heading', { name: '정말 이번 집중을 포기할까요?' })).toBeVisible()
    await page.getByRole('button', { name: '계속 공부하기' }).click()
    await expect(page).toHaveURL(new RegExp(`/focus/${sid}`))

    // 새로고침 후에도 같은 세션으로 복원(브라우저 기본 경고는 자동 수락)
    page.on('dialog', (d) => d.accept())
    await page.reload()
    await expect(page.getByRole('button', { name: '일시정지' })).toBeVisible()
    // 다른 내부 주소를 직접 열어도 집중 화면으로 유도
    await page.goto('/records')
    await expect(page).toHaveURL(new RegExp(`/focus/${sid}`))

    await backdateSession(sid, 40 * 60)
    await expect(page.getByRole('heading', { name: '한 번의 집중이 숲에 남았어요.' })).toBeVisible({ timeout: 30_000 })
    await page.getByRole('button', { name: '휴식 시작 (10분)' }).click()
    await expect(page.getByText(/휴식 중/)).toBeVisible()
    await page.getByRole('button', { name: '대시보드로 돌아가기' }).last().click()
    await expect(page.locator('.forest [aria-label*="나무 · 위치 고정"]')).toHaveCount(2)
    await expect(page.locator('.stats')).toContainText('40분')
  })

  test('이탈 확인 후 서버 포기 → 회색 시든 나무', async ({ page }) => {
    await login(page, member.email)
    await setMinutes(page, 20)
    await pickCells(page, 1)
    await page.getByRole('button', { name: '집중 시작' }).click()
    await expect(page).toHaveURL(/\/focus\//)
    await page.goBack()
    await page.getByRole('button', { name: '포기하고 이동' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.locator('.forest [aria-label*="시든 나무"]')).toHaveCount(1)
    await expect(page.locator('.forest [aria-label*="나무 · 위치 고정"]')).toHaveCount(3)
  })

  test('중도 포기 버튼은 결과 화면을 보여 준다', async ({ page }) => {
    await login(page, member.email)
    await setMinutes(page, 20)
    await pickCells(page, 1)
    await page.getByRole('button', { name: '집중 시작' }).click()
    await page.getByRole('button', { name: '중도 포기' }).click()
    await page.getByRole('button', { name: '포기하기' }).click()
    await expect(page.getByRole('heading', { name: '이번 집중을 마쳤어요.' })).toBeVisible()
  })

  test('일일 기록 작성·목표·공개 전환이 저장된다', async ({ page }) => {
    await login(page, member.email)
    await page.getByRole('link', { name: '기록' }).first().click()
    await expect(page.getByRole('heading', { name: /의 기록$/ })).toBeVisible()
    await page.getByLabel('오늘 계획').fill('VPC 개념 정리')
    await page.getByLabel('목표 추가').fill('NAT 게이트웨이 문제 풀기')
    await page.getByRole('button', { name: '추가', exact: true }).click()
    await expect(page.getByText('NAT 게이트웨이 문제 풀기')).toBeVisible()
    await page.getByLabel('스터디 멤버에게 이 날짜 기록 공개').check()
    await page.getByRole('button', { name: '저장', exact: true }).click()
    await expect(page.getByText('저장했어요 · 스터디 멤버에게 공개 중')).toBeVisible()
    await page.reload()
    await expect(page.getByLabel('오늘 계획')).toHaveValue('VPC 개념 정리')
    await expect(page.getByLabel('스터디 멤버에게 이 날짜 기록 공개')).toBeChecked()
  })

  test('프로필 이모지 선택과 저장', async ({ page }) => {
    await login(page, member.email)
    await page.goto('/me')
    await page.getByRole('button', { name: /아바타 이모지 선택/ }).click()
    await page.getByLabel('검색').fill('tree')
    await page.locator('.emoji-option').first().click()
    await page.getByLabel(/^표시 이름/).fill('숲속멤버')
    await page.getByRole('button', { name: '프로필 저장' }).click()
    await expect(page.getByText('프로필을 저장했어요.')).toBeVisible()
  })

  for (const width of [1440, 1280, 390, 360]) {
    test(`대시보드 레이아웃 ${width}px: 가로 넘침 없음 + 키보드로 칸 선택`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await login(page, member.email)
      await expect(page.getByRole('heading', { name: /오늘의 집중이/ })).toBeVisible()
      await expectNoHorizontalOverflow(page)
      await setMinutes(page, 20)
      const tile = page.locator('.forest button.tile[aria-label$="빈 칸"]').first()
      await tile.focus()
      await page.keyboard.press('Enter')
      await expect(page.locator('.forest button.tile[aria-pressed="true"]')).toHaveCount(1)
      await page.screenshot({ path: `screenshots/dashboard-${width}.png`, fullPage: true })
      // 오디오/진동/알림 API를 쓰지 않는다
      const silent = await page.evaluate(() => {
        const src = [...document.scripts].map((s) => s.textContent).join('')
        return !/new Audio\(|navigator\.vibrate|Notification\.requestPermission/.test(src)
      })
      expect(silent).toBe(true)
    })
  }
})
