# Social / party / guild / WoE — recovered coverage audit

20 finite feature rows; 14 original cached sources hash-verified. Active authority: `e985006171d2eb320ee512a653f4c83aea3d81b6`, `MAIN20180704/pre-renewal, obfuscation absent`.

## Outcome and evidence boundary

Native primitive evidence is limited to fresh public A→B chat relay and exact party invitation/acceptance in two smoke passes. The second records two persistent prior party members without reseed/reset. Neither report accepts full milestones. No autonomous useful social/group play, relationship/reputation/gossip, native guild, siege or competitive behavior is accepted here.

Evidence: `run/reviews/two-bot-first-native-limbs.json:4–13`; `run/reviews/two-bot-second-native-limbs.json:4–23`.

The supplied 4,177-test +65-subtest /95.37% source gate is not gameplay. No new tests, network requests, collection scripts or runtime effects were performed. This is a new recovery artifact; the interrupted original batch is not claimed successful.

## Top five gaps

1. Recipient- and epoch-bound private channel/roster receivers, including whisper and party/guild delivery.
2. Useful coordinated group behavior: legal support-skill actions, fresh ally telemetry, roles, regroup and effective heal/buff receipts.
3. Witness-bound contribution schema and native bridge; recipient identity, damage/heal/buff effect and sequence provenance before scoring.
4. Private relationship persistence and gossip learned only by actual recipients, not shared score-store/log shortcuts.
5. Native guild lifecycle/permissions/storage/alliance foundation before configured WoE/PvP/BG objectives.

## Observability and private relationships

Treat received event source, recipient, damage/heal/buff outcome, map and epoch/sequence as evidence, not omniscience. HumanContribution currently lacks recipient/skill/epoch/sequence provenance. ReputationStore and HumanTracker group propagation/logs are offline policy, not native gossip delivery. Each learner must witness an interaction or receive attributed hearsay; unrelated agents stay unchanged. Hidden member XP, private inventory, whole-world facts and missing observations cannot become public knowledge or certainty of bad play. Skill animations alone do not prove useful healing/buffing; require applicable success plus observed effect. WoE damage presentation can conceal or transform amounts. [Implementation: `src/robots/society/human.py:48–98,109–129`; `src/robots/society/society.py:109–159`; [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:6163–6210]]

## Ruleset and applicability frontier

Classic party advice uses a 10-level sharing window and says item modes require remaking; Renewal iRO advice uses 15 and iRO-specific bonuses. Pinned option changes and char-server party_share_level checks take authority; effective local share values remain unknown. Classic guild guide forbids master transfer while pinned guild_gm_change exists. Native availability depends on permissions/config/client support, not guide prose. Storage depends on PACKETVER rights and optional OFFICIAL_GUILD_STORAGE. WoE schedules, castles, siege restrictions and BG activation are local-script/config unknowns; no private config was read. Class-specific skill formulas and legality remain with the separate class audit.

[S1: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-1.txt:9–18] [S2: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-2.txt:20–24] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:877–940] [S14: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-14.txt:339–342] [S3: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-3.txt:37–42] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:2193–2238] [S12: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-12.txt:556–613]

## Requirements matrix

Every positive receipt below is a future acceptance criterion unless explicitly marked existing. All negative tests are proposed guard cases, not newly executed tests. Tier names describe inspected bounded implementation support, not server feature existence.

