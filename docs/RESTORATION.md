# Restoration status

CoC Restored+ uses the recovered Creation engine, 71 maps, soldier artwork, command buttons and sounds. The recovered files are kept unchanged in `game`.

The [feature provenance audit](FEATURE_AUDIT.md) separates preserved material from verified reconstructions, approximations and requested changes. Reusing the original engine and artwork does not establish original gameplay behavior.

A new local service runs the match, supplies player input and connects friends directly. Offline play uses the same service on your computer. No original account is needed.

## Presentation

The game window can be resized. Commands and messages sit below the battlefield. Original button artwork shows which command is pressed. Yellow pips identify only your four soldiers. Other players’ living multiplayer units show centered names. Ground markers have centered pips and draw beneath soldiers. Filled red squares flash at movement destinations. The mouse wheel is disabled. Community titles and icons replace the retired service branding at runtime.

The recovered Mission-End Debriefing now shows victory, defeat or draw, each soldier's condition and the player identity revealed at the end. Unavailable point totals are shown as dashes. The inactive promotion section is hidden.

## Missing map art

Four mapsâ€”hse, nagrsch, pst and rtsâ€”refer to missing images. The game substitutes recovered art while loading:

| Missing image | Replacement |
| --- | --- |
| icor | iwcr |
| qcor | wcor |
| wh09 | wh01 |

The original map files are unchanged. These corners and walls may look different from the intended artwork. Smoke also reuses recovered explosion-cloud frames.

## Still incomplete

The original online service, persistent ranks and complete promotion rules were not recovered. Commander assignments, equipment permissions, scoped chat and lobby continuity now have working reconstructed implementations. Local match history records outcomes without inventing original promotion scores. Combat and computer tactics use reconstructed rules. Loading every map successfully does not mean every map has had a full playthrough.

This project is separate from Combat on Contact. Its Godot code and assets are not used here.

For source setup and packaging, see [Building](BUILDING.md). For the current checks and limitations, see [Validation](VALIDATION.md).

## Current room features

The host can assign a cycle-free command tree for each side before launch. Commanders can equip their own fireteam and subordinate fireteams without exceeding recovered per-fireteam caps or the side stockpile. Combat orders still control only the player's own four soldiers. Exact original command succession, rank eligibility and subordinate visibility remain unverified.

Room, team and private messages are filtered by the server. Team/private history is restricted to its original recipients; late joiners do not inherit private messages. Ignore controls do not hide system notices.

Returning to the lobby preserves connections, chat, hierarchy and weapon choices; the next match resets casualties and ammunition. Map changes are host-only. Match history is stored locally in `saves/match-history.json`, with no original account authentication or promotion claims.
