# Feature provenance audit

Audited September 25, 2026, against the current working tree, including uncommitted work. This is a partial reimplementation built around a recovered client. Substantial gameplay and service behavior has been newly written. Describing it as only offline play and a few missing pieces understates the work and the departures from the original.

This audit describes provenance, not whether a feature works well. Updated September 26 after the recovered-data alignment pass: requested restoration of an original function is now distinguished from a deliberate departure. The earlier mutually exclusive use of “requested change” obscured that distinction. Passing tests does not establish historical accuracy.

“Approximation” usually describes the replacement implementation or an unknown formula, not an invented feature concept. These counts are neither a percentage of original files nor a measure of how much of the historical game is missing.

## What the classifications mean

| Classification | Meaning |
| --- | --- |
| **Original** | Preserved material from the recovered installation. This does not establish that it was present in the first commercial release: the recovered collection includes community-era material. |
| **Verified reconstruction** | Newly written code reproduces a specific recovered field, structure or client interface. Verification applies only to the stated detail, not the whole surrounding system. |
| **Approximation** | Newly written behavior, substitution or addition whose equivalence to the original has not been established. This includes new implementation choices; it does not mean all such choices came from historical sources. |
| **Requested change** | An explicit intentional departure or new convenience requested in this conversation. A request to bring back a documented original function is classified by its original evidence instead; request origin is noted separately. |

Mixed features are split into separate rows. The broad request to restore everything does not make every subsequent design choice a specifically requested change.

## Evidence and scope

- All **505 files** under `game/` matched the SHA-256 values in [the preservation manifest](../original-manifest.json) during this audit. There are **71 map layouts**. Preserved bytes do not mean unchanged runtime behavior.
- Primary evidence is the decoded `game/cocSc.ODF`, decoded map/scenario OIX files, and the code linked below. [The audit evidence file](feature-audit-evidence.json) records selected recovered fields, missing-art references and hash-check results.
- The model hash is `7cd25a3ce58d4224789d33fab92766cac9650932daecd7ca6b6ae86c940a0900`. The client hash is `bf817ef80d98872ffe117b9d7d11a79b4238ea616bd9a9a828a97c8db91d5ccd`.
- User-request evidence comes from this conversation. The supplied debrief screenshot establishes visible presentation, not combat or promotion formulas. The subsequent [media review](RESTORATION_SOURCES.md) records inspected screenshots and sampled video frames. Historical references can verify visible functions without verifying their implementation details.
- Existing native checks establish client compatibility for tested operations. They do not verify lost server behavior. This audit does not claim every map, camera rotation, networking environment or animation has been fully validated.

## Recovered material and engine integration

| Feature | Classification | Evidence and limits |
| --- | --- | --- |
| Creation executable and recovered support files | Original | Manifest match; the executable is reused, not recreated. Runtime hooks change some behavior. |
| Map layouts, terrain art and scenario records | Original | Recovered OIX and graphics files. Runtime terrain interpretation and mission rules are separate below. |
| Soldier, casualty, weapon, pip and command-button artwork | Original | Recovered ODF image/clip references and graphics. Reusing an image does not verify when or how it should appear. |
| Weapon and grenade sound recordings | Original | Recovered sound objects/files. Playback behavior is separate below. |
| Debrief artwork, rank names and promotion UI definitions | Original | `EndGameScoring`, rank objects and promotion fields survive. Their presence does not restore progression. |
| ODF decoding and OIX decoding/parsing | Verified reconstruction | [formats.py](../restoration/formats.py) reads the recovered schemas and records; scope is file-format compatibility. |
| Creation TCP framing and object/property encoding | Verified reconstruction | [protocol.py](../restoration/protocol.py), [assets.py](../restoration/assets.py), [server.py](../restoration/server.py); compatible with the recovered client in existing native checks. Not a reconstruction of the original online service. |
| Replacement server, JSON control connection and input bridge | Approximation | [server.py](../restoration/server.py), [client.py](../restoration/client.py), [bridge.js](../restoration/bridge.js). New architecture replacing missing functionality, including the absent game-specific client module. |
| App-local WinG replacement | Approximation | [wing32.c](../compat/wing32.c) maps four imports to Windows GDI. A new compatibility component, not a recovered WinG DLL or complete WinG implementation. |
| Disabling legacy browser launches and validating the executable before hooks | Approximation | New runtime compatibility measures in `bridge.js` and `client.py`; not original game features. |
| Bounded network writers, caching and staggered simulation work | Approximation | New engineering choices in `server.py`, `simulation.py` and `tactics.py`; no historical implementation claim. |

