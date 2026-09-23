// 示例客户端只用模拟传输测试；不访问模型、不自动连接账号。
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
require('../examples/agent_client.js');
require('../examples/rule_policy.js');
const results=[];let seq=0,casts=[],pending=false,phase='play',runId='run_test',left=false;
const world=()=>({ok:true,state:phase,runId,units:pending?[]:[{id:'human',hp:100,maxHP:100,downed:false},{id:'a1',hp:70,maxHP:100,downed:false}],enemies:[{id:'e7:9',tier:2}]});
const transport=async(name,args)=>{
 if(name==='nr_join')return JSON.stringify({ok:true,agentId:'a1',token:'x'.repeat(32),nextSeq:1,heroId:2,pending:false,runId});
 if(name==='nr_observe')return world();
 if(name==='nr_heartbeat')return{ok:true,lastSeq:seq,runId};
 if(name==='nr_leave'){left=true;return{ok:true};}
 if(name==='nr_command'){assert.equal(args.runId,runId);assert(args.seq>seq);assert.equal(args.agentId,'a1');assert.equal(args.token,'x'.repeat(32));seq=args.seq;casts.push(args);return{ok:true,seq};}
 throw new Error('Unexpected tool: '+name);
};
(async()=>{
 const client=new NRCompanionClient(transport);const joined=await client.join(1,'TEST');assert(!JSON.stringify(joined).includes('token'));
 results.push({test:'Client normalizes JSON results and does not expose credentials',passed:true});
 await Promise.all([client.command({tactic:'guard'}),client.command({tactic:'follow'})]);assert.deepEqual(casts.map(x=>x.seq),[1,2]);
 results.push({test:'Concurrent client commands serialize to increasing sequences',passed:true});
 runId='run_changed';await client.command({tactic:'focus'});assert.equal(casts.at(-1).runId,runId);
 phase='paused';const skipped=await client.command({tactic:'guard'});assert.equal(skipped.skipped,'NOT_PLAYING');phase='play';pending=true;assert.equal((await client.command({tactic:'guard'})).skipped,'DEPLOYMENT_PENDING');pending=false;
 results.push({test:'Client refreshes run ID and skips paused or pending deployment',passed:true});
 const oldRun=runId;runId='another_run';let count=casts.length;
 const staleRun=await client.command({tactic:'hold',x:1,y:2},{runId:oldRun,startedAt:Date.now(),maxAgeMs:15000});
 assert.equal(staleRun.skipped,'STALE_DECISION');assert.equal(casts.length,count);
 const staleAge=await client.command({tactic:'guard'},{runId,startedAt:Date.now()-16000,maxAgeMs:15000});
 assert.equal(staleAge.skipped,'STALE_DECISION');assert.equal(casts.length,count);
 results.push({test:'Decision context rejects cross-run and expired decisions before sending',passed:true});
 const stopSlow=new AbortController();let slowDecisions=0;count=casts.length;
 await client.run(async()=>{slowDecisions++;if(slowDecisions===1){await Promise.resolve();runId='restarted_while_thinking';return{tactic:'guard'};}stopSlow.abort();return null;},{signal:stopSlow.signal,intervalMs:300});
 assert.equal(slowDecisions,2);assert.equal(casts.length,count);
 results.push({test:'Async decision spanning restart is discarded by run loop',passed:true});
 const decision=await NRExampleRulePolicy(world(),{agentId:'a1'});assert.equal(decision.tactic,'focus');assert.equal(decision.target,'e7:9');
 const abort=new AbortController();let decisions=0;await client.run(async()=>{decisions++;abort.abort();return{tactic:'guard'};},{signal:abort.signal,intervalMs:300});assert.equal(decisions,1);await client.leave();assert(left);assert.equal(client.agentId,null);
 results.push({test:'Explicit rule policy, abort lifecycle and leave',passed:true});
 fs.writeFileSync(path.join(__dirname,'client_results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
