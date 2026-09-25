# Validation through v0.2.0

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