## Match rules and combat

The detailed implementation values are in [Technical rules](TECHNICAL_RULES.md). Unless a row below identifies a recovered value, those values are unverified.

| Feature | Classification | Evidence and limits |
| --- | --- | --- |
| Four soldiers per player's fireteam | Verified reconstruction | Recovered rank loadouts enumerate soldiers 1–4 for both sides. This does not verify every command/ownership rule. |
| USA/Germany weapon identities and base rifles | Verified reconstruction | Recovered weapon objects and rank loadouts support Garand/Mauser and faction-specific special weapons. |
| One MG and two SMGs maximum per fireteam | Verified reconstruction | `INIT_LimitPerSquad` is 1 for BAR/MG42 and 2 for Thompson/MP40. Mapping “Squad” to the four-soldier group remains an interpretation; it does not establish side stockpiles. |
| Five-square maximum grenade throw | Verified reconstruction | `Model.INITMaxGranadeDistance = 5`; `Game.command` uses five. Does not verify distance geometry or trajectory. |
| Reading scenario starting-point coordinates | Verified reconstruction | `Game.__init__` reads `startingpoint`, `Start_X` and `Start_Y` from recovered scenario records. |
| Deploying extra soldiers around spawns; fallback spawns | Approximation | New connected-cell placement and fallback coordinates in [simulation.py](../restoration/simulation.py). |
| One to seven fireteams per side | Approximation | `roster.MAX_SLOTS = 7` is a current implementation limit. The audited local evidence does not establish this as a universal original limit. |
| Symmetric side stockpile defaults and automatic distribution | Approximation | [roster.py](../restoration/roster.py) explicitly invents default quantities and distribution. Recovered stockpile field names do not establish the formula. |
| Adjustable offline team sizes and weapon pools | Requested change | Explicitly requested for Offline vs CPU; default quantities and distribution remain approximations. |
| Removal of objective-capture victory requirements | Requested change | Explicit request to remove capture requirement. This is a deliberate gameplay departure, not a recovered rule. |
| Rally point and CPU movement toward it | Approximation | First objective or midpoint is selected and relocated to an open cell. The `RALLY POINT` label and use are new choices. |
| Elimination as a mission-ending condition | Verified reconstruction | Gallery screenshot 14 explicitly shows annihilation ending a mission. Current “no active soldiers” interpretation and all scoring details are not thereby verified. |
| Elimination-only rules and 15-minute draw | Approximation | Current `Game.step` ends on no active opposing soldiers or 900 seconds. Original objective/scoring alternatives remain omitted by request or incomplete. |
| Eight-neighbor A* paths, diagonal restrictions and formation offsets | Approximation | New routing and group-destination algorithms in `Game.path` and `Game.command`. |
| Walk/run/assault/crawl speeds and movement restrictions | Approximation | New numeric speeds; only assault permits shooting while moving. Recovered command names do not establish these exact rules. |
| Terrain collision, doors, windows, low cover and trees | Approximation | Grid classification uses terrain tags and image-name heuristics. Not recovered wall-edge, window or collision code. |
| Visibility distance, stance concealment and shared side vision | Approximation | New detection ranges and line tests; hidden enemies are removed from each client's world. Original client line-of-sight behavior is disabled in the generated model. |
| Weapon ammunition limits | Verified reconstruction | Reads `AmmoMax$weapon`: rifles 70, SMGs 200, MGs 900. Used as total carried ammunition; that semantic interpretation is recorded. |
| Weapon magazine/reserve split, ranges, reloads and shot intervals | Approximation | These parts of the `WEAPONS` model remain newly chosen. Real-world specifications do not prove game balance. |
| Accuracy, cover modifiers, damage and target selection | Approximation | New probability formulas and nearest-target behavior; original server formulas are missing. |
| Health, WIA/KIA probabilities, stress and stun | Approximation | 100 health, 45% initial KIA chance and other effects are new simulation choices. Recovered casualty graphics do not verify them. |
| Carrying wounded soldiers | Approximation | Recovered command/art support the concept; two-square pickup, 60% speed, firing restrictions and drop behavior are reconstructed choices. |
| Grenade inventory and blast distance | Verified reconstruction | Now reads five grenades from faction UnitTile objects and distance two from `Model.GranadeHitDistance`. Interpretation as inventory/radial cutoff is explicit. |
| Grenade fuse, falloff, damage and window failures | Approximation | Five-second fuse, linear falloff, friendly damage and failed-throw rules remain unverified original formulas. |
| Smoke inventory, duration, radius and sight blocking | Approximation | One smoke grenade, 30 seconds and 2.5-square blocking radius are new rules. |
| Retreat | Approximation | Recovered button supports the concept; immediate withdrawal of selected owned soldiers and its result handling are new rules. |
| Randomly assigning which soldier represents the player | Approximation | `Game.player_identity` randomly chooses one per fireteam. The original debrief concept does not verify this selection method. |
| Offline CPU opponents and vacant-team control | Approximation | New playable mode/controller; current controls were explicitly requested, but original AI implementation was not recovered. |
| CPU cover seeking, bounding, smoke, memory and role selection | Approximation | Entirely new heuristics in [tactics.py](../restoration/tactics.py), including 12-second memory. Not original behavior code. |

