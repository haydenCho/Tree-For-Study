// 아바타 이모지 선택기(ui/components/EmojiPicker.jsx 기반).
// Unicode Emoji 18.0 전체 3,972개. 국기·피부색·ZWJ 조합 문자열을 한 항목으로 보존한다.
// 데이터(약 900KB)는 선택기를 처음 열 때 지연 로드한다. 선택은 초안만 바꾸며
// 프로필 저장 버튼을 눌러야 서버에 반영된다.
import { useMemo, useRef, useState } from 'react'

const PAGE = 120

export default function EmojiPicker({ value = '🌱', onChange }) {
  const dialog = useRef(null)
  const trigger = useRef(null)
  const search = useRef(null)
  const [data, setData] = useState(null)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(0)

  async function open() {
    if (!data) {
      const mod = await import('../data/emoji-data.json')
      setData(mod.default)
    }
    dialog.current.showModal()
    setTimeout(() => search.current?.focus(), 0)
  }
  function close() {
    dialog.current.close()
  }

  const categories = useMemo(() => (data ? [...new Set(data.items.map((e) => e.group))] : []), [data])
  const results = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLocaleLowerCase()
    return data.items.filter(
      (e) =>
        (!category || e.group === category) &&
        (!q || [e.name, e.ko, e.keywords, e.emoji, e.codes].join(' ').toLocaleLowerCase().includes(q)),
    )
  }, [data, query, category])
  const pages = Math.max(1, Math.ceil(results.length / PAGE))
  const current = Math.min(page, pages - 1)

  return (
    <div className="avatar-field">
      <button type="button" ref={trigger} className="emoji-open" aria-haspopup="dialog" onClick={open}>
        <span className="emoji-glyph avatar-draft">{value}</span> 아바타 이모지 선택
      </button>
      <dialog className="emoji-picker" ref={dialog} aria-label="아바타 이모지 선택" onClose={() => trigger.current?.focus()}>
        <div className="section-top">
          <h2>아바타 이모지 선택</h2>
          <button type="button" onClick={close}>
            닫기
          </button>
        </div>
        <label>
          검색
          <input
            ref={search}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(0)
            }}
            placeholder="웃음, tree, 🇰🇷"
          />
        </label>
        <label>
          카테고리
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value)
              setPage(0)
            }}
          >
            <option value="">전체</option>
            {categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <p className="hint" role="status">
          {data ? `${results.length}개 · Unicode Emoji ${data.version}` : '불러오는 중…'}
        </p>
        <div className="emoji-grid">
          {results.slice(current * PAGE, (current + 1) * PAGE).map((e) => (
            <button
              type="button"
              key={e.emoji}
              className="emoji-option emoji-glyph"
              aria-label={`${e.ko || e.name} · ${e.name}`}
              title={`${e.ko || e.name} · ${e.name}`}
              aria-pressed={value === e.emoji}
              onClick={() => {
                onChange?.(e.emoji)
                close()
              }}
            >
              {e.emoji}
            </button>
          ))}
          {data && results.length === 0 && <p>검색 결과가 없어요.</p>}
        </div>
        <div className="emoji-pages">
          <button type="button" disabled={current === 0} onClick={() => setPage(0)}>
            처음
          </button>
          <button type="button" disabled={current === 0} onClick={() => setPage(current - 1)}>
            이전
          </button>
          <span>
            {current + 1} / {pages}
          </span>
          <button type="button" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>
            다음
          </button>
          <button type="button" disabled={current >= pages - 1} onClick={() => setPage(pages - 1)}>
            마지막
          </button>
        </div>
        <p className="hint">이모지 모양과 지원 범위는 사용 기기에 따라 달라요.</p>
      </dialog>
    </div>
  )
}
