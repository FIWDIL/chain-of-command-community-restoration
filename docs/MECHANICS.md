# How a match works

Each fireteam has four soldiers. You control one fireteam; the computer fills unoccupied places. A side can have up to seven fireteams.

Defeat every opposing soldier to win. A match is a draw if both sides still have active soldiers after 15 minutes. The capture point guides computer movement; capturing it gives no points.

## Moving and fighting

Walking, running and crawling prevent soldiers from shooting while they move. Assault movement allows shooting with reduced accuracy. Running is fastest; crawling is slowest and keeps a soldier low.

Walls block movement and fire. Low cover and trees make soldiers harder to hit. A soldier must stand to shoot through a window. Friendly teams share what they can see.

Soldiers reload automatically using their remaining ammunition. Ammunition is limited. Stress slows movement, firing and reloading and reduces accuracy.

## Weapons and casualties

Machine guns and SMGs replace rifles. Settings apply to the whole side. Joining, changing sides or reconnecting never creates more equipment.

A badly injured soldier may be wounded or killed. Wounded soldiers cannot fight or move. Use the wounded-carry command near a friendly casualty to carry them; use it again to put them down. A carrier moves slowly and cannot shoot.

Each soldier starts with five fragmentation grenades and one smoke grenade. Throws have a five-square range and a five-second fuse. Blast effects fall to zero at two squares. Grenades can hurt teammates. Smoke lasts about 30 seconds and blocks sight.

These are the restoration's rules. The lost server's exact formulas are unknown. Developers can find the numbers in [Technical rules](TECHNICAL_RULES.md).


## Capture point

The capture point occupies one square and starts neutral. An active soldier must occupy that square for 120 seconds to capture it. Multiple friendly soldiers do not speed this up. Both sides on the square pause the timer; leaving resets progress. The owner keeps control until the other side completes a full capture. Ownership uses the recovered USA/Germany floor symbols and flag sprites. Capturing does not end the match or award reconstructed victory points. The 120-second rule and contest/reset behavior are requested/reconstructed behavior, not verified original timing.
