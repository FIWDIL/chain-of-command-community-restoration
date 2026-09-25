# Weapon restrictions: recovered evidence and restoration defaults

## What the recovered game data actually says

The primary source is the preserved `original/cocSc.ODF`. The relevant property is **`weapon.INIT_LimitPerSquad`**:

| Original object | Weapon | Recorded per-Squad limit |
| --- | --- | ---: |
| AW_BAR | BAR | 1 |
| GW_MG42 | MG42 | 1 |
| AW_Thompson | Thompson | 2 |
| GW_MP40 | MP40 | 2 |

All nine recovered rank definitions start the four American soldiers with Garands and the four German soldiers with Mausers. Special weapons are separate from those base rifle loadouts.

The `SCENARIO` schema contains independent side stockpile fields: `Am_BAR`, `Am_Thompson`, `Gm_MG42`, `Gm_MP40`, plus extra grenade and ammunition fields. Both faction objects refer to a weapon cache and weapon-assignment display. The message provider includes an over-limit error. These are evidence of **both a group assignment cap and a finite side/scenario cache**, not evidence that every player automatically received an MG or two SMGs.

The lost server's assignment and stockpile-generation code has not been recovered. None of the recovered OIX map/scenario records specifies the four special-weapon stockpile quantities. We therefore **cannot verify an original table such as “one MG every two players” or a particular 7v7 SMG allowance**. Absence of these values is not proof that the stockpile was zero. The client also contains later community-era material, so its values do not establish every rule used by the original 1999 service.

For the restoration, “Squad” in that property is interpreted as the original four-soldier player group (called a fireteam in the launcher). That scope is an inference; the numeric caps are directly recovered. This does not establish the historical limits for a larger command hierarchy.

The [machine-readable extraction](recovered-weapon-rules.json) includes the ODF hash and original field/object names. The surviving [CoC Central weapon page](https://www.coccentral.com/CoC/Weapons/) lists the special weapons but provides no allocation counts. It was checked as a secondary corroboration of the lineup, not used to invent a quota.

## What v0.2.0 implements

The host can set **MGs per side** and **SMGs per side** before opening a match. Both sides receive the same quantities; USA uses BAR/Thompson and Germany uses MG42/MP40. Rifles fill all other positions. Automatic assignment spreads MGs across the fireteams and favors groups without an MG when handing out SMGs. It enforces one MG and two SMGs at most in each four-soldier fireteam.

These initial stockpile values are explicitly **reconstructed balance defaults**, not claimed historical rules:

| Match | Soldiers per side | MGs per side | SMGs per side | Rifles equipped per side |
| --- | ---: | ---: | ---: | ---: |
| 1v1 | 4 | 1 | 0 | 3 |
| 2v2 | 8 | 1 | 0 | 7 |
| 3v3 | 12 | 2 | 1 | 9 |
| 4v4 | 16 | 2 | 1 | 13 |
| 5v5 | 20 | 3 | 1 | 16 |
| 6v6 | 24 | 3 | 2 | 19 |
| 7v7 | 28 | 4 | 2 | 22 |

The default formula is `MG = ceil(fireteams / 2)` and `SMG = floor(fireteams / 3)`. The host may change those values, including a rifles-only match, within the recovered group caps. The highest permitted configurable 7v7 stockpile is 7 MGs and 14 SMGs; this is the restoration's aggregate cap, **not a claim that the original game supplied that many**.

The assignment cannot be duplicated by joining, reconnecting or changing sides. A connection takes over an existing fireteam with the equipment, casualties and ammunition it already has. The original rank-based commander assignment screen is not restored in this release.
