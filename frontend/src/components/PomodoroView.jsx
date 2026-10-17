// 집중 전용 화면의 표시 컴포넌트(ui/components/PomodoroView.jsx 기반).
// 시간·상태는 모두 서버 기반 부모가 넘겨준다. 이 컴포넌트는 타이머나 보상을 계산하지 않는다.
// 성장 단계: 씨앗 → 새싹 → 어린 나무 → 완성. 중간 성장은 보상 확정이 아니다.
import { formatClock } from '../lib/time.js'

function stageText(progress, paused) {
  if (paused) return '잠시 쉬는 중 · 성장이 멈춰 있어요.'
  if (progress < 0.2) return '씨앗이 깨어나고 있어요.'
  if (progress < 0.55) return '새싹이 잎을 펼치고 있어요.'
  if (progress < 0.85) return '어린 나무가 가지를 뻗고 있어요.'
  return '풍성한 나무가 되어가고 있어요.'
}

export default function PomodoroView({
  remainingSeconds,
  totalSeconds,
  paused,
  finished,
  wilted,
  treeUrl,
  seedUrl,
  caption,
  busy,
  onTogglePause,
  onRequestLeave,
}) {
  const progress = finished && !wilted ? 1 : Math.max(0, Math.min(1, 1 - remainingSeconds / Math.max(1, totalSeconds)))
  const shown = finished ? 1 : progress
  return (
    <section className="focus-layout" aria-label="집중 전용 화면">
      <div className="focus-copy">
        <p className="eyebrow">FOCUS</p>
        <h1>지금은, 이 나무가 자라는 시간.</h1>
        <p role="status">
          {wilted ? '이번 나무는 시들었어요. 다시 시작할 수 있어요.' : finished ? '집중을 마치고 나무가 자랐어요.' : stageText(progress, paused)}
        </p>
        <div className="focus-clock" aria-label="남은 시간">
          {formatClock(finished ? 0 : remainingSeconds)}
        </div>
        <div
          className="focus-progress"
          role="progressbar"
          aria-label="집중 진행률"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round((wilted ? 0 : shown) * 100)}
        >
          <span style={{ width: `${(wilted ? 0 : shown) * 100}%` }} />
        </div>
        {!finished && (
          <div className="inline">
            <button type="button" className="primary" onClick={onTogglePause} disabled={busy}>
              {paused ? '집중 재개' : '일시정지'}
            </button>
            <button type="button" className="danger" onClick={onRequestLeave} disabled={busy}>
              중도 포기
            </button>
          </div>
        )}
        <p className="hint">{caption}</p>
      </div>
      <div className={`growth-scene${paused ? ' paused' : ''}${wilted ? ' wilted' : ''}`} aria-hidden="true">
        <div className="growth-halo" />
        <div className="growth-soil" />
        <img className="growth-seed" src={seedUrl} alt="" style={{ opacity: Math.max(0, 1 - shown * 4) }} />
        <div
          className="growth-layer"
          style={{ opacity: Math.min(1, shown * 4), transform: `translateX(-50%) scale(${0.3 + shown * 0.7})` }}
        >
          <img src={treeUrl} alt="" />
        </div>
        {!paused && !finished && (
          <div className="growth-motes">
            <i />
            <i />
            <i />
            <i />
          </div>
        )}
      </div>
    </section>
  )
}
