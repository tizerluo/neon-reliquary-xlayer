# Neon Reliquary — Oath Expedition

A browser roguelite built around playable TapeOut NAND/LATCH circuits on X Layer. One leader and up to three companions fight through twelve encounters across three regions. The leader can be human-controlled or assigned to an external AI agent; each companion seat can hold a tactical circuit chip, an external AI agent, or remain empty. The default human-plus-three-chip squad is free to play and needs no wallet.

## Play

Open [Neon_Reliquary_v3.html](Neon_Reliquary_v3.html) in a modern browser, keep **Oath Expedition** selected, choose a class and difficulty, then deploy. The file bundles the game, visuals, audio, and its browser-side Ethereum library; normal play does not fetch a model or require a server. English and Chinese are available in the game.

Move with WASD or the arrow keys, aim with the pointer, dodge with Space, use the skill with E and the ultimate with R. Press P for the squad panel and Esc to pause. On touch screens, use the on-screen joystick and ability buttons; landscape is recommended for combat.

The expedition contains clear, defend, escort, rescue, and boss objectives, route choices, camps, upgrades, six classes, and two relic sockets per member. Equipment is chosen before a run. Game state and scores are local browser data; they are not certified on-chain results.

## Circuit workshop and X Layer

In **Oath Workshop**, edit a tactical chip's priorities, skill requests, upgrades, and limited memory, or edit a relic's trigger circuit. Save a version, run the built-in fixed-scenario logic checks, and equip it. The circuit ABI uses only NAND and LATCH gates; its inputs, outputs, limits, and decoding rules are in [docs/CIRCUIT-ABI.md](docs/CIRCUIT-ABI.md). Local templates and tests are free.

The **TapeOut** panel can connect an injected wallet on X Layer, quote the current processor/material/tapeout costs, mint missing NAND/LATCH material, tape out a saved circuit, and read the resulting circuit NFT back. Transactions require an explicit quote review and wallet confirmations. The game verifies the processor registration, original tapeout event, material link, netlist, ABI, and sample outputs before allowing a read-back circuit into the blueprint library. There is no project-owned processor or game circuit deployment implied by this repository.

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

The browser file includes ethers 6.16.0; its third-party license is retained in src/vendor/ethers.LICENSE.md. The automated suite covers circuit compilation/evaluation, gameplay rules, mixed squads, input, manufacturing readback, author provenance, and the local bridge. Paid mainnet actions require separate wallet confirmation. Desktop and mobile browser emulation have been exercised; physical iPhone/Safari and paid mainnet writes are not represented as verified here.

## 中文速览

直接打开 Neon_Reliquary_v3.html，选择“誓约远征”即可免费游玩。默认是人类队长和三名战术芯片队友，无需钱包。队长也可交给外部 AI；三个队友席位可分别选芯片或外部 AI。工坊里编辑芯片行动和圣物触发规则，先做免费逻辑试验，再按需连接 X Layer 钱包流片。对局成绩保存在本地，不等于链上认证成绩。
