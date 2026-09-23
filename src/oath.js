    /* Circuit decisions run at 5 Hz; the existing 60 Hz simulation owns physics. */
    const OC=NRCircuits,OD=NROathData,loadedOath=OD.load(localStorage);
    const OATH={profile:loadedOath.profile,warning:loadedOath.warning,verified:new Map(),leader:{slot:0,mode:'off',token:null,uid:0,actor:null,seq:0,lastSeen:0},command:'guard',clock:0};
    const oathText=(en,zh)=>language==='zh'?zh:en;
    function oathSave(){if(OATH.warning)return false;const ok=OD.save(localStorage,OATH.profile);if(!ok)toast(oathText('Storage unavailable · export your blueprints','无法写入存档 · 请导出蓝图'));return ok;}
    function oathName(r){return r?.[language]||r?.blueprint?.name||r?.name||r?.id||'—';}
    function oathInstance(id){
      const r=OD.find(OATH.profile,id);if(!r)return null;
      const c=OC.decode(r.circuit);
      return{id,c,state:new Uint8Array(c.nState),cooldown:0,ack:false,fires:0,fault:null,source:r.source.type==='xlayer'?(OATH.verified.has(id)?'verified':'unverified'):'local'};
    }
    function oathSetupActor(a,config){
      a.oath={energy:65,chip:config.mode==='chip'?oathInstance(config.chip):null,relics:config.relics.map(oathInstance).filter(Boolean),rescueEvent:false,decisions:0,lastDecision:null};
      a.controller=config.mode;a.strictIntent=config.mode==='chip';
      if(a.controller==='chip')a.order={tactic:'guard',stance:'balanced',autoSkills:false,until:Infinity};
    }
    function oathApplyLoadout(){
      const l=OD.validateLoadout(OATH.profile.loadout,OATH.profile);
      for(let i=0;i<3;i++){
        const s=PARTY.slots[i],v=l.slots[i];
        if(s.mode!==v.mode||s.heroId!==v.heroId)coopConfigure(i+1,v.mode,v.heroId);
        s.chip=v.chip;s.relics=[...v.relics];
      }
      OATH.leader.mode=l.leader==='external'?'external':'off';
      if(l.leader==='human')oathRevokeLeader();
      if(l.leader==='external'||l.slots.some(s=>s.mode==='external'))PARTY.enabled=true;
      coopRefreshUI();
    }
    function oathPreflight(){
      const l=OATH.profile.loadout,ids=[...l.leaderRelics,...l.slots.filter(s=>s.mode!=='off').flatMap(s=>[...(s.mode==='chip'?[s.chip]:[]),...s.relics])].filter(Boolean);
      const unverified=ids.find(id=>OD.find(OATH.profile,id)?.source.type==='xlayer'&&!OATH.verified.has(id));
      if(unverified){toast(oathText('Re-verify equipped chain circuits in the workshop, or equip a free template.','请在工坊重新校验已装备的链上电路，或换用免费模板。'),5);return false;}return true;
    }
    function oathStartRun(){
      OATH.clock=0;OATH.command='guard';
      const l=OATH.profile.loadout;
      oathSetupActor(P,{mode:l.leader==='external'?'external':'human',relics:l.leaderRelics});
      P.order={tactic:'hold',x:P.x,y:P.y,stance:'defensive',autoSkills:false,until:Infinity};
      OATH.leader.actor=P;OATH.leader.pending=false;
      if(P.controller==='external'&&!OATH.leader.token)P.stale=true;
      for(const s of PARTY.slots)if(s.actor)oathAttachSeat(s);
      if(mode==='expedition'){P.nextXP=110;expeditionStart();}
    }
    function oathAttachSeat(s){oathSetupActor(s.actor,{mode:s.mode,relics:s.relics||[],chip:s.chip||'oathkeeper'});if(s.mode==='chip')s.actor.name=oathName(OD.find(OATH.profile,s.chip||'oathkeeper'));}
    function oathFacts(a){
      const alive=partyActors().filter(u=>!u.downed),near=alive.filter(u=>dist2(u.x-a.x,u.y-a.y)<280**2),ex=run?.expedition,ob=ex?.objective;
      const th=coopThreat(a),boss=run.bossId>=0&&E.a[run.bossId];
      return {ally_down:partyActors().some(u=>u!==a&&u.downed),self_low:a.hp<a.maxhp*.35,self_recovered:a.hp>=a.maxhp*.70,
        boss:!!boss,ally_low:near.some(u=>u.hp<u.maxhp*.60),skill_ready:a.skillCD<=0,ultimate_ready:a.ult>=99.9&&a.ultTime<=0,
        danger:th.count>=3,blade_room:a.swords<24,objective:!!ob,objective_threat:!!ob&&ob.threat>0,rescue_event:!!a.oath?.rescueEvent,
        leader_assault:OATH.command==='assault',leader_guard:OATH.command==='guard',distant:dist2(a.x-P.x,a.y-P.y)>330**2,
        alive:!a.downed,relic_ready:false,effect_applied:false,boss_window:!!boss&&(!ex||ex.bossWindow),moving:!!a.moving};
    }
    function oathChipFault(a,e){
      a.oath.chip.fault=e.message;a.oath.requests=null;
      a.order={tactic:'hold',x:a.x,y:a.y,stance:'defensive',autoSkills:false,until:Infinity};
      coopEvent('circuit_fault',{unit:a.uid?'a'+a.uid:'human',error:e.message});
    }
    function oathDecision(a){
      const inst=a.oath?.chip;if(!inst||inst.fault)return;
      try{const r=OC.step(inst.c,inst.state,OC.bits(oathFacts(a))),d=OC.interpret(inst.c,r.outputs);inst.state=r.state;
        a.order={tactic:d.tactic,stance:d.tactic==='retreat'?'defensive':'balanced',autoSkills:false,until:Infinity};
        a.path=d.upgradePath;a.nextThink=0;a.oath.lastDecision=d;a.oath.decisions++;a.oath.requests=d;
      }catch(e){oathChipFault(a,e);}
    }
    function oathAbilities(a){
      const d=a.oath?.requests;if(!d)return;a.oath.requests=null;if(a.downed)return;
      if(d.skill)castSkill(a);if(d.ultimate)ultimate(a);
      const fallen=coopRescueTarget(a);if(d.dash&&(!fallen||dist2(fallen.x-a.x,fallen.y-a.y)>240**2))coopDash(a);
    }
    function oathRelicEffect(a,effect){
      if(!OATH.profile.unlocked.includes(effect))return false;
      const near=partyActors().filter(u=>!u.downed&&dist2(u.x-a.x,u.y-a.y)<280**2).sort((u,v)=>u.hp/u.maxhp-v.hp/v.maxhp);
      let target=near[0],applied=false;
      if(effect==='shield'&&target&&target.shield<target.maxhp*.60){target.shield=Math.min(target.maxhp*.60,target.shield+28+target.maxhp*.10);applied=true;}
      if(effect==='heal'&&target&&target.hp<target.maxhp){target.hp=Math.min(target.maxhp,target.hp+24+target.maxhp*.12);applied=true;}
      if(effect==='repulse'||effect==='frost')queryCircle(a.x,a.y,effect==='frost'?210:170,i=>{if(!E.a[i])return;const d=Math.hypot(E.x[i]-a.x,E.y[i]-a.y)||1;if(effect==='repulse'){E.kx[i]+=(E.x[i]-a.x)/d*(E.tier[i]===2?80:380);E.ky[i]+=(E.y[i]-a.y)/d*(E.tier[i]===2?80:380);E.stagger[i]=.3;}else E.freeze[i]=Math.max(E.freeze[i],E.tier[i]===2?.25:2.8);applied=true;});
      if(effect==='fury'&&a.boost<1){a.boost=5;applied=true;}
      if(effect==='charge'&&a.ult<85&&a.ultTime<=0){a.ult=Math.min(100,a.ult+18);applied=true;}
      if(applied)ring((effect==='shield'||effect==='heal'?target:a).x,(effect==='shield'||effect==='heal'?target:a).y,100,'#f1d18a',.7,3);
      return applied;
    }
    function oathTick(dt){
      for(const a of partyActors())if(a.oath){
        if(a.downed){for(const i of [a.oath.chip,...a.oath.relics].filter(Boolean)){i.state.fill(0);i.ack=false;}a.oath.rescueEvent=false;continue;}
        a.oath.energy=Math.min(100,a.oath.energy+dt*2.2*(run.expedition?.contract==='scarcity'?.65:1));
        for(const i of a.oath.relics)i.cooldown=Math.max(0,i.cooldown-dt);
      }
      OATH.clock-=dt;if(OATH.clock>0)return;OATH.clock+=.2;
      for(const a of partyActors())if(a.oath&&!a.downed){
        oathDecision(a);
        for(const i of a.oath.relics){if(i.fault)continue;
          try{
            const f=oathFacts(a);f.relic_ready=i.cooldown<=0;f.effect_applied=i.ack;
            const r=OC.step(i.c,i.state,OC.bits(f));i.state=r.state;const {effect}=OC.interpret(i.c,r.outputs),priorAck=i.ack;i.ack=false;
            // A previous success is consumed in this tick. Never fire twice from one latch.
            if(effect&&!priorAck&&i.cooldown<=0){const base=OD.bases[effect];if(a.oath.energy>=base.cost&&oathRelicEffect(a,effect)){a.oath.energy-=base.cost;i.cooldown=base.cooldown;i.ack=true;i.fires++;coopEvent('relic_fired',{unit:a.uid?'a'+a.uid:'human',blueprint:i.id,effect,energy:round3(a.oath.energy)});}}
          }catch(e){i.fault=e.message;coopEvent('relic_fault',{blueprint:i.id,error:e.message});}
        }
        a.oath.rescueEvent=false;
      }
    }
    function oathRescued(rescuers){for(const a of rescuers)if(a.oath)a.oath.rescueEvent=true;}
    function oathGoal(a,gx,gy){
      if(a.order?.tactic==='objective'&&run.expedition?.objective){gx=run.expedition.objective.x;gy=run.expedition.objective.y;}
      if(a.order?.tactic==='retreat'){const i=nearest(a.x,a.y,650);if(i>=0){const d=Math.hypot(a.x-E.x[i],a.y-E.y[i])||1;gx=a.x+(a.x-E.x[i])/d*200;gy=a.y+(a.y-E.y[i])/d*200;}}
      return{x:gx,y:gy};
    }
    function oathLeaderMove(dt){
      const a=P,s=OATH.leader;
      if(a.controller!=='external')return null;
      if(!s.token||performance.now()-s.lastSeen>90000){a.stale=true;a.order={tactic:'hold',x:a.x,y:a.y,stance:'defensive',autoSkills:false,until:Infinity};}
      else if(a.order.until<run.time){a.order={tactic:'guard',stance:'defensive',autoSkills:true,until:Infinity};coopEvent('order_expired',{unit:'human'});}
      const o=a.order,idx=coopCombatTarget(a),fallen=coopRescueTarget(a);let gx=a.x,gy=a.y;
      if(o.tactic==='hold'||o.tactic==='move'){gx=o.x??a.x;gy=o.y??a.y;}
      else if(fallen){gx=fallen.x;gy=fallen.y;}
      else if(['assault','focus'].includes(o.tactic)&&idx>=0){const d=Math.hypot(a.x-E.x[idx],a.y-E.y[idx])||1;gx=E.x[idx]+(a.x-E.x[idx])/d*210;gy=E.y[idx]+(a.y-E.y[idx])/d*210;}
      const g=oathGoal(a,gx,gy),th=coopThreat(a),m=coopSteer(a,clamp(g.x,-1490,1490),clamp(g.y,-1310,1310),th,!!fallen);coopAim(a,idx);
      if(fallen&&dist2(a.x-fallen.x,a.y-fallen.y)<64**2)a.dashTime=0;
      if(o.autoSkills&&!a.stale){if(th.count>2||oathFacts(a).ally_low&&a.heroId===4)castSkill(a);if(run.bossId>=0&&a.ult>=99.9)ultimate(a);}
      return m;
    }
    function oathRevokeLeader(){const s=OATH.leader;s.token=null;s.seq=0;s.actor=P;s.mode='off';if(P){P.controller='human';P.stale=false;}if(typeof resetInput==='function'&&$('joystick')?.firstElementChild)resetInput();}
    function oathLeaveLeader(){const s=OATH.leader;s.token=null;s.seq=0;s.pending=false;if(P){P.stale=true;P.order={tactic:'hold',x:P.x,y:P.y,stance:'defensive',autoSkills:false,until:Infinity};}coopEvent('agent_left',{slot:0,reason:'agent_left'});}
    function oathTakeover(){oathRevokeLeader();OATH.profile.loadout.leader='human';oathSave();coopEvent('leader_control',{controller:'human'});oathHUD();}
    function oathAuthorize(args){if(args.agentId!=='leader')return null;const s=OATH.leader;if(!PARTY.enabled||s.mode!=='external'||!s.token||args.token!==s.token)throw Error('UNAUTHORIZED');return s;}
    function oathJoinLeader(args){const s=OATH.leader;if(!PARTY.enabled||s.mode!=='external')throw Error('SEAT_NOT_RESERVED');if(s.token)throw Error('SEAT_OCCUPIED');s.token=opaqueId();s.seq=0;s.name=args.name.replace(/[<>\u0000-\u001f]/g,'').trim();s.lastSeen=performance.now();s.actor=P;s.pending=!P||!run||run.ended||!['play','paused','route','camp'].includes(state);if(P)P.stale=false;coopEvent('agent_joined',{slot:0,agentId:'leader',pending:s.pending});return{ok:true,agentId:'leader',token:s.token,heroId:selected,pending:s.pending,runId:PARTY.runId,nextSeq:1,leaseSeconds:90};}
    function oathObservation(){return{leader:{controller:P?.controller||OATH.profile.loadout.leader,connected:!!OATH.leader.token,stale:!!P?.stale},command:OATH.command,expedition:expeditionObserve()};}
    function oathUnit(a){return{controller:a.controller||'legacy',upgradePath:a.path,pendingUpgrades:a.pending||0,energy:a.oath?round3(a.oath.energy):null,chip:a.oath?.chip?{id:a.oath.chip.id,source:a.oath.chip.source,fault:a.oath.chip.fault,decisions:a.oath.decisions,lastDecision:a.oath.lastDecision}:null,relics:a.oath?.relics.map(i=>({id:i.id,cooldown:round3(i.cooldown),memory:Array.from(i.state),fires:i.fires,fault:i.fault,source:i.source}))||[]};}
