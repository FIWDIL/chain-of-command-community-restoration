# Validation for v0.1.0

Test machine: Windows x64, CPython 3.12, Frida 17.18.0. The portable client runs the original x86 Creation executable with this project's app-local WinG shim.

## Completed

- Original native client started from the separate restoration fileset, negotiated the local service, opened its command strip and rendered the original map and soldiers.
- Manual native-window checks confirmed keyboard selection and right-click movement. The service received logical map coordinates, and soldiers reached the new location in the native renderer.
- A smoke grenade was thrown through the native input controls and rendered its recovered cloud frames after the fuse.
- Two original client processes joined opposite sides of a direct-connect match on loopback. Their shared match ran combat, consumed ammunition, produced WIA/KIA, and completed with a winner. The service reported no errors during that test.
- Sixteen automated tests passed. They cover fragmented native frames, malformed frame rejection, archived property clearing, all 71 map snapshots, pathfinding around blocked squares, corner line-of-sight blocking, windows, concealed enemies, command ownership, formation destinations, distance/stress accuracy, finite automatic reloads, grenade fuses, smoke visibility, WIA carrying, and AI match completion.
- Original recovered file manifest: 505 files, 260,787,033 bytes, excluding the newly added compatibility DLL. The original executable's SHA-256 remains unchanged.

## Limits of this evidence

Map data validation is not a full playthrough of every map. Only selected original maps and interactions received native-window inspection. Direct connection across two separate computers, router forwarding, and Internet conditions have not been tested. Legacy graphics/DirectSound compatibility may vary across Windows systems. The native client's remaining unused menus are not restored online-service features.

Gameplay tests establish the documented reconstructed behavior; they do not prove equivalence to the lost original server. In particular, exact aiming curves, historical weapon balance, original injury odds, pixel-precise cover, campaign scoring, and corner-peeking logic remain unverified or unimplemented.
