# Tactical AI update

Both friendly and enemy computer-controlled fireteams use the same controller rules. Human orders retain priority. The new behavior is part of each game's authoritative simulation, so it also runs on a direct-connect host and takes over disconnected fireteams.

## Behavior

- Cover selection considers the direction of the observed threat, nearby protection and concealment. A wall behind a soldier does not count as shelter. A support position needs a firing lane; a stressed soldier can choose full concealment to recover. Exposed stationary soldiers go prone, rising when a sill or fence requires it to fire.
- Fireteams divide into a firing element and a moving element. Armed, unstunned soldiers with a usable weapon provide covering fire using normal ammunition, accuracy and suppression. Machine guns and automatic rifles receive initial preference. Roles alternate on a staggered nine-second cycle so the gunner can move while rifles cover. Casualties and reloading change who is available.
- Movement uses short bounds, at most six squares toward the assigned position before a small local cover search. Chosen routes are retained for several seconds to prevent constant redirection. Nearby occupied positions and reserved destinations are penalized or rejected. Original-engine paths also include a soft traffic cost; narrow passages remain traversable.
- Smoke is considered when a visible threat covers exposed movement and a firing element is not ready. Nearby pending/active screens prevent duplicate throws, with an additional fireteam cooldown. Soldiers wait for the existing five-second fuse before resuming. Smoke is finite and blocks both sides' sight; it does not give the AI a targeting exception.
- Fireteam contact memory stores the last observed location for twelve seconds. Hidden enemies do not update it. The AI still needs ordinary sight and range to shoot. Grenade avoidance, ammunition limits and stress remain active. Combat on Contact additionally avoids firing through an ally directly in its firing lane, and keeps its existing WIA rescue and safe frag-throw checks.
- Objective assignments remain independent of enemy sightings elsewhere. Capturing soldiers use the flag area while supporting fireteams occupy separate surrounding sectors. Combat on Contact retains its multi-flag allocation and player command hierarchy.

## Implementation and limits

These are deterministic game heuristics, not machine learning or recovered 2AM AI. Position searches examine a small set of local candidates and check only the best few routes. The original service staggers fireteam decisions and caps each local AI route search at 768 visited nodes; manual player movement keeps its full route search. No game artwork or recovered map files were changed. The original restoration still uses its conservative square-based wall model; Combat on Contact uses its existing wall-edge and body-exposure geometry.

Congestion can still occur temporarily at doors and other narrow passages. No controller can make every position defensible. A depleted or isolated fireteam may have to crawl across open ground; it does not receive extra equipment or knowledge. Covering fire uses the existing weapon/stress mechanics rather than inventing hits on unseen targets. AI balance has been tested with fixed scenarios and seeds, not an exhaustive tournament on every map.

## Research references

The general ideas of alternating movement and overwatch, adapting to cover, and using obscuration to protect movement were checked against the US Army's [squad movement overview](https://www.benning.army.mil/Infantry/DoctrineSupplement/ATP3-21.8/chapter_04/section_09/page_0020/index.html) and [FM 3-90-1](https://www.benning.army.mil/infantry/DoctrineSupplement/ATP3-21.8/PDFs/fm3_90_1.pdf). Those are modern references used for game behavior inspiration, not a claim of historically exact WWII faction doctrine. Timings and scoring weights here are game design choices.
