const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');

test('HUD refresh preserves command and takeover button identity during live updates',()=>{
 const element=tag=>({tag,children:[],classList:{values:new Set(),toggle(k,on){on?this.values.add(k):this.values.delete(k);}},append(...xs){this.children.push(...xs);}});
 const elements=Object.fromEntries(['oathHUD','dashBtn','skillBtn','ultBtn'].map(id=>[id,element('div')]));
 const context={document:{createElement:element},$:id=>elements[id],language:'en',state:'play',run:{expedition:null},P:{controller:'external',stale:false,oath:{energy:65}},OATH:{command:'guard'},oathText:(en,zh)=>context.language==='en'?en:zh,oathTakeover(){context.P.controller='human';},EX_TYPES:{}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/oath-ui.js'),'utf8'),context);vm.runInContext('oathHUD()',context);
 const bar=elements.oathHUD.children[2],buttons=[...bar.children],takeover=buttons[3];
 for(let i=0;i<100;i++){context.P.oath.energy=i;vm.runInContext('oathHUD()',context);assert.equal(elements.oathHUD.children[2],bar);bar.children.forEach((node,j)=>assert.equal(node,buttons[j]));}
 buttons[1].onclick();assert.equal(context.OATH.command,'assault');takeover.onclick();vm.runInContext('oathHUD()',context);assert.equal(context.P.controller,'human');assert.equal(elements.skillBtn.disabled,false);assert(takeover.classList.values.has('hidden'));
 context.language='zh';vm.runInContext('oathHUD()',context);assert.equal(buttons[0].textContent,'护卫');assert.equal(buttons[1].textContent,'突击');assert.equal(elements.oathHUD.children[2],bar);
});
