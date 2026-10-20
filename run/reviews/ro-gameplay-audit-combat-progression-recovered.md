# Combat/progression recovered capability/gap matrix

**18 grouped features; completed partial matrix, not gameplay acceptance.** Pin `e985006171d2eb320ee512a653f4c83aea3d81b6`; MAIN20180704/pre-renewal. Renewal applicability is explicit per JSON row. No new collection/play.

**Boundary:** Native movement/damage and bounded chat are historical primitive proof. XP/loot/stat/skill spending and first-job loop remain unaccepted. Source readiness: 4,177 tests +65 subtests, 95.37%, 208 frozen inputs, inherited from `run/reviews/playing-mvp-native-npc-approved.json` (not rerun). Actual budgets0 are delegated context, not an independently anchored receipt.

| Feature | Current tier | Gap / native acceptance required | Cached sources |
|---|---|---|---|
| `combat.target_selection` | native_primitive_verified | Accept repeated target acquisition/arrival/hit across despawn and session boundaries; primitive receipts do not prove sustained farming. | [4] `src/map/unit.cpp`:2902-2977; [5] `src/map/battle.cpp`:7869-7920 |
| `combat.basic_attack_damage` | native_primitive_verified | Native damage is verified, not kill, XP, loot, productive survival or complete goal. | [5] `src/map/battle.cpp`:6753-6800; [4] `src/map/unit.cpp`:2902-2977 |
| `combat.survival_recovery` | offline_pipeline | Current source has rest ownership, standing and motion interlocks; old diagnostic predates these fixes. Repeat native survival/recovery acceptance is unknown. | [1] `src/map/pc.cpp`:9682-9695; [6] `src/map/clif.cpp`:11697-11830 |
| `combat.death_and_reentry` | unknown | Death observations exist in historical ledger; resurrection/return-to-play behavior not accepted. | [3] `src/map/status.cpp`:9276-9295 |
| `combat.learned_skill_observation` | missing | No accepted native learned-skill context or runtime skill action; templates and official skill DB are knowledge, not telemetry. | [1] `src/map/pc.cpp`:9129-9177; [7] `db/pre-re/skill_tree.yml`:44-81 |
| `combat.skill_targeted` | unknown | No native targeted-skill action/ACK acceptance; absence of runtime action does not prove every codec absent. | [4] `src/map/unit.cpp`:1765-1786; [6] `src/map/clif.cpp`:12993-13003; [8] `db/pre-re/skill_db.yml`:165-190 |
| `combat.skill_self` | unknown | Endure is a source example, not an agent capability; basic prerequisite is Provoke5 in pinned tree. | [8] `db/pre-re/skill_db.yml`:328-347; [4] `src/map/unit.cpp`:1765-1786 |
| `combat.skill_ground` | unknown | Safety Wall is an illustrative ground skill; not part of Novice/Swordman loop and not native accepted. | [4] `src/map/unit.cpp`:2585-2626; [6] `src/map/clif.cpp`:13100-13128; [8] `db/pre-re/skill_db.yml`:450-481 |
| `combat.skill_area` | unknown | Magnum Break is self-targeted splash with Bash5 prerequisite, not a generic ground cast; no agent AoE proof. | [8] `db/pre-re/skill_db.yml`:261-301; [7] `db/pre-re/skill_tree.yml`:68-81 |
| `combat.cast_timing` | unknown | Pinned Magnum Break aftercast delay is 2000ms; universal cooldown/native scheduler behavior unverified. | [2] `src/map/skill.cpp`:8237-8275; [2] `src/map/skill.cpp`:9325-9360; [8] `db/pre-re/skill_db.yml`:294-325 |
| `combat.resource_requirements` | missing | HP/SP are projected, but learned skills, consumables/ammo eligibility and runtime cast authority are not accepted. | [2] `src/map/skill.cpp`:9593-9650; [8] `db/pre-re/skill_db.yml`:303-325; [8] `db/pre-re/skill_db.yml`:503-535 |
| `combat.status_and_map_guards` | unknown | Server checks exist; agent observation-to-action enforcement beyond inspected life/pose/transport guards is unknown. | [2] `src/map/skill.cpp`:819-870; [3] `src/map/status.cpp`:10129-10175 |
| `progression.levels` | offline_pipeline | Current source projects Novice baseline/levels; no XP-gain or growth acceptance. Snapshot is not continuously authoritative class telemetry. | [1] `src/map/pc.cpp`:8244-8278; [1] `src/map/pc.cpp`:8317-8347; [6] `src/map/clif.cpp`:3637-3657 |
| `progression.experience` | unknown | Pinned MAIN20180704 XP uses 0x0ACB long-long status branch per existing frontier; frame registration is not decoding. Native XP/loot gains remain unaccepted. | [1] `src/map/pc.cpp`:8452-8500; [1] `src/map/pc.cpp`:8317-8347 |
| `progression.stat_budget_and_spend` | missing | Delegated context says actual received point budgets are0; detailed receipt not independently located. No spendable points may be inferred from level10 or build plan. | [1] `src/map/pc.cpp`:8872-8920 |
| `progression.skill_budget_and_tree` | missing | Basic Skill has cap9; job-level growth may generate points server-side but cannot establish current unspent budget. No skill spend accepted. | [1] `src/map/pc.cpp`:9129-9177; [7] `db/pre-re/skill_tree.yml`:44-81; [15] `npc/other/Global_Functions.txt`:622-628 |
| `progression.first_job_change` | offline_pipeline | NPC source-ready only. Current progression supports Novice0; authoritative post-change class and continued first-job play remain blocked. | [9] `npc/pre-re/jobs/1-1/swordman.txt`:136-162; [15] `npc/other/Global_Functions.txt`:622-628 |
| `progression.rebirth_and_later_jobs` | unknown | Cached Valkyrie/high-Novice routes exist; enabled route, agent transitions and Renewal variants unknown. | [16] `npc/jobs/valkyrie.txt`:57-105; [16] `npc/jobs/valkyrie.txt`:140-157; [9] `npc/pre-re/jobs/1-1/swordman.txt`:41-69 |

