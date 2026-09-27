# Original assets: changed and kept

September 27, 2026. Original files stay unchanged. This pass reconnects suitable recovered assets to offline and direct-connect play. It does not claim that the missing client module, online service or every original rule has been recovered.

## Changed to use original assets

| Area | Change |
| --- | --- |
| Soldier movement and posture | Added recovered stance transitions, falling/getting up, prone-to-run and idle/rest animations. Animated frames advance on the server clock, including clips beyond the previous eight movement loops. |
| Cover | Added left/right cover poses, peeking, aiming, firing, ducking, prone cover and barrel-cover presentation. These use existing terrain and stress state; they do not add new combat bonuses. |
| Casualties | Added hit reactions, three corpse variants per faction, leg/side wound animation and poses. The generic death references contain no bitmap, so visible recovered corpse art replaces those empty references. |
| Grenades and carrying | Added grenade preparation and wounded pickup/put-down transitions. Carry movement and idle continue using recovered art. The prone-throw references are bitmap-free aliases, so the usable original standing throw is retained as a visual fallback. |
| Sounds | Connected all 13 available scream recordings, the alternate MG42 recording, and original command-button press/release sounds. Existing recovered weapon/grenade sounds remain. Playback is still the replacement Windows sound path, not the original mixer. |
| Maps and missions | Exposed 81 named map layouts, 71 additional mission variants, and the standalone alternate StoneHouse layout: 153 selectable combinations. The previous selector exposed 71 layouts with only their first mission. All 202 duplicated nested files are kept intact but not listed twice. |
| Mission presentation | Restored original deployment-area artwork, available from Orders and shown while waiting for a match. Every mission objective now has independent one-square capture state and recovered faction artwork. Orders cycles through objectives. The requested 120-second capture rule remains. |
| Native controls | Restored Chat, Set Commander(s), Assign Weapons and end-of-match Play Again button art and actions. Buttons connect to the current chat, assignment viewers and return-to-lobby workflow. |
| Executable | Rebuilt `CoC Restored+.exe` with the community icon. The portable package launches without Python and contains no `launch.py`. That file remains a development/build entry point in the source repository. |

## Replacements kept

| Replacement | Why it remains a better fit |
| --- | --- |
| Offline / Host / Join launcher | Original GameClub assumes the retired account and room service. It has no equivalent flow for selecting CPU teams or entering a direct-host address. |
| Lobby roster and assignment dialogs | Current controls understand CPU slots, local host authority, side changes and finite host-configured weapon pools. Original dialogs depend on missing service/module behavior. Original battlefield buttons now open these dialogs; assignments are view-only during a match. |
| Chat pane and transport | Room/team/private messages work over the current connection. The original account-backed chat service cannot be used as a replacement. The original Chat button focuses the current message input. |
| Simplified debrief data | Original background and soldier-result presentation stay. Promotion controls remain inactive because exact scoring/progression and account records were not recovered. No invented promotion results are shown. |
| Destination markers and name/pip placement | Keep the explicitly requested filled red ground squares, centered pips, ownership filtering and hidden self/dead names. Some legacy marker art would reverse those choices. |
| Missing-map-art substitutions | Keep the existing substitutions where the referenced original corner/house image is absent. Present artwork is reused; no replacement artwork was generated in this pass. |
| Animation driver and game logic | Keep the replacement server, bridge and frame clock. Original clips are available, but the original state-machine code, timing and complete combat formulas are not. |
| Community branding | Keep the community icon and removed version/2AM title presentation as requested. Original branding files remain preserved. |

## Preserved but not forced into gameplay

GameClub graphics/music, unsupported weapon icons, unused editor/legacy art and promotion-specific widgets remain in the recovered files. Their presence is not proof that their associated feature belongs in this offline/direct-connect build. They have not been deleted or replaced with invented equivalents.

Three small OIX files (`TheBunker1_gw1`, `frmft1_aw1`, `frmft1_gw1`) only request ammunition-object creation. They do not provide a complete usable cache placement/quantity rule, so they are preserved without granting arbitrary ammunition.

German-HQ floor records contain `_HG_Evan`, `_Evan`, `_HG_NEvan` and `Worlds` typos. These resolve to the existing `_HG_Even` terrain and `World` at load time. Original file bytes remain unchanged.

The [inventory](asset-restoration-inventory.json) lists every UnitMaster image reference, renderable/placeholder status and every selectable map/mission. Original imagery is evidence for appearance; transition timing and state selection remain reconstructions. Not every pose, camera rotation or complete mission has had a visual playthrough.
