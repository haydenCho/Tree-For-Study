// 로그인/가입 화면 왼쪽 소개 영역.
import { treeAsset } from '../../lib/trees.js'

export function AuthStory() {
  return (
    <div className="auth-story">
      <p className="eyebrow">TREE FOR STUDY</p>
      <h1>같은 공간, 각자의 속도로.</h1>
      <p>집중한 시간이 나만의 숲과 스터디 공동 숲에 나무로 남아요. 소리나 알림 없이, 화면 속 변화만으로 함께해요.</p>
      <img src={treeAsset('oak', 'large', 'normal')} alt="" />
    </div>
  )
}
