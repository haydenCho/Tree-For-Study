// 운영 빌드 스모크: CSP·정적 자원·지연 로드 청크·폰트가 실제 Caddy 뒤에서 동작하는지 확인한다.
// 데이터를 만들지 않고 읽기·화면 이동만 한다(운영 환경에서도 안전).
import { expect, test } from '@playwright/test'

test('운영 빌드: 로그인 → 주요 화면 → 이모지 청크, 콘솔/CSP 오류 없음', async ({ page }) => {
  const problems = []
  page.on('console', (m) => m.type() === 'error' && problems.push(m.text()))
  page.on('pageerror', (e) => problems.push(e.message))

  await page.goto('/login')
  await page.getByLabel('이메일').fill(process.env.OP_EMAIL)
  await page.getByLabel('비밀번호').fill(process.env.OP_PASSWORD)
  await page.getByRole('button', { name: '로그인', exact: true }).last().click()
  await expect(page.getByRole('heading', { name: /오늘의 집중이/ })).toBeVisible()
  // 자체 호스팅 Pretendard 로드
  expect(await page.evaluate(async () => (await document.fonts.ready, document.fonts.check('16px Pretendard')))).toBe(true)

  for (const [path, heading] of [
    ['/plaza', '함께 자라는 공동 숲'],
    ['/calendar', '스터디 캘린더'],
    ['/records', /의 기록$/],
  ]) {
    await page.goto(path)
    await expect(page.getByRole('heading', { name: heading })).toBeVisible()
  }
  await page.goto('/me')
  await page.getByRole('button', { name: /아바타 이모지 선택/ }).click()
  await expect(page.getByText(/Unicode Emoji 18.0/)).toBeVisible()
  // 새로고침 후 refresh 쿠키로 로그인 유지
  await page.reload()
  await expect(page.getByRole('heading', { name: '나의 숲 정보' })).toBeVisible()
  expect(problems.filter((p) => !/favicon/.test(p))).toEqual([])
})
