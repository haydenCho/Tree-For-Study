// 2.5D 고정 시점 6×6 숲(ui/components/ForestGrid.jsx 기반).
// - 시작 전에는 빈 칸만 선택/해제할 수 있다. 기존 나무 칸은 비활성.
// - locked면 모든 칸이 비활성(시작 후 위치 변경 불가). 이동/수납 동작은 없다.
// - 칸 목록 대신 숲의 실제 타일을 클릭/터치하거나 Tab·Enter로 직접 선택한다.
// - onTreeFocus가 있으면(공동 숲) 나무 칸을 눌러 소유자 카드를 연다.
import { treeAsset } from '../lib/trees.js'

const STATE_LABEL = {
  seedling: '자라는 중인 묘목',
  normal: '나무',
  library: '도서관 장식 나무',
  wilted: '시든 나무',
}

export default function ForestGrid({
  cells = [],
  selectedCells = [],
  requiredCount = 0,
  locked = false,
  onCellToggle,
  onTreeFocus,
  label = '숲',
  className = '',
}) {
  const items = []
  for (let row = 0; row < 6; row += 1) {
    for (let col = 0; col < 6; col += 1) {
      const item = cells.find((c) => c.row === row && c.col === col)
      const selected = selectedCells.some((c) => c.row === row && c.col === col)
      items.push({ row, col, item, selected })
    }
  }
  const selectable = Boolean(onCellToggle)
  const isDisabled = (c) => {
    if (c.item) return !onTreeFocus
    if (!selectable || locked) return true
    return !c.selected && selectedCells.length >= requiredCount
  }
  const describe = ({ row, col, item, selected }) => {
    const pos = `${row + 1}행 ${col + 1}열`
    if (item) {
      const owner = item.ownerName ? ` · ${item.ownerName}` : ''
      return `${pos}, ${STATE_LABEL[item.state] || '나무'}${owner} · 위치 고정`
    }
    return `${pos}, ${selected ? '선택됨' : '빈 칸'}`
  }
  return (
    <div className={`forest ${className}`} role="group" aria-label={label}>
      {[...items]
        .sort((a, b) => a.row + a.col - (b.row + b.col))
        .map((c) => (
          <div
            className="iso-cell"
            key={`${c.row}-${c.col}`}
            style={{ left: `${50 + (c.col - c.row) * 7.5}%`, top: `${24 + (c.row + c.col) * 5.5}%`, zIndex: c.row + c.col + 1 }}
          >
            <button
              type="button"
              className={`tile${c.selected ? ' selected' : ''}`}
              disabled={isDisabled(c)}
              aria-label={describe(c)}
              aria-pressed={c.item ? undefined : c.selected}
              onClick={() => {
                if (c.item) onTreeFocus?.(c.item)
                else if (!isDisabled(c)) onCellToggle?.({ row: c.row, col: c.col })
              }}
              // 공동 숲: 마우스 hover뿐 아니라 키보드 focus로도 같은 정보를 연다.
              onFocus={c.item && onTreeFocus ? () => onTreeFocus(c.item) : undefined}
              onMouseEnter={c.item && onTreeFocus ? () => onTreeFocus(c.item) : undefined}
            />
            {c.item && (
              <img
                className={`iso-tree ${c.item.state}`}
                src={treeAsset(c.item.species, c.item.size, c.item.state)}
                alt=""
                draggable="false"
              />
            )}
          </div>
        ))}
    </div>
  )
}
