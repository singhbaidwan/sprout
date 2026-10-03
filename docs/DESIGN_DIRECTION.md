# Making Sprout deeper and distinctive

Research reviewed 2026-09-20; implementation status updated 2026-10-03. These are design recommendations, not a claim to have played the reference games. Only the features explicitly marked implemented below exist in Sprout; the proposals do not add Python APIs yet.

## Lessons from the references

| Reference | Observed design | Application to Sprout |
| --- | --- | --- |
| [Factorio's official overview](https://www.factorio.com/) | Factories combine resource extraction, infrastructure, technology research, and automated production at growing scale. | Give players connected systems where improving one part exposes the next constraint. |
| [Factorio logistics](https://wiki.factorio.com/Logistic_network) | Supply/request storage, transport robots, capacity limits, and charging throughput shape logistics. | Make inventory targets, transport distance, and visible queues meaningful; a larger fleet alone should not solve every problem. |
| [The Farmer Was Replaced store description](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/) | Python-like programs automate farming; resources unlock technology, concepts arrive gradually, and progression continues into harder programming challenges. | Teach one new decision at a time, with short examples and opportunities to optimize a working solution. |
| [The Farmer Was Replaced 1.0 announcement](https://steamcommunity.com/ogg/2060160/announcements/detail/521978797993492537) | Its full release added multiple drones and a revised unlock tree. | Multiple drones are useful depth, but are not by themselves a distinctive premise for Sprout. |

## Recommended identity

**Program a living farm that supplies a small village.** Combine crop care, cooperative transport, and production with measurable resource trade-offs. A player should be able to build a fast industrial farm, an efficient low-water farm, or a resilient mixed farm, and see why each program performs differently.

The proposed differentiator is the interaction between ecology and factory scheduling. For example: use residue for fertilizer to boost next harvest, or divert it to fuel during a power shortage. A forecast makes the shortage predictable, and a village contract rewards a different output mix. This is a design direction, not a claim that no other game has used these ideas.

## Prioritized additions

| Priority | Proposal | Player decision and example challenge | Completion criterion |
| --- | --- | --- | --- |
| Implemented now | Optional two-drone team | Assign farming and courier roles, observe cargo congestion, keep the bakery supplied. | Independent programs and cargo, one world clock, conflict handling, paused saves, all growing-option combinations tested. |
| Implemented now | Efficiency dashboard and three reproducible contract scenarios | Deliver 24 loaves in a fixed tick budget; then improve water per loaf, machine idle time, and empty travel. | Fixed starting snapshot, visible before/after score, personal records separated by rule preset and drone count. |
| Next: production choices | Residue → compost → fertilizer, or biomass → fuel | Decide whether the next harvest or the machines need the byproduct more. | Conserved items, bounded machine buffers, at least two useful production strategies, no forced grind. Existing simple compost remains the easy preset. |
| Next: buildable logistics | Place machines, short conveyors, storage targets, reusable routes | Reduce delivery distance; reserve enough grain for seeds or processing. | Validated layouts and blueprints, visible buffer/throughput limits, old fixed-map saves preserved. |
| Later: living fields | Crop rotation, adjacency effects, and crop-specific harvest rules | Alternate soil-restoring crops with hungry crops; reserve irrigation for the right field zone. | Each crop changes code structure or planning, not just its price; inspectors explain effects. |
| Later: predictable variation | Optional weather forecasts and seasonal contract demand | Store water ahead of a dry period or change production before market demand shifts. | Seeded, replayable scenarios; visible forecast; no unexplained crop loss; toggles retain progress. |
| Later: specialization | Scout/sensor, irrigator, hauler attachments and research branches | Trade cargo capacity for watering reach or sensing coverage. | Sidegrades create distinct strategies; ordinary Python control flow stays available from the start. |
| Later: sharing | Local challenge seeds and code/blueprint export | Compare two programs against the exact same starting farm and rule set. | Portable validated artifacts, deterministic results, no hosted account system required. |

**Efficiency feedback plus three contract scenarios** is delivered: Bakery Rush, Waterwise Harvest and Full Buffers, each with separate solo/team records. All six starter variants complete within their tested budgets. [Exact shipped rules and results](CHALLENGES.md). The next proposed milestone is one conserved byproduct chain that makes crop-care and production decisions interact; its recipes and quantities still need design.

## Configurable complexity

Keep the existing independent Fertilizer, Irrigation, and Soil health options. Proposed presets could group them as Relaxed, Logistics, and Living Farm, while still allowing custom combinations. Future weather, energy, spoilage, and traffic should each be optional. Record enabled rules in scenario scores; comparing different rule sets as if they were equivalent would be misleading.

Introduce systems when they create a new decision. Avoid adding several routine refill chores at once. Unlock useful capabilities and trade-offs rather than withholding basic loops or making early farming deliberately tedious. Do not introduce unavoidable disasters, combat, public execution, accounts, or an unrestricted Python runtime as incidental parts of this roadmap.

## Technical sequence

1. Build on the implemented shared-clock scheduler and versioned saves; do not tick the world once per drone or conveyor.
2. Bounded measurement counters, a snapshot-based scenario runner and local personal records are implemented. Online leaderboards remain a separate proposal.
3. Add one conserved byproduct chain and a visible bottleneck inspector before increasing item count.
4. Design schema migration and construction validation before movable buildings or blueprints.
5. Keep complete original artwork/code; study design principles rather than copying assets, maps, progression names, or exact puzzles.

Requirements and implementation details for the delivered drone milestone are in [DRONE_TEAMS.md](DRONE_TEAMS.md). Broader proposals remain scoped separately in [ROADMAP.md](ROADMAP.md).
