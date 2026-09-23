const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const context=vm.createContext({window:{devicePixelRatio:1}});
vm.runInContext(fs.readFileSync('src/renderer.js','utf8')+';globalThis.rendererPrototype=NRRenderer.prototype;globalThis.matrix=NRM;',context);
for(const [w,h] of [[1280,720],[1440,900],[390,844],[360,800],[844,390]]){
 test(`Ground pointer projection and uniform world scale at ${w}×${h}`,()=>{
  const r=Object.create(context.rendererPrototype);
  Object.assign(r,{canvas:{clientWidth:w,clientHeight:h},options:{quality:'auto'},scale:.028,sinElev:34/Math.hypot(34,27)});
  r.resize();
  const cam={x:147,y:-93},S=r.scale,M=context.matrix;
  const vp=M.mul(M.ortho(r.width,r.height,.1,150),M.look([cam.x*S,34,cam.y*S+27],[cam.x*S,0,cam.y*S]));
  for(const [x,y] of [[.5,.5],[.1,.2],[.85,.8]]){
   const p=r.pointerWorld(x,y,cam),q=M.project([p.x*S,0,p.y*S],vp);
   assert(Math.abs((q[0]+1)/2-x)<1e-6);
   assert(Math.abs((1-q[1])/2-y)<1e-6);
  }
  assert(Math.abs(w/r.viewWidth-h/r.viewHeight)<1e-10,'world is not stretched by CSS aspect');
  if(w===1280)assert.equal(r.viewWidth,1280);
 });
}