### `social.public_chat` — Local public chat and recipient isolation
**Tier:** `native_primitive_verified` · **Priority:** P0
- **Observe:** Received named speaker/text, map/area and session sequence; self echo is not peer delivery.
- **Legal actions:** Say on local public channel, with pacing and byte limits.
- **Prerequisites:** Selected native speaker identity; healthy epoch; know room/channel routing.
- **Positive receiver/state acceptance:** A sends fresh exact text; nearby B receives it; out-of-area C does not.
- **Existing receipt:** Both native smoke reports say fresh A chat relayed to B; no public isolation test receipt.
- **Negative guards (not run):** Spoofed speaker, NUL/UTF-8 overflow, echo-only, muted/rate-limited send, stale epoch.
- **Gap:** Native relay exists, not autonomous helpful conversation or routing coverage.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `spikes/003-clientless-limbs/client.py:608–630`
- **Cached citations:** [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:11511–11543]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `social.whisper` — Private whisper with rejection semantics
**Tier:** `missing` · **Priority:** P0
- **Observe:** Exact recipient name, delivered text, ACK success/offline/ignored; visibility belongs only to actual recipients.
- **Legal actions:** WhisperTo exact named recipient; stop on refusal.
- **Prerequisites:** Native whisper encoder/receiver and ACK correlation; identity and privacy boundary.
- **Positive receiver/state acceptance:** B receives A whisper; A receives correlated ACK; unrelated C memory remains unchanged.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Offline/nonexistent target, ignore/all-ignore, spoofed sender, unrelated agent inspection, duplicate ACK.
- **Gap:** Domain WhisperTo exists but active native _social falls through to unsupported action; no whisper receipt.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`
- **Cached citations:** [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:11861–11976]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `social.chatrooms` — Player chatrooms, consent and room lifecycle
**Tier:** `missing` · **Priority:** P2
- **Observe:** Visible room ID/title/public flag and occupancy; actual join/failure and membership notifications.
- **Legal actions:** Create/join/leave owned or consented room; owner changes only with rights.
- **Prerequisites:** Room packet/action codecs and scoped native membership tracker; never bypass passwords.
- **Positive receiver/state acceptance:** Joiner receives join success, occupants receive join notice, and only room members receive room chat.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Wrong password, full room, wrong map, vending/already joined, level/zeny restrictions, kicked user.
- **Gap:** No chatroom action in inspected GameAction/native dispatcher; current support beyond these seams unknown.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`
- **Cached citations:** [S11: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-11.txt:77–182] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:11520–11535]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `social.emotes` — Observable emotes without invented intent
**Tier:** `missing` · **Priority:** P2
- **Observe:** Received actor ID and emotion code in actual visible area.
- **Legal actions:** Send valid paced emote; interpret as weak communication, not ground-truth intent.
- **Prerequisites:** Profile-specific encoder/receiver and actor identity binding.
- **Positive receiver/state acceptance:** Nearby B receives A emote; off-area C sees nothing and no affinity is fabricated.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Unknown emote, stale actor, spoofed ID, flood, treating gesture as proof of contribution.
- **Gap:** No emote action in inspected active action surface; no native emote receipt.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`
- **Cached citations:** [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:11625–11675]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `social.friends` — Native friends list versus social affinity
**Tier:** `missing` · **Priority:** P2
- **Observe:** Received friend request, consent outcome, list and online notifications only as exposed.
- **Legal actions:** Request, accept/decline or remove friendship with explicit consent.
- **Prerequisites:** Native friend packets and exact AID/CID mapping; affinity independent of native list.
- **Positive receiver/state acceptance:** Both consenting characters receive matching list updates; removal updates both.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Decline, full list, duplicate/self request, nonexistent player, consent timeout, stale list.
- **Gap:** SocialGraph seeded affinity is offline_model, not server-side friends-list membership or private consent.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/society/society.py:69–179`
- **Cached citations:** [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:15434–15580]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `social.private_relationships_gossip` — Private relationships and received, attributed gossip
**Tier:** `offline_model` · **Priority:** P0
- **Observe:** Own witnessed interactions; received statements retain sender, channel, sequence, hearsay confidence and provenance.
- **Legal actions:** Update only witnessing agent relationship; gossip by actually delivered chat, independently received by listener.
- **Prerequisites:** Agent-isolated durable memory, identity-scoped contribution events, native channel receipt and uncertainty handling.
- **Positive receiver/state acceptance:** A changes relationship after witnessed help; B changes only after receiving A statement; isolated C unchanged; restart preserves only rightful private history.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** No whole-world broadcasts, group-store shortcut, human-name collision, repeated/looped gossip, unsupported accusation, unreceived message.
- **Gap:** HumanTracker propagates group scores directly and logs prose; that is not native delivered gossip or recipient-private learning.
- **Implementation:** `src/robots/society/human.py:48–98`; `src/robots/society/society.py:69–179`; `src/robots/society/human.py:109–129`
- **Cached citations:** [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:11525–11535] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:11966–11976] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:1101–1120]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `social.observable_contribution` — Witness-bound contribution and reputation
**Tier:** `offline_model` · **Priority:** P0
- **Observe:** Received source/recipient identity, target, damage/heal/buff success, local map, own epoch/sequence/time and encounter participation; missing facts unknown.
- **Legal actions:** Score bounded witnessed evidence only; attribute hearsay separately; do not turn incomplete views into blame.
- **Prerequisites:** Native event-to-HumanContribution bridge; richer witness/recipient/skill/sequence schema; deduplication and effect confirmation.
- **Positive receiver/state acceptance:** B observes attributable useful hit or effective heal/buff and updates only its own evidence-backed score; uninvolved C learns nothing.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Overheal/no-op/failed buff, packet replay, stale actor, missing recipient, hidden XP/loot, death without context, invented kill-steal or dead-weight verdict.
- **Gap:** HumanContribution has human/kind/magnitude/map/time but no receiver, skill, epoch or sequence; no native witness-to-score receipts. Visible damage can be transformed/hidden and is not universal server damage truth.
- **Implementation:** `src/robots/society/human.py:48–98`; `src/robots/society/society.py:69–179`; `src/robots/adapters/native_gameplay.py:90–146`
- **Cached citations:** [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:5236–5320] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:6163–6210] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:8095–8115]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `party.membership` — Party creation, invitation and exact acceptance
**Tier:** `native_primitive_verified` · **Priority:** P0
- **Observe:** Received party ID, pending invitation source, exact recipient and current roster.
- **Legal actions:** Create legal named party; leader invites; recipient accepts or declines current invite.
- **Prerequisites:** Native Basic Skill eligibility, capacity, no existing party, map/instance locks and inviter rights.
- **Positive receiver/state acceptance:** Exact invitee accepts matching current party and both receive consistent membership.
- **Existing receipt:** Both smoke reports verify fresh exact recipient accepted; second records two prior persistent members, without reseed/reset.
- **Negative guards (not run):** Forged/stale invite ID, wrong recipient, already joined, full party, nonleader, refused invite, reconnect.
- **Gap:** Primitive verified; autonomous intent/consent, complete fail-closed roster lifecycle and useful play remain open. Guides differ on join prerequisites; pinned native checks win.
- **Implementation:** `spikes/003-clientless-limbs/client.py:608–630`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/app/playing_runtime.py:559–562`
- **Cached citations:** [S1: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-1.txt:6–7] [S2: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-2.txt:2–4] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:144–194] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:383–470] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:571–616]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `party.leadership` — Party leader transfer, kick/leave and roster lifecycle
**Tier:** `missing` · **Priority:** P1
- **Observe:** Current received leader/roster, departure/kick/transfer outcomes and freshness.
- **Legal actions:** Leader transfers/removes only legal member; self leaves; do not infer authority from local group ownership.
- **Prerequisites:** Native roster/action support; configured same-map/instance constraints; explicit consent for transfer.
- **Positive receiver/state acceptance:** Both members receive new leader; old leader can no longer issue restricted changes; leave clears current membership.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Nonleader kick/transfer, target outside roster, stale leadership, wrong-map/instance lock, disconnect and disband.
- **Gap:** Membership boolean and invite primitives are not a leadership/roster state machine; no native lifecycle receipt.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/app/playing_runtime.py:559–562`
- **Cached citations:** [S2: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-2.txt:5–9] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:699–728] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:759–799] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:940–1003]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `party.chat` — Party channel recipient-bound coordination
**Tier:** `offline_pipeline` · **Priority:** P0
- **Observe:** Received party sender/text and current party identity, distinct from public chat.
- **Legal actions:** PartyChat only with current membership; confirm delivery before relying on instructions.
- **Prerequisites:** Profile encoder exists; receiver/channel classification, membership freshness and correlation still needed.
- **Positive receiver/state acceptance:** B in same party receives A plan; outsider C does not; no public fallback leaks.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Not in party, old party/session, forged speaker, UTF-8 overflow, self echo only, private channel misclassification.
- **Gap:** Native send branch and encoder exist; inspected smoke receipts prove public chat, not party chat delivery or useful coordinated action.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/adapters/native_gameplay.py:48–62`
- **Cached citations:** [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:1101–1120] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:8041–8080] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:13970–13978]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `party.xp_share` — Configured EXP sharing and individual observed gains
**Tier:** `missing` · **Priority:** P1
- **Observe:** Received share mode, roster/levels where exposed and SELF XP changes; other members XP unknown unless personally received or reported.
- **Legal actions:** Authorized leader requests share mode; eligible members fight on valid map.
- **Prerequisites:** Current mode/level bounds and server party_share_level, idle/share settings; no iRO default assumed.
- **Positive receiver/state acceptance:** Each eligible participant gets its own SELF XP delta after shared kill; leader receives actual option acceptance.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Level bound exceeded, dead/off-map/idle member, share refused, family exception, lost frame, fabricated other-member XP.
- **Gap:** No native party-option action or shared-XP receipt. Classic 10 versus iRO Renewal 15/bonus claims are guide variants; effective server value unknown.
- **Implementation:** `src/robots/app/playing_runtime.py:360–376`; `src/robots/adapters/native_gameplay.py:115–146`
- **Cached citations:** [S1: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-1.txt:15–18] [S2: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-2.txt:20–24] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:877–940] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:1238–1294] [S14: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-14.txt:339–342]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `party.loot_share` — Pickup priority and actual loot recipient
**Tier:** `missing` · **Priority:** P1
- **Observe:** Received floor item, share/pickup modes, own acquisition and member-reported receipts only.
- **Legal actions:** Pick up legal floor item under current ownership/party distribution; never assign beneficiary from send request.
- **Prerequisites:** Mode readback, item ownership/capacity and fresh floor identity; configured random/round-robin authority.
- **Positive receiver/state acceptance:** Actual beneficiary receives inventory acquisition; pickup disappearance alone does not identify winner.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Wrong priority, off-map/dead/idle, full inventory, expired floor item, mode change, duplicate receipt.
- **Gap:** Solo pickup encoder/tracker does not prove party distribution, mode support or native loot gain. Classic remake-only advice differs from pinned option-change implementation.
- **Implementation:** `src/robots/app/playing_runtime.py:378–390`; `src/robots/adapters/native_gameplay.py:129–146`
- **Cached citations:** [S1: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-1.txt:9–14] [S2: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-2.txt:13–19] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:1298–1365]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `party.role_coordination` — Useful roles, follow/regroup, healing and buffing
**Tier:** `offline_model` · **Priority:** P0
- **Observe:** Only received member HP/location/death, legal learned skills/SP/range, targets and attributable effects; unavailable member state unknown.
- **Legal actions:** Agree roles and target; follow observed positions; eligible class casts learned legal support skill; withdraw or regroup safely.
- **Prerequisites:** Fresh party roster/telemetry, legal class skill action and effect decoder; class-specific mechanics belongs to separate audit.
- **Positive receiver/state acceptance:** Two agents carry out a received plan; defender damages real target, healer improves injured member HP or applied buff state; group then regroups after death/loss.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Out-of-range/hidden/dead member, absent skill/SP, overheal, failed/already-active buff, stale position, unsafe pursuit, group loss and solo outsider.
- **Gap:** Social intent/model is not execution: no support-skill GameAction, no useful role/heal/buff group receipt; damage smoke evidence cannot close this row.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/app/brain.py:407–439`
- **Cached citations:** [S1: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-1.txt:7–7] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:1122–1160] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:8095–8138] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:6163–6210]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `party.recruitment` — Consent-based recruitment and optional party booking
**Tier:** `unknown` · **Priority:** P1
- **Observe:** Actual local replies/whispers; booking results only if native interface enabled; advertised class/role not verified skill telemetry.
- **Legal actions:** Advertise bounded need; negotiate goal and role; invite consenting compatible player; stop listing when complete.
- **Prerequisites:** Channel privacy, role legality and current eligibility; booking packets/config separate from chat recruitment.
- **Positive receiver/state acceptance:** Recipient receives advert, agrees role, joins intended party and performs first useful coordinated action.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Spam, ignored refusal, incompatible level/role, stale listing, changed party, treating recruitment send as acceptance.
- **Gap:** Generic invite/chat available; actual recruitment behavior and optional booking support/config not verified.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/app/brain.py:407–439`
- **Cached citations:** [S2: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-2.txt:61–70] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:13993–14128] [S7: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt:541–569]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `guild.creation_membership` — Native guild creation, invitations and membership
**Tier:** `offline_model` · **Priority:** P1
- **Observe:** Received guild creation result, guild ID/master and member invitation/roster, not synthetic registry IDs.
- **Legal actions:** Create eligible named guild, consume required Emperium if enabled; authorized invite and explicit accept/leave.
- **Prerequisites:** Emperium policy, available inventory, rights/capacity, clan and map/instance restrictions.
- **Positive receiver/state acceptance:** Server returns native guild ID/master, inventory cost where applicable, then both characters receive accepted membership.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** No Emperium, already member, invalid name, full guild, no permission, noask, clan, stale/forged invite.
- **Gap:** GuildRegistry creates synthetic guild-NNN values; no native creation/membership action or receipt. Effective guild_emperium_check unknown.
- **Implementation:** `src/robots/society/guild.py:32–104`; `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`
- **Cached citations:** [S3: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-3.txt:19–30] [S4: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-4.txt:4–16] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:689–744] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:925–1071]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `guild.roles_progression_chat` — Guild permissions, titles, tax/skills and guild chat
**Tier:** `offline_model` · **Priority:** P2
- **Observe:** Received title/permissions, guild XP/skill points/notices and member-channel text; tax records only if actually delivered.
- **Legal actions:** Authorized rank/notice/tax changes and legal skill investment; member-only guild chat; leadership transfer only where server/client permit.
- **Prerequisites:** Native guild UI packet equivalents; master/position checks, effective caps and client feature support.
- **Positive receiver/state acceptance:** Member receives guild chat/notice and new rights; controlled action fails before rank grant and succeeds after; actual taxed SELF/guild progression observed.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Nonmaster edits, illegal tax/skill points, stranger receives chat, stale role, unauthorized kick, importing guide-only master immutability.
- **Gap:** Pure guild model has no native roles/XP/skills/chat; Classic guide says no master transfer, but pinned guild_gm_change exists—effective runtime/client support unknown.
- **Implementation:** `src/robots/society/guild.py:32–104`; `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`
- **Cached citations:** [S3: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-3.txt:24–51] [S4: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-4.txt:10–36] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:1462–1559] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:1728–1753] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:2193–2238] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:2640–2648] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:14334–14383] [S9: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt:14586–14600]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `guild.alliances` — Native guild alliance/opposition and safe target identity
**Tier:** `missing` · **Priority:** P2
- **Observe:** Received native alliance/opposition outcome and guild affiliation; avoid presumed friend-group alliances.
- **Legal actions:** Authorized master requests/accepts/removes permitted alliance; respect WoE and capacity locks.
- **Prerequisites:** Native guild membership and exact guild IDs, master rights, max alliances and effective WoE state.
- **Positive receiver/state acceptance:** Both guilds receive accepted alliance; authorized removal updates both; ally targeting remains refused in applicable GvG context.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Same guild, wrong rights, no target guild, max alliance, active WoE request, stale alliance and opposition confusion.
- **Gap:** No native alliance action/receipt; SocialGraph friendship does not establish combat ally status.
- **Implementation:** `src/robots/society/guild.py:32–104`; `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`
- **Cached citations:** [S3: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-3.txt:26–26] [S5: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-5.txt:47–47] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:1853–1988] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:2630–2648] [S13: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-13.txt:8143–8169]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `guild.storage` — Guild storage permissions, locking and item custody
**Tier:** `missing` · **Priority:** P2
- **Observe:** Received authorized open/list/count and item transfer results; only actual storage session exposes contents.
- **Legal actions:** Open through legal NPC/interface; authorized deposit/withdraw and close; never access another guild/private inventory.
- **Prerequisites:** Native guild/permission, PACKETVER storage checks, OFFICIAL_GUILD_STORAGE skill variant, lock/capacity/bound-item policy.
- **Positive receiver/state acceptance:** Depositor sees own inventory decrement and storage increment; authorized withdrawer later receives exact item and storage decrement after release.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** No guild/right, other session lock, storage skill disabled/missing, full storage, bound/expiring item, stale amount and double withdraw.
- **Gap:** No native storage GameAction/receipt; effective storage skill flag and capacity unknown; generic guild model is not custody.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/society/guild.py:32–104`
- **Cached citations:** [S4: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-4.txt:15–16] [S12: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-12.txt:556–613] [S12: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-12.txt:732–785]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

