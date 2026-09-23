/* 明确标注的规则示例，不是大模型。替换 decide 为你自己的 Agent 推理即可。
 * 本文件只定义策略，载入不会自动入队或修改游戏。
 */
globalThis.NRExampleRulePolicy=async(world,{agentId})=>{
  const self=world.units.find(u=>u.id===agentId);
  if(!self)return null;
  const fallen=world.units.some(u=>u.id!==agentId&&u.downed);
  if(fallen)return{tactic:'rescue',stance:'defensive',duration:8,autoSkills:true,upgradePath:2};
  if(self.hp/self.maxHP<.35)return{tactic:'guard',stance:'defensive',duration:6,autoSkills:true};
  const boss=world.enemies.find(e=>e.tier===2);
  return{tactic:boss?'focus':'follow',stance:'balanced',duration:8,autoSkills:true,...(boss?{target:boss.id}:{})};
};
