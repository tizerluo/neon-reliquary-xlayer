# Nandverse Arcade on X Layer

Neon Reliquary is the first playable game using the Nandverse Foundry processor. The game can be [played in a browser](https://1-2-231.tapekit.org/) without a wallet. Creating and testing local circuit blueprints is free; a player pays only when choosing to manufacture an immutable version.

| Parameter | Mainnet value |
| --- | --- |
| Network | X Layer mainnet, chain ID 196 |
| TapeOut factory | `0x1f09daefa827f02cbb40967cc91b259763760761` |
| Processor, factory index 231 | `0x57E9e1111f42F448126A9F12b2b3f99a79dd1A44` |
| Material contract | `0x911d63D068C05e7741fD507517c3aC7793c35bE2` |
| Publisher wallet | `0xb5c09b3322e21d459570c9c882d56f5b0769559e` |
| Material symbol | NDVR |
| Shared NAND/LATCH supply cap | 10,000,000 material units |
| Material mint price | 0.0005 OKB per unit |
| Processor creation | [successful transaction](https://www.oklink.com/xlayer/tx/0x0621daf701b57d1dc1b258e3429bb4805c9b1872dc9c0cdf89d941b930fc309b) |
| TapeKit site | [1.2.231.tape](https://1-2-231.tapekit.org/) |
| Site file SHA-256 | `84f7e7fe34da45a40c85e093d6ccc3a19644b39d2d23a2bdfd89e42fc68a51ba` |
| Initial 30-day binding | [successful transaction](https://www.oklink.com/xlayer/tx/0xe4d4423c4a51f5963871be46b7c92f49c0f6ed9257b54c81ae27131a2ad0d7ba) |

The processor was created through the X Layer TapeOut factory. The 11 original `TapedOut` events below fix the netlists. Each circuit was read back from mainnet and compared with the local compiler and eight on-chain execution probes. The publisher wallet held all 11 circuit NFTs at verification time; ownership can change later.

| Circuit ID | Chip | NAND | LATCH | Netlist Keccak-256 | Original tapeout |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | Oathkeeper | 118 | 1 | `0xe64774909343d9f7b9928ee66630ac0adec49f715ae3868c0bd10dee959fb179` | [tx](https://www.oklink.com/xlayer/tx/0xcd302c64d542558edc4209bba74c4d9f0e8a546e65b43f3358d5a513c90113a2) |
| 2 | Survivor | 114 | 1 | `0x1d4ff987bd5538719200170cb4f31baeeee3e1ab9611c2e27b2ab6a6d2f85fe8` | [tx](https://www.oklink.com/xlayer/tx/0x7fdb0dbf5910b4e7ee4b2673e0e9f095719393c484187b6e45d165c72928af8a) |
| 3 | Dawnbreaker | 116 | 1 | `0x30bdceb42e01750c110169cd697c5467f71a4970f67d6cd72f051a410c3a56ba` | [tx](https://www.oklink.com/xlayer/tx/0x2220eb2e05040205669db68c77ae21334fb5d01bb9f980ce26ab5bd85a647bf8) |
| 4 | Sentinel | 113 | 1 | `0x8867b0034c38320c81c9e89ce1a86a3e9ae72d574f71f0f33904394f1120e193` | [tx](https://www.oklink.com/xlayer/tx/0x7d2adcc9e1f368ee266b49f56a10f2db1e7f547270034b9fb481a83b35e677ca) |
| 5 | Mercy Lamp | 50 | 0 | `0xe7817e016ecc710b8c7a2a68d10fdb24248eb2320155bb1d67d09e80a5200b02` | [tx](https://www.oklink.com/xlayer/tx/0x6b4aeab089ace8539db23364d9d7da91b411b97a63d4c38176dcd953a979943a) |
| 6 | Echo Lamp | 58 | 1 | `0x53a924b524ef38259e3ed3431bcec1175bdfe5d6507421b2df5f9e5ec74b4d8f` | [tx](https://www.oklink.com/xlayer/tx/0xd41b597dffa463e1f726637cbf107f7a814d29d11117064eeba41ec57897a1e4) |
| 7 | Living Chalice | 50 | 0 | `0x6d908bcafd0152fc0f1f40b16a2a556a8c5121f2db9996f8cbb81d08c68127f3` | [tx](https://www.oklink.com/xlayer/tx/0x0cd705e0d7309a71dee2668da8a9ef9b07cf7b564bdcd8915428d13860b53fb9) |
| 8 | Breach Bell | 50 | 0 | `0xfbaf721877dc415132662994506cc59a4e1322686ce76dec2de6d350687a0693` | [tx](https://www.oklink.com/xlayer/tx/0xa8f2100f26b302fbc95e75aa2f5460f75d6a15762dc2fcc7d97368aefb6f2896) |
| 9 | Dawn Banner | 50 | 0 | `0xccdaa61d600240412df955aa6ec4c0799385a88055d8b33c029bedbd3d4d5d44` | [tx](https://www.oklink.com/xlayer/tx/0xf7987ed385c1c1f5e2d37682cab27dff093818f9cc022b204867463991442afe) |
| 10 | Winter Seal | 50 | 0 | `0xfa098638f4b83d54b0f443e72dfddcaf434b3a949dfbe30ba9aa3987adfe21c5` | [tx](https://www.oklink.com/xlayer/tx/0x3b5a5a61732283918a14d301d2452c0f22f6547c31ba3cc991cbe2a0f1ecdd95) |
| 11 | Star Conduit | 50 | 0 | `0xc0a0c49659f3f6243739e05318caf4027f92a0b83ea62f8693469935b1019f24` | [tx](https://www.oklink.com/xlayer/tx/0x8d23b17ecf36f3e1c926a3732e52c0fcdffe546914c4bebba878a5613896d265) |

The browser workshop starts with this processor and chip #1 selected. Pick any of the 11 featured chips in **Oath Workshop → TapeOut / X Layer**, then select **Verify and import** to reproduce the on-chain check without a wallet. The imported circuit can be equipped from the Squad tab. A different processor address and circuit ID can also be entered for compatible circuits.

The site HTML and its bundled JavaScript, styles, visuals and audio are stored as `index.html` in the X Layer SiteRegistry container owned by circuit #1. Its 931,833 bytes were read back from mainnet and matched to the SHA-256 above. TapeKit's HTTPS gateway and Service Worker provide ordinary-browser access; the game file itself is on X Layer. The name binding is paid in 30-day periods and must be renewed for the gateway URL to remain live. Real-time combat, local saves and scores execute in the browser; they are not certified on-chain results. Author provenance packages preserve the original publication event and optional signed declarations, not automatic royalties.
