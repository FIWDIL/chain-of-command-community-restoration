# Recovery and native compatibility

## Preserved client

`creation.exe` SHA-256:
`bf817ef80d98872ffe117b9d7d11a79b4238ea616bd9a9a828a97c8db91d5ccd`

The launcher rejects a different executable before installing its in-memory hooks. Original ODF, OIX, MBM, BMP and sound files are read directly. `original-manifest.json` records the recovered files; the separately added `wing32.dll` is built from this repository's compatibility source. No changes are made to Combat on Contact, the recovered Desktop installation, or Windows system files.

The missing `zamCocSc_client.dll` name is retained in the original ODF. Loading it is nonfatal, but its game-specific input glue is absent. The new bridge hooks Creation's native map input dispatcher at 0x4a2250 and key dispatcher at 0x4a3f40. It forwards logical map coordinates and original command-strip clicks to the authoritative service. The legacy browser preference is overridden for this process; no account or registry configuration is changed.

Original weapon and grenade WAV files play through the launcher's Windows sound channel, replacing the missing module's DirectSound trigger. This first release has one effect channel, so overlapping sounds can interrupt each other. Network messages select only an allowed sound name; they cannot choose a local file path.

The app-local WinG shim implements only the four functions this executable imports. It uses GDI `CreateCompatibleDC`, `CreateDIBSection`, `BitBlt` and `CreateHalftonePalette`, and exports the original WinG names. [Microsoft's DIB documentation](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdibsection) describes the shared pixel-memory mechanism. The shim is not intended as a general WinG replacement.

## Wire format

Native game TCP port: 1850. Frame header: little-endian four 32-bit values `(0xfedcba98, payload_length, sequence, 0xabcdef00)`. Payload: 16-bit message kind, message data, 32-bit `0x89abcdef` trailer. Incoming frames are limited to 4 MiB.

Observed startup sequence: server 0; client 1; server 2 version/model negotiation; client 3 credentials; server 4 model snapshot; client 13 snapshot acknowledgement; server 5 startup complete. Client type 25 acknowledgements can interleave with these messages.

Snapshots declare all new object identities before their property records. New properties use `u16 property-id + typed value`; existing-object changes additionally have a one-byte presence flag. A zero presence flag clears the property. Object/property lists use their observed zero or 0xffff terminators. All references are resolved case-insensitively.

Runtime message 8 sets a property, with full-reference escape bytes when compression tables are empty. A user-object Refresh update commits a visible redraw; setting a world's Refresh alone is insufficient. Camera scroll updates are sent after the view is created. Startup metadata must supply the recovered background bitmap and palette or the native renderer can dereference an empty surface.

TCP 1851 is newline-delimited JSON, capped at 4096 bytes per client message. The initial handshake is `{"version":1,"password":"room password","support":"MG"}`. The server allocates a random temporary username and binds the native client to that session's source address. Commands can operate only on that session's side. Selection, keyboard, and native mouse messages are validated and rate-limited. No original 2AM login credentials are used. This protocol is version-specific and unencrypted.

## Map fallback data

71 map layouts are indexed from recovered `_map.OIX` files; their original files and names are unchanged. Scenario `_1.OIX` supplies deployment centers and the first victory point when present. Defaults are (20,50), (80,50), and the midpoint; impassable spawn/objective cells move to the closest walkable cell.

Four maps — hse, nagrsch, pst and rts — reference absent generic images. At load time `icor` maps to `iwcr`, `qcor` to `wcor`, and `wh09` to `wh01`, using original recovered art. Those substitutions preserve playability but may differ from the intended decorative corners. They are not written into the original maps.

The German crouch uses the recovered crouch transition with looping disabled. Smoke holds/repeats middle cloud frames from the original explosion. No remastered or Combat on Contact assets are included.

## v0.2.0 player slots

The command/session protocol now requires version 2. Native Creation framing is unchanged. The control handshake returns a server-selected side and fireteam slot, plus team size and finite weapon pools. Each native snapshot maps the four-row HUD to that slot while rendering all visible soldiers. Slots range 0–6 per side; a side-local soldier index maps to `slot = index // 4` and `number = index % 4`. Soldier IDs occupy a separate range from HUD and effect objects to avoid the collisions that simply extending the old eight-soldier ID block would create.

The host receives a fresh in-memory capability to start its room. Regular joiners cannot start it or command another fireteam by supplying a forged side/slot in input. The local host slot is reserved. This does not add encrypted transport or original account authentication.
