# Neon Reliquary — Oath Expedition

**[Play the live X Layer edition](https://1-2-231.tapekit.org/)** · [Processor, price, and all 11 verified mainnet circuits](docs/XLAYER-MAINNET.md)

New to the game? Read the complete [English player guide](docs/PLAYER-GUIDE.en.md) or [中文完整玩法指南](docs/PLAYER-GUIDE.zh-CN.md). Both start with a wallet-free route for players and continue with AI companions, circuit design, free lab tests, and optional X Layer tapeout.

Prefer to watch? The [complete English video guide](https://youtu.be/Pp3l9Mzx0sQ) (13:29) and [中文完整玩法视频](https://youtu.be/VyF5jggNrfE)（11:14）follow the same two paths, with matching narration and burned-in captions. Both are unlisted and available by link.

A browser roguelite built around playable TapeOut NAND/LATCH circuits on X Layer. One leader and up to three companions fight through twelve encounters across three regions. The leader can be human-controlled or assigned to an external AI agent; each companion seat can hold a tactical circuit chip, an external AI agent, or remain empty. The default human-plus-three-chip squad is free to play and needs no wallet.

Nandverse Arcade — Neon Reliquary was submitted to the TapeOut Genesis Transistor Hackathon on 2026-09-24. The [English competition demo](https://youtu.be/jwszzKPWcrI) shows the live game and on-chain chip verification. The accompanying videos cover [gameplay in English](https://youtu.be/5nsdvGTCElg) and [chip creation with 11 templates in English](https://youtu.be/_yW_HZ9HUjc); [Chinese competition demo](https://youtu.be/-xOcF6qaUAI), [Chinese gameplay](https://youtu.be/p7j430kNNXQ), and [Chinese chip guide](https://youtu.be/EBraOXO7ZwU) are also available. Each video pairs narration and captions in the same language.

## Play

Open the [live game](https://1-2-231.tapekit.org/) or download [Neon_Reliquary_v3.html](Neon_Reliquary_v3.html) and open it in a modern browser. Keep **Oath Expedition** selected, choose a class and difficulty, then deploy. The file bundles the game, visuals, audio, and its browser-side Ethereum library; normal play does not fetch a model or require a server. The live game's file bytes are stored on X Layer and served to browsers through TapeKit's gateway and Service Worker. English and Chinese are available in the game.

Move with WASD or the arrow keys, aim with the pointer, dodge with Space, use the skill with E and the ultimate with R. Press P for the squad panel and Esc to pause. On touch screens, use the on-screen joystick and ability buttons; landscape is recommended for combat.

The expedition contains clear, defend, escort, rescue, and boss objectives, route choices, camps, upgrades, six classes, and two relic sockets per member. Equipment is chosen before a run. Game state and scores are local browser data; they are not certified on-chain results.

## Circuit workshop and X Layer

In **Oath Workshop**, edit a tactical chip's priorities, skill requests, upgrades, and limited memory, or edit a relic's trigger circuit. Save a version, run the built-in fixed-scenario logic checks, and equip it. The circuit ABI uses only NAND and LATCH gates; its inputs, outputs, limits, and decoding rules are in [docs/CIRCUIT-ABI.md](docs/CIRCUIT-ABI.md). Local templates and tests are free.

The **TapeOut** panel features the [Nandverse Foundry processor and 11 manufactured circuits](docs/XLAYER-MAINNET.md). Select a featured chip and **Verify and import** to inspect its on-chain bytes and execution without a wallet. The panel can also connect an injected wallet on X Layer, quote the current processor/material/tapeout costs, mint missing NAND/LATCH material, tape out a saved circuit, and read the resulting circuit NFT back. Transactions require an explicit quote review and wallet confirmations. The game verifies processor registration, the original tapeout event, material link, netlist, ABI, and sample outputs before allowing a read-back circuit into the blueprint library. The shared material supply cap is 10,000,000 NAND/LATCH units, priced at 0.0005 OKB per minted unit.

The **Author Provenance** panel can package the original tapeout transaction, publisher address, exact netlist, ABI, and blueprint lineage. Participants can sign their own author, collaborator, commissioner, adaptation, or publisher declarations and export/import the package. Import rechecks signatures and on-chain data. This is evidence of publication and self-declarations, not a legal authorship finding or an automatic royalty payment.

## Optional external AI

Reserve the leader or companion seats for external AI in the squad panel. The public gameplay interface accepts periodic observations and tactical intentions while the browser runs movement, combat, and cooldowns. A human can take over the leader and revoke its agent credential. The seven-tool contract is described in [WEBMCP_INTEGRATION.md](WEBMCP_INTEGRATION.md), with example clients in [examples/](examples/).

For a local agent connection, run python3 tools/live_server.py and open http://127.0.0.1:8766/. This bridge listens on loopback and is optional. The repository contains no hosted model, model account, API key, or multiplayer backend.

## Build and verify

The checked-in HTML is built from src/ with Python's standard library. Node.js 18+ is needed for the automated JavaScript tests.

    python3 build.py
    npm ci --ignore-scripts
    npm test
    npm run test:legacy
    python3 tests/test_live_server.py

The browser file includes ethers 6.16.0; its third-party license is retained in src/vendor/ethers.LICENSE.md. The automated suite covers circuit compilation/evaluation, gameplay rules, mixed squads, input, manufacturing readback, author provenance, and the local bridge. Paid mainnet actions require separate wallet confirmation. The 11 published chips were manufactured and read back on X Layer mainnet; desktop and mobile browser emulation have been exercised on the live gateway. Physical iPhone/Safari and a public player's own paid mint/tapeout flow have not been verified here.

## 中文速览

打开[链上网页](https://1-2-231.tapekit.org/)或下载 Neon_Reliquary_v3.html，选择“誓约远征”即可免费游玩。默认是人类队长和三名战术芯片队友，无需钱包。队长也可交给外部 AI；三个队友席位可分别选芯片或外部 AI。工坊里可以一键选取 11 枚已流片的演示芯片，免费读回校验并装备，也可以编辑自己的芯片行动和圣物触发规则，先做免费逻辑试验，再按需连接 X Layer 钱包流片。对局成绩保存在本地，不等于链上认证成绩。初次游玩和深入制作芯片的步骤见[中文完整玩法指南](docs/PLAYER-GUIDE.zh-CN.md)。
