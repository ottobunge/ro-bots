# ro-bots Wiki Index

> Design records and concept docs. ADRs in `decisions/` are normative and drive the code.
> Last updated: 2026-10-12
> Implementation acceptance is tracked in [[goals-ledger]]; mock tests are not live-world proof.

## Decisions
- [[adr-021-llm-planning-clef-execution]] — accepted subgoal11: LLM investigates
  permitted context and authors plans; CLEF executes/escalates, scripts remain
  mechanical. Overrides historical plan-authorship only; implementation OPEN.
- [[adr-000-hexagonal-architecture]] — ports & adapters; app core depends only on ports
- [[adr-001-event-driven-brain]] — scripts execute; Clef fires on events/reviews, never per tick
- [[adr-002-randomized-timers]] — time-based triggers with random delays (5–20 min class)
- [[adr-003-farm-plans]] — Clef authors farming sessions (duration, target mobs, interrupt rules)
- [[adr-004-isolated-agents-optchat-memory]] — per-agent OptChat memory: append-only log,
  summary tree, fixed-size view, zoom; schedules as experiences
- [[adr-005-society-groups-reputation]] — personas, friend groups + overlapping schedules,
  solo outsiders, SocialGraph affinity, human reputation with damped propagation
- [[adr-006-clef-context-selector]] — Clef ranks memory-line relevance (one pass, ≤64
  score questions) to pick the context view on busy ticks; tree-cover stays the default
- [[adr-007-rust-dashboard]] — Rust dashboard (Dioxus LiveView on Axum; no WASM) consuming
  a WorldFeed SSE/JSON contract; roster, live feed, agent inspector views
- [[adr-008-dashboard-control-plane]] — dashboard grows configurator (counts, ranges,
  generate), persona editing, force-action commands, character tracker; write path via
  a Command API on the WorldFeed contract; local Docker deployment
- [[adr-009-character-builds-item-cognition]] — agents author builds (class path, stats,
  skills, equip goals) via Clef; MechanicsPort pre-calculates item/skill digests so
  item decisions (equip/store/sell) are one Clef pass over normalized comparisons
- [[adr-010-worlds-volumes-e2e]] — debug/test/prod-NAME worlds on isolated volumes;
  `task e2e` wipes+seeds the test world, runs scheduled bots with real brains and
  asserts goal-directed behavior; `KEEP=1` playground mode
- [[adr-011-decision-runtime-strategy]] — spike 001 verdict: Clef-Flash on CPU is
  ~65s/decision (LCP-warm: 0.94s) → Clef becomes the amortized planner (Tier 3);
  reflexes via scripts + rule-based triage (Tiers 1-2); Qwen chat ~2s (Tier 4);
  prefix-stable serialization + DecisionModel port keep remote Clef swappable

## Concepts

- [[completion-roadmap]] — seven-point finite delivery roadmap, current subpoint,
  parallel worker lanes and the hourly verified status-report contract.

- [[optchat-definition-update-2026-10-08]] — current UniiChat revision pinned;
  four real cache/coverage/UTF-8 failures reproduced in our legacy RO memory,
  core/provider compatibility and safe adoption audits running; no compliance claim

- [[gameplay-coverage-roadmap]] — 104 candidate gameplay requirements across five
  recovered audits; explicit support tiers, received-state gaps and finite native
  acceptance order, not a claim of complete gameplay or server enablement

- [[public-rules-knowledge-pilot]] — working four-card ruleset-tagged offline
  advice lookup with provenance/UTF-8 budgets; 28 parent tests, live wiring open

- [[native-mechanics-and-encounter-context]] — criteria 9/10 source-to-request
  gaps; observed species/hit/encounter-level component first, native stat/skill/gear
  retention and legal actuation still open; public knowledge is advisory

- [[native-packet-manifest]] — accepted compiler-derived catalogue goal; full-header
  probe succeeds, generator rejected after two repairs, runtime/gameplay unaccepted
- [[native-packet-manifest-review-blocker]] — final compiled counterexamples;
  automatic repairs exhausted, architectural direction required
- [[native-packet-ast-spike]] — newly authorized offline AST/hybrid experiment;
  compiler-profile and bounded identity/mutation feasibility, no runtime migration
- [[native-packet-tracer-callback-trial]] — offline tracer candidate/quality
  independently approved; scratch callback qualification separately bounded
- [[native-packet-sink-closure]] — conditional AREA/SELF source facts independently
  verified; ownership/lifetime invariants unresolved and sink not adopted
- [[native-callback-package-plan]] — separate offline callback-qualified package
  independently approved; deployment/runtime/world changes excluded
- [[native-qualified-catalogue-readiness]] — independently approved bounded offline
  layout/validator snapshot and receiver gaps; no runtime registration
- [[native-qualified-catalogue-review-history]] — preserved initial integration
  and independent rejection/repair checkpoints; not current authorization

- [[matched-playing-provider-latency]] — matched eleven-question timing succeeds on
  all three providers after the schema repair; isolated hardware/offload and
  population-scale validation remain open

- [[adr-012-benchmark-framework]] — common workload and explicit latency/batch measurements
- [[adr-013-durable-agent-journals]] — private raw-experience persistence and restart boundary;
  see the host integration addendum for the newer offline checkpoint
- [[adr-014-host-memory-integration]] — proposed shared host/brain/inspector ownership,
  isolated Clef/LLM context, poisoned-writer semantics, and unfinished failure cleanup
- [[adr-015-host-owned-operator-commands]] — accepted offline host-owned public-chat
  delivery only; Rust/browser/native delivery and other command slices remain open