### `competitive.woe` — WoE attendance, siege roles and castle outcome
**Tier:** `offline_model` · **Priority:** P3
- **Observe:** Actual event/map/GvG state, native guild/alliance identity, visible objective/defense and received ownership change; damage may be hidden.
- **Legal actions:** Attend enabled authorized window; perform legal siege roles and attacks; obey ally protection, skill restrictions and capture state.
- **Prerequisites:** Native guild and approval skill, configured castle scripts/windows/GvG mechanics, travel/supplies, legal support roles.
- **Positive receiver/state acceptance:** Authorized guild actually enters active siege, cooperates, and receives objective/castle ownership state; a calendar attendance tuple alone fails.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** Outside window, no guild/approval, attacking ally, unavailable castle/script, illegal skill, guide schedule import, hidden-damage ranking, death/reentry.
- **Gap:** WoeCalendar/WoeParticipation are offline weekly policy; no native siege/castle receipt. iRO schedules, damage reductions, disabled skills and edition-specific scripts are not effective local config.
- **Implementation:** `src/robots/society/guild.py:107–217`; `src/robots/society/guild.py:32–104`; `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`
- **Cached citations:** [S5: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-5.txt:19–22] [S5: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-5.txt:44–76] [S6: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-6.txt:16–19] [S6: /home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-6.txt:47–81] [S8: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt:2532–2608] [S13: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-13.txt:8143–8169]
- **Applicability:** pre_renewal: WoE candidate only if castle/NPC scripts and schedule enable it; Classic guide mechanics advisory.; renewal: Different guide details and WoE2/TE variants; no inherited activation or receipts.; unknown: Effective schedule, castles, siege reductions, skill-disable tables and objective mechanics not fully audited; other class report owns skill legality.

