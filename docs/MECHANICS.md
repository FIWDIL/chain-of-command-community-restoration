# Reconstructed skirmish mechanics, v0.1.0

The missing server formulas could not be recovered. Values below describe this implementation, not historical fact or a claim of original-game equivalence. Distances are logical map squares, not a verified meters conversion. The recovered model does specify a maximum grenade throw of five squares; that value is retained.

## Match

Each side has four soldiers. Three have Garand or Mauser rifles. The fourth has BAR/MG42, or Thompson/MP40 when that player chooses SMG before loading. The offline AI uses the German default loadout. Capturing within three squares adds one point per uncontested second. 90 points wins. Incapacitating every opposing soldier also wins. At 15 minutes, the higher capture score wins; equal scores draw. Retreat concedes. A randomly chosen soldier per side is identified as the player at match end; there is no persistent promotion score.

## Weapons

Intervals are practical simulated shots, not mechanical cyclic rates. One simulated MG/SMG shot consumes one cartridge. All weapons use the recovered faction infantry animations, not individually redrawn weapon-in-hand art.

| Weapon | Loaded | Reserve | Shot interval, s | Empty reload, s | Range | Base accuracy | Damage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Garand | 8 | 80 | 1.00 | 3.2 | 24 | .70 | 65 |
| Mauser | 5 | 60 | 1.80 | 4.0 | 26 | .76 | 70 |
| BAR | 20 | 160 | .30 | 4.5 | 24 | .48 | 58 |
| MG42 | 50 | 200 | .18 | 6.0 | 27 | .40 | 58 |
| Thompson | 30 | 180 | .24 | 3.6 | 16 | .48 | 40 |
| MP40 | 32 | 192 | .30 | 3.6 | 17 | .50 | 40 |

Reloads transfer at most one magazine from finite reserve ammunition. No tactical reload, heat, penetration, stoppage, or manual barrel-management system is modeled.

## Accuracy and injury

No shot is allowed outside range or across a blocked line. Otherwise:

`chance = base_accuracy × max(.1, 1 - .8 × distance/range) × (1 - .65 × stress)`

Multipliers: shooter moving .48; shooter prone 1.20; target prone .48 or crouching .72; target moving .80; low cover/window near the target .45; target in tree concealment .65. The result is clamped to .01–.95. A random value below the chance hits. A hit deals weapon damage multiplied by a uniform .65–1.30, rounded to a whole health point.

Soldiers start at 100 health. At zero health, the first incapacitation is 45% KIA and 55% WIA. Further damage that reduces an already wounded soldier to zero makes them KIA. WIA cannot fight or move. A friendly soldier within two squares can carry them at 60% normal movement speed and cannot fire while carrying. Put them down with the same command. No body-part damage, bleeding timer, medical revival, or ballistic penetration is claimed.

Stress is 0–1. Being fired at adds .08; injury adds .45. It decays .025 per second. Stress multiplies shot interval by `(1 + .4 × stress)`, reload duration by `(1 + stress)`, and movement speed by `(1 - .2 × stress)`. Stun stops movement and firing until its timer reaches zero.

## Movement, cover, and visibility

Speeds: walk 1.35, run 2.5, assault 1.15, crawl .55 squares/second. A* uses eight neighbors, rejects diagonal corner cutting, and doubles traversal cost for climbable low cover. Walls and large obstacles block movement by occupied square. Doors are gaps in that grid. This is a conservative approximation of the original wall geometry.

Solid cells block sight and gunfire. Windows allow a line only when both shooter and target stand. Prone soldiers cannot see or be seen through intervening low cover. Trees shorten detection distance and reduce hit chance. Detection limits are 28 squares standing, 22 crouching, and 16 prone; tree concealment multiplies the limit by .65. Visibility is shared within a side and hidden enemies are removed from that client's rendered world. This is visual concealment, not an anti-cheat guarantee.

The AI advances toward distributed objective positions, favors nearby cover in its destination choice, and goes prone or crouches when engaging at close range. Soldiers with no ammunition continue toward the objective. It has no learned tactics or original 2AM behavior code.

## Grenades

Each soldier has two fragmentation grenades and one smoke grenade. A throw has a five-square limit and a five-second fuse from the throw command. A solid wall blocks a throw. If the path crosses a window, success is 100% at distance one or less and decreases linearly to 10% at five squares; a failed throw lands at the thrower's square. This is a simple reconstructed rule, not a collision-based ballistic trajectory.

For a fragmentation blast, `factor = max(0, 1 - distance/3)`. Damage chance equals factor; a successful roll deals `150 × factor`, reduced to 60% against prone soldiers. Stun is up to `5 × factor` seconds and stress increases by factor. Solid walls shield the blast. Friendly soldiers can be hit. Smoke lasts 30 seconds and blocks lines through its 2.5-square radius. Cloud visuals reuse the middle frames of the original explosion animation.

All formulas live in `restoration/simulation.py`; the service is authoritative for both offline and direct play.