## Controls, graphics and presentation

| Feature | Classification | Evidence and limits |
| --- | --- | --- |
| Reusing recovered command-button idle/pressed images | Verified reconstruction | ODF `ImageIdle` and `ImagePressed` references drive the feedback. Exact click duration and selection behavior are new. |
| Click/drag selection, right-click orders, right-drag facing and cancel behavior | Approximation | New input interpretation in `MatchServer.handle/choose`. Original button labels alone cannot verify the complete interaction model. |
| Supplemental Orders menu | Approximation | New native menu in `bridge.js`; exposes commands without reconstructing all original dialogs. |
| Removing gameplay hotkeys and shortcut labels | Requested change | Explicit request. The restoration's previous bindings were additions; this audit does not establish that the historical game had no hotkeys. Text entry still uses keys. |
| Bottom command UI and visible scrollbars | Verified reconstruction | Requested restoration; archived screenshots and recordings show bottom command rows and both scrollbars. Runtime layout code is new. |
| Resizable window | Requested change | Retained explicit request; original resize behavior was not established by sampled images. |
| Pressed-in feedback when clicking commands | Verified reconstruction | Requested restoration of original feedback: recovered `ImagePressed` references support it. New timing logic remains unverified. |
| Disabling mouse-wheel scrolling | Requested change | Explicit request; message filtering in `bridge.js`. |
| Center and camera-rotation controls | Approximation | Recovered controls/properties reused with new server dispatch. Full rotation behavior is not established by this audit. |
| Movement animation repair | Verified reconstruction | Requested restoration of existing directional clips, now using recovered UnitMaster assignments. Frame scheduling remains approximate as described separately. |
| Advancing animation from server time at 10/8/6 frames per second | Approximation | `Assets.build_motion_frames/unit_image`; new workaround and timing, not recovered animation scheduling. State-to-clip choices in `Game.image` are also reconstructed. |
| Correcting soldiers appearing beneath terrain | Requested change | Integer/fractional position updates and runtime unit depth changes. No claim of perfect occlusion on every map. |
| Yellow pips over owned soldiers | Verified reconstruction | Requested restoration: recovered pip art and gallery screenshots show this visual function. Exact offsets and eligibility edge cases remain reconstructed. |
| Multiplayer overhead names | Verified reconstruction | Requested restoration: names are visible in original screenshots and recordings. Current centering and eligibility rules use new code. |
| Hide own/dead/retreated overhead names | Requested change | Explicit filtering request; WIA remains eligible. Samples do not establish every original eligibility rule. |
| Filled red destination squares with centered soldier pips | Verified reconstruction | Requested restoration: CoC Central screenshot 5 directly shows filled ground diamonds and centered pips. Recordings show destination feedback. New polygon drawing, flash cadence and depth implementation are not recovered code. |
| Missing map-image replacements | Approximation | `icor → iwcr`, `qcor → wcor`, `wh09 → wh01`. All three missing names occur in each of `hse`, `nagrsch`, `pst`, `rts`, in `Image1` fields. Existing art is substituted; intended appearance is unknown. |
| Grenade explosion image | Verified reconstruction | Now uses `ImageShop.GranadeExplosion$art` (`grex`). The recovered `exp2` cloud is retained alongside it based on visible reference clouds; composition/lifetime remain approximate. |
| Unit stance/throw/carry image assignments | Verified reconstruction | Reads UnitMaster references, including German static crouch, prone throw and stationary carry. Transition timing and injury/death variants remain incomplete. |
| Smoke graphics | Approximation | Middle frames of recovered `exp2` explosion are reused as smoke. Not recovered smoke-specific artwork. |
| Sound playback triggers and mixing | Approximation | Recovered files played by new event handling/`winsound`; original timing and mixing are not restored. |
| Modified mission-end screen | Approximation | Original artwork reused, new outcome/casualty text and dashes for unavailable scores; promotion controls hidden and dimensions changed. It is not a complete replica of image 2. |
| Live timer/ammunition text and notices | Approximation | New text produced by `Game.status` and server notices. |
| Removing 2AM titles/icons; community icon; removing displayed versioning | Requested change | Explicit requests, applied to presentation/package. Preserved original bytes and attribution are separate. |

