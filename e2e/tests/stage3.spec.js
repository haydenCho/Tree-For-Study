// 3단계 E2E: 캘린더 날짜 → 정확한 일일 기록, WBS 생성·편집·공개, 드래그 시간표(역방향/겹침/이동/폼 대안),
// 주간 회고, 주말 보충, 모바일 레이아웃.
import { expect, test } from '@playwright/test'
import { approve, expectNoHorizontalOverflow, login, register } from './helpers.js'

const c = { email: `carol-${Date.now()}@e2e.local`, realName: '캐롤' }
const DAY = '2026-10-21'

// 시간표 좌표: 특정 분(minute)의 y, 레이어 열의 x
async function slotPoint(page, minute, layer) {
  const slot = page.locator('.time-slot').nth(minute / 15)
  await slot.scrollIntoViewIfNeeded()
  const box = await slot.boundingBox()
  const line = await page.locator('.timeline').boundingBox()
  const colW = (line.width - 48) / 2
  const x = line.x + 48 + (layer === 'plan' ? colW * 0.5 : colW * 1.5)
  return { x, y: box.y + box.height / 2 }
}

async function dragTimeline(page, fromMin, toMin, layer = 'actual') {
  const a = await slotPoint(page, fromMin, layer)
  const b = await slotPoint(page, toMin, layer)
  await page.mouse.move(a.x, a.y)
  await page.mouse.down()
  await page.mouse.move(b.x, (a.y + b.y) / 2, { steps: 4 })
  await page.mouse.move(b.x, b.y, { steps: 4 })
  await page.mouse.up()
}

