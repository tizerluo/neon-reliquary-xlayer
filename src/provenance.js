/* Exportable authorship evidence. Imported claims are never trusted until chain readback. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?require('ethers'):root.ethers,node?require('./circuits.js'):root.NRCircuits);if(node)module.exports=api;else root.NRProvenance=api;})(globalThis,(E,C)=>{
 'use strict';
 const KEY='nr.oath.provenance.v1',FORMAT='nr-oath-provenance',VERSION=1,MAX_PACKAGE=150000;
 const canonical=x=>JSON.stringify(x,(k,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(key=>[key,v[key]])):v);
 const digest=x=>E.keccak256(E.toUtf8Bytes(canonical(x)));
 const addr=x=>E.getAddress(x);
 const hex32=x=>{if(!/^0x[\da-f]{64}$/i.test(String(x)))throw Error('INVALID_PROOF_HASH');return x.toLowerCase();};
 const integer=(x,name)=>{if(!Number.isSafeInteger(x)||x<0)throw Error('INVALID_'+name);return x;};
 const id=x=>{if(!/^[1-9]\d{0,19}$/.test(String(x)))throw Error('INVALID_CIRCUIT_ID');return String(x);};
 const roles=Object.freeze(['author','coauthor','commissioner','adaptation-author','publisher']);
 const key=p=>p.proof.chainId+':'+p.proof.processor.toLowerCase()+':'+p.proof.circuitId;
 function proof(e){
  if(!e||e.chainId!==196)throw Error('INVALID_PROOF_CHAIN');
  const c=C.decode({netlist:e.netlist,nIn:e.nIn??e.abi?.nIn,nOut:e.nOut??e.abi?.nOut});
  if(c.nState!==(e.nState??e.abi?.nState)||c.kind!==(e.kind??e.abi?.kind))throw Error('PROOF_ABI_MISMATCH');
  const netlistHash=E.keccak256(c.netlist),abi={version:C.VERSION,kind:c.kind,nIn:c.nIn,nOut:c.nOut,nState:c.nState,inputs:[...C.INPUTS]};
  if(hex32(e.netlistHash)!==netlistHash||hex32(e.abiHash)!==digest(abi))throw Error('PROOF_HASH_MISMATCH');
  const result={chainId:196,processor:addr(e.processor),circuitId:id(e.circuitId),txHash:hex32(e.txHash),logIndex:integer(e.logIndex,'LOG_INDEX'),blockNumber:integer(e.blockNumber,'BLOCK_NUMBER'),blockHash:hex32(e.blockHash),publisher:addr(e.publisher),netlist:c.netlist,netlistHash,abi,abiHash:digest(abi)};
  if(e.abi&&canonical(e.abi)!==canonical(abi))throw Error('PROOF_ABI_MISMATCH');
  return result;
 }
 function work(w,p){
  if(!w||typeof w!=='object')throw Error('INVALID_WORK');
  const blueprint=w.blueprint==null?null:C.normalize(w.blueprint);
  if(blueprint&&C.compile(blueprint).netlist!==p.netlist)throw Error('BLUEPRINT_NETLIST_MISMATCH');
  const blueprintHash=blueprint?digest(blueprint):null;
  if(w.blueprintHash!==blueprintHash)throw Error('BLUEPRINT_HASH_MISMATCH');
  const parent=w.parent==null?null:{id:String(w.parent.id),netlistHash:hex32(w.parent.netlistHash)};
  if(parent&&(!/^[\w-]{1,100}$/.test(parent.id)))throw Error('INVALID_PARENT');
  if(w.compiler!=='oath-compiler/1'||w.game!=='neon-reliquary/1.0.0')throw Error('UNSUPPORTED_WORK_VERSION');
  return{blueprint,blueprintHash,compiler:w.compiler,game:w.game,parent};
 }
 function make(evidence,record){
  const c=C.decode({netlist:evidence.netlist,nIn:evidence.nIn,nOut:evidence.nOut});
  const abi={version:C.VERSION,kind:c.kind,nIn:c.nIn,nOut:c.nOut,nState:c.nState,inputs:[...C.INPUTS]};
  const p=proof({...evidence,kind:c.kind,nState:c.nState,netlistHash:E.keccak256(c.netlist),abiHash:digest(abi),abi});
  const blueprint=record?.blueprint?C.normalize(record.blueprint):null;
  if(blueprint&&C.compile(blueprint).netlist!==p.netlist)throw Error('BLUEPRINT_NETLIST_MISMATCH');
  const parent=record?.parent&&record?.parentNetlistHash?{id:record.parent,netlistHash:record.parentNetlistHash}:null;
  return{format:FORMAT,version:VERSION,proof:p,work:{blueprint,blueprintHash:blueprint?digest(blueprint):null,compiler:'oath-compiler/1',game:'neon-reliquary/1.0.0',parent},claims:[]};
 }
 function claimFields(input){
  if(!roles.includes(input?.role))throw Error('INVALID_AUTHOR_ROLE');
  const note=String(input.note||'').trim();if(note.length>500||/[\u0000-\u001f]/.test(note))throw Error('INVALID_AUTHOR_NOTE');
  return{signer:addr(input.signer),role:input.role,royaltyRecipient:input.royaltyRecipient?addr(input.royaltyRecipient):null,note};
 }
 function statement(pkg,fields){
  const p=proof(pkg.proof),w=work(pkg.work,p),f=claimFields(fields);
  return 'Neon Reliquary authorship declaration v1\n'+canonical({chainId:p.chainId,processor:p.processor,circuitId:p.circuitId,txHash:p.txHash,logIndex:p.logIndex,blockNumber:p.blockNumber,blockHash:p.blockHash,publisher:p.publisher,netlistHash:p.netlistHash,abiHash:p.abiHash,workHash:digest(w),claim:f});
 }
 function addClaim(pkg,input,signature){
  const normalized=validate(pkg),fields=claimFields(input),sig=String(signature||'');
  if(!/^0x[\da-f]{130}$/i.test(sig)||addr(E.verifyMessage(statement(normalized,fields),sig))!==fields.signer)throw Error('INVALID_AUTHOR_SIGNATURE');
  if(normalized.claims.some(x=>x.signer===fields.signer&&x.role===fields.role))throw Error('AUTHOR_CLAIM_EXISTS');
  normalized.claims.push({...fields,signature:sig});return normalized;
 }
 function validate(value){
  if(!value||value.format!==FORMAT||value.version!==VERSION||!Array.isArray(value.claims)||value.claims.length>32)throw Error('INVALID_PROVENANCE_PACKAGE');
  const p=proof(value.proof),w=work(value.work,p),pkg={format:FORMAT,version:VERSION,proof:p,work:w,claims:[]};
  for(const item of value.claims){const f=claimFields(item),signature=String(item.signature||'');if(!/^0x[\da-f]{130}$/i.test(signature)||addr(E.verifyMessage(statement(pkg,f),signature))!==f.signer)throw Error('INVALID_AUTHOR_SIGNATURE');if(pkg.claims.some(x=>x.signer===f.signer&&x.role===f.role))throw Error('AUTHOR_CLAIM_EXISTS');pkg.claims.push({...f,signature});}
  return pkg;
 }
 function parse(text){if(typeof text!=='string'||text.length>MAX_PACKAGE)throw Error('PACKAGE_TOO_LARGE');return validate(JSON.parse(text));}
 function exportPackage(pkg){return JSON.stringify(validate(pkg),null,2);}
 function list(storage){let raw;try{raw=storage?.getItem(KEY);}catch{return [];}if(!raw)return[];const data=JSON.parse(raw);if(!Array.isArray(data))throw Error('PROVENANCE_STORE_CORRUPT');return data.map(validate);}
 function save(storage,value){let pkg=validate(value);const all=list(storage),i=all.findIndex(p=>key(p)===key(pkg));if(i<0)all.push(pkg);else{
   const old=all[i];if(canonical(old.proof)!==canonical(pkg.proof)||canonical(old.work)!==canonical(pkg.work))throw Error('PROVENANCE_CONFLICT');
   const claims=[...old.claims];for(const c of pkg.claims){const prior=claims.find(x=>x.signer===c.signer&&x.role===c.role);if(prior&&canonical(prior)!==canonical(c))throw Error('AUTHOR_CLAIM_CONFLICT');if(!prior)claims.push(c);}
   pkg={...pkg,claims};all[i]=pkg;
  }storage.setItem(KEY,JSON.stringify(all));return pkg;}
 return Object.freeze({KEY,FORMAT,VERSION,MAX_PACKAGE,roles,canonical,digest,key,make,statement,addClaim,validate,parse,exportPackage,list,save});
});
