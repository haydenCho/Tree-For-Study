import React, {useMemo, useRef, useState} from 'react';
import data from '../emoji/emoji-data.json';
import './emoji-picker.css';

// Native emoji characters, including flags, skin tones and complete ZWJ sequences.
// onChange updates the draft; parent persists the avatar on profile Save.
export default function EmojiPicker({value='🌿',onChange}) {
  const dialog=useRef(null),trigger=useRef(null),search=useRef(null);
  const [query,setQuery]=useState(''),[category,setCategory]=useState(''),[page,setPage]=useState(0);
  const categories=useMemo(()=>[...new Set(data.items.map(e=>e.group))],[]);
  const results=useMemo(()=>data.items.filter(e=>(!category||e.group===category)&&[e.name,e.ko,e.keywords,e.emoji,e.codes].join(' ').toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())),[query,category]);
  const pages=Math.max(1,Math.ceil(results.length/120)),current=Math.min(page,pages-1);
  function close(){dialog.current.close();trigger.current.focus();}
  return <div className="avatar-field">
    <button type="button" ref={trigger} aria-haspopup="dialog" onClick={()=>{dialog.current.showModal();search.current.focus();}}><span className="emoji-glyph">{value}</span> 아바타 이모지 선택</button>
    <dialog className="emoji-picker" ref={dialog} aria-label="아바타 이모지 선택" onClose={()=>trigger.current.focus()}>
      <h2>아바타 이모지 선택</h2><button type="button" onClick={close}>닫기</button>
      <label>검색<input ref={search} value={query} onChange={e=>{setQuery(e.target.value);setPage(0);}} placeholder="웃음, tree, 🇰🇷" /></label>
      <label>카테고리<select value={category} onChange={e=>{setCategory(e.target.value);setPage(0);}}><option value="">전체</option>{categories.map(c=><option key={c}>{c}</option>)}</select></label>
      <p role="status">{results.length}개 · Unicode Emoji {data.version}</p>
      <div className="emoji-grid">{results.slice(current*120,(current+1)*120).map(e=><button type="button" key={e.emoji} className="emoji-option emoji-glyph" aria-label={`${e.ko||e.name} · ${e.name}`} title={`${e.ko||e.name} · ${e.name}`} aria-pressed={value===e.emoji} onClick={()=>{onChange?.(e.emoji);close();}}>{e.emoji}</button>)}{results.length===0&&<p>검색 결과가 없어요.</p>}</div>
      <div className="emoji-pages"><button type="button" disabled={current===0} onClick={()=>setPage(current-1)}>이전</button><span>{current+1} / {pages}</span><button type="button" disabled={current>=pages-1} onClick={()=>setPage(current+1)}>다음</button></div>
      <p>이모지 모양과 지원 범위는 사용 기기에 따라 달라요.</p>
    </dialog>
  </div>;
}
