# Neon Reliquary: The Complete Oath Expedition Guide

[Play now](https://1-2-231.tapekit.org/) · [中文版](PLAYER-GUIDE.zh-CN.md) · [X Layer processor and 11 manufactured circuits](XLAYER-MAINNET.md)

Lead a four-member squad through three regions held by a machine legion. Play the leader yourself, reserve a seat for a real external AI agent, or give companions tactical circuits that you design. Start with an action roguelite; if a teammate's choice makes you curious, open the workshop and find out why it happened. You can eventually manufacture your own immutable circuit on X Layer.

There are two paths through this guide. For a complete first-run loop, read through “Research and relics.” If you want to make circuits, continue with “Turn a rescue decision into a chip.” **Ordinary play, local editing, logic tests, and read-only imports of existing on-chain chips are free and require no wallet.** A wallet and OKB are needed only if you decide to manufacture a new version.

## Path one: play tonight

Open the [game](https://1-2-231.tapekit.org/), enter the citadel, choose a class and difficulty, keep **Oath Expedition** selected, and deploy. Initiate difficulty is a good place to learn the objectives. You do not need to clear all twelve encounters to understand the loop: finish one encounter and choose one camp gift.

The default squad is ready: you control the leader and three companions run free tactical chip templates. No circuit knowledge or AI connection is required. Companions follow rules about rescues, objectives, and bosses. The game handles ordinary movement, attacks, collision, and legal cooldowns; a chip chooses **what tactical intent to pursue**, rather than steering a character every frame.

### Choose a leader

| Class | Feel | Why try it |
| --- | --- | --- |
| Aurelian | Balanced warden; his breach knocks enemies aside and grants a shield | A forgiving first choice for movement and objectives |
| Mordred | Heavy cleavers, armor breaking and a burning lane | Cut straight through a front line |
| Volt | Quick electric blades with chain damage | Clear clusters while staying mobile |
| Nyx | Light, fast, dense microblade swarms | Trade durability for agility and sustained fire |
| Seraph | Life siphon and a skill that heals nearby allies | Keep the squad in the fight |
| Isolde | Slowing blades and a forward freeze | Control space in defense and escort objectives |

Weapons auto-attack nearby enemies. Your main jobs are movement, aiming, opening a lane, and dodging. Use WASD or arrow keys to move, hold the left mouse button to direct fire, Space to dash, E for your class skill, and R for charged overdrive. Cyan shards trigger a live upgrade choice on 1/2/3; the battle does not pause while you choose. P opens the squad and Esc pauses. On mobile web, use the left joystick and right-side abilities; landscape is best for combat.

Watch red attack warnings and the objective marker. Aim E at a thinner part of the formation, then dash through the opening. A dash briefly protects you, but a thick armored wall can still stop your escape.

### The expedition loop

Oath Expedition has three regions, each with three ordinary encounters and a boss: twelve encounters in all. Choose a route before each stretch; the fourth node in a region is always its boss. Your very first choice is between breaking a blockade and recovering the lost. After an encounter, take one gift for the whole squad at camp and choose the next route. Health, upgrades, and relic memory carry forward. Combat simulation pauses while you consider routes and camp gifts.

| Encounter | Success condition | The tactical question |
| --- | --- | --- |
| Break the blockade | Defeat 200 enemies **and** survive at least 100 seconds, within a 180-second limit | Can you keep moving after your kill count is high enough? |
| Hold the beacon | Attune near it for a cumulative 95 seconds | Do enough members stay close while enemies threaten its integrity? |
| Carry the last light | Escort the moving lantern to its destination | Is someone within range, and have you cleared enough enemies from its path? |
| Recover the lost | Channel at three seals, 25 seconds each | Can the squad stay near each seal and keep nearby threats below the interruption threshold? |
| Break the sovereign | Defeat the regional boss within the time limit | Can you save burst damage for its seven-second opening every 24 seconds? |

Read the objective progress, integrity, and boss-opening cues as carefully as the kill count. You can feel powerful in an escort yet fail because everyone has drifted away from the lantern. The combat HUD also lets you signal **guard** or **assault**; different chips react differently to objective pressure and leader signals.

Downed companions can be revived when surviving squad members stay close and channel a rescue. If everyone goes down, the expedition ends. At camp, downed members return and you choose one squad-wide gift: **Mending Oath** increases max health and heals, **Honed Steel** raises damage for this expedition, and **Shared Embers** restores relic energy. Think about the next route rather than automatically taking the same gift each time.

Live upgrades make another build layer. In Oath Expedition, attack gives +4% damage; blades add two swords until the 24-sword cap, then improve damage instead; vitality increases maximum health, heals immediately, and improves regeneration and movement. A chip can choose its companion's future upgrade direction too.

### Human, AI, and chips in one squad

Open **Oath Workshop → Squad** from the home screen. The leader can be human or external AI. Each of the three companion seats can use a tactical chip, reserve an external AI, or close. Every member has up to two relic sockets. Loadouts lock when a run begins, and you can name and save favorite squads for later runs.

A **tactical chip** is a repeatable NAND/LATCH circuit. It reads a bounded set of facts—“my HP is below 35%,” “an ally is down,” “the objective is threatened”—and chooses a tactic such as rescue, retreat, guard, or focus. It is not a language model and does not converse. Its advantage is steady, local response without a model round trip.

An **external AI** is an agent running outside the game. First reserve and enable a seat in the workshop; then your own agent host joins through the public tool interface. It periodically observes a compact view of the battle and sends an intention that lasts a short time. The browser keeps the action moving while the model thinks. You can take over an AI leader immediately or revoke external access; a disconnected companion falls back to explicit local defense.

For a first co-op setup, try **human leader + one external AI companion + two chips**. You still choose routes and camp gifts, the AI directs one teammate, and the circuits provide consistent support. If you have no agent host ready, leave the default three chips in place. **The website does not bundle a model service or multiplayer account:** reserving an AI seat alone will not spawn an AI. See the [agent contract](../WEBMCP_INTEGRATION.md) for WebMCP and the local loopback bridge. Agents cannot choose routes or camp rewards, start or pause a run, change HP, or award themselves a score.

### Research and relics: what carries into the next run

Each completed ordinary encounter earns 5 research points, each boss 15, and a full clear adds 20. A standard complete expedition earns **110**. Before deployment, you can accept one of two optional contracts. **Scarcity** cuts relic energy regeneration by 35%; **Hunted** increases enemy reinforcements by 30%. Either adds another 30% of your completed-encounter research, rounded down, making a complete clear **137**. A loss or an explicit abandon still settles completed encounters. These points live in this browser's local profile. They are not OKB, an on-chain token, or a certified leaderboard result.

Shielding, healing, and repulsion relic effects are available immediately. Spend **20 / 25 / 30** research to unlock Dawn Banner's speed boost, Winter Seal's freeze, and Star Conduit's overdrive charge. Use the research archive in the Squad tab. Unlocks add strategic choices rather than a permanent global damage multiplier. Advanced templates may be visible or equipped before unlock, but their combat effect remains inactive until its base effect is unlocked.

Each member's two relics share an energy pool of 100, start at 65, and normally regenerate 2.2 energy per second. Each effect also has its own cost and cooldown. For example, Mercy Lamp tries to shield a nearby wounded ally, while Breach Bell repels close threats. A failed or inapplicable effect does not drain energy. Relic energy is a **during-battle resource**, separate from between-run research points.

## Path two: turn a rescue decision into a chip

Imagine an ally has fallen while your chip-controlled companion drops below 35% health. Should it risk a rescue or retreat first? You can change the answer. This is the best first experiment in the workshop.

Open **Oath Workshop → Circuits & Relics** and select a tactic template, perhaps Oathkeeper or Survivor. Rules are checked top to bottom; **the first matching rule wins**, and an unmatched state falls back to guard. Oathkeeper puts rescue first; Survivor considers its own low health first. Swap “ally down → rescue” and “self below 35% → retreat,” name the version, and record what changed. You can also set conditions for skill, ultimate, and dash requests, plus an upgrade direction.

**Recovery memory** is a useful LATCH example. Once low HP sends the teammate into retreat, it keeps retreating until health reaches at least 70%. Without memory, a health value wobbling around 35% can repeatedly switch tactics. This state bit affects actual circuit output; it is not a decorative label.

Choose **Save as a new version** to add a local blueprint with a parent link. The original template stays intact. In **Circuit Lab**, put your version beside a baseline and run five fixed scenarios. Start with *Rescue under pressure*: when low health and a fallen ally coincide, do the versions make different first choices? Then inspect *Recovery memory* and *Boss opening*. The arrows in the table are logic steps, not a replay of a whole fight. **The lab proves what a circuit outputs for given inputs; it does not certify a win rate across random runs.** Equip the saved version from Squad, then play an encounter to judge the behavior yourself.

Relics are editable too. Pick a bounded chassis—shield, heal, repulse, and eventually the unlocked options—then set its trigger and optional “store after rescue” memory. The chassis fixes range, cost, and cooldown; the circuit decides when to request it. You are making a **budgeted trigger policy**, not an item with arbitrary damage values. Blueprints can be exported as share packages, BLIF, or netlists. Other players can import, try, and adapt them, but a local source claim by itself is not on-chain verification.

### Eleven manufactured starting points

The **TapeOut / X Layer** tab features four tactic chips—Oathkeeper, Survivor, Dawnbreaker, Sentinel—and seven relic chips—Mercy Lamp, Echo Lamp, Living Chalice, Breach Bell, Dawn Banner, Winter Seal, Star Conduit. All eleven have been manufactured on X Layer mainnet. Select one and choose **Verify and import · read only**. Without a wallet, the game reads the immutable netlist, checks its origin and sample execution, and adds it to your library. You can then equip it from Squad. Re-verify an equipped chain chip in each new browser session; a mutable local label is not enough proof of origin.

The satisfying loop is to equip a ready-made chip, notice one choice that surprises you in battle, change one rule, compare fixed inputs, and play again. Only then decide whether your version deserves a permanent on-chain edition.

### Decide whether to tape out your version

Local blueprints can be compiled, tested, shared, and equipped for free. Pay only when you want to manufacture one **immutable logic version** through TapeOut:

1. Save the final circuit in Circuits & Relics. Check its name, rules, parent, and NAND/LATCH gate counts.
2. Compare fixed lab scenarios and play it in a real encounter to make sure this is the behavior you want to preserve.
3. In TapeOut / X Layer, connect an X Layer-compatible wallet, select the saved version, and request a **fresh** material and fee quote.
4. Review missing NAND/LATCH material, the unit price, protocol and tapeout fees, and estimated gas. Nandverse Foundry material costs **0.0005 OKB per unit**. Your total also depends on gate count, material already held, and current network charges.
5. Only after accepting the displayed quote, confirm the required wallet transactions. Read the circuit back from chain, verify it, and equip it.

A manufactured netlist cannot be rewritten. Changing a rule means saving and, if desired, manufacturing a **new version**. Readback checks the registered processor, original tapeout event, material association, netlist, ABI, and execution samples. Real-time combat runs the verified bytes locally; **you do not make a transaction every frame**. An on-chain circuit publication does not make a local battle score cheat-proof.

The workshop also offers author-provenance packages with the original publication transaction, publisher wallet, exact netlist, blueprint lineage, and optional signed declarations. These help preserve evidence and context; a signature is not a legal judgment of originality or an automatic royalty.

## A free first-hour route

1. **First ten minutes:** Initiate difficulty, human leader, default three chips. Finish your first route, practice E to make space and Space to escape, and take a camp gift.
2. **Next run:** Try Seraph in a companion seat, or swap Oathkeeper and Survivor. Watch how rescue and retreat priorities affect defense or escort. If you have an agent host, give it one companion seat and leave two chips in support.
3. **First creation:** Change only the order of the low-health and ally-down rules. Run the five free logic scenarios, save and equip the result. Consider paid mainnet manufacturing only after you know you like its behavior.

The [mainnet manifest](XLAYER-MAINNET.md) lists the game site, processor, and all eleven chip transactions. Combat, ordinary saves, and scores currently live in the browser, so clearing browser data can remove progress; export blueprints and provenance packages you want to keep. Mobile web has touch controls, but the full paid tapeout path has not yet been publicly verified on a physical iPhone/Safari.
