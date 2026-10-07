    const OATH_TOKEN_RELEASE = Object.freeze(__OATH_RELEASE_JSON__);
    let economyPhase = OATH_TOKEN_RELEASE.status === 'launched' ? 2 : 1;
    function economyLink(text, href) {
      const link=oe('a','o-link',text);link.href=href;link.target='_blank';link.rel='noopener noreferrer';return link;
    }
    function oathEconomy() {
      const body=$('oathBody'),token=OATH_TOKEN_RELEASE,live=token.status==='launched';
      body.append(oe('p','o-intro',oathText('Nandverse connects games through shared NAND/LATCH materials. Neon Reliquary is the first game; OATH is the ecosystem token. More games are planned.','Nandverse 以共用 NAND／LATCH 材料连接游戏。Neon Reliquary 是首款游戏；OATH 是生态代币。更多游戏尚在规划中。')));
      const grid=oe('div','o-ecosystem-grid');
      for(const [en,zh,descEn,descZh,noteEn,noteZh] of [
        ['PLAY','游戏','Free expeditions with human, external AI and circuit companions. Verified chip bytes drive local behavior.','免费远征，可混编人类、外部 AI 与战术芯片队友。读回校验后的芯片在本地驱动行为。','Available now · one game','已开放 · 当前一款游戏'],
        ['MATERIALS / THE FOUNDRY','材料／铸造厂','Buy missing NAND/LATCH in OKB and consume the required gates to manufacture a chip. Materials can be held in your wallet before manufacturing.','用 OKB 购买缺少的 NAND／LATCH；制造芯片时消耗所需门数。材料可先保存在钱包中。','Material sales ≠ protocol fees ≠ Gas','材料销售收入 ≠ 协议费 ≠ Gas'],
        ['OATH / THE ECOSYSTEM','OATH／生态','A token for Nandverse and future games. Trading tax: 1% on buys and sells; of that tax, holders receive 20% and the project receives 80%.','面向 Nandverse 与未来游戏的代币。买卖税各 1%；该税款中持币者分 20%，项目分 80%。','Consumption and staking are planned','消费与质押尚未开放']
      ]){const card=oe('section','o-ecosystem-card');card.append(oe('h3','',oathText(en,zh)),oe('p','',oathText(descEn,descZh)),oe('small','',oathText(noteEn,noteZh)));grid.append(card);}
      body.append(grid,ob(oathText('Open material quote & chip readback','打开材料报价与芯片读回'),()=>{OUI.tab='forge';oathRender();},'primary'));
      const launch=oe('section','o-forge-block');launch.append(oe('h3','',token.name+' / '+token.symbol),oe('span','o-token-status',live?oathText('Issued on X Layer','已在 X Layer 发行'):oathText('Preparing launch · not issued yet','准备发行 · 尚未发行')));
      launch.append(oe('p','o-small',oathText('OKB quote · IGNIX Standard · System Vault · Initial buy 0 · Anti-snipe off · Graduation protection 1 day. Platform fees, LP fees, Gas and slippage are separate.','OKB 计价 · IGNIX Standard · System Vault · 首购 0 · 反狙击关闭 · 毕业保护 1 天。平台费、LP 费、Gas 与滑点另计。')));
      launch.append(oe('p','o-small',oathText('Holder dividends use the quote asset; minimum eligible holding: 0 OATH (no threshold).','持币者分红使用计价币种；最低持币门槛为 0 OATH（不设门槛）。')));
      if(live){launch.append(oe('p','o-economy-address',oathText('Token: ','代币：')+token.address),oe('p','o-economy-address','Vault: '+token.vault),economyLink(oathText('Official OATH trading page ↗','OATH 官方交易入口 ↗'),token.tradeUrl),economyLink(oathText('Launch transaction ↗','发行交易回执 ↗'),'https://www.oklink.com/x-layer/tx/'+token.transactionHash));}
      else launch.append(oe('p','o-small',oathText('The contract address and trading link will appear after a confirmed launch. No OATH purchase is required to play or manufacture chips.','交易确认后再显示真实合约地址和交易入口。免费游玩与芯片制造均不要求购买 OATH。')));
      launch.append(economyLink(oathText('IGNIX launch documentation ↗','IGNIX 发行说明 ↗'),'https://ignix.bot/docs/launching-a-token'));body.append(launch);
      const phases=[['Before launch','未发行'],['Launch','发行期'],['Graduated','已毕业'],['Consumption','消费开放'],['Staking','质押开放']];
      body.append(oe('h3','',oathText('Five stages · actual features determine progress','五阶段 · 以实际功能为准')));
      const nav=oe('nav','o-economy-phases');nav.setAttribute('aria-label',oathText('Economic stages','经济阶段'));
      phases.forEach(([en,zh],index)=>{const n=index+1,b=ob(n+' · '+oathText(en,zh),()=>{economyPhase=n;oathRender();},n===economyPhase?'chosen':'');b.setAttribute('aria-pressed',String(n===economyPhase));nav.append(b);});body.append(nav);
      const currentPhase=live?2:1;
      const phaseState=economyPhase===currentPhase?oathText('Current stage','当前阶段'):economyPhase<currentPhase?oathText('Completed stage','已完成阶段'):oathText('Planned stage','规划阶段');
      const flow=oe('section','o-phase-flow');flow.append(oe('h4','',economyPhase+' · '+oathText(...phases[economyPhase-1])+' · '+phaseState));
      const lines=[
        ['PLAY → free expedition → circuit behavior','游戏 → 免费远征 → 战术芯片行为'],
        ['OKB → missing NAND/LATCH → material consumption → manufactured chip','OKB → 缺口 NAND／LATCH → 材料消耗 → 制造芯片'],
        ['Material sales → project accounts; protocol fees and Gas are separate','材料销售 → 项目账目；协议费与 Gas 分列']
      ];
      if(economyPhase===2)lines.push(['OKB ↔ OATH curve trading; project trading tax → System Vault → holders 20% / project 80%','OKB ↔ OATH 曲线交易；项目交易税 → System Vault → 持币者 20%／项目 80%']);
      if(economyPhase>=3)lines.push(['OKB ↔ OATH DEX trading; eligible project trading tax → System Vault → holders 20% / project 80%','OKB ↔ OATH 毕业后 DEX 交易；合格项目交易税 → System Vault → 持币者 20%／项目 80%'],['Curve proceeds → graduation liquidity pool; these funds are not project operating income','曲线募资 → 毕业流动性池；该资金不属于项目经营收入']);
      if(economyPhase>=3)lines.push(['Planned: selected project income × a later-defined share → buy OATH → pending-burn pool → batch burn','规划：选定项目收入 × 后续确定比例 → 回购 OATH → 待销毁池 → 批量销毁']);
      if(economyPhase>=4)lines.push(['Planned: OATH consumption settlement → the same pending-burn pool → batch burn','规划：OATH 消费结算 → 同一待销毁池 → 批量销毁']);
      if(economyPhase>=5)lines.push(['Planned: stake principal → rights → return principal; principal stays outside revenue and burn budgets','规划：质押本金 → 权益 → 本金返还；本金不属于收入或销毁预算']);
      for(const [en,zh]of lines)flow.append(oe('p','o-flow-line',oathText(en,zh)));
      flow.append(oe('p','o-small',oathText('Future games share the material system. Author orders, if added, settle in the author’s specified currency; platform income is recorded separately. Buyback scope and share will be set before the first buyback. Refund liabilities and stake principal never enter the burn pool. Material consumption and OATH burning are separate.','未来游戏共用材料体系。作者订单若开放，按作者指定币种结算，平台收益另行记账；首次回购前再确定收入范围与比例。退款责任与质押本金不进入待销毁池。材料消耗与 OATH 销毁分别记录。')));body.append(flow);
    }
