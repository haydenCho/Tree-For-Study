// Design demo only: no credentials are persisted, no JWTs are fabricated.
const navigatePreview=showPage;
let pendingDestination=null,focusSeconds=0,lastFocusTick=performance.now(),focusDemoTimer=null,focusResultShown=false;
showPage=function(page){
  if(active&&page!=='focus'){
    pendingDestination=page;
    if(!$('abandon-dialog').open)$('abandon-dialog').showModal();
    return;
  }
  document.body.classList.toggle('focus-mode',page==='focus');
  navigatePreview(page);
};
const startPreview=$('start').onclick;
$('start').onclick=()=>{
  startPreview();if(!active)return;
  focusSeconds=0;lastFocusTick=performance.now();focusResultShown=false;
  $('focus-result').hidden=true;$('growth-scene').classList.remove('wilted','paused');
  $('focus-pause').hidden=$('focus-complete-demo').hidden=false;
  const tree=personal.find(t=>active.ids.includes(t.id));
  $('growth-tree').src=asset(`trees/${tree.species}-${tree.size}-${tree.library?'library':'normal'}`);
  $('focus-tree-info').textContent=`${species.find(s=>s[0]===tree.species)[1]} · ${tree.size==='large'?'큰':'작은'} 나무 ${active.ids.length}그루`;
  showPage('focus');renderFocus();
  clearInterval(focusDemoTimer);focusDemoTimer=setInterval(tickFocus,250);
};
function renderFocus(){
  if(!active)return;const progress=Math.min(1,focusSeconds/(active.minutes*60));
  const remaining=Math.max(0,Math.ceil(active.minutes*60-focusSeconds));
  $('focus-clock').textContent=`${String(Math.floor(remaining/60)).padStart(2,'0')}:${String(remaining%60).padStart(2,'0')}`;
  $('focus-progress-fill').style.width=`${progress*100}%`;$('focus-progress').setAttribute('aria-valuenow',String(Math.round(progress*100)));
  $('growth-seed').style.opacity=String(Math.max(0,1-progress*4));$('growth-layer').style.opacity=String(Math.min(1,progress*4));
  $('growth-layer').style.transform=`translateX(-50%) scale(${.3+progress*.7})`;
  const stage=state==='paused'?'잠시 쉬는 중 · 성장이 멈춰 있어요.':progress<.2?'씨앗이 깨어나고 있어요.':progress<.55?'새싹이 잎을 펼치고 있어요.':progress<.85?'어린 나무가 가지를 뻗고 있어요.':'풍성한 나무가 되어가고 있어요.';
  if($('focus-stage').textContent!==stage)$('focus-stage').textContent=stage;
  $('focus-pause').textContent=state==='paused'?'집중 재개':'일시정지';$('growth-scene').classList.toggle('paused',state==='paused');
}
function tickFocus(){const now=performance.now(),delta=(now-lastFocusTick)/1000;lastFocusTick=now;if(!active)return;if(state==='focusing')focusSeconds+=delta*60;renderFocus();if(focusSeconds>=active.minutes*60)finishFocus(false);}
$('focus-pause').onclick=()=>{tickFocus();if(!active)return;$('pause').onclick();lastFocusTick=performance.now();renderFocus();};
function finishFocus(abandoned){
  if(!active)return;clearInterval(focusDemoTimer);
  const tree=personal.find(t=>active.ids.includes(t.id)),count=active.ids.length,minutes=active.minutes;
  settle(abandoned);focusResultShown=true;$('focus-result').hidden=false;
  $('focus-pause').hidden=$('focus-complete-demo').hidden=true;$('growth-seed').style.opacity='0';$('growth-layer').style.opacity='1';$('growth-layer').style.transform='translateX(-50%) scale(1)';
  $('growth-tree').src=asset(`trees/${tree.species}-${tree.size}-${abandoned?'wilted':tree.library?'library':'normal'}`);
  $('growth-scene').classList.toggle('wilted',abandoned);$('growth-scene').classList.remove('paused');
  $('focus-clock').textContent='00:00';$('focus-stage').textContent=abandoned?'이번 나무는 시들었어요. 다시 시작할 수 있어요.':'집중을 마치고 나무가 자랐어요.';
  $('focus-progress-fill').style.width=abandoned?'0%':'100%';$('focus-progress').setAttribute('aria-valuenow',abandoned?'0':'100');
  $('focus-result-title').textContent=abandoned?'이번 집중을 마쳤어요.':'한 번의 집중이 숲에 남았어요.';
  $('focus-result-description').textContent=abandoned?'이번 세션 인정 시간 0 · 이전 완료 기록은 유지됩니다.':`${minutes}분 완료 · ${count}그루가 시작할 때 지정한 자리에 남습니다.`;
}
$('focus-complete-demo').onclick=()=>{if(state==='paused'){notify('집중을 재개한 뒤 완료 상태를 확인해 주세요.');return;}finishFocus(false);};
$('focus-exit').onclick=()=>{if(active){pendingDestination='dashboard';$('abandon-dialog').showModal();}else showPage('dashboard');};
$('focus-return').onclick=()=>showPage('dashboard');
$('keep-session').onclick=()=>{pendingDestination=null;$('abandon-dialog').close();};
$('abandon-dialog').addEventListener('cancel',()=>{pendingDestination=null;});
$('confirm-abandon').onclick=()=>{
  $('abandon-dialog').close();const destination=pendingDestination;pendingDestination=null;
  finishFocus(true);
  // Show the wilted result before a deliberate return; do not silently navigate.
  if(destination){$('focus-return').textContent=destination==='auth'?'로그인 화면으로 이동':'선택한 화면으로 이동';$('focus-return').onclick=()=>{showPage(destination);$('focus-return').textContent='대시보드로 돌아가기';$('focus-return').onclick=()=>showPage('dashboard');};}
};
window.addEventListener('beforeunload',e=>{if(active){e.preventDefault();e.returnValue='';}});
// Back/forward cannot reveal another service screen during an active session.
window.addEventListener('popstate',()=>{if(active){showPage('dashboard');}});

let authMode='login';
function setAuthMode(mode){authMode=mode;const signup=mode==='register';$('register-fields').hidden=$('confirm-field').hidden=!signup;['auth-name','auth-invite','auth-confirm'].forEach(id=>$(id).required=signup);$('auth-password').autocomplete=signup?'new-password':'current-password';$('auth-login-tab').setAttribute('aria-pressed',String(!signup));$('auth-register-tab').setAttribute('aria-pressed',String(signup));$('auth-submit').textContent=signup?'회원가입 화면 시연':'로그인 화면 시연';$('auth-message').textContent='';}
$('auth-open').onclick=()=>showPage('auth');$('auth-login-tab').onclick=()=>setAuthMode('login');$('auth-register-tab').onclick=()=>setAuthMode('register');
$('auth-form').onsubmit=e=>{e.preventDefault();if(authMode==='register'&&$('auth-password').value!==$('auth-confirm').value){$('auth-message').textContent='비밀번호 확인이 일치하지 않아요.';return;}$('auth-password').value=$('auth-confirm').value='';$('auth-message').textContent='화면 흐름을 확인했어요. 실제 계정 생성과 JWT 인증은 서버 개발에서 연결합니다.';notify('인증 화면 시연 완료 · 계정이나 토큰은 생성하지 않았습니다.');};
const accountButton=document.createElement('button');accountButton.type='button';accountButton.textContent='로그인 / 회원가입 화면 보기';accountButton.onclick=()=>showPage('auth');$('profile-form').after(accountButton);
