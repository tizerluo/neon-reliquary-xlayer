(function(root,factory){
 const api=factory();
 root.NRWarningData=api;
 if(typeof module==='object'&&module.exports)module.exports=api;
})(globalThis,()=>{
 'use strict';
 const WARNING_CAPACITY=80,TAU=Math.PI*2;
 const positive=n=>Number.isFinite(n)&&n>0;
 const wrap=a=>((a+Math.PI)%TAU+TAU)%TAU-Math.PI;

 // Read simulation age directly: render frames and pause never advance a warning.
 function warningState(w,scale=1){
  if(!w||!positive(scale)||!Number.isFinite(w.age)||w.age<0||!positive(w.delay)||w.age>=w.delay||
   !Number.isFinite(w.x)||!Number.isFinite(w.y))return null;
  const startX=w.x*scale,startZ=w.y*scale;
  const state={type:null,x:startX,z:startZ,startX,startZ,endX:startX,endZ:startZ,
   angle:0,sizeX:0,sizeZ:0,progress:w.age/w.delay,remaining:w.delay-w.age,
   delay:w.delay,age:w.age,boss:w.boss?.boss??null};
  if(w.type===0){
   if(!positive(w.r))return null;
   state.type='circle';state.radius=w.r*scale;
   state.sizeX=state.sizeZ=state.radius*2;
  }else if(w.type===1){
   if(!Number.isFinite(w.angle)||!positive(w.len)||!positive(w.width))return null;
   state.type='lane';state.angle=wrap(w.angle);
   state.length=state.sizeX=w.len*scale;state.width=state.sizeZ=w.width*scale;
   state.endX=startX+Math.cos(state.angle)*state.length;
   state.endZ=startZ+Math.sin(state.angle)*state.length;
   state.x=startX+(state.endX-startX)/2;state.z=startZ+(state.endZ-startZ)/2;
  }else return null;
  // Finite native inputs can overflow when scaled; never send invalid geometry onward.
  if(![state.x,state.z,startX,startZ,state.endX,state.endZ,state.sizeX,state.sizeZ].every(Number.isFinite)||
   !positive(state.sizeX)||!positive(state.sizeZ))return null;
  return state;
 }
 function snapshotWarnings(warnings,scale=1){
  const states=[];
  if(!Array.isArray(warnings))return states;
  for(const w of warnings){
   const state=warningState(w,scale);
   if(state)states.push(state);
   if(states.length===WARNING_CAPACITY)break;
  }
  return states;
 }
 return Object.freeze({WARNING_CAPACITY,warningState,snapshotWarnings});
});