## Minimal Novice → first-job acceptance loop
**Specification only; blocked/not executed.**
1. **Received Novice baseline:** Exact selected character/map/native epoch, fresh Novice0, received HP/SP/position and healthy transport. Unknown stats/skills/budgets stay unknown. Reject: Reject wrong identity, stale epoch, invalid levels and stale class.
2. **NPC-guided preparation:** Observed NPC, actual native dialogue/menu reaching decision context and private instructions; no blind purchases. Reject: No invented menu/quest state, SQL grants or assumed reward.
3. **Bounded encounter and recovery:** Received eligible target, matching arrival/standing, positive SELF damage and recovery receipts; demonstrate sustained survival separately. Reject: Rest holds attacks; server-forced standing is not healing; reject dead/unseen/stale targets.
4. **Earn and reconcile growth:** Received XP/next-XP or level-growth receipts plus actual available point budgets; inventory ACK if loot claimed. Reject: Hits/despawn/send counts/level10 do not prove XP, loot or unspent points.
5. **Learn Basic Skill9 legally:** Each increase uses received positive skill budget and permanent learned level; confirm new level and remaining points. Stat spending optional but requires actual nonlinear cost if exercised. Reject: Budget0 or unknown stops progress; no nine inferred points from joblevel10.
6. **Swordman exam and authoritative transition:** Follow receipt-driven exam instructions, Basic9 if basicskillcheck enabled, receive exam success and independent authoritative current Swordman class, refresh skill/level context, then one legal first-job action with native effect. Reject: NPC congratulations and LOOK_BASE alone are insufficient; Novice-only projection must not invent Swordman.

Require two consecutive future-authorized owned-fixture passes with persisted state and per-session receipts, no point/item grants. Stop at unknown prerequisites; Swordman is the bounded selected route, not all first-job routes.

## Top five gaps
- Receive exact base/bonus stats, learned skills and unspent budgets; preserve actual0 versus unknown.
- Prove received XP/level growth and inventory gain; hits do not close XP/loot acceptance.
- Exercise reviewed native NPC dialogue and receipt-guided Swordman exam; source readiness is not gameplay.
- Provide authoritative post-change class refresh beyond Novice-only baseline; appearance is not actual class.
- Repeat native survival/recovery and add guarded skill actions with timing/resource/status feedback.

## Caveats
- Official feature existence and guide advice do not establish agent behavior.
- Native movement/damage and bounded chat are historical primitive proof; XP/loot/stat/skill spending and full milestone remain unaccepted.
- Provided delegated context reports actual received point budgets0; underlying exact receipt was not independently located.
- Cached inventory has17 entries:16 successful and one failed old rebirth-path request; cached valkyrie source provides limited later-job evidence.
- Original progression frontier and survival diagnostic predate inspected current source: retention and recovery interlocks exist; native growth/recovery acceptance remains unknown.
- Negative cases are acceptance requirements, not new test executions. UNKNOWN is absent evidence; MISSING is bounded active-path/context gap, not exhaustive repository absence.
- No private configuration or enablement read; Renewal-specific rules and enabled NPC routes remain unknown.
- Initial report build failed one local line-range assertion before writing; corrected to verified file boundary, no tests/gameplay rerun.

All **16 cached successful snapshots** match stored SHA-256. Source inventory **17 entries** includes one failed collection attempt; original collection/inspect scripts not rerun.
Actual support counts: `{"missing": 4, "native_primitive_verified": 2, "offline_pipeline": 3, "unknown": 9}`. JSON contains all required fields, exact local implementation anchors, native receipt requirements, planned negatives and applicability.

## Cached sources: fetched paths and URLs
- [1] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/pc.cpp` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/src__map__pc.cpp`.
- [2] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/skill.cpp` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/src__map__skill.cpp`.
- [3] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/status.cpp` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/src__map__status.cpp`.
- [4] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/unit.cpp` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/src__map__unit.cpp`.
- [5] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/battle.cpp` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/src__map__battle.cpp`.
- [6] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/clif.cpp` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/src__map__clif.cpp`.
- [7] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/skill_tree.yml` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/db__pre-re__skill_tree.yml`.
- [8] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/skill_db.yml` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/db__pre-re__skill_db.yml`.
- [9] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/pre-re/jobs/1-1/swordman.txt` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/npc__pre-re__jobs__1-1__swordman.txt`.
- [10] `https://irowiki.org/classic/Novice` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/Novice.txt`.
- [11] `https://irowiki.org/classic/Stats` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/Stats.txt`.
- [12] `https://irowiki.org/wiki/Skills` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/Skills.txt`.
- [13] `https://irowiki.org/classic/Swordman_Job_Change_Guide` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/Swordman_Job_Change_Guide.txt`.
- [14] `https://irowiki.org/classic/Transcendent` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/Transcendent.txt`.
- [15] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/other/Global_Functions.txt` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/npc__other__Global_Functions.txt`.
- [16] `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/jobs/valkyrie.txt` — `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/combat-progression/npc__jobs__valkyrie.txt`.

Owned copied ledger: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/recovery-combat-progression/citations.json`. Original ledger/cache untouched. Local implementation anchors are present in JSON and copied ledger.
