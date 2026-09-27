# What we check

Automated tests cover all 71 map layouts, four-soldier ownership, matches with up to fourteen connections, weapon limits, movement, cover, ammunition, grenades, casualties, computer tactics, lobby side changes and chat.

Native Windows checks cover the actual recovered renderer, command buttons, selection, movement, window layout and messaging. Two clients have played together on one computer. Separate-computer and Internet play still need testing.

The recovered files are checked against all 505 hashes in `original-manifest.json`. The packaged launcher must start a match without a Python installation or a source-tree dependency.

These checks establish the restoration's behavior. They do not prove that reconstructed combat rules match the lost original server, or that every map is visually perfect.

The current checks include 62 automated tests, the packaged Offline vs CPU and Host forms, visible horizontal scrolling, mouse orders, and the recovered debriefing. Tests also cover private-message visibility, ignored players, finite weapon assignments, command hierarchy cycles, lobby resets and saved results. Two native clients completed a round, returned to the same lobby and started another round with their control connections preserved. Movement now advances the recovered directional frames explicitly on the server clock. Native checks cover run poses, own-fireteam pips, multiplayer owner labels, filled destination flashes and disabled wheel input. Integer cells and fractional positions are both updated for terrain sorting.

Recovered-data alignment checks cover five-grenade inventory and exhaustion, data-driven throw limits, two-square blast cutoff, all six ammunition totals, the native grenade image reference, prone throws, German crouching, stationary carrying and retreat-label cleanup. These verify use of client data; magazine subdivision and blast falloff are still reconstructed.

Native alignment checks confirmed visible recovered ammunition/grenade labels and the `grex` flash. The existing cloud is retained alongside the flash; exact sequencing remains unverified; see [reference review](RESTORATION_SOURCES.md).
