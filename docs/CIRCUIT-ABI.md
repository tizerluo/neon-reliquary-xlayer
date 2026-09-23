# Oath Circuit ABI 1

The executable circuit is a flat TapeOut NAND/LATCH netlist. Byte encoding and evaluation are in `src/circuits.js`; no script or REF gate is accepted. Inputs occupy signals 2–21, constants are signals 0 and 1, and outputs are the last `nOut` signals. Integers in gate records are big-endian u24. RPC bit strings pack bit 0 into the least significant bit of the first byte.

NAND opcode `00` carries two signal IDs. LATCH opcode `01` carries its D signal ID; its output is the previous state, and its new state is sampled after all NANDs evaluate. State starts at zero for a new run and resets on death. It does not advance while paused, selecting a route, or resting in camp. The game evaluates at 5 Hz; physics remains 60 Hz. Each equipped instance has separate state.

## Inputs, in order

| Bit | Signal | Meaning |
|---|---|---|
|0|ally_down|Another party member is down|
|1|self_low|HP below 35%|
|2|self_recovered|HP at least 70%|
|3|boss|Living boss present|
|4|ally_low|Living member within 280 units below 60% HP, including self|
|5|skill_ready|Skill cooldown reached zero|
|6|ultimate_ready|Charge at least 99.9 and no active ultimate|
|7|danger|At least three nearby threats in the existing danger detector|
|8|blade_room|Fewer than 24 blades|
|9|objective|An active escort, beacon or rescue objective exists|
|10|objective_threat|Enemies within 120 units of objective|
|11|rescue_event|This member completed a revive channel or prisoner rescue|
|12|leader_assault|Human selected assault signal|
|13|leader_guard|Human selected guard signal|
|14|distant|More than 330 units from leader|
|15|alive|Not downed|
|16|relic_ready|This relic's cooldown is zero|
|17|effect_applied|This instance applied an effect on its previous decision step|
|18|boss_window|Expedition boss in its 7-second vulnerability period, every 24s|
|19|moving|Member was moving on the previous physics step|

The recovery-memory template retains retreat until 70% HP. Rescue memory arms after a real rescue, and clears only after a successful effect. Boss/camp revival never grants a rescue charge. The engine sends success acknowledgement on the next step and prevents a second activation while consuming it.

## Outputs

Outputs 0–15 must be a provably constant little-endian signature. The decoder performs partial constant evaluation including adversarial inputs and state; a nonconstant signature fails validation.

- Tactical signature `0x114f`, 28 outputs. Bits 16–22: guard, rescue, retreat, focus, assault, objective, follow (one-hot). Bits 23–25: skill, ultimate, dash requests. Bits 26–27: upgrade path (0 attack, 1 blades, 2 vitality; 3 invalid).
- Relic signature `0x124f`, 22 outputs. Bits 16–21: shield, heal, repulse, fury, frost, charge requests (one-hot).

At most 1024 gates and 4 state bits. Conflicting actions/effects fault the instance. All actions still obey physics, cooldowns, targeting, unlocks, arena bounds and resources. No output carries damage magnitude or arbitrary coordinates. Chips do not override another actor's control.

Every character has two relic sockets sharing 100 energy, initially 65, regenerating 2.2/s (−35% in Scarcity). Chassis define fixed cost/cooldown/effect; the circuit defines when to request it. An unsuccessful or locked effect consumes nothing. Equipment changes are locked for an active expedition.

## Manufacturing and provenance

X Layer 196, official factory `0x1f09daefa827f02cbb40967cc91b259763760761`. The adapter validates factory registration and the reciprocal processor/material link, metadata, typed ABI, then compares eight read-only `step` results against local execution. Imported provenance claims are not verification. Session verification is intentionally not trusted from shared files or persistent storage.

BLIF export preserves the circuit's meaning, including arbitrary compatible imported output layouts. The official canvas adds gates when re-importing; its final bill of materials can differ. The integrated manufacturing flow submits and quotes our exact final netlist.

Transactions require a connected wallet and explicit UI confirmations. Prices, fixed fees, inventory and supply are read before manufacture. Wallet and public RPC provenance/fees must agree. A pending transaction blocks additional sends until its receipt is resolved. Receipt events must come from the expected contract and author. After tapeout, bytes are read back and compared to the submitted netlist.

Author provenance certificates are a separate `nr-oath-provenance` v1 JSON package (`src/provenance.js`). The proof binds chain ID, registered processor/NFT address, circuit ID, original tapeout transaction and log index, block number/hash, event publisher, exact netlist and Keccak-256 hash, ABI 1 inputs and hash, optional source blueprint/hash, compiler/game versions, and a parent version ID plus its netlist hash when available. The current `ownerOf` is shown after readback but is never substituted for the original publisher or a signing author. A legacy circuit can be reconstructed with its original tapeout transaction hash; missing historical blueprint/parent metadata is left absent rather than invented.

Each author, coauthor, commissioner, adaptation author or publisher declaration is signed by that person's connected wallet using a domain-separated `personal_sign` message over the exact proof and work hash. A declared royalty recipient is signed metadata only; it does not enforce a payment rule. A commission or adaptation note is a declaration, not proof that all other parties authorized it; additional collaborators sign their own claims. The package preserves all distinct signatures when re-imported or rebuilt and rejects conflicting claims. New tapeouts save the chain proof immediately, then let the player sign and export; rejecting the signature leaves the publication proof recoverable for later signing.

Certificates are stored under `nr.oath.provenance.v1`, independently of the last-30 transaction journal and the limited blueprint library. Import verifies the package's hashes/signatures locally, re-reads the original transaction event and current netlist, and only then marks it verified for this browser session. Imported text or persistent storage alone never confers verified status. A certificate and signature establish a verifiable publication and self-declaration, not legal originality, copyright, guaranteed royalties, or certified local match scores.

The on-chain asset fixes circuit logic. Match state and physics execute locally, so local scores are not cryptographically certified or cheat-proof.
