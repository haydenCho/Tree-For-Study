import React from 'react';
import './forest-grid.css';

// Fixed placements; only empty cells may be selected before session creation.
export default function ForestGrid({ placements = [], selectedCells = [], requiredCount = 1, locked = false, onCellToggle }) {
  const cells = Array.from({ length: 36 }, (_, i) => {
    const row = Math.floor(i / 6), col = i % 6;
    return { row, col, item: placements.find(p => p.row === row && p.col === col), selected: selectedCells.some(p => p.row === row && p.col === col) };
  });
  const label = ({ row, col, item, selected }) => `${row + 1}행 ${col + 1}열, ${item ? (item.status === 'wilted' ? '시든 나무 · 위치 고정' : '나무 · 위치 고정') : selected ? '선택됨' : '빈 칸'}`;
  const disabled = c => locked || Boolean(c.item) || (!c.selected && selectedCells.length >= requiredCount);
  const activate = cell => { if (!disabled(cell)) onCellToggle?.({ row: cell.row, col: cell.col }); };
  return <section className="tf-forest" aria-label="시작 전 나무 위치 선택">
    <p role="status">{locked ? '시작한 나무의 위치는 변경할 수 없습니다.' : `${selectedCells.length} / ${requiredCount}칸 선택`}</p>
    <div className="tf-forest-scene" aria-label="고정 시점 숲">
      {[...cells].sort((a,b) => a.row + a.col - b.row - b.col).map(cell => {
        const {row,col,item} = cell;
        return <div className="tf-cell" key={`${row}-${col}`} style={{left:`${50 + (col-row)*7.5}%`,top:`${24+(row+col)*5.5}%`,zIndex:row+col+1}}>
          <button type="button" className="tf-tile" disabled={disabled(cell)} aria-label={label(cell)} aria-pressed={cell.selected} onClick={() => activate(cell)} />
          {item && <img className="tf-tree" src={item.assetUrl} alt="" />}
        </div>;
      })}
    </div>
  </section>;
}
