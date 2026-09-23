const {simulation,ROOT}=require('./sim_harness.cjs');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const before=process.argv.includes('--before');
const scenarios=[];
for(const seed of [82103,17,91]){
 const s=simulation({seed,coopFile:before?'evidence/rescue-fix/coop-before.js':'src/coop.js'});s.start();
 // Keep real combat, damage and director. Reproduce an early downed player away from the companion.
 for(let i=0;i<14*60;i++)s.tick(1/60);
 let {P,actor,run}=s.raw();Object.assign(P,{x:-284,y:-504,hp:0,downed:true,revive:0});
 const start=run.time;actor.order={tactic:'rescue',stance:'aggressive',autoSkills:true,until:Infinity};
 let minDistance=Infinity,maxProgress=0,revivedAt=null,nearSeconds=0,damageBefore=actor.damageTaken;
 for(let i=0;i<35*60;i++){
  s.tick(1/60);const d=Math.hypot(actor.x-P.x,actor.y-P.y);minDistance=Math.min(minDistance,d);if(d<72)nearSeconds+=1/60;maxProgress=Math.max(maxProgress,P.revive);
  if(!P.downed){revivedAt=run.time-start;break;}if(s.raw().state==='result')break;
 }
 scenarios.push({seed,revivedAt,minDistance,maxProgress,nearSeconds,actorHP:actor.hp,actorDowned:actor.downed,damageTaken:actor.damageTaken-damageBefore,playerHP:P.hp,kills:s.raw().run.kills,passed:revivedAt!==null&&revivedAt<20});
}
const report={variant:before?'before':'after',scope:'Real core.js + coop.js combat in Node VM; rendering, audio and DOM stubbed. Player downed position is a deliberate fixture; no invincibility, enemy clearing or teleporting rescuer.',scenarios};
fs.mkdirSync(path.join(ROOT,'evidence/rescue-fix'),{recursive:true});
fs.writeFileSync(path.join(ROOT,'evidence/rescue-fix',before?'before.json':'after.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
if(!before)assert(scenarios.every(s=>s.passed),'Full combat rescue failed');
