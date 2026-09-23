/* 将此文件载入已授权的 Agent 宿主。这里只是控制客户端，不包含或冒充大语言模型。
 * transport(name, args) 必须由宿主连接到正在运行的游戏页。不得绕过用户的席位授权。
 */
(function(global){
  'use strict';
  class NRToolError extends Error {
    constructor(code){ super(code); this.name='NRToolError'; this.code=code; }
  }
  class NRCompanionClient {
    #transport; #identity=null; #seq=0; #lastHeartbeat=0; #queue=Promise.resolve();
    constructor(transport){
      if(typeof transport!=='function')throw new TypeError('A tool transport function is required.');
      this.#transport=transport;
    }
    async #call(name,args={}){
      const raw=await this.#transport(name,args);
      const result=typeof raw==='string'?JSON.parse(raw):raw;
      if(!result||typeof result.ok!=='boolean')throw new NRToolError('INVALID_TOOL_RESULT');
      if(!result.ok)throw new NRToolError(result.error||'TOOL_FAILED');
      return result;
    }
    get agentId(){return this.#identity?.agentId??null;}
    async join(slot,name){
      if(this.#identity)throw new NRToolError('ALREADY_JOINED');
      const result=await this.#call('nr_join',{slot,name});
      this.#identity={agentId:result.agentId,token:result.token};
      this.#seq=result.nextSeq-1;this.#lastHeartbeat=Date.now();
      // 凭证只保存在此实例；返回公开状态，不把 token 暴露给日志或其他 Agent。
      return{agentId:result.agentId,heroId:result.heroId,pending:result.pending,runId:result.runId};
    }
    async observe(){return this.#call('nr_observe',this.agentId?{agentId:this.agentId,limit:24}:{limit:24});}
    async heartbeat(){
      if(!this.#identity)throw new NRToolError('NOT_JOINED');
      const r=await this.#call('nr_heartbeat',this.#identity);
      this.#seq=Math.max(this.#seq,r.lastSeq);this.#lastHeartbeat=Date.now();return r;
    }
    command(order,decision=null){
      // 串行化请求；序号单调增长，即使网络重试也不能重复施放同一条指令。
      const execute=async()=>{
        if(!this.#identity)throw new NRToolError('NOT_JOINED');
        const world=await this.observe();
        if(decision && (world.runId!==decision.runId || Date.now()-decision.startedAt>decision.maxAgeMs))
          return {ok:true,skipped:'STALE_DECISION'};
        const unit=world.units.find(u=>u.id===this.agentId);
        if(world.state!=='play'||!unit||unit.downed)
          return{ok:true,skipped:!unit?'DEPLOYMENT_PENDING':unit.downed?'UNIT_DOWNED':'NOT_PLAYING'};
        const allowed=['tactic','stance','x','y','target','autoSkills','duration','cast','upgradePath'];
        if(!order||typeof order!=='object'||Array.isArray(order))throw new TypeError('Invalid order');
        for(const key of Object.keys(order))if(!allowed.includes(key))throw new TypeError('Unknown order key: '+key);
        const result=await this.#call('nr_command',{
          ...order,...this.#identity,runId:world.runId,seq:++this.#seq
        });
        this.#lastHeartbeat=Date.now();return result;
      };
      const result=this.#queue.then(execute);this.#queue=result.catch(()=>{});return result;
    }
    async leave(){
      await this.#queue;
      if(!this.#identity)return{ok:true};
      const result=await this.#call('nr_leave',this.#identity);this.#identity=null;return result;
    }
    async run(decide,{intervalMs=1500,maxDecisionAgeMs=15000,signal,onError=console.warn}={}){
      if(typeof decide!=='function')throw new TypeError('A policy function is required.');
      if(!Number.isFinite(intervalMs)||intervalMs<300)throw new RangeError('Use a sensible polling interval.');
      if(!Number.isFinite(maxDecisionAgeMs)||maxDecisionAgeMs<1)throw new RangeError('Invalid decision age');
      if(!signal)throw new TypeError('Supply an AbortSignal to stop the client explicitly.');
      const sleep=ms=>new Promise(resolve=>{
        if(signal.aborted)return resolve();
        const end=()=>{clearTimeout(timer);signal.removeEventListener('abort',end);resolve();};
        const timer=setTimeout(end,ms);signal.addEventListener('abort',end,{once:true});
      });
      let busy=false,leaseLost=null;
      const timer=setInterval(async()=>{
        if(busy||!this.#identity||Date.now()-this.#lastHeartbeat<25000)return;
        busy=true;try{await this.heartbeat();}catch(error){leaseLost=error;}finally{busy=false;}
      },5000);
      try{
        while(!signal.aborted){
          if(leaseLost)throw leaseLost;
          const startedAt=Date.now();
          const world=await this.observe();const self=world.units.find(u=>u.id===this.agentId);
          if(world.state==='result')return;
          if(world.state==='play'&&self&&!self.downed){
            try{
              // LLM 调用发生在 decide 中。长耗时请求须由宿主遵守 signal；token 不在 world 中。
              const order=await decide(world,{agentId:this.agentId,signal});
              if(signal.aborted)return;
              if(order)await this.command(order,{runId:world.runId,startedAt,maxAgeMs:maxDecisionAgeMs});
            }catch(error){
              const recoverable=['STALE_TARGET','STALE_RUN','STALE_SEQUENCE','RATE_LIMIT','NOT_PLAYING','UNIT_DOWNED','DEPLOYMENT_PENDING'];
              if(!recoverable.includes(error.code))throw error;
              onError(error.code);
              if(error.code==='STALE_SEQUENCE')await this.heartbeat();
            }
          }
          await sleep(intervalMs);
        }
      }finally{clearInterval(timer);}
      // 退出循环不会自动移除角色；宿主可再调用 leave()，或让租约回退到本地护卫。
    }
  }
  async function createNativeNRTransport(context=global.document?.modelContext){
    if(typeof context?.getTools!=='function'||typeof context?.executeTool!=='function')
      throw new Error('This context does not provide the current native WebMCP discovery API.');
    return async(name,args)=>{
      const tools=await context.getTools();
      const tool=tools.find(t=>t.name===name);
      if(!tool)throw new NRToolError('TOOL_NOT_DISCOVERED: '+name);
      return context.executeTool(tool,args);
    };
  }
  global.NRCompanionClient=NRCompanionClient;
  global.NRToolError=NRToolError;
  global.createNativeNRTransport=createNativeNRTransport;
})(globalThis);
