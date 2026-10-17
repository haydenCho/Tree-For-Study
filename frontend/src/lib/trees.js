// 수종 목록과 나무 SVG 경로 helper(ui/tree-catalog.js 기반).
// 6수종 × 작은/큰 × 일반/도서관/시듦 = 36개 원본 + 진행 중 묘목.
import seedlingUrl from '../assets/seedling.svg'

export const SPECIES = [
  { id: 'oak', name: '둥근 참나무' },
  { id: 'fir', name: '층층 전나무' },
  { id: 'cherry', name: '분홍 벚꽃' },
  { id: 'ginkgo', name: '황금 은행' },
  { id: 'willow', name: '늘어진 버드나무' },
  { id: 'blossom', name: '꽃송이 정원수' },
]

const assets = import.meta.glob('../assets/trees/*.svg', { eager: true, query: '?url', import: 'default' })

export function treeAsset(species, size, state = 'normal') {
  if (state === 'seedling') return seedlingUrl
  return assets[`../assets/trees/${species}-${size}-${state}.svg`]
}

export function speciesName(id) {
  return SPECIES.find((s) => s.id === id)?.name || id
}

export const SEEDLING = seedlingUrl

export function sizeLabel(size) {
  return size === 'large' ? '큰' : '작은'
}