## Launcher, multiplayer and distribution

| Feature | Classification | Evidence and limits |
| --- | --- | --- |
| Compact launcher and mode-dependent controls | Requested change | Explicit requests; new Tk UI in [launch.py](../launch.py), not recovered launcher code. |
| Offline vs CPU name; hide IP/multiplayer fields offline | Requested change | Explicit requests. |
| Open/join/close/leave lobby and Start match buttons | Requested change | Explicit button names and mode visibility requested. |
| Display host IP and game/lobby ports | Requested change | Explicit request; new lobby presentation. |
| Lobby team hierarchy display and side changes | Requested change | Explicit requests; the new service supplies the displayed data. |
| Host start authority, guest ready state and 45-second launch timeout | Approximation | New coordination rules in `server.py`; not a recovered original workflow. |
| Password, ownership token, direct connection and control protocol | Approximation | New service/authentication design; TCP 1850/1851 setup is not a restoration of accounts or matchmaking. |
| CPU takeover, reconnecting to existing soldiers and ownership enforcement | Approximation | New session rules; preservation of equipment/health is a current implementation policy. |
| Assignable commander tree | Approximation | Original commander fields/warnings and visible Set Commander controls support the original concept; this is not a wholly new feature. Host-only pre-match editing, default slot-zero leadership and permission rules are new choices. |
| Individual equipment assignment and commander branch permissions | Approximation | Original weapon-assignment controls/fields and the in-match window at 3:07 in `l0kDpa43yJA` verify the original concept; current pre-match-only behavior is incomplete. Replacement dialogs and exact authority rules are not verified. Recovered numerical caps are classified separately. |
| In-game message box | Verified reconstruction | Requested restoration of the original chat pane visible in screenshots/recordings. Transport, audiences and layout details remain new. |
| Simple launcher lobby message box | Requested change | Requested convenience in the replacement launcher. |
| Room/team/private chat, ignore and restricted history | Approximation | Gallery image 7 and recording `l0kDpa43yJA` verify original chat, whisper and ignore concepts. Current audiences, 240-character limit, rate limit and history handling are new implementation rules. |
| Return to lobby, retain connections/settings and change map between rounds | Approximation | New continuity workflow in [room.py](../restoration/room.py); not verified original behavior. |
| Local match-history file and viewer | Approximation | New feature in `RoomFeatures.record_result` and launcher; not original account or promotion records. |
| CoC Restored+ executable with community icon | Requested change | Explicit request; PyInstaller distribution, not a replacement for the preserved Creation executable inside `game/`. |
| Removing the `original/` folder from the player fileset | Requested change | Files moved under `game/`; they were not discarded. Source variable names and manifest filename may still say “original.” |
| Simpler documents and README missing-files section | Requested change | Explicit requests. Missing-data requests do not verify the approximations already implemented. |
| Build scripts, automated tests, hashes and packaging manifests | Approximation | New project infrastructure. Useful implementation checks, not evidence of original gameplay equivalence. |

