import { STAGES, currentStage } from './stage.js'

// 현재 개발 단계를 화면 왼쪽 하단에 표시하는 배지.
// 지금 어느 단계까지 구현됐는지 한눈에 확인하기 위한 개발용 표시이며,
// 모든 화면 위에 고정으로 떠 있는다.
export function StageBadge() {
  const stage = STAGES.find((s) => s.id === currentStage) || STAGES[0]
  return (
    <aside className="stage-badge" aria-label={`개발 단계 ${stage.id}: ${stage.label}`}>
      <span className="stage-badge__num">단계 {stage.id}</span>
      <span className="stage-badge__label">{stage.label}</span>
      <span className="stage-badge__track" aria-hidden="true">
        {STAGES.map((s) => (
          <span
            key={s.id}
            className={'stage-badge__dot' + (s.id <= currentStage ? ' is-done' : '')}
            title={`단계 ${s.id} · ${s.label}`}
          />
        ))}
      </span>
    </aside>
  )
}
