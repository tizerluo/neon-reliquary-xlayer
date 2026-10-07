import { createSkillFX } from './skill-fx.mjs';
import { createBossProjectiles } from './boss-projectiles.mjs';
import { BOSS_EFFECTS, bossContext, primitiveContext, bossOwnerId, zoneOwnerId } from './boss-effects/index.mjs';

// 跟随真实 Boss 池、预警执行事件和危险区；不预测下一次攻击、不写战斗状态。
export function createBossFX(scene) {
  // 狂暴六束光的十二个端门、密集落羽仍保留完整低画质主形；英雄预算保持原值。
  const fx=createSkillFX(scene,{heroBindings:false,feedbackEnabled:false,timelineCapacity:512,lowBudgets:{shield:12,shard:64,wing:48}});
  const projectiles=createBossProjectiles(scene);
  const aims=new Map(),zoneRecipes=new Set();
  let run=null,cursor=0,events=0,disposed=false,perBoss=Array(8).fill(0),kinds={};
  function reset(nextRun=null,nextCursor=0) {
    if(disposed)return;
    run=nextRun;cursor=nextCursor;events=0;perBoss=Array(8).fill(0);kinds={};aims.clear();zoneRecipes.clear();
    fx.reset(nextRun);projectiles.reset(nextRun);
  }
  function update(frame,native,S=.028) {
    if(disposed)return;
    if(run!==frame.run)reset(frame.run);
    const incoming=(frame.bossEvents||[]).filter(e=>e.id>cursor);
    for(const e of incoming)if(e.kind==='attack'||e.kind==='charge')aims.set(bossOwnerId(e.source,e.generation),e.angle);
    const actors=[],liveOwners=new Set(),liveZones=new Map(),E=frame.E;
    for(let i=0;i<E.max;i++)if(E.a[i]&&E.tier[i]===2){
      const uid=bossOwnerId(i,E.gen[i]);liveOwners.add(uid);
      actors.push({uid,x:E.x[i],y:E.y[i],aim:E.charge[i]>0?Math.atan2(E.dy[i],E.dx[i]):aims.get(uid)??0,downed:false});
    }
    for(const uid of aims.keys())if(!liveOwners.has(uid))aims.delete(uid);
    for(const z of frame.zones||[])if(z.boss&&z.id){
      liveZones.set(z.id,z);actors.push({uid:zoneOwnerId(z.id),x:z.x,y:z.y,aim:0,downed:false});
    }
    for(const id of zoneRecipes)if(!liveZones.has(id))zoneRecipes.delete(id);
    const sceneFrame={...frame,P:null,agents:actors,skillEvents:[]};
    // 先清理上一帧预约；快进时过期打击不能挤掉仍有效的毒池。
    fx.update(sceneFrame,native,S);
    for(const e of incoming){
      cursor=e.id;
      const recipe=BOSS_EFFECTS[e.boss];
      if(!recipe?.[e.kind]||!Number.isFinite(e.time))continue;
      if(e.kind!=='zone'){
        const c=bossContext(e,S);
        fx.sequence(recipe[e.kind](c),primitiveContext(c),e.time);
      }
      events++;perBoss[e.boss]++;kinds[e.kind]=(kinds[e.kind]||0)+1;
    }
    let rebuilt=false;
    // 持续区域从仍活着的战斗状态恢复，而非依赖早已跳过的事件。
    // Canvas / 高清切换只恢复毒池与井，不重播已结束的爆炸或起手。
    for(const [id,z] of liveZones)if(!zoneRecipes.has(id)){
      const c=bossContext({...z.boss,kind:'zone',id,zoneId:id,x:z.x,y:z.y,r:z.r,duration:z.life},S);
      const definition=BOSS_EFFECTS[c.boss].zone(c);
      // 原生同帧会推进新区域 age；用真实 age 对齐溶解曲线，并在区域移除时取消。
      // 主人是区域 uid 而非 Boss uid，击杀 Boss 不会抹掉仍在伤人的地面。
      for(const cue of definition.cues)cue.effect={...cue.effect,cancelOnOwnerLoss:true};
      if(fx.sequence(definition,primitiveContext(c),frame.run.time-z.age)){zoneRecipes.add(id);rebuilt=true;}
    }
    if(incoming.length||rebuilt)fx.update(sceneFrame,native,S);
    projectiles.update(frame,native,S);
  }
  return {update,reset,metrics:()=>({...fx.metrics(),events,perBoss:[...perBoss],kinds:{...kinds},cursor,liveZoneRecipes:zoneRecipes.size,projectiles:projectiles.metrics(),disposed}),
    dispose(){if(disposed)return;reset();fx.dispose();projectiles.dispose();disposed=true;}};
}
