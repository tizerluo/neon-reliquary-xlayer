// Genuine combat using a declared deterministic leader policy. No invincibility,
// enemy clearing, extra damage, health injection or objective-progress shortcuts.
const fs=require('node:fs'),path=require('node:path'),{simulation,ROOT}=require('./sim_harness.cjs');
const rows=[];
const heroes=process.argv.includes('--all')?[0,1,2,3,4,5]:[0];
for(const hero of heroes){
 const s=simulation({seed:9023+hero*17});s.oath.profile.loadout.leader='external';s.startFull({hero,difficulty:1});s.raw().run.expedition.seed=9023+hero*17;const identity=s.call('nr_join',{slot:0,name:'QA deterministic policy'});if(!identity.ok)throw Error(identity.error);
 let seq=0,frames=0,next=0,errors=[],encounters=[],lastType=null;
 while(!s.raw().run.ended&&frames<60*2700){
  const {run,state,P}=s.raw(),ex=run.expedition;
  if(state==='route'){const opts=s.options();const type=opts[(hero+ex.node)%opts.length];s.chooseRoute(type);encounters.push({type,chapter:ex.chapter+1,started:run.time});}
  else if(state==='camp'){s.reward(P.hp<P.maxhp*.7?'mend':ex.node%2?'edge':'battery');}
  else if(state==='play'){
   if(frames>=next&&!P.downed){next=frames+90;const tactic=s.all().some(a=>a!==P&&a.downed)?'rescue':P.hp<P.maxhp*.28?'retreat':ex.objective?'objective':run.bossId>=0?'focus':'assault';
    const result=s.call('nr_command',{agentId:identity.agentId,token:identity.token,runId:identity.runId,seq:++seq,tactic,stance:'balanced',autoSkills:true,duration:4,upgradePath:P.hp<P.maxhp*.6?2:P.swords<24?1:0});if(!result.ok)errors.push(result.error);
   }
   s.tick(1/60);frames++;
  }else throw Error('unexpected state '+state);
 }
 const {run,P,state}=s.raw();const row={hero,seed:9023+hero*17,state,won:s.oath.profile.wins===1,time:run.time,cleared:run.expedition.cleared,failure:run.expedition.failure||null,level:P.level,kills:run.kills,rescues:run.coopRescues,hp:P.hp,units:s.all().map(a=>({hero:a.heroId,hp:a.hp,downed:a.downed,damage:a.damageDealt,relicFires:a.oath.relics.reduce((n,r)=>n+r.fires,0),decisions:a.oath.decisions})),encounters,errors:[...new Set(errors)]};rows.push(row);console.log(JSON.stringify(row));
}
fs.writeFileSync(path.join(ROOT,'evidence/first-edition/endurance.json'),JSON.stringify({scope:'Real combat in Node VM. Deterministic policy controls external leader via public sequenced tools. Chip companions use actual NAND/LATCH decisions. No cheating fixtures. Rendering and audio stubbed.',rows},null,2));
if(rows.some(r=>!r.won||r.state!=='result'||r.cleared!==12||r.errors.length)){console.error('Endurance acceptance failed; see recorded per-class results.');process.exitCode=1;}
