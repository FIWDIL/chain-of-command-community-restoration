# Restoration reference review

Reviewed September 25–26, 2026. A requested restoration of an original function is not a new feature merely because the user had to ask for it. The earlier audit confused those two questions in several rows. [The revised audit](FEATURE_AUDIT.md) separates the historical function from the accuracy of its current implementation.

## What was actually reviewed

The review covered all 18 images linked by CoC Central's two-page Chain of Command gallery, the March 2000 advertisement below, the user's supplied images, and selected frames from five relevant YouTube recordings. These were viewed in the browser. Videos were sampled at the positions listed below, not watched continuously or analyzed frame by frame. This is not a claim to have located or viewed every surviving image/video on the Internet.

General web/image searches returned many unrelated tabletop games, newer games with the same title and Call of Combat successors. They were excluded. YouTube's search for “chain of command 2am” supplied the five relevant recordings below; subsequent visible results were primarily unrelated titles. The community-era recordings cannot by themselves prove that every detail existed in the first 2AM release.

## Recordings

| Source | Inspected positions | What can be established |
| --- | --- | --- |
| [2AM CHAIN of Command — tennie ArmyBarbie](https://www.youtube.com/watch?v=OpUfEyB25sQ) | 0:07, 1:23, 2:46, 4:10, 6:15, 6:45; supplied 6:48 debrief screenshot | Bottom command rows/chat, overhead labels, ground destinations, fighting poses, scrolling/rotated views, visible explosion clouds. The supplied image shows the debrief and promotion area. |
| [2am chain of command by CannonFodder — thomas](https://www.youtube.com/watch?v=f5gLn7Ly4U8) | 0:25, 3:28, 6:15 | Building/field combat, overhead pips, terrain visibility and a white explosion cloud. The crop excludes much of the command UI. |
| [Chain of Command Game — XenaCOC](https://www.youtube.com/watch?v=HSF-941tVfg) | 0:24, 2:03, 3:41 | Edited montage, nearby combat, different soldier poses, labels/pips, objective annotations and closing title. Transition frames are not animation evidence. |
| [chain of command 2am — tennie ArmyBarbie](https://www.youtube.com/watch?v=l0kDpa43yJA) | 0:33, 1:43, 3:07 | Original Ignore dialog, battlefield/chat layout, and an in-match weapon-assignment window with a mission commander's cache. Current pre-match-only equipment editing is therefore incomplete. |
| [2am chain of command — tennie ArmyBarbie](https://www.youtube.com/watch?v=dkvSdMlScKI) | 2:07, approximately 4:22 | Command/status rows, notices, pips and a filled red destination diamond with centered pips. Does not establish precise flash cadence or movement speed. |

## Screenshot gallery

[Page 1](https://www.coccentral.com/CoC/Screenshots/index.php?page=1) and [page 2](https://www.coccentral.com/CoC/Screenshots/index.php?page=2) link the following images. Every image below was opened at full image size in the browser; taller images were inspected within the viewport. Text near cropped edges is not treated as established evidence.

| Image | Observations |
| --- | --- |
| [1](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/1.jpg) | Orchard battle, names/pips, casualties, bottom commands/chat, both scrollbars. |
| [2](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/2.jpg) | Building interiors, names/pips and low walls. |
| [3](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/3.jpg) | Stone-house objective, prone soldiers, bottom command strip. |
| [4](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/4.jpg) | Crowded building combat, varying poses and labels. |
| [5](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/5.jpg) | Direct evidence of filled red ground diamonds with yellow pips centered inside; overhead pips on owned soldiers. |
| [6](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/6.jpg) | Ground destination feedback, wall/terrain relationships and battlefield chat. |
| [7](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/7.jpg) | Original game-club lobby with room list, player list, chat, whisper and ignore controls. New direct-host launcher is not this service. |
| [8](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/8.jpg) | Deployment stage, four owned soldiers, command table showing 70/900 ammunition and five grenades. Supports total-ammunition display rather than just loaded rounds. |
| [9](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/9.jpg) | Soldier positioned at a window, Cover status, ammunition/grenade columns and separate message window. |
| [10](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/10.jpg) | Multiple window-cover positions and the same command/status table. |
| [11](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/11.jpg) | Scrolled battlefield and persistent commands/chat. |
| [12](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/12.jpg) | Prone soldiers, numerical ammunition, five grenades, Lying status and chat. |
| [13](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/13.jpg) | Mission selection, two side rosters, commander rank requirements, leave-side control, waiting countdown and chat. |
| [14](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/14.jpg) | Debrief after annihilation, individual WIA/OK outcomes, player identity, kill/terrain totals and commander/subordinate promotion rows. Establishes elimination as an original ending condition, not the complete current victory formula. |
| [15](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/15.jpg) | Wall/cover combat, black and yellow labels and short red shot traces. Label-color semantics are not established. |
| [16](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/16.jpg) | Visible white explosion cloud, cover, prone/standing poses. |
| [17](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/17.jpg) | Low-cover fighting poses, pips and red shot traces. |
| [18](https://www.coccentral.com/Enlarge.php?img=CoC/Screenshots/18.jpg) | Red shot traces and a notice refusing movement too far from the fireteam. The screenshot does not supply the distance threshold. |

The [March 2000 advertisement preserved by Retromags](https://www.retromags.com/gallery/image/42587-chain-of-command-march-2000/) was also inspected. It presents the game as online play against other people and emphasizes regiment/team play. Offline CPU play is an addition; command rows, messaging and pips are not.

## Changes supported by the combined evidence

- Load grenade inventory and distances from the recovered ODF: five grenades, five-square throw limit and two-square blast distance.
- Load ammunition limits from the six recovered weapon objects: 70 rifle rounds, 200 SMG rounds, 900 MG rounds. Show total ammunition in the recovered command table. The current magazine/reload subdivision remains approximate.
- Use `ImageShop.GranadeExplosion$art` and UnitMaster image assignments instead of hard-coded alternate image names. This restores references, not the complete effect/animation state machine.
- Reveal the recovered soldier information labels at their recovered positions. The missing module no longer controls their visibility. Keep ammunition text above its weapon image.
- Reclassify bottom commands, scrollbars, pips, destination markers and in-game chat as requests to restore documented original functions.

## Remaining alignment gaps

The recovered files are more substantial than just artwork: they include UI layouts, object schemas, scenario records, image-state assignments and some concrete gameplay values. The missing server/module still leaves many transitions and formulas unknown. An absent verified implementation does not mean the feature was absent from the original.

All 438 recovered OIX files were parsed and checked for the specific inventory, distance, equipment-pool, time-limit and promotion fields listed in [the scenario scan](recovered-scenario-values.json). None populated those exact fields. This narrow check does not establish that all other scenario behavior is absent. The concrete ODF values and image assignments are recorded separately in [the recovered-value extract](recovered-gameplay-values.json).

The references establish original deployment and mission selection, in-match equipment/cache assignment, commander/promotion interfaces, shot traces, fireteam-distance restrictions, cover-specific poses and richer explosion presentation. Current replacements do not fully reproduce those systems. Exact point formulas, inventory overrides, commander authority, distance limits, effect composition and animation timings need further evidence or reverse engineering.

In particular, `grex` is the recovered grenade-effect reference and renders as a small flash in the current native check. References also show a larger white cloud. The existing recovered `exp2` cloud is retained alongside that flash to match the observed appearance. Their combined lifecycle/timing is still reconstructed, not a recovered effect script. Smoke currently reuses generic explosion frames and is not verified original smoke behavior.

Some screenshots show equipment combinations that should not be used to infer one universal per-fireteam cap across all versions/modes. Recovered `INIT_LimitPerSquad` values remain the current cap source until scenario/version differences are understood.

Objective-capture requirements, gameplay hotkeys and retired branding remain removed under the user's explicit instructions. Media review is not authorization to reverse those preferences.
