// Execute the real combat simulation in Node; only DOM, audio and rendering are stubbed.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..');
function simulation({seed=82103,coopFile='src/coop.js'}={}){
 const noop=()=>{};
 const drawing=new Proxy({}, {get:()=>noop,set:()=>true});
 const listeners=new Map();
 const listen=(target,type,fn)=>{const key=target+':'+type;listeners.set(key,[...(listeners.get(key)||[]),fn]);};
 const el=(id='anonymous')=>({firstElementChild:{style:{}},getBoundingClientRect:()=>({left:0,top:0,width:110,height:110}),setPointerCapture:noop,style:{setProperty:noop},classList:{add:noop,remove:noop,toggle:noop,contains:()=>true},getContext:()=>drawing,append:noop,replaceChildren:noop,addEventListener:(type,fn)=>listen(id,type,fn),setAttribute:noop,querySelectorAll:()=>[],value:0});
 const elements=new Map();const doc={addEventListener:(type,fn)=>listen('document',type,fn),getElementById:id=>{if(!elements.has(id))elements.set(id,el(id));return elements.get(id)},documentElement:el(),createElement:el,querySelectorAll:()=>[],activeElement:{tagName:'BODY'}};
 let randomState=seed,elapsedMs=0;
 const math=Object.create(Math);math.random=()=>{let t=randomState+=0x6D2B79F5;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296};
 const context={advanceClock:dt=>{elapsedMs+=dt*1000;},document:doc,window:{dispatchEvent:noop,addEventListener:(type,fn)=>listen('window',type,fn)},NRCircuits:require('../src/circuits.js'),NROathData:require('../src/oath-data.js'),localStorage:{getItem:()=>null,setItem:noop},NRAudio:class{init(){}sfx(){}music(){}battle(){}pause(){}},performance:{now:()=>elapsedMs},crypto:require('node:crypto').webcrypto,CustomEvent:class{},Math:math,console,URLSearchParams,location:{search:'?test'}};
 vm.createContext(context);
 const runtime=fs.readFileSync(path.join(ROOT,'src/runtime.js'),'utf8').split('    async function boot()')[0];
 const extra=`
 function oathHUD(){} function expeditionRenderRoute(){} function expeditionRenderCamp(){} function updateHUD(){} function coopRefreshUI(){} function coopHUD(){} function drawMinimap(){} function render(){} function refreshSelection(){} function resetInput(){keys.clear();joy.x=joy.y=0;joyPointer=null;$('joystick').firstElementChild.style.transform='';} function finish(won){if(run.ended)return;run.ended=true;state='result';expeditionFinish(won);} function diagnostics(){} function openInspector(){} function closeInspector(){}
 ready=true;installTest();
 window.sim={bindInputs:bindUI,input:()=>({x:joy.x,y:joy.y,pointer:joyPointer}),start(opts={}){selected=opts.hero??0;difficulty=opts.difficulty??1;mode=opts.mode??'campaign';coopConfigure(1,'bot',opts.companion??4);startGame();},tick:dt=>{advanceClock(dt);step(dt);},pause:pauseGame,raw:()=>({P,actor:PARTY.slots[0].actor,run,state,events:PARTY.events}),clear(){E.clear();B.clear();HB.clear();warnings.length=zones.length=0;buildHash();},spawn:spawnEnemy,hash:buildHash,warnings,zones,threat:coopThreat,steer:typeof coopSteer==='function'?coopSteer:null,coopTick,coopRescue,hurt:hurtActor,call:coopCall,slots:PARTY.slots,oath:OATH,chooseRoute:expeditionChoose,reward:expeditionReward,route:expeditionRoute,options:expeditionOptions,finish,takeover:oathTakeover,decision:oathDecision,preflight:oathPreflight,relicTick:oathTick,effect:oathRelicEffect,revive:coopRevive,level:levelUp,choose:chooseUpgrade,all:partyActors,enemies:E,setState:x=>state=x,apply:oathApplyLoadout,startFull(opts={}){mode='expedition';selected=opts.hero??0;difficulty=opts.difficulty??0;oathApplyLoadout();startGame();},damage:damageEnemy};
 })();`;
 const code=fs.readFileSync(path.join(ROOT,'src/i18n.js'),'utf8')+'\n'+fs.readFileSync(path.join(ROOT,'src/core.js'),'utf8')+'\n'+fs.readFileSync(path.join(ROOT,coopFile),'utf8')+'\n'+fs.readFileSync(path.join(ROOT,'src/oath.js'),'utf8')+'\n'+fs.readFileSync(path.join(ROOT,'src/expedition.js'),'utf8')+'\n'+runtime+extra;
 vm.runInContext(code,context,{filename:'combat-simulation.js'});context.window.sim.inputEvent=(target,type,event={})=>{for(const fn of listeners.get(target+':'+type)||[])fn({preventDefault:noop,...event});};return context.window.sim;
}
module.exports={simulation,ROOT};