## Corrected discrepancies and remaining uncertainty

The alignment pass now reads grenade inventory, throw range, blast distance, ammunition limits and grenade-effect references from the preserved ODF. German crouching, prone throws and stationary carrying use recovered UnitMaster image references. The retreat-label case mismatch is fixed.

| Recovered field | Current use | What is still uncertain |
| --- | --- | --- |
| `ArmamentGranade = 5` | Five fragmentation grenades per soldier | Whether scenarios or service rules altered the initial inventory. |
| `GranadeHitDistance = 2` | Two-square cutoff with zero effect at the boundary | Original geometry, damage distribution and stun formula. |
| `INITMaxGranadeDistance = 5` | Five-square throw limit read from data | Original trajectory and collision behavior. |
| `AmmoMax$weapon` | 70 rifle / 200 SMG / 900 MG total carried rounds | Exact original total/reserve/cap semantics; current magazines/reloads remain approximate. |
| `GranadeExplosion$art` | Recovered `grex` grenade image | Complete timing and effect lifecycle. |
| UnitMaster image fields | Recovered state-specific references | Full transitions, aiming, injury locations and death-variant selection. |

See [extracted recovered values](recovered-gameplay-values.json). The earlier audit evidence JSON preserves the raw evidence from the initial audit; the current code and this updated table describe the corrections.

## Not restored

Missing original server code and `zamCocSc_client.dll` remain missing. Original account authentication, public matchmaking, persistent ranks, promotion-point calculation/distribution, regiment progression, complete mission objectives/configuration, original commander eligibility/succession and exact combat/visibility/animation timing are not restored. Some related artwork and schema fields survive; that is evidence of their existence, not a working implementation.

The highest-value next fidelity work is to interpret the recovered fields above and compare representative scenarios against primary evidence. New behavior should stay labeled as an approximation until that comparison supports a narrower verified claim.


## Capture update — September 27, 2026

The capture point occupies one square and starts neutral. An active soldier must occupy that square for 120 seconds to capture it. Multiple friendly soldiers do not speed this up. Both sides on the square pause the timer; leaving resets progress. The owner keeps control until the other side completes a full capture. Ownership uses the recovered USA/Germany floor symbols and flag sprites. Capturing does not end the match or award reconstructed victory points. The 120-second rule and contest/reset behavior are requested/reconstructed behavior, not verified original timing.
