# Validation through v0.3.0

## v0.3.0 tactical AI

The full 29-test Python suite passed, including seven new tactical behavior tests and the fourteen-player protocol/ownership test. Tactical coverage includes divided firing/moving elements, gunner preference and rotation, directional cover, endpoint spacing, expiring observations, smoke fuse/inventory coordination, stress behavior and preserved human control.

Three all-AI 7v7 matches completed on AbbeyArden, Farm Fight (fmft) and StreetFight. Each used covering fire, movement, smoke and cover-seeking roles. Results and timing samples are in [ai-validation.json](ai-validation.json). The German side won these three selected seeds; this is not evidence of faction balance.

| Original map | Simulated seconds | Median step ms | p95 step ms | Maximum step ms | Smoke thrown |
| --- | ---: | ---: | ---: | ---: | ---: |
| AbbeyArden | 93.4 | 5.46 | 22.87 | 33.71 | 8 |
| fmft | 122.8 | 3.88 | 18.09 | 67.80 | 9 |
| StreetFight | 113.6 | 5.56 | 28.87 | 46.20 | 6 |

These are headless 0.2-second simulation steps on this computer, not rendering FPS. Fireteam decisions are staggered over 1.4 seconds. Local AI route checks stop after 768 visited nodes and try a bounded number of candidate destinations; player pathfinding retains its full search. Narrow passages and unusual layouts can still defeat local cover choices. The dense StreetFight sample exposed a 429 ms search burst before these bounds; its updated maximum was 46.2 ms in a separate run, not an identical-state replay.

Two actual native Creation clients also ran a 7v7 loopback battle with twelve AI fireteams for 45 seconds during this update. They received movement, combat and casualties without client exits or service errors. All 505 recovered original files still match their recovery hashes. Artwork, native executable, original maps and sound archives are unchanged.

The service remains authoritative for offline and direct play. A physical LAN/Internet route and fourteen full native renderers have not been tested together. The original engine's square-based collision and coarse HUD placement remain unchanged.

## Earlier validation through v0.2.0

Test machine: Windows x64, CPython 3.12, Frida 17.18.0. The portable client runs the original x86 Creation executable with this project's app-local WinG shim.

## v0.2.0 team expansion

The full 22-test suite passed. The fourteen-connection test was rerun after the final input-validation changes and passed again.

The portable launcher was opened, switched to seven fireteams per side, and used to launch an offline match. Its roster showed one human and six allied AI fireteams against seven enemy AI fireteams. The original battlefield rendered their movement and combat.

- All match sizes from 1v1 through 7v7 have unique soldier IDs and spawn squares. All 71 maps load with 56 soldiers and serialize a native snapshot for the seventh player slot.
- Fourteen simultaneous wire-level native/control connections completed the real framing and snapshot handshake. Tests covered full-room rejection, team choice, host-only start, frozen lobby time, order ownership, AI takeover and reconnecting without replacing or replenishing soldiers. These wire clients do not run the renderer.
- Two actual original Creation client processes joined a 7v7 match on loopback, leaving twelve AI fireteams. Both rendered the larger battle; native objective centering was exercised. The 150-second run consumed ammunition and produced casualties without service errors or unexpected client exits.
- Recovered MG/SMG caps, custom pool validation, slot-scoped retreat and AI destination distribution have regression coverage.
- A deterministic all-AI 7v7 match on AbbeyArden completed in 109.2 simulated seconds. Its simulation took about 2.1 wall-clock seconds on this machine (median step 2.0 ms, 95th percentile 9.2 ms, first-step maximum 173 ms). This is a headless simulation measurement, not a rendering FPS or Internet-latency benchmark.

## Earlier baseline checks

- Original native client started from the separate restoration fileset, negotiated the local service, opened its command strip and rendered the original map and soldiers.
- Manual native-window checks confirmed keyboard selection and right-click movement. The service received logical map coordinates, and soldiers reached the new location in the native renderer.
- A smoke grenade was thrown through the native input controls and rendered its recovered cloud frames after the fuse.
- The portable executable's launcher was opened and used to start an offline match; its bundled runtime successfully launched and drove the original client. Objective centering and grenade input were exercised in that packaged build.
- Two original client processes joined opposite sides of a direct-connect match on loopback. Their shared match ran combat, consumed ammunition, produced WIA/KIA, and completed with a winner. The service reported no errors during that test.
- The initial sixteen automated tests passed; the expanded suite adds six team/network tests. They cover fragmented native frames, malformed frame rejection, archived property clearing, all 71 map snapshots, pathfinding around blocked squares, corner line-of-sight blocking, windows, concealed enemies, command ownership, formation destinations, distance/stress accuracy, finite automatic reloads, grenade fuses, smoke visibility, WIA carrying, and AI match completion.
- Original recovered file manifest: 505 files, 260,787,033 bytes, excluding the newly added compatibility DLL. The original executable's SHA-256 remains unchanged.

## Limits of this evidence

Map data validation is not a full playthrough of every map. Only selected original maps and interactions received native-window inspection. Direct connection across two separate computers, router forwarding, and Internet conditions have not been tested. Legacy graphics/DirectSound compatibility may vary across Windows systems. The native client's remaining unused menus are not restored online-service features.

Gameplay tests establish the documented reconstructed behavior; they do not prove equivalence to the lost original server. In particular, exact aiming curves, historical side stockpile quantities and weapon balance, original injury odds, pixel-precise cover, campaign scoring, and corner-peeking logic remain unverified or unimplemented.
