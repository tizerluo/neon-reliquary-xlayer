# v3 delivery status

Completed: v2 mechanics preserved; six hero models refined; eight distinct boss anatomies; native 3D inspector; human + three independent companions; local rule bot preview; seven tool schemas; modern/legacy WebMCP feature detection; local API fallback; explicit host permission; token ownership, sequence/run checks and control leases; rescue and party defeat; per-wave difficulty locking; EN/ZH; integration client and documentation.

Verification: tests/test_results.json is the reproducible core suite; tests/ui_results.json covers actual desktop and simulated touch actions. Rendering screenshots use Chromium/Xvfb/SwiftShader with the same model geometry as the shipped game. Scripts enable the test guard only in an in-memory copy. Core suite uses manual simulation time; forced boss kills check state progression, not legitimate autonomous completion. No real external LLM was invoked.

Remaining deployment work: select an actual browser/Agent host, provide an authorized tool transport, plug in a real model decision function, and complete native WebMCP end-to-end verification. No network room server, API secrets, credentials or external calls added to the standalone game. No edits to the original/v2 files.

Future balance tuning: four-member tuning uses configurable formulas in coopScale(). Test with real player/Agent latency before making balance or device-framerate claims. Physical iPhone/Safari validation remains outstanding.
