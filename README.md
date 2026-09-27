# CoC Restored+

Free supported community restoration using the recovered Creation client, graphics archives and maps.

Double-click **CoC Restored+.exe** to play. Keep the `game` and `_internal` folders beside it. No Python installation is needed for the packaged game.

## Play against the computer

Choose **Offline vs CPU**, then choose a map, team size, machine guns and SMGs. Click **Start match**.

You control four soldiers. Each extra fireteam adds four computer-controlled soldiers to each side. Weapon settings apply to each whole side, with rifles filling the remaining places.

## Play with friends

Choose **Host**, set up the match and click **Open lobby**. The launcher shows your local IP address and the lobby and game ports. Give those details and your room password to your friends.

Friends choose **Join**, enter your IP and password, then click **Join lobby**. Everyone can choose or change sides before the host starts. The team list shows players, computer fireteams and their commanders. The host can change reporting relationships before launch. Commanders may assign weapons within their branch, while each player keeps control of their own soldiers.

**Start match** marks a guest ready. The host uses it to launch the battle for everyone. **Leave lobby** disconnects a guest; **Close lobby** closes the hosted room. After a match, the host chooses **Return to lobby** to prepare another round without disconnecting everyone. The host can then choose the next map.

The lobby uses TCP port 1851 and the game uses TCP port 1850. Both must be reachable. The displayed IP is a local network address; Internet play may need router forwarding or a VPN. There is no public matchmaking service. Use a room-only password because connections are not encrypted.

## Give orders

Click a soldier or drag around your soldiers to select them. The top command row gives orders to all four; each lower row controls one soldier. Choose an order, then right-click its destination or target. Right-drag sets facing. Click a targeting command again to cancel it.

The **Orders** menu also provides smoke grenades, stop, crouch, stand, prone, soldier selection and cancel targeting. No gameplay hotkeys are needed. Use **Equipment** before a match to assign individual weapons from the limited side stockpile.

Use **Center** to return to your soldiers. Use the horizontal and vertical scrollbars to look around. Yellow pips identify your four soldiers; filled red squares flash at their destinations. Only other players’ living soldiers show names in multiplayer. Destination pips sit in the center of the ground marker. The mouse wheel is disabled; use the scrollbars to move the view. Choose room, team or private chat, then type a message and press **Enter** or **Send**. In the launcher, select a private recipient and use **Ignore / unignore** to control incoming messages. The in-game **Lobby** button brings the launcher forward.

Defeat the opposing soldiers to win. After 15 minutes, surviving teams draw. Capturing the point is optional and does not end the match.

## About the restoration

This is a partial reimplementation around the recovered engine, maps, sounds and artwork. Combat, movement, visibility, computer tactics and multiplayer service behavior have been newly implemented; much of that behavior is approximate rather than verified against the original. See the [feature-by-feature provenance audit](docs/FEATURE_AUDIT.md) for what is original, verified reconstruction, approximation or a requested change. The original Mission-End Debriefing artwork now shows the result and each soldier's condition. Campaign progress, persistent ranks and the original online service are not available.

Completed matches are saved on the host computer and can be reviewed with **Match history**. These are local results, not recovered accounts or original promotion records.

See the [reference review](docs/RESTORATION_SOURCES.md) for inspected recordings/screenshots and remaining alignment gaps. The recovered files include more than art: layouts, scenario records, state-to-image references and some gameplay values survive. Requested restorations of original controls are distinguished from intentional changes in the audit.

See the repository's `docs` folder for gameplay notes, restoration details and test coverage. For help, include the map, mode and steps that caused the problem.

The MIT license applies only to the newly written restoration code. Original game files remain separately copyrighted. See [third-party notices](THIRD_PARTY_NOTICES.md). This is a community restoration, not an official 2AM service.

## If anyone has the following data or files, let me know!

The aim is to restore Chain of Command as completely and as close to the original as feasible. Some approximations were gleaned from limited public sources, including surviving community pages, screenshots and gameplay videos, alongside the recovered client data. Those sources do not establish every formula: undocumented numbers and some behavior remain restoration choices. Exact original files and rules would be preferable to approximations.

The most useful contributions would be:

- **`zamCocSc_client.dll`**: the missing game-specific client module, matching symbols, source code, or an installer that contains it.
- **The original server**: source code, server executables, configuration files, database schemas and protocol documentation. The gameplay server and original online service were not recovered.
- **Scoring and promotion rules**: kill/injury points, mission rewards, point distribution through commanders, rank thresholds, penalties after death or retreat, and any persistent player/regiment progression rules. Rank names and some client fields survive, but the complete formulas do not.
- **Command and weapon-assignment rules**: commander selection and succession, rank restrictions, subordinate visibility, special-weapon stockpiles by player count or mission, and who could assign equipment to whom.
- **Combat and movement details**: original accuracy, weapon timing and ammunition rules; stress and injury behavior; wall edges, windows, corner-peeking, grenade trajectories and visibility calculations.
- **Missing graphics**: the original `icor`, `qcor` and `wh09` image entries and their matching graphics archives/model definitions. The maps `hse`, `nagrsch`, `pst` and `rts` currently need substitutions. Original smoke-specific artwork and animation definitions would also help.
- **Complete maps and scenarios**: original mission configurations, spawn points, objectives, timing, ammunition and weapon-cache quantities, plus any missing map variants.
- **Original manuals and recordings**: help files, training manuals, screenshots or videos showing the command controls, assignment screens, debriefing, chat and lobby. Full installations from different periods would help distinguish original behavior from later community changes.

Useful surviving references include [CoC Central's history](https://www.coccentral.com/CoC/Information/) and this [gameplay recording](https://www.youtube.com/watch?v=OpUfEyB25sQ). They help establish appearance and broad behavior; they are not a substitute for the missing server code or exact rules.

Please describe the source and approximate date of anything you can share. Reports can be opened in [GitHub Issues](https://github.com/Huckleberry87/chain-of-command-community/issues).

This restoration deliberately keeps objective-capture requirements, gameplay hotkeys and retired-service branding removed. Missing-file requests do not mean those choices will be reversed.


## Capture point

The capture point occupies one square and starts neutral. An active soldier must occupy that square for 120 seconds to capture it. Multiple friendly soldiers do not speed this up. Both sides on the square pause the timer; leaving resets progress. The owner keeps control until the other side completes a full capture. Ownership uses the recovered USA/Germany floor symbols and flag sprites. Capturing does not end the match or award reconstructed victory points. The 120-second rule and contest/reset behavior are requested/reconstructed behavior, not verified original timing.