- [[adr-016-private-runtime-before-world-launch]] — proposed offline private runtime
  preparation before separately guarded and authorized world launch
- [[adr-017-default-suppressed-public-bootstrap]] — accepted offline public SQL derivation,
  exact default-account suppression and quarantine rather than presumed rollback
- [[playable-rathena-package]] — separate runnable native package/Docker archive;
  independent artifact review accepted260 cases/15 matched inputs; native startup pending
- [[native-self-progression]] — reviewed offline selected-row/returned-CID binding
  and SELF level retention; historical snapshot is not current-class authority,
  native receipt and continuous freshness remain unverified
- [[native-host-vitals]] — reviewed fail-closed host vitals and self-chat; bounded
  two-fixture native HP/SP receipt/projection/cleanup verified, cognition still off
- [[scheduled-native-host-idle]] — actual two-fixture real-time host sessions and
  fresh-process private session-journal replay verified; idle-only/inference off,
  production named-volume storage and real cognition remain unaccepted
- [[two-bot-live-limbs]] — two authorized non-GM native fixtures; two four-action
  smoke passes, actual required PIN/success frames and shared-party readback;
  movement arrival/persistence and all full milestones remain open
- [[first-live-native-world]] — actual isolated healthy database and connected native
  roles;1265 maps/13036 NPCs loaded, character login/gameplay still pending
- [[simple-world-compose]] — ordinary projects/named volumes and Taskfile routing;
  real configuration rendering verified, runtime/import/startup still pending
- [[adr-019-simple-volume-world-isolation]] — current user clarification:
  ordinary Compose projects and separate volumes, no custom workspace prerequisite
- [[adr-020-pinned-protocol-gameplay-first]] — accepted pinned/manual protocol
  maintenance and practical two-bot gameplay gate; qualified test-only deployment
- [[adr-018-trusted-user-local-workspace]] — user-selected existing rootless setup,
  same-user programs trusted; cooperative staging policy, not world authorization
- [[decision-flow]] — mermaid map of the whole loop: events, scripts, Clef, LLM escalation
- [[escalation-policy]] — when a decision leaves Clef and reaches the LLM
- [[recovery-validation]] — recovery evidence: full Python gates, repeated native
  four-limb passes, service health, and explicit remaining acceptance gaps
- [[renewal-build-research]] — separate provisional Renewal archetypes with pinned
  item/skill evidence, episode/rebalance boundaries, and explicit adoption gaps
- [[test-world-inventory]] — fixed-scope read-only engine inventory and its explicit
  nonauthorization boundary; no provisioning/reset executor
- [[rathena-nix-package]] — independently accepted offline native package/Docker
  archive only; launch blocked, runtime/NPC/bootstrap work remains
- [[private-rathena-runtime]] — actual offline private NPC/db/config bundles;
  seven exact patterns closed, publication/construction residuals open;
  replacement contract proposal precedes any additional repair
- [[rathena-db-nix-image]] — actual pinned MariaDB package/Docker archive;
  artifact checks passed, overall review withheld for historical scope violation
- [[public-rathena-bootstrap-assets]] — actual default-suppressed pinned SQL and
  schema/engine manifest; independently accepted for offline derivation only
- [[isolated-rathena-bootstrap-frontier]] — pinned schema/import/cache and launch
  authority requirements; no SQL execution, provisioning or reset approval
- [[runtime-publication-contract]] — proposed controlled-workspace staging,
  explicit commit/receipt and quarantine semantics; not implemented or approved
- [[runtime-publication-io]] — accepted source-only nonreplacing move helper;
  exact-string bypass closed, no durability/receipt/admission integration
- [[runtime-tree-sync]] — actual borrowed-FD bottom-up synchronization helper;
  final independent40+41 probes pass; accepted for synchronization only,
  no publication/admission integration
- [[runtime-publication-journal]] — accepted data-only journal/cleanup observation;
  independent223 cases/23 inputs matched, no release/recovery/world authority
- [[native-runtime-root]] — real three-role offline ELF directory diagnostics;
  parent133 tests and independent133+207 probes pass; accepted for the
  offline directory diagnostic only, all startup still refused
- [[classic-paladin-build-evidence]] — candidate stage-aware shared skill-pool,
  equipment identity and acquisition research; core independently supported
- [[classic-paladin-acquisition-addendum]] — missing MVP reward and quest/reset
  precision corrections; original evidence preserved, no executable approval
- [[persistent-summary-cache]] — accepted optional offline summary-node port;
  independent210 cases/15 hashes matched; host wiring separately accepted offline
- [[host-summary-cache]] — accepted optional offline host/CLI cache wiring;
  independent330 cases/30 inputs matched, native/provider acceptance pending
- [[playable-world-acceptance]] — criterion8's six required milestones, evidence
  boundaries and the initial small-population end-to-end scenario
- [[goals-ledger]] — living checklist mapping every standing goal to ADRs and status

## Implementation history
- [[offline-checkpoint-history-2026-10-05]] — verbatim earlier ledger checkpoints,
  kept separate from current approval and acceptance status
- [[implementation-log-2026-10-05-a]] — preserved initial recovery, journals and protocol review history
- [[implementation-log-2026-10-05-b]] — preserved later repair, configuration and verification checkpoints
- [[implementation-log-2026-10-05-c]] — preserved resource/chat approval, offline
  package verification and private runtime/bootstrap delegation history
- [[log]] — current append-only actions and links to historical log segments
