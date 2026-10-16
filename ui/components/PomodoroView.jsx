import React from 'react';

// Presentational UI only. All times/status come from the server-backed parent.
export default function PomodoroView({remainingSeconds,totalSeconds,paused,treeUrl,seedUrl,onTogglePause,onRequestLeave}) {
  const progress=Math.max(0,Math.min(1,1-remainingSeconds/Math.max(1,totalSeconds)));
  const left=Math.max(0,Math.ceil(remainingSeconds));
  return <section className="focus-layout" aria-label="집중 전용 화면">
    <div className="focus-copy"><h1>지금은, 이 나무가 자라는 시간.</h1>
      <p role="status">{paused?'일시정지':progress<.2?'씨앗':progress<.55?'새싹':progress<.85?'어린 나무':'완성을 향해 자라는 중'}</p>
      <div className="focus-clock">{String(Math.floor(left/60)).padStart(2,'0')}:{String(left%60).padStart(2,'0')}</div>
      <div className="focus-progress" role="progressbar" aria-label="집중 진행률" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress*100)}><span style={{width:`${progress*100}%`}}/></div>
      <button type="button" onClick={onTogglePause}>{paused?'집중 재개':'일시정지'}</button><button type="button" onClick={onRequestLeave}>포기하고 나가기</button>
    </div>
    <div className={`growth-scene${paused?' paused':''}`}><div className="growth-halo"/><div className="growth-soil"/>
      <img className="growth-seed" src={seedUrl} alt="묘목" style={{opacity:Math.max(0,1-progress*4)}}/>
      <div className="growth-layer" style={{opacity:Math.min(1,progress*4),transform:`translateX(-50%) scale(${.3+progress*.7})`}}><img src={treeUrl} alt="집중과 함께 성장하는 나무"/></div>
    </div>
  </section>;
}
