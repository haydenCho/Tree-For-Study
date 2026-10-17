// 2단계 E2E: 운영자 도서관 IP 등록·휴무/대면 지정 → 출석 체크 → 도서관 시작 세션 →
// 공동 숲 배치·소유자 카드 → 팀원 공개 WBS/기록 → 공개 해제 시 사라짐.
import { expect, test } from '@playwright/test'
import {
  OP,
  approve,
  backdateSession,
  expectNoHorizontalOverflow,
  login,
  logoutViaMyPage,
  pickCells,
  register,
  sessionIdFromUrl,
  setMinutes,
} from './helpers.js'

const stamp = Date.now()
const a = { email: `alice-${stamp}@e2e.local`, realName: '앨리스' }
const b = { email: `bob-${stamp}@e2e.local`, realName: '밥' }
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date())

test.describe.serial('2단계 흐름', () => {
  test('두 멤버 가입·승인 후 표시 이름 설정', async ({ page }) => {
    for (const m of [a, b]) await register(page, m)
    for (const m of [a, b]) await approve(page, m.email)
    for (const [m, name] of [
      [a, '앨리스숲'],
      [b, '밥나무'],
    ]) {
      await login(page, m.email)
      await page.goto('/me')
      await page.getByLabel(/^표시 이름/).fill(name)
      await page.getByLabel(/^소개/).fill(`${name}의 소개`)
      await page.getByRole('button', { name: '프로필 저장' }).click()
      await expect(page.getByText('프로필을 저장했어요.')).toBeVisible()
      await logoutViaMyPage(page)
    }
  })

  test('운영자: 접속 IP 진단 → 도서관 등록, 오늘을 대면일로 지정', async ({ page }) => {
    await login(page, OP.email, OP.password)
    await page.goto('/admin')
    await expect(page.getByText('서버가 본 접속 IP')).toBeVisible()
    await page.getByRole('button', { name: '현재 접속 IP 채우기' }).click()
    await page.getByLabel('IP 또는 CIDR').locator('..').getByRole('textbox').first().isVisible()
    await page.getByRole('button', { name: '등록', exact: true }).click()
    await expect(page.getByText('도서관 주소를 등록했어요.')).toBeVisible()
    await expect(page.getByText('도서관으로 인식됨')).toBeVisible()
    await page.getByLabel('날짜').fill(today)
    await page.getByRole('button', { name: '대면일로 지정' }).click()
    await expect(page.getByText(/대면일로 지정했어요/)).toBeVisible()
  })

  test('멤버: 출석 체크 + 도서관에서 시작한 세션은 장식 나무', async ({ page }) => {
    await login(page, a.email)
    await page.getByRole('button', { name: '출석 체크' }).click()
    await expect(page.getByRole('button', { name: /오늘 출석 완료/ })).toBeVisible()
    await expect(page.getByText(/도서관 네트워크로 인식돼요/)).toBeVisible()
    await setMinutes(page, 20)
    await pickCells(page, 1)
    await page.getByRole('button', { name: '집중 시작' }).click()
    await expect(page).toHaveURL(/\/focus\//)
    await expect(page.locator('.focus-top')).toContainText('도서관 장식')
    await backdateSession(sessionIdFromUrl(page), 20 * 60)
    await expect(page.getByRole('heading', { name: '한 번의 집중이 숲에 남았어요.' })).toBeVisible({ timeout: 30_000 })
    await page.getByRole('button', { name: '대시보드로 돌아가기' }).last().click()
    await expect(page.locator('.forest [aria-label*="도서관 장식 나무"]')).toHaveCount(1)
  })

  test('기록 공개 → 다른 멤버가 광장에서 보고 공개 해제 시 사라짐', async ({ page }) => {
    await login(page, a.email)
    await page.goto(`/records/${today}`)
    await page.getByLabel('오늘 계획').fill('S3 스토리지 클래스 정리')
    await page.getByLabel('스터디 멤버에게 이 날짜 기록 공개').check()
    await page.getByRole('button', { name: '저장', exact: true }).click()
    await expect(page.getByText(/공개 중/)).toBeVisible()
    await logoutViaMyPage(page)

    await login(page, b.email)
    await page.goto('/plaza')
    await expect(page.getByRole('heading', { name: '함께 자라는 공동 숲' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
    // 공동 숲 나무에 focus → 소유자 카드(표시 이름, 실명·이메일 없음)
    const tree = page.locator('.community-forest button.tile[aria-label*="앨리스숲"]').first()
    await tree.focus()
    const card = page.getByRole('dialog', { name: '나무 주인' })
    await expect(card).toContainText('앨리스숲')
    await expect(card).not.toContainText('앨리스@')
    await expect(page.locator('body')).not.toContainText(a.email)
    await page.keyboard.press('Escape')
    await expect(card).toHaveCount(0)

    await page.getByText('S3 스토리지 클래스 정리').isVisible()
    await page.locator('.feed-item', { hasText: 'S3 스토리지 클래스 정리' }).getByRole('link', { name: '열기' }).click()
    await expect(page.getByText('MEMBER RECORD · 읽기 전용')).toBeVisible()
    await expect(page.getByText('S3 스토리지 클래스 정리')).toBeVisible()
    const recordUrl = page.url()

    // 팀원 카드 → 공개 WBS(읽기 전용) 캘린더
    await page.goto('/plaza')
    await page.getByRole('link', { name: '앨리스숲의 공개 WBS 보기' }).click()
    await expect(page.getByText('MEMBER CALENDAR · 읽기 전용')).toBeVisible()
    await expect(page.getByText('공개된 WBS가 없어요.')).toBeVisible()
    await logoutViaMyPage(page)

    await login(page, a.email)
    await page.goto(`/records/${today}`)
    await page.getByLabel('스터디 멤버에게 이 날짜 기록 공개').uncheck()
    await page.getByRole('button', { name: '저장', exact: true }).click()
    await expect(page.getByText(/나만 보기/)).toBeVisible()
    await logoutViaMyPage(page)

    await login(page, b.email)
    await page.goto(recordUrl)
    await expect(page.getByText('공개된 기록이 없어요.')).toBeVisible()
    await page.goto('/plaza')
    await expect(page.getByText('S3 스토리지 클래스 정리')).toHaveCount(0)
  })

  for (const width of [390, 360]) {
    test(`광장 모바일 ${width}px: 가로 넘침 없음, tap으로 소유자 카드`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 })
      await login(page, b.email)
      await page.goto('/plaza')
      await expectNoHorizontalOverflow(page)
      await page.locator('.community-forest button.tile:not([disabled])').first().click()
      await expect(page.getByRole('dialog', { name: '나무 주인' })).toBeVisible()
      await page.screenshot({ path: `screenshots/plaza-${width}.png`, fullPage: true })
    })
  }
})