test.describe.serial('3단계 흐름', () => {
  test('가입·승인', async ({ page }) => {
    await register(page, c)
    await approve(page, c.email)
  })

  test('캘린더 날짜 클릭 → 해당 날짜 기록', async ({ page }) => {
    await login(page, c.email)
    await page.goto('/calendar')
    await expect(page.locator('.month-nav strong')).toBeVisible()
    if ((await page.locator('.month-nav strong').textContent()) !== '2026년 10월') {
      await page.getByRole('button', { name: '이전 달' }).click()
    }
    await page.getByRole('link', { name: '10월 21일 대면' }).click()
    await expect(page).toHaveURL(new RegExp(`/records/${DAY}$`))
    await expect(page.getByRole('heading', { name: '10월 21일 (수)의 기록' })).toBeVisible()
  })

  test('WBS 생성(상위/하위)·편집·공개', async ({ page }) => {
    await login(page, c.email)
    await page.goto('/calendar')
    await page.getByText('+ 작업 추가').click()
    await page.getByLabel('제목').fill('AWS SAA')
    await page.getByLabel('스터디 멤버에게 이 항목 공개').check()
    await page.getByRole('button', { name: '추가', exact: true }).click()
    await expect(page.getByText('WBS를 추가했어요.')).toBeVisible()
    await page.getByText('+ 작업 추가').click()
    await page.getByLabel('제목').fill('VPC 오답')
    await page.getByLabel('상위 과제').selectOption({ label: 'AWS SAA' })
    await page.getByLabel('시작일').fill('2026-10-21')
    await page.getByLabel('종료일').fill('2026-10-24')
    await page.getByRole('button', { name: '추가', exact: true }).click()
    await expect(page.locator('.wbs-row.child')).toContainText('VPC 오답')
    // 하위 작업을 상위 기간 밖으로 → 서버 거부 메시지
    await page.locator('.wbs-row.child').click()
    await page.getByLabel('종료일').fill('2026-11-30')
    await page.getByRole('button', { name: '저장', exact: true }).click()
    await expect(page.getByText('하위 작업 기간은 상위 과제 기간 안이어야 해요.')).toBeVisible()
    await page.getByLabel('종료일').fill('2026-10-24')
    await page.getByLabel('상태').selectOption('in_progress')
    await page.getByRole('button', { name: '저장', exact: true }).click()
    await expect(page.getByText('WBS를 저장했어요.')).toBeVisible()
    await expect(page.locator('.wbs-row.child')).toContainText('진행')
  })

  test('드래그 시간표: 역방향 드래그 생성 → 겹침 거부 → 블록 이동 → 폼 대안', async ({ page }) => {
    await login(page, c.email)
    await page.goto(`/records/${DAY}`)
    // 11:00 → 10:00 역방향 드래그 = 10:00~11:15
    await dragTimeline(page, 660, 600, 'actual')
    const form = page.getByRole('form', { name: '새 시간표 블록' })
    await expect(form).toBeVisible()
    await expect(form.getByLabel('시작')).toHaveValue('600')
    await expect(form.getByLabel('종료')).toHaveValue('675')
    await expect(form.getByLabel('종류')).toHaveValue('actual')
    await form.getByLabel('공부 제목').fill('VPC 강의')
    await form.getByRole('button', { name: '블록 저장' }).click()
    await expect(page.locator('.time-block.actual')).toContainText('VPC 강의')

    // 같은 레이어 겹침 → 거부(폼으로 겹치는 시간 입력)
    await page.getByRole('button', { name: '블록 추가' }).click()
    await form.getByLabel('시작').selectOption('630')
    await form.getByLabel('종료').selectOption('690')
    await form.getByLabel('공부 제목').fill('겹침')
    await form.getByRole('button', { name: '블록 저장' }).click()
    await expect(page.getByText('같은 종류의 다른 블록과 시간이 겹쳐요.')).toBeVisible()
    await form.getByRole('button', { name: '취소' }).click()

    // 계획 레이어는 겹쳐도 허용
    await dragTimeline(page, 600, 645, 'plan')
    await form.getByLabel('공부 제목').fill('계획: 네트워킹')
    await form.getByRole('button', { name: '블록 저장' }).click()
    await expect(page.locator('.time-block.plan')).toContainText('계획: 네트워킹')

    // 블록 본문을 1시간(80px) 아래로 끌어 이동 → 11:00–12:15
    const body = page.locator('.time-block.actual .block-body')
    await body.scrollIntoViewIfNeeded()
    await page.evaluate(() => window.scrollBy(0, -120)) // 아래로 끌 공간 확보
    const box = await body.boundingBox()
    await page.mouse.move(box.x + 20, box.y + 8)
    await page.mouse.down()
    await page.mouse.move(box.x + 20, box.y + 48, { steps: 5 })
    await page.mouse.move(box.x + 20, box.y + 88, { steps: 5 })
    await page.mouse.up()
    await expect(page.locator('.time-block.actual')).toContainText('11:00–12:15')

    // 키보드/터치 대안: 블록 추가 폼
    await page.getByRole('button', { name: '블록 추가' }).click()
    await form.getByLabel('시작').selectOption('840')
    await form.getByLabel('종료').selectOption('900')
    await form.getByLabel('공부 제목').fill('모의고사')
    await form.getByRole('button', { name: '블록 저장' }).click()
    await expect(page.locator('.time-block.actual', { hasText: '모의고사' })).toContainText('14:00–15:00')

    // 새로고침 후 유지 + 블록 Enter로 수정
    await page.reload()
    await page.getByRole('button', { name: /실제 모의고사 14:00부터/ }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('form', { name: '시간표 블록 수정' })).toBeVisible()
  })

  test('주간 회고 저장 + 주말 보충', async ({ page }) => {
    await login(page, c.email)
    await page.goto(`/records/${DAY}`)
    await page.getByLabel('목표 추가').fill('IAM 정책 복습')
    await page.getByRole('button', { name: '추가', exact: true }).click()
    await expect(page.locator('.goal-list')).toContainText('IAM 정책 복습')
    await page.getByLabel('잘한 점').fill('매일 출석')
    await page.getByLabel('다음 주 계획').fill('모의고사 2회')
    await page.getByLabel('주간 회고 공개').check()
    await page.getByRole('button', { name: '회고 저장' }).click()
    await expect(page.getByText(/회고를 저장했어요/)).toBeVisible()

    await page.reload()
    await page.getByLabel('미완료 목표').selectOption({ label: '10월 21일 (수) · IAM 정책 복습' })
    await page.getByLabel('보충할 날').selectOption('2026-10-24')
    await page.getByRole('button', { name: '보충으로 옮기기' }).click()
    await expect(page.getByText(/보충 목표를 옮겼어요/)).toBeVisible()
    await page.goto('/records/2026-10-24')
    await expect(page.locator('.goal-list')).toContainText('IAM 정책 복습')
    await expect(page.locator('.goal-list .badge')).toContainText('보충')
    await expect(page.getByLabel('잘한 점')).toHaveValue('매일 출석') // 같은 주
  })

  for (const width of [1440, 390, 360]) {
    test(`기록·캘린더 ${width}px 레이아웃`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await login(page, c.email)
      await page.goto(`/records/${DAY}`)
      await expect(page.locator('.time-block').first()).toBeVisible()
      await expectNoHorizontalOverflow(page)
      await page.screenshot({ path: `screenshots/records-${width}.png`, fullPage: true })
      await page.goto('/calendar')
      await expect(page.locator('.month-grid')).toBeVisible()
      await expectNoHorizontalOverflow(page)
      await page.screenshot({ path: `screenshots/calendar-${width}.png`, fullPage: true })
    })
  }
})