### `competitive.pvp_battlegrounds` — PvP legality and Battleground queue/team/objectives
**Tier:** `missing` · **Priority:** P3
- **Observe:** Received map mode/flags where exposed, actor/team identity, queue rejection/readiness/team assignment and objective result.
- **Legal actions:** Fight only eligible enemy in enabled PvP/GvG/BG context; legally queue, accept, cooperate, respawn/leave.
- **Prerequisites:** Configured mode/NPC/queue availability and level/class constraints; native player target policy and BG team state.
- **Positive receiver/state acceptance:** PvP opponent receives attributable damage in legal arena; BG participants receive actual team assignment, cooperative objective result and exit—not normal PvE hits.
- **Existing receipt:** None established by inspected receipts; requirement not executed in this recovery.
- **Negative guards (not run):** PvE player attack, ally/same BG team, PK novice/level limits, invalid class/level, duplicate queue/team, timeout/desertion and disabled mode.
- **Gap:** Current attack targeting is bounded PvE; no native PvP/BG behavior, player-combat eligibility bridge or team objective support. BG service/script activation remains unknown.
- **Implementation:** `src/robots/domain/actions.py:22–45`; `src/robots/app/playing_runtime.py:360–376`; `src/robots/adapters/native_gameplay.py:1–11`
- **Cached citations:** [S13: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-13.txt:7869–7905] [S13: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-13.txt:8143–8200] [S10: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-10.txt:523–567] [S10: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-10.txt:630–657] [S10: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-10.txt:924–960] [S10: /home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-10.txt:999–1092]
- **Applicability:** pre_renewal: Candidate under MAIN20180704 pinned server; effective config and fresh native state still govern.; renewal: Separate candidate; do not inherit iRO rates, guide assumptions or native acceptance.

