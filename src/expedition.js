    /* Route/camp states stop combat. All objectives advance on simulation time. */
    const EX_TYPES={
      clear:{en:'Break the blockade',zh:'冲破封锁',tip:['Defeat 200 enemies and hold for 100s.','击败 200 名敌人，并坚持 100 秒。'],seconds:180},
      defend:{en:'Hold the beacon',zh:'守住信标',tip:['Stay within 160m to attune for 95s. Enemies inside 120m damage its integrity.','靠近 160 范围内持续校准 95 秒。进入 120 范围的敌人会破坏信标。'],seconds:180},
      escort:{en:'Carry the last light',zh:'护送余烬',tip:['Escort the moving lantern within 180m. Clear enemies ahead.','在 180 范围内护送移动灯芯；清理沿路敌人。'],seconds:210},
      rescue:{en:'Recover the lost',zh:'营救失落者',tip:['Channel near each of three seals for 25s. Nearby enemies interrupt the channel.','依次靠近三处封印各维持 25 秒；附近敌人会干扰解救。'],seconds:180},
      boss:{en:'Break the sovereign',zh:'击破君王',tip:['A 7s opening every 24s amplifies damage. Coordinate your burst.','每 24 秒出现一次 7 秒破绽；合力爆发造成更多伤害。'],seconds:240}
    };
    function expeditionStart(){
      const seed=crypto.getRandomValues(new Uint32Array(1))[0];
      run.expedition={seed,chapter:0,node:0,phase:'route',contract:['scarcity','hunted'].includes($('oathContract')?.value)?$('oathContract').value:'none',cleared:0,research:0,buffs:[],choices:[],clock:0,objective:null,bossWindow:false,resultRecorded:false};
    }
    function expeditionRoute(){if(!run?.expedition||run.ended)return;state='route';run.expedition.phase='route';resetInput();audio.pause(true);hide('hud');hide('bossHud');hide('upgradePanel');expeditionRenderRoute();show('routeModal');coopHUD();oathHUD();}
    function expeditionOptions(){const ex=run.expedition;if(ex.node===3)return['boss'];if(ex.chapter===0&&ex.node===0)return['clear','rescue'];const types=['clear','escort','defend','rescue'];const k=(ex.seed+ex.chapter*7+ex.node*3)>>>0;return[types[k%4],types[(k+1)%4]];}
    function expeditionChoose(type){
      const ex=run?.expedition;if(state!=='route'||!ex||!expeditionOptions().includes(type))return false;
      for(const pool of [E,B,HB,O,F])pool.clear();for(const arr of [warnings,zones,rings,lines,numbers,traces])arr.length=0;
      ex.phase='encounter';ex.type=type;ex.clock=0;ex.startKills=run.kills;ex.choices.push(type);ex.spawn=0;ex.marker=0;
      run.wave=ex.chapter*4+ex.node+1;run.waveClock=0;run.waveLength=EX_TYPES[type].seconds;run.bossId=-1;run.bossSpawned=false;
      setStage(ex.chapter,true);P.x=-350;P.y=0;
      coopWaveStart();partyActors().forEach((a,i)=>{a.x=P.x+Math.sin(i*2)*70;a.y=P.y+Math.cos(i*2)*70;a.inv=Math.max(a.inv,2);});
      ex.objective=['escort','defend','rescue'].includes(type)?{x:type==='escort'?-300:0,y:0,hp:100,progress:0,target:type==='escort'?1300:type==='defend'?95:75,threat:0,rescued:0}:null;
      state='play';hide('routeModal');hide('campModal');show('hud');audio.init();audio.pause(false);audio.music(type==='boss'?'music_boss':'music_battle');
      if(type==='boss')spawnEnemy([1,4,7][ex.chapter],2,P.x+350,P.y-80);else spawnPack(28,true);
      buildHash();snapPrevious();lastFrame=performance.now();simAccumulator=0;
      announce(oathText('CHAPTER ','区域 ')+(ex.chapter+1),EX_TYPES[type][language],EX_TYPES[type].tip[language==='en'?0:1],4);
      coopEvent('expedition_encounter',{chapter:ex.chapter+1,node:ex.node+1,encounterType:type});return true;
    }
    function expeditionDirector(dt){
      const ex=run.expedition;if(!ex||ex.phase!=='encounter')return;
      ex.clock+=dt;run.waveClock=ex.clock;run.phase=Math.floor(ex.clock/15)%4;
      ex.bossWindow=ex.type==='boss'&&ex.clock%24>=17;
      const cap=Math.round((100+ex.chapter*22)*(run.scaling?.density||1)),mult=ex.contract==='hunted'?1.3:1;
      ex.spawn+=dt*(ex.type==='boss'?2.5:6+ex.chapter*1.3)*DIFFS[difficulty].spawn*mult*(run.scaling?.density||1);
      let budget=5;while(ex.spawn>=1&&E.count<cap&&budget-->0){spawnPack(1);ex.spawn--;}ex.spawn=Math.min(5,ex.spawn);
      const ob=ex.objective;
      if(ob){
        const escorts=partyActors().filter(a=>!a.downed&&dist2(a.x-ob.x,a.y-ob.y)<(ex.type==='escort'?180:160)**2);
        let threat=0;queryCircle(ob.x,ob.y,120,i=>{if(E.a[i])threat++;});ob.threat=threat;
        if(ex.type==='defend'){
          if(escorts.length)ob.progress+=dt*(threat? .7:1);
          ob.hp-=dt*Math.min(1.4,threat*.13);if(!threat&&escorts.length)ob.hp=Math.min(100,ob.hp+dt*.6);
        }else if(ex.type==='escort'){
          if(escorts.length&&threat<4){const move=dt*13;ob.progress=Math.min(ob.target,ob.progress+move);ob.x=-300+ob.progress;ob.y=Math.sin(ob.progress/170)*140;}
          ob.hp-=dt*Math.min(1.2,threat*.12);if(!threat&&escorts.length)ob.hp=Math.min(100,ob.hp+dt*.4);
        }else if(ex.type==='rescue'){
          if(escorts.length&&threat<3)ob.progress+=dt;
          const savedNow=Math.min(3,Math.floor(ob.progress/25));
          if(savedNow>ob.rescued){ob.rescued=savedNow;ob.x=[0,280,-240,0][savedNow];ob.y=[0,-150,180,0][savedNow];coopEvent('prisoner_rescued',{count:savedNow});for(const a of escorts)if(a.oath)a.oath.rescueEvent=true;}
        }
        ex.marker-=dt;if(ex.marker<=0){ex.marker=.7;ring(ob.x,ob.y,ex.type==='escort'?180:160,ob.threat?'#eea27e':'#f0d590',.85,4);}
        if(ob.hp<=0){ex.failure='objective_lost';finish(false);return;}
      }
      const success=ex.type==='boss'?run.bosses>ex.chapter:ex.type==='clear'?run.kills-ex.startKills>=200&&ex.clock>=100:ob.progress>=ob.target;
      if(success){expeditionComplete();return;}
      if(ex.clock>=EX_TYPES[ex.type].seconds){ex.failure='timeout';finish(false);}
    }
    function expeditionComplete(){
      const ex=run.expedition;if(ex.phase!=='encounter')return;
      ex.cleared++;ex.research+=ex.type==='boss'?15:5;ex.phase='camp';ex.objective=null;
      coopEvent('encounter_complete',{chapter:ex.chapter+1,node:ex.node+1,encounterType:ex.type});
      if(ex.chapter===2&&ex.node===3){finish(true);return;}
      state='camp';resetInput();hide('hud');hide('bossHud');hide('upgradePanel');audio.pause(true);expeditionRenderCamp();show('campModal');coopHUD();oathHUD();
    }
    function expeditionReward(kind){
      const ex=run?.expedition;if(state!=='camp'||ex?.phase!=='camp'||!['mend','edge','battery'].includes(kind))return false;
      ex.buffs.push(kind);
      for(const a of partyActors()){
        if(a.downed)coopRevive(a,'camp');
        if(kind==='mend'){a.maxhp+=6;a.hp=Math.min(a.maxhp,a.hp+a.maxhp*.45);}
        if(kind==='edge')a.damage*=1.07;
        if(kind==='battery'&&a.oath)a.oath.energy=Math.min(100,a.oath.energy+40);
      }
      ex.node++;if(ex.node>3){ex.node=0;ex.chapter++;}
      hide('campModal');expeditionRoute();return true;
    }
    function expeditionFinish(won){
      const ex=run?.expedition;if(!ex||ex.resultRecorded)return;ex.resultRecorded=true;ex.phase='result';
      const p=OATH.profile,reward=ex.research+(won?20:0)+(ex.contract!=='none'?Math.floor(ex.research*.3):0);
      ex.reward=reward;p.research=Math.min(1e6,p.research+reward);p.runs=Math.min(1e6,p.runs+1);if(won)p.wins=Math.min(1e6,p.wins+1);p.bestChapter=Math.max(p.bestChapter,ex.chapter+(won?1:0));
      p.history.unshift({date:new Date().toISOString(),won,chapter:ex.chapter+1,time:run.time,seed:ex.seed,research:reward});p.history=p.history.slice(0,12);oathSave();hide('routeModal');hide('campModal');oathHUD();
    }
    function expeditionObserve(){const ex=run?.expedition;return ex?{chapter:ex.chapter+1,node:ex.node+1,type:ex.type||null,phase:ex.phase,clock:round3(ex.clock),remaining:ex.type?round3(Math.max(0,EX_TYPES[ex.type].seconds-ex.clock)):null,contract:ex.contract,cleared:ex.cleared,bossWindow:ex.bossWindow,objective:ex.objective?{...ex.objective}:null}:null;}
