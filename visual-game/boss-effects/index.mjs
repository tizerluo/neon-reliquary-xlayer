import boss0 from './boss-0.mjs';
import boss1 from './boss-1.mjs';
import boss2 from './boss-2.mjs';
import boss3 from './boss-3.mjs';
import boss4 from './boss-4.mjs';
import boss5 from './boss-5.mjs';
import boss6 from './boss-6.mjs';
import boss7 from './boss-7.mjs';

export const BOSS_EFFECTS = Object.freeze([boss0,boss1,boss2,boss3,boss4,boss5,boss6,boss7]);
// 敌人槽位会复用；代次进入 uid，失去本体的挂件不能挂到下一只敌人。
export const bossOwnerId = (index,generation) => (generation*2048+index)*4;
export const zoneOwnerId = id => id*4+3;
const wrap = a => Math.atan2(Math.sin(a),Math.cos(a));
export function bossContext(event,S=.028) {
  return { ...event, hero:0,
    owner:event.kind==='zone'?zoneOwnerId(event.zoneId):bossOwnerId(event.source,event.generation),
    x:event.x*S,z:event.y*S,angle:wrap(event.angle??0),seed:event.id,
    radius:event.r==null?undefined:event.r*S,
    length:event.len==null?undefined:event.len*S,width:event.width==null?undefined:event.width*S,
    summons:(event.summons||[]).map(p=>({...p,x:p.x*S,z:p.y*S,radius:p.r*S})),
  };
}
// 战斗 shape 是 circle / line；渲染器 shape 是 seal / lane / sector。
// 只带入锚点，不让战斗半径、轨长或 shape 污染配方的其他层。
export const primitiveContext = c => ({owner:c.owner,hero:0,boss:c.boss,x:c.x,z:c.z,angle:c.angle,seed:c.seed});