## Original source ledger / provenance

Original `sources-ledger.json` and all 14 retrieval-manifest records are embedded unchanged in JSON. Hashes match original cached bytes. Wiki source author is the iRO Wiki community, not a claim of official Gravity authorship; rAthena source is commit-pinned mechanics authority. Cached access date is inherited (2026-10-08), not a new fetch. Initial certificate verification failures remain in the original manifest. Wiki citations address bounded derived article excerpts in recovery scratch with revision IDs, original HTML lineage and excerpt hashes; no source cache was modified.

- **S1** Party; author/source: iRO Wiki community-authored server-specific guide, advisory only; original URL: `https://irowiki.org/classic/Party`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-1.txt`; SHA256 `5e7cb8d8c1f5aee8fae056fddef4ca744014cda68824bfe39ebcb0e31401b62b`; wiki revision 25894; excerpt `/home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-1.txt`
- **S2** Party; author/source: iRO Wiki community-authored server-specific guide, advisory only; original URL: `https://irowiki.org/wiki/Party`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-2.txt`; SHA256 `c944b6f230ee48062b89c7377a18f7f0d2de53d6e5546f09a6b9e3b85782a280`; wiki revision 60408; excerpt `/home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-2.txt`
- **S3** Guild_System; author/source: iRO Wiki community-authored server-specific guide, advisory only; original URL: `https://irowiki.org/classic/Guild_System`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-3.txt`; SHA256 `b5c1d2eec93be34a04eb0b8b2a8af836b7b32e85930deb5e1a914ffd5f214011`; wiki revision 25192; excerpt `/home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-3.txt`
- **S4** Guild_System; author/source: iRO Wiki community-authored server-specific guide, advisory only; original URL: `https://irowiki.org/wiki/Guild_System`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-4.txt`; SHA256 `cafd699aeed8184f6f38437269f1d35a6549274957aa0babc70c0bbf617f937d`; wiki revision 86614; excerpt `/home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-4.txt`
- **S5** War_of_Emperium; author/source: iRO Wiki community-authored server-specific guide, advisory only; original URL: `https://irowiki.org/classic/War_of_Emperium`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-5.txt`; SHA256 `4875f714706abfd1fff1bb95a99ca15c08d2d1fb4bb194f62da429553514bb1d`; wiki revision 27780; excerpt `/home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-5.txt`
- **S6** War_of_Emperium; author/source: iRO Wiki community-authored server-specific guide, advisory only; original URL: `https://irowiki.org/wiki/War_of_Emperium`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-6.txt`; SHA256 `b5d7af9e794f59b1f77d17b748798069ce471135c94d673ddde47548f70b9de5`; wiki revision 85058; excerpt `/home/otto/.hermes/cache/scratch/recovery-social-guild-woe/cached-wiki-excerpt-6.txt`
- **S7** party.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/party.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-7.txt`; SHA256 `5a87d5e1ce5260145aa7dc7b5dd3f0a9c878c05c2f20d8e7db893b38a723d75f`
- **S8** guild.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/guild.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-8.txt`; SHA256 `15d1f4eb3d37129685aa68842f6892eebd460e09077423bac9b0b3850de538f4`
- **S9** clif.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/clif.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-9.txt`; SHA256 `0b1db098158c240b090c6edb8417978ba495957c8a2df4cd9a0ab4cb39884ac5`
- **S10** battleground.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/battleground.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-10.txt`; SHA256 `5c9b8b163aef9837fcd6a3897811716e30d05d33fbf4ebf9e3cf6c0cbcec1038`
- **S11** chat.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/chat.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-11.txt`; SHA256 `0410b3f6a7a919ee813ec8f50fb9af00af8bbb69eb70a426b35d5ba7f9e93823`
- **S12** storage.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/storage.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-12.txt`; SHA256 `b66a2a85f062966b1cc9aab2a54401f45c0c53b11a712ffe88e6caa1fb4605f8`
- **S13** src/map/battle.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/battle.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-13.txt`; SHA256 `26b32fe653933cede710edf9e48d3fa8a85dc88f0936b93632d00a03ad572578`
- **S14** src/char/int_party.cpp; author/source: rAthena pinned public implementation; original URL: `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/char/int_party.cpp`; cached `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/social-guild-woe/source-14.txt`; SHA256 `42391c6c96d39dcd7510a724fa0cf9b269d048e8d979b4df479228a9423d6afc`

## Verification

JSON has exactly 20 unique feature IDs, all research-scope required fields, valid source line ranges and all 14 original source hashes checked. No row claims native_behavior_verified. Source-readiness gates and future native acceptance requirements remain separate. Effective local optional-feature configuration and sustained multi-agent behavior are still unverified.
