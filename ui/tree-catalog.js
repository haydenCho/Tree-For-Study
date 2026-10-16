export const treeSpecies = [
  {id:'oak',name:'둥근 참나무'}, {id:'fir',name:'층층 전나무'},
  {id:'cherry',name:'분홍 벚꽃'}, {id:'ginkgo',name:'황금 은행'},
  {id:'willow',name:'늘어진 버드나무'}, {id:'blossom',name:'꽃송이 정원수'},
];
const assets = import.meta.glob('./assets/trees/*.svg', {eager:true,query:'?url',import:'default'});
export function treeAsset(species, size, state='normal') {
  return assets[`./assets/trees/${species}-${size}-${state}.svg`];
}
