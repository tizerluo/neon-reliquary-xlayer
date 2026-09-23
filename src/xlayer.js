/* TapeOut X Layer adapter. No wallet request occurs until an explicit UI action. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?require('ethers'):root.ethers,node?require('./circuits.js'):root.NRCircuits);if(node)module.exports=api;else root.NRXLayer=api;})(globalThis,(E,C)=>{
 'use strict';
 const CHAIN=196,FACTORY='0x1f09daefa827f02cbb40967cc91b259763760761',RPC='https://rpc.xlayer.tech';
 const FABI=['function isCPU(address) view returns (bool)','function deployFee() view returns (uint256)','function createCPU(string name,string symbol,string story,uint256 transistorSupply,uint256 mintPrice) payable returns(address transistors,address circuits)','event CPUCreated(address indexed circuits,address indexed transistors,address indexed creator,string name,uint256 supply,uint256 mintPrice)'];
 const CABI=['function transistors() view returns(address)','function circuitInfo(uint256 id) view returns(uint32 nIn,uint32 nOut,uint32 nState,uint32 gateCount)','function netlist(uint256 id) view returns(bytes)','function step(uint256 id,bytes state,bytes inputs) view returns(bytes newState,bytes outputs)','function ownerOf(uint256 id) view returns(address)','function TAPEOUT_FEE() view returns(uint256)','function tapeout(bytes nl,uint32 nIn,uint32 nOut) payable returns(uint256)','event TapedOut(uint256 indexed circuitId,address indexed author,uint32 gateCount,uint32 nState)'];
 const TABI=['function circuits() view returns(address)','function supplyCap() view returns(uint256)','function minted() view returns(uint256)','function mintPrice() view returns(uint256)','function protocolFee() view returns(uint256)','function balanceOf(address,uint256) view returns(uint256)','function mint(uint256,uint256) payable'];
 const pack=bits=>{const bytes=new Uint8Array(Math.ceil(bits.length/8));bits.forEach((v,i)=>{if(v)bytes[i>>3]|=1<<(i%8);});return E.hexlify(bytes);};
 const same=(a,b)=>String(a).toLowerCase()===String(b).toLowerCase();
 function makeProvider(){const req=new E.FetchRequest(RPC);req.timeout=12000;return new E.JsonRpcProvider(req,CHAIN,{staticNetwork:true,batchMaxCount:1});}
 class Adapter{
  constructor({provider,ethereum,storage}={}){this.provider=provider||makeProvider();this.ethereum=ethereum;this.storage=storage;this.log=[];try{const log=JSON.parse(storage?.getItem('nr.oath.transactions')||'[]');if(Array.isArray(log))this.log=log.filter(x=>x&&/^0x[\da-f]{64}$/i.test(x.hash)).slice(-30);}catch{}this.account=null;this.busy=false;}
  async network(provider=this.provider){if(Number(await provider.send('eth_chainId',[]))!==CHAIN)throw Error('WRONG_CHAIN');}
  async cpu(address,provider=this.provider,blockTag='latest'){
   address=E.getAddress(address);await this.network(provider);const factory=new E.Contract(FACTORY,FABI,provider),cpu=new E.Contract(address,CABI,provider),opt={blockTag};
   if(!await factory.isCPU(address,opt))throw Error('NOT_FACTORY_PROCESSOR');
   const transistors=await cpu.transistors(opt),t=new E.Contract(transistors,TABI,provider);
   const [back,supply,minted,price,protocol,fee]=await Promise.all([t.circuits(opt),t.supplyCap(opt),t.minted(opt),t.mintPrice(opt),t.protocolFee(opt),cpu.TAPEOUT_FEE(opt)]);
   if(!same(back,address))throw Error('MATERIAL_PROVENANCE_MISMATCH');
   if(fee!==1300000000000000n)throw Error('UNRECOGNIZED_TAPEOUT_FEE');
   return{address,transistors,supply,minted,price,protocol,fee};
  }
  async readCircuit(address,id){
   if(!/^[1-9]\d{0,19}$/.test(String(id)))throw Error('INVALID_CIRCUIT_ID');
   await this.network();const block=await this.provider.getBlockNumber();const info=await this.cpu(address,this.provider,block),cpu=new E.Contract(info.address,CABI,this.provider),opt={blockTag:block};
   const [meta,netlist,owner]=await Promise.all([cpu.circuitInfo(id,opt),cpu.netlist(id,opt),cpu.ownerOf(id,opt)]);
   const c=C.decode({netlist,nIn:Number(meta[0]),nOut:Number(meta[1])});
   if(c.nState!==Number(meta[2])||c.nodes.length!==Number(meta[3]))throw Error('CIRCUIT_METADATA_MISMATCH');
   // Read-only execution comparison. No state or gameplay is written to chain.
   for(let k=0;k<8;k++){
    const inputs=C.INPUTS.map((_,i)=>(k*13+i*7)%11<5?1:0),state=Array(c.nState).fill(k%2),local=C.step(c,state,inputs),remote=await cpu.step(id,pack(state),pack(inputs),opt);
    if(!same(remote[0],pack(local.state))||!same(remote[1],pack(local.outputs)))throw Error('CHAIN_EXECUTION_MISMATCH');
   }
   return{...info,c,owner,block,id:String(id),hash:E.keccak256(netlist)};
  }
  async quote(address,c,account){
   c=C.decode(c);const block=await this.provider.getBlockNumber(),cpu=await this.cpu(address,this.provider,block),t=new E.Contract(cpu.transistors,TABI,this.provider);
   const balances=account?await Promise.all([t.balanceOf(E.getAddress(account),0,{blockTag:block}),t.balanceOf(account,1,{blockTag:block})]):[0n,0n];
   const need=[BigInt(c.nNand)>balances[0]?BigInt(c.nNand)-balances[0]:0n,BigInt(c.nLatch)>balances[1]?BigInt(c.nLatch)-balances[1]:0n];
   if(need[0]+need[1]>cpu.supply-cpu.minted)throw Error('INSUFFICIENT_MATERIAL_SUPPLY');
   const mint=need.map(n=>n?cpu.price*n+cpu.protocol:0n);
   return{...cpu,block,c,balances,need,mint,total:mint[0]+mint[1]+cpu.fee,account:account||null,quotedAt:Date.now()};
  }
  async connect(){
   if(!this.ethereum?.request)throw Error('WALLET_UNAVAILABLE');
   const chain=Number(await this.ethereum.request({method:'eth_chainId'}));
   if(chain!==CHAIN)await this.ethereum.request({method:'wallet_switchEthereumChain',params:[{chainId:'0xc4'}]});
   await this.network(new E.BrowserProvider(this.ethereum));
   const accounts=await this.ethereum.request({method:'eth_requestAccounts'});if(!accounts[0])throw Error('NO_ACCOUNT');this.account=E.getAddress(accounts[0]);return this.account;
  }
  async walletVerified(address){
   if(!this.account)throw Error('CONNECT_WALLET_FIRST');const wallet=new E.BrowserProvider(this.ethereum);
   const accounts=await this.ethereum.request({method:'eth_accounts'});if(!same(accounts[0],this.account))throw Error('ACCOUNT_CHANGED');
   const [a,b]=await Promise.all([this.cpu(address),this.cpu(address,wallet)]);
   for(const key of ['transistors','price','protocol','fee'])if(!same(a[key],b[key]))throw Error('WALLET_RPC_MISMATCH');return a;
  }
  async signStatement(message,expectedAccount){
   if(typeof message!=='string'||!message.startsWith('Neon Reliquary authorship declaration v1\n')||message.length>12000)throw Error('INVALID_AUTHOR_STATEMENT');
   if(!this.account||!same(this.account,expectedAccount))throw Error('AUTHOR_WALLET_REQUIRED');
   const chain=Number(await this.ethereum.request({method:'eth_chainId'})),accounts=await this.ethereum.request({method:'eth_accounts'});
   if(chain!==CHAIN||!same(accounts[0],this.account))throw Error('ACCOUNT_OR_CHAIN_CHANGED');
   const signature=await this.ethereum.request({method:'personal_sign',params:[E.hexlify(E.toUtf8Bytes(message)),this.account]});
   if(!same(E.verifyMessage(message,signature),this.account))throw Error('INVALID_AUTHOR_SIGNATURE');
   return signature;
  }
  async receiptEvidence(address,id,txHash,verified=null){
   if(!/^0x[\da-f]{64}$/i.test(String(txHash)))throw Error('INVALID_TAPEOUT_TRANSACTION');
   if(!/^[1-9]\d{0,19}$/.test(String(id)))throw Error('INVALID_CIRCUIT_ID');
   await this.network();address=E.getAddress(address);
   const circuit=verified||await this.readCircuit(address,id);
   if(!same(circuit.address,address)||String(circuit.id)!==String(id))throw Error('PROOF_CIRCUIT_MISMATCH');
   const receipt=await this.provider.getTransactionReceipt(txHash);
   if(!receipt||receipt.status!==1||!same(receipt.hash,txHash)||!/^0x[\da-f]{64}$/i.test(String(receipt.blockHash))||!Number.isSafeInteger(receipt.blockNumber))throw Error('TAPEOUT_RECEIPT_NOT_FOUND');
   const iface=new E.Interface(CABI),matches=[];
   for(const log of receipt.logs||[])if(same(log.address,address)){
    try{const event=iface.parseLog(log);if(event?.name==='TapedOut'&&String(event.args.circuitId)===String(id)){
     const logIndex=Number(log.index??log.logIndex);
     if(!Number.isSafeInteger(logIndex)||logIndex<0)throw Error('TAPEOUT_LOG_INDEX_MISSING');
     matches.push({chainId:CHAIN,processor:address,circuitId:String(id),txHash:receipt.hash,logIndex,blockNumber:receipt.blockNumber,blockHash:receipt.blockHash,publisher:E.getAddress(event.args.author),netlist:circuit.c.netlist,netlistHash:circuit.hash,nIn:circuit.c.nIn,nOut:circuit.c.nOut,nState:circuit.c.nState,kind:circuit.c.kind});
    }}catch(e){if(e.message==='TAPEOUT_LOG_INDEX_MISSING')throw e;}
   }
   if(matches.length!==1)throw Error(matches.length?'AMBIGUOUS_TAPEOUT_EVENT':'TAPEOUT_EVENT_NOT_FOUND');
   return matches[0];
  }
  journal(entry){this.log.push(entry);try{this.storage?.setItem('nr.oath.transactions',JSON.stringify(this.log.slice(-30)));}catch{}return entry;}
  async checkPending(){
   const last=new Map(this.log.map(e=>[e.hash,e]));
   for(const entry of last.values())if(entry.status==='pending'){
    const receipt=await this.provider.getTransactionReceipt(entry.hash);
    if(!receipt)throw Object.assign(Error('TRANSACTION_PENDING_DO_NOT_RESEND'),{hash:entry.hash});
    this.journal({...entry,status:receipt.status===1?'confirmed':'reverted'});
   }
  }
  async send(label,to,data,value,onProgress=()=>{}){
   await this.checkPending();
   const chain=Number(await this.ethereum.request({method:'eth_chainId'})),accounts=await this.ethereum.request({method:'eth_accounts'});
   if(chain!==CHAIN||!same(accounts[0],this.account))throw Error('ACCOUNT_OR_CHAIN_CHANGED');
   const hash=await this.ethereum.request({method:'eth_sendTransaction',params:[{from:this.account,to,data,value:E.toQuantity(value),chainId:'0xc4'}]});
   const entry=this.journal({label,hash,status:'pending',chainId:CHAIN,date:new Date().toISOString()});onProgress(entry);
   const until=Date.now()+180000;let receipt;
   while(Date.now()<until){receipt=await this.provider.getTransactionReceipt(hash).catch(()=>null);if(receipt)break;await new Promise(r=>setTimeout(r,2000));}
   if(!receipt)throw Object.assign(Error('TRANSACTION_PENDING_DO_NOT_RESEND'),{hash});
   entry.status=receipt.status===1?'confirmed':'reverted';this.journal({...entry});onProgress(entry);
   if(receipt.status!==1)throw Object.assign(Error('TRANSACTION_REVERTED'),{hash});return receipt;
  }
  async manufacture(q,onProgress=()=>{}){
   if(this.busy)throw Error('TRANSACTION_IN_PROGRESS');this.busy=true;
   try{
    if(Date.now()-q.quotedAt>120000)throw Error('QUOTE_EXPIRED');
    await this.walletVerified(q.address);const fresh=await this.quote(q.address,q.c,this.account);
    if(!same(q.account,this.account)||fresh.total>q.total||fresh.price!==q.price||fresh.protocol!==q.protocol)throw Error('QUOTE_CHANGED_REVIEW_AGAIN');
    const material=new E.Interface(TABI),circuit=new E.Interface(CABI);
    for(let i=0;i<2;i++)if(fresh.need[i]>0n){await this.walletVerified(q.address);await this.send(i?'mint LATCH':'mint NAND',fresh.transistors,material.encodeFunctionData('mint',[i,fresh.need[i]]),fresh.mint[i],onProgress);}
    await this.walletVerified(q.address);const receipt=await this.send('tapeout',q.address,circuit.encodeFunctionData('tapeout',[fresh.c.netlist,fresh.c.nIn,fresh.c.nOut]),fresh.fee,onProgress);
    let id=null;for(const log of receipt.logs)if(same(log.address,q.address)){try{const parsed=circuit.parseLog(log);if(parsed?.name==='TapedOut'&&same(parsed.args.author,this.account))id=parsed.args.circuitId.toString();}catch{}}
    if(!id)throw Error('MISSING_TAPEOUT_EVENT');const verified=await this.readCircuit(q.address,id);if(!same(verified.c.netlist,fresh.c.netlist))throw Error('MANUFACTURED_BYTES_MISMATCH');
    const evidence=await this.receiptEvidence(q.address,id,receipt.hash,verified);
    if(!same(evidence.publisher,this.account))throw Error('TAPEOUT_AUTHOR_MISMATCH');
    return{...verified,evidence};
   }finally{this.busy=false;}
  }
  async deployQuote({name,symbol,story,supply,price}){
   if(typeof name!=='string'||!name.trim()||name.length>48||typeof symbol!=='string'||!symbol.trim()||symbol.length>12||typeof story!=='string'||story.length>500)throw Error('INVALID_PROCESSOR_DESCRIPTION');
   if(!/^[1-9]\d{0,17}$/.test(String(supply))||!/^\d+(\.\d{1,18})?$/.test(String(price)))throw Error('INVALID_SUPPLY_OR_PRICE');
   const fee=await new E.Contract(FACTORY,FABI,this.provider).deployFee();await this.network();return{name,symbol,story,supply:BigInt(supply),price:E.parseEther(price),fee,quotedAt:Date.now()};
  }
  async deploy(q,onProgress=()=>{}){
   if(this.busy)throw Error('TRANSACTION_IN_PROGRESS');this.busy=true;
   try{if(!this.account||Date.now()-q.quotedAt>120000)throw Error('CONNECT_AND_REFRESH_QUOTE');
    const wallet=new E.BrowserProvider(this.ethereum);await this.network(wallet);const [a,b]=await Promise.all([new E.Contract(FACTORY,FABI,this.provider).deployFee(),new E.Contract(FACTORY,FABI,wallet).deployFee()]);if(a!==b||a!==q.fee)throw Error('DEPLOY_FEE_CHANGED');
    const iface=new E.Interface(FABI),receipt=await this.send('create processor',FACTORY,iface.encodeFunctionData('createCPU',[q.name,q.symbol,q.story,q.supply,q.price]),q.fee,onProgress);
    for(const log of receipt.logs)if(same(log.address,FACTORY)){try{const p=iface.parseLog(log);if(p?.name==='CPUCreated'&&same(p.args.creator,this.account))return await this.cpu(p.args.circuits);}catch{}}
    throw Error('MISSING_PROCESSOR_EVENT');
   }finally{this.busy=false;}
  }
 }
 return Object.freeze({CHAIN,FACTORY,RPC,FABI,CABI,TABI,pack,Adapter,format:E.formatEther,hash:E.keccak256});
});
