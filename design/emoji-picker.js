let emojiPage=0;
const emojiPageSize=120;
const emojiSearchIndex=EMOJI_DATA.items.map(item=>({...item,search:[item.emoji,item.name,item.ko,item.keywords,item.codes].join(' ').toLocaleLowerCase()}));
for(const category of new Set(EMOJI_DATA.items.map(item=>item.group))){const option=document.createElement('option');option.value=category;option.textContent=category;$('emoji-category').append(option);}
function renderEmojiPicker(){
  const query=$('emoji-search').value.trim().toLocaleLowerCase(),category=$('emoji-category').value;
  const found=emojiSearchIndex.filter(item=>(!category||item.group===category)&&(!query||item.search.includes(query)));
  const pages=Math.max(1,Math.ceil(found.length/emojiPageSize));emojiPage=Math.min(emojiPage,pages-1);
  $('emoji-count').textContent=`${found.length.toLocaleString()}개 · Unicode Emoji ${EMOJI_DATA.version}`;
  $('emoji-page').textContent=`${emojiPage+1} / ${pages}`;$('emoji-prev').disabled=emojiPage===0;$('emoji-next').disabled=emojiPage>=pages-1;
  $('emoji-grid').replaceChildren();
  for(const item of found.slice(emojiPage*emojiPageSize,(emojiPage+1)*emojiPageSize)){
    const button=document.createElement('button');button.type='button';button.className='emoji-option emoji-glyph';button.textContent=item.emoji;
    button.title=`${item.ko||item.name} · ${item.name}`;button.setAttribute('aria-label',button.title);button.setAttribute('aria-pressed',String(item.emoji===$('profile-avatar').value));
    button.onclick=()=>{$('profile-avatar').value=item.emoji;$('avatar-draft').textContent=item.emoji;$('emoji-dialog').close();notify('이모지를 골랐어요. 프로필 저장을 누르면 반영돼요.');};$('emoji-grid').append(button);
  }
  if(!found.length){const p=document.createElement('p');p.textContent='검색 결과가 없어요. 다른 이름이나 이모지를 입력해 주세요.';$('emoji-grid').append(p);}
}
$('emoji-open').onclick=()=>{renderEmojiPicker();$('emoji-dialog').showModal();$('emoji-search').focus();};
$('emoji-close').onclick=()=>$('emoji-dialog').close();
$('emoji-dialog').addEventListener('close',()=>$('emoji-open').focus());
$('emoji-search').oninput=$('emoji-category').onchange=()=>{emojiPage=0;renderEmojiPicker();};
$('emoji-prev').onclick=()=>{emojiPage--;renderEmojiPicker();$('emoji-grid').scrollTop=0;};
$('emoji-next').onclick=()=>{emojiPage++;renderEmojiPicker();$('emoji-grid').scrollTop=0;};
