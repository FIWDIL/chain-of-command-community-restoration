# Chain of Command — original-engine community restoration

Free experimental restoration of the recovered 2AM Chain of Command client. This runs the **original `creation.exe` 1.50.0.621**, original graphics archives, and recovered maps. It is a separate project from Combat on Contact.

The original online service and `zamCocSc_client.dll` were not recovered. A new local match service supplies their missing gameplay and input behavior. Offline play still uses that service on your own computer; it needs no Internet connection or 2AM account. This is not a claim to have recovered the original server source or its exact rules.

## Download and play

Download the Windows ZIP from [Releases](https://github.com/Huckleberry87/chain-of-command-community/releases). Extract the whole ZIP, then run **ChainOfCommand.exe**. Keep the `original` and `_internal` folders beside it. Windows 10/11 x64 is the target; the preserved game executable itself is 32-bit.

Choose **Offline vs AI**, pick an original map, and start. You command four American soldiers against four German AI soldiers. The fourth soldier can carry the automatic weapon or an SMG. The original battlefield opens in its own window; the launcher remains available for match status and extra commands.

Capture the control point for 90 uncontested seconds, or incapacitate the opposing team. Press **O** to find the objective and **Space** to return to your selected soldiers. The first recovered scenario's spawn locations and first victory point are used. Maps without those records receive documented fallback positions.

## Direct connection

One player chooses **Host direct connection**. The other chooses **Join host**, enters the host's IPv4 address, and uses the same room password. The host plays USA and the joining player plays Germany. Both must finish loading before the match runs. A disconnected player pauses the match and may rejoin the vacant side.

The host listens on **TCP 1850 and TCP 1851**. Allow both ports through the host's firewall for the network you use. Across the Internet, the router must forward both TCP ports to the host; a VPN providing a reachable private IPv4 address is another option. There is no matchmaking, relay, automatic router setup, or public master server.

1850 carries the recovered Creation protocol; 1851 carries the restoration's command/session protocol. Passwords and traffic are not encrypted. Use a room-only password and connect to people you trust. The local offline service binds to loopback only. Actual native-client direct play has been tested between two processes on one PC; a separate-machine or Internet test is still needed.

## Controls

Left-click a friendly soldier, or select with **1–4**. **A** selects all four. Shift-click adds a soldier. Dragging selects a group, although this build does not yet draw a selection rectangle. Right-click gives the current order. A right-button drag gives a facing order. Escape cancels grenade, smoke, fire-target, or facing mode.

The recovered command strip works for its movement, shooting, facing, stance, grenade, and centering buttons. Its upper order row addresses everyone; each lower row addresses one soldier. Campaign promotion and commander/weapon assignment panels are hidden because their original service is unavailable. Choose the support weapon in the launcher before starting.

| Key | Order |
| --- | --- |
| W / R | Walk / run to the next right-click |
| X / C | Assault / crawl to the next right-click |
| H | Stop |
| Z / V / P | Stand / crouch / prone |
| G / T | Fragmentation / smoke grenade at the next right-click |
| F | Face the next right-click |
| S / E | Hold fire / fire at will |
| B | Carry a nearby friendly WIA soldier, or put them down |
| Space / O | Center selected soldiers / objective |

The launcher also exposes these orders. Fire at a specific visible enemy using its **Fire at** button or the native command strip. Orders preserve the selected soldiers' relative destination spacing, although pathfinding can split the group around an obstacle. Walking, running, and crawling suppress firing while moving; assault allows it with an accuracy penalty. Reloading happens automatically when the weapon is empty.

## What is preserved

- Original native rendering engine and isometric projection; `creation.exe` remains byte-for-byte unchanged.
- Original map files, graphics archives, soldier animation frames, and sound files.
- Original command-strip artwork and core row-based ordering.
- 71 indexed original map layouts. All pass data-loading checks; most have not received a visual playthrough.

The portable package adds a small, open-source WinG-to-GDI compatibility DLL beside the copied game. It does not install files in Windows or require an administrator account. A version-checked Frida bridge supplies input routing inside this one launched process; it never attaches to Combat on Contact or another running game.

## Reconstructed behavior and current limits

This first release supports a complete four-versus-four skirmish loop, offline enemy AI, direct connection, limited ammunition, automatic reloads, stress, stance effects, tile-based cover/visibility, fragmentation and smoke grenades, WIA/KIA, carrying, and match results. One hidden soldier identity is revealed after the battle.

These rules are **reconstructed defaults**, not verified original formulas. Collision treats recovered terrain as occupied squares rather than reproducing the lost server's wall-edge geometry. Smoke reuses recovered explosion-cloud frames. The AI and weapon balance need playtesting. Native menus unrelated to the restored skirmish may remain inert. There is no saved match, persistent rank/company system, original lobby, campaign, larger team mode, or exact corner-peeking/body-part simulation in this release. HUD labels retain some of the original engine's coarse positioning.

See [mechanics](docs/MECHANICS.md), [protocol and compatibility notes](docs/RESTORATION.md), and [validation](docs/VALIDATION.md). Report a problem with the map name, mode, and steps that produced it.

## Source and building

The repository contains the new service, bridge, launcher, compatibility source, and tests. The larger original data files are in the release ZIP rather than Git history. Copy the release's `original` directory into a source checkout to run from source.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python launch.py
.venv\Scripts\python -m unittest discover -s tests -v
```

To build a portable package, install `pyinstaller==6.19.0` in that environment and run `tools/build_release.py --output <release-directory> --work <build-directory>`. `compat/wing32.dll` is reproducible using `tools/build_wing.py --llvm <LLVM-bin-directory>`; its source needs no Windows SDK headers.

The MIT license applies only to the newly written restoration code. Original game files remain separately copyrighted and are included for free distribution under the project owner's asserted rights. See [third-party notices](THIRD_PARTY_NOTICES.md). This is a community restoration, not an official 2AM service.
