---
title: Current implementation log
created: 2026-10-05
updated: 2026-10-06
type: guide
status: accepted
tags: [ops, testing]
---

# Wiki Log

Append-only current actions. Historical records were split at an existing entry
boundary to keep pages below the schema threshold, without dropping any content:
[[implementation-log-2026-10-05-a]] and [[implementation-log-2026-10-05-b]].
Acceptance is tracked in [[goals-ledger]].

## [2026-10-05] update | All six completion milestones explicitly retained
- Preserved the previous current log verbatim in
  [[implementation-log-2026-10-05-c]]; earlier segments remain linked in the index.
- Added [[playable-world-acceptance]] covering criterion8's six required milestones,
  evidence boundaries and the initial two-friends/one-solo end-to-end scenario.
- Updated [[goals-ledger]] and index; no milestone is accepted from offline tests
  alone. Current private runtime and pinned bootstrap delegates remain separate
  from the package reviewer; implementation guard boundaries stay unchanged.
- Steered the runtime delegate to prioritize actual private runtime assets and
  reference checks, without inventing launchability or expanding live authority.
- No world/server/SQL/account/provider effects, staging, commit or push.

## [2026-10-05] update | Independent offline package approval reconciled
- Read actual rathena-nix-package-review.json: passed exact offline contract;
 18 scoped repository tests and172 independent cases, with no blocking findings.
- Parent matched all127 reviewed file fingerprints and136 packaged file hashes,
  native binary/image hash and size, package NAR and pinned public-source NAR.
  Checks precede documentation acceptance updates; root flake/binaries unchanged.
- Saved rathena-nix-final-disposition.json; updated package guide, index and ledger.
  Two nonblocking boundaries retained: unknown fixture obfuscation runtime policy
  and lexical host validation, which is not endpoint/world ownership proof.
- Informed ongoing private-runtime delegate; all launch guards remain blocked78.
  No second-clean-build, launchability, gameplay or whole-project approval.
- No engine/server/SQL/account/provider effects, staging, commit or push.

## [2026-10-05] update | Actual private bundles checked; native wire mismatch found
- Read both completed delegate reports/code and read back actual synthetic test
  and debug bundles:679 public assets each,527 NPC scripts/540 total NPC files,
 1265 configured maps,110 explicit omitted imports; hashes/modes/owners matched.
- Parent fullcheck854+65subtests/93.49% and all static gates/audit passed;58 scoped
  runtime/package cases passed. All129 source/test/config fingerprints stable.
- Reconciled7 bootstrap repository references and26 pinned-source hashes. Main
  baseline56 tables/53MyISAM, native23-byte credentials, argv0/CWD relocation and
  absence of login.online are concrete launch constraints, not live authority.
- Parent independently reproduced RUNTIME-WIRE-001: runtime validation accepts
  synthetic24/32-byte inter passwords although native readers truncate at23.
  Runtime approval withheld; delegated exact vertical-TDD correction before review.
- In parallel delegated actual default-account-suppressed public SQL derivation,
  without SQL execution. Created proposedADR-017; updated ledger/index/task list.
- Saved parent before/after verification and four real execution/probe logs.
  Bootstrap guide frontmatter/navigation added after immutable report capture;
  its original source-evidence body and report remain unchanged.
- All native launch/E2E/seeder guards remain blocked; no world/server/SQL/account/
  provider effects, staging, commit or push.

## [2026-10-05] update | Pinned database-image build delegated
- Runtime wire-limit correction and public SQL-asset derivation are still running;
  no new approval or checkpoint count inferred from their intermediate files.
- Delegated actual MariaDB package/Docker-archive build in a separate tiny Nix
  flake with the exact root nixpkgs pin, preserving root/server/runtime inputs.
- Required real Nix artifact/hash/layer readback and source-proven offline native
  help/version; no datadir initialization, SQL, engine load/run or DB startup.
- Coordinated scratch-first RED tests during cold image build to avoid introducing
  known missing-artifact failures into other delegates' combined gate runs.
- Updated overview/ledger; launch/provisioning/ownership authority remains absent.
  No staging, commit, push or existing-world/account/provider effects.

## [2026-10-05] update | Corrected runtime and SQL assets parent-verified
- Active-task control showed runtime/SQL writers no longer running. Read their
  final exact-target reports/artifacts without waiting or polling unfinished work.
- Runtime wire correction is exactly the23-byte interserver/32-byte SQL split.
  Parent repeated23/24/32/33 boundaries and actual file/stdin tests; no values logged.
- Read back all five public bootstrap artifacts with exact hashes/sizes. Suppression
  is fixed public-source span under full-file hash; no SQL or account effect.
- Parent fullcheck884+65subtests/93.51%,88 scoped cases and audit passed. All132
  fingerprinted source/test/config files stable. DB test appeared after collection,
  excluded from this snapshot's acceptance; DB packaging remains separate.
- Saved runtime-bootstrap-parent before/verification reports and four actual logs;
  bootstrap guide frontmatter/navigation added before the frozen review snapshot.
- Dispatched fresh disjoint independent runtime and SQL-reference reviews;
  updated goals/task overview. No independent runtime/SQL approval inherited.
- All native launch guards remain unchanged; no world/server/SQL/account/provider
  effects, staging, commit or push.

## [2026-10-05] update | Database software artifacts parent-verified
- DB writer no longer active; read final report/flake/guide and actual artifacts.
  Child/rootlock bytes match, exact native package and Docker archive resolve;
  image168286076 bytes/SHA and package NAR match. Root server flake unchanged.
- Examined actual pinned daemon source: nonverbose version sets abort, exits before
  database/network startup. Parent --no-defaults --version used empty inherited
  env and private scratch:exit0/version11.4.12, empty stderr and scratch. No init/SQL.
- Parent fullcheck887+65subtests/93.51% and3 DB tests passed. All136 fingerprinted
  source/test/config files stable; preceding Python dependency audit remains valid
  for unchanged project lock/dependencies, not a native DB vulnerability audit.
- Saved db-image-parent before/verification and four execution logs; dispatched
  fresh independent offline database-image review, existing runtime/SQL reviews
  remain disjoint. Source/API/package guides frozen; only overview docs updated.
- No image engine-load/run, datadir initialization, schema/account/world/server
  effects, staging, commit or push. Raw DB capability is not launch authority.

## [2026-10-05] update | Late database completion and source-boundary qualification
- Database completion arrived after parent artifact/hash/version/fullgate checks;
  it is not a new build or independent approval. Review already running.
- Late completion explicitly disclosed an erroneous whole-root path getFlake lookup.
  Existing completed trace lines35–38 corroborate unsupported run/mysql.sock failure
  then the corrected Git-root lookup. The unsafe expression was not rerun by parent.
- Whole-root lookup violates the briefing even when it fails without an output.
  Failure does not establish absence of transient reads/copies; final tiny-flake
  image purity is a separate claim. Saved db-image-execution-scope-note.json and
  forwarded the qualification to the independent reviewer, without private scans.
- No new package/world/database operation or milestone acceptance was performed.
- Resolved the skill-size warning by preserving all six topic sections verbatim
  in linked references; always-on skill is now95 lines/5296 chars. skill_view
  confirms all six references discoverable; no project implementation was changed.

## [2026-10-05] update | Component reviews reconciled; first runtime repair dispatched
- All three reviewer processes finished. Read actual final reports and exact
  findings; old runtime133 and DB134 file maps matched before corrective dispatch.
- SQL-reference derivation independently passed12 scoped cases, exact5-file
  readback and raw DDL/type/index/option preservation. Parent reconciled64 records;
  only runtime.py/runtime_io.py subsequently changed in the active unrelated repair.
  Pure SQL source/tests/artifacts match; ADR-017 accepted for offline derivation only.
- Runtime review independently closed RUNTIME-WIRE-001 but rejected8 supported
  root/publication/cleanup/mode/native-display/raw-path/encoding findings. Delegated
  first bounded vertical-TDD corrective cycle with real reached interleavings.
- DB final offline artifact contract independently passed; overall report remains
  false for DBIMG-SEC-001 historical whole-root source-boundary violation. It is
  not a demonstrated final-image contamination; no zero-exposure claim is made.
- Saved offline-component-review-dispositions.json; updated ledger/index/task list.
  Source snapshots before new repairs remain historical; no future approval inherited.
- No new engine, SQL, schema/account/world/server/provider effects, staging/commit/push.

## [2026-10-05] update | Native working-directory prerequisite delegated
- Read actual pinned Core::start:333–376. argv[0] directory relocation precedes
  SQL362/socket370/roleinitialize376, so shell cd before store-binary exec is wrong.
- Delegated separate tiny-flake native runtime-core build using exact existing pin
  and compiler profile; actual three-role diagnostics must prove explicit private
  runtime-root handling before all initialization. All default/start modes refused.
- This is native location support, not launchability or world authority. Old source
  package, runtime/SQL/DB inputs and launch guards are unchanged by that slice.
- Informed runtime repair owner and kept cold-build tests in scratch until actual
  artifact GREEN, preventing known missing-artifact noise in shared gates.
- Overview/ledger updated; no engine, SQL, schema/account/world/server/provider
  effects, staging, commit or push.

## [2026-10-05] update | Parallel source-backed Classic build research
- Runtime repair owner steered to report exercised results and exact residuals
  within the bounded cycle, without unsupported completion claims.
- Read the actual tank-sac-paladin template and the existing Renewal distinction.
  Delegated independent pinned-source calculations and cited web research for the
  unresolved57-point Crusader/shared-transcendent-budget question.
- Research owns only a new guide/report and task-specific citation captures;
  templates, mechanics and other delegates' inputs remain read-only. Require
  stage allocations, stat/equipment legality, acquisition evidence and explicit gaps.
- Updated criteria/task tracking; playable-world prerequisites retain priority.
  No live effects, character creation, SQL or new source approval claimed.

## [2026-10-05] update | Late DB review delivery reconciled
- Delivered DB review matches the already-recorded qualified disposition: final
  offline artifact contract true, overall review false for DBIMG-SEC-001.
- Rehashed the actual archive: review SHA-256 and168,286,076-byte size matched.
  No DB tool, engine or service was invoked by this coordinator verification.
- Added the explicit independent disposition to rathena-db-nix-image guide;
  status stays proposed. Preserve the incident and original failed report, the
  temporary-exposure uncertainty, and the future /etc/environment link concern.
- No initialization, SQL, launch permission, clean rebuild or whole-goal acceptance.

## [2026-10-05] update | Runtime first repair parent verification
- Read first-cycle report and actual runtime/I/O implementation. Fixer explicitly
  reports not fully closed: IO-003 marker restoration can fail after descriptor
  release and path-binding loss; foreign replacements must remain untouched.
- Parent exercised final103 runtime/failure/package cases:103 passed in73.17s,
  exit0. Reconciled111 dependency/owned file hashes with no mismatch; saved
  rathena-runtime-first-repair-parent-verification.json, overall passed=false.
- Static-gate log is green; full coverage test phase reached71% then terminated
  after240s. No current full count/coverage claim; cycle exceeded its20min target.
- Delegated disjoint read-only independent correction review and verbose bounded
  coverage/timeout investigation. Implementation inputs frozen; no automatic
  second repair, marker-absence admission, launch or SQL authority granted.

## [2026-10-05] update | Acceptance navigation reconciled
- Corrected the stale criterion5 table row and private-runtime index entry to
  distinguish accepted SQL derivation, qualified DB artifact checks and the
  currently unaccepted runtime repair. No source or acceptance labels were upgraded.
- Independent correction reviewer and full-gate investigator remain active;
  their implementation dependencies stay frozen until actual reports arrive.

## [2026-10-05] update | Native diagnostic exercised; research verification dispatched
- Read completed native runtime-core artifact/source/test evidence and actual
  helper/Core patch. Parent physically matched3 NARs,19 artifact hash/size records,
  five-file tiny input allowlist and exact root lock copy; root flake unchanged.
- Parent133 actual three-role ELF diagnostic/fault/race cases passed in7.33s.
  Saved native-runtime-root-parent-verification.json; all startup still refused78.
- Implementer full gate records1047+65/93.58%;105 recorded source/test/config hashes
  match now. This is not a coordinator rerun or IO-003 publication approval.
- Read complete Paladin source/web research guide/report; retained its provisional
  interpretation and unresolved literal class, item-identity and progression gaps.
- Dispatched disjoint independent native-package and Paladin research reviews;
  added both guides to index/ledger/task overview. No native game or SQL startup.

## [2026-10-05] update | Full gate completed; publication architecture frontier
- Read actual completed correction-review and timeout-investigation reports.
  Seven original patterns independently verified; IO-003 plus reached early
  empty-private-root construction/adoption gap remain. Reports preserved unchanged.
- Full investigation completed1047+65/93.58%; no persistent hang reproduced.
  Uncached Ruff I001 in test_decisions.py reproducedRED; import-order-only patch
  followed by whole uncached RuffGREEN and6 decision tests passing.
- Parent then ran actual configured taskcheck: exit0,1047+65/93.58%, all static
  gates,217.004s.136 named public dependencies stable; actual local source/store
  dependency omissions remain explicit. Audit not rerun; no blanket approval.
- Saved runtime-parent-final-task-check.json/log and runtime-first-repair-final-
  disposition.json. Review111 hashes differ only by documented later import sort.
- Delegated read-only replacement contract before more production repair: explicit
  commit-versus-receipt, quarantine/recovery and controlled workspace assumptions.
  No best-effort universal marker rollback or mkdir creation-identity claim.
- No world, SQL, server, engine, provider effects or startup authorization.

## [2026-10-05] update | Native diagnostic accepted; Paladin correction addendum
- Read actual independent native and Paladin reports. Native exactscopePASS133
  tests+207 probes; parent matched26 frozen dependencies and19 actual artifacts.
  Saved native-runtime-root-final-disposition.json, accepted only offline root
  diagnostics and updated guide/index/ledger. All startup remains refused78.
- Paladin core source research independently supported, but62/63 assertions expose
  an acquisition-completeness omission and quest/reset precision qualifications.
- Parent independently parsed all public mob reward categories:46 recorded regular
  rows match exactly plus1 MVP reward (StormyKnight1251→Boots_2406, rawRate500).
 15 candidate identities and original source hashes match; no raw live probabilities.
- Added classic-paladin-acquisition-addendum.json/guide, retaining original reports
  unchanged and recording paid-vs-quest reset and dialogue-vs-executable pet gate.
- No executable build, native equipment/acquisition, SQL or whole-goal approval.

## [2026-10-05] update | Staged-publication primitive implementation dispatched
- Read completed200-line replacement contract and structured acceptance specs.
  Original failed marker/creation guarantees stay failed; proposal is not approval.
- Selected only a narrow architectureA prerequisite for implementation: real
  descriptor-relative nonreplacing move, preserving borrowed descriptors and
  rejecting collisions/unsupported semantics without ordinary-rename fallback.
- Retrieved primary Linux rename/fsync manuals; dispatched strict verticalTDD
  helper with real directory/process races, no existing runtime integration.
- Added proposal navigation/ledger and task tracking. Manager deployment/lease,
  receipt/recovery, durability/admission and live world authority remain absent.
- No source pin, existing guard, world, engine, SQL or serving effects.

## [2026-10-05] update | Bottom-up synchronization prerequisite delegated
- Nonreplace helper writer remains active. Delegated disjoint private-tree sync
  helper with actual file/directory fsync ordering, bounded traversal, no-follow
  metadata checks and origin-preserving cleanup faults on owned scratch fixtures.
- Both helpers leave existing builder and launch guards unchanged. Notify owners
  of concurrent new files; do not inherit full-gate approval across publication.
- No manager/workspace exclusivity, receipt/recovery, production publication,
  world, SQL, container, server or provider authority is asserted.

## [2026-10-05] update | Current exact test-world inventory verified read-only
- Exercised existing accepted inventory adapter; default exact query timed out10s.
  DockerCLI is present and existing Podman service/socket active. Same configured
  local socket read-only ping/version returned200 and advertised API1.44.
- Process-only API1.44 pin made the same exact allowlisted inventory commands
  succeed. Repeated readback shows test volume absent and no scoped containers/
  volume users; mutation_authorizedfalse. No permanent endpoint/config changes,
  engine/service restart, new container/volume/network or SQL effects.
- Saved test-world-current-readonly-inventory.json. Exact initial negotiation
  timeout cause remains unproven; do not equate observations with exclusive lease.
- Nonreplace/synchronization writers remain disjoint; manager and live authority
  still absent.

## [2026-10-06] update | Nonreplace primitive parent verification
- Read completed105-line ctypes/native helper and its real TDD evidence.
  Parent55 scoped cases passed in0.22s with100% module coverage; two exactowned
  hashes match. Saved runtime-publication-io-parent-verification.json.
- Implementer1102/65/93.67 configuredgate is not a parent rerun; newly published
  disjoint sync source still in progress. No broad stability approval inherited.
- Dispatched frozen read-only independent primitive review; no existing runtime
  integration, durability/receipt/admission or original finding closure claimed.
- Live local timestamp confirmsOctober6 CEST; priorOctober5 records preserved.
  No world/server/SQL/engine/provider effects.

## [2026-10-05 UTC] update | Combined primitive gate and narrow cleanup reuse
- Parent reproduced40 sync cases/95.50% before integration check; combinedgate
  failedR0801 duplicated close cleanup versus existing rathena_runtime_io.
- Interrupted sync review, changed only new-sync helper to import unchanged
  verified close_owned; no gate/test/whitelist exemptions.122 focused cases and
  whole duplicate-code gate pass; final40 synccases/95.19% pass.
- Parent configuredtaskcheck thenpassed1142+65/93.71%,188.094s,140 namedpublic
  dependenciesstable. Originalfailed gate and implementerreport remain preserved.
- Saved publication-primitives-parent-final-task-check.json/log and runtime-tree-
  sync-parent-verification.json; dispatched fresh final sync independentreview.
- Added proposed syncguide navigation/taskoverview. No originalflaw closure,
  manager/publication/admission integration or world permission follows.

## [2026-10-05 UTC] update | Exact-string component correction
- Independentnonreplace reviewfailed IO-STR-SUBCLASS-COMPONENT-BYPASS: a Python
  str subclass overrodeencode and actualnative moveescapedretainedparent within
  ownedfixture. No built-instr bypass or privilegeescalation claimed.
- Parentnewrealfilesystemregression failed DID NOT RAISEValueError0.12s; minimal
  exacttype guard anddocstring then58 original/new tests pass0.20s/100%coverage.
  Addedsource/destination preencode/native denial checks; fixed localtestimport
  formatting without gateexemption. Originalfailed review/report preserved.
- Parentconfiguredgate1145+65/93.71%,215.451s,141 namedpublicdependenciesstable.
  Saved publication-io-first-fix-parent-verification.json/log. Firstfixindependent
  reviewdeleg_1db0b8a3 running; no scopedapproval/manager integration yet.
- Delivered interruptedearliersyncreview remainsnonapproval; freshfinalsync
  reviewalready replacesit. No world/SQL/engine/native/provider effects.

## [2026-10-05 UTC] update | Synchronization prerequisite scoped acceptance
- Read actualfinalsync independentreport:40 repository cases+41 fresh probes,
 95.19% publishedcoverage; allfive missinglines reached independently, notmerged
  into inventedcoverage. No security/logicfinding in supportedhelpercontract.
- Parentmatchedexact3 helper/test/shared-cleanup hashes; saved runtime-tree-sync-
  final-disposition.json. Original143-file reviewsnapshot is historical, notglobal
  acceptance of later unrelated nonreplacecorrection or documentlabels.
- Acceptedonly source-onlysyncguide/index/task; construction/publication/manager
  authority andbothoriginalflaws remainopen. No code/liveeffects.

## [2026-10-05 UTC] update | Exact-string first-fix scoped acceptance
- Read actualfirstfix independentreport:58 repository cases+53 independentprobes
  passed,100%modulecoverage; two probes are explicitlyprior-guard calibrations.
- Parentmatchedall14 frozen source/test/reportdependencies; saved runtime-
  publication-io-final-disposition.json. IO-STR-SUBCLASS-COMPONENT-BYPASS closed
  onlyinreviewedsnapshot; originalfailedreview staysimmutable.
- Createdacceptedsource-onlymoveguide andindex/ledger/taskentry. Both narrow
  move/syncprerequisites accepted, but no actualmanager/workspace authority,
  receipt/recovery or builderintegration; originalIO003/EARLYCONSTRUCTION open.
- No SQL/container/native/world startup or fullmilestonecompletion follows.

## [2026-10-05 UTC] update | Data-only publication journal implementation dispatched
- Resumed explicitcontinuationrequest; no activewriters beforedispatch. Delegated
  strictpublicationjournalwith actualprivatefiles/processwriterlock/restartprobes.
- Scope historicalintent/prepared/committed/uncertain/quarantined data, durable
  boundedappend/readback acknowledgement andpoisoned failure; freshgeneration
  acknowledgements defaultfalseforrecoveredrecords. No record/callerflag grants
  controlledworkspace, treecommit ormanager/worldadmissionauthority.
- Required origin/cleanup, malformed/tornhistory, nofollow/mode/binding, bounds
  andappend/close serialization tests. Existingacceptedhelpers/source untouched.
- No actualmanager deployment, SQL, engine/container/volume, service orprovider
  workauthorizedinthisslice; allstartupguardspreserved.

## [2026-10-06 local] update | Journal implementation and parent verification
- Read the new journal source/report and matched source/test hashes. Parent51
  focused tests pass in0.48s,94.83% journal coverage with a separate coverage file.
- Parent configured gate1196+65 subtests/93.75% passes,exit0,191.377s. All143 named
  public code/gate fingerprints stayed stable; all104 pre-existing Python files
  match the recorded implementation baseline. Audit/native/gameplay not claimed.
- Saved runtime-publication-journal-parent-verification.json and its full gate
  log; created proposed runtime-publication-journal guide, updated index/ledger.
- Independent read-only reviewdeleg_22c7059c is running, including constructor,
  acknowledgement interruption and pre/post-release close ownership probes.
  No code changes during review; no approval inferred from gate counts.
- Initial RED import-absence and timebox overrun caveats retained. All original
  runtime findings and manager/recovery/launch requirements remain open.

## [2026-10-06 local] update | Persistent summary-node slice dispatched
- Publication journal remains frozen under independent review. Read actual
  MemoryLog: constructor restores notes but starts _nodes empty, so cached
  summaries are currently recomputed after reopen.
- Fresh OptChat primary source retrieval succeeded; storage section distinguishes
  raw history from a separately persisted summary-tree cache. Original reference
  addresses/view/compactor and torn-line behavior differ from this RO memory.
- Delegated optional SummaryNodeStore integration plus a private source-bound
  adapter and real restart/view/zoom tests. Explicit world/persona/policy isolation,
  bounded coordinates, persist-before-visible-node and cleanup-origin required.
- Only existing memory.py and new cache files belong to this writer; publication
  journal actual dependencies untouched. Reviewer steering was not delivered
  because that review had already finished; its actual verdict awaits delivery.
  Parent will separately qualify later unrelated drift and rerun combined gates.
- Host factory wiring/native restart/provider inference remain outside this slice.
  No cache completion or OptChat-equivalence claim before execution/review.

## [2026-10-06 local] update | Journal review rejected; bounded repair dispatched
- Read the actual failed independent journal review. Source/test hashes match the
  reviewed snapshot. Independent123 passing characterization cases coexist with
  three expected-contract failures; they do not make the journal acceptable.
- JOURNAL-ACK-001: acknowledgement swallowed reached KeyboardInterrupt/SystemExit.
  Parent fresh owned-file regressions both fail at identity assertions in0.07s;
  preceding append/True acknowledgement and the reached stat frame are calibrated.
- JOURNAL-OWNERSHIP-001: pre-release cleanup retains the writer fd/lock without a
  supported ownership/status boundary, including failed constructors. A one-close
  policy remains required but cannot be presented as cleanup completion.
- Saved runtime-publication-journal-first-disposition.json; delegated one narrow
  repair with origin propagation and explicit unresolved cleanup handoff, no
  descriptor retries or false release claims. Original failed evidence unchanged.
- Summary-cache writer owns disjoint memory files; no current full gate is claimed
  during concurrent edits. Fresh completed combined checks/review must follow.
- No manager/world/SQL/container startup or completion milestone accepted.

## [2026-10-06 local] update | Journal first-fix verification and remaining oracle
- Read first-fix source/report; matched all recorded hashes and11 immutable shared
  dependencies/gates. Parent73 scoped tests pass in4.34s,97.14% journal coverage;
  18 scoped source/test/report/dependency fingerprints remain stable.
- Repair propagates acknowledgement interrupts and exposes typed process-owned
  cleanup observations on objects/constructor origins. Unresolved status does not
  mean physical release; descriptor retry and automatic process teardown absent.
- Saved runtime-publication-journal-first-fix-parent-verification.json, coverage
  and log; dispatched frozen independent rereviewdeleg_19fa459e.
- New parent real-file diagnostic oracle has two reached assertion failures:
  successful actual close plus sole post-close KeyboardInterrupt/SystemExit is
  swallowed. Real unpatched fstat confirms release, while API reports unresolved.
  Saved first-fix-parent-diagnostic.json/probe and queued reviewer evidence.
- Original unconditional constructor-release oracle remains unchanged and is not
  claimed to pass under the new unresolved-handoff boundary. No closure/approval.
- Completed combined gate waits for the disjoint summary-cache writer; no live
  world/SQL/container/provider/manager effects or milestone acceptance.

## [2026-10-06 local] update | Summary-cache recovery and completed combined gate
- Only journal read-only reviewer remained active; read finished summary-cache
  report/source and matched four core/adapter/backend/test hashes. Optional cache
  persistence is implemented, not independently approved or host-wired.
- Parent completed full configured gate1286+65/93.94%,exit0,183.71s; all147 named
  public fingerprints stayed stable. Saved summary-cache-journal-parent-task-
  check.json/log. Two separate journal diagnostic failures remain outside suite.
- Parent seven-file memory selection155passes2.49s,91.36% combined memory/cache
  coverage. Its scope differs from the implementation195 selection. Adapter
  covers183/196 statements, core219/244. Cache meaningful baseline/restart claims
  remain local injected-summarizer tests, not actual inference/billing evidence.
- Fresh taskaudit exit0 reports no known vulnerabilities; saved output handle in
  memory-summary-cache-parent-verification.json. All147 hashes still match after
  audit/focused rerun, no pins or source changes.
- Dispatched frozen cache/core independentreviewdeleg_51b985ef. Created proposed
  persistent-summary-cache guide and registered ledger/index/task checkpoints.
- No native/world/host-factory or CLI integration, launch authority or acceptance
  milestone follows. Journal first-fix review remains separate and unapproved.

## [2026-10-06 local] update | Optional summary-cache scoped acceptance
- Read actual cache independent PASS report. Parent matched15 frozen inputs and
  parsed both JUnit batches:210 distinct executed cases, no failures/errors/skips,
  including71 fresh probes. Saved memory-summary-cache-final-disposition.json.
- Accepted optional Memory/cache persistence only. Updated guide/index/ledger/task;
  source code unchanged and original implementation/review evidence preserved.
- Retained measured quadratic prefix hashing and inherited pre-release fd/flock
  ownership loss despite cleared fd slots. Actual residuals were observed before
  fixture recovery; incomplete-cleanup notes are not physical release or recovery.
- Host factory/CLI wiring, provider/native memory acceptance, journal approval and
  all world milestones remain pending. No startup or full OptChat parity claim.

## [2026-10-06 local] update | Final journal cycle and host cache wiring dispatched
- Read failed journal first-fix rereview. Parent matched its source to the last
  completed gate and parsed141 JUnit executions/10 failures. ACK001 is closed
  for its reviewed method; OWNERSHIP001 remains partial, with new DIAGNOSTIC001
  sole-interrupt and OWNERSHIP002 post-open/getpid allocation faults.
- Saved runtime-publication-journal-first-fix-final-disposition.json. Dispatched
  one final bounded second repair; no automatic third repair or source approval.
- Read real AgentHost factory and CLI: only raw storage is currently constructed.
  Parallel disjoint host/CLI task adds explicit opt-in cache world/policy settings,
  shared brain/inspector memory and real offline host restart/lifecycle tests.
- Accepted cache/core/backend and shared publication helpers are outside both
  writers' scopes. Constructor cleanup must attempt all owned stores/personas,
  preserve origin and avoid double-close or false physical-release claims.
- Latest1286+65/93.94 gate is historical during these source changes. A newly
  completed combined gate and independent reviews remain required. No native,
  provider, DB, engine, world startup/reset or full-milestone acceptance.

## [2026-10-06 local] update | Final repair and host wiring parent verification
- Read completed source/reports after both writers finished. Parent matched journal
  freeze/new test and all18 host source/dependency/guide hashes; parsed JUnit112
  journal and318 distinct host cases, no failures/skips. Original accepted cache,
  shared helpers, tests/gates/pins/failed reports remain unchanged.
- Parent completed taskcheck1397+65/94.01%,exit0,210.551s;150 named public files
  stable. Saved host-cache-journal-final-parent-task-check.json/log with isolated
  coverage. Current parent pure-diagnostic probe2GREEN0.29s; old failure evidence
  remains immutable and new success is recorded separately.
- Final journal source now propagates sole nonlocal diagnostics after storing
  unresolved status and obtains process identity before writer allocation. Typed
  handoff remains observations, not FD retry/process termination/world authority.
- Host explicitopt-in cache world/policy plusmemoryroot reaches shared persona
  memory/brain/inspector; inherited cleanup and stub backend limitations retained.
- Dispatched fresh frozen reviewsdeleg_ff36f7da (journal+host). No approval yet,
  automatic third journal cycle, native/provider/world operations or milestone
  completion. Registered new proposed host guide and updated ledger/index/tasks.

## [2026-10-06 local] update | Scoped acceptance and trusted-user workspace choice
- Read both final PASS reports. Parent parsed JUnit223 journal and330 distincthost
  cases, no failures/skips; matched23 journal/30 host frozen inputs. Saved separate
  finaldispositions, acceptedonlydatajournalhandoff/offlinehostcachewiring.
- Retained originalunconditionalFDcleanupnotclosed and active-sys.exceptionpolicy;
  caches/hostbackend inheritedpre-releaseownership and quadraticwork limits remain.
- Strict test-worldinventory nowfailsgenericunavailable/module2/task201. Default
  andprocess1.44pin sameengineversionreads succeeds, server5.8.7/API1.44; existing
  userengineunitsactive. No targetabsence/ownership/mutation claim or servicechange.
- User explicitlyselected existingrootlessPodman withsame-UIDprojectcode trusted,
  isolateddebug/test/namedproddata andnohostilesameuserexclusionclaim. Created
  acceptedADR018 fortrustdecision, notdeployment/provisioning permission.
- Dispatched cooperativeworkspacepublisher usingacceptedprimitives/actualexisting
  bundlebuilder andseparateREADONLYinventoryfailurediagnostic (deleg_afa66ecf).
  No oldevidence/gates/pins/builder/helpercode changed byparent; noliveeffects.

## [2026-10-06 local] update | Current inventory recovers without code changes
- Completed read-only diagnostic did not reproduce earlier inventory failure;
  default/pinned unchanged routes returned0, no selected target resources. It
  explicitly leaves historical cause unknown rather than inventing an API fix.
- Parent re-executed exact task withprocessAPI1.44:exit0, volume_exists=false,
  containers=[]/volume_users=[],inventory_stable=true,mutation_authorized=false.
  Saved test-world-current-inventory-recovery.json with observational limits.
- No code/engine/service/configuration/container/volume/world changes or diagnosis
  acceptance for unknown pastcause. Cooperative workspace implementation remains
  active; resource observations never grant reset/provisioning authority.

## [2026-10-06 local] update | User redirects isolation to simple Docker volumes
- User clarified playable worlds need different Docker volumes, nothing fancy.
  Recorded ADR-019: ordinary Compose projects and per-world persistent data;
  only name validation and exact test-only reset safeguards, no custom manager
  or receipt/catalog architecture prerequisite. Updated ledger/index/skill/tasks.
- Tried stopping workspace delegate; it had already finished and no live children
  remained. Any experimental artifact stays unintegrated, not an execution blocker.
  No deployed containers, volumes, data or world lifecycle changed.

## [2026-10-06 local] update | Simple Compose and runnable native variant
- Inspected lifecycle wrapper/Taskfile: still blocked. Current Compose has reserved
  external volume stanzas and legacy image routes, not a usable isolated stack.
  Existing native adapter deliberately refuses startup78. These are functional
  blockers, not a need for the abandoned workspace-manager architecture.
- Verified configured Docker Compose CLI5.5.1. Dispatched TDD simple per-world
  Compose/command routing and separate tiny public-flake runnable native package
  plus Docker archive (deleg_fa13df43), with disjoint file ownership.
- Old accepted native artifacts, SQL/legacy seeder guards and private inputs stay
  unchanged. Parent integrates wrapper/tasks after the module interface completes.
  Verification permits rendered config and early safe native probes only; no
  engine/container/volume/world/SQL mutation or live gameplay acceptance.

## [2026-10-06 local] update | Fresh-world SQL rendering implemented
- Added small world_bootstrap_sql adapter and36 focused cases. Reused attested
  public schema derivation:70 disjoint tables, default account removed, configured
  database selected in five ordered files and one server-only non-GM row.
- Reached missing-renderer RED,24 invalid-input RED and hex-value row RED before
  their production fixes; final36new+12existing tests passed2.68s/100% module
  coverage. Black/Ruff/strictmypy/Bandit green. Saved world-bootstrap-sql.json;
  parsed48 unique JUnit cases, no failures/errors/skips.
- Encoded credential values as SQL hex literals (still sensitive, not encryption);
  retained original pinned bytes and exception origins. No new lint waiver.
- Queued Compose writer with init-directory integration contract; dispatched
  bounded frozen independent SQL reviewdeleg_4ad405da. No SQL execution, private
  file/volume initialization, parser/startup acceptance or combined-gate claim.

## [2026-10-06 local] update | Simple world Taskfile/CLI integration verified
- Compose writer finished; parent read its module/template/report and integrated
  world.sh routing and Taskfile world:config/up/down/wipe/status with quoted WORLD
  environment. Wipe selects onlytest; debug/prod refused. E2E/playground/seeder
  stay explicitly unfinished/blocked; no environment FORCE bypass introduced.
- Wrapper/config6RED andmissingTaskselection5RED preceded fixes. Found variable
  nativehostports stillmappedfixedcontainerports;3RED regressions then aligned
  target/published native ports so prepared runtime can use the same values.
- Final parent116 unique selected cases passed6.26s. Actualread-onlyComposeconfig
  throughwrapper andTaskfile worked fordebug/test/prod-blue. Mutation routes only
  printedvalidatedargumentplans. Black/Ruff/bashsyntax green; JUnitcount verified.
  Saved simple-world-parent-integration.json with7 source/dependency fingerprints;
  originalwriterreport preserved, parentpostwriterchange explicitlyrecorded.
- Delegated independentComposeroutingreviewdeleg_5ec3b9d7 andsimplehost runtime/
  bootstrap preparationdeleg_e9a16947. Nativepackagebuildongoing. NoSQL execution,
  volumeimport, containersstarted/reset or native/world/gameplay acceptance.

## [2026-10-06 local] update | Native artifacts verified and image-role routing corrected
- SQL independentreview passed108 unique cases/100% coverage. ParentparsedJUnit
  andmatched3 currentfrozeninputs; savedworld-bootstrap-sql-final-disposition.json.
  Acceptedpurerendereronly; no MariaDB parser/execution/permissions acceptance.
- Nativewritercompletedrealpackage+Dockerarchive. Parentmatchedpackage/imageNAR,
  archiveSHA/size,19publicpkgfiles,5tinypublicinputs and5unchangedoldofflineinputs.
  Executedactual --check-runtime-root inall3newELFs:exit0/rootbound/CWDmatch.
- Parentinspectedarchivelayers: /libexec/rathena/{login,char,map}-server symlinks
  resolveactualpackagebinaries. Defaultimageentrypoint islogin, sooldCompose role
  commandswouldnotselectchar/mapor supplyrequiredroot. InterruptedoldCompose review
  ratherthanacceptmutableinput;3reachedRED tests thenfixedentrypoints/runarguments.
- Finalparent119selectedcases pass4.13s; nativewriter260JUnitdistinctcases parsed.
  Savedplayable-rathena-parent-verification.json/simple-world-role-integration.json;
  originalreportsand116casecheckpointremainunchanged. Nativevalidrunmode neverrun.
- DispatchedfreshnativeartifactandcorrectedCompose reviewsdeleg_21b18d66. Hostprep
  ongoing; no imageload, containerstart, SQLinit, volumechange or wholeworldacceptance.

## [2026-10-06 local] update | Combined gate and narrow preparation correction
- Native scoped independentPASS reconciled260JUnitcases/15 currentpublicinputs;
  savedplayable-rathena-final-disposition.json. Artifact/startupadapter acceptance
  only; no nativevalidrunmode or world/gameplay accepted.
- First configuredgate failedBlack: reachedAF_UNIX listeneraddress111bytes. Short
  private processTMPDIR solved it. Inheritedpytestplugin-disableflag causedmissing
  covoptions; unsetprocess-only. No toolchain installs or gate rule relaxations.
- Vulture found3 type-onlyRunnerargs: reachednewRED beforeexplicitabstractsignature
  preservingkeyword interface. 65scopedGREEN/staticgreen. Wholegate thenfound16
  oldglobalblocked-message/custom-network expectations; replacedwithADR019 explicit
  world/noDocker-on-env-bypass/projectdefaultnetwork checks. Legacyseed/e2eguards
  andexact-account cleanup tests unchanged.
- Final completed configuredgate1761+65/94.27%,exit0,260.349s;131 selectedpublicfiles
  stable. Failedattemptrecords retained. ThispasspredateslaterWP01cleanup change.
- Hostprep independentordinary693-filefixture/92cases+50freshchecks good; WP01low
  severitycloseerrorcouldreplaceactivewriteorigin. Parent2reachedRED thenminimal
  once-close/origin-preserving correction;238selectedGREEN/100%prepcoverage. Saved
  world-preparation-first-fix.json; no newmanager, rollback orreleaseclaims.
- Dispatcheddelta reviewdeleg_93957260 andsimpleprivate service-credential prepCLI
  deleg_7125c0aa. No volume/database/engine initialization or provider/nativeeffects.

## [2026-10-06 local] update | Cached DB image init-reader verified
- Exactread-onlylocalimagequeries foundcachedMariaDB11.4 andnoengine-loadednew
  rathena-playabletag. InspectedofficialRepoDigests beforeexportingcachedDBimage
  byimmutableconfigID. Export isread-onlyengineaction, localprivatescratchartifact.
- Extractedselectedetcpasswd/group/entrypointsourceonly: actualmysqlUID/GID999,
  root_FILEreadthenunset,gosumysqlbeforefreshinit-hook SQLfile reads. Saved
  cached-mariadb-init-source.json withsourceSHA/scope andno credentials/environment.
- Hostoperator700/600SQLbinddir thusisnotreadyforreader999. Delegated smallpinned
  utilityimage/script volumeimport (deleg_d9e4325a): copyprivatepreparedfilesinto
  EMPTYnamedvolume withruntime10000/mysql999 subtrees androotSQLinitfiles. No
  manager/catalog, hostworld-readablesecrets, Dockercreate/run orSQLexecuted.
- ExistingCLI/deltareviewworkcontinues; actualvolumeownership/initreadback and
  firstnativeworld remain acceptance steps, not provedby image filesystem inspection.

## [2026-10-06 local] update | Preparation Task and persisted world inputs verified
- Delta reviewPASS parsed268uniqueJUnitcases andmatched33currentpublicinputsbefore
  subsequentCLIintegration; savedworld-preparation-and-runner-final-disposition.json.
  WP01closedinreviewedsnapshot; originalfailedreportpreserved, no newmanager scope.
- CLIwritercompleted actualmodule37new/131selected cases, private694-filefixture,
 96.43%CLIcoverage/scopedstaticgreen. Parentparsed131JUnit andrecorded later
  world_compose metadata-loading delta, notclaimwriteroldhashstillcurrent.
- AddedTask world:prepare/world.shprepare branch aftermissingTaskRED; actualTask
  generatednewprivatefixture. Addedprivate savedinputloader after5RED tests and
  saved-stageconfigRED; metadataworld/project/volume mustmatchselectedworld before
  use. Exactschema/plainstrings; hostsettingsprivatereaderreused, no credentialecho.
- Parent116selectedGREEN10.41s, Black/Ruff/strictmypy/bashsyntax green; actualTask
  configconsumedprivate savedworldinputswithconfig-onlyimagefixture refs. Task
  stageenvironment isquoted; lifecyclecommandsstillonlyplans inverification.
- Savedworld-preparation-cli-parent-integration.json/seven source hashes and
  dispatchedreviewdeleg_bd7edcce. Utilityvolumeimportimagebuildongoing. NoSQL/
  container/volume/nativeinit/provider state changes or whole-world acceptance.

## [2026-10-06 local] update | Initializer rebuilt and first live scope authorized
- Importwritercompletedreal97MBarchive/offline28tests. Parentusedexistingproject
  tools toresolvewriteruncachedVultureclosure(noinstalls); strictVulture/Banditpass.
  XenonfoundpreflightD; extractedvalidationhelpers preservingorder/conditions,
  reran28regressions/allscopedgatesgreen, rebuiltnewactualinitializerarchive.
- Matchedpackagedscriptbytes, archiveSHA/NAR/User0/Entrypoint andnoanonymousVOLUME;
  savedworld-volume-import-parent-verification.json. Originalwriterreport/archive
  preserved. CrossUID10000/999 andcontainerexecution remain untested.
- UserexplicitlyAUTHORIZED firstfreshro-bots-test/ro-bots-world-test bring-up after
  pendingreviewspass: imageload/import/DBinit/three localhostnative roles only;
  refuseexistingresources/portconflicts,noprod/debugresets/humanchanges/paidcalls.
  Savedfirst-test-world-live-authorization.json; no live execution yet.
- AddedminimalnativeCompose(4services,nofrontendimagedependencies)aftermissing-
  templateRED. SQL/secretsreadfrominitializednamedvolume, notoperatorhostbind.
  CachedDBimageVOLUME/var/lib/mysql wouldcreateanonymousdata: reachedREDthenbound
  sameworldvolume explicitly. Final73selectedbootstrapcasesPASS13.31s; no startup.
- Dispatchedinitializerreviewdeleg_b4aaca5d. Pendingreviewdelivery precedes exact
  target/port preflight and authorizedfirstliveaction; separatehost/privatefixture
  and realworldacceptance boundaries retained.

## [2026-10-06 local] update | First actual isolated database and native startup
- Reconciled52initializerreview cases/18inputs and232CLI/nativeprestart cases/27
  inputs. CLIannotation defect closed; full gate exposed15additional test-only
  untypedcalls. Addedtypeimports/signatures only, reversedthem toexact oldreviewed
  bytehashes;30scopedGREEN. Finaltaskcheck1836+65/94.27%exit0,260.81stesttime.
- Defaultports6900/6121/5121busy with existinghostservers; didnotstopthem. User
  explicitlyselected16900/16121/15121. Freshresource/port/imagepreflightpassed.
  Loadedtwoactualarchives andreadIDsback. Createdro-bots-world-test/testproject,
  copied683runtime/5SQL/2secret files, actualUID10000/999 readers/modesverified.
- MariaDBfirstexit2: root0711 blockedlsinitdirectory. TDDroot755RED→28GREEN,
  changedonlyrootmode/publicentrynames; privatefiles600/subtrees700retained.
  VerifiedownedDBstillEMPTYbeforechmod, UID999directorylistingreadbackthenpassed.
- ActualinitSQLall5hooksran: read70tables, one server-onlyrowsexS/group0/state0,
  nohumanrows. DB ranbuthealthfailed1045 becausehealthscriptdefaultconfigpathdid
  notfollowcustomdatadir. Publiccachedscriptread; explicitdefaults-extra-file
  livehealthcommandrc1→0. TemplateTDDRED→29GREEN; DBnowhealthy afterrecreate with
  samepersistentvolume, noreset. Oldfailure/private logsretained0600,values[REDACTED].
- Firstnativeup0 and3TCPs passedinitially; delayedreadbackcaughtcharexit1.
  Minimalroleconfigdiscardeddefaults:zerocharacterslots/emptyrequiredtablename,
  clanquerywrongtable. Login/maprunning;mapcannotreachchar. No joinable-world or
  bot-gameplay claim. MissingoptionalDB/NPCyaml diagnosticssubsequentfrontier.
- Rebuilt0755initializerarchive08nzyk5rvg1a0bkpnibfm54l22rdvsk2, matchedscriptbytes
  andSHA/NAR. NewarchiveNOTloaded;oldcopiedvolume repairedexplicitly. Saved
  first-test-world-bootstrap-frontier/readers/init-directory-fix/database-readback/
  native-startup/native-readiness records. Deleg_eae4721c owns offline defaultcfg
  repair vsread-onlybootstrapfixreview; parent retains liveworldoperations.

## [2026-10-06 local] update | Defaults fix reaches connected native roles
- Defaults writerreachedRED('native SQL defaults missing') then162GREEN/100%prep.
  Parent163uniqueJUnit/100%, actualhashes10matched. BootstrapdeltaPASS parsed28
  uniqueJUnit/10current inputs; new0755archivealreadyparentbuilt/byteverified.
- Correct earlierinterpretation: pinnedchar.cpp char_per_account0 meansunlimited,
  notzeroslots. MissingSQLtablename/clanwrongtablewereactualstartupfailure.
  Mergedpinneddefaultsrestore40char-table mappings; no arbitraryslots override.
- Builtprivate7-pathpatch fromexistingownstagecredentials/customports;mapsconfig
  unchanged. Stoppedonly3ownednatives, wrote/readbackall7files600UID10000 and
  restartedwithoutDBreset. Charlogin/mapchar peerconnectionsobserved.
- Delayedcheckall4servicesrunning/DBhealthy;charregistered1265maps, maploaded1265
  maps+13036NPCs. SQLpreservation70tables/one server-onlyaccount/0humans/0characters.
  No clientcharacterentry, botgameplay, provider inference or complete milestone.
- Fullconfiguredgateafterallfixes1839tests+65subtests/94.32%,exit0,282.86stesttime,
  134publicfingerprints stable. Actualconfiguredtaskauditexit0/no knownvulnerabilities.
  Servicesremainup afterwholegate+audit; no nativeautorestarts. Rawprivate logs600.
- Savedfirst-test-world-native-config-update/defaults-restart/defaults-delayed/
  post-gate-status andnative-defaults-final-task-check/auditrecords. Newguide
  first-live-native-world linked. Source-onlydefaultsreviewdeleg_a03ea35d running;
  optionalmapcache/mob-appearance/barterdiagnostics remainseparatefrontier.

## [2026-10-06 local] update | Native-defaults independent scope closed
- IndependentdefaultsreviewPASS162uniqueJUnit/100%world_preparestatementcoverage;
  allscopedgates0,58effectiveprivateoverrides andimportmalformationprobesverified.
  Parentmatched10currentpinnedsource/dependencyhashes/JUnit andactual delayed
  readinessreporthash. Savedworld-native-defaults-final-disposition.json.
- No newsource repair or milestoneclaim. Parentrealnative/SQLreadiness remains
  separate fromreviewer'soffline evidence. Cliententry/fixtures/nativeTaskE2E,
  optionaldatawarnings andremainingstandingmilestones stillopen.

## [2026-10-06 local] update | Two-bot client-entry tracer bullet authorized
- Legacyseeder remainsblocked; do not reuse inerttransaction/upsert/resetroutes.
  CurrenttablesmostlyMyISAM; nextfixturehelperPURE INSERT-only renderer for two
  freshnonGMnovices withBasicSkill9, exactIDs/privatefreshcredential/PIN inputs.
- ExistingclientcharhandshakeignoresPINrequiredstatus; serverPINpolicy staysON.
  Deleg_8dfa9dff owns disjoint renderer/newtests versus source-provenPINclient/
  harness/newtests, strictTDD offlineonly. Parentowns liveengine/SQL/actions.
- Userauthorized twoNONHUMANfixtureaccounts/characters andlogin/move/chat/sit/
  party aftercodepassesreview, plusbriefownnative stop/restart. Noexistingaccount
  changes/DBreset/proddebugchanges/paidinference. Savedauthorizationrecord.
- ReadonlycurrentDB1server-onlyrow/0normal/0characters; actualAUTO_INCREMENT
  char150000/login2000000, notguessedranges. Pinnedpre-reprontera312x392 cells
 150150/152150/153150/151151 allwalkablepernativegat2cell0/2/3. Theseobservations
  arenot futurewriteauthority, refreshbeforeexecution. No fixtureSQL/actionsyet.

## [2026-10-06 local] update | Fixture and PIN integration green, reviews pending
- Renderercompleted46new+36bootstrap82cases/100%cov; pure6INSERTs/twofreshnonGM
  novicechars Basic9/PIN. Legacyseederblocked/no DBwrite/no buildlegalityclaim.
- PINclient40newpass but164/7 combined: parentsourceproofchar_logif80..83 emits
  accountmatchedstate0 evenPINdisabled. Reproducedall7failedreplays; appended
  onlystatusframe to2oldsyntheticstreams, keptfailure/cleanup/slotsassertions.
- ParentaddedPINmetadataassertRED->0x08B8fixed10/nameCH_SECOND_PASSWD_ACK,
  pinnedpackedstruct+registeredsizeof primaryauthority. WorldPINpolicy unchanged.
- Actualparentintegrated254tests+65subtests GREEN4.02s, scopedBlackRuffstrictmypy
  green. OriginalfailedimplementerPINreportpreserved; broaderlegacyspikeRuff/mypy
  explicitlynonclean, exactbaselineattributionnotverified/no waiver claimed.
- Fullconfiguredgate1926tests+65subtests/94.36%,exit0,137publicfingerprintsstable,
  aftercurrentcompletedrenderer/PIN/replaymetadata sources. No privatevalues/hash
  output; recordedtwo-bot-parent-integration +prestart-task-checkJSON/logs.
- Independentreadonlyreviewsdeleg_35084179 dispatched separatefixturevsPIN
  frozenclosures. Userliveauthorizationconditionalafterreview stillnotexecuted;
  no fixtureaccounts or playeractions added inthese turns.

## [2026-10-06 local] update | Independent fixture review accepted; PIN lint delta
- Renderer source-only PASS: reconciled 82 unique JUnit cases, 51 extra refusal
  probes and all 17 frozen current dependency hashes. No SQL execution claimed.
- PIN protocol independently passed 93 cases/405 native decrypt vectors. Reviewer
  identified seven new EM101 raises; parent reproduced exactly seven, then changed
  only sanitized literal assignment before the same exception raises. Original
  report preserved. Current integration remains 254 tests +65 subtests green.
- Dispatched read-only quality-delta review deleg_a8513937. Live provisioning stays
  conditional on final review; no accounts, characters or player actions added.
- Fresh read-only inventory: exactly four project-owned containers on the owned
  volume, all running, DB healthy, only loopback16900/16121/15121 published, no DB
  port published. SQL remains one server-only row/zero normal rows/zero characters;
  actual allocation counters unchanged. Pinned Prontera cache validates movement
  target (150,151), in addition to both spawn cells. Recheck before actual writes.

## [2026-10-06 local] update | Authorized two-bot native smoke verified twice
- Final PIN quality-delta review passed: exactly seven message-assignment edits
  reversed in memory to original hashes, 254 unique cases +65 subtests green.
  Parent matched all current frozen sources and actual JUnit before live action.
- Fresh exact labels/images/mounts/volume users/ports/database checks preceded
  stopping only owned native roles. Database stayed healthy; no client listener
  or non-root DB sessions remained. Fresh allocation/conflict observations used.
- Generated private fresh two-bot manifest/SQL, six INSERTs executed once and all
  login/character/Basic9 rows read back exactly. Existing server row unchanged
  before restart, other67 table counts unchanged. No rollback or legal-build claim.
- Actual harness twice passed chat, advertised movement destination, sit-stand and
  exact-recipient party acceptance. Second run reused fixtures/party without reset;
  observed eight PIN-required/eight success frames, all matched, cleanup confirmed.
- First second-run preflight failed its incorrect saved-Y>=151 assumption before
  game actions. Actual positions remained spawns; saved arrival/persistence not
  accepted. Corrected rerun used actual walkable cells; no assertion weakened in
  the harness. Preserve failure report and investigate arrival separately.
- Final SQL/engine readback: four running services/healthy DB; server row1, exact
  nonGM bot accounts2, offline fixture chars2, Basic9 rows2, one shared persistent
  party. No paid inference/human changes/proddebug/reset/legacy-seeder bypass.
- Wrote [[two-bot-live-limbs]], updated [[first-live-native-world]] and
  [[goals-ledger]]; sanitized provisioning/two-run/final-readback reports retained.
  No six-full-milestone acceptance, no Clef/LLM/combat/loot/host/dashboard claim.

## [2026-10-06 local] update | Native movement disconnect timing differential
- Tested the same exact authorized fixtures, changing only post-announcement dwell
  before cleanup; no SQL writes/reseed/reset. Fresh world/container/mount/fixture
  checks preceded both moves, target cells came from pinned mapcache walkability.
- Both peers observed requested (150,151) from native start (150,150). Immediate
  disconnect saved (150,150), while one-second dwell saved (150,151). Both exact
  chars offline after each probe and supported transport cleanup confirmed.
- This is one real completed/saved movement under the dwell condition. It is not
  universal arrival certification from a fixed sleep, nor a repaired smoke harness.
- Public native unit.cpp238 schedules future walk timer before242/244 announcements;
  timer623-625 applies coordinates; map.cpp2316/2325/2329 removes/saves on logout,
  pc.cpp1430-1433 saves current native coordinates. Source investigation
  deleg_06c0347b is tracing cancellation and reliable arrival evidence, read-only.
- Preserved differential report; no source fix before completed root-cause review,
  no complete standing milestone accepted.

## [2026-10-06 local] update | Native arrival barrier prototype verified
- Source investigation completed: observer target and initialself0x0087 are
  acceptance announcements; native ordinary EOF cancels pending movement then
  saves current coordinates. Parent timing differential corroborates this path.
- Dispatched strict TDD harness fix deleg_0e7a9d18: require peer announcement and
  fresh same-target self0x0087 from=to=target, reject initial/stale/wrong frames,
  single bounded confirmation request, unchanged overall deadline/cleanup.
- Parent live prototype independently tested the source candidate. Initial ACK
  (150,151)->(150,152); one fresh same-target request yielded (150,152)->(150,152)
  in0.151s. No fixed post-move sleep. Immediatecleanup then exact native SQL
  readback saved (150,152); both exactchars offline, supportedcleanup confirmed.
- No SQL writes/reseed/reset/provider calls or changes to old worlds/accounts.
  Recorded native-movement-same-target-live-probe.json; production harness TDD
  implementation/source review/full live rerun still pending, no milestone claim.

## [2026-10-06 local] update | Scheduled-host native transport seam identified
- While arrival-harness TDD runs, inspected agent_runtime ManifestEntry/load_manifest
  and ScheduledAgent._new_client. Current manifest drops endpoint/PIN, constructor
  passes only account/password/character/verbose, so legacy BotClient6900 remains.
  Actual owned native test target requires explicit16900 and per-account PIN.
- Delegated disjoint strict TDD endpoint/PIN manifest forwarding deleg_97eb000a:
  agent_runtime.py/newtests/report only, complete explicit endpoint pairs and opaque
  PIN validation, preserve legacy/injected factory contracts. No globalclientdefault
  change, no provider/SQL/network/AgentHost execution or private fixture access.
- Movement fix deleg_0e7a9d18 remains separate; no final whole-gate claims while
  parallel source edits are underway. Host-native source review and guarded live
  scheduled cognition remain future acceptance, not implied by constructor tests.

## [2026-10-06 local] update | Arrival barrier integrated; frozen review pending
- Movement implementation completed22 new RED->GREEN cases; revised harness
  requires peer announcement plus fresh mover-stream zero-length native self ACK,
  exactly one confirmation, pre-send history snapshot and bounded existing budget.
- Implementer combined193pass/1fail preserved. Parent reproduced old movementfake
  lacking raw_log; supplied native ACK only on second send, retained exact actor
  versus character-ID assertion, added send-count2/1 assertions. No barrier weaken.
- Parent combined276 tests +65 subtests green, actual unique JUnit reconciled;
  three filesBlack/newtests+oldfixtureRuff/newtestsmypy pass. Existing broader
  legacy spike style/type debt remains explicit, not waived.
- Frozen independent review deleg_f30cb9df dispatched on movement closure only;
  host-native transport worker remains disjoint. No revised-harness live execution
  or new full-repository gate yet. Existing parent prototype remains separate.

## [2026-10-06 local] update | Host transport complete offline; combined gate green
- ManifestEntry now carries keyword-only explicit IPv4 login_host/login_port and
  optional per-account PIN; loader rejects incomplete endpoint pairs/malformed
  explicit PINs, and scheduled native constructor forwards all three fields.
  Legacy6900/default/first-duplicate/injectedfactory behavior remains qualified.
- Implementer31new cases/214scoped regressions,89.90% fullruntime module coverage;
  targeted Black/Ruff/mypy/Bandit/Vulture/Xenon green. Constructor spies only.
- Dispatched independent readonly host review deleg_9b7a7d64. Arrival review is
  separate frozen closure; no source changes during full parent validation.
- Actual parent configured whole gate1979tests+65subtests/94.46%,exit0;139public
  fingerprints unchanged. Recorded native-arrival-host-transport-task-check.
- No actual ScheduledAgent/AgentHost activation/provider calls or revised-harness
  native rerun in this step. Those remain separate reviewed/authorized checks;
  no legacy-wide spike quality waiver or complete-standing-milestone claim.

## [2026-10-06 local] update | Revised native arrival verified twice; reviews closed
- Accepted scoped arrival review after22 current hashes/276 unique JUnit+65subtests
  matched; host review77 current hashes/222unique JUnit/scopedstatic gates matched.
  No source repair needed. Helper100% linecoverage/nativecompiler boundary probes
  remain independent evidence, not new parent compiler executions.
- Reconciled implementer214 JUnit scope: core-interruption cleanup25 versus
  independent host-chat interruption20 selection; reviewer222 includes13 new probes.
  Actual report artifacts preserved; no invented totals or dropped failed evidence.
- Fresh exact images/mounts/project/all4running/healthyDB/offlineownedidentity
  checks and source-cache destination checks preceded each native harness replay.
- Revised production harness passed twice: fresh zero-length SELF ACK and saved
  coordinate progression150152->150153->150154, plus chat/sit-stand/current party.
  No reseeding/reset/SQLwrites/providercalls/fixed post-move wait. Both exact chars
  offline/sharedparty after each; four services healthy and sourcehashes unchanged.
- Bounded ordinary one-cell fixture arrival/save gap accepted. Host transport
  sourcecontract accepted only; no actualHost/provider/cognition/memoryactivation,
  generalmovement/combat guarantee or full-standing-milestone acceptance.
- Recorded native-arrival-host-transport-final-disposition and
  native-arrival-revised-harness-live JSON; [[two-bot-live-limbs]]/[[goals-ledger]]
  updated with precise acceptance and retained prior false-positive smoke evidence.

## [2026-10-06 local] blocked | Scheduled-host activation permission unanswered
- Inspected actual AgentHost step, construction and shutdown plus private-journal
  injection seams. Proposed only two existing fixtures, two short real-time idle
  sessions, at most60 seconds total, brain/inference disabled, private host-stage
  session journals and fresh-process restore. No fake cognition acceptance.
- User clarification timed out with no answer. No scheduled host, new host
  manifest, journal writes or providers were started. Prior four-limb permission
  is not extended into this activation. Saved exact unanswered-scope record;
  blocked pending explicit user decision, no alternate execution or retry.

## [2026-10-06 local] update | Idle native host lifecycle and journal replay verified
- Fresh direct user instruction `continue, finish the work` applied only to the
  previously outlined bounded idle-only scope; original timeout history preserved.
- Fresh preflight found all4owned containers stopped. Exact images/labels/mounts/
  owned volume/users/free loopback ports verified, only4existing resources resumed;
  no reset/new resources/unrelated changes. Why they had stopped is unknown.
- First host probe failed before login: six-second windows versus minute-only
  PersonaClock. Both private journals empty; failed result retained. Injected real
  local wall-clock seconds through existing SocietyClock seam, production unchanged.
- Two fresh actualAgentHost processes used declared16900/PIN and both exactpairs,
  real schedule openings/closings observed in host, threads and native SQL. Both
  PIN challenges/successes matched perprocess; no inference/autonomous actions.
- Newprocess restored one prior own session peragent, then each reached2notes.
  Total4session notes, private roots700/files600/operatorownership verified;
  scheduled facade/inspector binding and supported worker/client/storage cleanup
  observed. Finished22.678s, both exactchars offline/4servicesrunning/DBhealthy.
- All77frozen host dependencies stillmatched; no production edits/new modelcalls.
  Journals are private test-world host stage, NOT claimed production volume path;
  stub summary views not realLLM cache/provider memory acceptance.
- Added [[scheduled-native-host-idle]], sanitizedlive/finalreadback/clockfailure/
  ownedresume records and refreshed [[goals-ledger]]. No wholemilestone acceptance.
  Native perception audit deleg_b7e38618 remains pending before real cognition.

## [2026-10-06 local] update | Perception audit found real cognition blockers
- Source-only audit nowcomplete: no currentparams/inventoryretention; host reports
  fictional full HP/SP, allplayer actors/fixeddistance/personalevel/emptyinventory.
  Ownaccount-ID chat can become event; legacy008E echo stilltagscharacter ID.
  No native self-reply loop or vitals observations claimed from static inspection.
- Deleg_7593d289 disjointstrictTDD: client/native_vitals helper/newtests versus
  hostselfchat drain/newtests. No DB/globalknowledge/inference or sideeffects in
  delegates; healthappintegration/nativeproof/reviews stillpending. Brains off.
- Parent baselineprobe refused to run currentclient because its accepted oldhash
  no longer matched duringimplementation. No unreviewed native client executed.
- Retrieved suppliedOptChat primarygist storage/tree sections, registeredsource
  ledger and saved optchat-supplied-source-recheck.json. Separate raw/tree streams
  do not make current session-note/nativeidleproof fullOptChat parity.
- Existing idlehost/nativearrival proofs remain scoped; no fullmilestone acceptance.

## [2026-10-06 local] update | Vitals/self-chat baseline green; health gate delegated
- Client retains selectedSELF0xb0 HP/SP IDs with explicit unreceived state and
  resetsnewtransport; pure strictquartet helper denies missing/invalid counts,
  notdefaultfullhealth.38newtests/100%helper statements+branches. RawHPpresentation
  still notdeathtruth; noinventory/class/actor/position claims changed.
- Self-chat ownaccountID andlegacycharID tags suppressed whilepeers/cursor preserved;
  12newtests/128implementerregressions. Inheritedsenderlessprovenance remainslossy.
- Parentactualcombined311tests+65subtests/100%helper at85gate, scopedBlackRuffstrict
  mypygreen; existingStarlettewarning retained. No native telemetry/cognition yet.
- Deleg_84fa4ae3 disjointindependentvitals review versus strictTDDhostprojection/
  readinessintegration. Client/helperfreeze excludesevolvinghostsource; explicit
  mockstatus fixtures mayneedadaptation, no productionfallback or assertionweaken.
- PublicOptChat retrieval completed through officialGitHubGist API/Nixcurl after
  extractionbackend andPythonCA failures; TLS verification kept. Currentstorage/
  tree heading lines98/137 deriveactualcontent, contenthash recorded. Existing
  journalproof notfullOptChat parity ormodelcallsavings.
- Nextacceptedstate remainsbrainsOFF pendinghostintegration/frozenreviews/native
  capture andremainingtruthfulperception. No fullmilestone acceptance.

## [2026-10-06 local] update | Native vitals review reconciled; stopped-reader RED
- Independentreviewer client/projection PASS208unique+65subtests/100%helper;
  parentmatched14currentpublicinputs andfiveexactreviewartifacts/JUnit. Hostsource
  excluded, no nativeframe orwholelegacyspikequality acceptance.
- Hostintegration21newcases reported; onlyexplicitFakeGameClient statusfixture
  added. Configuredroot120secondattempt timedout, no completedgate claimed.
- Parentactualoffline RED: stopped/disconnected/nosocket/noreader client withfull
  retainedquartet stillpasses_native_vitals iferrorlists empty. Failure preserved
  inhost-native-vitals-stopped-reader-red.log; no actualhost activation/probe.
- Deleg_d9e1508b strictTDD narrowguardrepair/newhosttests, thenfreshfrozenhost/selfchat
  review/wholegate required. CognitionOFF and otherperceptionplaceholders remain.
- New [[native-host-vitals]] frontierguide links exactevidence; protocolskill records
  source-shapedSELFstatus, unknownhealthdenial/positiveHPnotdeathtruth, transport
  readiness gap andaccount-vs-characterchat provenance. No wholemilestone accepted.

## [2026-10-06 local] update | Reader repair functional; complexity gate failed
- Scopedreaderrepair20newcases/41totalhost; implementer325combined/93.08% scope,
  guardchecks exposednativeflags/socket/reader, no error-swallowing/controlchanges.
- Frozenreviewdeleg_8408ed50 dispatched. Parentconfiguredcheck failed Xenon rankC
  in_native_vitals(maxB), exit201beforepytest/149hashesstable. Reviewersteered with
  actualfailure whiledependencyclosure keptfrozen; no sourceschanged/loweredgate.
- Separatelyconfiguredtasktest PASS2070unique+65subtests/94.57%, exit0/149public
  inputssamebeforeafterandidenticaltofailedchecksnapshot. ExistingStarlette/fork
  warningspreserved; 191.891s elapsed. Fullcheck isNOTpassed.
- Failedstaticandpassingfulltests preservedseparately, dispositionpassed=false.
  Minimalbehavior-preservingguardextraction/freshreview/fullcheck remain. No
  nativecapture/realcognition orwholemilestone acceptance.

## [2026-10-06 local] update | Host review failed quality only; minimal repair cycle1
- Completedindependentreview functionalityTRUE/overallFALSE:325host,104client,
  50adversarial physicalJUnitunique=479 reconciled; source149matched before repair.
  Security[]/logic[], onlyXenonrankCmaxBquality failure. No nativeacceptance.
- Dispatchdeleg_7d3443f8 repaircycle1: behavior-preservingsessionguard extraction,
  sameevaluationorder/opaqueexception/omitted-vs-explicitfakefield semantics,
  no tests/thresholds/client edits. Freshreview/fullconfiguredcheck follows.
- Parentpreservedfailedreviewandgates and compactexactcase reconciliation. No
  liveworldactivation/providers/privatefixture reads; allwholemilestones open.

## [2026-10-06 local] update | Full quality gate passes after minimal extraction
- Cycle1 apponlyguard extraction current4c99c3a9...; tests/other149-inputclosure
  unchanged, guardorder/opaqueexceptions andselfchat preserved. Implementer479
  cases/scoped93.11/helper100%, allstatic gates. OldC13->native_vitalsB6/helperB8.
- ParentactualconfiguredtaskCHECKPASS2070unique+65subtests/94.57%,exit0/allstatic
  gates/149stable/current,196.823s elapsed. ExactXMLandcurrenthashes matched.
  OlderfailedCcheck preserved separately. No complexity/coverage thresholds changed.
- Configureddependencyauditexit0/no known vulnerabilities found by thisrun; all
  selected sourcehashes unchanged afteraudit. Existing framework/fork/nosec notices
  retained, not universalsecurity orwholelegacyspikequality guarantee.
- Freshread-onlyfinalreviewdeleg_875a98fc pending; sourcefrozen. Hostacceptance
  withhelduntilreview, actualnativeframes/realcognition stillunverified/off.

## [2026-10-06 local] update | Final vitals review and passive native receipt accepted
- FreshfinalreviewPASS489unique (375+104+10),93.11% scope/helper100%,source149+
  whitelistandphysicalXML matched. Host/selfchat offlinecontractaccepted; failed
  earlierreviews/qualitygate preserved. Fullconfigured2070+65/94.57%/audit0 unchanged.
- User explicitlyauthorizedone passive2-existing-fixture probe<=60s/no restart,
  gameplay/inference/accounts/manualSQL/reset/debugprod edits. Fresh exactengine
  labels/volumeusers/images/ports/SQLidentity/offline guards verified beforelogin.
- RawterminalinspectJSONtruncation refused; directkernel lackingterminalDocker
  endpoint refused. Compactterminal-local parsing used; engineconfigunchanged.
- ActualnativeB0 IDs5/6/7/8 ->retained->host matchforboth HP42/MAXHP86/SP11/MAXSP20;
  nativephase0.053s,2PINchallenges/2successes,brains/workerloops/inference/actions0.
- Supportedcleanup andstalequartetdenial observed; exactnativeSQLbothoffline/
  savedpositions unchanged,4existingserviceshealthy. All149sourcesmatchafterlive.
- Onlyboundedreceivedvitals presentation accepted—notdeathtruth/realcognition or
  fullmilestone. No seeding/restarts/resets done. Nexttruthfulactor/progression/
  position/inventory work remains.
- Read-onlyactorfrontierdeleg_a46eee5a dispatched: compiledobjecttype/layout-to-kind
  sourceaudit andsmallestfutureTDD contract; no implementation/liveactions and
  no distance/position truth inferredfromdestinations.

## [2026-10-06 local] update | Actor presentation ambiguity; strict pure decoder TDD
- Read-onlyactorfrontiercomplete executedCPPsize/offsetof FD110/FE103/FF104,
  objecttypeu8@4/wireAID@5/separateGID@9; MAINshieldguard inactive. Parentmatched
  9sources+compiledflagshash, no liveactor observations. Currentactualclassname
  ScheduledAgent; auditproseNativeScheduledAgent corrected by parentaddendum.
- Wireobjecttypepresentation non-injective:0PCsprite canbemob/pet/NPC;5disguised
  PCself;6/12NPCnotmonster. No numeric/job/name/globalcatalog identity shortcuts.
- Deleg_caff0ce5 ownsONLYNEWpurestrictheader/presentationenum adapter+tests/report
  verticalTDD; existingclient/app/sourcefreeze unchanged forjoblevelreconnaissance.
  Presentationmetadata notActorRef/attackpermission; unsupportedknown/unknown raw
  values retained withNoneprojection. Fakecurrentdistance/position stillblockcombat.
- Self-progressionauditdeleg_c2cfe280 pending; no inference/liveactions delegated.

## [2026-10-06 local] update | Native progression source frontier and pure TDD
- Completedfrontierartifact read; parent5repo+7nativehashes match. Actual155-byte
  CHARINFOselectedjob/base/joblevel/slot authority derivedcompiler; B0level11/55
  emission resolved, class19enum notemitted. LOOK_BASE sprite appearancecannotbe
  promotedtoactualjob; gateafterinvalidation untilauthoritative refreshresolved.
- Source-auditor runningbeyondbrief steeredtofinalize existingreport, no source
  changes. First newtaskdispatch missinggoal refused; correcteddeleg_e2865580
  dispatchedNEWpureSnapshot/progressionmodule/tests only, existingclient/app frozen.
- VerticalTDDexplicitfreshness/receivedlevels/no persona default, firstbounded
  Novice0 allowlist/unsupportedraw retained-denied; notallclasses/currentjob/native
  proof. Concurrentactordecoder/presentationmetadata TDD stillrunning disjointfiles.
- No worldactions/inference or new milestone acceptance.

## [2026-10-06 local] update | Pure actor decoder813green; independent review dispatched
- Completedpureactorheader/presentationadapter andtests: parentactual813unique
  syntheticcases/helper100%statements+12branches under85gate. Exactprofileframe
  sizes/header/declaredlength, rawuint8falseyzero, separatewireAID/charGID,
  frozenpresentation-onlyenum andunsupportedNone; no identity/distance inference.
- Sourcehelpersha81140e81.../test02e21afb...; existingclient/app/domain unchanged.
  Independentreviewdeleg_c8bd79c9 freezescompletedactorslice only; concurrent
  progressionimplementation excludedfromreview'sdependencyclosure.
- ProgressionpuremoduleTDDstillpending; no actualactorretention/hostprojection/
  combat/nativeplay/modelactivation or milestone acceptance yet.

## [2026-10-06 local] update | Actor helper accepted; real-client retention TDD
- ActorpureindependentreviewPASS813unique+104probes/helper100%,15currentinputs
  matched/exactXML/CPPcompiledoracle readback. Source-onlynohost/combat approval.
- Progressionpuremodule47newcases; parentactual47unique/helper100%statements8
  branches gated85. Explicitfreshness/Novice0-known/currentlevels/no snapshot or
  persona fallback. No selected-client state orcontinuousjobfreshness supplied.
- Dispatcheddeleg_eea2e4d2: ownedactualclient actorparser/rawobjecttype retention/
  strictprofileframeintegrity +NEWtests; separateindependentpureprogressionreview
  excludeschangingclient/app source. Preservepose/IDs/vanish/deadlines/PIN/health.
  StandaloneNixpythonimportcompatibility requested withouttools/depsworkarounds.
- Existinghostkindplayer/dist1 stillunknown/placeholders, no actorcombat/brains/
  nativeeffects orwholegoal acceptance. Parentfreshcombinedgate followsstablecode.

## [2026-10-06 local] update | Pure progression review accepted; combined860green
- FinalpureprogressionreviewPASS67unique=47repo+20independent,100%statements/
  8branches/9frozeninputs currentmatched. Preliminaryfalsequality flag fromempty
  scratchclassname aggregation corrected usingphysicalXML; no sourcesrepaired.
  Parentsteer failedbecausechildalreadyfinished, notclaimedasdelivered.
- Parentcombinedpureactor/progression860unique/100%61statements20branches at85
  gate verified. Currentreceivedselection/epoch/jobfreshness stillcaller'sfuture
  authority; Novice0onlyallowlist, no classfromsprite orpersona fallback.
- ActualclientactorTDD stillpending; no source/progression-host/nativecombat/
  modelactivation orfullmilestone acceptance. Frozenpuremodelsacceptedonly.

## [2026-10-06 local] update | Actor retention implemented; import boundary repair
- Actor client worker completed raw objecttype retention and strict profile-frame
  validation. It reports71 new cases and1079 tests+65 subtests; those counts are
  implementation evidence, not a parent full-gate or independent approval.
- Parent matched14 public inputs, the new test hash and31 unchanged method ASTs.
  Only the actor-entry method changed; host, PIN, status and cleanup stay unchanged.
- Parent reproduced bare Nix Python standalone import failure: adapters package
  initialization eagerly imports HTTP providers, making the stdlib helper depend
  on httpx. No sockets, native services or provider calls occurred.
- Deleg_b5efe165 owns only adapter initializer +new import-boundary tests/report,
  with vertical TDD and lazy public exports preserving identities. No global
  installation, loader fallback or silent venv-only compatibility downgrade.
- Integration acceptance is withheld until standalone repair and frozen review;
  cognition/combat remain off and all six full milestones remain open.

## [2026-10-06 local] update | Standalone import repaired; full configured gate green
- Lazy adapter exports are implemented; the parent repeated bare Nix Python
  import and dummy constructor from outside the checkout successfully, without
  connections or provider instances. Eight public export identities stay tested.
- Parent reconciled the repair worker's physical1187-case JUnit and current code
  fingerprints. Dispatched independent frozen actor-client/import-boundary review
  deleg_b2df9b1c; it cannot edit code and no other source writer is active.
- Parent full configured CHECK passes3013 tests +65 subtests/94.64% coverage,
  all static gates,155 unchanged public source/test/config inputs. Physical unique
  JUnit counts and current fingerprints rechecked. Audit exits0, no known
  vulnerabilities reported in this run; temporary requirements file removed.
- Integration acceptance remains pending independent review. No native actions,
  bots' cognition or combat enabled, and no full milestone accepted.

## [2026-10-06 local] update | Actor/import scope accepted; native progression retention TDD
- Independent actor/import review passes1124 unique tests +65 subtests, including
  33 adversarial cases. Parent matched2869 current public dependencies and24
  artifact hashes, plus physical JUnit identities. Accepted bounded offline raw
  actor retention and public lazy exports only; no actor-kind/position/native proof.
- Legacy client Ruff47/mypy13 findings unchanged and not waived. Reviewer corrected
  its own mechanics/YAML dependency assumption; the failed harness is preserved.
- Dispatched deleg_6b2b24d8: selected native155-byte row/actual wire slot and matched
  returned character identity; received SELF B0 levels11/55; reset old selection
  on reconnect/disconnect. Only client +new tests/report owned. Parent owns any
  old synthetic routing-CID fixture corrections; guard must not be weakened.
- No current-job freshness guessed from appearance, no persona/historical-level
  fallback and no host projection or activation. Continuous class authority and
  native receipt remain separate. Previous3013+65 gate predates this evolving
  slice; fresh combined gates/review are required. All six milestones remain open.

## [2026-10-06 local] update | Selected snapshot and level receipt retained; full gate green
- Worker completed49 new tests for source-shaped selected row/slot, matched map
  routing CID, strict whole-list validation, SELF level11/55 retention and reset.
  Historical snapshot only: no job_fresh/current-class/host projection supplied.
- Worker combined435 passed/1 failed on obsolete ID11-discard assertion. Parent
  reproduced that exact RED and changed unsupported test parameter to12, keeping
  four unsupported cases. Added3 health-isolation cases: level receipts do not
  alter HP/SP or fill missing vitals. Production client unchanged by parent.
- Parent selected439 unique cases green; helpers100% statements/branches at85.
  Parent full configured CHECK3065 +65 subtests/94.64%,156 unchanged current public
  inputs, physical unique JUnit readback verified; all configured static gates pass.
- Dispatched frozen independent review deleg_1268de36, code read-only. Previous
  dependency audit passed; pins unchanged, audit not rerun in this phase.
- Initial worker failure/parent RED are preserved. Source approval still pending;
  native receipt, continuous job/look/warp freshness, cognition and gameplay remain
  unverified. No native services/accounts/inference changed; all milestones open.

## [2026-10-06 local] update | Selected snapshot/level retention accepted offline
- Independent review passes469 unique cases=439 repository+30 adversarial, no
  skips/subtests; vitals/progression helpers100% statements/branches. Parent matched
  2869 current public dependencies,27 artifacts and physical JUnit identities.
- Reconciled configured parent3065 +65 subtests/94.64% gate and156 current source
  fingerprints. Accepted bounded offline historical snapshot and raw SELF levels;
  native receipt/current class/warp/look freshness/cognition are not accepted.
- Spike Ruff47/client mypy13+packetdb2 debt remains. Existing constructor statements
  51→52, char branches31→32/statements108→111 explicitly preserved—not waived.
- Archived reviewer fake-allocator signature failure; correction changed scratch
  harness only. Created final-disposition report and [[native-self-progression]];
  updated index/ledger. All six full milestones remain open; no live effects.

## [2026-10-06 local] update | Renewed playing-world execution; real startup mismatch
- User explicitly requested continuation until completion with a populated,
  playing world. Recorded scoped owned-test-world execution direction; human
  accounts, debug/production and unrelated services stay protected.
- Fresh preflight: exact four owned services/volume users, healthy DB. First native
  receipt probe failed waiting for SELF11/55. Preserved that failure, then captured
  initial frames explicitly: both selectedclass0/base10/job10/CIDmatched, updates
  absent, normal same-map0091 and self weapon-look2. Both offline/unchanged positions,
  supported cleanup and four services healthy; no gameplay/inference in diagnostic.
- Dispatched disjoint actual TDD slices: session readiness + sequenced frames,
  wire gameplay observer/attack/loot/party chat, real model runtimes; public-map
  pathfinding/starter route in separate worker. Parent owns actual integration.
- SSH public-key denial observed, but direct Heavengraph HTTP health for both
  existing models succeeds. Steered runtime worker to use that existing path;
  health alone is not inference/GPU-utilization acceptance. No current full milestone.
- Ledger priority now actual playing population. Offline foundations are not the
  final result; startup baseline policy must be derived from source and provenance.

## [2026-10-07 local] update | Playing pipeline integrated; live blockers reproduced
- Existing scheduled host now uses native state/actions and real model providers;
  the playing CLI loads without fake fallback. Public species metadata remains
  separate from each agent's received map membership. Empty farm plans no longer
  suppress grinding. Explicit native .gat/cache identity passes10 new regressions.
- Wire repair201 cases are green; parent matched all eight frozen public inputs.
  Six missing framing IDs, initial deletion-barrier rearming, empty party chat,
  new test typing and epoch-scoped event/floor bounds are repaired.
- Configured whole CHECK passes3393 unique tests +65 subtests/94.57% coverage,
  with physical JUnit verified. Provider annotations and three obsolete raw-client
  constructor assumptions were corrected; endpoint/PIN/injected-factory identity
  assertions remain. Historical spike-wide quality debt is not waived.
- Independent final pipeline review passes1545 regressions +65 subtests but fails
  three of25 host probes: two cancellation origins leak a connected startup client;
  received sitting agents never obtain standing confirmation before walking.
  Both are blocking. Third-context TDD repair deleg_941320c0 is running.
- Reviewer mypy unreachable diagnostic is preserved; fresh parent src-only mypy
  passes. Reconcile exact commands/snapshots rather than erasing failed evidence.
- Fresh read-only engine preflight: four exact owned services/volume users and
  healthy DB. No autonomous native combat/XP/loot run approved or executed here;
  all six full milestones remain open. Updated [[goals-ledger]].

## [2026-10-07 local] update | Real autonomous travel and map-warp receipt
- User authorized the focused bounded-shutdown/origin-preservation contract after
  the automatic repair limit. Independent final contract review now passes on
  matching frozen source. Parent CHECK3444 +65 subtests/94.73%; audit no known CVEs.
- Preserved the obsolete waiting test's RED; strengthened it to assert resources
  retained while alive, bounded stop failure, then explicit termination and reap.
  No skips, gate changes or release-before-termination assertion relaxation.
- Actual existing two-fixture AgentHost used real Clef startup calls and native
  mechanical navigation. Completed241.9s travel run observed31/27 positions and
  southern warp to prt_fild08(170,375); exact SQL readback saved those field coords.
  Both clients cleaned up and both chars offline; all four owned services healthy.
- The earlier480s verifier was killed by its tool's420s limit before final report.
  Offline/saved-position readback is preserved, not mislabeled supported cleanup.
  Later runs save progress periodically and use bounded shorter durations.
- No combat/XP/loot/LLM escalation: EXP0, inventoryempty, no attack/pickup receipts.
  A45s reconnect preserved model-selected SOCIAL and traversed the return portal;
  arrival/post-warp progression then stalled. TDD source investigation deleg_96007390
  targets map-load ACK/active-state and source-supported position feedback.
- Evidence: playing-world-travel-only-autonomous-run.json; current field diagnostic
  playing-world-first-autonomous-run.json. Updated [[goals-ledger]]; no milestone closed.

## [2026-10-07 local] update | Matched gameplay provider latency and schema blocker
- Same synthetic11-question actual brain request, one loaded first plus20 warm
  repeats sequentially. Framework p50 5.404/p95 5.564s; Heavengraph .650/.718s.
  Framework device-wide activity peak100%; no remote GPU or quant parity proof.
- Hosted request rejected HTTP422/code5012: unsupported top-level
  goal_criterion_grind. Two bounded diagnostic calls confirm input validation,
  not authentication failure. Primary Cloudflare examples use model/state/questions.
- Disjoint TDD deleg_60aad21d owns decisions.py/contract tests; no native/model effects.
  Preserve original rejected benchmark, then rerun matched corrected payload after
  integration. Full benchmark remains incomplete; no population-scale claim.
- Added [[matched-playing-provider-latency]] and updated index; numeric raw samples
  and sanitized rejection in run/reviews/matched-playing-backend-benchmark.json and
  matched-cloudflare-failure-diagnostic.json. All six milestones remain open.

## [2026-10-07 local] update | Post-warp repair parent verification
- Pinned source confirms missing0x007D leaves same-server warped PCs outside the
  active map until LoadEndAck. The client now sends it only after valid0x0091 on
  an active connected socket; initial authentication and cross-server denial remain.
- Arrival confirmation can retry without an intervening receipt, at most3 retries
  paced1s apart. Exhaustion denies further motion; a requested destination still
  does not prove arrival. No readiness/alive promotion from sends.
- Parent reran14 focused tests: physical unique14, failures0/errors0/skips0; three
  critical source/test fingerprints match the completed implementation report.
  Evidence: native-map-lifecycle-parent-targeted.json; implementation report retains
  genuine RED/GREEN artifacts,564 selected regressions and measured legacy spike debt.
- Independent functional review deleg_5ae0a880 dispatched; no native reconnect yet.
  The3444-case whole gate predates this map repair. Updated [[goals-ledger]];
  combined gate/native combat/XP/loot and all six full milestones remain open.

## [2026-10-07 local] update | Combined gate, corrected providers and real town motion
- Map slice independently accepted582 cases including18 adversarial probes; exact
  critical hashes and physical XML matched. Final configured gate3483 +65 subtests,
  94.78% coverage,177 frozen source/test/pin files unchanged. Only inherited
  Starlette/httpx deprecation warning; numerical whole-spike debt still open.
- Corrected same11-question payload now succeeds21/21 requests per provider:
  Framework warm p50/p95 5.796/6.162s, Heavengraph .642/.710s, Cloudflare .374/.804s.
  Updated [[matched-playing-provider-latency]] and index. The Framework CPU quality
  suite ran concurrently; remote GPU/offload/quant parity unverified (SSH unavailable).
  Full hardware/population benchmark not closed.
- Parent-owned exact2fixture181.8s native run passes supported cleanup/offline
  readback with42/43 distinct received positions. Saved15667/15666 in Prontera.
  Both real Clef startups selected SOCIAL; no new post-login warp, attacks, damage,
  XP, loot or LLM escalation. Continuous movement is real; warp-ACK live acceptance
  is NOT implied. Updated [[goals-ledger]] and saved explicit acceptance flags in
  playing-world-post-warp-autonomous-run.json.
- User suggested mature open-source bot code. Primary OpenKore source research
  deleg_8df58447 inspects routing/combat/loot/goals and an optional standalone limbs
  backend, respecting license constraints, per-agent perception and pinned protocol.
  No third-party code incorporated into the application or executed. All six
  full milestones remain open.

## [2026-10-07 local] update | Controlled field run and two concrete repairs
- Operator-tagged GRIND intervention before producer startup, real Clef events,
  0.25s mechanical tick,300.3s bounded run. Both reached prt_fild08;99/137 positions
  retained and field coordinates saved after supported cleanup/offline readback.
- Reader failures/reconnects prevent uninterrupted/same-session claims. No attack,
  damage, XP, loot or LLM escalation. Corrected functional verdict tofalse and kept
  the original cleanup-only report as playing-world-controlled-grind-cleanup-only-original.json.
- Captured real model choices are grind; current same-goal explicit selection falls
  into the low-review heuristic and createsSOCIAL. Earlier 'Clef chose SOCIAL'
  statements inferred from final runtime goals, not raw choices. Scoped vertical
  TDD deleg_2f5ddf1f repairs only this precedence error.
- First passive field diagnostic preserved a harness cleanup failure (unsupported
  raw disconnect API). Corrected to actual wire.close; fresh owned/offline preflight
  then a one-fixture public-geometry route with zero model calls reproduces unknown
  0x007F for both readers, standalone and aftercoalesced09FD. Exactlysix bytes remain;
  pinned clif_notify_time/TickSend identifies the clock reply. TDD deleg_8bfafb06
  compiles its layout and adds strict framing only; unknown-ID denial retained.
- Reports: active-field-route-protocol-capture.json; passive-field-protocol-capture-cleanup-failed.json;
  playing-world-controlled-grind-run.json. Updated [[goals-ledger]], leaving all six
  full milestones open. Prior3483-case full gate predates pending repairs.

## [2026-10-07 local] update | Clock framing live regression and combined repair gate
- Explicit-goal author262 selected/33new; clock author274+65subtests/14new with
  executed native127/6/0/2/4 layout. Parent physical XML/source hashes match.
- Stable combined configured gate3530 +65subtests/94.83%,179 files unchanged.
  Inherited Starlette and fork-deprecation warnings retained. Independent combined
  review deleg_0dceaac8 running; scope approval/native combat remain distinct.
- Native route replay now parses19 clock replies per client over100s, no reader
  or dispatch errors, running transport before cleanup. Actual wire.close and
  exact offline readback confirmed; firstfixture saved170335, second173362.
  Evidence active-field-route-clock-regression.json; no model/attack/XP/loot claims.
- Public field spawn definitions exist; no hidden live locations fed to agents.
  Current patrol rerolls ±8tile target everymechanicaltick, causing local wandering
  rather than committed travel. OpenKore research was steered toward persistent
  route tasks; latest steer returned no-live-child, so no delivery assumed.
- Updated [[goals-ledger]]; all six full milestones remain open.

## [2026-10-07 local] update | Fail-fast name reply and recovered OpenKore report
- Independent goal/clock review601 +65subtests physically matched and current.
  Single-session unforced-goal probe stops after6.04s on missing0x0ADF, not concealed
  by reconnection. Supported close/offline readback confirmed; no combat/XP/loot.
  Pinned packedNPC/monstername header identified; name-family TDD deleg_48593d4e.
- Completed old OpenKore trace revealed report-builder approval timeout, not a
  missing research source. No silent retry. Clarify user explicitly authorized
  source-only finalization and said missed approval timeouts may be asked again;
  exact authority recorded openkore-report-renewed-authorization.json.
- Reauthorized executor produced report/note; corrected a too-short structured
  evidence quote, split citation sentences, and used an eight-cited-source final
  ledger while preserving broader reconnaissance. Strict/evidence verificationpass.
- Public pinnedsource51de1ddfc4449ae5217f6886de702f87ca934030 yields five designpatterns:
  route segments, target lock, acquisition-driven loot, portal legs, rest/follow.
  No bot code incorporated into the application or executed; license compatibility remains unresolved.
- Parent read randomwalk2440–2477: choose destinationwhenidle andqueue route.
  Per-agent committedpatrol target TDD deleg_dbaf2927 ownsourruntime; name codec
  owner ownspacketdb. Sourcegatesfreezeafterboth. Researchartifact
  open-source-gameplay-patterns.json and cited research.md; updated [[goals-ledger]].

## [2026-10-07 local] update | Name/patrol gate and first real attack choice
- Name author6 new/948 selected; patrol32 new/348 selected,95%module/100%responsibility.
  Independent read-only1300 cases including19 new adversarial probes physically
  matched with29 frozen dependencies; protected pending/standing AST unchanged.
- Parent configured task check exits0:3568 unique +65subtests,95.00%,181 frozen
  inputs stable; evidence playing-name-patrol-parent-gate.json. Legacy spike debt
  remains unwaived. No Git staging/commit or gameplay acceptance follows.
- Fresh owned-world/exact offline fixture preflight; single-session real Clef with
  no goal override rerun stops3.641s onunknown0x0088 position-correction packet.
  Native0ADF name replies now parsed. One fixture receives two eligible actors;
  Clef choosesattack and0437 request sent once. No damage/XP/loot/LLM acceptance.
- Both supported closes and exact offline readback confirmed. Failure preserved
  playing-world-name-patrol-run.json with independent execution/cleanup/observed
  flags. Earlier0x0ADF failure receipt remains unchanged.
- deleg_fbc03dd4 splits focused0088 compiler/TDD registration from read-only
  pinned active fixed-sender gap audit, addressing inherited-table coverage rather
  than guessing lengths or weakening unknown-ID rejection. Updated [[goals-ledger]];
  [[two-bot-live-limbs]] remains narrower than full playing acceptance.

## [2026-10-07 local] update | Compiled fixed-sender gaps and stopmove repair
- Stopmove author changes only0088=10 and its name;19 helper ASTs unchanged,
 11new/203selected physical tests pass. Parent matches dependency/source/artifact
 hashes, re-executes oracle136/10/0/2/6/8 and parses clean203-case XML.
- Source sender audit reports14 absent active fixed families: attack distance,
 existing ground items, casting/effects/cooldown/skill updates and party notifications.
 Parent reruns inventory binary, matches saved sizes and deduplicates14 IDs. Only
 captured dependency drift is the parallel0088 registration. No whole-table or
 actual scenario reachability claim; variable prefixes excluded.
- deleg_25ea277a owns only14 registry/name additions and new vertical-TDD tests.
 No source semantics, unknown-ID bypass, native/model/SQL or other-world effects.
 Reports native-stopmove-repair.json and native-fixed-sender-framing-audit.json.
 Updated [[goals-ledger]];3568-case gate is historical before these pending changes;
 [[native-self-progression]] and all broader live acceptance boundaries retained.

## [2026-10-07 local] update | Audited framing implementation frozen for review
- Completed14 separate source-backed RED/GREEN registry slices;33 new framing
 cases/243 selected passes,19 helper ASTs unchanged and no existing-entry overwrite.
 Parent matches reported artifact/protected hashes and parses clean243-case XML.
- Snapshot freezes183 source/test/pin inputs; packetdb hash89a3630ad446e06a1b1128bf96e0b6263874858311be3f529204e4818c5f8e31.
- Combined0088+14 registration independent review deleg_5d827fbb dispatched read-only;
 parent task check runs with physicalJUnit and unchanged coverage/statics thresholds.
 No native retries before both checks and fresh owned-fixture preflight. No source
 handlers, position/arrival/class/life/acquisition semantics or gameplay acceptance
 added. Evidence native-audited-fixed-framing-repair.json; updated [[goals-ledger]]
 and retained [[two-bot-live-limbs]]/broader acceptance separation.

## [2026-10-07 local] update | Compiler-derived framing accepted as an additional goal
- Independent fixed-framing264 physical +65subtests matched; parent3612 unique
 +65subtests/95%,183 stable inputs and actual task-check exit0 confirmed.
- Real unforced single-session rerun fails4.046s unknown00C0 at25 after07FB;
 supportedclose/offline readback, unchanged native XP/inventories. No damage/XP/loot
 acceptance. Evidence playing-world-fixed-framing-run.json; prior failures preserved.
- User asked for the compiler-derived explanation, then said 'sounds good' and
 'accepted as a goal'. Recorded compiler-manifest-direction.json; created
 [[native-packet-manifest]], updated [[goals-ledger]] and index.
- Parent full unchanged-header probe uses installed mapcppflags and existing source
 bundledryml/c4core/libconfig/Maria includes. Compilation exit0; actualoutput
 emotion192/7/0/2/6,stop136/10. No map.hpp deletion or guessedconstants. Artifact
 hashes native-manifest-full-header-preflight.json; no native effects.
- deleg_88c694ee: strict-TDD generator and disjoint read-only full sender surface
 enumeration. Offline first; no packetdb/runtime integration or world activation
 before independent review and combined gates. All six full milestones stayopen.

## [2026-10-07 local] update | Recover interrupted catalogue at exact RED frontier
- Original generator transcript endsinterrupted at400.88s; reportnotwritten. Parent
 actualowned-test rerun4pass/1failure: compiler dependency closure missing, physical
 JUnit preserved native-manifest-parent-recovery-red.xml. Existingfour working
 slices retained; no fabricated acceptance or runtime catalogue integration.
- deleg_4cd8d164 finishes only generator/newtests/report/provenance/validation; no
 native/parser/collector/world edits. Source-owning task resumedat frontier, not
 restartedfromscratch orduplicated byparent.
- Senderauditcompleted:430 structure rows,517 sendtokensites,366 unresolved entries.
 Parentmatches20 compilerartifacts pluspinnedpublicsources andphysicalcategorytotals.
 Theseareinventorycategories, not approvedframes/uniquemissingIDs orfull dataflowproof.
- Added native-manifest-parent-recovery.json; updated [[native-packet-manifest]]
 and [[goals-ledger]]. New code/fifthRED blocks currentwhole-suite acceptance until
 finishercompletes; historical3612gate predatesnewgenerator.

## [2026-10-07 local] update | Preserve framing migration baseline during finishing
- Late originalbatch reconciled: completedsender audit hash matches delivered
 ecb3eb29fd348006fee7ea7d989d2111ff0329994b57a23b1f8b232b8ba47fde;
 generatorinterruption alreadyrecovered bydeleg_4cd8d164. No duplicategenerator.
- deleg_9c48e822 audits actualclient/collector-used IDs against the completed
 compiler sender/numeric evidence, including fixedactoraliases, variableparty
 prefix, outgoingshuffle separation and login/char scope. Read-only; no parser,
 native orworld changes. Updated [[native-packet-manifest]].
- Cataloguefinisher still owns provenance/validation output; migration baseline
 serves [[goals-ledger]] beforeloaderintegration, not native/full-goal acceptance.

## [2026-10-07 local] update | Reproduced completed bounded generator catalogue
- Finisher preservesall5 originaltests andcompletesclosureRED;10physical tests
 pass/89.96%ownedcoverage, Black/Ruff/strictmypy/XenonBBA. Authorwhole-suite timeout
 preserved, no fullgateclaimed. Report native-manifest-generator.json.
- Parentmatchesowned/evidence hashes and10-case XML; independentactualCLI output
 byte-identicalgold3413a9078d6383e5d00de9c9e4aaace07d5bb6e64eba67679e04547b515ebe23.
 265uniqueentries216fixed49var+102unresolved; all469 recordeddependencies verified.
 Evidence native-manifest-parent-reproduction.json; not universalcoverageclaim.
- Completed185-file source/test/pin snapshot frozen; independent reviewdeleg_1a23a6a6
 and freshbackgroundparenttaskcheckwithphysicalXML underway. No catalogue runtime
 integration/nativeeffects. Updated [[native-packet-manifest]] and [[goals-ledger]].

## [2026-10-07 local] update | Generator review rejects trust and sender ambiguity
- Parentfullgateexit0/3622unique+65subtests/95% on185-file pre-repair snapshot.
 Independent37physical probes30pass7fail; realoptionsresponsefile/profileguard
 bypass emits261 rows labeledsameprofile. Generator remainsREJECTED, no runtime
 admission. No malicious/plugin/private-input execution or wronggoldrow demonstrated.
- Exactfindings: mutableevidence/compileroptions notauthorized bymetadata/hashes;
 firstheader/name matching unsound onshadow/reassignment/order; floatoffset/size
 metadata accepted. deleg_b1f2d2eb ownsautomaticrepaircycle1onlythreefindings/TDD.
- Migrationauditreadonlyhashescurrent,97candidateIDs/44receivedliterals; four
 fixed-versus-variable differences09FD/FE/FF/0A1C requireexplicitmigrationreview.
 No model/native/world changes. Reports native-manifest-parent-review-rejection.json,
 manifest-generator-parent-gate.json, native-manifest-migration-baseline.json.
- Parentverificationinitialrelativepath lookup failed; corrected torepo-root lookup,
 no source/scope change. Updated [[native-packet-manifest]] and [[goals-ledger]];
 fullsixmilestonesremainopen, greenconfiguredgate doesnotwaiveindependentrejection.

## [2026-10-07 local] update | Generator review-repair physical evidence frozen
- Reconciled missedlatecompletion afterruntime interruption. Cycle1repairverified
36physicalcases94.76%coverage; ownedsource/testhashes and RED/GREENXML match.
No originalfailedreport/gold deletion. Native/runtime source unchanged.
- Exacttrustedinstalledevidence+Nixcompiler bindprecompile; responseprobes reject;
bounded lexicalscope/order/reassignment nowunresolved; variable offset/width/min
exactinteger. Conservativeclif_additem/tradeadditem resets marktwo rows unresolved:
263resolved214fixed49var+104unresolved, honestshapechange retained.
- Independent rereviewdeleg_86d5a7cf read-only and freshparenttaskcheck queued on
185-file freeze. Previous3622gate coverspre-repair snapshot, notacceptance ofthisfix.
- Updated [[native-packet-manifest]]/[[goals-ledger]]. No loader integration or
new native effects; awaitreviewandcombinedgate before explicitmappingmigration.

## [2026-10-07 local] update | Second and last automatic recognizer repair
- Cycle1parentfullgateexit0/3648unique+65subtests/95% onstable185files.
 Re-review71independentcases68pass3fail:lambda parameter shadow andprefix++/--
 header mutations. Original37and36authoredcasespass; optionsspoofingnowblocked.
- Parentmatchesallrereview artifacts andexecutescompiled C++counterexample output
 2/66,0/66,2/4 (header/length). No pinnedmatchinglambda/prefixwrites found;
 no provenwrongcurrentcataloguerow, yetfailclosedcontract remainsrejected.
- deleg_c786aebb ownsrepaircycle2of2 ONLYthesefindings. After furtherrejection
 stopautomaticrepair/requestuserdecision. Originalrejections/counterexamples/gates
 preserved; no runtime/packetdb/native/model/SQL changes.
- Saved manifest-repair1-parent-gate.json; updated [[native-packet-manifest]] and
 [[goals-ledger]]. AllsixmilestonesandlivecombatXPlootacceptance stillopen.

## [2026-10-07 local] update | Final bounded recognizer repair awaiting independent verdict
- Cycle2finishes43physicalownedcases/94.81%coverage; all71 previousprobes re-executed
byrepairer GREEN. ParentmatchesphysicalXML hashes/source/test fingerprints; only
associated_body existingASTchanges, trustedcompiler checks/original36testAST stable.
- Lambda-containing uncertainbindings andprefix rootedmutations remainunresolved;
real263/104 cataloguebytes998f7163fa650a1c71f7206415927e16257f9faf8211fd8f9946df63754d338b unchanged.
Repairreport native-manifest-generator-cycle2-repair.json; notindependentapproval.
- deleg_e885e556 finalreadOnlyreview andfreshfullparentgate on185-file freeze.
No furtherautomaticrepairs afterrejection; parentmustrequestuserdecision. No
runtime/PDB/native/model/SQL effects. Updated [[native-packet-manifest]]/[[goals-ledger]].

## [2026-10-07 local] update | Final catalogue review rejects; stop automatic repair
- Fresh independent137physicalcases/ninefailures: lambda syntax variants,
parenthesized writes and helper/reference/pointer escapes. Parent verifies162
artifact hashes and re-executes allninevalid-C++ witnesses (2/4 or2/66).
- Current pinnedcatalogue remainsbyteidentical; no wrongcurrentrow established.
Configuredgate3655+65subtests/95% on185stablefiles cannotwaive semanticrejection.
- Recorded manifest-cycle2-parent-gate.json; created [[native-packet-manifest-review-blocker]],
updated [[native-packet-manifest]], [[goals-ledger]] and index. Bothautomaticrepairs
exhausted; stopimplementation andrequestuserarchitecturedecision. No runtime/world changes.

## [2026-10-07 local] update | User authorizes standalone AST/hybrid feasibility
- After trade-off discussion, exact UI choice: Proceed with the offline AST/hybrid
experiment. Saved native-ast-spike-authorization.json; no production migration or
third automatic generator repair authorized. Prior failures/evidence preserved.
- Created spikes/007-native-packet-ast README and tiny public-only toolchain flake
using unchanged root nixpkgs pin. Actually executed offline shell: Clang21.1.8,
GCC16.2.0, Python3.14.7;185productioninputs hash-matched and frozen.
- deleg_241d374a owns disjoint compiler/profile and AST-binding experiments.
Synthetic fixture proof, real sender extraction and runtime acceptance are separate.
- Created [[native-packet-ast-spike]], updated [[goals-ledger]], index and
[[native-packet-manifest-review-blocker]]. No bot/world/model/SQL effects.

## [2026-10-07 local] update | AST feasibility partial; configured-source authority frontier
- Both workstreams PARTIAL. Parentverifies44compiler+206binding artifacts and185
productioninputs; reruns3compiler+10binding tests, freshClangrealemotionAST andallnine
formerfailureCLIcases(unresolved) plusone admittedsafe case.
- Parsed30case records:27unsafe denials,1of2safe admitted;23freshGCC oraclematches.
Parentcount harness initially assumed uniformoptionalfields/casegroups; corrected
missingfailed-header fields andfresh-vs-prior oracle groups withoutwaiving outcomes.
- Criticalprofileguardfailure retained: upstreamcustomheader definesobfuscation,
installedapplyruntime script appendsundef. GCC-preprocessedClang route alsofails.
No profileoverride, configuredsource edit, productionmigration or world effects.
- Saved native-ast-parent-reconciliation.json; updated spikeREADME, [[native-packet-ast-spike]]
and [[goals-ledger]]. Read-onlyinstalled-sourceauditdeleg_f36704d3 nowrunning;
exactconfiguredclosure authority is the next frontier, not another classifier patch.

## [2026-10-07 local] update | Configured-source audit verified; public replay underway
- Audit c70312d5b1bd6a3e80f85453461851c85019fb4d73b6c82b29169120ecca1567 verified
against immutable transform/header/profile-script/derivation and retained installed
evidence. Predictedcustomheaderbytes hashedinmemory; original185productioninputs stable.
- Corrected source explanation: config/packets.hpp definesOBF/WARN; customheaderis
late empty customization beforeinstalledappend. Builtheader/sourcearchive absent in
boundedinstalledoutput inventory, notuniversalstoreabsence/binaryequivalenceproof.
- Parent records native-ast-profile-replay-scope.json withinexplicitofflineexperiment:
newpublicscratchcopy, retainedCore/header and exactappendthreepaths only. Delegate
3a238a19 owns newprofile-replay subtree +evidence; profile/layout/realAST checks pending.
No source-store/prod/runtime/world mutation, serverrebuild orprofileflagswaiver.
- Updated [[native-packet-ast-spike]] and [[goals-ledger]]; oldfailedguards/rejections
remain intact. No gameplay or fullmilestone acceptance.

## [2026-10-07 local] update | Reconstructed profile/layout/AST replay reproduced
- Authorprofile-replay report5dfd2f0620a69e02f2119d8e4f9e07a41c44a59c86dbbe282222d943bc73c5b2
boundedVALIDATED. Parenthashes106artifacts, runsrealCLIexit0 andfourunitmethods;
physicallychecks3206copiedfiles, exactly2modified+1added. Fingerprint matchesauthor.
- EightGCC/Clang×fourroleprofiles matchactualinstalledJSON; source-basedemotion192/7,
STOPMOVE136/10 offsetsandFD110/FE103/FF104 sizes reproduced. Three filteredASTs
underreconstructedprofile; originalupstreamnegativecontrol staysfailed intentionally.
- Capturedimmutableparentresult byCLIreturnedroot, notracinglatestpointer; archived
pointerbefore rerun. 189criticalsource/authorityinputs stable. No source-store,
production/runtime/worldchanges orhistoricalbinaryequivalence claim.
- deleg_3d442bb5 independentlyreviewsboundedexperiment; profile/layoutsuccess isnot
senderidentity/dataflow/fullcatalogue approval. Saved native-ast-profile-replay-parent.json;
updated [[native-packet-ast-spike]]/[[goals-ledger]]. Sixmilestonesremainopen.

## [2026-10-07 local] update | Bounded profile proof approved; real sender/sink tracer
- Independentreview90f8f0d5c25de1e74eefdcc22bed664269ff76d0da09e756cc0d1a9eb53f580a
passesONLYprofile/layout/selectedAST. Parentverifies22linkedhashes,44freshcommands,
12precompilerAPInegativecases+12realCPPguardprobes,189criticalfiles unchanged.
- Recorded native-ast-profile-replay-approved.json; oldgenerator remainsrejected,
no realsender orcatalogue admission. Saved native-ast-real-sender-scope.json under
authorizedofflineexperiment. No production/world/SQL/model/native effects.
- deleg_710856c6 owns new sender-proof TDD realemotionidentity/header/send/sizeof
tracer and independentreadOnlyclif_send sink/helperaudit. Candidateonly, audited
sinknotyetadopted; no bodyhash-onlyshortcut or arbitraryCPPdataflow promise.
- Updated [[native-packet-ast-spike]], [[goals-ledger]] and parent007README.
Fullsixmilestones/combatXPlootacceptance remainopen.

## [2026-10-07 local] update | Real emotion candidate; conditional sink frontier
- Parentverifies158sender artifacts bystreamhash (fullAST~2.12GB),8sinkcompileroutputs
and189unchangedinputs; reruns4unitmethods+actualCLIemotion. Var/Field/header/send/
sizeof IDs joinedfromonefrontendinvocation, freshGCC192/7/offset0,2,6; candidatenever
setssemantic/runtimeadmission.27ownedcompilednegativesunresolved,30previousretained
cases notmiscountednumericstructuralcoverage. Name/sitting unresolved.
- Sinksource/activeASTaudit describes12memcpy sites unchangedbuf/len copy/queue
requests,notdelivery/recipientcounts.7explicitunresolvedgroups; nullpo macroinactive,
getSCE cachemutation noted, returningzero notreceipt. No sinkexceptionadopted.
- deleg_6b515863 performs candidate/auditindependentreview and narrowprimaryspec
variadic-pointercontract research; no patch/adoption. Parentreconciliation saved
native-ast-real-sender-parent.json; updated [[native-packet-ast-spike]]/[[goals-ledger]].
- Currentgen/runtime/worldstate unchanged; allsixmilestonesremainopen.

## [2026-10-07 local] update | Candidate facts retained; recognizer rejected and scope decision
- Independentreview rejectsnewtracer3compiledcounterexamples:uncheckedfinalsend
argumentsmutateheader, mutableglobalH treatedconstant, unsupportedfloatingcast.
Exactpinnedemotionidentity/layoutfacts andfactualsinkauditverifiedonly; general
recognizer remainsunapproved. Parentmatches82reviewartifacts and189criticalinputs.
- SeparateofficialC++17/C11specassessment pointerqualification/type mismatches in
AREA callback; assemblyprobe notportabledefinedness/receiptproof. VerifiedPDF/text
andprobe source/assemblyhashes. No observedserverfailureattributedtothisanalysis.
- Saved native-ast-sender-review-blocker.json; pauseimplementation for narrowtracer
fix/scratch-onlycallback experimentdecision. No originalgeneratorrepair, callback
patch, runtime orworldeffects. Updated [[native-packet-ast-spike]]/[[goals-ledger]].
Fullsixmilestonesremainopen.

## [2026-10-07 local] update | Fresh tracer-fix and scratch callback experiment authorization
- UserUIchoice Authorize tracer fixes and the offline callback experiment. Saved
native-ast-tracer-callback-renewed-scope.json; thisdoesnotauthorizeoldgenfix/server
packagebuild/deploy/installedbaseline/rootpin/worldchanges orsinkadoption.
- deleg_5850c4a0 ownsdisjointnewprototypeL1-L3tracerTDDrepair andscratchsource
callbackqualificationtrial. Exactconstpointerretrievals andcompiler/typebridge
checks only; originalsource/mismatch/failureevidence intact, no UBprobeexecution.
- Updated [[native-packet-ast-spike]]/[[goals-ledger]], keptallmilestonesopen.
Results/parentreplay/freshindependentreview pending.

## [2026-10-07 local] update | Tracer repair and callback trial parent replay passes
- Parentverifies234tracerrepairartifacts/49callbackartifacts; reruns10tracer +5
callbackunitmethodsandbothactualCLIsexit0. Tracercandidate192/7identity unchanged,
L1-L3guardfixes authoredseparateRED/GREEN; no semantic/runtimeadmission.
- Freshcallbackphysical3206files onlyclif.cpp differs/fourqualifiedretrieval-local
substitutions. GCC/Clang wholeTU parse +definedlocal7bytecopy/len7/AREA2probe pass;
originalUBretrievalnotexecuted andbaseline/installedsource unchanged. U2-U7 remain.
- Capturednative-ast-tracer-callback-parent-replay.json,198criticalinputs stable;
deleg_9be3924d independentreview running. No serverbuild/deploy/rootpin/worldeffects.
- Created [[native-packet-tracer-callback-trial]] tokeepmainspikeguideunder200lines;
updatedindex, [[native-packet-ast-spike]] and [[goals-ledger]]. Oldfailurespreserved;
allmilestonesopen.

## [2026-10-07 local] update | Callback trial approved; last record-shape repair
- Combinedreviewa0ea7d5ce2e8dda0b33eb3d06d6e238cd7ee793364ad09213d9e7e2c24605971
approvesONLYscratchcallbacktypes/fullTU/localbridge; rejectsnewtracerL4unionoverlap.
Parentmatches87reviewartifacts/198criticalinputs andre-executesdefinedGCCfixture:
metadataid1size4offset0,0; bytecopiedsent_header2size4, noinactiveunionmemberread.
- Exactpinnedemotionfacts remainverified; genericunsafeclaim cannotbewaived.
Saved native-ast-tracer-callback-review-reconciliation.json. deleg_b626625d owns
lastnewproto repaircycle2of2 onlyunsupportedrecordshapes. Originalgen/callback/
package/runtime/worldunchanged; anotherfailedreviewrequiresstop/userdecision.
- Updated [[native-packet-tracer-callback-trial]]/[[goals-ledger]] andprotocolskill
record-storage lesson. Boundedcallbackapproval isnotdeployment/sink/catalogue or
fullmilestoneacceptance. Initiallogpatchnonuniqueanchor wasrefused, thennarrowed.

## [2026-10-07 local] update | Last record-shape repair replay; quality regression blocks
- Finishedrepairreportedcd12969e69be3200bcbb3c7c7293637a18eafd2eb7c73c2b97d6f4facd5ca4
selfscopepasses but overallpassedfalse duequality. Parentmatches381artifacthashes,
195nonownedstable, reruns14unitmethods andactualCLI: C0candidate192/7 preserved.
- Independentlyreruns6baseline/currentqualitycommands offlineNix: Blackfailsboth,
Ruff150→189,my py88→102. Additional39Ruff/14mypy diagnosticsnotwaived.
- Saved native-ast-real-sender-record-shape-parent-gate.json; newfinal198input
snapshot stable. deleg_8a6b0d13 finalindependentread-onlyreview; automaticcycle2of2
exhausted, no thirdrepair. Callbackqualificationboundedapproval unaffected,
no oldgenerator/serverpackage/runtime/worldchanges; allfullmilestonesopen.
- Updated [[native-packet-tracer-callback-trial]] and [[goals-ledger]].

## [2026-10-07 local] update | Final tracer rejection; stop for explicit decision
- Review128e00e3557b57f636506cce6f9e420c7c85596acd92e881b55f121a7852934f rejects
supportedgrammar+quality. Uniondenialcorrect, butfieldlevelPackedAttrstilladmitted
contraryexplicitrequiredboundary; realfixtureheader1correct, NOTfalseheaderexploit.
- Parentmatches275reviewartifacts/198criticalinputs andrerunsactualASTtrace/defined
fieldpackedbinary: candidate1size6/offset0,2; sent_header1size6. Parentharnessinitial
TUdict/listAPI mismatchcorrected usingactualrootinner; no tracer/source changes.
- 20independentcompiledprobes/19expected; all14unitmethodsandrealC0factsretained.
Additional39Ruff/14mypy andbaselineBlackfailure unwaived. Bothautomaticcyclesdone;
saved native-ast-real-sender-final-blocker.json andPAUSED foruserdecision.
- Updated [[native-packet-tracer-callback-trial]]/[[goals-ledger]]. No thirdrepair,
thresholdwaiver/oldgeneratorfix/serverbuild/deploy/runtime/worldeffects. Separate
callbackqualificationboundedapproval persists; allfullmilestonesopen.

## [2026-10-07 local] update | Explicit user-authorized bounded cleanup
- UIuserchoiceexact: Authorize one bounded cleanup and fresh review. Saved
native-ast-real-sender-explicit-cleanup-scope.json. Allowsfieldpackingdenialand
format/type-only tracer/testedits preservingbehavior; no thresholdsuppression.
- deleg_5bf1aae8 owns3prototypefiles/newcleanupreportandprivateevidence ONLY.
Exactlyoneexplicitcleanupattempt; exhaustedautomaticallowanceNOTreset. Nooldgen/
callback/CLI/pins/package/runtime/worldchanges. Ifreviewfailsstopfornewdecision.
- Updated [[native-packet-tracer-callback-trial]]/[[goals-ledger]]; parentreplayand
freshindependentreview willdependoncompletedauthorresult. Allmilestonesopen.

## [2026-10-07 local] update | Explicit cleanup partial; parent quality replay
- Author093c66b90b947e74d50c8c8660d5048c78625de3fdac80447dca150e87255d2d
reportsfieldpackingREDGREEN,15tests/14normalizedtestbodiespreserved,20/20freshprobes.
Parentverifies317artifacts/195nonownedstable andreruns15tests+actualC0CLI192/7.
- ParentqualityattemptBLOCKEDapprovaltimeout, codeNOTexecuted. Reviewersteerto
avoidblockedoutcome failsnolivesubagent; no effectclaimed. UserUIrenewsqualityONLY
Authorize the read-only quality-check rerun. Thenparent6commandsactuallyrun:
Blackclean,mypy0,Ruff67; kinds andcomplexity27/29/101→29/31/110 stillregressions.
- Saved native-ast-real-sender-explicit-cleanup-parent-gate.json;198reviewinputsstable.
Freshindependentreviewdeleg_efa050bc notificationpending. No furthercleanupgrant/
server/runtime/worldchanges. Updated [[native-packet-tracer-callback-trial]] and
[[goals-ledger]]; overallfalse, allmilestonesopen.

## [2026-10-07 local] update | Candidate scope passes independent review; quality blocked
- Independent59d25ddd5baa159c716e1131582f8c645031ce2ae6d0a9c7a192762200635ed2
candidate_scopePASS/securitylogicempty, qualityFAIL/overallfalse.15methods/8fresh
compilerprobes match; original14bodies/helpers normalizedpreserved. Parentverifies
203reviewartifacthashes/198frozeninputs. Fieldpackingdenied; realC0candidateintact.
- Black/mypy clean; Ruff67 remainingkinds andtracecomplexityunwaived. Saved
native-ast-real-sender-explicit-cleanup-final-blocker.json andPAUSED foruserdecision.
Previousgrantformat/type-onlyused; extractinghelpers or equivalenttestassertion
style requiresnewexplicitgrant. Noautomaticbudgetreset/additionaledits.
- Updated [[native-packet-tracer-callback-trial]]/[[goals-ledger]]. SinkUNREVIEWED,
semantic/runtimefalse, allmilestonesopen; no server/package/worldchanges.

## [2026-10-07 local] update | Explicit quality-only structural refactor grant
- ExactUIuserchoiceAuthorize quality-only refactoring and fresh review. Recorded
native-ast-real-sender-quality-refactor-scope.json; oneattemptcoherenthelper
extraction/equivalentassertionsandtestnames, preservingbehavior/grammar.
- deleg_2e14b435 owns3prototypefiles+newreport/privateevidence. UnchangedBlack/Ruff/
strictmypy mustclean; freshcompilerbeforeafterequivalence/scenarios/strength and
actualC0CLI required, thenparentreplayandfreshindependentreview. Noautomaticreset.
- Updated [[native-packet-tracer-callback-trial]]/[[goals-ledger]]. NoCLI/pins/oldgen/
callback/serverpackage/runtime/worldchanges or qualitysuppression; failuresstop
foranotherdecision. Allfullmilestonesremainopen.

## [2026-10-07 local] update | Quality refactor parent scoped/root gates pass
- Author0e26557fa31bb6a895a30ce034db43482c7ffe7d751d4a350485c2fc731a2cbc
selfpasses8coherenthelpers andequivalent15scenarios;40samefreshASTcomparisons.
Parent411artifacthashes/195nonownedstable andreruns15scopedmethods/actualC0CLI.
OwnedBlack/Ruff/strictmypy all0. No suppressions/settingschanges.
- Actualconfiguredtaskcheck3655physical+65subtests/95%,0failures/errors/skips,
oneStarlette/httpxdeprecatedtestclientwarning. Audit0reportsnoknownvulns;tempremoved.
TinyASTshellmissingtask andlegacy nix-shell--offlinefailures retained; successful
modernofflineNixshellsamepubliclockednixpkgsinput suppliesgo-task/uv, no pin edits.
- Saved native-ast-real-sender-quality-refactor-parent-gate.json;198inputsstable,
deleg_9f16726d freshindependentreviewrunning. Combinedhelperextractionslicelimit
isdisclosed(notfabricatedindividualruns); no Git/server/runtime/worldeffects.
- Updated [[native-packet-tracer-callback-trial]]/[[goals-ledger]]; fullgoalsstillopen.

## [2026-10-07 local] update | Independent bounded tracer/quality approval
- Review36274d795343691d9a37f99ea467eb289ea457a22e99c3ede0fad5b283a73b87
PASScandidate_scope/ownedquality withsecuritylogicqualitylists empty. Parentmatches
326reviewartifacthashes/198inputs. Independent15methods/20freshClangGCCprobes/
40whole-resultdifferentials andscenarioassertionstrength validated; actualC0intact.
- Recorded native-ast-real-sender-quality-refactor-approved.json ONLYboundedoffline
candidate+quality; pairedparentfullcheck3655+65/95% andaudit0 previouslyverified.
Combinedextraction-sliceprocesslimitation remainsdisclosed, notperhelperhistory.
- Updated [[native-packet-tracer-callback-trial]]/[[goals-ledger]]/index. Checkpoint
completebutoldgeneratorrejected, callbacksourceauthorityseparate; sinkUNREVIEWED,
sendersemantic/runtimefalse andall6milestonesopen. No Git/server/package/worldchanges.

## [2026-10-07 local] update | Move from approved tracer to send-path closure
- Currentstandinggoalcontinuation promptsnextconcretestep: READONLY remaining
allocator/FIFO andcallbacklifetime sourceaudits, notmoretracerrepair/unsafeactivation.
Parentmatches20publicdependencyhashes/198frozeninputs; Gitmain/profilepinsunchanged.
- Recorded native-ast-sink-followup-scope.json; deleg_69a1129e ownsdisjointU2/U3/
relevantU6memoryFIFO andU4/relevantU5lifetime reports+privateevidenceonly. Exact
emotionAREA+optionalSELF; U7otherrecipientroutes outscope. U1originalvarargs
mismatchretained; qualifiedscratchvariant separate, no sourcefingerprintstitch.
- Created [[native-packet-sink-closure]], linkedindex/[[native-packet-tracer-callback-trial]]
and[[goals-ledger]]. Sourceauditscannotimplyqueue/receipt/fullmilestoneacceptance.
No sourcepatches/packagebuild/deploy/runtime/world/model/SQLchanges.
- RetrieveduserOptChatgist throughwebsuccessfully; contentavailable, no newmemory
implementation or behavioral adoption fromthatretrieval.

## [2026-10-07 local] update | Conditional allocator/lifetime audits parent verified
- Memoryreport2c057201a4a95f443803733aeb76d6fea935567a5d315b6fa1f4e29e25b04398:
U2/U3invariantsrequired, U6conditionalcopy/capacityonly. Lifetime3e922db577c20c6b29a8c3243f454fa6cbaf87161662055e1585002d935de9ce:
normalcallback/unlock/automaticporder, butcapacity-fullimmediatedestroywhilelocked,
exceptions/reentrancy/concurrency/destructor/DBMap/skilldispatch remainfrontiers.
- Parentmatches518dependencyhashes/18memoryartifacts,35exactsourceexcerpts/15
activebodyranges and7lifetimeoutputcommands;198criticalinputsstable. Freshparent
GCCmacro+mapfreeblockASTcommands0,17allocatorvaluesmatch, immediatefreebranchactive.
TheseareconditionalSOURCEfacts, no runtimecases/receipt/sinkapproval.
- Saved native-ast-sink-followup-parent-reconciliation.json; deleg_2f026be2 fresh
independentfactualreviewrunning. No recursiveaudits/codefixes/waivers automatically.
Updated [[native-packet-sink-closure]]/[[goals-ledger]]; allfullmilestonesopen.
- Evidence correction: previousOptChatretrievalstatementisnotbackedbyasavedfetch
inthisexchange; treatthatlineasunverified. No newmemoryadoptionreliesonit.

## [2026-10-07 local] update | Prepare staged offline package decision; retrieve OptChat
- Usercontinuesstandinggoal. Readactualnix/playable-worldflakeandguardedpatcher;
existingrecipebuilds3roles, appliesCore/runtime-root/customdefines butnocallbackfix.
Created [[native-callback-package-plan]] StageAseparateofflinequalifiedpackage,
StageBframing/adoption/testworldNOTauthorized. No source/packagebuild/deploychanges.
Independentfactualsinkreview hasno liveworker; awaitingnormalnotification,notpolled.
- ActualOptChatfetch: web_extractfails(search-onlybackendcannotextract); official
GitHubGistAPIviaurllibHTTP200 succeeds, optchat.md untruncated, observedrevision
f51fe5c910427fd6f384d22823140b1693c76207. SavedprivateAPI snapshothashad374acffe57edc0d9401cd9d6773d71240bb34b61c5e5a412a0c4c823ff2e9b.
Readactualspecprefix; no followingwebinstructions or newmemoryimplementation.
- Initialretrievalmetadatawronglysaidweb.run beforeafetch; correctedactualmethod
andfailurehistoryinrun/reviews/optchat-reference-retrieval.json. Priorunverified
claimnowexplicitlysupersededbyrealAPIoutput. No durability/gameplayclaim.
- Updatedindex/[[native-packet-sink-closure]]/[[goals-ledger]]; allmilestonesopen.

## [2026-10-07 local] update | Explicit offline callback-qualified package grant
- ExactUIchoiceAuthorize the offline callback-qualified package variant. Saved
native-callback-qualified-package-scope.json with5canonicalpublicfilebeforehashes.
StageAONLYfourreviewedcallbackpointercorrections+guardedTDD+offlinebuild/profile/
source/early-refusalevidence andfreshreview, unchangedpins/profiles/Core behavior.
- deleg_293759b7 ownsnewnix/playable-callback-qualified, oneguardedpackage testfile
andnewbuildreport/privateevidence. No canonicalpackage/oldreports/generator/CLI/
tracer/runtime/Compose/privateworldchanges. No deploy/restart/engineimageimport/
serverinit/model/SQL/nativegameplay; all6milestonesopen.
- Updated [[native-callback-package-plan]]/[[goals-ledger]]. Existingfactualsource
reviewawaitsnormaldelivery; packagebuildindependentoftheunadoptedsourceinvariants.
Newartifactreview willnotclaimcanonical/semantic/runtimeadmission.

## [2026-10-07 local] update | Conditional sink audit factual review approved
- Reviewba257498fac8ab56f552231307084cfb585b075d378c339515024aafee8ecc50
PASSONLYfactualconditionalbounds/provenance. Parentmatches5mainreviewevidence
hashes/198frozeninputs; recorded native-ast-sink-followup-factual-approved.json.
No allocator/ownership/lifetime/indirectcallee invariantdischarged. OriginalU1
mismatchpreserved, scratch/newpackagevariants separate. Sink/runtimefalse.
- Lifetimeauthor412.223/360s andreviewfive-minute-targetoverrunremain disclosed,
notprocedurallyapproved/waived. No source/runtime/worldchanges fromthisreview.
- Updated [[native-packet-sink-closure]]/[[goals-ledger]]/index. SeparateStageA
packagebuilddeleg_293759b7 stillauthorizedofflineonly; no deployedfix/fullmilestone.

## [2026-10-07 local] update | Offline package build exits0; parent ELF readback
- Child-ownedproc_a064bec2cdd7 Nixbuildexit0. Parentparsesactualbuild.stdout/exit,
readsexactreturned/nix/store/0w1nfsmj8gaipcidhgx2nkg4axqxcbbr-rathena-playable-callback-qualified-20180704-e985006171d2-callback-qualified output.
All3roles executableELFheaders/SHA256s physicallyverified; no binaryexecution byparent.
- Saved native-callback-qualified-package-build-receipt.json ONLYbuild/artifact
presence. Steerqueued toauthorfinishsource/profile/type/guardtests/earlydiagnostics;
no claimofalreadydeliveredsteer or independentpackageapproval.
- Updated [[native-callback-package-plan]]/[[goals-ledger]]. Remainingauthorchecks/
freshreviewpending; no deploy/restart/imageimport/runtime/worldactionauthorized.

## [2026-10-07 local] update | Offline qualified package parent full regression passes
- Author16289829c59bd8d82e08c00ee654564193a229bc522fb0f27df943ed9d3a2922
completesStageAselfverification. Parent77evidencehashes/23installedfiles/3206actual
publicsourcefiles verified; onlyclifcpp4subs, trialclosure1f2d...;10generatedMakefiles
explicitlyaccounted. Canonicalprofiles/recipes/Core/runtimebytesidentical5filesstable.
- ActualNARhashsha256-hIVo2RvlabG8Jw362W7PxdXkQx2CDYihvHKwhZjP0Es= matches;
26scopedtests/Black/Ruff/strictmypy0. Fullconfiguredroot3681+65/95%,audit0(noknown),
0failures/errors/skips,oneStarlette/httpxdeprecation.206completedreviewinputs stable.
- FreshparentGCC/Clanglayoutbinariesmatch192/7,136/10,actors110/104/103; no roleELF
executionbyparent. Author9earlyrolechecks subjecttofreshreview. Initialparentfreeze
printsyntaxfailedbeforeexecutionthenfixed; Nixpath-infoJSONformatdeprecationnoted.
- Saved native-callback-qualified-package-parent-gate.json; deleg_a21c3d67 independent
read-onlyreviewrunning. Updated [[native-callback-package-plan]]/[[goals-ledger]].
No deployedvariant/image/engineimport/runtimepacket/worldinit, all6milestonesopen.

## [2026-10-07 local] update | Read-only receiver readiness before next catalogue scope
- Currentusercontinuesgoal. Packagepeer hasno liveworker; awaitingnormalnotification,
notpolled. Parent206completedinputs stable. Readcurrentpacketdb andmigrationbaseline.
- AST-only currenttable888 matchesbaselineexactly;10runtimeconsumerhashesunchanged,
111literaluses/60IDs(44Rx16Tx). C0stillabsentdespitequalifiedlayout192/7/0,2,6.
LegacyNATIVE_MACROS OBF/WARNemptydefinedflags differfromactualprofileABSENT;
notpatchedorusedasnewsourceauthority. Literalcoverage!=completeemissions.
- Parentliteral_eval initiallyrefusedstruct.calcsize thenexactliteralformatwhitelist
handlesitwithoutmoduleimport/genericeval. Saved native-qualified-receiver-readiness.json.
- Created [[native-qualified-catalogue-readiness]], linkedindex/[[native-callback-package-plan]]/
[[goals-ledger]]. ProposednewofflineStageB1contract/catalogue keepsuncertainties/
manualexceptions/nooldgenadoption; no runtime/worldchange or StageB1codegrant.

## [2026-10-07 local] update | Explicit offline contract/catalogue implementation grant
- ExactUIchoiceAuthorize offline contract/catalogue implementation. Recorded
native-qualified-catalogue-implementation-scope.json +parentsharedinterface.json
andREADMEinspikes/008-qualified-packet-catalogue. NEWpipeline,nooldgenrepair/reset.
- deleg_bf815d0a disjointcontractvalidator+explicitundischargedpreconditions and
compiler-backedlayoutcollectorphases. Initialcommon/mapdeclarationtrancheunderMAP
profile; prefixcoverageexplicit, not completewire/senderproof orcharloginreplacement.
- No package/tracer/CLI/runtime/NATIVE_MACROS/pin/gates/world/model/SQLchanges.
LAYOUTonly+conventionalIDcandidates, unknownsretained; no copiedoldrejectedrows.
Freshparentproducer-validatorintegration andindependentreview followresults.
- Updated [[native-qualified-catalogue-readiness]]/[[goals-ledger]]; packagepeer
resultawaitsnormalnotification, allfullmilestonesopen.

## [2026-10-07 local] update | Offline package independently approved; CPP evidence bounded
- Reviewe9c4e6278e62962e46f6738b4f4a3b6405aecdf4725f67b4af8c4f6be5cdd6fe
PASSofflineStageA/securitylogicqualityempty. Parent82reviewartifacthashes/206stable
inputs; recorded native-callback-qualified-package-approved.json.26tests/8fresh
refusals/9tracedearlycases passed, no initialization/deployment/sinkruntimeadmission.
- CompilerboundclarifiedactualMakefile: savedmaprecipe selectsNPCcustomruleusing
CXXFLAG_CLEARS, not clifobj/%.oCXXFLAGS. CFLAGSffast-math !=clifCXXflagproof.
ScopeCPP/profile/frontend/layoutonly, nobinary/backend-envelopeequivalence.
- Queuedscopedapproval/flagclarificationsteerstoB1bothchildren (deliverynotassumed).
Updated [[native-callback-package-plan]]/[[goals-ledger]]; separatelyauthorized
B1implementationcontinuesofflineonly, allmilestonesopen.

## [2026-10-07 local] update | Real catalogue collected; scoped validator integration RED
- B1authors complete(contract7tests/collector11tests). Raw8a6443efd199edb2fc38d20109e043c637d2923648cd6aa1554cc613aeba802e
632declkeys/631spellings,578map54common,477conventionalIDs,allGCCClanglayoutmatch.
Parentfreshproducerexit0 artifact414b098ea0e68bf9e751c711da630f5c08896c21cae7f78f0f84ccedd5e8e064
samealllayouts/headers/classifications. No sender/wire/nativeadmission.
- Parent206inputs stable,sourcefull3206hashes afterproducerprivateheaderREDoverwrite
incidentrestoredexactimmutablebytes. ParentBlack4files0 closeschildtoolfrontier.
Initialparentverifycount/listtypeharnesserror corrected,no source/data changes.
- ACTUALrealcollector→validatorCLIexit2 missing/unexpectedfields. Neednestedsource/
authority,4primaryheadersvs3206wholemanifest,632scopekeys vs631spellings,94legal
flexible-arrayoffsetof==size(prefix) harmonization,notdropprovenance/coercevalues.
Saved native-qualified-catalogue-parent-frontier.json +parent-producer-replay.json.
- deleg_c064326e ownsTDDcontract/tests/interface harmonization underexistingB1grant;
collector/rawartifact/oldreports frozen, no runtime/source/package/worldchanges.
Bothauthors exceededtargetminutes andremain disclosed/notwaived. Updated
[[native-qualified-catalogue-readiness]]/[[goals-ledger]], no pipelineapprovalyet.

## [2026-10-07 local] update | Measured runtime migration frontier, no table edits
- ActualNixread-onlyASTaudit exits0.888 runtimeentries matchbaseline;tenconsumer
hashesunchanged.477conventional-headerrecords→472IDs:108fixedsizeagreements,
20variablepolicyreviews,340absent,4fixedmismatches,5multi-declIDs. No automatic
registration recommendation or wire-length/senderproof inferred.
- Only30of44RXliterals associated ininitialheadercandidatecoverage;14explicitgaps.
Actorlayoutcontrols110/103/104 present butno conventionalheaders; don'tcallthat
missingdeclarations/dropregistrations. Preservechar/login/PIN/party/outgoing;
C0stillabsent emotionlayout7 doesnotbyitself permitreceivermigration.
- Saved native-qualified-catalogue-runtime-delta-readiness.json (parentactual
script/readbackSHAaa08aa768b9cc19c6006f256366c97ced2cbd2d194d1fb4a676887c54a11bd25).
No importedreceiver/native/DB/inference.206frozeninputsunchanged. Scriptclarified
headerassociationabsence vsdeclarationabsence beforefinalreplayexit0.
- Integrationsteerattempt nolivesubagent; resultawaitsnormalnotification notPASS.
Updated [[native-qualified-catalogue-readiness]]/[[goals-ledger]], allmilestonesopen.

## [2026-10-07 local] update | Real catalogue→validator passes parent combined gates
- Integrationreport567c1f866da28e58641d56447409e3435bb948e56ac15590cf60f4396e292cef
physically verifiedcode/CLI/raw hashes; parentfreshCLIexit0 preservesall632/631,
477headers/94tails/source/authority/coverage/preconditions.622layoutONLY/10manual
rows;6conflictentries5uniquemessages(BANduplicate) explicitlyforreviewnotwaived.
- Parent27scoped tests +BlackRuffstrictmypy5files0. ConfiguredCHECKinitial20F4E
becauseparenttoolshell lackedg++; preservedXML/log. SamepubliclockedinputGCC16.2
addedonlyto ephemeraltoolset; onecompiledrepro0 thenfullCHECK0:3681physical+65
subtests/95%,audit0 no knownvulnerabilities. No code/gate/pin/sourcechanges.
- Rehashed206frozen+3206publicfiles; recordednative-qualified-catalogue-parent-gate.json
withallactualhashes. Author8mintargetexceeded918.09s wall,607.6sinceRED;notwaived.
- Update [[native-qualified-catalogue-readiness]]/[[goals-ledger]], frozenindependent
reviewnext. No compiler-executionauth/sink/runtimeadmission ornative/worldeffects;
allcanonicalconditionsUNDISCHARGED/allmilestonesopen.

## [2026-10-07 local] update | Catalogue independent REJECT physically reproduced
- Review108ee2dfa49cb45756c04eb5331308193d300bcb41261dd86f3037048b852d43
REJECTboundedofflinepipeline, securityempty/norepairs. NominalfreshGCCClang632,
CLI0/27tests/quality0;53coreprobes50pass3fail+supplementaryconfirmed4findings.
- Parent92reviewartifacthashes+229frozenunchanged verified; actualNix replay5
syntheticboundaryprobes confirmsL1zeroextentnontrailingaccept,L2commonemotion
identityaccept,L3retaineddisagreementcount/headerreject,Q1malformednullCLI1
AttributeError/noacceptedoutput. Originalevidence/reports retained controlling.
- Savednative-qualified-catalogue-review-rejection.json+repair1-scope.json;
deleg_c6d7efde firstof2NEWpipeline fix/review cyclesforonlyL1L2L3Q1 underexisting
implementationgrant. No exhaustedoldgen/tracerbudgetreset. Preserve27tests/data.
- Parentsecondarycountprobe wasstageddebugfrontier, NOTfuturevalidgold: document
repair1-probe-clarification.json requiringvalid631compiled+1unresolved forfailed
row; wrong632/0stilldeny. No runtime/sink/source/package/worldeffects.
- Updated [[native-qualified-catalogue-readiness]]/[[goals-ledger]], allmilestones
open/freshcombinedgateandindependentreview stillrequired.

## [2026-10-07 local] update | New catalogue repair1 passes parent replay, not approved
- Repairauthor4d300f7894137f08e0852ab85167169a9dee38f69f2b37ee598a42c83d3149a3
candidateonly L1L2L3Q1. Parent106artifacthashes/code physicallyverified; producer
andtest_contractunchanged, sixallowedcode/test/docs/interfacechanges only.
- Parentactualfreshproducer/validator0 preservesall632/631/477/94facts,authority/
coverage/conditions;622layoutONLY10manual aliasrows. Parent5boundaryprobesallpass:
L1L2deny,L3valid631/1manualaccept,wrong632/0deny,Q1CLI2emptystdoutnoAttributeError.
- Actual74scoped tests(original27identifiers+47new) +5fileBlackRuffstrictmypy0;
configured3681physical+65subtests/95%CHECK0, audit0. Preservedoldreject/history.
Parent206protected+221nonownedoldfreeze+3206publicsourcesmatchimmutablemetadata.
- Savednative-qualified-catalogue-repair1-parent-gate.json.627smeasuredrepair>
480starget acknowledgednotwaived; authorpatch/log-name/refusedwrite/Ruffissues
retained. Update [[native-qualified-catalogue-readiness]]/[[goals-ledger]]; fresh
frozenrepair1independentreviewnext, no sink/runtime/source/package/worldeffects.
Allmilestonesopen; priorrejectcontrollinguntilfreshreview, budgetsnotreset.

## [2026-10-07 local] update | Repair1 review rejects only classification error frontier
- Independent419c87dc5137cb1b42c81f9a17205cb53ef4896c6d1a0f730de6400fa1fc2d3f
REJECT; L1L2L3verifiedfixed, Q1-R1class[]{}unhashablemembershipTypeError API/CLI1.
Correctlegacy1/1/0andproducerzero-countmaskingfixturesexpose; oldtests sometimes
hitcountdenialfirst. Failclosedemptystdout notaccepteddata/executionexploit.
- Parent379reviewartifacthashes/249unchangedverified;actualNixfourexactCLIrepros1
TypeError/emptystdout.74tests/73freshprobes69pass4fail nominalgatesnotapproval.
Savednative-qualified-catalogue-repair1-rejection.json/repair2-scope.json.
- deleg_282c2c5f second/LASTautomaticNEWB1repaircycle2of2 onlycontract.py and
reachingTDDtest_integration.py classliteralshape guard. No generator/tracerbudget
reset, no unrelatedcleanup/pins/gates/source/package/world/runtimeeffects.
- Update [[native-qualified-catalogue-readiness]]/[[goals-ledger]], fullmilestones
open; parentreplay/freshreviewrequired, no automaticcycle3ifstillreject.

## [2026-10-07 local] update | Final automatic repair passes parent; fresh review required
- R2author31dec08c89f5affc05e2fd981a67093bcbb364d01b6f62ac11bafab1fea3d3fd
candidateonly. Parent40evidencehashes,verifiedoneproductionexpr text(classification)
beforeunchangedmembership;74priorIDs+20priorintegrationbodiesbyte-identical+4new.
Actual78scoped/5fileBlackRuffstrictmypy0, four exactmalformedCLI2emptystdout/no
TypeError ortraceback. Nominalvalidator0/report==prior632/631/477/94/rawfields.
- FullrootCHECK0:3681physical+65subtests/95%, audit0.247nonownedfrozen+206protected
and3206publicphysicalhashesmatchimmutablemanifestbeforeparentdocs. Saved
native-qualified-catalogue-repair2-parent-gate.json; child222.26>180stargetnotwaived.
- Readiness201lines split [[native-qualified-catalogue-review-history]] preserves
alloldcheckpointsectionsverbatim148lines; [[native-qualified-catalogue-readiness]]
current99lines linksit, clarifieshistoricalproposal/packageofflineapproval and
finalcandidatepending. Updated [[goals-ledger]]/index. No source/package/world/
runtime/sinkadmission; allmilestonesopen. Freshfinalindependentreviewnext; both
NEWB1automaticcyclesused,nocycle3ifrejectwithoutnewuserdecision.

## [2026-10-07 local] update | Qualified offline catalogue/validator independently approved
- Finalreview216bae47f108122865ce506a364056c9a35b0396a025ac009317e6f77b227fcf
PASS ONLYfrozenboundedofflinecommon/maplayout/provenance/nonadmittingvalidator,
securitylogicqualityempty. Parent252reviewartifacthashes/268inputsunchangedverified
beforeapproval/docupdates. Indep78tests/prior74bodies+IDs retained,54freshprobes,
fivefilequality/freshproducer-validator pass; no broadwire/sink/runtimeapproval.
- Recordednative-qualified-catalogue-approved.json. Root3681+65/95%audit0 above
remainparent evidence(read/hashed), not rerunbyfinalreviewer. All6conditions
UNDISCHARGED/authsinkruntimefalse. Historicalrejected snapshots preserved; old
exhaustedgenerator/tracerbudgets unchanged, NEWB1twocyclesused.
- Updated [[native-qualified-catalogue-readiness]]/[[goals-ledger]], standalone008
README/index status. [[native-qualified-catalogue-review-history]] preservesfailed
frontiersverbatim. Nextseparatesender-to-wire/framing/receiverpolicy permission;
no packetregistration/deployment/world/model/SQLeffects. Allfullmilestonesopen.

## [2026-10-07 local] update | Qualified emotion source-framing readiness inspected
- Standinggoalnextconcretestep read-only qualifiedclif9412-9420exactemotionfragment
byte-identicalcanonical, hash a1261d1ac07891c69891c6a7db28033c03069ee08f3aab1e8d4bb91d4c105bb6.
ExistingcanonicaltracerCLI actualexit0 ID192/size7/offset0,2,6 candidateidentity.
NotfreshqualifiedASTidentity: callbackqualifiedsourceclosure differs; noASTIDjoin
or oldcanonicalUBsinkadoption. QualifiedAREA forwardsbuf/len, callbackFIFOcopy
visiblebutconditionalallocator/session/lifetime/receipt unproven.
- Receiverhash89a363...unchanged/noC0,206protectedstable. Created
native-qualified-framing-next-step-readiness.json withexactfragment/sourcehashes
andqualifierbounds. No code/runtime/package/source/model/SQL/world effects.
- Updated [[native-qualified-catalogue-readiness]]/[[goals-ledger]]; proposed
separateboundedOFFLINEemotion source-framingtranche toremoveimmediateblocker.
Requiresnewexplicitgrant, not oldrepaircycle3or permissiondeploy/register/retry.

## [2026-10-07 local] update | User accepts faster gameplay-first course
- Exactusercorrection 'I accept your proposed change of course'. Recorded
playing-mvp-change-of-course-scope.json +NEWaccepted [[adr-020-pinned-protocol-gameplay-first]];
manualpinnedprotocol+compiler/source/parserchecks/observednativeMVP insteadof
all-pathC++proof prerequisite. Knownbugsnotwaived/rejectedtoolrowsnotadopted.
- Delegfa11110e disjoint C0staticmanifest+oneparserregistrationTDD andexisting
qualifieddocker-image offlinebuild/inspection. No genericASTpipelineextensions;
parentcoordinatesfinishedreview/qualifiedtest-onlydeploy preservingdatabasevolume,
thenexistingtwofixtureactualClef/damage/XP/loot/LLM/schedule-memorygate.
- Actualreadonlyengineinventory0:fourrunningtestcontainers/exacttestvolume/no
foreignusers. Detailedsanitizedprojection0 identifiesnativeoldimages andhealthyDB;
ordinaryComposevolumeproject/world-datalabels match. Customro-bots.worldabsence
isnotforeignownershipornewframework prerequisite. No DBaccount/offlineproofyet.
- PrivatepreflighttemplateHealthfieldquery initiallyfailedsanitized; switchedto
allowedStateprojection/supportHealthcheck andactualrerun0. No container effects.
Imagechildsteer nolivesubagent—awaitnormalnotification,nobuildapprovalinferred.
- Updatedindex/[[goals-ledger]]; allfullmilestonesopen. Readiness/oldreviewevidence
remainhistoricalofflinebounds; scopechangeexplicitnotexhaustedautomaticcycle3.

## [2026-10-07 local] update | Exact owned fixture/database read-only preflight passes
- Parentnextstandinggoalstep actualNixread-onlySQLbaseline exits0; privatefixture
expectedcredential/characterpairs consistency checkedinsideprocess, bothnonGM/
nonserver/normalstate+selectedcharownership/offline. FreshSQLcountallonline0,
totalcharacters2. No nativeclient opened, inference or game actions.
- Reusedknownread-onlybaseline source privately, preservingoldreports; newengine
projection builtfromactualcurrentresourceview, appendedSELECT-onlyall-character
onlinecheck andobservedHealthcheckcompatibility. No fabricatedownership/status.
Privatevaluesonly[REDACTED], sanitizedstdout. Freshplaying-mvp-readonly-baseline.json
report; immediatelybeforeimageswappreflightmustrepeat; no deploymentyet.
- Delegatecontrollerreportsnolivesubagents; normalcompletionnotificationsawaited,
notpollingtheirartifactsorinferringPASS. Update [[goals-ledger]], allmilestonesopen.
Scope [[adr-020-pinned-protocol-gameplay-first]] remainsactive.

## [2026-10-07 local] update | MVP protocol and image parent gates, actual image import
- Recoveredcompletedprotocol/image reports. ParentminimalC0:7sourceaddition only,
888preserved→889. Actualroot3826physical+65subtests/95%CHECK0/audit0; selected
225physical+65subtests excludes6namefamilycases, fullrootcoversall. Newtestquality0.
- Parentarchive52layerhashes/3581storefiles/threeELFhashes/virtualrootlinks matched
reviewedqualifiedpkg; initialbasenames-as-rootpaths harnesscorrected,noartifactedit.
Recordedplaying-mvp-parent-gate.json; focused25freeze reviewdeleg_b064d14c pending.
- Actualdockerload qualifiedarchive0. Follow-upimageinspectapprovaltimeoutNOTRUN;
workflowpaused, renewedexplicitUIAuthorize read-only inspection and continue test
deployment obtained, actualretryreadback0/configimageIDd6aa8e...matches. Saved
playing-mvp-image-import-receipt.json. No container replacement/worldreset.
- Postimportinventoryexactlyequalspriorfourcontainer/testvolumeprojection. Fresh
reviewdelivery andimmediateDBownership/offline refresh requiredbeforeservice swap.
Updated [[goals-ledger]], allmilestonesopen, no gameplay acceptance yet.

## [2026-10-07 local] update | Qualified server deployed; real agents move, timeout frontier
- Focusreview9e810700ac7d3718586605357ac3d77b7997a3760ed2eb0d11314ed29cc616a5
PASS finiteC0manifest/parser+archive. Parent25reviewhashes/25frozenverified; initial
relative-artifactpathharness correctedROOTprefix. Recordedprotocol-image-approved.
- Freshimmediateexactresource/SQLofflineproof, actualCompose --no-deps only3native
roles up/recreate0. Readbackexactqualifiedimage for3, originalhealthyDBcontainer/
testvolume preserved; no reset. Nativeports16900/16121/15121 readinesslogsverified.
- First2boundedclientprobesfailedlogin SC_NOTIFY_BAN path; capturedfirstorigin
beforehostretrymasked it. Loginlognocharonline; peerlogs oldDNSIPstargetportsvalid.
ConfigactualprivatearchivevaluesclassifycorrectserviceDNS/loopbackadvertisement.
Orderedcharthenmaprestart andlaternative retriesrestorepeerlinks; initial8s
readbackassertfalse/name-vs-fullIDstdoutcomparison preserved,no credential edits.
DiagnosticinitialkernelDockerendpointabsence andmsgconfUTFdecode mistakes corrected
terminalenvironment+exactroleconfigallowlist, no source/runtime config changes.
- Actualpostrepair2botrun79.823s:4realClefcalls,100SELF0087receipts,5C0frames no
unknown rejection. Goalssocial/actualmovement; zeroeligible selfdamage,XPgain/loot/
LLMchat unaccepted. Fixture1EOF; maplogSessiontimedout. Bothsupportedcleanup/SQL
both offlineverified. Savedplaying-mvp-live-progress.json andexactrunfailure.
- deleg_fbc7dff9 ownedsource-backedpacedkeepalive TDD onlyplayingadapter/newtests,
no livechildactions. Clientkeepaliveexists butnohostcalls/actual0x0360send observed.
Parentnextfocusedreview/live rerun, not expandinggenericprotocolproof. Updated
[[goals-ledger]], allsixfullmilestonesopen; accepted [[adr-020-pinned-protocol-gameplay-first]].

## [2026-10-07 local] update | Live goal-selection branch examined during keepalive fix
- Readactualtwofixturesrecordedstartupresponses: change_goalkeep/next_actiongrind,
goal_review scoresbelow.5. Sourcebrain._review_goal hardcodedbad-reviewfallback
changesGRIND→SOCIAL despite explicitkeep; _run_review choosesgoal-script notnext_action.
Subsequentreact_monsterflee weakconfidence producesnorthMoveTo. Actualoneeligible
actor seenperspective-only, no othermapmobpositions/identityguesses.
- deleg_19155b51 read-onlygoal/request/scriptdiagnosis andsmallcoherentoptions,
newreportonly/no inference/code/native effects. Existingkeepalivefix fbc7dff9 still
runningatcontrollercheck; no partial-sourcegate/review or pollingoutput.
- Updated [[goals-ledger]]; bothbotsprevioussupportedcleanup+offline verified,
no live retriesduringfix. Parent will keep operatorintervention versusactualClef
choice explicit; no forcing-goal-to-fake-autonomous-gameplay acceptance.

## [2026-10-07 local] update | Goal diagnostic corrects flee interpretation; narrow contract change
- Diagnostic0ca44629164c398b9f6e7fcd62e1d6c42af78549abb32fdc5ecd9012c3095f18
showscontinuousnorthmovementmostlySOCIALIdleTownScript(+1Ytensteps/recreated), not
repeatedClefFLEE. Parentreadsactualscripts.py77-88/115-121 andexistingkeepfallback
paramtests. EachactualmonstereventFLEE only+4Y/no scriptreplacement.
- Currentkeep→bad-scorefallback was deliberatelytested/retained, notaccidental
untestedbug. Parentchoosesnewexplicitgoal-execution consistencycontract: valid
explicitkeep wins; missing/invalid retainsoldscorefallback. Savedplaying-mvp-
explicit-keep-scope.json; deleg_12d7ab9f strictTDD brain/keep-specifictestsONLY,
no keepalive overlap/no sourceactor/perception/magicconfidence orforceattack.
- Monster exactspecies/level/weakness/whyFLEE unproved; nativeappearance/request
not retainedinoldreport. DoNOT inferweakmob from runtimeactorID orglobalmapdata.
All4recordedcalls notbenchmark. Parentcorrects priorgeneric'fleeing' interpretation.
- Updated [[goals-ledger]]; keepaliveindependentongoing, no newnative/inference
sessions thisexchange, allmilestonesopen/freshfocusedreview/live acceptancepending.

## [2026-10-07 local] update | Keepalive parent scope passes; independent review started
- Keepaliveauthor5b85938747cb449670e7098a17eea4c65f64715145286eb5d9466a37c5cf2753
completedofflinecodehash e305b545... playing_runtime +18newtests only. Parent146
scopedcases0/BlackRuffstrictmypy0, actualREDGREENXML stages inspected. No native
session byauthor/parent verification. Author920.41s exceeded8mintargetnotwaived.
- Parent actualownedmapcontainerpacketconf archive read-only confirmsstall_time60
/noimports (configSHAa90ca...), no wholefileparityclaim. New20sdrain-native-events
pump beforecognition, getterspure, clientepoch/timer/poisonownership; serialtick
blocked>60snotcovered. Originalwireencodingpacket0360unchanged.
- Recordedplaying-mvp-live-timeout-config.json +keepalive-parent-gate.json;
focused19freeze deleg_010984d7 read-onlyfreshreviewrunning. Parallelbrainkeep
semanticworker remainsdisjoint/notinfeaturefreeze; finalrootgateafterbothstable.
- Updated [[goals-ledger]], no live retries untilreview+combinedgate. Allsix
milestonesopen, no synthetic91s tests promotedto native survival.

## [2026-10-07 local] update | Both fixes completed; combined parent gate passes
- Explicitkeepauthor517f5eff4a639e6f8536b0c23fcec82155709ac19922d8c25b3732d5bc430f97
completedminimal_review_goalchange. Parentverified3ownedhashes andactualRED5/2fails,
intermediateGREEN30/2testeventlabelfailsretained, final68/0. Two recordedstartup
answer replays nowGrindScript/no phantomgoalnotes; no newrealmodel/nativecalls.
- Stablecompletedbothfixes configuredtaskcheck0:3861physical+65subtests/95.07%
coverage;taskaudit0. RootJUnitparsed0failure/error/skip; recordedplaying-mvp-
keepalive-goal-combined-parent-gate.json. No thresholds/pins/sourceboundarieschanged.
- Goal15frozeninputs independentdeleg_c742184e read-onlyreviewstarted; keepalive
19inputreviewdeleg010984d7 separatelypending. No rootgate onpartialdelegatefiles.
- Updated [[goals-ledger]], allmilestonesopen/no native rerunyet. Live90scheck
stillrequiresfocusedreviewresults/freshowned-worldpreflight; syntheticcountnot
promotedto actualsurvival/damageXPloot/chat acceptance.

## [2026-10-07 local] update | Keepalive focused approval physically reconciled
- Independent76c42a55601985dcb1ee8540b1ad6e14734b331272b19cd19fc69f75df41f563
PASS146scoped+8freshprobes/quality0. Parentphysical26artifacthashes and actualXML
146/8nofailures/errors/skips verified;19frozeninputs/currentcombinedsourcehashes
unchanged. Recordedplaying-mvp-keepalive-approved.json, approvalofflineonly.
- Reviewerreportedrootgatepending; parentalreadycompletedstablecombined3861+65/
95.07%/audit0 beforethisnotification. No needrepeatunchangedrootgate; exacthashes
matchreceipt. Review448s>4mintargetnotwaived, scratchimportissue correctedonlyharness.
- Goalreviewdelegc742184e stillpending; live90sparentrun afterthatpass+freshowned
preflight. Nativekeepalivereceipts/survival/damageXPlootchat unaccepted. Updated
[[goals-ledger]], allsixmilestonesopen; >60sblockedserialticklimitretained.

## [2026-10-07 local] update | First real positive combat; new NPC-close framing frontier
- Goalreview31962cb78b7dfb851c546398a39d5da0379538942147569824201f0ffc2f7e6f
PASS68+398fresh; parentartifacthashes/15freeze/currentrootgatehashes checked,
actualscoped/probeXML0fail; scratchcollectionfailure preserved. Offlineapproved
receipt recorded. Review517.5s>4mintargetnotwaived. Bothsourcefixes independently
approved/currentcombinedroot3861+65/95.07%/audit0, no redundantgate beforelive.
- Newparentharness preservesoldfailed79.823sreport, usesonly exactnewreviewed
brain/runtime/testkeep hashes over prior sourcefreeze. Firstattempt refused old
explicitkeep-testhash BEFOREclientcreation; repairedonlyauthorizednewtestsnapshot
binding and preservedstderr. Realrerun afterfreshownedworld/accountofflinepreflight.
- Actual51.937s:26realClefcalls/noLLMchat, positiveSELFdamage14+16 toactuallyobserved
eligible targets (sample1damageeach);258attackrequests distinctfrom30damageeffects.
Bothsent2keepalive0360/received2tick007F. Maxhoststep1.624s. BothgoalsGRIND retained,
no forcedgoal/attack. Native90s survivalNOTverified; no XPgain oritemacquisition.
- Fixture1receiveValueError unknown0x00B6offset74 preceding196/AB2/80; strict
failure endsrun, notcatch-skip. Bothsupportedcleanupconfirmed; immediateSQLoffline
readbackfailed, subsequentfreshreadonlypreflight passedexactfixtureownership/
bothoffline/allonline0. SavedHP43/prontera both, no unsupportedrespawncauseclaim.
- Publicpinnedclif.cpp2504-2525 identifiesPACKET_ZC_CLOSE_DIALOG sizeofsender;
sourcecomments alone notlengthauthority. deleg_b0e4717c: disjointframingTDD+fullheader
compileroracle/smallcompanionmanifest, andreadonlyRest-versuscontinuingattack
executiondiagnosis. No automaticNPCack/semanticdeathproof/globaltargetweakness.
- Savedplaying-mvp-live-after-keep-goal-frontier.json; updated [[goals-ledger]],
firstpositivecombatreceipt isprogress notfullmilestone. Allsixremainopen.

## [2026-10-07 local] update | B6 parent passes; REST execution defect confirmed
- Source-backednewB6companionmanifest+fixed6mapping, all889previouspreserved890
current; exacttokenremovalrecoverspriorpacketdbbytes. ActualGCC/Clang1826align1/
offsets0/2width2/4 publicunchangedheaders and3206closure. Parentverifiedhashes/
RED1failure→firstGREEN1→final261, originalC0spec/test unchanged.
- Stablebeforefurtheredits configuredparenttaskcheck0:3977+65subtests/95.07%,
audit0. New12inputfreeze independentdeleg_3010d327task0 focusespacket/source only,
excludesparallelrecoverymodules; liveRERUNnotperformed.
- Diagnosticd388c698ecfb5990dd631f3995390ede7d78ba63bc8141bf5c453ff5a9d64271
confirmsRESTwire.sit executesbut_sameTick_scriptstepsAttack; nexttick attacksfrom
unsuspendedplan, lowHP25%flaps. NativeAttack bypassesstanding/pending gates;
serverincomingdamageforce-stands (notclientauto-stand-before-attack).
- Countcorrection actual258actionrecords=234normalattacks+24sits; eachfixture
122/112normalattack versusprior128/130alltypes,14/16actualeligiblehitsremain30.
Received54/61ACT3notpureSELFposecount; STOPMOVE0088notstopattack. Oldfailedrun
negativeevidencepreserved, no fabricatedspecies/weaponreasonorrevivemechanism.
- Parentexplicitchosenexecutorpolicy recordedplaying-mvp-rest-interrupt-scope:
configurabledefault.75HP recovery threshold (engineeringchoice notgameformula),
persistentplan/scriptpause/no patrollootfallback, received-standing/pending
barrierforAttack, preservedexplicitFLEE, keepalivedrainactive. deleg3010d327task1
verticalTDDimplementation/disjointpacketreview. PursuedRESTcanstillfail; no
automaticfleeconversion/confidenceoverride/hiddenmonsterknowledge.
- Updated [[goals-ledger]], allmilestonesopen/no newnative/inference. Scope
sourceapprovalforpacketfixisnotnative90ssurvival orcombatXPloot acceptance.

## [2026-10-07 local] update | New criteria 9/10: native mechanics context and bounded public knowledge
- Explicitlyaddednative stats/skillpoints/learnedskills/equipbonuses beforeactuation,
observedencounterdamage+ownlevel context, andsource-attributedruleset-taggedpublic
knowledge separatefromprivateexperiences. ExistingMechanicsPort/MechanicsYaml must
bereused; guidesnotmechanical/currentstateauthority. Ledgernewlatestcheckpoint
qualifieshistoricalentriesandkeepsall6milestonesopen.
- B6completedreviewfileavailable/controlleronlyRESTworkerstillrunning;parent
reviewfe00f0c0e26f0653f0abc71fd70fab8f3f7e37254a38114c27ba078e70a9d59dPASS
57artifacthashes/12freeze/261+8 checked; savednpc-close-approved.json. Root3977+65
95.07%audit0 remainspre-RESTcheckpoint,nofinalpartial-treegate.
- RESTworker1705selapsed>8mintarget; queuedboundedfinish/precisepartialfrontier
steer,no new9/10fileoverlap/no taskexpansion. No newnative/inference/modelcalls.
- Publicsourceextractionbackendsearch-onlyrefused; browserreal-profileSQLite
writelockblocked. No profilechanges/guessedlogin. Actualparallel5urllibfetches
throughpinnedNix allHTTP200,MediaWiki revisionIDs readfromHTML, gistAPIactual
revisionf51fe5c910427fd6f384d22823140b1693c76207,full35091charoptchat.mdnottruncated.
Contentchecked/canonicalcleanhashes/private5sourcefiles retained. Unsupported
initialrevision/fetched metadata removedBEFOREcorpus andrestoredonlyafteractual
fetch proof. Copyrightbody/footerdifferentlicenseversionreferences retained;
no fullwiki mirror/images/redistributionassurance. Isolatedcitationledgercreated.
- deleg_e410aac7: readonlynativefield→request/actionACKaudit; disjointpureTDD
publicadvicecataloglookup undercount/UTF8budget usingactualsnapshots (noactivebot
wiring/privatejournalmutation). Existingpublicmechanicsport authoritative later
legalplanning. Recordedmechanics-knowledge-scope.json; updated [[goals-ledger]].
- Previousrealcombat30positivehits retained; XP/loot/native90ssurvivalunverified,
allmilestonesopen.

## [2026-10-07 local] update | REST parent scope passes after exact resurrection-test reconciliation
- RESTauthorcompletedfileavailable/controlleronlyknowledgepilot+nativecontext
streams remainrunning; report status184focused/90of91playingpass, oneoldfake
resurrectiontest assumesAttackwithoutfreshstandingandhasnoWire.stand seam.
Parentverified5ownedhashes+33evidencefiles/physical184XML andexact91/1failure.
- Parentreproducedexactfailure usingonefocusedtest beforeedit (realAttributeError
missingfake stand). Recordedplaying-mvp-rest-resurrection-test-scope.json:
TESTONLYWire.standrecorder (notposepublication) andresurrectionbranch nowasserts
standrequest/noAttackthenactualSELF08C8type3rawreceiptthenAttack. OriginalpositiveHP/
alive/death/warp/authlessdenialassertionspreserved; no productionguardweakened.
- Parentactual275focusedcases0fail/error/skip, including36newrecoverycases;
Black/Ruff/strictmypy6files0. Original_review_goal exactpreserved, scriptsunchanged;
newbrain/host/nativeadapter recoveryholdshealththreshold.75engineeringpolicy,
FLEE/KEEPprecedence+plan/pose/pending/keepaliveregressions. No gameplayclaim.
- Savedplaying-mvp-rest-interrupt-parent-gate.json;28criticalinputfreeze andfresh
independentdeleg_db4e7197 reviewstarted. Rootcombinedcheck deferreduntilongoing
publicknowledgepilot stable; last3977+65/95.07%audit0 PRE-REST only. No midworker
wholetreegates/no live native/inference or SQLwrites. Updated [[goals-ledger]].
- Allmilestonesopen; native90ssurvival/XPloot/LLMchat stillunverified.

## [2026-10-07 local] update | Criterion9 source audit completed; first encounter-context slice started
- Nativeaudit05a9e1c4956e98bdcd19b30fddd4a5a6051303adbdef88c656ce227fd168d233
completeREADONLY. Parent14stablepublic/sourcehashesverified. Currentmodelcontext
omits stats/bonuses/freepoints/learnedskills/equippedindices+effects/species/history;
BDonce/141twelvetimes realfixture0buttypedstatsnotretained. Auditcompilerboundary
explicit: prioractorSIZE measurements don'tprovejoboffset; BE/BC/equipACKlayouts
notadmittedbyaudit/tablecounts. No fakepointvalues/sourceoffsetautoapproval.
- Firstminimalorderobservedspecies+SELFdamage+ownreceivedlevelatreceipt, then
currentstats/freepoints, learnedskills, equippeddetails, ONLYTHENlegalactuators.
ExistingMechanicsPort/YamlMechanics reusedwithunsupportedscript/bonusfactsunknown.
Oldreal30hits lackspecies/ownlevelbindingsremainunknown; no retroSQL/personajoin.
- Recordednative-encounter-context-scope.json anddeleg_be49cc3b purecodec/facts
TDD withtargetedactualfull-header joboffsetofproof; no editsREST28frozen
runtime/model/requestdeps/no activebotintegration/no native ormodelcalls.
- Created [[native-mechanics-and-encounter-context]], indexedandlinkedledger.
Ongoingknowledgepilot644sover6mintarget queuedfinitefinish/partialblockersteer,
notmasswiki/contextfeatureexpansion. RESTfreshreview129satcontrollercheckongoing,
notpartialgated. Finalrootaftercompletedstableimplementations; allmilestonesopen.

## [2026-10-07 local] update | REST independent approval and real bounded knowledge lookup
- RESTindependente03ebfb673095856f30f51a37254b3a8c7ee4682c3f8beb171ddbc0553d02ca4
PASS275+9fresh. Parentphysicalartifacthashes/28freeze/tests275+probes9XMLverified;
recordedrest-interrupt-approved.json. Realnative90srerunstillpendingfinalstable
root; independentofflineapprovaldoesnotproveunderpursuitsurvival.
- Knowledgeauthor97edb0aa682a34d074a8aabca51a5278bda568e7fbb0a6ef06c37a3f84f19000
workingoffline4statscards(2eachruleset), no skills/equipcards/fullwiki/private
memory/modelwiring. Parentactual28tests/BlackRuffstrictmypy0, source/seedhashes,
5verticalREDGREENXMLstages+final28 checked. Realpublicseed lookup pre-re1120bytes/
renewal1128under2048 includingprovenance/advisoryflags; sourceIDs/revisionactual.
- Recordedrules-knowledge-parent-gate.json +8frozeninputs independentdeleg67f5a953
reviewrunning. Created/indexed [[public-rules-knowledge-pilot]], no rawarticles/
images/tables shipped/copyrightlicensingassurance. Sourcepinsnotsemanticvalidation
ofeditedcardtext;exactcatalogreviewrequiredbeforeactiveintegration.
- Nativeencountercomponent234satcontrollercheckstillrunning disjointpuremodule,
no midpartialrootgate/no liveinference/SQL effects. Finalrootaftercompletedstable
component; allmilestonesopen/no newnative session. Updated [[goals-ledger]].

## [2026-10-07 local] update | Public advice pilot independently approved
- Review4468ed246664656c7b9d92c9b81ba6b80f31a4800e0f915521b4cc865218a4b3
PASS28+8fresh/source-support/canonicalbytes; parentphysicalartifacthashes/8freeze/
actualXML28/8zeroerrorsfailuresskips verified. Recordedrules-knowledge-approved.
Review361s>4mintargetretained; source-onlymypy --follow-imports=skip isnotfull
projecttypegate, parent'sfullstrictbothownedfilesalready0/currenthashesmatch.
- Approvedexact4seedstatsadvicecards/sourcepinmetadata, notarbitraryeditedtext
semanticverification/fullwiki/skillsgear/currentstate/privateobservations. No
activebots/Clef/LLMwiring/nativeeffects; updated [[public-rules-knowledge-pilot]].
- Encountercomponent921s>6mintargetlastunfinishedimplementation; queuedfinish-
nowcurrentcall/GREENfiniteartifactorprecisePARTIALfrontiersteer, norolling-history
featureexpansion/unownededits/hiddenskips. Stablefullroot/live90safteritsfinal
snapshot. Updated [[goals-ledger]], allmilestonesopen/no newnative session.

## [2026-10-07 local] update | Combined gate repaired; real sessions persist four minutes, chat-size frontier
- Encounterslice7cdd4e39aaa2b3567abc06e1bd4f231e07748544a740901535fc7ac99f063366
completednewpureadapter10tests/92scoped. Parent source/hash/XMLchecked; actual
GCC/Clang signedint16job@23 width2 withsizes104/103/110 sourceprofile. Caller
provenance preservednotauthenticated; all active9context/stat/skill/gearwiringopen.
- StablefirstrootfailedwholeSOURCEXenonC knowledge.select/class, despitebounded
28+8approval. Recordedquality-onlycycle1of2scope; parentexactargumentvalidation
helper extraction(inversebytesrecoversentireold3a1677...), preservedmessages/order/
tests/seed/quotas. FirstretryBlackformatonlyfailurepreserved; formattedONEowned
source, scopedquality+wholeXenon0, unchanged28tests. No thresholds/oldbudgetswaived.
- FinalROOTcheck0:4051physical+65subtests/95.36%, audit0. PrivateXML parsed0errors/
failures/skips. Savedrecovery-context-combined-parent-gate.json; readonlyfresh
reviewsdeleg_af9eff76 knowledgequalityrepair5freeze+encounter9freeze running.
Unwiredcomponents excludedfromnativeknowledgeacceptance butincludedrootgate.
- Actualfirst90.638s sessionscontinuous,4keepalive/4tickreplyeach,cleanupboth/
SQLoffline; labelleddirectedchatreachedClef+LLMcallfailed. Readonlyhealth/oldPID/
portproofchatdependencydown; sameprojectscript e52fb.../Qwenweights2fde00.../Nix
xvvpg... restoredonlyownedunused8300, processproc_d2218b0c81fb PID1698492 readback
health200/modelchat/listenerexactPID. No installs/newweights/otherprovider changes.
- Actualsecond240.444s: bothreadershealthy/11keepalive11clockeach/town+fieldmaps,
14realClefcalls,4actualpositiveSELFdamage/1SELFdeath/1B6noerror; XP0lootnone.
ConnectioncontinuityPASSnotcharacter-survival. Supportedcleanupboth/SQLoffline;
fixture0savedtowndiff fromlastfieldstate, no inventedrespawn/warpcausality.
- RealLLM1success282chars286UTF8, NativeSay1, peerRX0—functionalchatpathFALSE.
Exactownedmaplog1toomessage-longwarning. Sourceclif.cpp10514-39 activepost20151001
messageLength+1 andlimit255; existingwireclientaddsNUL1, so286→288rejected and
currentwirevalidtextmax253. NotserverUTF8character-count guesses/sendreceiptPASS.
- Savedlive-recovery-chat-frontier/chat-size-frontier/chat-dependency-restored.
Newdeleg36f688b1 ownsminimalUTF8safepublicSayboundaryTDD/helper/newtests only,
no party/client/frame/RESTpolicy changes; furtherliveafterfreshreview/rootgate.
Allmilestonesopen; updated [[goals-ledger]], no fakeXP/loot/chat delivery acceptance.

## [2026-10-07 local] update | Native chat parent passes; encounter cursor repair dispatched
- Nativechatfix completed: source-backed253UTF8prefix helper+ONLYnativeSayargument
inruntime (reverseimport/call recoversold29f7...runtimebytes/AST). ActualGCC/Clang
fullheadersactiveMAIN20180704 ChatMAX256/253+NUL1+modernincrement1=255. Shorttext/
empty/NUL unchanged, malformedfullUnicode raisesbeforeclipping, longprefixvalid
codepoints. No party/wire/packet/REST/pose/readiness/keepalive changes.
- Parent verified3ownedhashes/realRED budget1failure→GREEN1/UTF2cases1failure→GREEN2/
final353authorXML. Actualparent326scoped0errorsfailuresskips incl27new+recovery/
pose/clock/packet cases; BlackRuffstrictmypy3files0. Recordednative-chat-text-
parent-gate.json;13frozenindependentreviewdeleg6374bccbtask0 running,no live repeat.
- Knowledgequalityrepairreview234b17b49b113a5e080cd10704eb49cb829826056f9afc8bc95ac09aead71158
PASS28+8/exactASTinverse/wholecomplexity/testseedunchanged; parentartifacthashes
andcurrent0877ca...sourceverified, savedrules-knowledge-repair1-approved.json.
- Encounterreviewd72517c03f53ed37f7041bc7b5c0f367794da8e4f1a2ddd56a7dc8bfa560c2de
REJECToneEC-HISTORY-OVERSIZE-CURSOR: builder-valid3196byteUTFbinding seq10budget
DROPdoesnotconsumecursor, permitsolder9/same10changedfactsafterseenreceipt.
Compiler/signedjob/sourcefieldproofpassed—notgenericgrammarerror. Parent7review
artifacthashes+privatehashregistryverified, initialregistrytypeassumptioncorrected.
- Recordedencounter-context-repair1-scope.json firstof2automaticbudget; deleg6374bccb
task1 EXACTrecord/dropcursoronly+newreachedTDD, keepspriorrecords/budgets/foreign
semantics/typedcapture intact. No reducingbindinglimits or maskingreplaydefect.
Unwiredhelpernotadopted; otherhistoricalbudgetsunchanged. Stablewholegateafterboth
new-sourcechangesfinal; no currentrootpass/nativepeerchatclaim. Allmilestonesopen.

## [2026-10-07 local] update | Bounded-transmission observer prepared without premature live retry
- Controller163s showschatreview+encounterrepairrunning; no partialwriterfiles
usedforgate/acceptance. No newnative/model/SQL/serviceeffects.
- Preparedrun-playing-mvp-clipped-chat.py guardedexactchat-approvedreceipt/current
completed-rootcheck/audit/nativefeaturefreeze/ownershipobserverlock/offlinepreflight.
HistoricalRESTruntimehash mayonlybeoverriddenbythe separatelyapprovedchat snapshot,
notblanketignored; all othercriticalinputs checked.
- Nativewire.say observer nowrecordsactualboundedtransmittedLLMtext/UTF8bytes,
andpeer matcher usesTHATtext ratherthanfullrawgeneratedreply. Offlineactualold
286-bytegeneratedresponse +syntheticpeerfixture:bounded253bytes matches, original
fullreplydoesnot; SHAa43eda...verified. Explicitsyntheticnotactualnewdelivery.
- Savedclipped-chat-verifier-readiness.json/codehash4294192543a9319003267ff093bfcec2fb66990dc392d137c6b06b7fd2e5637c;
actualexecutionnotattempteduntilchatreview+stablegate. Updated [[goals-ledger]],
allmilestonesopen.

## [2026-10-08 local] update | Current root passes; live reply finds downstream relay cap
- Chat independent review passed the incoming-budget scope; parent verified all
13 frozen inputs, private artifact hashes and 242 physical regression cases.
Saved native-chat-text-approved.json; no peer-safe approval inferred.
- Encounter repair1 verified:97 scoped/965 broader physical cases, actual RED
cursor replay then GREEN, five added boundary tests, all evidence hashes checked.
Fresh read-only repair review deleg_c1f3d06b dispatched; helper remains unwired.
- Initial root check hit220s timeout during pytest; failed log retained. Repeated
unchanged completed snapshot with600s bound:check0/audit0,4083+65/95.38% coverage.
Saved chat-current-combined-parent-gate.json; no gate thresholds changed.
- Actual first clipped-chat run90.610s:both4 keepalive/clock replies, Clef3,
zero stimulus because saved locations stayed on different maps. Cleanup/offline
passed; chat was NOT exercised. Preserved live-clipped-chat.json.
- Follow-up240.574s allowed natural route convergence, no location/goal/attack
or fixture override. One labelled stimulus at90.558s, realClef18/LLM1, transmitted
252UTF8 bytes, exact sender/name/message-bound peer matches0. Two positive SELF
hits, two deaths, XP gains0/lootnone;11 keepalive/clock replies per fixture,
healthy connections and supported cleanup, exactSQL both offline.
- Exact owned map readback:incoming-too-long0, clif_GlobalMessage outgoing
truncation1. Source6756-6774 caps FULL name+' : '+text+NUL at256; incoming253 text
cap alone is insufficient. Source-shaped outgoing test now required; preserve
original bounded incoming approval and failed exact peer acceptance separately.
- Recorded CHAT-OUTGOING-NAME-BUDGET repair1of2 scope and chat-followup-summary;
deleg_2141050c owns only selected-name-aware helper/minimalSaycall/newtests,
no live effects. Budget min(253,255-UTF8(name+' : ')), full valid-codepoint prefix.
Updated protocol skill/[[goals-ledger]]; all milestones remain open.

## [2026-10-08 local] update | Encounter cursor repair independently accepted
- Repair1 review c3d2c8d9f09b2122b72a4be700e8c7669cadf0f7095e594aca3fe4a74609af79
passes15 repository cases+7 fresh boundary probes, no security/logic/quality
blockers. Parent physically verified22 JUnit cases,7 stable inputs and20
artifact hashes. Saved native-encounter-context-repair1-approved.json.
- Seen-but-budget-dropped sequence consumes cursor; older/equal changed facts
cannot overwrite history. Retained records, foreign epochs and encoding-error
policy remain unchanged. Original rejection/RED preserved; cycle1of2 consumed.
- Helper remains unwired; no native stats/skills/gear or model-context acceptance.
Selected-name-aware chat repair still owns minimal runtime Say seam; no moving-
snapshot root gate or extra live run performed. [[goals-ledger]] updated.

## [2026-10-08 local] update | Exact known vitals projected into active decision request
- Disjoint source change while sender-budget author owns runtime: real SystemOne
state.bot now includes hp,max_hp,sp,max_sp directly from existing BotState.
Previously only ratios reached Clef. Four dictionary entries only; removing them
recovers exact original source. No native stats/gear/skills/bonuses guessed.
- Genuine RED1 missing allfourfields (not importerror) -> minimalGREEN1; existing
ratio/question/envelope preserved, zeroSP retained. Added two preservation cases
for equal ratios/different capacities and zeros/no fabricated unrelated fields.
- Parent122 scoped decision/brain/playing-runtime tests passed, Black/Ruff/strict
mypy2files0. Initial PT018 test-stylefailure preserved, split assertions only.
- Saved decision-vitals-context-fix.json and5inputfreeze; deleg_af9039b3 independent
read-only review dispatched. No model/native effects or moving-snapshot whole
check. Chat-author steer arrived after it finished and did not land; no source
scope overlap occurred. Parent future combined freeze must include decisions.py.
Updated [[goals-ledger]], full criteria9 and all milestones remain open.

## [2026-10-08 local] update | Selected-name relay fix and exact vitals pass combined gate
- Sender-budget repair1 completed: required helper(text,sender_name) uses actual
wire selected char_name; min(253,255-prefixUTF8) and strict whole-input encoding.
Parent hashes/physicalXML verified relayRED1failure→GREEN1 and extremebudgetRED2
failures→GREEN;35 chatcases/184 scoped author cases, minimal runtime inverse.
- Frozen18 dependencies; fresh chat-peer repair reviewer deleg_c24ce04d dispatched.
Exact-vitals reviewer still pending; neither offline test result implies live RX.
- Completed stable ROOTcheck0/audit0:4094+65/95.38%, no threshold changes. Separate
parent198 focused cases pass and Black/Ruff/strictmypy5files0. Saved chat-peer-
vitals-combined-parent-gate.json with decisions.py and exact current source hashes.
- Prepared peer-safe-chat verifier guarded BOTH new approval receipts/current
combined gate/freeze/owned-world/offline observer lock. Required helper signature
updated, exact sender+full transmitted-text peer matching preserved. Records
already-built exact HP/MAXHP/SP/MAXSP at real provider-input seam without request
mutation or manufactured telemetry. No native execution on new snapshot yet.
- Saved peer-safe-chat-verifier-readiness.json, sourceSHA51f5b22197b6a7a788ca887435b80e0f08f54050cdd973c649ffec647410e542.
Updated [[goals-ledger]]; full milestones remain open pending actual gameplay.

## [2026-10-08 local] update | Real native LLM replies observed; exact vitals reach Clef
- Both fresh reviews PASS. Parent verified18 chat inputs and private hashes,
physical242cases(57fresh); exactvitals5inputs/9artifact hashes/physical17cases.
Saved peer-budget-repair1-approved and decision-vitals-context-approved receipts;
current4094 gate/source hashes checked before native actions, modelhealth200.
- Actual guardedrun240.502s:realClef10 successful requests capture exact native
HP/MAXHP/SP/MAXSP; realLLM6 successful calls/sends. One labelledoperatorstimulus
at181.525s. Peer matcher exactsender/fullboundedtext finds5per-transmitted-text
membership matches; oneprefix repeats, so this is NOT5distinctdelivery ACKs or
proofevery6senddelivered. At least bounded native freeform chat path passes.
- Both11 keepalive sends/clock replies, healthyreaders, supportedcleanup and
exact SQL bothoffline. Ownedmap readbackincoming-size0/outgoing-truncation0/
timeouts0. Thisruncombat0/deaths0/XPgain0/lootnone; do not turnchat intoallmilestones.
- Saved live-peer-safe-chat-acceptance.json and peer-safe-chat-map-readback.json;
source reportSHA30462b8c16ad53030316cbe298585885ac5f93540d2ab9824965189175ebdbe1.
- Next fullend-to-end criterion9slice deleg_d94326a4 owns ordered encounterstream/
minimalPlayingClient hooks/defaultBotState context/realdecisionprojection+tests.
Explicitselectedbaseline only; futureB0 levels/actorappearances cannotretrojoin
pastdamage, actor reuse/map/gap/epoch isolation and8fact/2048bytebudget retained.
No newactions/providers/guides/SQL/native effects bydelegate. Updated [[goals-ledger]],
allmilestonesopen; currentgate refers to completed pre-integration snapshot.

## [2026-10-08 local] update | Current-stat field measurements run while encounter writer works
- Encounter-to-request delegate still owned its six source/test files; no moving
combined gate, acceptance label or redundant native session was performed.
- Parent reused exact installed CPPFLAGS and executed immutable full-source/profile
binding before compiling full unchanged core/packets/map headers with BOTH GCC
and Clang. Fresh actual executable outputs agree:BD189/44/align1, pointuint16@2,
sixuint8base/costpairs@4..15;141header321/14/align1, statuint32@2, signedbase/bonus
@6/10width4; B0header176/8/align1, param@2uint16/count@4signed32. Compiledpoints9/12,
STR..LUK13..18. Existing table already44/14/8, no packet mapping changes.
- Saved native-character-stat-field-oracles.json; parent read report/source hashes,
both binary hashes and raw measured stdout back. No current values received,
collector/request integration or legalactuation acceptance follows from layouts.
No services/native/SQL/models/Git changes. Updated [[native-mechanics-and-encounter-context]]
and [[goals-ledger]], all milestones open.

## [2026-10-08 local] update | Actual passive stats show zero free-point budget
- Sent encounter author finite finish-now steer at448.6s of8min scope; no scope
expansion or inference/live acceptance delegated. Do not waive later overrun.
- Guarded passive diagnostic used ONLY unchanged reviewed native client/table,
not changing PlayingClient/request files. Exclusive observerlock, fresh4owned
resources/qualifiedimage/exactfixtures/allonline0 preflight, identity matching,
routing restrictions and20s absolute connect/observe budget checked.
- Actual4.136s:eachfixture BD1/14112/B019 rawframes, completecontiguouscapture,
healthyreader. Sixbases1/aggregatebonuses+1/nextcosts2, statpoints0 andskillpoints0
received—not missing defaults or inferred fromlevel. Typed signedness/source
layouts fromprecedingGCC/Clang measurements. No newaccounts/gameplayrequests/
inference/pointspending/operator SQL writes. Server-owned session bookkeeping
naturally occurs; report/schema explicitly distinguish it fromoperatorSQL.
- Supportedcloseboth and freshSQLboth offline; no capture/cleanup errors.
Savedpassive-character-stats scope/report/receipt and as-executedprobe snapshot;
originalstdoutSHA9c6dfd0ad064fce42964438450832339b19a0e86f362cc30d2d3930536329530
preserved after operatorSQLfieldclarification. Script control-flow origins retained.
- These receipts do NOT prove thecause ofearlier one-damagehits or equippedsources
ofbonuses. They do establish that no spendable points may be invented from level.
Productionretention/modelprojection/validstat-skillequipactuators stillpending.
Updated [[native-mechanics-and-encounter-context]] and [[goals-ledger]], allopen.

## [2026-10-08 local] update | User redirects to real NPC preparation and equipment readiness
- Latestuserinterrupt:havebotsevenequipedanything;theyshouldtalktoNPCsto learnwhat
todo, supportthat. Subsequentsteer:nonequipment/lowstrengthprobably1damage.
Do NOTresumeinterruptedencounterreview asactivepriority; its completedoffline
GREEN25new/460scopedreportpreserved, unapproved/unadoptednative.
- Checkedactions/native dispatch: noNPC orEquip actions; inventoryquantities
cannotprovegear. Actual guardedpassivecapture verified BOTH complete native
inventoriesempty, noequiprows, fixture1twoobservedNPCcandidates (fixture0zero).
Healthyreader/supportcleanup/SQLbothoffline, no gameplayorprovider actions.
Savedpassive-equipment-inventory scope/report andequipment-readiness-frontier.
- Correctionacceptedasplausiblecontributor, notisolatedformula proof. Visual
weaponLook2/savedappearancecannotestablishequippeditemwheninventoryisempty.
- Newnpc-guided-readinessscope/deleg_f9a1bf1c implementsreceivedNPCperception,
nativeTalk/Next/Select/Close, boundedactualpages/original1basedmenus,Clefchoice
andprivateinstructionmemory, novicepreparation—notanotherunwiredpilot.
NPCclickcanattackBL_PC/BL_MOB(source12196..12251), soonlyknownNPC6/12 allowed.
InvalidNPCmenu index cankick(source13319..13343), soexactreceivedindices only.
- Currenttable lacksB4/B5/B7 andseveralunsupportedinput/shopresponses; newsource/
compiledNPCframingneeded beforeanyliveconversation. No catch-and-ignoreunknowns.
No SQLgear/pointgrants, blindpurchases/questrewardclaims ornewfixtureseeding.
Updated [[goals-ledger]]; allmilestones andNPC/equipnativeacceptance remainopen.

## [2026-10-08 local] update | Headless architecture confirmed; equipment codec runs beside NPC MVP
- User asked whetherbotsgetvision/useGUI; verified factorybuilds nativePython
BotClient and Clefstatebuilder serializespacketobservations intoJSON/text.
No screenshot/video/renderedvision path. Humanclient/dashboardseparate; user
explicitly answered'perfect', retain protocol-drivenagent architecture.
- NPCauthor stillownedactiveTDD source. Parent didnotgate/accept moving snapshot
or rerun unpreparednativegrinding. Newdisjoint equipment scope/deleg_a7a94501
owns ONLY equipment.py/newtests/manualmanifest/report, no sharedNPCfiles/table.
- Equipmentdecoder mustprove active57row/flags/WearState andsender/ACKlayouts
viafullunchangedheaders, thenactualbytesREDGREEN; decodedsuccess/correlation
separate from legalactuation, packetregistration andlivewearverification.
Emptycurrentinventory means no equipment acquisition/ACKcan beclaimednow.
- NPCauthor notified of concurrentnewmodule quality boundary and agreedheadless
architecture; parentcombinedgate afterbothfinitecompleted snapshots. No source
owner interference/globalNPCknowledge/injectedgear. Updated [[goals-ledger]].

## [2026-10-08 local] update | Complete finite NPC blockers; equipment codec parent green
- Both writers stopped and handedback artifacts. NPC PARTIAL:30physicalNPCcases
pass,331priorregressions/2old6-12visibilityexpectationfailures. Currentdispatcher
rankC afterNPCnameintegration, NoteKind lacksnpc_dialogue (usesother), and
legacyframingtests requireexact6newrows/old890sourcepreservation accounting.
No fullcurrentgate/liveNPC/equipacceptance; overrunremainsrecorded.
- Parent verifiedNPCafter-sourcehashes andactualXML. Newfinite-completion scope
splitsmetadataquality/exactoldcontracts vsNPCmemorytag/journalreplay; delegates
AE9103b4 task0/runtime+oldtests,task1/NoteKind+_remember_npc+newdurabletests.
No newNPCfeatures/gatewaivers/tablechanges/nativeeffects allowed.
- EquipmentGREEN20physicalcases +fullGCC/Clangfieldproof/artifactreceiptsverified.
Parent reran20cases +Black/Ruff/DEFAULTprojectstrictmypy2files0, no customconfig
waiver. Saved equipment-parent-gate.json and5filefreeze; BA258969freshreadonly
reviewsource/flags/ACKsemantics, no currentclass/legality/nativewearclaim.
- Sourceclif2976..79 setsoption_count0whilefilling5slots; codec preservesall
signedoptionvalues, doesn'tzeroeffects. Snapshot57/WearStatevsallowedslots,
request8/ACK11/unequipACK9 sourceprofilepreRE-only, integration/tableACKstillopen.
- Wholecheck/audit waitscompletedsourcewriters; no reviewofmovingNPCdependencies.
Updated [[goals-ledger]], all milestones open, no repeatedunpreparednativefight.

## [2026-10-08 local] update | Equipment codec independently accepted, not live equipping
- Review117f445f13c42b87618aa6004a7c87eb10247fbd1b2645dc4b8705076943ac44
PASS20existing+8freshphysicalcases, GCC/Clangfreshfullheaders/flagfixtures,
strictisolatedscope+authorstrictmypy/BlackRuff/barestdlibimport. All256flag/result
values exercised; unknownACK result remainsunknown, notboolinverted.
- Parent verified5frozendependencies,36authordelivery/proof receipts and all
reviewer artifacts, physicalXML20/8zeroerrorsfails/skips. Savednative-equipment-
codec-approved.json boundedoffline only; no matchingcurrentownedinventory,
class/level/gender/slotlegality orpendingintent/epochcorrelation is established.
- No ACKregistrations/liveequip/unequip/itemacquisition occurred; bothfixtures
remainpreviouslyobservedbare. NPCcompletion quality/schemaworkers owncurrent
sharedsource; parentcombinedgates/review aftercompletedstablefrontier.
Updated [[goals-ledger]], all milestones remain open.

## [2026-10-08 local] update | Completed NPC source passes combined project gates
- Parent verified completion hashes and physical RED/GREEN XML: metadata quality
C/11 and four old-contract failures reproduced; three responsibility extractions
recover identical full-runtime AST. Final603 scoped tests pass, exact896 mappings
preserve original890 source bytes; memory205 scoped tests pass, dedicated tag
replays in a fresh process and next real NPC decision memory_view. Suites overlap.
- Canonical original report playing-mvp-native-npc-guidance.json remains preserved;
child's discovery used a different filename lacking native, not artifact loss.
- Full stable-source task check0/audit0:4177 tests +65subtests,95.37% coverage,
227.24s pytest;208 frozen public inputs unchanged. Nix supplemental tools use
existing tiny locked public flake, no whole-checkout source or gate changes.
Saved playing-mvp-npc-equipment-combined-parent-gate.json with exact input hashes.
- Independent read-only review deleg_86716415 covers complete NPC/decision/private
memory pipeline plus shared encounter/chat/REST safety, not only local repairs.
Original writer and finite completion overruns remain recorded, not waived.
- No native NPC/equip/model/SQL/services/Git effects in this completion; all six
milestones and live reward/equipment/progression acceptance remain open.
Updated [[goals-ledger]], [[native-mechanics-and-encounter-context]] still tracks
the broader missing skill/stat/equipment/guide integration.

## [2026-10-08 local] update | NPC source-readiness independently approved
- Independent review5a20a9f8a61df61943930e68a3d21517b90045070944bf958ba335f9b7dac7f4
passes402focused/200memory-brain-encounter/12fresh=614testexecutions, not asserted
unique tests. Fresh immutable-source nine-layout oracle and six-source strict
mypy pass; exact six registrations preserve890 original mappings/sourcebytes.
- Parent verified all13 reviewer artifacts, physicalXML402/12/200no failures,
errors/skips,208 frozen dependencies and equal sourcefreeze for completed project
check0/audit0/4177+65/95.37%. Saved playing-mvp-native-npc-approved.json.
- Reviewed source preserves NPCidentity/range/menu/blankindices/cancel255,
private tag/replay/oldkinds, encounter temporal ordering, chat/REST/KEEP/keepalive.
No liveconversation, quest/reward or equipmentclaim follows this source verdict.
- No native/model/SQL/network/service effects; actual NPC conversation and receipt-
based reward/gear retention remain next gameplay acceptance frontiers. All full
milestones and broader stat/skill/equipment/public-rule integration remain open.
Updated [[goals-ledger]]; source approval does not close [[playable-world-acceptance]].

## [2026-10-08 local] update | Requested status and five-domain gameplay coverage audit
- User interrupted native-run preparation to request current build/missing/next
status and delegates auditing full Ragnarok gameplay. No native run was launched.
Fresh read-only preflight confirms four owned containers running, exact owned
volume users, both fixtures offline and all-online-character count0;208 reviewed
source dependencies remain unchanged. This is not a populated playing world.
- Dispatched five research-only delegates in deleg_51e9c466: combat/progression,
economy/inventory, NPC/world/quests, social/guild/WoE, class-specials/rulesets.
Each owns separate JSON/markdown reports and private source/citation evidence;
no code, native/SQL/model/service/fixture/Git effects. Source requirements must
map observations, prerequisites, actions, positive native receipts, negatives,
current support tier and ruleset/server applicability. No universal RO guarantee.
- Saved ro-gameplay-coverage-research-scope.json and ro-gameplay-audit-dispatch.json.
The next finite gameplay objective remains one complete ordinary-player loop:
actual NPC guidance -> legal earned progression/gear -> combat/XP/loot -> items/
shops/storage -> useful party play -> reconnect memory, before population scale.
Updated [[goals-ledger]], with all six full milestones still open.

## [2026-10-08 local] update | Real autonomous NPC click reached missing cut-in frame
- Continued native acceptance while five cached-source gameplay audits recover.
Owned chathealth was down; exact reviewed launcher/model hashes matched. Initial
non-executable launcher permissionfailure preserved; bash invocation restored
owned localserverhealth200. Clefhealth200, no provider/billing substitution.
- Native preflight refused before login because allfour owned containers exited.
Fresh restricted inspect verified same identities/images/users/mounts and owned
volume labels with0foreignusers; restored onlyexistingMDB/login/char/map in order.
External readbacks confirm running/healthyDB, no containerrecreation/volumereset/
operatorSQL. Outside-established-shell inspector failure retained; same helper
succeeded in pinned Nix shell. Cause of earlier world stop remains unknown.
- First verification-harness guard NameError occurred before resourceallocation;
fixed only guard ordering. Initial native attempt's final diagnostic incorrectly
read Memory._notes instead of Memory.log._notes afterhost.stop; no completed
verdict fabricated, failure retained and fresh both-offline preflight passed
before corrected probe. Production src unchanged by these harness corrections.
- Completed corrected run3.4402477039998303s: fixture0 Clef3calls,fixture1 Clef1;
fixture1 autonomous0090 target observedNPCdistance1, then strict rx ValueError
unknown01b3 at0 preceding[]. No NPCpages/instructionnotes/menuchoice accepted.
Both supportedcleanups andfresh all-online0/nativeoffline readback verified.
Saved live-npc-guidance.json and native-NPC-cutin-frontier.json with exact hashes.
- Sourceauthority clif.cpp2733..2750 clif_cutin SELF sizeof illustration sender;
packets_struct.hpp5340..5345 header01b3/packedimage64/type. New scoped writer
1e3dc8d3 will compiler-measure unchanged fullheaders then add only exactframing,
strictrealstreamREDGREEN/collision/old896preservation; no pixel/quest/gear inference.
Independent review/newstablewholegate neededbeforeanothernativeattempt.
Updated [[goals-ledger]], no fullmilestone closed; [[playable-world-acceptance]]
requires realreceived effects, not this successful request plus framing failure.

## [2026-10-08 local] update | Recovered gameplay audits compiled into finite backlog
- Allfive recovery JSON/MD reports exist; original ownerexit remains an incomplete
batch, not retroactive success. Parent parsed/deduped/schema-checked104 candidate
feature rows: classspecials18/combat18/economy30/NPC18/social20.
- Tiers55missing/14unknown/10offlinemodel/7codec/12offlinepipeline/5historicalnative
primitives/1notapplicable; no native_behavior_verified row. Primitive receipts
cover targeting, damage, inventorycompletion, publicchat andpartymembership only.
No exhaustive enabled-content inventory or completionpercentage inferred.
- Parent verified110 source-cache receipts and source-report hashes; placeholder
copyright-only ledger evidence is explicitly NOT semantic mechanics authority.
Confirmed actual currentactionunion lacks use/equip/stat/skill/shop actions and
native progression gates rawjob0/Novice, irrespective of class/build templates.
- Created catalogueJSON(fullprovenance)/CSV/summaryMD and proposed livingguide
[[gameplay-coverage-roadmap]]. OrderedNPCframing+realconversation, currentplayer
resource retention, legalactuation+earnedXPloot, shops/quests/classrefresh, useful
party/reconnect/humanE2E, then specialist/dashboard/guild/WoE/scale/benchmarks.
- Updated indexdate/link and [[goals-ledger]]. No code or native action executed
while cutin writer owns its framing snapshot; whole-source/newnative gates wait
finite handback. All full milestones remain open.

## [2026-10-08 local] update | Cut-in repair halted on missing configured-source authority
- Cutinwriter PARTIAL before productionchange: realunknown01b3 RED plus two
source-bindingfailures. No compilerinvoked/no67lengthregistered. Table896 and
all208 priorreviewedinputs remainexact; newtest/manifest unadopted.
Scoped437pass with10 explicitcompiler/authoritydeselections is NOTa wholegate.
- Exact configured-variant scratchtree ismissing; availablepublicheaderreplay
has457immutableclosuremismatches. No convenientflags/publicreplacement/hashwaiver.
The deployedpackage'simmutableevidence remains available:3216configuredfiles,
closure08a7056eab5f58d83e8f00af4f3371d56551c3033b9c377d5fd3860c3744d138,
profiles/mapflags/maprecipe/qualifiedclif/auxiliarycore-start plusinstalledtransforms.
- Dispatched c9faeb9b source-onlyrecovery fromexactstoreevidence andlockedcached
inputs, private staging/fullhashproof before restoringmissingSOURCE, optional
publicdurablemirror. No package/image/sourcefeature/SQL/native/model/service change;
actualoldbindingtestGREEN required before cutin repair resumes. No budgets reset.
Savednpc-cutin-source-authority-blocker.json; old4177gate historical while source
compilerchecks unavailable. Updated [[goals-ledger]], allfullmilestones open.

## [2026-10-08 local] update | Reconciled late audit completions and quarantine
- All five late completion report hashes match the compiled104-row catalogue;
no reapplication or duplicate research. Economy guide sources11..13 have original
retrieval-digest mismatches and remain quarantined; parent verified no feature
source_refs cite those IDs. Current-cache hash matching does not restore retrieval
integrity. Added this explicit limit to summary and [[gameplay-coverage-roadmap]].
Saved audit-completion-reconciliation.json; no code/native effects. Exactconfigured
source recovery remains the active compiler prerequisite, all milestones open.

## [2026-10-08 local] update | Restored compiler authority; cut-in candidate whole gate green
- Source recovery COMPLETE: parentchecked3216configuredfiles+auxiliary and37
immutable/recoveredartifacthashes; physicaloldbinding/NPCoracleGREEN2 afterRED1.
Receiptconfigured-source-recovery-verified.json. No profile/hash relaxation.
- Optionalpublicdurablemirror approvaltimedout beforeexecution; renewedclarification
cancelled/unanswered. Copycode DIDNOTRUN; no mirrorcreated/retryoralternate route.
Framingworkindependentofoptionalbackup continuedunder its existing exactscope.
- Finitecutincompletioncandidate: single01b3:67,897total/all896preserved, sourcebyte
inverses old896/890 exact, fourGCC/ClangRED/GREENELFhashes verified. PhysicalRED3/
1failure, GREEN748, final932, verified932passing. Existingauthoroverruns retained.
- Parentrootcheck0/audit0:4511tests+65subtests,95.37%,219.42spytest. Restoredcompiler
checks INCLUDED;208completedpublicreviewinputs unchanged. Savedcutin-combined-
parent-gate.json. Independentreviewa29542da readonlyfreshparser/profile/boundaries,
no unreviewednativeattempt orvisual/NPCquestauthority inferred.
Updated [[goals-ledger]], prior4177gatehistorical/new4511gatecurrentcandidate,
allfullmilestonesremainopen; actualNPCdialogue still requiresnative acceptance.

## [2026-10-08 local] update | Resumed after unattended prompts; bounded native NPC dialogue
- Cut-in review645 physical cases and208 frozen inputs match the completed parent
  gate. Refreshed verifier guard-only passed exact historical/current hashes.
- Reviewed native90.519s: eight real Clef calls; one fixture received11NPCpages,
  retained11private notes and advanced received Next prompts. Actual options1/2/3
  reached Clef; cancel255 selected and B8 sent. No noncancel branch/reward/gear/XP
  accepted. Both readers healthy; supportedcleanup and separate all-online0 passed.
- Cancellation silence exposed waiting->blocked forever. Controller-only delegate
  stopped PARTIAL with production unchanged; parent verified13artifacthashes,
  genuine RED1failure and scoped589passes. Same-wire prompt may continue after255;
  menu/select may end, so no universal serverclosure inference.
- User requested continuation after unattended approvals. No live child remained;
  dispatched finite completion2fd3a98e with minimal brain/runtime NPC dispatch and
  uncertainty gates added to original scope. General cognition/chat/REST may resume
  after local abandonment, but not uncertain combat/motion/loot/recontact. New
  review/rootgate/nativeacceptance required, no generic guards waived.
- Optional public-source backup remains absent/unapproved; no alternate copy.
  Initial log append lookup hit pagination and made no change; retried targeted
  patch after reading actual final section. All full milestones remain open.
Updated [[goals-ledger]]; bounded receipts do not close [[playable-world-acceptance]].
Menu-cancel ambiguity and real dispatch/pacing checks recorded in the task skill.

## [2026-10-08 local] update | Fresh explicit backup approval obtained and exercised
- Renewed the missed optional public-source backup prompt; user explicitly chose
  Approve the public-source backup. Prior timeout/cancel remains historical.
- Before copying, revalidated original recovery receipt, immutable manifest,
  source3216+aux1 and all16 evidence hashes; no symlink/path substitution accepted.
  Copied only authorized public bytes into run/public-source/callback-qualified-
  e985006171d2, then read back every destination hash and enumerated the exact
  3233-file allowlist. Saved configured-source-durable-mirror.json with verified
  counts. No secrets/private configuration, compiler binding or server/DB changes.
- NPC cancel completion remains a disjoint background task. Source backup does
  not grant live retry or waive uncertain-cancel actuation guards. All full goals
  remain open. Updated [[goals-ledger]]; [[playable-world-acceptance]] unchanged.

## [2026-10-08 local] update | Cancel completion candidate passes full gate; independent review dispatched
- User asked for progress and continued execution. Recovered completed candidate
  directly from artifacts: production4modules+ownedtest only, unknown-server local
  cancel abandonment permits safe cognition/chat/REST while actuation remains
  suppressed. No new native effect or equipment/quest/XP acceptance inferred.
- Parent physically verified42artifacthashes, threeRED XML eachonefailure,
  scoped1217cases0fail0errors and249baselinefiles (onlyfive authorizedchanges).
  Frozen250inputs include authorreport; no unowned production drift.
- Parent fresh task check0/audit0:4549tests+65subtests,95.44%coverage,229.60spytest,
  one existing Starlette/httpx deprecationwarning. All250inputs stayed unchanged.
  Receipt playing-mvp-npc-cancel-combined-parent-gate.json. First failed regression
  XML/log overwritten byauthor is an evidence limit; terminalexcerpt retained,
  no failed historical XML reconstructed or budgets waived.
- Dispatched independent readonly395c6f6e on exact frozen snapshot and before/after
  source snapshots, fresh actualbrain/client/host guards. No productionwriter now;
  review pending, native cancel retry not yet approved. Full goals remain open.
Updated [[goals-ledger]]; [[playable-world-acceptance]] still requires ordinary
NPC preparation, earned XP/targetloot, equipment/economy and usefulparty/reconnect.

## [2026-10-08 local] update | Independent cancel review rejected; exact repair and earned-gear route dispatched
- Continuing standing goals: review395c6f6e FAIL reproduced real client attack
  after0080(targetNPCvanish)->B5sameID in one pending-cancel snapshot. NPC consume
  clearsuncertain before finalcontextvalidation removesview; attack request then
  reacheswire. No native test approved/executed on this rejected candidate.
- Parent verified22reviewartifacthashes, physical176/1failure,217/2failures and
  corrected15/1genuinefailure; compiler-environment and scratch inventory assertion
  failures preserved separately, notconfusedwithactualcontextbug. Frozen250inputs
  match last4549+65/95.44 gate; GREENwholegate doesn't waive failed semantic review.
- Dispatched79ca1d9c with disjoint owners: cycle1exactorderingrepair and actual
  vanish/reuse/validcontinuation REDGREEN; readonlysource scout maps the11received
  tutorialpages/menu to legallyearnedstartergear/progression and nextreceiptgap.
  No hiddenquestflagSQL/geargrants, no broad104feature reaudit or compilerrebuild.
- Repair scope saved npc-cancel-repair1-scope.json. Review/rootgate/newguardednative
  acceptance required after handoff. All goals and milestones remain open.
Updated [[goals-ledger]], source-to-actuation gap stays separate from
[[playable-world-acceptance]]; profile/source backups remain unchanged.

## [2026-10-09 local] update | Repair1 full gate green; observed bard rules out assumed tutorial reward
- Recovered79ca1d9c two completed handoffs. Repair parent verified41artifacthashes,
  actual REDindependent/nativecorrected failures and two900case final/frozen runs,
  only runtime+ownedtest drift; NPCcontroller unchanged. Per-frame existing tracker,
  metadata invalidation and context validation now precede continuation consumption.
- Fresh parentcheck0/audit0:4577tests+65subtests,95.40%coverage;251inputsunchanged.
  Saved repair1-combined-parent-gate.json. Dispatched aae0b2ca readonly independent
  repair review with original counterexample and temporal gameplay/encounter checks.
  No native retry or approval inferred from GREENrootgate; cycle1budgetoverrun held.
- Scout actuallymatchedNelliorde/Bard#brising publicscript, not Novice trainer.
  Parentverified9sourcefilehashes, archivedlivehash and all11pagehashes/literals
  inexactorder withsource lines. Observed closed-seal-window menu branches have
  no equipment/XP/stat/skill reward; paid song is not preparation. Unknown quest
  flags/activeNPCDBclosure not promoted toreceivedagentknowledge.
- Conditionaladvisorynextslice: ordinary shop discovery -> receivedbudget/offer ->
  oneKnife1201 purchase+inventory -> guarded equipACK+currentwear, with unknown
  budget/eligibility/funding reported plainly. No NPCreward or worn-item acceptance.
  Source-backedroute and parentverification receipts saved; no code/live effect
  fromscout. All fullmilestones and criteria remainopen.
Updated [[goals-ledger]], no priorfailedreview or [[playable-world-acceptance]]
rewritten as success. Generic received NPC text is not starter-gear instruction.

## [2026-10-09 local] update | Reviewed repair live run reaches nested bard menu; bounded page frontier and shop codec dispatched
- Reviewer aae0b2ca had no live task/report at initial lookup; one interrupted-
  handoff recovery read found actual completed transcript/report. Parent checked
  11reviewartifacthashes,1003physicalpasses and251freeze identical to4577gate.
  Savedrepair1-approved.json boundedoffline only, no fabricatedpendingresult.
- Scratch verifier refreshed onlyfivecancel source/test supersessions. Initial
  guard-only KeyError omittedthreeunchangedhistoricalcriticalinputs fromnewgate;
  failedbeforeallocation. Restoredexactcutinfrozen client/table/authorproof pins,
  current251+historicalguards nowpass, no profile/hashwaiver. Prior reports retained.
- Ownedchathealthdown; reviewedlauncher/modelhashes rechecked, bash launch restored
  health200. Actualnative90.329s10Clefcalls, bothhealthyreaders/cleanup/freshallonline0.
  Fixture1 autonomouslyselected2then4:20B4+receivedB6, localretained16pages483bytes
  hitcountcap andblocked. No255request:livecancelnotexercised, no nativecancelPASS.
  Noclose0146, gear/reward/XP receipt. Lifecycle/menu-path pass is notfullconversation.
- Savedseparate nativecancel-repair1-acceptance.json functionalgap andpage-budget-
  scope.json. Dispatched558d3d98 disjoint bounded16->32pages/unchanged4096bytes64
  presentations32requests120slifetime, plusnewpure shopcodec withGCC/Clang active
  profile proof and streamTDD. No integration/shopspend/equip/nativeeffects bywriters.
  Combinedcompletedsnapshotreview/fullgate/newguardednative requirednext.
Updated [[goals-ledger]]; allfullmilestones remainopen, [[playable-world-acceptance]]
stillrequires actualpreparation/progression/economy, notmerelyNPCtext orsyntax.

## [2026-10-09 local] update | User-directed latest memory-definition review; actual cache/coverage failures reproduced
- User explicitly redirected to VictorTaelinupdatedgist/cacheloss concern. Official
  GitHubgistAPI+revisionhistory fetchedlatest3c190e06... committedOct8T01:58:24Z,
  previousf51fe5...Oct4. Fullsnapshotsha12f300f...19092bytes; previous35129bytes
  sha8f6997e... andactualunifieddiff saved, versioncoherence verified.
- web_extract stillconfiguredsearch-only; searchbackend fallback gaveemptyresult.
  NoTLS/proxy/profilebypass: officialghAPI suppliedgenuinecurrentpubliccontent.
- ExistingMemorycore actual4RED tests: unpressuredappendrewritesprefix,4193UTF8bytes
  admittedunder4000chars, oldcoverage discarded, relativeage changes onread. Physical
  XML4fail0errors; no paidmodel/native/privatejournal/sourceeffects. Freeze8 memory
  dependencyfiles forreadonlycore/provider audit ebb8b1c5. Sourceevidence receipt and
  proposed citedguide saved; citations strict/evidence gate passes.
- Newcontract last-message mergeage, persisted view, batchedhigh->low andUTF8bounds
  cannotbeclaimedby currentper-readminimalcover. Durable originaljournal vsmodel
  promptcache/viewloss keptdistinct. Literal64–128KB/defaultproviderctx capability
  remains a decision boundary toverify, no memory/cache migration or API assumption.
- ExistingNPCpage/shop/skilldelegates disjoint; no Hermesliveprofile/enginechange.
  AcceptedADR004 remains historicalimmutable. Updated [[goals-ledger]] andindex;
  [[optchat-definition-update-2026-10-08]] tracksnormativerevision andremainingproof.
Allfullmilestones remainopen; implementation scope follows actualaudit handoff.

## [2026-10-09 local] update | Page/shop completed snapshot verified while memory audits run
- Memory/core/provider audits remain readonly on eight unchanged memoryinputs;
  four actual updated-definition REDs are still open. No conformance inferred.
- Recoveredcompletedpage/shop/skill handoffs: parenthashchecked35page artifacts,
  104shop artifacts and13skill artifacts; physicalXML195/75/275 zero failures,
  counts overlap and are not summed as unique tests. Currentold251 drift isonly
  authorizedNPCpagebound, NEWshopmodule/test/manifest andpagetest heldstable.
- Fresh combinedrootcheck0/audit0:4646tests+65subtests,95.54%coverage;257frozeninputs
  unchanged. Savepage-shop-combined-parent-gate.json. Dispatchedb5c74b33 readonly
  feature review; no futurelive close/purchase/equip/skillallocation acceptance.
- Fullheaderproofcorrects scoutZenysender: B1param20signed32, notB0. Skillfullheader
  proof confirms010F prefix4/row37 andupdates11139/10E11/7E115 alreadyframed;
  sourceeffectivelevels/upgradeflags do not reveal permanent/copied ownership.
  Syntheticlearned9cancoexistwithzeroFREEpoints, reallearnedcount remainsUNKNOWN.
- Usermemorydefinition priority staysactive; no realjournalmigration/current
  providercontextsize orHermesprofilechanged. NewAPI/cachematch tests require
  implementationafterfiniteauditreports, greenlegacygate isnotUniiChatapproval.
Updated [[goals-ledger]]; [[optchat-definition-update-2026-10-08]] remainsproposed,
[[playable-world-acceptance]] remainsopen with realpreparation/economy stillmissing.

## [2026-10-09 local] update | Updated-definition audits physically verified; finite view-core implementation started
- Memoryauditparent checked allcore source/evidence hashes andprovider extra13
  source/evidence5 hashes; physicalnewcontract9REDfailures,139legacybaselinepasses,
  28providerfakewire/replaypasses. Eightmemoryinputs unchanged. Core37rows6PASS/
  20FAIL/6ADAPTED/5UNKNOWN isnotcompletionmetric; currentROmemorynoncompliant.
- Independentlast-basedrankoracle matchesall20001steps0..20000; FIRSTvariant481,
  T10wrongoldest0..7vsright8..9 exactcounterexample. Oracleactual0.115s resultheld.
- Providerwire probes varybeforememoryonall8routes; SystemOne tokenizedtemplate
  ordering/cachehits notprovedbyJSONorder. Local4k-tokenlaunchdefault vs128k-byte
  definition requiresactualcapvalidation, no char/tokenratio orprovideracceptance
  fabricated. Raw notesprivate/durablebutnormalized/notfulltranscript; viewnotstored.
- Started7f3339f8 NEWopt-inpureproductionviewlibrary/test/report only, scopedstrict
  TDDcorrectrank/fullcoverage/bytebudgets/eventappendbatch/stable reads/exactsnapshot
  roundtrip. Defaults64000/128000; noexistingMemory/journal/provider/liveprofile
  adoption yet. Safeview-storebinding/compactor/rawlogging/retrieval laterseamsheld.
- Page/shopindependentreview280physicalcases+28artifacthashes matched257freeze /
  completed4646gate; savedpage-shop-approved.json offlineonly. No new native effect.
Updated [[goals-ledger]], [[optchat-definition-update-2026-10-08]] auditnowcomplete,
fullsystemcompliance and allgameplaymilestones stillopen.

## [2026-10-09 local] update | New incremental view core parent gate green; full-system adoption still unchosen
- Recovered7f3339f8 completed newcomponentlibrary/test/report. Parent35artifacthashes
  andall14physicalXMLreceiptsverified:50final0fail/96.47modulecov+203legacypasses;
  initialAPIscaffoldRED is1error, NOTgenuineassertionfailure. FourlaterassertionRED
  stages11/9/13/1fail preserved withGREEN, no historicalrewrites.
- Newcomponentactualdifferentials20001steps+1500variableUTF8state roundtrips; strict
  completecoverage/last-rank/default64000-128000/stablelinebytes/snapshot JSON.
  Existing207Pythonfiles/eightmemorydeps/old257featureinputs unchanged.
- Freshrootcheck0/audit0:4696tests+65subtests,95.56%;260freezeinputsunchanged.
  Savedview-core-combined-parent-gate.json. Dispatched62bdacf0 readonly actualobject
  independentprobe review; nosourcefix/liveprovider/statemigration byreviewer.
- User answeredadoptionquestion with explain-the-difference, not a policychoice.
  ExplainedscaledROcorrectness vsliteralformat/context/cacheverification; neither
  allowsdroppedoriginals or provesKVhits. No profile choice silentlyassumed.
- Existingnineupdated-contract legacyREDs remainopen becausecomponentisnotwired;
  filesystem identity/rawprefix/nodeclosure persistence nextseam afterreview. No
  live128KBrequest/currentbackendcontext increase/newsubscription/oldjournal writes.
Updated [[goals-ledger]], allfullmilestones and fullUniiChatcompliance remainopen.

## [2026-10-09 local] update | Incremental core independently approved; private bound view store dispatched
- Parentchecked62bdacf0 independentreport15artifacthashes andactual282XMLcases:
  50component+203legacy+29freshprobes, nofail/errors/skips. All260inputsmatch4696
  fullgate/95.56coverage; savedview-core-approved.json componentofflineonly.
- Reviewerwarnedadmittedleafcallback failure boundary: coreappendcanpublishsource
  leaf thenadvance raises; adaptermustinspectsourcecount/advance, neverblindduplicate
  originalnote. Futureworld/rawsource/nodeclosure binding isnotpurePolicyauthority.
- Started7fd8cb45newprivateFSviewstore/test/report ONLY, strictverticalTDDwithfresh
  privateScratchdirs, exactsave/reopen/freshprocessprefix/snapshot, source/node/
  world/persona/policy mismatch denial andprivateNoFollow lifetimewriter/fsync ack.
  Reuseexistingauditedprivatehelpers withouteditingrawjournal; no existingmemory
  profile orjournalmigration, tokencontexts, backendmodels ornativeclients changed.
- Currentadoptionchoice remainsunchosen. Implementingofflinepersistence ispossible
  withoutforcingliteral64-128KBontoexistingmodelroutes orclaimingcachehit metrics.
  Consumerintegration/contextualcompactor/rawzoom/date/fulltranscript stillnextseams.
Updated [[goals-ledger]] and [[optchat-definition-update-2026-10-08]], ninelegacy
new-definitionREDs andallfullgameplaymilestones remainopen.

## [2026-10-09 local] update | Private view-store implementation parent gate green; independent persistence review dispatched
- Handoff7fd8cb45 actualnewstore/test/report. Parent18physicalXMLhashes/counts
  verified, includingpreservedinitialscaffold/setup/interruptedprepoison distinctions;
  final314cases=61adapter+50core+203legacy0fail0error,211/219adapterstatementcoverage.
  Executionloghashes/source2ownedhashes match; old260inputsstable.
- Freshfullcheck0/audit0:4757tests+65subtests,95.58%,263completedstorefreeze stable.
  Receipt optchat-view-store-combined-parent-gate.json saved, no assumptions that
  greenoldconsumer tests close nineupdated-definitionREDs.
- Independent9b1dcd39 readonly actualprivateFS/foreignscope/rawprefix/nodeclosure/
  fd/flock/fault-origin/poison probes dispatched before adoption. Sourceprefix
  shape isnotproofactualhostlog/resourceownership; callerbinding documented.
- Author689.03s/49calls exceeds8min/24target, recordednotwaived. Caps1MiBcheckpoint,
  retainedprivatependingfiles, explicitclose/reopen andinheritedroot-helperlimits
  remaininMVPcontract. Onlyfreshscratchtestdirs used, no oldjournal/provider/live
  profile ormodelallocation/nativegame changes. Literalvsscaledadoption unchosen.
Updated [[goals-ledger]], [[optchat-definition-update-2026-10-08]] remainsproposed;
fullmemoryconformance andallfullmilestones remainopen.

## [2026-10-09 local] update | View-store diagnostic repair parent gate passes; independent repair review pending
- Parent verified failed review 9b1dcd39: 334 physical cases, 3 failures, 0 errors;
  the failures reached restoration and physical held-lock checks. Approval denied.
- Repair 86104a60 touches only diagnostic handling and owned tests. Parent verified
  351 artifact hashes, original 3 RED cases and 12 reached owned RED variants,
  then 349 final cases without failure/error/skip. Secondary metadata-fault cases
  are follow-up regressions, not separately observed RED; earlier harness failures
  and failed first GREEN receipts remain preserved.
- Fresh full check/audit both zero: 4772 tests + 65 subtests, 95.59% coverage;
  all 264 repaired-snapshot freeze inputs unchanged. Receipt saved in
  optchat-view-store-repair1-combined-parent-gate.json. Independent ae4f0954
  reviews exact origin, safe owner retrieval, physical locks and unchanged poison/
  publication behavior before approval. No existing journals or live effects.
- Repair overrun 344.79 seconds/39 individual invocations is not waived.
  Allocation-failure constructor handoff remains an explicit bounded limitation.
  Updated the verification reference: fallible diagnostic access must not replace
  OSError, KeyboardInterrupt or SystemExit while cleanup ownership is unconfirmed.
Updated [[goals-ledger]]; original nine consumer conformance failures, deployment
choice and all full gameplay milestones remain open.

## [2026-10-09 local] update | Private view store approved offline; received-skill cognition implementation dispatched
- Parent verified ae4f0954 report hash, all 15 review artifact hashes and actual
  356 unique JUnit cases without failures/errors/skips. Its 264-input freeze equals
  current source and the completed 4772+65/95.59% full gate exactly. Saved
  optchat-view-store-approved.json: bounded offline component only, not migration,
  live integration, provider adoption, measured cache savings or full conformance.
- Source-prefix verification remains caller-supplied; deployment policy is unchosen.
  Original failed review, cleanup-allocation limits and overruns remain recorded.
- Next gameplay-context slice 031812cf implements ReceivedSkillContextReadOnly.
  Parent rechecked all 13 existing measured-skill proof artifacts before dispatch.
  Owned scope is native_skills/domain skills, minimal PlayingClient/BotState/Clef
  hooks, one new test file, manifest and report. No packet-table/spike-client edits,
  allocation, casting, SQL, native sessions, inference or memory activation.
- Require source-shaped Basic9 plus level0 rows to traverse actual framing and
  received-state projection into bounded model input; zero free points cannot mean
  learned zero. Empty LIST and opaque upgrade hints do not prove complete absence,
  permanent ownership or spending eligibility. Session/gap/health/map invalidation
  and explicit partial/unknown/truncated state are acceptance requirements.
- Prior full-gate applicability is tied to its completed snapshot; this new source
  work requires its own independent review and fresh combined gate after handoff.
Updated [[goals-ledger]]; all full milestones, criterion9 completeness and nine
legacy memory conformance failures remain open.

## [2026-10-09 local] update | Received-skill integration remains partial; bounded lifecycle completion dispatched
- Parent verified 031812cf report SHA, all 41 registered artifacts plus 13 preserved
  measured-layout proofs, and physical 214-case final receipt (no failures/errors/
  skips). Actual vertical, update and boolean-timestamp REDs remain preserved;
  overlapping GREEN runs are not added as unique cases. Three allowed existing
  files alone differ from the 264-input approved memory-store baseline.
- The received Basic9/zero-level path reaches bounded Clef facts without free-point
  inference, but original handoff remains PARTIAL: actual PlayingClient map/gap/
  reconnect/epoch/client identity and broader strict/legacy defaults need tests.
  No source-shaped live skill observation, allocation or casting is accepted.
- Completion 8d1c71d2 owns one test file/new completion report and conditional
  minimal production fixes only after genuine reached RED. Frozen 269-input
  completion baseline saved. No rollback to invent historical tests-first evidence;
  original partial report remains byte-identical. Full review/gate awaits completion.
Updated [[goals-ledger]]; all milestones and full criterion9/memory conformance
remain open. No native, SQL, inference, provider or journal changes.

## [2026-10-09 local] update | Received-skill completion parent gate green; independent snapshot review running
- Parent verified 8d1c71d2 completion: all 326 registered artifact hashes, actual
  251-case final XML with zero failures/errors/skips and all three new reached REDs.
  Original partial report and 54 historical proof/layout artifacts remain unchanged;
  all three historical source originals were found and hash-verified.
- Completion's actual map/gap/reconnect/epoch/client-identity lifecycle tests now
  pass through PlayingClient; these are follow-up GREENs, not retroactive REDs.
  Genuine RED fixes reject missing provenance and boolean packet metadata, and
  expose explicit UNKNOWN for legacy-default BotState. No casting/spending added.
- Fresh full check/audit both zero: 4812 tests + 65 subtests, 95.63% coverage,
  all 270 completed-snapshot inputs unchanged. Saved native-skill-context combined
  parent gate. Independent 40ebad3c reviews actual framing-to-Clef/lifecycle and
  unchanged NPC/REST/encounter boundaries before any component approval.
- Completion 556.48 seconds/30 calls versus 240/16 target and two failed Xenon
  receipts remain recorded; historical ancillary tests-first gaps are not waived.
  All native sessions, SQL, inference, providers and existing journals untouched.
Updated [[goals-ledger]]; native received-skill observation, full criterion9,
all full milestones and full memory conformance remain open.

## [2026-10-09 local] update | Received-skill slice independently approved offline; passive native verifier preparation dispatched
- Parent verified 40ebad3c report SHA and all 25 review artifact hashes, actual
  251 candidate + 8 fresh independent cases =259 unique with no failure/error/skip.
  Archived completion reference is overlapping, not added. All 270 frozen inputs
  equal current source and completed 4812+65/95.63% gate. Saved native skill-context
  approval: bounded offline integration only, not native observation or skill use.
- Read standing owned-world execution scope and historical passive-stat executor.
  The latest source gate does not include spike client/table inputs; current client
  matches historical binding but current table is the later cut-in-approved table,
  not the old passive-stat table. Preparation must explicitly resolve those guards
  from prior approvals rather than merely refresh a current hash.
- c10592d8 prepares/tests a NEW passive skill-context executor in isolated scratch:
  exact two existing non-human fixtures, protected 16900/16121/15121 endpoints,
  private lifetime fixture lock, fresh owned-world/offline preflight, received skill
  rows versus generated bounded decision input, both cleanup attempts and fresh SQL
  offline readback. No model, gameplay, allocation/casting, seeding or service effects.
  Child cannot run live sessions; parent reviews the completed executor first.
- Original partial/TDD receipts and overruns remain recorded. Native generated-input
  evidence would not prove actual provider inference, full skill ownership/absence,
  allocation legality, equipment acquisition or any full milestone.
Updated [[goals-ledger]]; all full milestones/criterion9 and full memory conformance
remain open.

## [2026-10-09 local] update | Passive verifier remains partial; helper qualification and launcher completion split
- Parent checked c10592d8's 15 artifact hashes and actual verified-effects XML:
  12 tests, no failures/errors/skips. The prior approved 270-source snapshot still
  matches; preparation makes no production/live/provider/database changes.
- The core is not a native executor: __main__ refuses, private input loading/native
  factory wiring is unfinished, physical ownership/temporary-transport fault tests
  remain, and helper hash observations have no located historical approval binding.
- Parent searched helper names/hashes in reports and read the exact 41/66/59-line
  live-preflight/read-only-baseline/engine-preflight sources. No prior binding was
  recovered. Fresh independent qualification is a new source-review decision,
  not re-labeling current observed bytes as historically approved authority.
- 3f2fcf6a disjoint tasks: one read-only reviewer qualifies exact helper/dependency
  bytes with offline spies; one completes new scratch-only launcher/loader/tests,
  preserving original partial files and refusing absent/rejected helper approval.
  Parent review and fresh world/fixture checks remain prerequisites for native use.
Updated [[goals-ledger]]; no native skill acceptance, casts, spending, inference,
service changes or full milestone closure.

## [2026-10-09 local] update | Observer qualification rejected on two real omissions; versioned fixes dispatched
- Parent verified helper-review SHA/all 127 evidence hashes and actual 19 JUnit
  cases: 17 pass, 2 reached failures, no errors/skips. Helpers can accept duplicate
  map roles/no login and a correctly named volume at the wrong DB destination.
  These are ordinary owned-world misconfiguration counterexamples, not hostile-user
  sandbox requirements. Source and 270-input feature snapshot were unchanged.
- Parent verified conditional-launcher 17 artifacts and physical 40-case receipt
  without failures/errors/skips. Actual default-adapter full patched-boundary
  integration remains missing; native use is not approved.
- 6f4e1a78 split: helper cycle1 creates new copies with exact unique qualified
  service IDs/images and fresh volume/type/destination guards; another isolated
  worker exercises default native assembly fully offline and binds future repaired
  helpers only through verified parent approval. Original rejected helpers/review,
  partial preparation and conditional launcher remain unchanged.
- No helper approval/native-result receipt is minted. No actual Docker/SQL/native
  network, inference, private-config or service effects occurred in these tests.
Updated [[goals-ledger]]; all full milestones and live criterion9 remain open.

## [2026-10-09 local] update | Versioned helper faults GREEN; default executor verified offline; independent reviews pending
- Parent checked helper repair1 SHA and all 704 artifact hashes; physical final
  27 cases pass without errors/skips, with original two and new ten behavioral REDs
  retained. Role/qualified-ID/image bijection and fresh DB storage binding repaired
  only in new helper copies. Original helpers/review and 270 code inputs unchanged.
- Helper qualification remains PARTIAL: unweakened broad scratch Ruff/Bandit
  failures and inherited baseline comparisons are recorded, not called clean.
  Independent review must distinguish actual security/logic conditions, including
  non-optimized Python assertion guards, from inherited script-style diagnostics.
- Parent checked default-integration SHA/all 18 artifacts and physical 50 unique
  cases (40 preserved +10 new). Actual assembled default adapter is exercised under
  patched system boundaries, with functional-failure CLI exit1 fixed tests-first.
  Transitive helper dispatch is synthetic, not an actual world inspection.
- 94f4c55d runs read-only disjoint helper repair qualification/quality disposition
  and executor admission/deadline/ownership/failure reviews. No parent approval
  receipts are issued yet. No native/SQL/Docker/inference/service actions occurred.
Updated [[goals-ledger]]; full milestones, live skill receipt and memory conformance
remain open. Historical TDD limits and overruns remain unwaived.

## [2026-10-09 local] update | Native helper/executor reviews blocked; final bounded guard repairs dispatched
- Parent verified helper review 252 evidence hashes and physical normal 33-case
  pass. Optimized PYTHONOPTIMIZE=1 counterexamples instead accept wrong role/storage
  and reach mocked SQL; -B only controls bytecode writing, not assertion stripping.
  B101 is a real blocker, not inherited-style debt to waive.
- Parent verified executor review 16 artifact hashes and actual 58 cases: 57 pass,
  1 reached owner-loss failure, no errors/skips. After both unlock and close fail,
  a physical flock remains held but the owner has fd=None/quarantined=False.
  Exact primary control-flow origin/frame survives; that alone does not prove safe
  resource handoff. Initial reviewer harness failures are retained separately.
- 1d9d426f owns new helper repair2 and executor repair1 versions only. Helpers'
  final automatic cycle2 must reject optimized entry before effects and force child
  PYTHONOPTIMIZE=0. Executor must retain uncertain fd/quarantine and never auto-retry.
  Old failed reports/artifacts, production, private inputs and services unchanged.
- Native use remains blocked pending fresh frozen independent reviews and parent
  approvals. Any remaining helper blocker after cycle2 requires user escalation;
  no feature/quality relabel may reset its repair budget.
Updated [[goals-ledger]]; no actual TCP/Docker/SQL/HTTP/inference or native result.
All full milestones and criterion9/native acceptance remain open.

## [2026-10-09 local] update | Final helper optimization repair and retained-lock repair parent-verified; combined review running
- Parent checked final-normal helper XML33 and executor final XML66: no failures,
  errors or skips, exact recorded hashes. All six runtimefile hashes match receipts;
  completed artifact freeze488 and all 16547 prior file hashes verified directly.
  Probe core remains byte-identical. Optimized helper denial and lock-origin REDs
  remain preserved, not replaced by synthesized success records.
- Helper2 entrypoints now explicitly reject optimized execution before effects;
  executor entry rejects optimization and actual/nested Python dispatch forces
  PYTHONOPTIMIZE=0. Uncertain lock close retains fd/quarantine and refuses retry.
  Tests cover still-held flock and release-before-raise separately.
- File-mutation warning was an ambiguous test patch that did not execute. Parent
  read the actual test_repair.py and verified its matching frozen hash and physical
  tests instead of assuming a successful edit or silently rewriting evidence.
- Final c1d0dc39 independent combined review uses 283 frozen inputs, three helper
  files plus guards/probe/native launcher. Broad scratch Ruff/Bandit findings stay
  recorded; conditional B101/S101 disposition still requires verified invocation.
  No helper/executor parent approvals, native sessions, SQL, Docker or inference.
- Helper budget final2/2; executor1/2. Further helper failure requires escalation,
  not a reset or relabelled quality loop. All original evidence remains preserved.
Updated [[goals-ledger]]; all full milestones/criteria and native skill acceptance
remain open.

## [2026-10-09 local] update | Combined offline qualification approved; runtime execution approvals timed out
- Parent verified final c1d0dc39 report SHA, 33 review artifact hashes and actual
  helper33/executor66/fresh4 =103 unique cases without failure/error/skip. Both
  283-input and 488-completed freezes match actual files. Saved offline-approved
  receipt only; qualification does not itself activate the native executor.
- User explicitly answered 'Authorize the passive probe', then 'Approve verification
  and passive probe' after the first runtime approval timeout. An initial coordinator
  syntax error ran no code; both subsequent tool attempts separately timed out
  without execution consent and ran no code. No fallback tool was used to obtain
  that blocked private-binding/approval/native outcome.
- Read-only inspection confirms required helper-repair2-approved.json is absent.
  Private-input binding, exact operational approval and native sessions remain
  unexecuted. Further action requires the runtime execution approval to be cleared;
  no repeated automatic retry or reinterpretation of silence as consent.
Updated [[goals-ledger]]; all full milestones/criteria remain open, with verified
finite offline qualification but no live skill-to-input acceptance.

## [2026-10-09 local] update | Resent approval succeeded; passive native skill-to-input probe accepted narrowly
- User requested 'send for approval again' and explicitly re-authorized verification
  and passive probe. The exact blocked code then executed, validating private
  uid/0600/regular/no-follow inputs without displaying values; saved exact reviewed
  approval and canonical byte-identical combined-review copy. No code/runtime guard
  was changed or skipped to obtain the previously blocked outcome.
- Actual unchanged native executor command through tiny offline Nix and nonoptimized
  Python returned PASSIVE_PROBE_EXIT=0; stderr empty. Read back native report:
  passed true, two identity-matched fixture receipts, each 010F list contains skill
  ID1/effective level9 and the generated decision-input section matches received
  rows. Readers healthy; vitals each HP86/86 SP20/20. Current skill_points is null,
  hence UNKNOWN, not historical zero or eligibility authority.
- Both supported cleanup confirmations and fresh SQL both-offline readback pass;
  no errors/quarantine. Actual model calls0, native gameplay actions0, direct
  SQL writes0. No account changes, service starts/resets or private-value disclosure.
- Parent saved playing-mvp-passive-skill-context-acceptance.json binding actual
  native report hash. Bounded live received-skill→generated-input accepted only;
  no actual provider request, skill allocation/cast, completeness/permanent
  ownership, equipment or full-milestone acceptance inferred.
Updated [[goals-ledger]]; all full milestones and full criterion9 remain open.

## [2026-10-09 local] update | Skill tooltip sanity-check gap becomes bounded public-meaning implementation
- User asked whether skill receipts include tooltip information. Parent checked
  pinned SKILLDATA and actual decision serializer: no tooltip/description payload;
  current model receives numeric fields, not explanation. DB Description is a
  display label, not by itself a meaningful tooltip paragraph.
- 498f4934 owns new public-skill domain/adapter/asset/test/report and minimal
  PlayingClient/BotState/decision/CLI opt-in injection. Baseline272 saved including
  both actual public skill-db hashes; all previous approved code still matched.
- Initial public semantic coverage is ID1/NV_BASIC only, for pre-re and Renewal
  catalogs; actual compiled native world remains pre-re. Require pinned primary
  server source for conditional basic interactions, provenance and honest unknowns.
  Select only received IDs, max8cards/2048 total UTF8bytes, public advice distinct
  from experience, state facts and casting/spending authority. No new client tooltip
  mirroring, StubMechanics meanings, provider changes or public→private journal writes.
- Strict vertical RED→GREEN must exercise actual received Basic9 through wrapper
  and decision input with readable public meaning; no all-skill/full-tooltip claim.
  Parent independent review/full quality gate required after completed snapshot.
Updated [[goals-ledger]]; all six milestones and ten criteria remain open.

## [2026-10-09 local] update | User adds subgoal11: investigating LLM planner, CLEF executor
- User explicitly requested LLM context investigation/objectives/plans and messages,
  with CLEF fast plan execution and escalation for replanning. Supplied a paste-ready
  subgoal prompt; subsequent continuation retains this new instruction.
- Created accepted ADR021 without rewriting accepted ADR003/011 historical text;
  event-driven scripts remain zero-model-call mechanical work. Added OPEN subgoal11
  to ledger/index with private/public/current-state separation, freshness/unknowns,
  structured admission, bounded nonblocking replan, continuity/dashboard acceptance.
- Steered 498f4934 to keep public BasicSkill meaning scope provider-neutral and avoid
  a concurrent planner/brain rewrite. It remains a disjoint source-knowledge slice.
- Dispatched 60420ec8 for new-file-only typed plan admission and bounded lifecycle:
  single-flight request, identity/ruleset and capability checks, stale/foreign reply
  denial and cooldown/timeout/retry state. No old brain, native, provider or journal
  changes. Actual LLM tools, plan execution, persistence/dashboard remain later gates.
Updated [[goals-ledger]], [[adr-021-llm-planning-clef-execution]] and [[index]];
all six full milestones and all eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Basic Skill public meaning candidate parent-verified; scoped independent review running
- Parent verified 498f4934 report SHA, eight owned source/data/test hashes, seven
  actual JUnit receipts and source/gate-log hashes. Final261 cases pass; feature25,
  new modules100% coverage. Genuine vertical/CLI/malformed/budget REDs preserved.
- Two source-frozen pre-re/Renewal cards explain Basic Skill conditional utilities,
  keep omitted declared Type unknown and don't mislabel DB Description as tooltip.
  Opt-in constructor/CLI routes advice only for received IDs, separately from
  received levels/private experience/native permission. No real provider/native use.
- Independent6e1d8347 reviews completed277input feature snapshot. The new-file-only
  planner worker remains disjoint; parent full-root gate waits for both completed
  slices to avoid giving a moving source tree a false whole-project approval.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Real existing-brain compatibility probes expose three planner/chat integration gaps
- Four physical offline probes: three reached assertion failures, one pass. Actual
  brain uses CLEF answers to install FarmPlan without LLM; PlanExpired only clears
  it without replan escalation; chat sends player text without current job/map or
  context investigation tools. Twenty script steps add no model calls.
- Preserved initial test-harness AttributeError (.id rather than .plan_id) separately;
  corrected rerun and final three behavioral failures have distinct physical XML.
  Overlapping executions not summed. This is new-goal compatibility evidence,
  not native gameplay, real-provider inference or complete future acceptance tests.
- Saved run/reviews/llm-planner-existing-brain-compatibility.json with source hashes,
  receipts and limitations. Public meaning277input review freeze remains unchanged.
  Plan-lifecycle candidate and independent meaning review are still pending; no
  production brain/provider edits or live effects performed by these probes.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Stable combined gate passes; public Basic meaning approved offline; plan review dispatched
- Both workers no longer live; parent recovered exact completed reports rather
  than continuing to wait for delayed fan-out notifications. Meaning reviewer PASS:
  269 physical unique cases0fail/errors/skips; parent verified ten referenced
  artifact hashes and unchanged277input feature dependency freeze.
- Plan core: parent verified four current source hashes, all91 preserved artifacts,
  25 final physical cases and17 actual RED/GREEN pairs. Grouped later assertions
  remain follow-up proof, not separate invented tests-first history. Provider tools,
  planner/chat adapters, scheduler/native/brain/dashboard consumers still OPEN.
- Frozen combined283inputs; actual root task check0/audit0,4862physical tests plus
  65subtests/95.76% coverage. One inherited Starlette/httpx deprecation warning.
  Initial report parsed rounded TOTAL96%; immediately corrected to precise95.76%
  from actual coverage summary; original gate log preserved. No thresholds changed.
- Saved combined-parent-gate and BasicSkill bounded offline approval with exact
  feature/current/gate equality. Independent d9a26ccc now reviews plan core only,
  no code repairs. Existing three legacy brain planner compatibility REDs remain
  separate uncovered acceptance obligations, not waived by green main suite.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Independent plan-core blocker verified; bounded timing repair1 dispatched
- Parent recovered d9a26ccc BLOCKED report after no live children: author25 passed,
  fresh10 have one reached invalid-timing failure/no errors. All report artifact
  hashes and current original283source freeze matched. Oversized integer duration
  raises OverflowError during premature isfinite conversion, retains pending and
  fails to increment rejection; no source repair made by reviewer.
- Saved repair1scope and dispatched656d0e7b for domain planning numeric/timing
  validation plus permanent tests only. Reproduce same-class oversized deadline/
  config arithmetic hazards before fixes; no broad schema/brain/provider rewrite.
- New core cycle1of2; historical exhausted budgets unchanged. Prior4862+65/95.76%
  green gate does not waive fresh independent blocker. Repaired snapshot needs
  parent full gate and independent completion review. BasicSkill offline approval
  is unchanged; no native effects or full planner acceptance claimed.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Timing repair1 parent-verified; fresh root gate passes; final independent review pending
- Verified656d0e7b report SHA, actual39case RED5fail/0error/skips and final39passes,
 19currentartifact hashes plus106 preserved original/review artifacts. Only allowed
 domain planning and tests changed;281of283protected inputs unchanged. No catch-all
 or clock restrictions: numeric bounds before isfinite; deadline window before
 subtraction. Four new permanent regressions are genuinely pre-fix RED.
- Froze286completedinputs and dispatched597f05f0 read-only independent re-review.
 Fresh root check0/audit0,4866physical tests+65subtests/95.76%, freeze unchanged.
 Initial parent aggregation guessed a registry was a Path and raised TypeError;
 no report written by that attempt. Inspected actual dictionary, verified all106
 physical hashes, and saved the corrected combined-parent-gate artifact.
- Core approval waits for independent completion verdict; existing three brain
 integration REDs, realLLMtools/provider/scheduler/native/dashboard gates remain
 open. BasicSkill bounded offline approval unchanged; no native effects.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Repaired plan core approved offline; owner-bound investigation reader TDD dispatched
- Recovered597f05f0 completed PASS after no live workers:43unique physical cases,
 39existing+4fresh,0fail/error/skips/blockers. Parent verified17review artifacts
 and286input/current/full-gate equality. Saved bounded offline core approval;
 repairedCORE-TIMING-001 closed atcycle1/2, all original failed receipts retained.
- Next3725764c owns only NEWplanning_context.py/test/report. Concrete reader topics
 character/map/receivedskills/publicrules/private ExperienceNote search/read.
 Mustdenyforeign/currentbindingdrift beforeprivateaccess; selected publicrulebook
 lookup maydescribeunreceivedskill onlyaspublicadvice, neverobservedpossession.
- Rawstorednote pagination/UTF8 continuation without .view/.ensure_summarized avoids
 implicit summary-model/cache writes. Does not migrate journals, choose UniiChat
 scale/providercontextpolicy, exposeotheragent knowledge or implementLLMtool-loop.
 Source-shapedPlayingClientBasic9 vertical TDD required. Realprovider/brain/native
 objectiveprogress/dashboard/restart acceptance remains separate and OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Actual local LLM public-rule tool round trip exercised without bot access
- Read-only existing-runtime health/props: chat healthy,4096token single slot,
 actualbuild b11146-7fe450e, template reports tool support. Default local CLEF
 listener absent; this says nothing about hosted/private decision-provider health.
 Binary --version printed stderr, not stdout; actual build and local vendored-doc
 source binding not assumed from flake comments or outer-project Git revision.
- Actual two-request local chat protocol smoke: forcedpublic_rule skill:1, one
 validatedhandler using strict pinned public catalog, correlated role-tool response,
 finish tool_calls then stop. Latencies1.59/6.27sec; provider token totals261/793.
 No services/config/contextbudget changes, private memory or bot/game sessions.
- Saved actual request/response/tool/result artifacts and hashes; report
 run/reviews/llm-planning-local-tool-protocol.json. Result remains a scratch probe,
 not production reader/PlannerPort integration or autonomous tool-choice proof.
 Answer kept UNKNOWNserver/possession/casting but added unsupported fairness gloss;
 mechanical admission remains required. Provider-reported cached tokens are not
 fullUniiChat compliance or measured multi-agent cache savings.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Concrete investigation reader parent-verified; fresh root gate passes; independent review running
- Recovered3725764c completed candidate after no live workers; two NEWsource/test
 files only,26feature/91scoped physical GREEN cases,0fail/errors/skips/module91%
 coverage. Parent verified34artifacts/eight physical RED/GREEN XMLreceipts, twoowned
 hashes and286priorinputsunchanged; originalauthorfreeze288before report, parent
 completedfreeze289includingreport. No originalcore/brain/provider/memory edits.
- Actualsource-shapedBasic9PlayingClient→reader pipeline; strictownerbinding,
 unknowncharacterfields, public-ruleunreceivedknowledge distinctfrompossession,
 storedExperienceNote search/read without model/summary/storage writes, UTF8chunks.
 ReaderstillnotrealLLMtools/scheduler/nativeeligibility/planner integration.
- Dispatched4f00fd56 read-only independent completed-snapshot review. Parent root
 check0/audit0,4892physicaltests+65subtests/95.67%,289sourcefreezeunchanged.
 Saved llm-planning-context-combined-parent-gate.json; no componentapprovaluntil
 independent result. Full native/context-richplan/social/dashboard milestones open.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Investigation reader approved offline; bounded real planner adapter TDD dispatched
- Parent verified4f00fd56 completedPASS:91candidate+8fresh physical cases nofail/
 error/skips,19review artifact hashes and289current/review/fullgate equality.
 Saved llm-planning-context-approved.json; component read functions approved only,
 not actualLLM/privateinference/nativeplanexecution or fullUniiChat adoption.
- Confirmed actualexistingserver /apply-template fulltoolrequest + /tokenize
 yields239tokens includingtoolname/schema, exactlypriorrealinference239prompt
 tokens. Puretemplate/tokenization requests only; no inference/context changes.
 Primarylocalserver docs inspected, samecompiledsourcebinding not assumed.
- Dispatched50f9abeb NEWplanning model port/appLLMloop/localHTTPadapter/tests/report.
 Strictreadonlytoolallowlist/currentowner/deadline/callbounds; strictgeneratedplan
 decodeidentityboundfromrequest/currentcapabilityvalidation, actualtokenizer slot
 admission beforegeneration. No unboundedprompt/silenttruncation/newmodelpolicy.
- Worker musttestactualHTTPassemblywithMockTransport offline and realReader→tools→
 ProposedPlan→existingLifecycle admission. Parentrealproviderverification later;
 no oldbrain/CLI/chat/native/memory changes bythisslice. ThreeoldconsumerREDs still
 open untillaterlivebrain/scheduler/chat integration. Allfullgoals retained.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Source-inspected next host/phase integration hazards while adapter writer continues
- Read existing scheduled runtime/scripts/native adapter; no source edits. Startup
 andtick call brain synchronously; native keepalive is in drain_native_events.
 A future planner must use a separate job path without blocking native event drain.
- Emptybrain script actions can stillbecome loot/patrol/NPCexploration in native
 mechanical fallback. Pending/invalidplanneedswhole-tick explicitsafe gate, not
 merelyemptyresult. IdleTownScript emitsmoves, so cannotstandinforpassive waiting.
- Existing FarmScript consumeslegacyFarmPlan targetnames ratherthanordered typed
 ProposedPlan/species IDs. Validatephaseexecution/perceivedactor mapping/native
 prerequisites atrealconsumer; neverinterpretpublicspecies asruntimeactorID.
- Saved source-hashed llm-planner-brain-integration-frontier.json fornextbounded
 integration; this is source reconnaissance, not implementedbehavior oracceptance.
 Adapter50f9abeb remainsrunning; scope stillnewfilesonly/nomodel/nativeeffects.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Planner adapter candidate parent-verified; whole-root gate passes; independent review pending
- Recovered50f9abeb completedreport after no live worker:25physicalpasses, three
 newprodmodules+test only. Verified25artifacts/fourcurrentownedhashes/289unchanged
 priorinputs. Preserved scaffoldcollectionerror separately; genuinevertical/HTTP/
 sanitizationREDs andfollow-upnegativecases notmisrepresentedastests-first.
- Froze294completedinputs, dispatched5dd1d205 read-onlyindependentreview. Real
 Reader→modeltools→stricttypedplan→Lifecycleadmission andrealHTTPMockTransport
 preflight exercised offline; no actualLLMcall/brain/CLI/otherprovider activation.
- Fresh root check0/audit0,4917physicaltests+65subtests/95.27%, sourceunchanged;
 saved llm-planner-tool-loop-combined-parent-gate.json. No thresholdweakening.
 Review tests will inspect denials/correlation/unknownfacts/tokenizeradmission and
 schema/clockconsistency before separate real local model planning acceptance.
- All full gameplay/social/dashboard/progression milestones remain OPEN; source
 safe-pending/phase-execution frontier retained for next consumer integration.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Planner clock-contract blocker verified; enum-vocabulary usability completion scoped in repair1
- Recovered5dd1d205 completed BLOCKED report:43physical unique cases25old+18fresh,
 41pass/2fail/noerror/skips. Parent verified8artifact hashes and294source equality.
 Clock1e12+1 acceptedbyrealCore/decodedPlan isdeniedpremodel byarbitraryadaptercap.
 Schema probe failure isseparatenonblockingusabilityrisk, notsecondlogicblocker.
- Scope explicitlyauthorizesa4c56287 repair1/2 toremovefiniteclockcontractnarrowing
 andpublishexistingObservableCondition/fallback/ReplanCondition values inmodel
 schema. Onlyapp/tests modifications; no newfields/abilities/caps orHTTPchanges.
 Both actualfailedprobes mustREDbeforefix; originalreports/artifactsimmutable.
- Prior4917+65/95.27% green gate doesnotwaiveblockingindependentcounterexample.
 Freshmatchingcompletedreview/fullgate requiredbefore actuallocalplanningproof.
 No model/native effects or oldbudgetreset; all fullstandinggoal criteriaOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Planner clock/schema repair1 parent-verified; fresh root gate passes; final review running
- Verifieda4c56287 report SHA,29artifact hashes/fivepreservedreports, pre-fix47case
 RED5fail/0error andseparatecorrectedschema1assertionRED, final47unique passes.
 Two largeclocktests+schema failbeforefix; invalidclock followupalreadyGREEN.
 InitialschemaKeyError andlint/type failures retained, notgenuineassertionRED.
- Only app/tests changed;292protectedsourceinputsunchanged. Froze297completed
 inputs, dispatched88fd2f68 read-onlyindependentcompletionreview. Parentfirst
 metadata verification resolvedrelativepreservedreportpathsfromwrongcwd andfailed
 beforewritingfreeze; correctedrepo-relativepathhandling verifiedallfive hashes.
- Fresh root check0/audit0,4921physicaltests+65subtests/95.29%,297inputsunchanged.
 Saved repair1combinedparentgate. No native/model calls, brain/CLI/chat activation,
 new abilities/contextpolicy changes or oldbudgetreset. Actualautonomousmodelplan
 andconsumer safety still pending after independentverdict.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Adapter approved offline; actualmodel failsclosed twice; final capability-context completion dispatched
- Verified88fd2f68 PASS51unique cases47old+4fresh/12artifact hashes/current297input
 andmatching4921+65/95.29rootgate. Savedboundedofflineadapterapproval; not realmodel
 orbrain/nativeacceptance. No sourcechangedby independentreview/parentapproval.
- RealLocalPlanningModel/LlmPlanner/Reader/Lifecycle withsyntheticpacketcharacter:
 initialScratchPYTHONPATH lackedrepo tests andfailedbeforeanymodelcall; corrected
 exact invocation. FirstactualLLMresponse2toolcalls inonetturn despiteparallelfalse,
 guarddenied0handlers. Originaloutputs/resultretained; no privateuserjournal/world.
- Onebounded retry explicitcallerone-call/public-rule syntax:3realmodelcalls,
 2investigations, thensubmitunsupportedtravel+inventedrequired_fact. Production
 freshcapabilityvalidatorcorrectlydenied; noactiveplan/noactuation. Both realfailed
 resultsrequests/responses saved; no generateddatarewrites orfakesubstituteresults.
- Published llm-planner-real-model.json andscoped31e237c8 finalcycle2/2: app/tests
 onlycurrentcapabilities visibleincontext/schema, explicitsinglecall/pubicrule
 syntax. Keepfinalguards unchanged. Remainingproviderblockerafterthisscope must
 escalate, notanotherautomaticloop. Actualplan/nativeprogress/fullgoals OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Final capability-context completion parent-verified; root pass; completion review pending
- Verified31e237c8 completedcandidate:59unique physical passes51prior+8new,
 33artifact hashes; actual1contextRED/1protocolRED beforeimplementation, sixnew
 followupsnotclaimedhistoricalRED. Initialqualityfailures preserved thenallscoped/
 wholeSourcegates passed normalthresholds. Twoownedsourcechanges/295protectedsame.
- Froze302completedinputs; dispatched4c89a083 read-only final review. Exactcurrent
 supported phases/maps/facts/fallback schema andADVISORYcontext eachround, one-call
 trustedsystemprotocol/publicrule syntax, finaldecoder/identity/round/token guards
 retained. No inference ornativeeffects bywriter/parentgate.
- Parent fresh root check0/audit0,4929physicaltests+65subtests/95.31%,302inputs
 unchanged; saved completion2combinedparentgate. Realprovideracceptancepending:
 previousfailedattempts are notpassed. Cycle2/2 exhausted; scopedrevieworprovider
 blockerrequiresescalationratherthanadditionalautomaticrepair. FullgoalsOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Final offline completion approved; final actualprovider probe rejected oversized reason; budget escalation
- Verified4c89a083 PASS63unique cases59old+4fresh,11review artifact hashes/source302
 equality andmatching4929+65/95.31gate. Savedcompletion2offlineapproval, notactual
 autonomousmodel/nativeacceptance. No sourcechangedafterfrozenindependentreview.
- RanfinalproductionLocalPlanningModel/Reader/LlmPlanner/Core originalsynthetic
 fixture scenario (not manual one-call retryreason). Twoactualmodelcalls andone
 investigation; generatedsubmitplan reason273UTF8bytes >unchanged256bound.
 Correctdecoderrejection/no planadmitted, no outputtrimming/normalization/fakeplan.
- Savedrawnetworkresponses/result and llm-planner-real-model-final.json hashes;
 previousfailures remainfailed. No actualworldsession/privateuserjournal/action.
 Actualproviderformatadherence remainsblocked; cycle2/2 exhausted. No automatic
 furtherrepair. Usermustchooseauthorizeoneformat-onlyschema/instructioncorrection,
 differentexistingprovider evaluation orleaveplannerunactivated. FullgoalsOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | User explicitly authorizes one additional format-only completion and bounded rerun
- After exhaustedbudget/finalreal273byte reason denial, clarification UI asked for
 a decision. Userselected 'Authorize one format-only correction and bounded rerun'.
 Saved llm-planner-format-completion-scope.json; dispatched785e6055 app/tests only.
- Conservative64Unicodecharacter objective/reason tool-schema/instructions, original
 256UTF8byte decoderguard unchanged. No outputtrim/normalization/handmadeplan or
 additionalphase/ability/schemaframework. StrictTDD,freshreview/fullgate thenone
 realModelrerun; priorautomatic2/2 remains exhausted, notreset.
- This is freshuserauthorizedexception, notinferredconsentfromstandingcontinuation.
 No furtherautomaticloop orbrain/nativeactivation allowed bythisgrant. Allfull
 milestones/criteriaOPEN andpreviousactualfailedprobespreserved.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Format-only behavior verified; mechanical refactor; root pass and review pending
- Verified785e6055 PARTIAL handoff:65unique physical passes and16artifact hashes;
 production-POST assertion RED then GREEN, two later byte-boundary regressions.
 Objective/reason maxLength64 and concise instructions;256UTF8 validator unchanged.
 Original Black/Ruff failed on a new103column test assertion; remaining gates passed.
- Completed same authorized change's mechanical REFACTOR: Black only test file,
 compared before/after Python AST identical, production unchanged. Preserved original
 PARTIAL report643c38c2f8ec9e640e2bc2f5de1d13fda7a0b45cc8bf0e687c8b16166b6f8191,
 all failed lint receipts. No extra behavior repair or exhausted-budget reset.
- Froze308completed inputs and dispatchedba797b5c read-only independent review.
 Fresh root check0/audit0,4931physicaltests+65subtests/95.32%,308inputs unchanged;
 saved format-combined-parent-gate. Single user-authorized real-model rerun remains
 unused pending independent approval. No native activation or full-goal acceptance.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Format review verified; actual model plan admitted with reporting failure; exact offline replay; host frontier dispatched
- Recovered completedba797b5c report after delayed notification; parent69physical
 cases65prior+4fresh/14artifacts/308inputs/full4931+65/95.32gate matched. Offline
 format approval saved;65handoffpasses andfailedlint/refactor chronology retained.
- Executed singleuserauthorizedactualrerun:2HTTPresponses investigatepublic_rule
 skill:1 thenRestplan prontera/reason62UTF8bytes. Actualsuccess-only branch reached
 afterlifecycle.admitTrue andnosentactions; finalresultserializationFAILEDTypeError
 frozenset required_facts. Exit1 preserved, nooriginalcounter/total-latency invention.
- Saved reportingfailure immediately; exactcapturedoutputs replayed OFFLINE through
 productionreader/planner/core, bothrequestpayloads byte-value-equivalent toactual
 savedrequests, admissionPASS/newinference0. Properreportencoder changesreportonly,
 not modelarguments. Rawnetworkfiles intact. Saved format-real-model-acceptance
 withexplicitactualtrace/offlinereplay limits; earlierfailedrunsremainfailed.
- Useronecorrection/rerun grant consumed; no furthermodelrerun/repairbudget reset.
 Scope proves bounded SYNTHETICcontext modelinvestigation/plan admission, notreal
 worldexecution/semanticobjectiveprogress orfullsubgoal11. Modelprose isn'treceived
 possession/inventory completeness. All6milestones11criteriaOPEN.
- Dispatched3ab05c42 read-only actualScheduledAgent/brain integration frontier,
 implementation-ready opt-in nonblocking/pendinggate/freshadmission/CLEFscripts
 scope withfiniteofflineacceptance. No detachednewframework ornativeactivation.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Actual pending fallback RED verified; bounded opt-in host segment assigned
- Verified3ab05c42 reportbfd05fca14b710669dcc34f38a462dffecb938608a0e9a565a44968c2ee5b98f,
 threeartifacts,308unchangedinputs andonephysicalassertionRED/noerrors/skips: real
 ScheduledAgent ticks throughPlayingClient emittedpickup despitehypotheticalpending
 marker;20secondkeepaliveassertionpassed. Notfutureprotocolacceptance.
- Chose conservativeOFFLINE implementation policies:64private notes/8192textbytes,
 32768jobserializedbytes;UNKNOWNonoverflow/lockcontention, no truncation/renumbering;
 jobdeepcopy/owner-onlyfreshadmission;singlephysicalworker/singlecompletionslot,
 provider30seconds/max4calls/planning120seconds/join1second;retainunresolvedownership
 anddenyreplacement/reconnect. Existing4096token policy unchanged, no migration.
- Savedhost-segment-scope and [[llm-planning-host-segment]]. Assigned6e5a3cef actual
 opt-inCLI/AgentHost/ScheduledAgent integration IDLE/REST, explicitpending/active
 fallbackgate,CLEFexecution-only,recovery/cleanup,strictverticalTDDsixfiniteactual
 hostcases. Legacydefaultunchanged;freeform/farm/progression/social/dashboardOPEN.
- This is a new host feature scope, notproviderrepairbudgetreset. No newrealmodel
 calls/native/world/SQL/Docker/privatejournal/service/liveflagactivation authorized.
 Previousrootgate becomeshistorical on sourceediting;freshfrozenreview/fullgate
 requiredbeforeapproval. Allsixmilestonesandelevencriteria remainOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Independent historical passive receipt recovery during host implementation
- Recovered exact stored nativepassive report, no newnative/execution effects:
 bothfixturesBasicID1 effective9 SPcost0/range0/inf0/upgraderaw0, HP86/86 SP20/20,
 freeSkillPointsNULL/UNKNOWN. Bothsupportedcleanup/freshhistoricaloffline true,
 noerrors/quarantine; modelcalls/gameactions/directSQLwrites0. Generatedinputonly,
 notprovider-delivered. Existing acceptance already recorded; notnewliveacceptance.
- Savedsourcehash-bound passive-skill-context-recovered receipt; explicit historical
 scope/currentstateunknown preserved. Steered6e5a3cef nottoinfer freepoints0 or use
 syntheticrange1/inf-1 asnativefacts. No sourceoverlap; hostwritercontinuesTDD.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | User asks to ensure continuation; interrupted host worker recovered and split into two active scopes
- On 'make sure the work continues', currentdelegate list wasempty. No6e5a3cef
 terminalreport existed. Exactsource/trace recovery found CLI+AgentHost changes,
 no-op PlannedBrain scaffold, missingcontext/runtime modules. Bothconstruction XMLs
 physically1failure/noerrors/skips; GREENfilename isnotpassing evidence. Actual
 failure isaccidentalone-tuple legacybrain inAgentHost._build_agent.
- Preservedinterruption receipt and312inputresumptionfreeze. No reset/stash/rollback,
 completedfeatureclaim oroldqualitygate reuse. No secretvalues preserved inreports.
- Dispatched4616e552 TWOdisjointcontinuations: constructorTDDfix+failclosedunfinished
 opt-in guard, and owner-safeboundedcontext/nonblockingMemoryLog capture. Separate
 source/report/scratchownership; siblingchanges excluded explicitlyfromfreezeclaims.
 The actualruntime/keepalive/pendinggate/CLEF/scriptacceptance stillfollows afterthese
 prerequisites. Sameunfinishedfeature, nooldrepairbudget reset orrealinference.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Constructor candidate119 verified; context provisioning/test approval blocked; independent constructor review continues
- Verified4616e552 constructorreport572c7dd0ec55ac15491c8811807c39cf600bdb37c6e771b3a5f28aca635f1aa3:
 actual119unique cases0fail/errors/skips,18artifacts/four current source hashes;
 legacyone-tuple repaired andunfinished PlannedBrain.start nowexplicitlyfailsclosed
 undergenuineREDGREEN. NormalBlack/Ruff/projectmypy passed. Actualpipelinepartial.
- Contextreportcefb418d2750dda56ac5a19fc03ccca15bada9a6838c0827bace5677faccd407
 isPARTIALbeforebehavioralRED: newcapture returnsNone, initialtestwrittennotrun,
 MemoryLog unchanged. Missinguv/scratchenvsetup failure notRED. Followupapproval
 timedout10minutes:zero toolcalls/no bypass. No captureimplementation accepted.
- Parentread-onlyprerequisite lookup foundexistingprojectPython/pytest available;
 requestedfreshscope toREUSEit underpinnedNix forofflinecontextTDD, no newprovisioning
 ordownloads/model/native/privatejournal effects. UIalsoTIMEDOUT, nounconsented
 testexecution/retry/alternateoutcome. Approvalstillneeded forcontextpath.
- Parentfreezehelper initiallyNameError afterkernelstatechangedacrossUI wait;
 reloadedexplicitinputs, no sourceeffects, thenfroze316constructorreview inputs.
 Dispatched3612fb8e independentREADONLYconstructor review only. Explicitly excludes
 blockedcontexttest andfullrootsuite. No sourcewritercurrently authorized toresumeB.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Scoped constructor independent review123 physically verified; context remains approval blocked
- Verified3612fb8e report93088b9143c1835f6c5269ba40e8584ec780ce6f2a16bfd49659392f28a16568:
 actual119regressions+4fresh disjoint cases=123unique passes,0fail/errors/skips,
 candidate18artifact hashes and316currentfrozen inputs unchanged. Normalquality
 scopes passed; no blockedcontexttest/provisioning/model/native effects occurred.
- Savedconstructor-reviewed receipt asSCOPED only. No freshfullrootgate whilethe
 suiteincludesseparatelyblockedunfinishedcontexttest. Legacybrain construction
 restored; opted-inunimplementedstart explicitlyfailsclosed. Hostpipelinepartial.
- Contextstub remainsunimplemented andunintegrated; freshapprovalstillrequired
 afterpreviousUI timeout. No inferredconsentfromasyncreviewnotification.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Fresh context TDD approval received; existing interpreter reaches first behavioral RED; capture completion dispatched
- On latest 'continue', clarification explicitlyasked forblockedcontextscope; user
 selected 'Approve offline context TDD using the existing environment'. Saved
 job-context-resume-authorization; earlierno-consent timeouts preserved, notbypassed.
- ExecutedexistingprojectPython underlockedNix, noenvprovisioning/downloads:
 existingcapturecontract1actualassertionfailure 'captured is not None',0errors/skips.
 SavedphysicalparentREDXML/sourcehashreceipt. Previousmissinguv/setup failures are
 notbehavioralRED. No production source changed byparent, model/nativeeffects0.
- Froze319resumptioninputs anddispatchedf3010544 contextmodule/MemoryLog/tests only,
 strictverticalTDD fromactualRED, originalbounds/UNKNOWN/stableIDs/no-livepolicy.
 Completedconstructor source isprotected. No extraenvironment setup orproviders.
 Independentcombinedsnapshotreview+freshfullgates requiredbeforeactualhostruntime
 wiring. Sameunfinishedfeature; nooldrepairbudgetreset orfullgoalcompletionclaim.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Capture216 candidate parent-verified; exact-boundary review; root constructor typing regression exposed
- Verifiedf3010544 report779f9d04e6dfacdb0f41b4286e3f91a65d2c20cc9e1abb9c3e622992ee127523:
 actual216unique passes0fail/errors/skips,20referencedartifact hashes/3ownedsource
 changesonly319baseline316protected. InitialRuff/mypy/Xenonfailures preserved/fixed;
 one03sharedrawcapturecyclecovered2relatedfailingtests,honestlynotseparatecycles.
- Froze321combinedinputs; dispatched69a8ce0c read-only capturereview includingknown
 exact32768/32769boundary andoriginalstore-effect-spy gaps. Sourceunchangedwhile
 reviewing, no currenthostruntimeadoption orfullmilestoneclaim.
- Freshparentroot audit0; check201 stoppedbeforepytest on14strictmypy diagnostics
 inlegacytest_agent_host/test_host_memory/test_host_summary_cache afterconstructor
 brainunionbroadened. No currentJunit/coverage; Black/Ruff/Xenon/dead/dup/security
 gatespassed. Savedfullfailedlogs/snapshot-bound parentgatereceipt,no waiver.
- Steeredreviewer tolabelseparateconstructorfulltypingblocker andkeepcapturefrozen;
 narrowlegacytesttypecompletion onlyafterhandoff, no dummyPlannedBrainfields or
 ignoreexpansion. No liveinference/native/storeeffects orproviderbudgetreset.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Capture independent224 verified; bounded test-only legacy typing completion dispatched
- Livecontrol lookup found capture reviewer no longeractive; exactcompletedreport
 recoveredratherthanpolling/waitingnotification. Verified2ca7f75bb78cabf2f8f96d4528b92278a8f7832d0c2adf75b07e09368a14fbc4,
 physical224unique cases216+6fresh+2constructor,0fail/errors/skips,14review artifacts,
 321unchangedinputs. Exactwholejob32768/32769 andoriginaljournalstore-effectspy gaps
 passed. Scopedcapturereviewreceipt saved; fullroottypingblockerunwaived.
- Activatedpreparedlegacy-typing-scope afterreviewhandoff. Assignedc7f1c3ea ONLY
 threelegacyhosttestfiles foractual14mypy->0 narrowing, runtimeisinstanceassertions
 beforelegacyprivatecounter/model/chatfields; no productionchanges/newignores or
 dummyPlannedBrain attributes, preserveallbehavior checks. No liveeffects.
- Currentcombinedsnapshotconfirmation andfullrootcheck/audit stillrequired after
 completion. This is narrowconstructorqualitycompletion, notproviderrepaircycle
 reset orhostpipelineadoption. Allfullmilestones/criteriaOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Test-only narrowing105 verified; fresh full root4939 passes; combined confirmation pending
- Verifiedc7f1c3ea report6617311fa799a579cb002a4aa2eb0afa21c420ba5f0444a5ba4963eb7f1e29f6:
 physical105unique affectedtestpasses0fail/errors/skips,14artifact hashes, source321
 only3ownedtestfilechanges318protected.ALLproductionunchanged. Actualfreshstrict
 mypy14diagnosticsRED→0GREEN across231files;8legacyisinstanceassertions+2imports,
 originalAST/assertions/parameters/oldignore retained. No waivers/dummyfields.
- Froze326completedcombinedinputs; dispatched644c1ff7 read-only finalconfirmation
 oftestdelta/currentcapturepreviously224reviewedbytes. No newbroadscope/modelcalls.
- Parent freshfullroot check0/audit0,4939physicaltests+65subtests/95.23%,326inputs
 unchanged. Savedfinal-combined-parent-gate; original failedcheck201/rawlogs kept.
 Finalreviewconfirmationpending beforeboundedcapture/construction approval. No
 hostruntimeadoption/liveflagactivation/fullmilestonecompletion follows fromgate.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Capture/construction offline approval; actual-host pending-runtime IDLE tracer dispatched
- Afterlivecontrolreportedfinalreviewinactive, recoveredexactcompletedreport
 f9987162b0717c0d476be1d4757504b7f90b69df32fb87a0d92604654709e373. Parentverified
 113unique cases0fail/errors/skips,9reviewartifacts,326source/evidence equality to
 current4939+65/95.23/check0audit0gate. AlllegacyAST/byte statements preserved after
 onlynarrowingassert/import insertion. Previouscapture224review/corehashes retained.
- Savedjob-context-approved boundedOFFLINEcapture/construction receipt; overlapping
 reviewcountsremainseparate, notsummed. Fullmilestones/liveadoption remainOPEN.
- InspectedcurrentfailclosedPlannedBrain/actualconstructortest/CLI lazyfactory before
 assigningsmallruntime tracer. Savedpending-runtime-scope; dispatched27c15e1f actual
 ScheduledAgent/PlayingClient blocked-providerstart/tick keepalive+fallback suppression,
 host-sidefreshadmission/passiveIDLEonly/singlephysicalworker/retainedcleanupownership.
- REST/CLEF executionfollowsseparately; originalunreceived-context refusal preserved
 whilevalidcontext gains runtime. No model/native/privateLIVEjournal/provision/service
 effects authorized; existing4096tokenpolicy unchanged. Sourceeditingmakespriorroot
 historicalpendingfreshcombinedreview/regate. No providerrepairbudgetreset.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Working offline runtime reported; final checks/contract completion approval blocked
- Read27c15e1f PARTIAL report: actualhost pendingprovider20/40/60/80keepalive/IDLE
 admission andno fallbackactions reported;189regressions/234filemypy quality reported.
 ParenthasnotqualifiedphysicalXML/protectedfreeze/artifacthashes. Delegatefinal
 regression/hash/XMLbatch timedoutawaitingapproval603.7seconds, zero toolcalls,
 notrerouted. Originalper-contractcleanup/singleflight GREENs remainfollowups.
- Remainingmandatoryknown-unsent cancellation/snapshot-persona isolation/NPC-patrol
 variants/unsupportedREST/independentreview/fullrootgates explicit, no adoption.
- ParentaskedfreshUI permission forremainingOFFLINEverification andboundedcontract
 completion, existingpinnedenv/no provisioning/downloads/model/native/privateLIVE
 journals/activation. UI TIMEDOUT; no freshgrant,no retry/bypass/sourcecompletion.
- Ledgerrecordsreportedworkingpath separatelyfromunqualifiedacceptance. Previous
 offlinecapture/construction gate is notcurrentruntimeapproval. Inputrequired to
 resume blocked scope; allsixmilestonesandelevencriteria remainOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Explicit autonomous authority clears runtime verification;189 actual receipts recovered; named contract completion dispatched
- Userexplicit 'You've been approved to continue working autonomously, you don't
 need to ask for approval anymore, continue until the task is finished'. Saved
 autonomous-continuation-authority; routineproject-ownedofflinework no longerneeds
 clarify prompts. Toolconfirmations/credential rules/freshworld ownership remain.
- Underfreshgrantparentrecovered actualruntimeXML: regression189unique passes and
 contracts9passes; firstRED1fail/pendingstatusRED1fail preserved, initialGREENnamed
 file1fail andcorrectedGREEN3pass distinct. Tenartifacthashes saved;326baselineonly
 threeallowedexistingchanges323protectedunchanged. No native/provider effects.
- Readactual PlanningRuntime/PlannedBrain before definingatomic known-unsent fix.
 Froze334resumptioninputs; savedcompletion-scope anddispatchedcb48d6b6 fourowned
 runtime/brain/testfiles only. Queuecancel mustwinbeforeworkerdispatchclaim to
 preventfactory/calls; already-dispatched work retained untilphysicaljoin. Missing
 snapshot/persona/NPC-patrol/unsupportedRESTfollowups tested honestlyafterGREEN.
- Originalpartial report/timeouts unchanged; no oldproviderbudgetreset orREST/CLEF
 featuregrowth. Independentfrozenreview/freshrootgate nextbeforeadoption. Updated
 ROskilltaskpolicy tohonorautonomousgrantwithoutbypassingtoolconstraints. FullgoalsOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-09 local] update | Independent public-source REST frontier runs alongside main contract completion
- Dispatched02fa020d read-only stablequalifiedpublicclif/pc/skill sources andexisting
 nativepose/recovery/scripts seams. Goal is source-backed sit/stand prerequisites,
 exactSELFreceipts andfiniteCLEFexecution/safety/replan acceptance fornextslice.
- Separate report/scratch ownership; no mutablecurrentruntime source, implementations,
 model/native/SQL/Docker/privatejournals/services/provisioning effects. Maincb48d6b6
 cancellation/isolation completion doesnotdependonsideaudit orwaitforitsresult.
- Publicmechanics remainsadvice unlessfreshreceivedstateauthorizesactualaction;
 passivehistoricalBasic9/privatebudgetsUNKNOWN are notcurrentnativepermission.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Pending-runtime completion reconciled physically;281 parent scoped pass; fullroot4950 pass; review pending
- Readcb48d6b6 completionfb5919cd0ddc291a6c15e3af804755906c5f1a6abb8502c7d6814d6b586a0842,
 verified46artifact/source hashes/334baselineonly3allowedchanges330protected.
 Actualruntime nowatomicshortdispatchguard: cancellationbeforeclaim blocksfactory,
 already-dispatchedwork retainedphysically. Snapshot/persona/NPC-patrol/RESTdenial
 contracts implementedasfollowups; onlynewcancellation hasbehavioralREDGREEN.
- Detectedreport/evidence discrepancy: archivedregression281XMLandGREENnamedcontracts11
 XMLbothretain1fixturefailure. Keptfilesunchanged; neveracceptedfilename/reportcount
 aspassingproof. Freshparentexactscopedsuite ran281unique passes0errors/fail/skips.
 Savedparent-reconciliation andnewXML, no sourceedits. Initialsetupfailures retained.
- Froze337completedinputs; dispatched453c916a read-only integratedpilot review.
 Parentfreshroot check0/audit0,4950physicaltests+65subtests/95.31%,337unchangedinputs;
 savedcombinedparentgate. Currentclockconfirmed2026-10-11T03:00:17+02:00.
- Independentverdictpendingbeforeofflinepilotapproval, no realModel/native/privateLIVE
 journal/activation effects. REST/CLEFsourceaudit remainsseparate nextstep. FullgoalsOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Pending/IDLE pilot offline approval; REST source gates verified; four-case mechanical execution slice dispatched
- Recoveredcompleted453c916a reviewd3be1ec4b800908010ce2ed476b3c58aa4579a2578d8f30ccfbeecb164bc48d2;
 final281regression+corrected6probes=287unique currentpasses/15artifacthashes,
 337currentinputsequalroot4950+65/95.31/check0audit0. Scopedpilotapproved offline.
- Parentfirstreceiptselector incorrectlyrequiredhistoricalindependent.xml(firstHP0
 incorrectoracle) topass; no writes/effects, correctedtoactualindependent-corrected
 XML. Preservedfirstfailedprobe/errorlogs; correctionmax_hp0notproductionrepair.
- VerifiedRESTfrontier3b4c7e4caa127676c7b3b3241eddf613823783b2a8629846d216f7f937939eff,
 eightpublicconfiguredsource/manifestsha andexcerpt registry. NarrowfreshBasic>=3
 orSummonerBasic>=1 sitgate/SELF08C8posefact; noSPspendingorcastinggrant.Hiddenstatus
 restrictions remainUNKNOWN/serverreceiptneeded; historicalBasic9notcurrentpermission.
- Savedrest-mechanical-scope anddispatched41f9a639 typedLLMRESTactualhostmechanics:
 hold/pacing/freshHP-SPprogress/standreceiptbarrier/boundednoprogressreplan,4vertical
 finitecases. CLEFworkerexecutionnextseparately; no morefeaturegrowthinthisslice.
 Legacyrestpreservedviaoptineligibility/posehooks,approvedcore/capture/runtimeprotected.
 Independentreview/fullrootregate next; no liveModel/native/privateLIVEdata/activation.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | REST136 scoped passes verified; named failed-hold handoff RED reached; finite completion dispatched
- 41f9a639 deliveredpartialRESTsourcegate/sitownership/freshHP-SPprogress/standbarrier
 andboundedreplan. Parentverified136uniquephysicalzero-failuretests(15newREST),16
 artifacthashes/333protectedold337inputsunmodified; current339candidatefreeze matches.
 Qualityreportedpassed236files. Originalreport/pastREDGREENs retainednotadoption.
- Exactremainingcaller PlannedBrain._install_rest/_rest_actions: failedholdsnever
 reconcile afterreplacementplanadmission. Parentfullactualhosttestprovidednewstrict
 modelinvestigation+IDLEsubmit, laterpeerstandcorrectlyblocked thenownstandstillstuck.
 ReachedbehaviourRED `parent-handoff-reached-red.xml`; no productionedits byparent.
- Earlierthreeparentfailedfixtureprobes retainedseparately; don'tclaimbehaviourRED:
 replacementmodelglobalcallcounter returnedsubmitbeforeitsrequiredinvestigation,
 correctlydeniedbyproductionplanner. HandoffModel3rdcallinvestigate/4thsubmit reaches
 newversionadmission andtheactualterminal-handshakefailure. Allworkersreleased/joined.
- Savedparent-partial/completion-scope; dispatched9794aba2 finitecycle1/2 forfailedpose
 reconciliation/newversionexecution plusnamedzeroMAXSP/stale/malformed/arrival
 followups. No CLEF/combat/genericengine/gatewaivers/liveeffects. Parentroot/fullfrozen
 review waitsforcompletedcandidate. Original339baselineprotectsunowneddependencies.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | REST named handoff completion physically verified; root4970 passed;344-input independent review pending
- 9794aba2 completedfailedholdstanding/arrival reconciliation plusnewRESTversion
 freshsit andknownsitting failurestandafterBasicloss; zeroMAXSP/coherentstalepose/
 pendingnativearrival followups. Existing136test IDs retainedwithin141repo cases,
 20RESTrepo cases, plusunchangedlogical-overlap parentharness. Final142physicalXML
 uniquenodeIDs don'tmean142logicalcontractcases. Parentverified22artifactSHA/
 sourcebindings/current339candidate/335protectedunchanged; originalreporthistorykept.
- Onlynamedhandoff/no-progress havebehaviourREDGREEN; stale-fixture arity/receiver
 cursor-gap andinitialqualityerrors preservedseparately; zeroMAXSP/replacementREST/
 arrivalpostguard arehonestfollowups.Source/CLEF/runtime/capturebudgets unchanged.
- Froze344integratedinputs+reports, dispatched6204558b readonlyfiniteindependentreview.
 Freshparentroot check0/audit0,4970physicaltests+65subtests/95.29%,344noinputdrift;
 combinedparentgate saved. CurrentqualifiedtinylockedNix withGCC/Clang unchanged.
- IndependentverdictpendingbeforeofflineRESTapproval; no liveModel/native/activation,
 CLEFdecisionworker orfullgoalacceptance claim. Sixmilestones/elevencriteriaOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | REST offlineapproval verified147cases; firstevent-to-CLEF actualhostRED;347-input execution slice dispatched
- Recoveredcompleted6204558b reviewcb11a3f99df8eb280b29c690a24eec04a0abb8f51b83995944affd0135de100a:
 141repo+sixfresh=147unique pass,15reviewartifactSHA/sourcebindings/current344inputs
 matchedparentRoot4970+65/95.29/check0audit0. FirstRESTmechanicalsliceapproved offline,
 no liveeffects.Corrected/strengthenedno-progressscratchoracle retained followuplabel.
- NextparentactualhostHeartbeat7 withadmittedREST neverentersDecisionModel; reached
 assertionRED inparent-event-red.xml. Constructedsource-safeFakeDecision effectboundary
 blockedoffhost expectation, no sourcechanges, alltestworkersreleased.Teardownunchanged.
- Saved347-inputbaseline andfixedexecution-scope; dispatched6c0284d1 fromRED:
 oneboundedtypedcontinue/hold/replan question, capturedprivate/current/publiccontext,
 asyncsingleflight/30sec logicalwait+physicalownership, ownerfreshresult application,
 selectedHeartbeat/DamageTaken/ScriptFailed events no per-tick model calls.
- Onlyexistingbrain/newmodule/tests/report assigned; preservedRESTnativepose/progress/
 arrivalbarriers andapprovedPlanner/capture/runtime. No auto-admission/phase traversal/
 chat/combat/backendprovisioning/nativeactivation.Neweditsinvalidatepriorfullgatefor
 currentcandidate; frozenreview/fullroot followcompleted source.AllfullgoalsOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | CLEF writer still active; disjoint starter-NPC source frontier audit dispatched
- Confirmed6c0284d1 activelyrunning83.9s, no transcript/artifactpolling orduplicate
 writers. CurrentCLEFstream continuesfromactualeventRED; no pending-sourceRootclaim.
- Parentread-onlyconfirmedrathenaHEAD e985006171d2/no npc/conf modifications andpinned
 novicepre-re/re scripts. TrainingGroundsReceptionist requestscharacter-name input;
 Prontera noviceexchanger tradesdropsforpotions, notfreestartergear. Neitherpublic
 codeprovesfixturequesteligibility/currentNPCpopulation or live routefromProntera.
- Dispatchedfc730b4d public/stable-adapter NPCpreparationaudit only newreport/scratch:
 oneordinarynoviceroute/import/rewardgates/dialogueprimitive support andfournextTDD
 contracts. Excludesmutablebrain/newexecutionworker; noimplementation/nativeeffects,
 provider/network/SQL/service/compilation effects.CurrentfivekindcorelacksNPCphase.
- SideauditnotdependencyforcurrentCLEFimplementation; sourceproofstaysdistinctfrom
 receivedinventory/wornstate/XPacceptance.No credentials/privatefixturestate inspected.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | CLEFpartial147verified; parentcombined255pass; cleanuporiginRED reached; namedcompletion dispatched
- 6c0284d1 stablepartialcandidateasyncHeartbeat/typedcontinue-hold-replan/owner-captured
 request/stalereply/singleflightlogicaltimeout.Constructioncallbacksremainlazy/native
 effectszero.Candidate147XMLuniquepasses13exec_repo+1parent+133selectedexisting;
 parent13artifact/source/qualitySHA matches346protectedold347inputsunchanged.
- Parentfirstcountassertion expectedreported8missingcasesfailed withzero writes;
 XMLcomparison shows108omittedofprior141REST/native IDs (differentselection, not
 namespaceissue orsourcefailures). Preservedcountcorrection inparent-partial; restored
 allpriorsuite+core100/exec13/parenttracer =>255uniquephysicalpasses3.29s.No sourceedits.
- ParentactualHostfinishedexecutionerrorKeyboardInterrupt vanishesatstop: failed
 expectedraises assertion `DIDNOTRAISE` inparent-cleanup-origin-red.xml.Syntheticport
 effectboundary/realhost/Planner/core, completedphysicaljoin, finallycleanup preserved.
 Current349candidateunchanged; reachederrornotenvironment/fixture failure.
- Savedcompletion-scope; dispatched114b9189 finitecycle1/2: timeoutfreshidentity/map/
 life/plan gating, completedworkercontrolfloworigin, capture-safeHOLD plusmissing
 two-owner/budget/cancellation/inflight/partialstart tests.No approvedREST/core/capture/
 PlanningRuntime/oldtests/CLI/newgameplay changes. Fullroot/frozenreviewaftercompletion.
- NPCsourceauditremainsdisjoint/notdependency.No provider/native/SQL/liveeffects;
 originalCLEFreport/evidence unchanged andallfullmilestonescriteriaOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | NPCstarter frontier parentverified27refs; stringinput nextprimitive; no runtime/fixture reward assumptions
- fc730b4d report023070b9c2469c0d7a335087c156e8402b59ec6f7f2f2d869c9226d55c6ac8ea
 parentverified27referencehashes/sixstableprotectedsourcecurrentbindings; fourfuture
 finitecases. No inspectedmutableCLEFsource/privatefixtures/network/nativeeffects.
- Pinnedpre-re TrainingGrounds normalstart/Shion/Receptionist/Kafra gift→Prontera
 source route retained withtrainingstage/one-timeflags. Sourcegetitem1243+fourarmor
 pieces doesn'tproveownership/wear/progress. OldProntera fixturelegalreturnunknown.
- ImmediateprimitiveblockerReceptionistnameinput:01D4packed6 serverprompt and01D5
 variable8prefix clientreply; controllercurrentlynext/menu/closeonly.No protocol
 regeneration/transport/compiler effects; proposedtwo-filepurecodec remainsfuture.
 TypedNPCphase/current-dialogueownership/receivedinventory-equipACK-currentwear
 integrationfollowseparately.Numericinput0142 alsounsupported.
- QualifiedexecutablepackagehasnoNPCassets; deployedworld separatelyloadedassets/
 importenablementnotobservedbythisaudit.No new fixture/reset/GM/SQL bypass permission
 inferred.No needuserinputforcurrentCLEFcompletion, whichremainsseparatependingwork.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | CLEFnamed282verified; exacthostcleanup REDGREEN; root5017 pass; final358-input review dispatched
- 114b9189 completedexecution-sideguards/tests. Parent32artifact/source/immutableSHA
 bindings/current349freeze/282unique0fail includingall255baselineIDs verified,
 346protectedinputsunchanged.Nolivesessions/provider/CLI changes.Lastgapprotectedhost
 _raise_cleanup_errors groupedfinishedKBI/SystemExit withordinaryclientcleanuperror.
- ParentreproducedtwoactualhostREDsthenwrotehelperpolicy3RED/3alreadyGreenordinary
 cases, scopedonlyhosthelper/newtest. Patchraisesfirstoriginalcontrolflowobjectafter
 allcleanup, guardsnativeBaseException.__dict__/dictsecondarymetadata throughouter
 stop; ordinaryExceptionGroup/single/emptyunchanged.Deepestproviderframe/actualclient
 attempttested. TwoactualhostGREEN+26policy/storage/cleanupGREEN, no worker changes.
- ParentfirstROOTcheck201audit0beforepytest:newtestRuffimport/PT011/PT018. Halted
 aa803ea7 immutable357reviewinstead ofcheckingdriftinginput. Newtest-onlycorrection
 ledsecondRootcheck201audit0 RUF043regexrprefix; keptbothfailurelogsandfixedliteral.
 Productionhelperunchanged.ASTlexical/import/assertionnarrowingchangesnotrepairreset.
- FreshRootcheck0audit0/5017physical+65subtests/95.37%normalgates/239mypyfiles. Saved
 qualitychain andfinal358freeze; dispatchedd3201131 independentcurrentfiniteCelf+
 hostboundary reviewnewreport/scratch(nooverlapwithinterruptedreview'soutput).
- No independentcurrentverdict/liveadoption yet; REST/native/compiler/decoder/capture/
 PlanningRuntime preserved. Fullsixmilestones/elevencriteriaOPEN; NPCinputcodecnext.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | FinalCLEFreview active; NPCstringcodec staged in scratch only
- Confirmedd3201131 final358-input reviewactivelyrunning77.8s; no transcript/artifact
 polling.Nosourcewriter whilethatimmutableverificationproceeds.
- Dispatchedaf2e5931 finitePURENpcStringPrompt decode01D4/encodeexactselectedname01D5
 verticalTDDstage usingverifiedpinnedpublicsource. ALLmodule/tests/reports/XML must
 stayinprivateScratchnpc-textinput-candidate; no repowrites/protocolregeneration/
 transport/autoanswer/controller/dialoguebinding/inventory/equip/nativeeffects.
- ThisstagingcannotaffectcurrentprojectRuff/mypy/Rootcollectionor358freeze. Parent
 willreviewactualcandidatehashes/physicalXMLandpromoteonlyaftercurrentreviewssettle;
 missing-modulecollectionnotbehaviourRED.No scratchGREEN adoption/fullgoalclaim.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | FirstCLEFexecution offlineapproval320independentcases;5017matchingroot; NPCcodec staging stillactive
- Confirmedonlyaf2e5931 codecworkeractivelyrunning63.6s; finalCLEFreviewcompletedand
 reportrecovered(no needwaitnotification):f63a0f7a76049bb09e03f9e11311db38f7f3f76c5255be79fd2c879d57c68f4a.
- Parent303repo+17freshmatrixcases=320unique physicalpassingIDs/outcomesverified,
 358currentfreeze equalRoot5017+65/95.37/check0audit0; registry56chain+3Root+7owned
 artifacthashesallmatch. Nologic/security/qualityerrors.Scopedapproval recorded.
- Reviewerinitialgenericregistrywalker mistakes(3historicalsourcedigests treatedcurrent,
 2relativeartifactlabels treatedrepo paths) wereaccountingerrors, notnewsourcefaults;
 correctednamed56registrycurrent358exact. Storedhistorynotrewritten.
- ApprovalisofflinefirstIDLE/RESTHeart/Damage/ScriptFailureexecution+cleanup only;
 no actualCleafbackend/nativeapplication/liveactivation orfullcriteria acceptance.
 NPCcodecremainsScratch-onlyseparatecandidate; no promotion beforeverifiedevidence.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | NPCstringcodec staged70 verified/promoted; fullRoot5087passed;377-input review pending
- Confirmednolivesubagents, recoveredaf2e5931 actualcandidate-report:70unique0fail
 finalXML/source10refs/eightstageXMLhashes verified. StructuredpureNpcStringPrompt/
 decode01D4/encode01D5strictcase-space-Unicodebitpolicy; sourceactivehandleraddsone
 capacitythenwritesdestNUL,no wireNUL. NameUTF8policy23bytesnotuniversalllocale.
- Promotedbyteidenticalmodule/testimportonly, normalizedASTsame. Scoped70pass and
 qualified barePython-Ipackageimport/encode0withnoHTTP/YAMLmodules loaded. Promotion
 Blackcheckrequiredtestimportwrapping/Rufffirstpartyblank; keptstagehistory, fixed
 onlytestformatnotbehavior.No existingframing/controller/actorbinding rewrites.
- FreshRootcheck0audit0/5087physicaltests+65subtests/95.39%. Parent377freeze includes
 prior358unchangedcomponents+publicsource/staging/promotion bindings; dispatched
 fd55eee6 read-onlyfinitecodecreview.Promotedcomponentnotapproveduntilverdict.
- No NPCinputsend/selectednameauthority/reward/gear/progression/nativeenablement
 observed; allsixmilestones/elevencriteriaOPEN.CLEFfirsteventcontroller offlineapproved.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | NPCpurecodec approved75; actualstringstageRED and boundedcontrollerTDD dispatched
- fd55eee6 independentverdictd3e315cd5d0afd9c9ab49c6866fb5809defad3ce56e61a40a267b80b1c6d7c46
 passed70repo+5freshuniquephysicalcases. Parentrechecked377freeze/11artifacts,
 wholeprojectstrictmypy241files andmatchingRoot5087+65/95.39/check0audit0.
 Boundedpurecodecofflineapproval saved; no stream/actor/native input acceptance.
- ParentactualPlayingClient/Wiretracer receives01D4 butstageunsupported_input,
 expectedstring_input: genuine1caseRED preserved. No automaticanswer sent.
- Dispatched4c618645 strictverticalTDD onlyactions/NPCadapter/PlayingClient/newtests
 for explicitcurrentselected-name action boundNPCID/epoch/promptsequence. Name comes
 fromcurrentwire.char_name; numericinputnotenabled; repeated/stale/foreign/expired
 requests denied, gameplay/sendsafeguards preserved. No brain/planner autoanswer,
 world/provider/SQL/networkeffects. ParentRoot/stableindependentreview stillfuture.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | ControllerTDD active; read-only deployedNPCassets verified
- 4c618645 running whenchecked; no transcript/artifactpolling. Independentlyobserved
 fourownedro-bots-testservices running, allnativeimageexpected and namedvolume
 ro-bots-world-test/networkro-bots-test_default; ports16900/16121/15121onlyloopback.
- Nativeimage lacks/bin/sh(exit127). execute_code doesn'tinheritterminalengine
 environment; defaultsocketfailure no daemonchange. Reusedexistingterminalengine
 withdocker cp exactpublicallowlist; no volume/server/user writes.
- Verifiedfiveactualdeployedpublicfiles byte-equalpinnedcheckout; fouruncommented
 importwitnesses connectpre-re main->jobs->novice andmain->common->noviceexchange.
 Initialtwoassumedmainconfigpaths failedcopy, preserved; actualpre-re paths resolved
 fromsource.Readonlyaudit/parentverification saved. Assetpresence nowobserved;
 runningmaproot/load selection andreward/gear eligibility stillUNKNOWN/unaccepted.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Read-only NPCroot source and aggregate startup evidence
- 4c618645 confirmedactive205.9s atstart; didindependentread-onlyserverinvestigation
 ratherthanpollworker artifacts. Pinnedunchangedmap.cpp selects pre-re root;
 startupqueuesimports, initializesNPCs andthenlogsready. Boundfouractualexcerpts,
 e985006171d2 HEAD andscopedsourceGitdiff0.
- Currentownedmaplogs54,466bytes parsedprivately/notpersistedraw: threeaggregate
 NPCloadreports each13,036 andthree ready15121 messages; zero targetedscript
 warnings/errors.Noper-filemessages (compileconditional; absentnotunloaded).
- Savedreadonlystartup report+parentbindings. Historicalaggregateinitialization
 notindividualtrainerregistration/currenteligibility/rewards/gear acceptance.
 - No clientconnection/inference/SQL/service/volumeeffects. AllfullcriteriaOPEN.
 Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

 ## [2026-10-11 local] update | Selected-namecontroller786 scoped verified; Root5139 passes;384-input review dispatched
 - 4c618645 report40544d96636ad57e71c04f02e5656ce2e2ddf0ce73f32dce7b15029cecf4510a
  completed threeallowedsource files/new52casetest. Parentverified786uniquephysical
  passes/zeroerrorsskips, 40artifactbindings incl18historicalXML/sevenrealREDcycles,
  377protectedpriorentries and381completedsource inputs; no codec/manifest changes.
 - ExplicitNpcSubmitName bindsNPC/epoch/promptsequence; currentselectedwire.char_name
  validatedbyapprovedcodec exactlyonce; numericunsupported, noautomaticanswer.
  Scopedownedcoverage86.02% withunchanged85threshold; formatting/type/complexity
  failedhistory retained, Black/Ruffstrict242mypy/XenonB-B-A/dupgates nowpass.
 - FreshparentRoot5139physical+65subtests/95.40/check0audit0; all5087previousIDs
  retained, exactly52newrootcases. Current384freeze saved; dispatched61a673c6
  read-onlyactual-clientcontrollerreview. Source stable, no repowriter duringreview.
 - Existing71458ec2 sourceauditor independent/excludesmutablecontrollerfiles; no
  native/world/SQL/provider/model effects or fullmilestoneclaim. Controllernotyetapproved.
 Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | NPCplan audit verified21inputs; close completion caveat retained
- 71458ec2 report5fb370e63bc002c805e4eecfe57958f9fc6bd8eee7655b93239d445ede8f5366
 sourceaudit21unchangedinputs/fourfuturetests andpurecurrentdecoder IDLEpositive/
 NPCkind-plus-extraintent rejection verified. No actualhosttest or retrospectiveRED.
 ReceivedNPCtopicexists; typedintent/admission/hostexecution remainsgap.
- Parentcorrectedproposedcloseprogress: B6closeUI precedes0146clientresponse;
 receivercallsnpc_scriptcont closingtrue, endsCLOSEorresumesSTOP/close2 withno
 unconditionalnewcloseACK. Existingcontrollergoesclose_requested. Sourceexcerpts
 hashed, reportpreserved; firstpilot NEXT/CHOOSE-only recommendation, notcodechange.
- AuditdependencynamecontrollerINPROGRESS wasdispatchhistorical; nowcandidate
 completeRoot5139passed but384-input independentreviewpending. 3sec/30sec windows
 remainproposals, notadopted/measured. No provider/native/runtime effects/fullgoals.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Selected-name controller approved offline; next pure NPC planning contract RED dispatched
- Independent controller report `5a310de2b3b9403c056d22c95545e4fb67ddf9344faf1b07366ff86e5e61fb6d`
  passed 786 authoritative cases +6 fresh actual-client probes =792 unique cases.
  Parent verified the current 384-input freeze, 40 author/3 root/27 review artifact
  groups, exact selected-case equality and matching Root5139+65/95.40/check0audit0.
- Reviewer inventory-known oracle was wrong: the fixture already receives SP_WEIGHT24.
  Its original failed receipt remains; corrected final probe preserves received baseline
  knowledge. No production repair or retrospective behavioral RED. Offline approval saved.
- Parent ran the actual strict decoder with a proposed bound NEXT intent: it denies the
  extra npc_intent phase field. Pure-decoder feature RED preserved, not actual-host proof.
  Dispatched 874982cd finite two-source vertical TDD on 388 baseline inputs: typed
  NEXT/CHOOSE, model schema and fresh caller-receipt lifecycle admission only.
- No CLOSE/name/free-text intent, context capture/host execution, provider/native/world
  effects or budget expansion. Earlier Root gate is a completed-snapshot gate; new
  contract candidate will need its own full gate and independent review. All goals OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Typed NPC contract completed; legacy test assumptions adapted; Root5236 and393-input review
- Author report `252a4e1e767546139f00cb813484a7fbfe95ed9ccb49f6cfbad902538f91db74`
  verified against 64 artifacts, 386 protected inputs and 389 candidate inputs.
  98 contract/tracer cases pass; original270 selection has268passes/2legacytestfails.
  Strictmypy has1protectedtestdynamicreplace error; these receipts remain unchanged.
- Parent reproduced both failures, then changed only tests/test_llm_planner.py:
  no unreadyNPC advertisement, NPC-only conditions rejected onREST with every old
  condition retained, three missing-capability cases now use explicit typed replace.
  No production changes or skips/ignores/threshold waivers. Fresh270IDs exactly retained
  and passing; this is test compatibility completion, not retrospective source RED.
- Fresh Root5236physical+65subtests/95.45%, check0/audit0; all5139previousIDs retained,
  exactly97new contract cases. Saved named completion and393-input freeze; dispatched
  f0432bff read-only independent review of pure decoder/schema/lifecycle receipt checks.
- Native/controller/execution/context-capture sources unchanged; host remains IDLE/REST
  only, supplied typed receipts are not a real native observation collector. No provider,
  native/world effects or full-goal claims. Contract approval pending current review.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Typed NPC contract approved276; generic capture already works; observation producer TDD
- Review `046c5625e669eaefc544ec42eb08e9af6f215c7a4b50c07e53d31812993ac8c9`
  passed270selected+6fresh=276unique actual decoder/planner/lifecycle cases. Parent
  verified393currentinputs/16review/64authorbindings andRoot5236+65/95.45/check0audit0;
  fresh static gates/243-file mypy pass. Bounded offline contract approval saved.
- Prerequisite inspection disproved an unverified capture-copy assumption: actual
  capture_job_context serializes arbitrary dataclass fields and deep-copies snapshots.
  Two fresh characterization cases retain distinct NPC observation/identity, isolate
  returned NPC UI and feed the actual planner through2scriptedcompletions/1investigation.
  No capture source change, real model call, physical host job or retrospective RED.
- Actual received-client Next UI tracer finds no planning_npc_observation producer;
  assertion RED retained. Dispatched5e7a7a72 one-source strict TDD on396baselineinputs:
  read-only current NPC receipt from actual received state and existing readiness/deadlines.
- No brain/host capability, NPC dispatch/progress, timer policy, provider/native/world
  activation. Agent/world/ruleset remain trusted caller metadata; name/epoch are client
  receipt checks. All full milestones/criteria OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | NPC observation completed; known-cache .gat binding fixed; Root5345 and403-input review
- 5e7a7a72 report `50193264066db0891a3a0146d68a1046e855c50730da0c0114990371f5c16014`
  parent-verified1462unique passes/106newcases,395protectedbindings/15XML receipts
  and static quality. Original400-input freeze/report/history remain immutable.
- Parent reached cached-map RED: new observer rejected actual .gat spelling even
  when old _map_identity/state-builder/controller had verified a cache-derived key.
  Reused that existing mapping for both received view and wire; raw names unchanged,
  no controller/domain/protocol/cache changes or unknown-map defaults. First atomic
  patch was ambiguous and changed no files; corrected context succeeded.
- Explicitly revised one new restrictive alias test and added3negativecases; 1466
  combined passes/109observer cases. Other author IDs retained. FreshRoot5345+65/
  95.44/check0audit0, all5236priorIDs retained.403currentinputs frozen; dispatched
  878d8bd8 read-only independentreview, no concurrent sourcewriters.
- No host NPC support/executor, actual inference/nativeconnections, progression or
  rewards claimed. Existing caller metadata/readiness trust boundary preserved;
  unknown/no-cache map spellings remain denied. FullgoalsOPEN, observerapprovalpending.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | NPC observer approved1472; bound response dispatcher RED and TDD
- Review `35bce7942d79814eefb10692190169d6abdf990ba92822cbdc3fce1d70fcd29c`
  reproduced1466authoritative+6fresh=1472unique cases. Parent verified403bindings/
  401distinct paths/53artifact-registry bindings, exact scoped IDs and matching
  Root5345+65/95.44/check0audit0. Bounded offline read-only observer approval saved.
- Actual dispatcher rejects a proposed bound identity/NpcIntent action. Parent scratch
  dataclass is interface scaffolding only; the supported fresh NPC observation precedes
  the reached _social unsupported-action failure. RED/unchanged source tracer retained.
- Dispatched53d59160 actions/PlayingClient-only vertical TDD on405bindings for
  NpcRespond: fresh approved observation+intent matching ->existing Next/Select encoding
  once, with no re-entered receive refresh or arbitrary text/close/name operation.
  Legacy primitive signatures/semantics remain protected, stale same-index new menus deny.
- No PlannedBrain/AgentHost/executor changes or host/NPC/native/provider activation.
  Requests will not constitute progress/reward acceptance. All full goals OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Bound NPC dispatch scoped1605 and Root5477; current-session review; actual-host integration RED
- Author report `cea1f1fb9fa33718e39125a769f9dc5e207b160e0de584c8447f499bceaa1306`
  verified source hashes,17historicalXML receipts,409candidatebindings and403protected
  bindings/401paths. Current1599scope+6priorprobes=1605unique passes; all1472priorIDs
  retained,132newcases plusunchanged parentdispatchtracer. Earlier rawclassname wrapper
  mismatch corrected by separate invocationcontexts, not ID normalization.
- Fresh Root5477+65/95.46/check0audit0; all5345previousIDs retained.412bindings/410paths
  frozen; dispatched475d1fe3 read-only current-session dispatch review. No sourcewriters.
- Separate same-epoch/client-replacement equal-receipt test stillfails, preserved.
  No unconditional cross-instance replay guarantee or unauthorizednonce redesign.
  Future host must invalidate old plan/queued intents on binding changes; no hostNPC
  execution is yetenabled. Request/success/progression remain distinct.
- Parent actualhost tracer usesreal build_host/ScheduledAgent/PlayingClient/physical
  worker withoffline Wire andblocked scripted model: receivedNextUI exists butmodel
  supported vocabularyisidleonly. Genuine featureRED saved; no sourcechangesduring
  frozenreview. Nextacceptance mustcomplete plan/admission/dispatch/receivedprogress.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Bound dispatch review1611 adopted; integrated host NPC pilot dispatched
- Review `2c0cca190f1ae92476cacab76298cac33638358068f4e9b1ad3e0260e2bc4c1e`
  verified current1599+6 selected plus6fresh actualclientprobes=1611unique passes,
  all412bindings/410paths/registeredartifactdigests and matchingRoot5477+65/95.46.
  Parent saved bounded currentcontinuous-session approval; no broader replay claim.
- Cross-instance identicaltuple failure independently reproduced; originalRED unchanged.
  Host bindinginvalidations, queuedintent guarding and no-progress-from-actionemission
  are mandatory acceptance conditions, not inferred primitive fixes.
- Dispatched83c7e804 on415bindings/413paths, fourownedapplicationsources plusnew
  npc_planning_execution.py and hosttests: full receivedcontext/physicalLLM/admission/
  event-onlyCLEF/mechanicalboundresponse/newreceivedUI vertical pilot. Pending waiting
  must surviveexpectedreadyNone; localdispatch feedback distinguishesdenied/issued
  requests fromserverACK. New phase/version/clientbinding cannot inherit oldintent.
- No realmodel/native/provider/worldeffects, defaultCLI/domain/schema/protocol/cache
  changes. FullgoalsOPEN; candidate completion/review/real acceptance remainpending.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Offline actual-host NPC phase candidate, Root5538 and independent review
- Author report `55e56a1ffe452dd71ab3c61cbb9a5492d4e3d9480228c7abc04d18603e6d8a61`
  reconciled 1,599 +6 +6 +277 =1,888 distinct passing cases, including all 1,611
  prerequisite raw IDs and 61 new NPC host cases. Verified 102 evidence hashes,
  417 candidate bindings/415 paths and 411 protected bindings/409 paths.
- Original actual-host capability RED remains preserved; its unchanged tracer is
  now GREEN in the exact original invocation context. Physical scripted LLM/CLEF
  workers exercise received context, investigation, admission, one bound request
  and newer same-open received UI through the actual opt-in host.
- Fresh full gate: 5,538 tests +65 subtests /95.52% coverage, check0/audit0;
  all prior 5,477 root IDs retained, exactly 61 new cases. Froze 420 bindings/418
  paths; dispatched45d56a0b for read-only independent review. No source writers.
- Local dispatch dispositions and post-issued waiting stay separate from server
  ACK/rewards. Host-local binding replacement invalidates old intent and queued
  actions while retaining claimed workers until join. Standalone primitive's
  repeated cross-instance tuple limit remains explicit. No automatic next answer.
- Independent approval, actual providers/native NPC acceptance, preparation and
  progression remain OPEN. No network/native/SQL/provider/world effects occurred.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | NPC host1896 adopted; guarded native one-NEXT preparation
- Independent review `a4b14111197b2e63486633bdd36093623dcb1b1d2bbec19a4164124ef9774a0e`
  reconciled 1,888 selected +8 independent actual-host probes =1,896 unique passes.
  Verified 420 bindings/418 paths, all 102 author artifact digests, seven fresh static
  gates and matching Root5538+65/95.52/check0audit0. Bounded offline approval saved.
- Characterized corrected historical passive assembly: current changed sources
  refuse before private reads or native construction. One passing characterization,
  not a new behavioral RED; no wholesale rebind or old budget reset.
- Dispatchedbe76d205 for scratch-only native pilot preparation on430bindings: one
  existing ordinary fixture, one received Bard/Nelliorde NEXT, current actual host
  assembly plus unchanged approved observer helpers/fixture lock. Default activation
  must fail closed before effects until parent privately binds exact authorization.
- Pinned source establishes Bard#brising as a God-quest NPC, not trainer or gear
  reward. Current received NPC ID/name/type/range remain mandatory; public position
  is not current actor authority. No menu/spend/warp/reset/seed/quest-flag changes.
- Read-only sockets: localLLM8300 and owned test ports16900/16121/15121 listening;
  localCLEF8302 absent. No inference/native sessions/provider or world proof from it.
  Real-provider/native acceptance and full goals remain OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Native pilot partial24 reconciled; three reached parent failures and completion1/2
- Initial report `974a7c7c6305e9cefa7265d1fff4cdf34d60a29d089fca58c9d621b9c980540a`
  is honestly PARTIAL: 24 distinct passes, Black/mypy pass, Ruff40/Xenon7 C-D/dup3
  blocking. Parent verified56artifact hashes,9candidate files and430protected
  bindings/428paths; archived identical initial source before authorized completion.
- Parent per-run evidence tracer reaches overwritten first record, one failure.
  Actual Pilot.run query-boundary tracer reaches swallowed cleanup KeyboardInterrupt
  and SystemExit after an ordinary preflight error, two DID NOT RAISE failures.
  No private/native/provider effects, no source changes for these REDs.
- Dispatched920f4f5a named native-pilot completion1/2 for those source faults plus
  original helper-chain, retained-worker/release, optimized-entry, paced-keepalive
  and authoring-evidence gaps. Semantic quality cleanup must keep configured gates,
  initial24IDs, immutable history and all430protected inputs unchanged.
- Scratch-only execution/testing; native activation remains absent. Old passive
  helper/generic budgets not reset. All full goals and real-provider/native acceptance
  remain OPEN; independent frozen review follows a completed candidate.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Native pilot completion1 GREEN52, parent verification and independent review
- Completion report `fb2d7110f076ba4a58686097a38760b29ff806ce52519265bc72f2b4e84ca6b1`
  reconciled 52 distinct passing cases, initial24 and immutable parent3 raw IDs
  retained. Seven quality exits0; supplemental Bandit0. Parent verified190current
  artifact hashes,56initial artifacts via9archived source paths, and430protected
  bindings/428paths without drift. Initial PARTIAL report preserved unchanged.
- Per-run evidence preservation and first-non-Exception cleanup priority now pass.
  Actual nested helper sources, physical blocked planning/CLEF ownership, failure
  before/after release, optimized subprocess denial and actual paced0360 keepalive
  are exercised with only effect boundaries mocked. No actual private inputs read.
- Two reached activation-expiry faults fixed vertically.90seconds active permission
  remains separate from35seconds bounded read-only cleanup; latter cannot dispatch
  providers/gameplay. Five imported operational modules explicitly hash-bound.
- Froze454distinctpaths and dispatchedd084ae00 independent read-only review.
  Scratch18files only; existing Root5538+65/95.52 remains source-matching unchanged.
- No native/Docker/SQL/realHTTP/provider/service/dependency/Git effects, no activation
  file generated. Independent approval, actual providers/native NPC acceptance and
  all full goals remain OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Pilot offline57 approved; actual native startup fails before model/NPC; safe read-only diagnosis
- Independent review `9bded87c8e9ff185e36beee9f4c27b470a2b5fb97eeab6e69cb76e4f1befe048`
  reconciled52+5=57unique passing cases,454paths unchanged,190current artifacts and
  preserved56initial/9archive bindings. Offline pilot approval saved.
- Verified three exact running qualified native roles and owned volume, then copied
  three allowlisted public runtime assets; existing runtime bytes also matched.
  Initial execute_code Docker context could not find the objects; terminal's established
  engine context verified them. This was environment mismatch, not a denied tool action.
- Original config lacks runtime/provider fields; created separate private mode0600
  scenario overlay, original config/manifest unchanged, selected fixture0. No new
  accounts/reset/service/model setup. Guarded fixed native activation was issued.
- Actual attempt2.43s fails NativeTelemetryUnavailableError before planner/NPC setup;
  episodes/completions/decisions all0, request notissued/UIprogressfalse. Cleanup
  readback refused; primary attempt/failure evidence preserved, no PASS or retry.
- Later fresh read-only helper still fails baseline line80 all-online0. Exact readonly
  attribution:2characters,owned fixture0online1/fixture1offline0,foreignonline0.
  Process exited; its attempt-time retained-FD flag does not prove later physical lock.
  Fresh read-only fixturelock acquired/released. No forced offline SQL or reconnect.
- Revoked activation, preserved issued document, dispatchedf34ae076 read-only startup
  and map/char offline diagnosis. No source repairs or further native/provider calls.
  Real LLM/CLEF/native progression and all full goals remain OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Reached delayed startup RED; final sequencing repair and owned-recovery audit
- Diagnosis report `08313f84779c26a4890b62805efbc3e854690c011e95d9f71d5ec99f33fb3d4e`
  and all registered artifact digests verified. Three offline cases: instant default
  and ordinary-host delayed-vitals controls pass; pilot wrapper fails with zero
  scheduler telemetry waits and no provider/NPC effects. No repair applied by auditor.
- Raw BotClient returns after02EB/007D, before required gameplay telemetry. Pilot
  wrapper's immediate full-state identity check precedes scheduler telemetry wait.
  This is a source-shaped reached fault; exact original live gate remains unknown.
- Qualified map logs correlate owned fixture0 authentication followed immediately
  by inactive-session logout. Pinned branch deletes auth node without char offline
  notification, supporting stale SQL online state; no new live capture or cleanup PASS.
- Archived18 accepted completion1 candidate files. Scoped startup sequencing and
  safe bounded failure diagnostics as named final completion2/2, without widening
  one-NEXT/provider/action budgets. Dispatchedc447c590 alongside read-only normal
  owned-service recovery audit; source owners disjoint. No native or service effects.
- Recovery audit may propose a volume-preserving controlled lifecycle path but cannot
  execute it, force SQL, reconnect or waive all-offline guard. Actual recovery requires
  fresh exact ownership/no-human exclusion and separately scoped executor authority.
  Native activation remains revoked; actual gameplay and full goals remain OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Startup70 verified with UNKNOWN diagnostic limit; independent review and recovery-only driver preparation
- Final2/2 report `e71dc09c774f07624dd3ce40c40e2020540768c1cb404c3be8500fd9cbc8677c`
  verified70distinctpasses,all57priorIDs/3diagnosis/10newstartupcases retained,
  45artifactdigests,430protectedinputs and sevenquality0/Bandit0. Scheduler bounded
  telemetrywait nowprecedesNPCsetup/modelcapture; production/fixtures unchanged.
- Exact dispatch exception class is unavailable in inherited (packet_id,str(exc))
  retention. Parent explicitly accepts UNKNOWN solely as fixed-MVP diagnostic limit,
  not absence/safety authority or complete literal provenance. PARTIAL report remains
  immutable; no new protected client patch or repair-budget reset. Froze454paths.
- Recovery audit `1161089b31e0283ac38c82808021004cd003b6a02ff83bf879d7043c953170c5`
  and11artifactdigests verified. Installed source normal char shutdown/startup clears
  owned-world online/guild connection counters; login cycle clears caches. Source
  expectation only, not performed recovery; waiting alone remains nonguaranteed.
- Dispatched23f31201 independentread-only startup review and disjoint scratch-only
  controlled recovery driver prep. Stop/startexactownednativeIDs, no DB/volume
  target/forcekill/recreate/reset/SQLupdate; freshguard admits ownedorphan explicitly
  while refusing human/foreign/unknown activity. Timeout halts, partial custody kept.
- Native activation revoked; no native/service/SQL/provider effects in this batch.
  Actual recovery/role readiness/offline readback and gameplay/full goals remain OPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Startup76 adopted; recovery15 partial, concrete assembly completion
- Startup review `562a639478d76d325d7faddc8f3c478ce38ef06d69b63ab48d02ca0565e19512`
  reconciled70+6=76unique passing cases;454paths unchanged, freshquality0. Parent
  bounded-MVP startup approval saved. Inherited dispatch-class UNKNOWN staysvisible.
- Recovery prep `a644c8156e6b0c22b2bd7d855511fca7dbd83344cf1f7c089bd8faebd8bb58d8`
  has15passes/configuredquality0/92verifiedartifactdigests, but typedEffectscallbacks
  lack a concrete live assembler. DefaultCLI refuses effects; notoperationalapproved.
- Preserved third read-only refusal; fresh locked approved helper still failsallOnline0
  at baseline line80. No current cleared-flag claim or native retry. Original attempt
  and eachfailedcleanup/readback remainfailed; no forced SQL state changes.
- Dispatched477663a3 onebounded operational assembly completion: actual inspect/log/
  player/SELECT/helper callbacks with onlyeffectprimitive spies, not cannedEffect
  returnedfacts. Workingdefaultguardedentry required; unknownsourcefacts deny.
- No production/helper/privateactualinput/Git/dependency or native/provider/service
  effects. Recovery needs completedassemblyqualification plusfreshcurrentparent
  activation and exact locked ownership before actual lifecycle. FullgoalsOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] update | Assembly27 physically verified; actual deployment admission blocked
- Assembly report0ad8c43dd93eb7ce3513f3da4a668f50e9863eb604b1838c4fcc0f9378116995:
 27uniqueXMLpasses,69newartifactdigests/132sourcebindings verified; scopedgates0.
 Independent readonly reviewdb452d2c covers combineddriver/defaultassembly, notonly
 fake typed callbacks. Native/server/SQL execution not issued.
- Actual4exactqualifiedrole/image/ownedvolume metadata observed: native services
 are rathena-login/rathena-char/rathena-map. Candidateguard requires logicalnames;
 reviewer notified with genuine source/deployment mismatch; candidate frozen.
- Read-only actualbattleclosure19files enablesfeature.autotrade. CountsremainUNKNOWN,
 neverzero inferred. Vending/buyingstore bootstraps omitcountmessageonzero initial
 rows and laterdelete/reinsertrows; currentemptySQL alone notuniversalcountproof.
- Parentonlyreadonlyprobe had logical-label and strictconfigline-oracle mistakes;
 correctedsolelyownprobe against actualmetadata and battle_config_read sscanfskip
 semantics. These are not candidate repairs or new featureTDD proofs.
- Recovery remains blocked on rolelabeldefect and explicitoperator choice ofnormal
 boundedmaintenancepolicy vs proof-onlyzero-autotraderadmission. DB/volume muststay,
 freshownership/no-human guard required; nofeatureflip/manualSQL/forcekill/retry.
 NativeactivationREVOKED, actualgameplay/recovery/fullgoalsOPEN.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-11 local] correction | Recovery33 offline adopted; claimed service-label defect retracted
- Review4b6ce3f931b888c06d48718626205704cf609dfadc117286ecaafccae6aaa361
 physically verified27+6=33disjointpasses,134frozenpaths/27reviewartifactdigests,
 configuredquality0 and expected missing-approvalCLIexit2. Parent initially asserted
 everyexit0; corrected verification oracle, notcandidate fault orrepair.
- **Previous parent claim of service-label defect was WRONG.** Current frozen
 recovery.py229 explicitly expects rathena-login/char/map. Reviewer fullCLIprobe
 passed exact actuallabels throughconcreteadapter/helperchain. No candidate drift,
 repairs orbudgetreset. Earlier mistaken records preserved; this correction supersedes.
- Offlinequalification is not actualrestartcompatibility. FullNetworkSettings hash
 and mandatory nonemptyaddresses at stoppedrole transitions are unverified against
 actualengine metadata behavior. No permission to stop/start merely to test it.
- Actual featureprobe establishesenabledautotrade, not zerocount. Unknown admission
 stillblocks; explicitboundedmaintenancepolicy decision remainspending. Reviewresult
 is not userconsent. No lifecycle/SQLchange/native/provider effects orflag-clearedclaim.
 AllgoalsOPEN; nativeactivationREVOKED.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-12 local] update | Autonomous project authority reaffirmed; bounded maintenance implementation
- User selected the bounded maintenance policy, preserving database and volume, then
  explicitly corrected the repeated authorization prompts: autonomous continuation
  until this project is done. Recorded project-specific skill convention and authority
  addendum. Routine consent is not a blocker; tool-enforced safety and actual technical
  qualification remain distinct and mandatory.
- Fresh read-only engine inspection verified four exact owned roles running with
  qualified images and the owned named volume. The prior 134-path source freeze has
  no missing files or drift. No actual service, SQL or native changes occurred.
- Dispatched f4a23a4d for a finite, test-first maintenance-policy extension of the
  existing driver/default assembly. Archive strict accepted bytes; keep old refusal
  behavior and all native allOffline guards. Admit UNKNOWN actor counts honestly
  only under fresh exact known-nonhuman registry ownership, never fabricated zeros.
- Cover normal stopped/network endpoint transitions while preserving stable owned
  identity, MariaDB lifetime, real role readiness/peers, bounded SIGTERM-only order,
  failure custody and final unchanged helper readback. No new recovery framework.
- Current gap is technical implementation/verification, not user authorization.
  Actual recovery, native planning progress and all full milestones remain open.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-12 local] update | Fresh read-only orphan attribution and next fixed-pilot candidate
- Maintenance-policy worker remains active. Parent ran a separately named clone of
  the existing read-only attribution script, changing only its output filename so
  original attempt evidence stays immutable. Current canonical fixture lock held.
- Actual SQL count readback: two characters, one online owned fixture0, fixture1
  offline, no foreign online characters. No SQL mutations, native sessions, inference
  or lifecycle commands. This is attribution only; full ownership checks remain.
- Checked the pinned public NPC source: Bard#brising is prt_fild08,175,374. Current
  saved SQL positions favor fixture1 at176,374 over fixture0 at193,362 for the next
  fixed one-response pilot. The unchanged authority schema already permits index1.
  Recorded candidate selection, not actual live range or NPC availability.
- After real recovery and fresh allOffline/source/world admission, select fixture1;
  retain received actor/name/type/map/range/UI gates. No teleport, stat grant, seed
  or unguarded click. Previous fixture0 failed run stays failed.
Updated [[goals-ledger]]; all six milestones and eleven criteria/subgoals remain OPEN.

## [2026-10-12 local] update | Parallel worker arsenal and hourly completion-roadmap reporting
- User requested multiple workers and hourly reports starting now, including the
  completion roadmap/current point. Saved the project convention and created
  [[completion-roadmap]] plus canonical project-roadmap-status.json.
- Maintenance worker remains active. Dispatched two independent lanes for existing
  provider metadata readiness and the dashboard-to-population runtime frontier.
  Their report artifacts are available: parent verified19provider source receipts
  and24dashboard source digests. Endpoint health is not inference acceptance.
- Dashboard first blocking runtime hop: host-bound regenerate enters WorldState's
  _require_unbound; actual host WorldFeed assembly injects chat commands but no
  host-owned population reconciliation caller. Finite later TDD slice recorded;
  actual accounts/characters/workers are not generated by this audit.
- Created/read back hourly cron57f8b2ceb72b. Origin delivery had no live channel;
  changed and verified route to the current profile's canonical Bot Chat. No broad
  all-channel broadcast or other-profile changes. Initial run dispatched d57175be;
  outcome/delivery pending, not claimed successful. Next recorded fire21:24CEST.
- Reporting is read-only, self-contained and continuity-enabled. Reports distinguish
  fresh/stale workers, offline/native evidence and explicit currentpoint1.2. The
  seven-point roadmap covers every standing criterion; all fullmilestonesOPEN.
Updated [[goals-ledger]], [[completion-roadmap]], and [[index]].

## [2026-10-12 local] update | Maintenance41 verified; exact dependency restoration and dashboard tracer lanes
- Maintenance handoff verified41physical passes, all33prior raw IDs retained and
  eight new cases,58artifactdigests and scoped quality0. Missing-approvalCLIexit2
  remains an expected denial. The current two driver modules/test match their hashes.
- Four unchanged approved helpers disappeared after the completed source snapshot;
  cause UNKNOWN. Current136-path source freeze has exactlythosefour absent, no
  present-source drift. Earlier original27 XML is also absent; prior IDs compared
  against the durable review JSON, not claimed freshly rehashed historical XML.
- Worker3790aeb1 restores exact approved helper bytes from existing provenance and
  saves an exact public-only durable backup; no authority rebind/substitute source.
  Its disjoint sibling creates the actual host-bound dashboard generation RED and
  two controls in scratch only. No production or native/service/SQL effects.
- Roadmap advances to1.3 dependency restoration/current maintenance qualification,
  not actual recovery. No routine user consent is missing. FullgoalsremainOPEN.
Updated [[goals-ledger]], [[completion-roadmap]], and [[index]].

## [2026-10-12 local] update | Exact helpers restored; maintenance review and live read-only admission
- Parent verified4approvedhelper restorations totaling22058bytes, exact target and
  durable public-backup hashes, compile-only metadata, no source rebind. Complete
  maintenance136source paths match again. Restoration reportaa80ecd9132fbfc1d2e8558308a1c52c7d0164f9b72021d3347a699b37b2296f.
- Dashboard tracer93980f0623e0565fab8dafea5c57b09a38307cfb774948cad2f338c50b1060fc
  physically has2passedcontrols+1intentionalHTTP400instead202 RED at the missing
  hostpopulationcaller. Runtimecodehashesmatch; mutablecoordinatorledger drift
  recorded ratherthanclaiming an unchanged entire audit scope. No implementation.
- Dispatchedc373ee86: independentcompletedmaintenance41snapshotreview with4fresh
  focusedprobes, anddisjoint actualREADONLYrole/network/runtime/worker/socket/SELECT
  qualification. Bothuseexistingcode, notnewoperators orpermissionprompts.
- No source repairs/native/reactivation/service/SQLwrite/provider effects byparent.
  Roadmappoint1.3 nowreview/operationalqualification; actualrecovery staysunperformed.
Updated [[goals-ledger]], [[completion-roadmap]], and [[index]].

## [2026-10-12 local] update | Offline45 reconciled; actual observer failures drive bounded repair
- Fresh completed-snapshot review3302bfc1... verified41regression+4boundary passes,
 139frozenpaths/26reviewartifacts. Six archived-source selectors relocate honestly;
 35rawhistoricalIDs equal, no normalization or duplicate-run case inflation.
- Actual preflightd141eb5... observes complete exactnonhuman SQLregistry: two accounts,
 twocharacters, flags1,0, noforeign accounts/chars/guildmembers. FixedtransportSELECT
 passed asdiagnostic; guardedEffects.query andsnapshot stillrefuse. Ownedroles/images/
 mounts/network identity verified; currentapprovalnotissued, zero lifecyclecalls.
- Actual adapter mismatches: nativeignoredcolonlessbattleline; Podman bridge mode/
 emptyEndpointIDs despitevalidownedattachments; unreadablePIDfds(errno13); mapconstant
 16122vsactual15121;11DBlifetimeerrormarkers and untimestampedchar/map loglines.
 These are technicalfacts, not missingconsent orpermissiontoforceworldstate.
- Dispatched2e179dfc three disjoint workers: verticalTDDforonlyparser/network/port;
 supportedownedrootless socket-observationdiagnosis; native logframing/lifetimeerror
 rootcauseclassification. No serverconfigchange, sudo, privilegedcontainer orwaiver.
- Roadmap1.3 remainsactualadmissioncompatibility beforecontrollednormalmaintenance.
 FullgoalsOPEN; no actualrecovery/native/provider effects byparent.
Updated [[goals-ledger]], [[completion-roadmap]], and [[index]].

## [2026-10-12 local] update | Deployment repair51 verified; real namespace sockets and genuine fault follow-up
- Parent verified all 51 physical passing cases and 70 artifact hashes for the
  configuration/network/port repair. The accepted adapter digest is e44b5d4b...;
  old assertions remain, with explicit synthetic transport-fixture correction.
- Two real observations through the same rootless engine user namespace establish
  PID-owned native/DB listeners and reciprocal peers. FD permission root cause is
  confirmed, not solved by fabricated zero counts or host privilege changes.
- LF records retain timestamps; Python splitlines separated CR progress fragments
  (3 char, 81 map), then sorting destroyed adjacency. Integration must preserve
  original LF framing and both streams, not invent missing timestamp provenance.
- Eleven DB Aria/crash/repair messages and three map asset startup errors remain
  genuine historical faults. Healthy service/SELECT evidence alone is not a table
  repair or asset-resolution receipt. No blanket historical-error waiver.
- Dispatched 4b8b4570 for three disjoint lanes: tested reader/framing integration,
  bounded current table-health diagnostics, and exact pinned public missing-asset
  attribution/restoration plan. No world rewrite or service stop/start was performed.
Updated [[goals-ledger]] and the canonical roadmap status; full goals remain open.

## [2026-10-12 local] update | Observation57 and current MyISAM checks; scoped public-asset restoration
- Parent physically verified57passing cases and integration artifact hashes; socket
  reader and LF/CR framing are integrated offline. Existing error refusals remain.
- Current CHECK TABLE QUICK:12unique targetedtables allOK, no warnings/errors.
  **Correction:** actualenginesareMyISAM, notAria; a broad MariaDBsubstring caused
  the earlier false engine label. Do not infer exact recovery mechanism or absence
  of past data loss. QUICK updated check times; primary docs consulted afterward is
  a preserved process deviation, not rewritten as prior validation.
- Exact three asset failures need four pinned files: empty import map cache,
  mob appearance template, barter root and its mandatory empty custom default.
  Privateplan6064092d... source/candidate hashes verified; no invented blank YAML.
- Parent scoped only absent-target public installs into exactowned testvolume,
  requiredowner/modes, freshcomplete nonhuman registry and nooverwrite/readback.
  Dispatchedf32d6ed4 installer plus disjoint minimaloperation-error contract writer.
  No database repair/reset/restart, game-role lifecycle or native/provider session.
- Roadmap1.3 remains current. Fresh startup must independently prove former asset
  errors gone and no new operation failure; historical counts are not erased.
Updated [[goals-ledger]] and the canonical roadmap status; full goals remain open.

## [2026-10-13 local] update | Connected world restored; roadmap 1.4
- Verified one owned map start and real post-start parser/reciprocal peer/error
  readback. DB/login/char stayed running, both owned fixtures offline0/0.
- Recovered exact pilot public source and host manifest with durable allowlists;
  imports pass. Source-pruning cause remains unknown; historical tests not rerun.
- Current blocker is audit/runtime coupling: six vanished old scratch tests/report
  are not executable dependencies. Minimal guard policy keeps immutable review
  anchors and actual code/data/helper/private/expiry bindings strict; no waiver.
- Dispatched the selected-provider availability check without inference or config
  changes; results are pending. No health or tool-support pass is inferred.
- No native pilot, quest/reward, equipment, XP/loot or sustained population accepted.
Full goals remain open; [[completion-roadmap]] and [[goals-ledger]] updated.

## [2026-10-13 local] update | Pilot reached missing host data inputs
- The audit/runtime guard passed its independent review (3 author + 1 reviewer
  physical cases). Runtime inputs and active authority checks remain mandatory.
- Parent initially selected the wrong default idle location. This refused before
  activation; the already-qualified pilot overlay is intact. The explicit existing
  location argument corrected the invocation, not private config or source bytes.
- One bounded pilot then failed FileNotFoundError before any native connection,
  provider or NPC call. Supported cleanup and exact offline SQL readback passed;
  activation was revoked and no automatic retry followed.
- The configured host runtime lacks both map caches and the pre-re mob database.
  These are bot-side public data inputs, not the already-restored server assets.
  Two disjoint workers restore exact qualified bytes and inspect constructor closure.
Full goals remain open; first received LLM/CLEF/NPC progression is not accepted.

## [2026-10-13 local] update | Durable repo-local runtime adopted
- User directed project scratchpads to a Git-ignored folder inside the repository.
  Created `.work/`, verified Git exclusion, copied three qualified public data inputs
  and required operator sources; private copies change only their local path fields.
- Parent independently read the source diff and verified bindings/29 artifacts/four
  physical final tests. Public-data host construction and cleanup pass offline.
- Actual repo-local helpers now pass under the original canonical fixture lock,
  with owned world admission and all characters offline. No native/inference effects.
- Path-only relocation retains inherited helper Ruff30/mypy7 findings unchanged;
  those broad helper gates are not clean or waived. New pilot/test gates pass.
- `.work/operators` and `.work/runtime` are canonical for the next pilot; historical
  Hermes scratch paths survive only as audit identifiers, not required runtime data.
Native activation remains revoked. Full goals and first NPC progression stay open.

## [2026-10-13 local] update | Repo-local native startup reached the map
- Fresh locked repo-local helper preflight passed; one separately scoped fixed
  pilot constructed real host/memory/providers and reached map authentication.
- Failure metadata retained complete validated HP/SP, live reader, no RX/dispatch
  errors and 67 received frames. Fixed NPC readiness still refused; the exact
  name/range/life/pose/motion/progression predicate is not retained, hence UNKNOWN.
- Planning/LLM/CLEF/NPC request counts stayed zero. Supported cleanup and exact
  offline readback passed, owner was not retained, and activation was revoked.
- Two project-local worker lanes investigate readiness/name acquisition and an
  ordinary novice equipment/stat/skill preparation route. No code or native retry.
No missing files or workspace failure is newly established. Full goals remain open.

## [2026-10-13 local] update | Received NPC name gap reproduced before implementation
- Pinned server actor-entry packets already include NPC names. Wrapper projection
  only retains a separate 0ADF reply and otherwise exposes NPC#id. Source-backed
  offline characterization reproduces readiness timeout with all other guards met.
- Parent ran a real PlayingClient pytest tracer: expected Bard#brising, received
  NPC#444 (behavioral RED). A finite TDD worker now implements retention of already
  received entry names; no additional query packet or wider native action scope.
- Separate worker adds only bounded cached-readiness diagnostics so any subsequent
  native refusal identifies available/unknown predicates without raw/private data.
  Exact failing predicate of the prior native attempt remains unproven.
- Preparation reconnaissance found conditional Knife1201 shop acquisition, not a
  free weapon guarantee for existing fixtures. Fresh currency/points/equipped state
  and legal navigation remain required; Bard is a God-quest NPC, not a trainer.
Full gates await the completed source snapshot. Activation remains revoked.

## [2026-10-13 local] update | Complete offline candidate and durable source locators
- Entry-name retention and safe cached diagnostics pass 48 combined cases; an
  explicit versioned source-binding evolution adds one case and preserves source/
  manifest drift and revoked-activation denial controls (49 total, no overlap count).
- The original 420-entry manifest is unchanged. A new candidate changes exactly two
  production source bindings; all 418 other entries and historical audit values stay
  preserved. Guard edits are only the new manifest filename and digest.
- Full gate finished 5,576 unique cases: 5,563 passed, 10 failed, 3 setup errors,
  plus 65 passing subtests; reported coverage 96%, audit exit0. Every non-pass was
  an obsolete configured-source locator, not a feature regression.
- Verified the existing durable public mirror; three test path assignments now use
  it with unchanged profile/compiler/hash assertions and original protocol metadata.
  All 549 source-consumer module cases pass. No cache restoration or recompilation
  of native server roles occurred; only existing layout diagnostic oracles ran.
- A matching fullcheck/audit rerun and one combined 266-path independent review are
  running. The first 240-second interrupted gate is retained, not rewritten as PASS.
Native authorization remains revoked; first received NPC progression remains open.

## [2026-10-13 local] update | Native dialogue and real LLM loop reached
- Final combined review passed with 49 identical physical test identities and all
  266 frozen paths unchanged. Matching root gates: 5,576 unique +65 subtests,
  check0/audit0, measured95.55078244860387% coverage. Version adopted offline.
- Fresh repo-local provider metadata and canonical locked world/allOffline checks
  passed. First parent invocation refused before activation on an obsolete initial-
  relocation config comparison; current canonical digest was intact. Preserved the
  refusal and corrected only the caller after fresh read-only reconciliation.
- One actual bounded pilot recognized the NPC, clicked once, received initial NEXT
  UI, and completed three HTTP200 LLM calls: investigate, investigate, submit_plan.
  Admission denied; CLEF0, NPCresponses0, UI advancement unaccepted. No retry.
- Supported cleanup and exact offline readback passed; owner not retained; activation
  revoked. Existing private request/response evidence drives offline denial replay.
Full goals remain open. This is real NPC perception/LLM authoring, not rewards/play.

## [2026-10-13 local] update | Captured plan timing failure and bounded UI policy
- Offline actual decoder replay passes shape, timing, supported phase, prerequisites,
  receipt identity and stage. Recorded advisory NPC receipt was expired before the
  final LLM response by1.665275748s; exact original worker/fresh-admission site unknown.
- The real model generated191 plan tokens at about18.86tok/s; prefix cache worked.
  No new inference was performed and captured private evidence remains unchanged.
- Qualified configured-source preprocessing with unchanged map flags verifies secure
  NEXT/menu timeout60s. Source timer implements that policy; no server changes.
- Parent scopes received-ready NEXT/menu window30s, preserving opening/response/cancel
  waits5s, absolute120s, cursor/actor/epoch/life/drift guards and strict deadline rejection.
  Old captured15s receipts remain expired; no renewed timestamps or cache authority.
- A finite TDD worker implements the forward policy. No model/context budget change,
  phase expansion, session retry or native authorization is inferred.
Full goals remain open; actual CLEF/NEXT dispatch and UI progression are pending.

## [2026-10-13 local] update | Received-ready policy completed, combined review running
- Parent verified worker artifacts, genuine behavioral RED, 1,056 unique scoped
  GREEN cases and all 264 completed source paths. Thirty-three new physical cases
  cover the window and unchanged safeguards; six historical timing cases revised.
- A new 420-entry operator manifest changes only the controller plus the two
  timing-test digests; 417 bindings remain unchanged and old manifest stays intact.
  Guard changes are exactly three manifest references and the corresponding digest.
- The old guard reached source-binding RED; parent combined policy/binding selection
  passed 34 physical cases, including revoked-authority and drift rejection.
- The complete 268-path source/operator snapshot is frozen for independent review.
  Parent unchanged full check/audit runs separately with physical XML and coverage.
- No native execution, model requests or authority activation. Root acceptance and
  independent verdict are pending; actual CLEF/NEXT progression remains unaccepted.

## [2026-10-13 local] update | First actual LLM -> CLEF -> NPC progression passed
- Independent review passed the completed 268-path snapshot with 34 identical parent
  test IDs, six boundary controls and six revised timing cases. Matching root gates:
  5,609 unique tests +65 subtests, 95.573954819585% coverage; check0/audit0.
- Fresh locked owned-world/helper offline admission and six provider metadata GETs
  passed. One new scoped forward-policy native invocation completed in20.13s.
- The bot perceived the named NPC, opened dialogue, investigated and submitted an
  actual LLM plan (two completions), obtained fresh admission and one CLEF execution
  decision, issued one NEXT and received newer matching same-open UI progression.
- Supported host/worker/transport cleanup, exact offline readback and lock release
  passed. No retained owner; activation revoked. No automatic retry or server change.
- Roadmap1.4 narrow gate passed; point1.5 human/wider-world acceptance remains open.
  Two disjoint offline lanes now close the existing novice route's portal gap and
  trace the first missing shop/equipment execution boundary. No XP/loot/preparation,
  completed dialogue/quest/reward or sustained playing-population acceptance.

## [2026-10-13 local] update | Ordinary route closed and first shop execution gap reached
- Parent verified 16 pinned public source bindings and loaded both actual qualified
  caches through MapCache. Field, city and shop paths are walkable, adjacent and
  corner-safe, with valid trigger/approach cells. This is public geometry only:
  current position, live clearance, loaded overrides and traversal remain unknown.
- Parent reran the exact actual-client shop frontier: two existing characterizations
  pass; one behavioral RED reaches unsupported typed BUY selection with no C5 send.
  C4 receipt/event already works. Historical setup/oracle failures remain preserved.
- A disjoint TDD worker now implements one guarded C4 -> typed C5(type0) zero-spend
  selection and bounded wait. Purchase, acquisition, equip and planner publication
  stay outside that slice. Another read-only worker checks human-client prerequisites.
- No new native or model effects; current activation stays revoked. Roadmap1.5
  human/wider-world acceptance and parallel preparation2.1 remain open.

## [2026-10-13 local] update | Shop selection scoped GREEN; human client unqualified
- Parent verified all253 worker freeze bindings, declared owned-source hashes,
  preserved RED/GREEN XML counts and whole-source quality receipts. The unadvertised
  owner-minted shop action passes1,010 scoped cases including38 new cases.
- The controller emits one zero-spend C5(type0), consumes the marker/request budget,
  and waits five seconds. No C8 purchase, equip, offer/currency projection or planner
  publication. Reached actor-entry/reader-replacement defects were repaired; no
  unrelated existing source/test drift. Root gate and independent review pending.
- Expanded the prior completed source/operator snapshot to273 current physical paths;
  old manifests and source guard remain unchanged, intentionally denying runtime
  activation of the new primitive. No model/native/world effects.
- Human inventory found21 uaRO-specific input files but no qualified matching plain
  MAIN20180704 bundle within bounded search. Compatibility and GRF-packed configs
  remain unknown. Primary-source discovery now checks realistic compatible-client
  paths; no downloads, protected-client edits or server-profile migration.

## [2026-10-13 local] update | Shop-selection library adopted; offers still absent
- Parent verified independent41 selected IDs,101 boundary/regression cases and all273
  current frozen source/operator paths. Matching unchanged root check/audit passed:
  5,647 unique tests +65 subtests,95.59869892254524% coverage. Offline adoption only.
- No native shop permission: source guard remains intentionally stale and revoked.
  Zero-spend list selection is not purchasing, ownership, wearing or planner support.
- The next actual-client parent tracer minted/dispatched C5, received framed C6, and
  failed at the precise missing BotState.shop_offer projection; no setup errors.
- A bounded TDD lane now correlates received offers and SELF B1 Zeny into typed state,
  with stale/malformed/unsolicited/owner-replacement denial and no spending/actions.
  Human-client source discovery remains separate and pending; no download/profile change.

## [2026-10-13 local] update | User-supplied HTTP client source works
- User has no local bundle and directed checking exacthttp://nemo.herc.ws/clients/.
  Its supplied HTTP index, MAIN entry and specific download instructions fetched
  successfully; earlier HTTPS counterpart failed certificate hostname verification.
  No TLS bypass, browser termination or Hermes configuration change was used.
- The MAIN2018-07-04aRagexe page supplies an archive SHA256 and a legacy downloader.
  Inspected the script as data and decoded literal download bases without eval/exec;
  no remote helper/downloader or client executable ran, no antivirus settings changed.
- A bounded worker now retrieves/verifies the exact archive and safely extracts/static-
  inspects PE data. Complete resource/client configuration and GUI acceptance remain
  open; no server-profile migration or human login is authorized by this discovery.
- Shop offer/currency TDD continues independently. Prior missing-source research
  remains immutable historical evidence, not a current global absence assertion.

## [2026-10-13 local] update | Shop offer/currency projection scoped GREEN
- Parent verified declared receipts, owned hashes, quality logs and protected
  source baseline. Worker scoped1,256 cases include40 new tests; parent selected41
  actual-client/feature cases passed. Only the declared model/runtime files changed;
  immutable domain DTOs, bounded adapter and tests are new.
- BotState now carries current owner-correlated C6 rows and receipt metadata, plus
  signed received B1/20 Zeny and provenance. Zero/negative values remain literal;
  ordinary warp retains currency history, not spending freshness. Current offers
  expire with the original five-second wait; no timers or permissions were expanded.
- The complete278-path snapshot is frozen for independent review while root gates
  run separately. No C8 purchase/equip, planner advertising or native guard rebinding.
- Exact MAIN client archive acquisition/static qualification continues independently.
  No client/script execution, human login, server change or new bot-model calls.

## [2026-10-13 local] update | User's RagnarokOnline flake inspected read-only
- Following user correction, paused downloader-audit continuation and inspected
  ~/RagnarokOnline/flake.nix, lock, launcher and README. It pins GE-Proton9-27 and
  steam-run-free for LATAM, with persistent prefix under that home directory.
- No default Ragnarok.exe, Ragexe.exe or GRF was found in that flake tree. The
  flake is a runtime recipe, not a client/game-resource bundle or gameplay proof.
- Existing uaRO lab archives were checked only for sizes/header bytes. data.grf
  carries Event Horizon/0x300 rather than the overlays' Master of Magic/0x200;
  legacy compatibility remains unknown, not assumed corrupt or decrypted.
- Original prefixes/resources untouched. Private-world experiments require a
  separate project prefix and tiny public Nix input boundary, not the original
  launcher's hard-coded prefix or a whole game tree imported into the Nix store.

## [2026-10-13 local] update | Offer/currency library adopted; one-item purchase next
- Parent verified independent41 matching selected cases plus9 probes, artifact hashes,
  all278 frozen paths and the completed root gate. Actual summary:5,687 unique
  tests +65 subtests,95.59931678890787% coverage, check0/audit0. Offline adoption only.
- Current offers are bounded local C5 correlations, not a protocol nonce; Zeny is
  received history, not permission to spend. No native/model/purchase/equip acceptance.
- A finite read-only lane now traces the source-correct one-unit purchase, effective
  price/currency/capacity gates, and active inventory/result emission through the
  actual framer/collector. It will reproduce the earliest missing receipt boundary
  before implementing or advertising spending. No generic catalogue expansion.
- User's flake/resource inspection remains read-only; matching human client still
  unqualified. No client launch, original-prefix change, native retry or new inference.

## [2026-10-13 local] update | User accepts uaRO-inspired incremental server baseline
- Recorded the new direction: a uaRO-like starting world is sufficient; missing
  server-side content can be added during development. Perfect custom-system parity
  is not the initial MVP requirement; core isolated-agent/LLM/CLEF goals remain.
- Two disjoint read-only lanes qualify public baseline information and actual local
  protected client/config/resource constraints. No unsupported compatibility claim,
  Gepard bypass, client patch, network redirection, engine migration or data reset.
- Existing qualified world/profile and completed evidence remain preserved. The
  reached capacity-projection RED is retained; profile-specific spending work waits
  for the concrete client/server target rather than embedding another guess.

## [2026-10-13 local] update | Retain working server for uaRO-inspired gameplay
- Completed compatibility reports establish local executable identity, but packet
  date/family and supported private-server connection/integration remain unknown.
  Public documentation is not a deployable custom uaRO server bundle. Parent keeps
  pre-renewal rAthena and isolated-agent architecture, with incremental inspired content.
- Small643-byte standard-format proxy-patch index contains data/clientinfo.xml.
  Standard payload decompression failed; preserved failure, no alternate decryption,
  client modification, endpoint redirection, license inspection or runtime attempt.
- Human joining remains blocked on a configurable compatible client/resource pair
  or supported publisher/vendor integration. No engine migration or world/data reset.
- Resumed a finite read-only capacity TDD producer on the known qualified baseline;
  disjoint public-source lane resolves Knife weight and actual slot rules. No spending,
  purchase/equip acceptance or native guard rebinding is inferred.

## [2026-10-13 local] update | Pinned Knife mechanics verified; defaults remain non-admitting
- Parent checked all declared public source bindings: nominal Knife1201 weighs400
  raw engine units (40 display), is non-stackable and needs one new slot for quantity1.
  This is pinned source, not deployed item/import override or acquisition evidence.
- Character inventory_slots loads directly; compiled array/schema default100 does
  not establish actual selected-character allowance. No active20180704 slot-limit
  packet was identified. Unknown limits are not normalized or assumed100.
- Capacity producer continues unchanged. A separate bounded lane now reads only
  exact owned public deployed item/import files to qualify nominal vs actual values;
  no character SQL, world lifecycle, client/server migration or native/model calls.

## [2026-10-13 local] update | Capacity scoped GREEN; root/independent gates dispatched
- Parent verified38newcases, current810passing scoped regressions, source/profile/log
  hashes and physical historical XML receipts. Retain original missing-capacity RED,
  reached lifecycle/regression failures and corrected scratch-oracle chronology.
- Frozen331interacting physical inputs; started unchanged full task check/audit and
  independent completed-snapshot review in parallel. No source writer is active;
  scoped GREEN is not root, native, spending or GUI acceptance.
- Public deployed disk closure has Knife400raw without reachable import override;
  copied public files verified. Actually loaded DB selector/state and selected-character
  slot allowance remain unknown. No assumption that array/default100 grants allowance.

## [2026-10-13 local] update | Capacity candidate rejected; bounded repair dispatched
- Full gate5725unique cases:5failures,0errors/skips; check201, audit0. Preserve
  generic-policy regressions in chat, invalid selected NPC name and encounter recovery.
- Independent39selected tests pass, but5additional owner-reference boundary probes
  fail: capacity clears while old complete inventory survives or replays after wire
  replacement. ReviewFAIL, not source drift; original331-path evidence unchanged.
- No adoption: previous accepted root remains the shop-context snapshot. New repair
  context owns only reached faults, first review-repair cycle; preserve original code
  bytes and failed receipts. Source-only disjoint lane identifies smallest existing
  selected-SELF slot metadata path without querying DB or exposing private inputs.

## [2026-10-13 local] update | Actual owned-read omission reproduced; narrow helper candidate
- Source frontier and all declared source hashes verified. Existing MechanicsPort is
  public catalog only; existing owned baseline character SELECT omits inventory_slots.
- Parent exercised unchanged real helper parsing, ownership and offline checks using
  synthetic private I/O and subprocess primitive spies. One behavioral failure,
  zero errors/skips: actual query omits allowance. No private inputs or SQL accessed.
- Dispatch minimal versioned selected-owner read candidate in offline TDD, disjoint
  from capacity repair. Reuse existing world/fixture checks and canonical locked caller;
  original helpers, pointers and failed receipts remain unchanged. Future evidence is
  server-verified own metadata, not native telemetry or permission to buy.

## [2026-10-13 local] update | First repair scoped GREEN; current-code acceptance pending
- Parent verified 2,666 unique passing regressions, including all five old root
  failures; repeated ten reached failures preserved. Five owner-boundary cases are
  permanent tests. Only three allowed source files changed in the bounded repair.
- Pre-repair hashes were recorded but source bytes not saved before editing. Keep
  that limitation explicit; no original diff reconstructed. Full current-code review
  uses the preserved failure evidence and the repaired actual-client path.
- Frozen 347 completed interacting inputs; new unchanged full check/audit and an
  independent full-current review run in parallel. Selected-owner read candidate
  remains a disjoint offline lane. No adoption, native activation or purchase yet.

## [2026-10-13 local] update | Selected-owner slot candidate verified; conditional review pending
- Parent verified 11 source bindings, eight physical receipt declarations and 12
  unique final passing cases. Projection and reached boundary failures are preserved;
  unchanged predecessor and parent omission RED remain byte-bound.
- Candidate resolves explicit persona and performs one fixed selected CID/AID/offline
  read, validates identity/name/raw allowance 0..100, and publishes selected SELF only.
  Actual allowance remains unknown; no native packet or spend authority inferred.
- Black/mypy pass, Ruff remains nonzero with ten inherited style findings. Independent
  conditional-helper review dispatched; caller-held canonical lock, fresh preflight
  and exact private-input alignment still require qualification before a live read.

## [2026-10-13 local] update | Repaired read-only capacity component accepted
- Parent verified matching full gates: 5,730 unique tests +65 subtests, zero
  failures/errors/skips, 95.67% coverage; check/audit0 and 347 frozen inputs unchanged.
- Independent full-current review passes 161 unique cases, including five additional
  fresh-barrier recovery controls. Original failed reports/receipts remain intact;
  missing pre-repair source-byte copies are disclosed, no historical diff invented.
- Adopt current read-only capacity library component only. No native activation,
  purchase/equip, LLM call or human GUI acceptance. Selected-owner metadata helper
  awaits conditional review and exact held-lock/fresh caller qualification; actual
  allowance and loaded item authority remain unknown. All full milestones stay open.

## [2026-10-13 local] update | Helper conditional PASS; caller ABI gap exercised
- Parent verified 14 independent slot-helper cases and artifact/quality-log hashes;
  conditional component approval only, with ten inherited Ruff findings unchanged.
- Two actual legacy-caller characterization cases pass: candidate refused before
  private/effect boundary; test-local allowance exposes missing persona argument and
  legacy result parser mismatch. This is not feature RED or a new source approval.
- Default helper pointer metadata is repo-local, regular nonsymlink, owner0600 for
  config/manifest; no private bodies read. Dispatch minimal metadata-only caller
  qualification using existing source/private checks and canonical FixtureLock.
- Separate bounded lane qualifies owned map item-loader keys/path/log metadata;
  no SQL, restart, native activation, purchase or private config-value publication.

## [2026-10-13 local] update | Corrected parent item-loader source-path error
- First inspection stopped at /run/public-source because the parent brief omitted
  the repository prefix. Preserve that partial report; do not describe it as missing
  configured assets. Correct repo-local mirror and all three selector sources exist.
- Resume only bounded owned item-loader inspection under a new evidence/report
  namespace. No source restoration, server restart or authority change. Selected-owner
  caller remains active by fresh delegate listing; its outcome is not yet assumed.

## [2026-10-13 local] update | Caller input-domain correction, no pointer mutation
- V1 caller source/receipts verified: ten physical tests pass and local gates pass.
  Actual public pointers differ on config/manifest, share private_directory. Parent
  requirement unnecessarily coupled an independent readonly reader to native pilot.
- Preserve V1; explicit V2 selects scheduled readonly inputs exactly from its own
  hash-bound scope, with both public-pointer hashes and equal shared lock directory.
  Never rewrite pointers, fall back to pilot config or relax native authority.
- Actual V1 alignment predicate reaches one new-policy RED using location metadata
  only; no private bodies or SQL. Narrow versioned correction dispatched. Caller
  review/live binding and actual selected allowance remain unaccepted.

## [2026-10-13 local] update | Corrected item-loader selection qualified on disk
- Corrected source hashes and preserved wrong-path report verified; exact owned
  admission before/after and 16 config-file metadata records checked. Effective disk
  db_use_sqldbs=false, db_path=db selects /world/runtime/db/item_db.yml.
- This matches the five verified public YAML files and nominal Knife400 definition.
  Bounded current/retry logs contain no item-load messages; no in-memory weight
  observation or startup-byte binding is claimed. No restart/reload/SQL/admin query.
- V2 selected-owner caller is active by fresh listing. Actual slots and loaded item
  value remain unknown; no live binding, spending, equipment or full milestone closed.

## [2026-10-13 local] update | V2 caller current snapshot verified; full review dispatched
- Parent verified 14 source bindings and three physical receipt declarations: 13
  final cases pass, all ten V1 mappings retained plus three policy controls. Only
  aligned() function AST changed; own namespace/status constants are versioned.
- Scheduled input choice remains exact and hash-bound; both public locations and
  shared lock-directory check persist, independent native pilot inputs untouched.
- Full 371-line current metadata caller receives independent review, not merely a
  tiny predicate diff. No private config/manifest bodies, scope issuance, SQL, native
  activation or purchase. Actual allowance remains unknown until reviewed live read.

## [2026-10-13 local] update | Actual selected-SELF slot metadata read passed
- Full current caller review verified: 16 unique independent cases, source/public
  hashes match. Parent issued one 180-second metadata/fixed-read scope with exact
  private descriptor hashes; no credential publication or native authority change.
- Reviewed caller ran fresh real ownership/offline checks under canonical FixtureLock,
  then one selected-owner read. host_fixture_0 allowance100 observed; saved exact
  run file verified. No new native sessions, inference, spending or world mutation.
- Scope revoked immediately after success; actual check_scope refusal tested before
  private/effects. Source/public/private hashes unchanged; successful caller evidence
  is published only after supported release. No automatic retry or extra query.
- Metadata is an offline server-verified own snapshot. Later actual wire identity/
  session binding and loaded item authority remain separate from purchase permission.
  All full milestones and sustained bots-playing acceptance remain open.


## [2026-10-13 local] update | Actual client slot-context tracer RED; two lanes assigned
- One synthetic server-SELF proof exercised the real native client/state path.
  Actual failure: no owner-bound server-SELF slot publisher exists. No traffic
  beyond the unchanged two fixture baseline sends; no native effects.
- Preserved complete original bytes of model.py and playing_runtime.py before
  writer changes, plus all other protected Python source hashes and physical RED.
- Assigned a narrow TDD integration into detached BotState context, requiring
  matching endpoint, selected owner and session, with explicit unknown values.
- A disjoint source inspector is resolving the finite one-item C8/acquisition
  frontier and distinguishing server checks from unknown client weight prediction.
  No purchase permission, live scope, restart, SQL or new model call issued.


## [2026-10-13 local] update | Slot publisher frozen; actual model-context omissions reproduced
- Parent verified 843 unique scoped cases, 256 protected sources, all XML/log
  and receipt digests, and original writable-source bytes. Frozen current source
  receives independent review in parallel with unchanged root check/audit gates.
- Verified 24 source snapshots for the finite purchase proposal. Server loaded
  weight checking is not a C8 protocol prerequisite, but the existing local unknown
  weight no-send policy remains unchanged. CA0 alone does not establish acquisition.
- A separate two-case actual-client tracer reaches known weight/max-weight and
  bound slots in BotState, then demonstrates omission in CLEF request construction
  and public LLM character investigation. Preserve this future slice's RED and
  original consumer bytes; no current-source changes during frozen review.
- No new native connection, inference, SQL, purchase, equip or live scope issued.


## [2026-10-13 local] update | Slot publication accepted; model context and one-item purchase assigned
- Recovered completed root gates and independent review without rerunning them:
  5,815 unique root cases, check/audit0, coverage95.70293338565682%, 90 independent
  cases. All 389 frozen paths and passing physical receipt/log digests match.
- Adopted the narrow read-only component. Actual native acceptance, model-visible
  context and purchase permission are not implied. Preserved the next two REDs.
- Byte-preserved existing files for two disjoint writers: model-input projection
  and guarded quantity-one C8/acquisition correlation. Full gates wait until both
  completed snapshots; no sibling in-flight file is treated as unchanged.
- Pinned public default group0 source does not explicitly list iteminfo allowance;
  deployed permissions remain unknown. No privilege changes or diagnostic command.
- All full goals remain open; no SQL, native/model session, purchase or equipment.


## [2026-10-13 local] update | Model context and purchase candidates jointly frozen
- Parent verified both completed candidates: 715 selected context cases and 1,633
  selected purchase cases (42 feature cases included, not added again). All 160
  declared artifact bindings, current owned/protected/native sources and original
  bytes match. Context's earlier sibling drift remains disclosed, not joint proof.
- One 555-path completed combined snapshot now receives independent review while
  unchanged root check/audit run in a separate output namespace. No writers active.
- Preserved source-backed native usability frontier: ordinary C5 emits C6, not a
  guaranteed B1 refresh. New conservative five-second resource gates may refuse a
  normal route with older unchanged money; synchronized synthetic timing is not
  native feasibility. Reviewer notified; no policy waiver or fabricated refresh.
- Actual loaded item/shop facts remain unqualified. No new native/model session,
  SQL/admin operation, purchase/equipment or scope issuance. Full goals stay open.


## [2026-10-13 local] update | Rejected pre-dispatch renewal; narrow retirement correction
- Original combined root gates passed, but independent review reproduced two
  failures for one real authority-renewal fault. Purchase adoption is withheld.
  Context projection passed its scope; no full milestone or live claim follows.
- Preserved original review/rejection and complete pre-correction bytes. New
  permanent four-case regression reached two behavioral REDs: bound-but-unminted
  and already-minted authority revives after common health loss plus slot-only
  republication. Two controls were already green, not claimed as RED.
- One existing production file now consumes lost pre-dispatch authority and clears
  live qualification, preserving issued-state rules. Final 80 actual scoped cases
  pass, including six unchanged original interaction probes. Owned Black/Ruff/
  strict mypy/Xenon pass after preserved average-complexity failures and refactor.
- Corrected 570-path snapshot receives targeted independent review and fresh root
  gates. Prior item-type/index repair stays consumed and recorded, not reset.
  No native connection, model call, SQL, purchase or live scope was issued.


## [2026-10-13 local] update | Corrected combined offline components accepted
- Parent verified independent correction report digest and all final 84 cases,
  source/artifact digests, no failures/errors/skips, and all 570 frozen paths.
- Matching root gate: 5,887 unique cases, check/audit0, coverage95.70663606808185%.
  Adopted model-context projection and corrected unadvertised one-item exchange
  as offline library components only. Original rejected candidate remains rejected.
- Authority retirement covers pre-dispatch qualifications and minted actions;
  advisory republication, fresh status and later receipts cannot revive them.
- No active worker remains in these lanes. Actual item/shop qualification and
  legal resource refresh remain the next native frontier; no live purchase,
  inference, server/DB change or activation occurred. Full goals remain open.


## [2026-10-13 local] update | Real ordinary-player command configuration inspected
- Fresh exact owned map identity admitted before/after bounded public copies;
  group0 Player Level0 does not enable iteminfo or refresh on disk. Footer imports
  empty; copied bytes/hash verified. Loaded permissions remain unknown, not denied
  by an invented native response. No groups, permissions or runtime files changed.
- Official refresh emits weight/max-weight but no guaranteed B1; it also has
  chat/trade/buying-store/mail effects. Do not invoke or enable it as a harmless
  balance query. Group1 availability does not authorize moving ordinary fixtures.
- Assigned two disjoint finite source lanes: existing ordinary item-information
  NPC or minimal informational script candidate, and explicit source-backed
  resource freshness/refresh proposal. No production edit or native activation.
- Latest accepted library remains corrected 5,887-root/84-independent snapshot.
  No loaded item fact, live purchase, equipment or full milestone is accepted.


## [2026-10-13 local] update | Source frontiers verified; explicit preparation and guide seam assigned
- Verified 44 resource-source snapshots/artifact digests. Reproduced four proposed
  policy REDs and two controls in the established Nix/venv environment, distinct
  from the worker's alternative source-research dependency closure/setup errors.
- Verified 18-line informational guide bytes, every source/excerpt binding and
  four fresh owned public NPC copies. No existing qualifying one-item guide found;
  candidate remains uninstalled, native parser acceptance and loaded facts unknown.
- Selected only a default-off TDD candidate for a one-use, source-qualified
  non-mutating preparation lane with fixed120-second envelope; strict default and
  active five-second offer deadline remain unchanged. No native policy adoption.
- Found actual reviewed recovery CLI/public core in legacy cache, not the guessed
  canonical workspace. Assigned qualification of accepted source lineage and the
  minimum durable dependency/content seam; do not run stale locators or bypass guards.
- Two disjoint workers active. No native/model session, permission/group change,
  resource setter, guide installation, restart, SQL or purchase occurred.


## [2026-10-13 local] update | Preparation candidate shelved; guide publication path continues
- Parent verified 700 passing scoped cases separately from two remaining failures:
  retroactive unqualified NPC opening and oversized active-lane reader clock.
  Candidate budget exhausted. Preserve source/test bytes and failures; no adoption.
- Restored only the three writer-owned production files from byte-preserved accepted
  originals and archived both new candidate files outside source/test collection.
  Every protected input and eight accepted source bindings match; no global reset,
  staging or replacement of unrelated dirty work. Strict defaults remain active.
- Verified all 243 guide-deployment artifact bindings and retained 157 qualified
  public originals. Path-only helper candidate still lacks full nested sequencing;
  stopped-map content hook and already-offline request behavior remain unimplemented.
- Two disjoint lanes now review actual migrated helper/lock dependencies and build
  the bounded default-off public content hook in a separate candidate namespace.
  Existing recovery owns all lifecycle sequencing; no new generic executor.
- No world/private/DB change, native/model session, guide installation or permission.
  Latest accepted production snapshot remains the 5,887-case corrected components.


## [2026-10-13 local] update | Informational guide text reaches both cognition consumers
- Exercised actual wire framing/controller/state, CLEF request and LLM NPC
  investigation using source-shaped synthetic guide text: eight unique cases pass
  across both success/unavailable branches and batched/per-frame delivery.
- All eight successful-branch messages remain intact, without replacing received
  inventory/SELF capacity or creating loaded-item/purchase authority.
- Initial scratch oracle used nonexistent current_weight instead of BotState.weight;
  preserved failed receipt/original test. No production change or behavioral RED.
- Accepted production bindings still match. Guide deployment/parser/actual loaded
  values remain unknown; two independent maintenance/publication workers continue.


## [2026-10-13 local] update | Maintenance chain review recovered; exact guard gap reproduced
- Recovered completed review before delayed batch notification. Parent verified
  350 unchanged frozen paths, 15 passing actual offline caller/helper cases and
  exact accepted successor lineage for eight changed production sources.
- Reproduced both missing package-parent binding failures through real admission.
  The child -m helper imports robots and robots.adapters before its own module;
  those runtime files must be guarded, not merely present in a historical freeze.
- Current candidate is not accepted: two admission failures and one new path-only
  E501 remain. Assigned a separate bounded successor correction; no old budget reset.
- Publication worker remains active in its separate namespace and was informed
  of the dependency verdict. No actual world lock, lifecycle or native scope issued.


## [2026-10-13 local] update | Exact missing parent-import guards corrected offline
- Parent verified the completed successor report digest, every artifact binding,
  386 current frozen paths and 25 physical passing cases retaining all15 controls.
- Exact semantic diff adds only the two package-parent paths. Full recovery AST
  remains unchanged after a string-wrap quality repair; reader bytes are identical.
- Two original REDs and before-correction failures remain preserved. Current helper
  diagnostics remain inherited51 Ruff findings/31 mypy errors, not clean or waived.
- Assigned immutable independent completed-snapshot review while publisher finishes
  its separate candidate. No source guard adoption, scope issuance or live change.


## [2026-10-13 local] update | Publication candidate verified; exact combination under review
- Reconciled delayed maintenance result against already-handled report/correction;
  no duplicate read, review or authority issuance.
- Parent verified publication47 passing physical cases, 167 public artifact bindings,
  two original feature REDs and actual default denial. Exact pre-RED test-source
  copy was not saved; preserve that limitation, original core bytes and XML.
- Created separate provisional five-module combination: only two parent source
  bindings and mechanical HELPER_ROOT string wrap change from publication.
- Six declared composite static gates pass. Actual combined default CLI exits2
  approval_required with zero lifecycle commands. Frozen inputs remain unchanged.
- Component and full combined independent reviews are running separately. No
  conditional adoption, real scope, public content writes, startup or loaded values.


## [2026-10-13 local] update | Runtime-import guard component conditionally accepted offline
- Parent verified independent28 passing physical cases retaining all25 writer
  cases, exact source/registry/freeze bindings and no candidate blockers.
- Narrow guard component is conditionally accepted offline; inherited51 Ruff/31
  mypy diagnostics remain non-clean. No execution approval or operational binding.
- Final composite review remains active and has received the component verdict.
  Combination, deployment/parser/loaded values and all live/full milestones stay open.


## [2026-10-13 local] update | Canonical public-data omission fixed without code repair
- Composite review78 physical cases passed, but actual canonical admission failed:
  parent copied modules without their two ROOT/public dependencies. Preserve the
  missing-file receipt; mirrored fixture success was not operational readiness.
- Copied only the two already-frozen public inputs at exact canonical paths. All
  prior403 frozen inputs remain unchanged; successor closure has405 paths.
- Actual canonical _authorize/validate_request probe now passes without ROOT/data
  replacement, lock/private/log/role/public-write effects. Five fault controls pass.
- Assigned only a finite two-file independent closure check, reusing the completed
  source review. No code changes, old budget reset, deployment or native permission.


## [2026-10-13 local] update | Composite offline closure accepted; real deployment prerequisites next
- Independent canonical5 tests and direct canonical file-read probe passed, but
  reviewer stopped after miscounting structured binding registry top-level keys.
  Parent audited raw XML/log/freeze evidence and all37 actual bindings; do not
  invent the uncreated reviewer JSON or rerun the entire source review.
- Composite conditionally accepted offline: prior78 source cases and six static
  gates retained; exact405-path code/data closure unchanged. No real scope issued.
- Two disjoint lanes now inspect fresh exact-owned public targets and resolve
  the existing original-lock maintenance handoff. No new executor, role lifecycle,
  native session or automated approval. Human/actor observations remain unknown.


## [2026-10-13/14 local] update | Fresh runtime inputs captured; publication preconditions named
- Parent read phase ran once under the original lock using accepted Effects APIs:
  39 source, 50 runtime bindings, four role log baselines and 39 config files
  captured privately. Zero SQL, lifecycle, publication or native effects; lock
  released; no execution approval (literal zero expiry, read-only by construction).
- Two exact source-level blockers now block any content-bearing approval: the
  pinned DB table-health receipt is outside its 24-hour window, and map error
  inventory still pins the old 2026-10-08 epoch while the current epoch captured
  zero errors. Both need a reviewed source successor, not hash rebinding.
- The captured runtime map includes the import target key; a future content
  approval simply omits non-mandatory target keys, so no code change is required
  there. Guide absence on disk remains UNKNOWN until the in-request probe runs.
- One earlier read-phase invocation refused cleanly on a caller path-shape bug
  (relative PINNED_ASSETS path) and was corrected in a separate namespace with
  the original receipt preserved. No library guard was changed or bypassed.


## [2026-10-14 local] update | Precondition successor built offline; independent review running
- Successor resolves both publication preconditions by design: table-health
  receipt now travels in Approval bindings (exactly-one selection, byte re-check,
  historical path cannot rebind digest), and map baseline admission accepts only
  a strictly newer zero-error parent-carried epoch. MAP_FAULTS history immutable.
- TDD chronology verified: 20 successor contracts RED-first (12 failures on the
  two gaps against stashed composite bytes), then GREEN 98/98; 78 composite cases
  retained unchanged; only live_recovery.py changed (3 hunks); changed-pair gates
  Black/Ruff/strict-mypy/Xenon pass. Bare multi-name except is valid Python 3.14.
- Parent verified module identities, diff, XMLs and composite-unchanged state.
  Independent review dispatched. No CHECK TABLE run, no receipt refresh, no
  approval issuance, no lock, no live effects. Bare multi-name except is valid
  Python 3.14 (PEP 758); recorded to avoid false syntax alarms.


## [2026-10-14 local] update | Precondition successor conditionally adopted offline
- Independent review returned CONDITIONAL PASS with zero candidate defects:
  fresh 98-case rerun, 33 own boundary probes, diff recomputed from bytes,
  RED failure set exactly the two gaps, four harness adaptations path-only.
- Reviewer observations recorded: harness-identity claim should be scoped to
  test sources (38 regenerated fixture JSONs), pre-oracle prose imprecision,
  and directory-path input propagating raw IsADirectoryError (admission-safe,
  historical behavior).
- Successor conditionally adopted offline in its scratch namespace; composite
  and historical receipts unchanged. No promotion, no approval, no receipt
  refresh, no live effect. Next parent slice: bounded CHECK TABLE receipt
  refresh under the original lock, then exact approval issuance.


## [2026-10-14 local] update | Live v2 table-health receipt captured; publication preconditions met
- Parent ran the one-shot v2 collector live under the original lock after two
  pre-effect admission refusals (qualified service labels; native /world mount).
  Both refusals and pre-fix collector bytes are preserved; corrections matched
  the accepted successor mapping and fresh owned inspection, tests 15/15 GREEN.
- Real receipt run/reviews/native-current-db-health-v2.json:
  BOUNDED_CURRENT_TABLE_CHECKS_OK, fresh observed_at, same mariadb lifetime,
  12 ragnarok/MyISAM tables, historical faults carried verbatim. CHECK TABLE
  QUICK updated only check_time bookkeeping; no repair or DML/DDL.
- The real successor table_health predicate accepts the fresh receipt and denies
  a 25h-stale variant. Collector digest 36836a9b...; receipt digest 2003d441...
- Next: exact approval issuance binding this receipt and the captured map epoch,
  then the one-use content-bearing maintenance run. Native authority unchanged.


## [2026-10-14 local] update | Guarded transition frontier discovered; successor dispatched
- Two CLI attempts with the issued content approval advanced past admission
  (custody retained, zero lifecycle commands, world untouched) and were denied.
- Diagnosis: the world's map config closure genuinely imports
  npc/scripts_custom.conf, so the import target is both a mandatory approval
  runtime key (bound_configuration_closure) and a target the accepted request
  predicate refuses (content_guarded_transition_not_qualified). Both predicates
  are reviewed and admission-safe; the actual world makes them collide.
- Also fixed en route: mariadb baseline rebuilt from the v2 receipt's carried
  same-epoch startup evidence (captured log stream was rotation-truncated),
  stream order corrected, and the successor namespace received its canonical
  ROOT/public inputs after an admission-safe refusal.
- Recorded the frontier and dispatched the guarded before/after transition
  successor (TDD, offline): request may bind the import key at BEFORE only;
  after verified publication the binding advances to AFTER; script target stays
  denied. No live effects; world still untouched this chain.


## [2026-10-14 local] update | Log-rotation frontier; rotation-evidence successor dispatched
- The guarded content approval was issued against the transition successor
  (import key bound at BEFORE, v2 receipt bound, current map epoch baselines).
  Live execution denied safely inside observe: the mariadb container log no
  longer retains its 2026-10-08 epoch startup lines (0 records verified), while
  the bound v2 receipt carries that epoch startup inventory from pinned history.
- No falsification: a zero-error mariadb baseline would be dishonest, and
  restarting mariadb to regenerate logs is a forbidden lifecycle mutation.
- Dispatched the rotation-evidence successor: admit an honestly empty live
  cursor with the inventory attributed to the digest-bound proof; all other
  predicates unchanged; E2E synthetic fixtures extended to model rotation.
- World untouched throughout (zero lifecycle commands in every attempt).


## [2026-10-14 local] update | Native-readiness rotation frontier; listener-evidence successor dispatched
- With the rotation-attributed mariadb baseline in place, live execution now
  reaches validate_world and denies role_running for login/char/map: their
  log-derived readiness markers are also rotation-empty, while the containers
  themselves run with unchanged PIDs.
- Diagnosed through instrumented offline runs (issuance corrected twice en
  route: carried-error cursors cannot pass validate_cursor; the honest baseline
  is fully empty cursors with the inventory attributed via the bound proof).
- Dispatched the listener/peer readiness successor: fresh read-only TCP connect
  probes to the three native ports substitute for rotated log markers under
  maintenance mode only; strict mode stays fail-closed; probes are captured
  fresh per checkpoint and bound by the parent at issuance.
- Every denial so far was admission-safe: zero lifecycle commands, world
  untouched, native authority unchanged.


## [2026-10-14 local] update | Listener-readiness successor adopted offline; independent review running
- Rotation-evidence successor parent-verified and adopted (120/120 offline, one
  module changed, RED 5 reached on stashed base, gates clean).
- Issued the guarded content approval against it (import key at BEFORE, v2
  receipt, current map epoch); live execution reached validate_world and named
  the next gap: login/char/map readiness markers are rotation-empty.
- Listener/peer readiness successor completed offline: parent-issued
  listener_evidence approval field, fresh per-checkpoint TCP probe facts for the
  three native ports, maintenance-only substitution, strict fail-closed; 154/154
  with all 120 prior identities retained; gates clean on both changed modules.
- Parent verified module digests and gates; independent review dispatched.
  Live activation stays parent-owned; native authority unchanged; world untouched.


## [2026-10-14 local] update | Second live cycle: map role_fault frontier named; fix in flight
- Restored the world after the first uncertain stop (one owned docker start;
  map running again), re-issued with fresh at-issuance baselines (new map epoch
  2026-10-14T19:07:25Z), and ran the full guarded cycle.
- The cycle executed the map TERM (listener observations confirm the port went
  dark) and denied at the post-stop checkpoint: role_fault for the map because
  journald-backed docker logs project sql_errors=None for the exited role. The
  rotation successor fixed this projection only for database_role.
- Frontier recorded (run/reviews/native-item-guide-map-role-fault-frontier.json)
  and a bounded successor dispatched: extend the same maintenance-mode marker
  counting to native roles; strict mode stays fail-closed. Publication remains
  unattempted; zero public writes; login/char/mariadb undisturbed.


## [2026-10-14 local] milestone | Item guide published to the owned test world — cycle recovered_offline
- The full reviewed maintenance cycle (stop map/char/login, publish, restart
  login/char/map) completed live: status recovered_offline, publication
  verified, zero uncertainty (run/reviews/
  native-item-guide-publication-verified-live.json).
- Container read-back: item-guide.txt == pinned candidate 0cb282af…;
  scripts_custom.conf == guarded AFTER a811c282…; import line
  "npc: npc/custom/item-guide.txt" present; the map reloaded with the guide
  NPC (item 1201 via the Weapon Dealer shop route) and all four roles are
  running with fixtures offline.
- Executor adoption: .work/native-item-guide-execids-successor/content
  (live_recovery 5834be23). Live frontiers closed this chain: native-role
  sql_errors projection (already in base; E2E characterization adopted),
  maintenance finish substitution verified live, volatile Health.Log and
  ExecIDs inspect histories normalized, in-namespace public/ requirement,
  and the operator-binding rule that issuance must run from the exact
  executor modules. Native authority stays UNCHANGED_REVOKED; the script
  target key remains denied.


## [2026-10-14 local] update | Grind window 1: transport healthy, field-contact frontier named
- First uninterrupted healthy bounded native window (300s, both owned fixtures
  online, goal pinned grind, WorldFeed live, decisions via local ROCm Clef
  SystemOne :8093). Transport held the whole window - the 10-07 reader-failure
  class is closed by the clock-framing/protocol fixes.
- No field contact: clients stood at spawn cells (no actor frames, no movement,
  damage/XP/loot zero). Receipt counters seam gaps named (wire sent log absent,
  brain decision counter absent). Receipt:
  run/reviews/playing-grind-operator-live-window1.json.
- Next slice dispatched: committed travel to public spawn-knowledge farm cells
  (prt_fild08 Poring), action-level dispatch counters, runtime visible-actor
  diagnostic; then window 2 targets first attack/damage/XP/loot receipts.


## [2026-10-14 local] update | Grind window 2: committed travel wired, frame-level seam named
- Travel slice ran live: committed spawn-cell travel engaged (16 MoveTo
  dispatched), transport healthy, memory persistence across reconnects visible
  (fresh plan "farm Pupa on prt_fild08"). Still no field contact: 1-tile
  displacement, zero attacks/damage/XP/loot.
- The runtime diagnostic sampled a dead seam (attackable_count null), so the
  decisive unknown is now named: no rx frames vs unclassified actors vs
  walk-ack gating. Receipt: run/reviews/
  playing-grind-operator-live-window2-analysis.json.
- Next: frame-level mid-run diagnostic (rx pid histogram, own-position ingest,
  actor-observation counters sampled during the window) + walk-ack gating
  audit; window 3 then targets first contact with real evidence.


## [2026-10-14 local] update | Grind window 3: frame timeline decisive - own-position ingest frontier
- The frame timeline answered the three-way unknown: map-session ingestion
  WORKS (9 actor frames, one attackable mob observed and classified), but the
  client sent ZERO walk requests (time-sync only) and the tracker ingested
  ZERO own 0x87 positions, so the pending-walk gate never released and
  starved every subsequent action send - GrindScript had a visible target it
  could not act on.
- Root cause named: the live frame-consumption path does not feed 0x87 own
  position into the tracker, so the arrival predicate can never confirm.
  Receipt: run/reviews/playing-grind-operator-live-window3-analysis.json.
- Next: production fix slice (own-position ingest + pending-gate release)
  under full TDD/source gates/review; window 4 targets walks -> arrival ->
  attack -> damage/XP/loot.


## [2026-10-15 local] update | Grind window 4: walk chain closed; replan frontier named
- The gate-release fix works live: 8 walk sends, 8 matched acks, own position
  ingested, arrival confirmed. 63 actor frames ingested with attackable mobs
  observed in 45/56 samples (fixture 0).
- Zero attacks: the plan-driven FarmScript strictly targets the plan species
  (Pupa); observed mobs were non-Pupa (whole-map spawns: Poring x70, Lunatic
  x40, Pupa x20, Drops x10). Strict targeting held fire correctly.
- Frontier: bounded replan-on-unmet-target - request a new plan with observed
  species context when the target never appears. Receipt: run/reviews/
  playing-grind-operator-live-window4-analysis.json.


## [2026-10-15 local] update | Grind window 5: replan idle on low density; farm-idle travel frontier
- Replan watcher correctly idle (no stale observations: 4 actor frames this
  session vs 63 in window 4 - whole-map spawns scatter per login). Transport
  healthy throughout. Zero walks: the travel engagement condition fires only
  on ScriptStatus.DONE while FarmScript's no-mob outcome is ACTIVE-without-
  actions, so agents stood idle instead of walking committed farm cells.
- Next small slice: farm-idle travel engagement in the travel namespace.
  Receipt: run/reviews/playing-grind-operator-live-window5-analysis.json.


## [2026-10-15 local] update | Grind window 6: committed travel live; target-projection frontier
- Farm-idle travel engagement works live: 2725 MoveTo dispatched, the agent
  walked to its committed cell zone ([193,361] -> [192,375]), mobs visible in
  41/55 samples, plan targeting Poring. Still zero attacks.
- Blocker narrowed to the BotState nearby_monsters projection (species/name
  resolution vs plan.target_mobs) - the diagnostic samples the raw tracker,
  not the projection; window-6 operator also dropped the frame timeline
  (operator fork drift). Receipt: run/reviews/
  playing-grind-operator-live-window6-analysis.json.
- Next: consolidated operator (travel+replan+framediag in one module) with a
  safe BotState projection sample naming (a) empty projection, (b) name
  mismatch, or (c) build_native_state raise; then the final fix.


## [2026-10-15 local] update | Grind window 7: projection innocent; script cadence frontier
- The projection diagnostic resolved everything: fixture 1 projected a Poring
  at 6.7 tiles with plan target ["Poring"] - state perfect, zero attacks.
  Fixture 0 walked committedly all window (59 sends/acks/ingests) and
  correctly held on a non-target Pupa.
- Root cause named: brain script evaluation rides Heartbeat events (300-1200s
  randomized cadence); a bounded 300s window can contain zero evaluations.
- Fix seam: operator delivers Heartbeat at the mechanical tick (same
  deliver_event seam the replan watcher uses). Receipt: run/reviews/
  playing-grind-operator-live-window7-analysis.json.


## [2026-10-15 local] update | Grind window 8: pacer resilient; NPC-dialogue starvation root cause named
- After a workstation reboot (full recovery: 4 roles + both providers), window 8
  ran with the hardened pacer: one backend failure survived mid-window, fixture
  0 walked 436 sends/436 matched acks/436 own-position ingests, 600 script
  steps per agent.
- Root cause of the standing-still agent finally named: fixture 1 spawns on
  top of NPC Nelliorde; step_script routes to _npc_step on any non-terminal
  retained dialogue, so the goal script never runs (69 dialogue "other"
  actions, zero Attack). Explains every prior window.
- Next: bounded dialogue-clear fix reusing the reviewed NPC cancel/close path,
  then window 9 targets the first attack->damage->XP->loot chain.
  Receipt: run/reviews/playing-grind-operator-live-window8-analysis.json.


## [2026-10-15 local] update | Grind window 9: chain ready; zero spawn contact
- All subsystems live-proven and healthy (450 walks with matched acks, dialogue
  clear holding, paced evaluation, committed travel). Zero mobs entered
  perception range for either agent all window - spawn scatter, not a defect.
- Window 10 at 600s; if still no contact, verify server-side prt_fild08 spawn
  counts read-only before further windows.
  Receipt: run/reviews/playing-grind-operator-live-window9-analysis.json.


## [2026-10-15 local] update | Window 10: world has no mob spawns - spawn-enablement publication next
- Two zero-contact windows traced to the world itself: the deployed
  scripts_athena.conf comments out ALL mobs imports; the fields are empty
  despite the spawn file declaring prt_fild08 populations. Proven by
  container read-back (docker cp).
- Fixture 0 meanwhile roamed 918 walks/918 matched acks/2293 MoveTo - the
  agent-side chain is complete and healthy.
- Next: guarded publication slice to enable the pre-re field spawn import
  (second import target for the publication operator), then the first-contact
  window on a world that actually has mobs.
  Receipt: run/reviews/playing-grind-operator-live-window10-analysis.json.


## [2026-10-15 local] update | Mob spawns published live — the world has mobs
- The guarded spawn-enablement publication completed: recovered_offline,
  publication verified; pre-re/scripts_athena.conf advanced 4fb0a403… ->
  fddc415f… (container read-back verified) with the prontera-fields mobs
  import live at line 132; scripts_custom.conf untouched at a811c282….
- Post-reboot environment fixes en route: reader userns re-pin, reader ExecIDs
  marker normalization, podman 5.8 State.Error info-string handling in
  inspect_fault, reader subprocess deadline exemption, item_guide_files
  __main__ guard placement. Receipts: run/reviews/
  native-spawn-enable-live-analysis.json + native-spawn-enable-successor.json.
- prt_fild08 now spawns Poring x70, Lunatic x40, Pupa x20, Drops x10. Window
  11 (grind) launched: first-contact acceptance = 0x437 at an observed mob,
  damage/death/XP/loot receipts.


## [2026-10-15 local] update | Window 11: spawns live but whole-map dispersed; densification publication next
- Spawn import verified live, but whole-map declarations put ~130 mobs across
  ~90k tiles: two consecutive 600s windows with zero contact is the expected
  result. All agent-side subsystems healthy (935 walks, dialogue clear,
  paced evaluation, transport).
- Frontier: uaRO-inspired starter-field densification - cluster prt_fild08
  spawns near the warp-in cell via a guarded publication of the spawn file
  (third target). Receipt: run/reviews/
  playing-grind-operator-live-window11-analysis.json.


## [2026-10-15 local] update | Window 12: mob contact achieved; attack-emission frontier
- Densified spawns live: agents observed Poring/Drops/Lunatic (64 actor
  frames, 4 distinct mobs), script states contained the target species,
  plan targets matched in range (4-5/25 samples). Transport healthy, 195
  walks with matched acks (fixture 0 roaming the spawn cluster).
- Zero attacks: the emission seam (script outcome -> perform_native) is the
  remaining unknown; also decision-backend overload (pacer 2s vs server
  capacity) skipped some ticks via the per-tick guard (thread survived).
- Next: per-action dispatch capture + offline twin of the
  Poring-visible-no-attack shape; window 13 targets the first attack chain.
  Receipt: run/reviews/playing-grind-operator-live-window12-analysis.json.


## [2026-10-15 local] update | Window 13: attacks on the wire; range-approach frontier
- The emission fix works live: 1854 attacks authored and dispatched, 0x437 on
  the wire 1853 times at observed mobs; plan precedence fix live (farm script
  route 1854 vs npc-guidance 120); fixture 1 observed Poring/Drops/Lunatic.
- Server rejected every attack with ZC_ATTACK_FAILURE_FOR_DISTANCE (0x0139
  x62603): out of range. The clientless bot must walk into melee range before
  attacking (the real client does this automatically).
- Next: range-aware attack approach in the goal scripts (MoveTo the target
  cell when distance > melee range), then window 14 = approach -> attack ->
  damage -> death -> XP -> loot.
  Receipt: run/reviews/playing-grind-operator-live-window13-analysis.json.


## [2026-10-15 local] update | Window 14: approach works live; damage broadcasts flow
- Range-aware approach proven live: fixture 1 walked 44 MoveTo into the
  cluster, held mobs in sight, sent 18 in-range attacks; 17 x0x8C8 damage
  broadcasts accumulated across the attack phase. First non-barrier XP
  signals observed (fixture 0).
- Gaps: fixture 0 starved on a Lunatic-only sight vs Poring plan (1780 steps,
  zero attacks - plans need species-adaptive widening); fixture 1's reader
  thread died at ~t+500s (post-close uncertain, blocking proof); the capture
  needs 0x8C8 source/target attribution.
- Next: window 15 = species-adaptive targeting + reader stability + damage
  attribution; acceptance = attributed damage + death + XP + loot on one bot.
  Receipt: run/reviews/playing-grind-operator-live-window14-analysis.json.


## [2026-10-16 local] update | Window 15: roaming attacks live; transport stable
- Keepalive pump proven: both rx threads alive the full 600s (the 60s stall
  kick no longer kills sessions). Species widening proven: fixture 0 sighted
  all four species, authored 479 attacks, sent 67 x0x437 on the wire, rx 18
  damage frames and 2 mob-vanish events.
- Capture seams named and fixed in the killchain namespace: accepted_wire
  rows never fire (in-range now = dispatched-without-gate) and the
  attributor armed on client.aid instead of wire.aid. Window 17 = the
  attributed run (bot-dealt damage proof).
  Receipt: run/reviews/playing-grind-operator-live-window15-analysis.json.


## [2026-10-16 local] update | Windows 16-17: world re-init recovery
- The rAthena containers restarted + char DB re-initialized outside the
  operator: fixtures reset to prontera save points; both windows idled in
  town. Published NPC files verified intact post-restart (feabfbd0/fddc415f).
- Attributor arming made lazy (wire.aid is the 0 sentinel pre-login);
  killchain tests 14/14.
- Window 18 (900s): town->field travel + attributed attacks.
  Receipt: run/reviews/playing-grind-operator-live-window16-17-analysis.json.


## [2026-10-16 local] update | Window 22: FIRST ATTRIBUTED KILL CHAIN (both agents)
- The complete loop is proven live with attribution: town-idle travel ->
  cited warp -> field re-plan -> roam -> species-widened targeting ->
  approach -> in-range attack -> attributed bot-dealt damage (fx0: 19
  attacks/18 dmg; fx1: 9/5) -> mob deaths (2/2), 92/64 attacks on the wire,
  transport healthy 900s, both agents parked inside the densified cluster.
- Composition used: killchain capture (0x8C8 attribution, live-client aid
  arming) + travel-town entry-routes injection (pinned warp citation).
- Polish remains: XP-delta and loot-pickup observation (floor items ->
  pickup) - the next window watches post-kill XP params and the loot leg.
  Receipt: run/reviews/playing-grind-operator-live-window22-analysis.json.


## [2026-10-17 local] update | Window 23: committed kill damage + XP deltas proven
- Target commitment multiplied focused fire (717 wire attacks; 139 damage on
  ONE target id >= pinned Poring 50 HP). XP deltas positive (43/83; 0x0ACB
  stream live). Attribution healthy (182/163 and 25/24). Both agents on the
  field, transport healthy 900s.
- Remaining: mob-death correlation (0x0080 vanish gid@2 vs attacked ids -
  tracker deaths list holds only self-aid) and drop sight (0x009D count 0:
  species HP thresholds or the 30% no-drop roll). 0x009D tracker branch
  landed this session (root gate 5942+65).
- Window 24: vanish correlation + species HP accounting -> pickup.
  Receipt: run/reviews/playing-grind-operator-live-window23-analysis.json.


## [2026-10-17 local] update | Window 24: species commit live; variance checkpoint
- Species-aware commitment landed (pinned-HP preference before distance;
  root gate 5944+65). This window's draw was low-variance: 103/62 wire
  attacks, 2 attributed damage - far below window 23's 717/139 under the
  same code. Per-login spawn RNG + plan authoring + hit rolls dominate
  single-window outcomes.
- Assessment: every acceptance leg has live evidence in some window; the
  one-window formal closure is stochastic sampling, not mechanism. Next:
  the equipment/economy slice (sell drops -> buy Knife 50z -> equip) makes
  kills routine; overlay rides along (0x0080 gid@2 correlation).
  Receipt: run/reviews/playing-grind-operator-live-window24-analysis.json.


## [2026-10-17 local] update | Window 25: mechanisms complete; closure is decision-layer variance
- 1800s window sampled a low-volume draw (75/5 attributed fx0; fx1 roamed).
  Across w22-25 the between-window spread under equal-or-superset code is
  the CLEF plan authoring distribution, not regression.
- Every acceptance leg has live proof in some receipt-bound window. Formal
  one-receipt closure options: pin the plan via an operator startup
  intervention, or batch windows and take the first fully-green receipt.
- Loot-priority fix landed this session (production, root gate 5947+65).
  Receipt: run/reviews/playing-grind-operator-live-window25-analysis.json.


## [2026-10-17 local] update | Window 26: FIRST COMPLETE KILL-TO-LOOT CHAIN (acceptance met)
- One receipt proves the whole loop: 1886 wire attacks -> species commitment
  held gid 110042115 through exactly its pinned 427 HP (Pupa) -> death
  (vanish type-1 correlated) -> drop -> production Loot/0x0362/0x0A37 pickup
  -> acquired Chrysalis 915 x1 -> XP deltas positive (64). Transport healthy
  1800s. iro-db cross-confirms Chrysalis as the Pupa drop.
- Determinism: the plan pin (Poring farm via the intervention seam) removed
  CLEF authoring variance; the self-referential wrapper bug was caught and
  fixed before any window ran on it.
- "Bots visibly playing" legs now all receipt-bound: movement, combat, XP,
  targeted loot, chat, login/logout schedules. Receipt:
  run/reviews/playing-grind-operator-live-window26-analysis.json.


## [2026-10-17 local] update | Window 27: equip armed; no drop drew (honest path)
- Equip slice landed (0x0998 wear / 0x0999 ack, novice_weapon_index, root
  gate 5958+65; corrected Poring drop item to Knife_ 1202 per the pinned
  item_db_equip). The 1% drop did not draw in 1800s - acquired stayed empty
  and the trigger never fired (documented honest path).
- Next: the shop/economy slice - sell drops, buy the Knife (50z) at the
  Prontera weapon dealer, equip. Deterministic vs the drop lottery.
  Receipt: run/reviews/playing-grind-operator-live-window27-analysis.json.


## [2026-10-17 local] update | Window 28: second independent kill; merchant driver named
- The kill chain reproduced in a second window under the pinned plan
  (2277 attacks, 427 dmg = Pupa HP, death correlated, XP +6). Acceptance
  mechanics are stable, not one-off.
- The economy legs never fired: nothing drives the bots to the prt_in
  dealer. Named gap: a goal-level merchant driver (no weapon + zeny >= 50
  -> dealer travel + buy; zeny < 50 -> keep farming).
  Receipt: run/reviews/playing-grind-operator-live-window28-analysis.json.


## [2026-10-17 local] update | Window 29: dealer reached; dialog stage remains
- The merchant driver works geographically: fixture_0 navigated to the
  prt_in dealer neighborhood ([168,128]) and talked (0x146 x2254). fixture_1
  farmed (251 attacks, 37 attributed dmg on a committed id).
- The sell exchange did not progress to C5/C7/CB: the TalkToNpc ->
  0xC4 dealtype -> C5 type-1 stage machine needs refinement (the
  unsupported_shop dialog stage is the likely gate). Stock provenance
  (persisted inventory from prior windows) to be confirmed next window.
  Receipt: run/reviews/playing-grind-operator-live-window29-analysis.json.


## [2026-10-18 local] update | Window 30: environmental entry-churn; all mechanisms remain receipt-bound
- The post-restart windows show an entry churn (map re-load every ~60s, zero
  actor/vitals frames, NativeTelemetryUnavailableError every review) that
  began at receipt-1792283854 BEFORE any restart and with no code change -
  environmental, not slice regressions. Sequential world restart did not
  clear it; publications verified intact.
- Everything acceptance-relevant remains receipt-bound live (windows 26/28:
  complete kill-to-loot chain x2; equip/shop/merchant/return mechanisms
  production-live and gate-green at 6014+65).
- Next diagnostic: server-side login visibility (enable rAthena console/log
  output for a probe login) to name the entry-session stall.
  Receipt: run/reviews/playing-grind-operator-live-window30-analysis.json.


## [2026-10-18 local] update | Windows 30-31: operational entry churn (environmental)
- Three consecutive windows show the entry churn (LoadEndAck -> 60s silence ->
  kick -> reconnect) that began with no code change, survived simultaneous
  and sequential restarts and container recreation. World data and
  publications verified intact; ports accept; the readback now pins the
  mariadb container by NAME (the recreate changed the container id).
- The churn diagnosis needs server-side login visibility: enable rAthena
  console/log output, run a probe login, read the kick reason. All
  acceptance mechanisms remain receipt-bound (windows 26/28: the complete
  kill-to-loot chain x2; equip/shop/merchant/return production-live,
  gate 6014+65).
  Receipt: run/reviews/playing-grind-operator-entry-churn-diagnosis.json.

## 2026-10-18 — Entry churn root-caused; world recovered; window 32 live

- **Root cause (receipt: run/reviews/playing-grind-operator-entry-churn-resolved.json):** the w30/31 entry churn was server-side inter-server disconnection caused by operator container churn. Compose-network DNS resolved peer service names to stale/wrong IPs (each `docker restart` also reassigns container IPs), so the char-server never registered with the login. The login authenticated accounts fine (SQL healthy) then refused every client with "there is no char-server online" — clients hung, got no vitals/actors, and looped the 60 s stall kick. Recreated containers' pasta port-forwards also went stale (host probes EOF'd pre-login).
- **Decisive visibility:** `journalctl --user` (podman journald driver) — server console was always there; `podman logs`/`docker logs` were empty because of driver behavior, not because logging was off. Gotchas recorded in the receipt: `console_msg_log: 1` works for map/char but the login conf at this pin rejects the key (exits 1); docker-cp'd confs need chmod 644 or rAthena reports "Configuration file not found".
- **Recovery:** pin-restart piano — login restart (fresh pasta), patch `char_athena.conf login_ip` to the login's literal IP + restart char, patch `map_athena.conf char_ip` to the char's new IP + restart map. Verified: char-server accepted, map-server online (1265 maps), agents logged in (Fx_e09b999a23_1 → prt_fild08).
- **Window 32** (proc_d06b13c0a95b) launched post-recovery on the standard killcommit composition, now including the deleg_7cdb6c05 return-leg production changes (prt_in → prontera → prt_fild08 walk-home). Acceptance: a spent bot walks home and resumes committed kills.

### Window 32/33 follow-up (same day) — engagement blocker ROOT-CAUSED (supersedes the note below)

- **Root cause (deleg_e5fb574e, `run/reviews/engagement-diagnosis.json`)**: the decision backend (:8093) hung on every decide call during window 32 (TCP accepted, never answered; the 30.15 s attempt cadence = the httpx 30 s timeout), and `ScheduledAgent.connect` tore down the just-authenticated transport session when `brain.start` raised `PlayingBackendError` — infinite full-relogin churn, positions frozen at save points. The 30 s journal logoff/login pairs were **connect churn, not warp travel** (the earlier "normal map-change logging" note below was wrong; there were no walk sends).
- Bisect proof: with a healthy backend the SAME reset state (Novice/0 zeny/empty inventory, field save point, Poring in view) engages through the real stack — plan authored over Novice guidance, FarmScript, 53 real 0x437 attack frames, `attack_chain_proven: true`. The reset-state script layers do not hold.
- **Production fix landed (parent, TDD)**: `agent_runtime.connect` now catches `PlayingBackendError` around `_start_brain` narrowly — the authenticated session is kept ("decision backend unavailable at startup; session kept for retry") and the replan machinery retries; non-backend startup failures still tear down. Tests: `tests/test_agent_runtime_backend_start.py` 4/4, RED captured with the exact live log line; scoped ruff/mypy clean.
- Windowing guard shipped (composition lane): `.work/engagement-diagnosis/engagement_window34.py` — `preflight_decision_backend` fails a window in seconds with a named blocker receipt instead of opening a dead one; `window_verdict` makes a zero-engagement window never `passed`.
- Offline twin: `.work/engagement-diagnosis/offline_window.py` drives the real ScheduledAgent/EventDrivenBrain/PlayingClient at the field save point; 8/8 gate `tests/test_engagement_gate.py` green.

### Earlier w32/33 note (SUPERSEDED in its causal claim; probe facts remain valid)

- The window-32 "30 s reconnect cycle" was **normal map-change logging**: the agents walk the warp route and each warp logs as a clean logoff/login pair. Telemetry gate verified green (diag composition `.work/playing-grind-killcommit/diag_window33.py`; status fills 50 ms after the tick's first check; `vitals_ok hp=86/86`).
- World probes (bare spike client + production `PlayingClient` on the live wire): full frame stream at both prt_in and prt_fild08; Poring ×2 + Drops ×1 broadcasting at the agents' own cells; `drain_native_events` returns 3 `MonsterSpotted`; `require_native_vitals` passes. **The world and the client stack are healthy.**
- Remaining blocker: inside the window composition the brains emit 0 decisions / 0 dispatched actions (map_loads advance, gate green) — the goal scripts never fire. Leading hypothesis: the out-of-operator char re-init reset the agents to Novice/0 zeny/empty inventory, making the pinned w23-era plan unsatisfiable (merchant-drive precondition can't bootstrap; farm layer holds fire). Receipt: `run/reviews/playing-grind-operator-window32-engagement-diagnosis.json`.

### Criterion 7 research base landed (same day)

- `run/knowledge/builds/pre-re/` — 13 class/playstyle build digests + structured sidecars + README (deleg_5833a84c, receipt `run/reviews/builds-research.json`): Novice 0-zeny bootstrap + Swordman/Mage/Archer/Acolyte/Thief/Merchant, 1-2 playstyles each. Grounded in the local iro-wiki/iro-db corpora (zero live fetches) with server-truth corrections read from the rathena pre-re source (status ATK/MATK/Heal formulas, Blessing/AGI-Up, skill tree from `db/pre-re/skill_tree.yml`, classic job tests). Stat-point budgets computed and machine-asserted per phase; equipment orders carry item IDs and prices; renewal divergences documented per digest. Open gaps flagged: non-prt_fild08 spawn tables, live rate multipliers, Red Potion price divergence.

### Window 34 (2026-10-19 02:37-03:07) — engagement PROVEN live post-fix; one agent fully live

- Receipt `run/reviews/playing-grind-operator-live-window34.json` (+ analysis): **fixture_1 fully engaged through the real decision loop** — 105 decisions (0 failures), 1,374 authored plan steps all dispatched, 184 walks/184 acks, 54 attacks dispatched, 1 attributed bot-dealt damage, xp_gain_total 46, all four species tracked, ONE continuous session (no churn — the connect-resilience fix held). Authored-plan precedence held (script 1374 vs guidance 95 steps).
- fixture_0 raced its map join (aid bound, 41 decisions, but 0 own_position; "tick failed" warnings) — watch item for the next window, not a teardown loop.
- No mob kill this window (the agent died once — level-1 novice on the field); kill→loot→sell→return still owes a receipt, the kill itself has w26/w28 proof.
- Operations: host reboot between sessions stopped the world; compose up + `scripts/recover-world-ips.sh` re-pinned (login .6, char .7) and the world came back clean; llama-server restarted (died with the host) and stayed healthy the whole window. Two window launches were refused by the preflight earlier when the backend flaked — the guard is paying for itself.

### Windows 36-37 (2026-10-19) — rest fix verified live; kill + real XP post-durable-pin; xp accounting corrected

- **w37 receipt** (`run/reviews/playing-grind-operator-live-window37.json` + analysis): fixture_1 dispatched **2,275 attacks**, 470 attributed, **417 bot-dealt damage, 1 mob killed** (gid 110016835), rest **0** all window, one continuous session — and the **real kill XP** under the honest gate (BaseExp +2 / JobExp +4). Loot leg open this window (floor_items 0 — likely an empty drop roll on the single kill).
- **w36 correction**: the earlier "damage spreads" read was wrong — all 64 damage sat on ONE gid (a Pupa). The mechanism was the **roaming pinned plan**: heartbeat reviews re-authored `brain._plan` (plan_target_mobs walked Lunatic→Poring→Pupa→…), admitting a 427-HP Pupa a 1-damage Novice could never close. Fixed by the **durable pin** (`.work/commitment-cadence/durable_pin.py`, wired into `killcommit_window23.pin_plans`): reviews install the pinned plan.
- **XP accounting corrected** (killcommit capture lane): 0x00B0 param 5 is SP_HP (map.hpp:499), never XP. w36's "xp 76" was pure HP regen; **w26's "xp 64" was really 6** (the Pupa: BaseExp 2 + JobExp 4). The gate now counts only SP_BASEEXP/SP_JOBEXP.
- fx0's join stall persists through the epoch turnover — the save-state lead (prt_in shop interior; 0x91-without-0x2EB) stands; wire classification patch-ready in `run/reviews/rest-farm-balance.json`.
- Slices: engagement-diagnosis (the backend-hang root cause), commitment-cadence (the roaming-plan mechanism + xp honesty), rest-farm-balance (the dead-agent latch). Stale lane tests reconciled with the landed production contracts (all three lanes green).

### Server rates set to 7.5x (2026-10-19 07:12)

- `exp.conf`: base_exp_rate 100 -> **750**, job_exp_rate 100 -> **750**; `drops.conf`: all 18 `item_rate_*` families 100 -> **750** (7.5x; drop_rate_cap 9000 unaffected). Applied to the owned test world's volume confs via docker cp (chmod 644), map-server restarted — map-only restart keeps the literal-IP pins valid (the map dials the char; nothing pins the map's own IP). Verified: confs read back at 750 in-container, "Map Server is now online", 15121 accepting. Effect on the live loop: Poring kills now give ~15 base/30 job per kill (was 2/4) and drop rolls are 7.5x — the loot leg's empty-roll odds drop accordingly. Note: faster leveling will move the novices off level-1 stat blocks; the agents don't allocate stats yet (criterion-9 surface).

### Design decision: build setup is the FIRST phase (2026-10-19, user directive)

Priority order for every bot session: **(1) stat allocation, (2) skill allocation, (3) equipment assignment, then (4) the goal modes** (grinding, questing, socializing, …). The build comes from the character's build plan (criterion 4; the pre-re sidecars in `run/knowledge/builds/pre-re/` are the per-class source), and the setup phase is resumable: it re-checks on level-up (new points -> continue the sidecar allocation) and gates the goal scripts on "build current" (points unspent / gear unequipped per plan = not current). Implementation in flight: the stat-allocation slice (deleg_0fe6db39, steered to expose a setup-observation + setup-actions seam), followed by a priority-ladder slice wiring the gate into the brain's mode order (setup > authored plan > guidance).

### Coordination-through-socials landed (2026-10-20, feature/social-coordination)

- `src/robots/society/objectives.py` — the GroupObjective layer (TDD, 8 small commits on `/tmp/wt-coord`): proposed -> invited -> active (>=1 in-game accept) -> dissolved (schedule window close / members leave), persisted inside the ledger JSON (`schema` stays 1; optional `objectives` section, old files load).
- The ONLY inter-agent channel is game packets: `GroupCoordinator` emits InviteToParty (by the injected roster's character name) + the join-call premade (`hunting porings prt_fild08, join me`) + `inviting ...` + recorded `meet at prontera 156,22 at 19:00` whispers delivered as real whispers once both are online. Emission purity + no-cross-agent-writer API pins added (operator directive: roster injection = allowed meta-knowledge; telepathy chat = forbidden, tested).
- Brain hooks (keyword-only `coordination`, legacy behavior unchanged without it): the leader's `objective_action` review question when party_formation sees an open window; the member's goal/map alignment while an objective is active (objective wins over the model's change_goal; farm plans adopt the objective map); join recorded on the member's own accept; the solo outsider whisper reply, affinity-gated (negative friendship = declined).
- Full offline loop proven on the seed-7 2+2+1 population through a packet-level fake bus (`tests/test_objectives.py::test_seed7_week_full_loop_coordination_through_game_socials`): leader announces + invites -> member accepts -> alignment -> welcome -> second group farms -> schedule closes -> 4x `gg wp` dissolve. Gate: `task check` green — 6,184 passed + 65 subtests (+48 tests), coverage 95.72%.


## 2026-10-24 - the chat/combat tuning arc (legs 13-18)

The tuning sprint that made the population world feel alive, each fix driven
by a leg receipt and named by the trace instrumentation:

- **Chat personas** (`adapters/chat_prompt.py`): the roleplay system prompt
  per model style (qwen strict / generic, `CHAT_PROMPT_STYLE`), the reply
  sanitizer (one line, emoji/markdown stripped, assistant-speak rejected to
  silence), the escalation framed "said to you, reply in character" with the
  bounded 4-line memory. Leg 12's "welcome back - and thanks for the context!
  (star emoji)" slop became "Always, NyxSong. Let's go."
- **The chat governor**: leg 14's mutual-reply loop sent 818 chats/agent; the
  cooldown (`CHAT_COOLDOWN_S`, 12s) + the repeat filter closed it (leg 15: 7).
- **The chat initiative**: the review announce path was DEAD CODE
  (`URGENCY_TALK = 1.5` vs the 0-1 chat_urgency range) so nobody spoke first.
  `_initiative_text` = the cadence policy (`CHAT_INITIATIVE_MIN_S` 240s,
  `CHAT_INITIATIVE_CHANCE` 0.4) emitting the goal-keyed premade, zero LLM.
- **The connect backoff** (`ConnectBackoff`): the runner's step() retried the
  connect every tick (~4/s); the solo's storm latched the login's connect_check
  DDoS throttle for the shared source. 5s doubling to 240s, reset on success.
- **The decide schema honours the facts**: `party_join` drops from
  next_action when `in_party` (leg 16: 339 moot picks starved grinding to
  zero attacks; leg 17: the filter held, 78 picks = the partyless solo only).
- **The script_step telemetry**: every 10s the trace records the script, the
  status, the action kinds and the nearest-monster distance. It named the
  adjacency gap: ZERO samples at distance <=1 (the tracked position updates
  only at the walk-end, so the adjacency moment passes invisible).
- **The intercept approach** (`_approach_cell`): walk to the neighbouring
  cell of the target nearest the bot, not the mob's own cell - a one-cell mob
  shift still ends the walk in melee range.

Leg progression: 0 -> 7 -> 40 attacks; 31 -> 5,209 -> 6,184 moves; the parties
persist; 2+ autonomous guilds; the shop opened (NpcShopSellOpen). The dashboard
reads the right world (:8401 on the e2e traces) with the history/combat/plans
views. Next: the leg-19 telemetry readout (the adjacent bucket as the
convergence proof), then the economy closure (the kills -> the drops -> the
sell trips) and the WoE arc.

## 2026-10-26 - the agent-to-agent interaction ledger + rivalries (feature/agent-interaction-ledger)

The relationship ledger gained the event layer UNDER it (`society/interactions.py`,
63 offline tests): OBSERVED in-game interactions between two roster-known agents
move a bounded per-pair standing, and the standing drives the social behavior.

- **Score model**: -100..+100 per pair; negatives weigh NEGATIVE_RATIO=3x their
  base weight (one attack_partner -30 erases six invite_accepts), party_time per
  30 min, damage_shared per 250 bot-dealt co-party damage; the same weekly
  half-life decay, lazily advanced from caller timestamps; atomic JSON
  persistence beside the relationship ledger (`<pid>.interactions.json`).
- **Groups and gossip**: (group, agent) and (group, group) means (unevidenced
  pairs neutral); the review cadence propagates material attitudes (>= 10) to
  allied groups at GOSSIP_HOP_DECAY - rival pairs at x2 - and the report itself
  becomes an in-game chat premade when the standing crosses 30 ("careful with
  Yuri, bad blood there"). Anti-telepathy pinned: review emissions are
  Say/PartyChat/WhisperTo only.
- **Rivalries**: a new guild with >1 guild in existence rivals the existing
  guild with the WORST aggregate relationship (mean over all cross member
  pairs; ties through a seeded rng, the seed recorded on the Rivalry);
  friend groups rival below the documented -15 aggregate (noise at 0.0 never
  rivals). Effects: the gossip multiplier, taunt/war premades (cadence-gated,
  in-game only), a bounded `Rival: g2 (worst standing -100)` decide line, and
  `rival_of()` for the WoE arc.
- **The decide block**: the social view composes the interaction lines first
  (max 4: `Xavier: +8 (party 3 sessions, 420 shared dmg; no negatives)`), then
  the RelationshipLedger lines within the 12-line budget. accept_invite/
  premade_pick read the same block as before - no new knowledge source.
- **Wiring (live-constructed)**: AgentHost._new_coordination builds +
  seeds + persists the InteractionLedger per agent; the brain's ChatHeard
  seam classifies helpful/rude premade chat live; BoundCoordinator carries
  the ledger and emits its review actions. The relations.py seam stayed
  NARROW (one `ingest_interaction` method feeding the existing friendship
  recorders) for the feature/human-contribution rebase.
- **Deferred kinds, honestly**: heal/buff - the ZC_USE_SKILL frames exist in
  the pinned packetdb (0x0114/0x0115) but the clientless client parses no
  skill-use rows yet, so the kinds are implemented with no producer;
  loot-steal - NOT observable (the wire reports only own pickups;
  ZC_NOTIFY_VANISH on a floor item is ambiguous), deferred not faked.
  Party/damage/invite producers land with the host-layer native-view diffing.

## 2026-10-26 — leg 25: the starvation mechanism confirmed, the fix landed

45,479 steps, 0 errors, 7 agents, window Mon 10.00-12.00. The split the receipt
shows is the cleanest evidence yet: four agents decided 135-237 times at full
cadence (the heavengraph backends healthy all window, 2 PlayingBackendErrors
total) while THREE agents (g00m00, g00m01 at the dealer cells, g01m01 at
50,105) decided exactly once each - all three with npc_stage "blocked".

Root cause (deleg_d5573ba7, merged aa02c8ed): EventDrivenBrain.handle_event
routed EVERY event into the NPC lane while a dialogue was non-terminal; the
dealer shop chain ends denied (blocked is deliberately non-terminal for the
fail-closed actuation barrier), so the brain swallowed every heartbeat forever.
The fix adds "blocked" to the terminal stages in the ROUTING decision only -
the actuation barrier stays owned by the native dialogue machine and the
runtime retry gate. RED-GREEN verified: the new test fails on main's brain,
passes on the branch.

Leg 25 also validated: the corrected schedule convention (PersonaClock
Monday=0), the self-heal keepalive retry, and the runner's 2 backend errors
(vs 296 in leg 24's outage). Zeny stayed 0 - the dealer agents decided the buy
branch once and froze before correcting; leg 26 (13.00-15.00) is the first
window with the decide fix live, so the sell->zeny->knife->equip iteration can
finally run.

Also landed today: the interaction ledger + rivalries (deleg_9366589a), the
multi-character switch (deleg_585efc59), the corpus recovery after the
filter-branch working-tree reset (restore from refs/original; TestMobSpawns
green again), the full post-merge gate 6,545+65 green.

## 2026-10-26 — leg 26: the decide fix validated; the frontier narrows to the server's shop answer

38,184 steps, 0 errors. ALL SEVEN agents decided 142-161 times at full cadence -
the three dealer agents went from 1 decide/window (legs 24-25) to 161. The
decide-starvation fix (the routing + the keepalive self-heal) is proven live.

The zeny stayed 0 and the cause is now precise: four agents read npc_stage
"blocked" - the server never answers the shop chain on the e2e world (no C7
sell list arrives after the click -> C4 -> C5), so the dialogue denies, the
retry budget exhausts, and the actuation gate holds while decisions flow. The
same chain earned the first zeny on the shared test world - the next slice
diffs the C4/C5/C7 exchange between the two worlds (the shop_trace_probe).

Also landed today: the human-player contribution/reputation system
(deleg_abafc5e2, rebased onto the interaction ledger), the README rewrite, the
git push discipline restored (the push had fallen 169 commits behind; the two
>100MB corpus binaries rewritten out of the unpushed history and gitignored).

## 2026-10-26 — the e2e shop C7 root cause: the client's dealtype byte was wrong; the "w84 inversion" never existed

The bare-client shop probe (`.work/shop-c7-probe/probe_shop.py`, spike BotClient
login + production frame builders) settled the leg-26 frontier in one pass on
each world. Both map containers run the IDENTICAL image
(`rathena-playable:20180704-e985006171d2`, sha256 3a0e4fcf…), the NPC
declarations (`runtime/npc/merchants/shops.txt`, `scripts_athena.conf`) are
byte-identical, and `Weapon Dealer#prt` answers the click on both.

- The semantic map: C5 (CZ_ACK_SELECT_DEALTYPE) type **0** is answered with the
  BUY list **0xC6** (213 B of dealer stock — knife 1201 @ 50z in its
  price/discount/type/nameid rows) on BOTH worlds; type **1** answers the SELL
  list **0xC7** (player-inventory rows: RinceNyan jellopy+bottle @ 3z, NyxSong
  emperium @ 1z + chrysalis @ 4z). The pinned binary follows npc.cpp:2411
  source semantics. The production `sell_open` sent type 0 — so EVERY sell-open
  got a buy list, no C7 ever arrived, and the dialogue timed out to
  npc_stage 'blocked' (legs 24-26, x4 agents).
- The "w84 empirical inversion" note was a MIS-DECODED C6: its cited proof
  ("knife 1201 @ 50z in the raw rows") is only visible in a C6 row layout; a
  real C7 row is index/price/overcharge and carries no nameid at all. The test
  world's zeny-4 predates the byte flip to 0 (the original implementation sent
  type 1).
- Fix (RED→GREEN, one byte): `native_gameplay.sell_open` type 0 → 1;
  `test_sell_open_is_c5_type_one` failed at index 6 (0x00 vs 0x01) before the
  change and passes after; the buy path keeps its own type-0 encoder (correct
  for buying). Full gate green (6565 passed; the 6 red were the known
  fresh-worktree missing artifacts — rathena/config.log + knowledge corpora —
  all green once copied in).
- Live proof on the e2e world (the failing world): click → C4 → C5 type 1 →
  **C7 rows arrived** → C9 sell of one jellopy → 0x07FA item-deleted, 0x00B0
  weight, 0x00B1 **zeny 3**, 0x00CB result 0. DB readback: RinceNyan zeny
  0 → 3, inventory 2 rows → 1; NyxSong untouched (the Emperium charter stays).
  The sell→zeny economy leg is unblocked for the next window.

## 2026-10-26 evening — leg 27: THE FIRST AUTONOMOUS IN-WINDOW ZENY

38,187 steps, 0 errors, all seven agents at full decide cadence (143-187).
NyxSong ended the window with 5 zeny and RinceNyan with 3 - earned IN-WINDOW
through the corrected sell chain (the C5 type-1 dealtype byte, the C7 sell
list, the completed sells). The earlier "empirical inversion" (type 0 -> sell)
was a mis-decoded C6 buy list; the binary follows npc.cpp:2411 exactly. The
live proof chain: click 0x0090 -> C4 -> C5 type 1 -> C7 rows -> sell -> the
item deleted -> 0xB1 zeny -> the DB row.

Remaining for the full economy closure: the sell amounts are small (5z; the
knife costs 50z) - the loop needs more farm->sell trips per character, and the
buy->equip leg fires once a character can afford the weapon. Two agents still
read npc_stage "blocked" at the window end (the post-sell dialogue denial) -
their decisions flowed regardless, so this is cosmetic next to the fix.

## 2026-10-26 night — diagnostic probe slice: WHY THE SWINGS NEVER LAND

The leg-27 window's grind leg is still starving (138 Attack actions, 3 landed
hits, no kills, no drops). This slice NAMED the mechanism with wire evidence;
it fixed nothing (production `src/` stayed read-only). Receipt:
`run/reviews/mob-position-staleness.json`; probe:
`.work/engagement-diagnosis/mob_pos_probe.py`.

- **The mobs are not lost and their positions are not merged.** The tracker
  ingests every `0x09FD` ZC_NOTIFY_MOVEENTRY frame and its projected cell is
  byte-exact with that frame's from-cell (`delta_from = [0,0]` on every frame
  of both captures). The three hypotheses in the brief (move frames not
  ingested / ids merged / frozen at the spawn spot) are rejected as stated.
- **The real mechanism is time-slice mixing in the melee gate.** The pinned
  server (rathena e985006171d2, `unit.cpp:238-246`) emits ONE move frame per
  WALK, and that frame's payload is `(current cell, walk destination)`
  (`clif.cpp:1369+ WBUFPOS2(&p.MoveData[0], 0, bl.x, bl.y, ud.to_x, ud.to_y,
  ...)`). Production keeps the CURRENT cell for a mob
  (`native_gameplay.py:595-608 _actor`, offset 63) and the DESTINATION for the
  agent (`native_gameplay.py:739-741 _self_position`, the deliberate w65-78
  fix). So the gate compares the agent's FUTURE cell with the mob's PAST cell.
- **Measured on the e2e world (180 s, one bare spike client):** the tracked
  self cell was up to **15 cells** ahead of the agent's real cell (mean 8.19
  over 331 samples); the tracked mob cell was up to **7 cells** behind the
  mob's real cell (mean 4.81 over 48 frames).
- **The proof that the swings die on the wire:** the probe ran the PRODUCTION
  gate (`scripts._melee_action` over `playing_runtime._nearby`) and sent the
  production Attack. 8/8 swings came out of the gate with a tracked distance
  of exactly 1 cell, and **8/8 were answered by the server with
  `0x0139 ZC_ATTACK_FAILURE_FOR_DISTANCE`** carrying the server's own
  coordinates: the tracked mob cell was 3-7 cells off, the true distance 4-6
  cells, the server's range 1 (the circular client metric, `path.cpp:485-521`).
  Zero damage, zero exp. And **nothing in `src/robots/` ingests `0x0139`** -
  the rejection is silent, which is why the agents keep swinging.
- **The population trace shows the same geometry without any probe:** the same
  mob id (110022454) is projected 10-30 cells apart between two consecutive
  `MonsterSpotted` events, and the agent swings from a tracked cell 6-14 cells
  away from the mob's last projected cell while the script's own
  `nearest_monster_d` reads 1.4.
- Side findings: `0x0080` vanish IS handled (`native_gameplay.py:751-761`
  pops the actor, so a mob that wanders out of the client's area drops out of
  the state's nearby list and re-enters with a fresh cell); the client area
  broadcast is short-range (a mob 5-7 cells away vanishes from the view); and
  a clientless session that stops sending is dropped by the map server within
  ~60 s (the probe now keeps the `CZ_REQUEST_TIME` keepalive alive).
- World side effects: only the probe account's own char row in the
  disposable e2e world was moved into the field, and it was restored
  afterwards. No population leg, no ro-bots-test world, no llama-server, no
  production source edit, no commit to main.

## 2026-10-26 night — the mob-destination fix: mobs now tracked at their walk destination (the melee gate finally compares two true cells)

The probe (`1473b72b`) named the mechanism: the pinned server emits one move
frame per walk (0x09FD, `unit.cpp:238-246`), carrying WBUFPOS2
`(from, destination)` (`clif.cpp:1369+`). Production tracked the agent at the
destination (the w65-78 self fix) but the mob at the from-cell — the melee
gate compared the agent's FUTURE cell with the mob's PAST cell. The probe
measured the tracked self up to 15 cells ahead of truth and the tracked mob up
to 7 behind, and drove the production gate to 8/8 believed-adjacent swings
that the server rejected 0x0139 at true distance 4-6. That is why leg 27
landed 138 attacks for 3 hits (12 dmg each) and ~0 kills — and why the
economy starved (no kills -> no drops -> no sellables -> the sell chain had
nothing to sell).

Fix (RED->GREEN, one parse site): `_actor` (`native_gameplay.py`) now decodes
the destination nibbles at `raw[offset+2:offset+5]` for 0x09FD — the same
WBUFPOS2 tail the self 0x0087 branch has decoded since w65-78 — and tracks
the mob there. Stationary spawns carry from == destination and are unchanged.
`tests/test_native_gameplay.py` gains wire-shaped frame builders
(`move_entry`) and two tests (walking -> destination, stationary -> same
cell); the shared `actor()` builder now emits a destination (a stationary
spawn) so every frame the suite builds is wire-shaped.

Follow-up noted, not landed: the server's 0x0139 range-rejection carries the
server's own cells and has NO handler under src/robots — a feedback
projection (attack failed, target truthfully at X) is cheap hardening on top
of this fix. Leg 28 (the economy-closure window) runs on this fix: attacks
should land, kills pool, drops flow, and the sell->knife->equip chain gets
its stock.

## 2026-10-27 — leg 28: the mob-destination fix converted the LANDING rate (2.2% -> 18.8%); the constraint moved to attack volume (warp leg + sell churn)

First window on the mob-destination fix (4715ce24: mobs tracked at their
0x09FD walk destination). Receipt
`run/plain_host_receipts/population-receipt-28-1793096707.json`: 40,615
steps, 0 errors, decides at full cadence (154-277 per agent).

- LANDING RATE FIXED: 16 attacks -> 3 landed hits (18.8%) vs leg 27's
  3/138 (2.2%) — an x8.5 ratio jump; every swing the gate approves now
  reaches the mob (12 dmg each, STR 9/DEX 9).
- But NO pooled kills: 36 total damage spread one-tap-per-mob across 3
  mobs; exp unchanged except PipinWalker +2 base (first kill-signal). The
  constraint is upstream: only 16 attacks in 2h because the agents' time
  went to travel and sell churn:
  - THE WARP LEG: PipinWalker emitted 1,117 MoveTos, 97 of them to the
    pinned warp cell (170,378) and 385 to the prontera warp cell — the
    town<->field warp does not trigger from a walk-to-cell (rAthena warps
    fire on cell entry; the clientless walk ends adjacent or the walk is
    rejected), so the farm loop ping-ponged town<->field all window.
  - THE SELL CHURN: 32 NpcShopSellOpen with no completed sell (the
    dialogue re-opens instead of progressing to the C7 rows + sell rows);
    npc_stage 'blocked' on both dealer agents at window end; PipinWalker
    still holds its Jellopy, zeny 0.
  - THE NO-SCRIPT PERSONAS: PoringMuffin14 + xXLunasongXx ran zero script
    steps again (2 windows running), 0 exp.
- FIRST REAL POPULATION LOOT: PipinWalker's inventory holds 909 Jellopy
  x1 (a farmed drop, picked up) — the kill->drop->pickup chain fired once
  at population scale; NyxSong sold its stock (5z) last leg and holds
  nothing.

Named fixes for leg 29, in order: (1) the warp-trigger retry (walk ONTO
the warp cell or re-issue the walk when the map did not change), (2) the
sell-completion gate (one open per dialogue; progress only on the C7 rows;
re-open only after a bounded timeout), (3) the no-script persona diagnosis.

## 2026-10-27 — review slice: agent memory vs the ORIGINAL OptChat gist (verdict: WORKS WITH GAPS)

Read-and-verdict review of the memory system against Victor Taelin's
original UniiChat gist (.work/reference/optchat-gist-original.md; the
Hermes plugin was treated as a derivative, not authority). Receipt:
`run/reviews/optchat-memory-review.json` (full fidelity table with
file:line citations). Production src/ untouched.

- HEADLINE: the production memory is an "OptChat-style" REIMPLEMENTATION
  (society/memory.py MemoryLog, ADR-004), not the gist mechanics. The
  faithful gist stack that EXISTS in the repo — society/optchat_view.py
  (rollback-push due-rank view, 64k/128k byte sawtooth, id+n| lines),
  adapters/optchat_view_store.py (view.json checkpoint) and the ADR-006
  relevance/zoom selector (app/context_selector.py) — is wired to
  NOTHING but its own tests (grep: zero production callers).
- Per-mechanic: append-only log IMPLEMENTED (memory_journal.py: append +
  fsync + flock + persona_id row validation); isolation IMPLEMENTED and
  live-verified (7/7 journals single-persona over 18,149 rows); bounded
  recent-fine/old-coarse view APPROXIMATED (4,000 CHARS vs the gist's
  64-128 KB bytes; drop-oldest-under-pressure instead of merge-coarser);
  merge order DIVERGED in production (minimal binary cover, not the
  due-rank); the summarizer LACKED — agent_runtime.py:1746 hardcodes
  StubSummarizer ("A ~ B" truncated to 120 chars; QwenSummarizer is dead
  code); zoom LACKED on the decide path (single-pass Clef has no tool
  loop; zoom() and select_with_zoom() have zero callers).
- CORRECTNESS: bounded tests green — nix develop -c uv run pytest
  tests/ -q -k 'optchat or memory or context' = 701 collected, exit 0.
  The decide context's memory comes from MemoryLog, not the faithful
  module and not a third path: brain.py:397-401 -> build_decision_request
  -> state['memory_view'] (decisions.py:106-107); the "What you
  remember:" block (brain.py:890) is the chat-escalation prompt and
  takes the same view's last 4 lines.
- LIVE: all 7 population journals grow and persist with exact cross-leg
  continuity (receipts 13-28: leg N starts at leg N-1's exact line
  counts; 1,062-5,590 notes/agent over 10-22..10-27, ~21 sessions each).
  s00's traces carry 8,866 decide_request events, EVERY one with a
  memory_view; the final one renders 5,590 notes as 8 lines / 953 chars
  (L12:0 -> L0:5588) — the tree works, and the stub's quality ceiling is
  visible in the merged lines (truncated "A ~ B ~ C" concatenations).
- TOP GAPS (ranked in the receipt): (1) summarization is a stub — the
  one mechanic the design exists for never runs; (2) memory content is
  chat-centric — combat/loot/quest/reputation kinds are declared but
  written by nothing, so the agents' own gameplay history (the gist's
  tool/echo) never reaches the tree (recent_encounters is a separate
  bypass channel); (3) the faithful stack is decorative; (4) zoom is
  unreachable; (5) 4k-char budget + drop-oldest; (6) node persistence
  (JsonlSummaryNodeStore) exists but the population runner exposes no
  flag to enable it — fine with the stub, blocking for any real
  summarizer (2N calls per session start, synchronous in the decide).
- The Hermes plugin divergences: essentially none INHERITED — ro-bots
  does not use the plugin's architecture; its divergences are its own.

## 2026-10-27 evening — the warp-trigger fix: NoRoute walks are sent DIRECTLY at the target (the server path-finds its own side)

Leg 28's biggest farming-time thief: the field warp cell (170,378) is
unwalkable in the client grid, so `shortest_path` raised NoRoute and `_move`
returned WITHOUT sending any walk packet — the server never moved the unit,
the warp never fired, and the script re-authored the same MoveTo (leg 28:
PipinWalker walked at the warp leg 97 times, 1,117 MoveTos in one window).
The spike clients warp precisely because they send raw walks without
client-side pathfinding.

Fix (RED->GREEN, `_move`): on NoRoute the client now sends the walk DIRECTLY
at the target — the server path-finds its own side and walks the unit as far
as it can; when the server-side path crosses the warp cell, the warp fires
and the map change arrives through the normal entry frames. The retry is
paced on the SAME pending-walk lifecycle as any walk (stall clock releases
the slot), and bounded: NO_ROUTE_DIRECT_SENDS=5 consecutive no-route sends,
then `no_route_exhausted` + the patrol fails so the goal layer re-rolls a
reachable target; a successful walk anywhere resets the budget. Tests: three
wire-shaped cases (direct send on NoRoute, the cap, the reset); the gate
names both new shapes (`no_route_direct`, `no_route_exhausted`) in the
receipt.

Leg 29 (the first window on this fix + the leg-28 mob-destination fix)
targets the town<->field round trip: farm on the field, warp to town, sell,
warp back, farm again — the loop whose travel legs were silently dead.

## 2026-10-27 night — the sell-completion gate ported: readiness is tracked adjacency, the epoch latches at the mint, the 0xC9 guard is fail-closed

The law (`feature/sell-completion-gate-law`, `6bc729bf`) named leg 28's sell
churn precisely: the C5 sell-open was gated on `tracker.view.arrival_confirmed`
through `_sell_actuation_ready` -> `_npc_motion_ready` — False after every
real walk — so 32 mints never sent one packet, no C7 was ever requested, and
the dialogue timed out to 'blocked'. The click path had been cured of the
same defect in e06dc511; the sell limb had not.

Ported (RED->GREEN, tests/test_shop_sell_loop.py T1/T3/T4/T11):
- `_sell_actuation_ready` no longer requires the arrival flag; `_send_sell_open`
  gates on TRACKED ADJACENCY to the received dealer (hypot <= 3, mirroring
  the click path), fail-closed.
- The epoch latch moved to the MINT (`_sell_open_action`): a guard failure
  cannot re-mint the same epoch's open (leg 28's 32 opens); a fresh received
  C4 is a fresh epoch and mints again.
- `_send_sell` compared a bool guard to `None` (never fired — fail-open):
  now fail-closed (`is not True`).
Remaining from the law (next lane): the C7-epoch binding (T5/T6/T12), the
no-C7 deadline recovery through the existing deny-origin path (T7-T10).

## 2026-10-27 late — leg 30 receipt: the pop is alive and social; the sell chain advanced one hop (C7 offer in state); 0 kills, 0 new zeny

Receipt population-receipt-30-1793130666.json (window 21:05-23:05, 33,504
steps, 0 step errors, all 7 online ~240/280 samples, decides 17k-30k each).
Socials live: 1,922 chats heard, PartyChats, GuildInvites dispatched. The
warp fixes held (agents farming the field anchor). The sell chain reached
further than ever: g00m00's state carried a received C7 sell offer
(shop_offer=1) with the dialogue ending 'blocked' — the C5 escaped (a
zero-length walkok epoch) but the C9 sell sat unsold behind the same
arrival_confirmed gate the law named; the port (this branch) removes it.
Combat: 418 attacks (g00m01) + 82 DamageTaken but 0 kills (no exp gain) —
mobs engage, the bots swing, nothing lands; the melee-landing discipline is
the next frontier after the sell gate. DB ground truth: NyxSong 5z,
=======
## 2026-10-27 night — LAW SLICE: the sell-completion gate — why leg 28's 32 sell-opens never became a sell (the arrival flag, again)

Research slice (no production change; `src/` read-only, `spikes/` untouched).
The law: `run/reviews/sell-completion-gate-law.md`. The reproduction:
`.work/probe/sell_gate_probe.py` (offline, read-only against production `src/`).

**The question.** Leg 28 (`run/plain_host_receipts/population-receipt-28-1793096707.json`)
minted 32 `NpcShopSellOpen` with ZERO completed sells; `npc_stage` walked
`unsupported_shop` (t=3641.4) -> `blocked` (t=3731.5) and stayed blocked; zeny
stayed 0. The frame probe (`.work/engagement-diagnosis/c7_probe.py`, 18:54, the
LIVE e2e dealer) had already proved the WIRE is healthy: click 0x0090 -> C4 ->
C5 type 1 -> **ZC_PC_SELL_ITEMLIST 0xC7 ARRIVES**. So the defect was in the
runtime's DIALOGUE PROGRESSION, not the wire.

**The mechanism (named, with citations).** The tick's shop path mints fine
(`_shop_loop_action` :1062 -> `_sell_open_action` :1106: the stage is
`unsupported_shop`, the dedupe key is unissued, and the agent held Jellopy 909
the whole window — `shop_sellable_stock` was 1, so "nothing to sell" never
blocked it). The failure is in the DISPATCH: `_send_sell_open` (:1133) ->
`_sell_open_request_ready` (:1148) -> `_sell_actuation_ready` (:1026) ->
`_npc_motion_ready` (:1298) -> **`tracker.view.arrival_confirmed` is False** ->
the C5 type 1 NEVER LEFT THE CLIENT. No C5 -> no C7 -> `_pending_sell` (:1080)
never mints a sell -> zeny 0. The chain terminates exactly at that guard.

**Why arrival_confirmed was False.** `native_gameplay.py:756` sets
`_arrival = (position.x, position.y) == destination` on a 0x0087 walk frame —
True only for a ZERO-LENGTH walkok; the pinned comment at :750-752 says so
("a moving walkok is IN FLIGHT"). PipinWalker WALKED to the dealer
(`(156,156) -> ... -> (173,130)`), so the flag was permanently False from the
arrival onward, and the agent stood still at the dealer for 13 minutes with it
False. **This is the SAME defect the w82 fix already cured for the CLICK path**
(`e06dc511`: "the npc click gate is tracked adjacency, not the arrival flag").
`_talk_npc` (:1305) was changed to tracked adjacency; the sell-open limb was
never given the same treatment and still reads `_npc_motion_ready`. The click
succeeded (the C4 arrived); the C5 that follows it could never leave.

**The reproduction proves it is the only difference.** Same offline state, two
cases: with a REAL walk -> `arrival_confirmed=False`, `_sell_actuation_ready=
False`, `wire.sent=[]`, and the mint REPEATS identically on the next tick.
With a zero-length walkok -> `arrival_confirmed=True`, the C5 type 1 goes out
(`b'\xc5\x00b~\x8e\x06\x01'`), the dedupe latches `(9, 10)`, and the second
tick mints no second sell-open.

**The re-mint, answered precisely (the brief asked).** It was NOT the dedupe key
advancing on server dialog updates. TWO separate facts: (a) WITHIN an epoch the
mint repeated 8x with the SAME `(opened_sequence, prompt_sequence)` because
`_sell_open_issued` is latched at :1145 — INSIDE `_send_sell_open`, AFTER the
failing guard at :1142 — so a refused send never latched; (b) BETWEEN bursts the
key advanced because the runtime **re-clicked** the dealer (a fresh 0x0090 =>
a new `opened_sequence`), which is the deny-origin recovery
(`_retry_blocked_dialogue` :781 / `_retry_blocked_dialogue_on_tick` :1782) after
the dialogue's deadline denied it with `deny_origin='timeout'`. (The re-click
cadence is resolved by the TRACE — its `NpcDialogueReceived` `stage='opening'`
events at 11:26:09.118 / 11:26:30.057 / 11:26:50.975; the receipt's 30s sampler
catches only `unsupported_shop` and `blocked`, because the ~3s opening windows
fall between samples.) So the loop was:
click -> C4 -> mint -> guard fails -> no C5 -> no C7 -> deadline -> deny(timeout)
-> retry re-click -> ... 4 epochs, `NPC_RETRY_BUDGET=3` spent, blocked forever.
`self._npc.requests` never hit its 32 cap: `begin()` resets it to 1 each re-click.

**A second defect the reproduction exposed.** `_send_sell` (:1181) reads
`self._sell_request_target(action, tracker) is None`, but that method returns a
**bool** (:1187). `False is None` is False, so the guard NEVER fires — the C9
sell request is sent even when every local guard rejects it (probe CASE C: the
C9 went out with `arrival_confirmed=False` and `_sell_actuation_ready=False`).
A fail-open where the codebase's convention is fail-closed; it must be closed in
the same port.

**The law's shape.** The shop loop becomes a state machine over DIALOG EPOCHS
(one click -> one C4 -> one C5 -> one C7 -> one C9): the shop's actuation
readiness uses TRACKED ADJACENCY, not the arrival flag (the w82 lesson); ONE
sell-open per epoch, latched at the MINT site (not after the send guards); the
stage advances ONLY on received C7 rows, and a C7 is bound to the epoch that
requested it (today `_pending_sell` reads `sell_lists[-1]` with no epoch check);
no C7 within N seconds of the C5 = a DEAD epoch, recovered by a FRESH CLICK
through the EXISTING deny-origin path (`deny_origin='timeout'`, the same marker
`_expire` uses) — never a second C5, never a second retry mechanism; bounded
epoch retries; and the fail-open sell guard closed.

**The RED tests the coordinator writes before the port** (13, named and
state-pinned in the law): the five that are RED today are the actuation gate
after a real walk, the readiness predicate's independence from the arrival flag,
the no-C7 deadline recovering with a click and NOT a second C5, the dead epoch
marking the dialogue denied with the timeout origin, and the fail-closed sell
request.

Leg 29 was LIVE during this slice: its traces were read freely and nothing was
mutated.

## 2026-10-28 early — LAW 3 landed: a C7 binds to its epoch

`_pending_sell` now requires the sell list's frame to postdate the CURRENT
dialogue's click (`dialog.opened_sequence`, the cursor the click armed): a
C7 received under a previous dialogue never authorises a sell — the recovery
re-click opens a fresh epoch instead. Pinned by T5 (RED->GREEN: the stale-C7
epoch does not sell), T6 (one C9 per received C7), T8 (the happy path end to
end: C5 -> C7 -> sell, and no recovery re-click), T12 (the 0xC9 carries the
C7's epoch). The harness also learned the real shape: the dialogue
self-invalidates when the dealer actor is missing/walking/out of range
(playing_runtime _validate_npc_context), so every shop-loop test now carries
the dealer frame and arms the click before the C4. The pre-existing
mechanical-seam test was reconciled to the epoch chain (an orphan C7 with no
dialogue is exactly what LAW 3 refuses). Remaining from the law: T7/T9/T10 —
the no-C7 deadline recovery, expected to compose with the existing
deny-origin machinery; verify on a live window before building anything new.

## 2026-10-28 night — leg 31 receipt: the sell gate never got its chance; the SOCIAL goal starves the economy

Receipt population-receipt-31-1793141373.json (window Wed 00:10-02:10, 33,533
steps, 0 errors, all 7 online). THE SELL QUESTION: no — zeny unchanged
(NyxSong 5z, RinceNyan 3z, PipinWalker 4z), no C7/C5 evidence (no shop_offer
samples; npc stages opening->blocked), zero sells, zero kills. The dominant
finding is UPSTREAM of the shop: 5 of 7 agents executed ZERO actions over the
whole window (only decides + goal reviews), RinceNyan 2,051 targetless Loots,
s00 2,057 MoveTos. The traces name it: the goal reviews hold goal='social'
(heartbeat after heartbeat) and Clef answers next_action=party_invite
(p=0.45) — but every agent is ALREADY in a party from earlier legs, so the
social action path dispatches nothing and the agent idles. The motivation
layer's social goal has no fall-through: when the social action cannot act
(in-party, no candidate), the brain must hand the tick back to the economy
scripts (farm/sell) instead of standing. NEXT SLICE: the social fall-through
(goal precedence — social attempts bounded per window, then economy). The
sell gate's live validation waits for agents whose goal reaches the shop.

## 2026-10-28 dawn — the starved-social bounce: a social goal that produces nothing may not persist

Leg 31's dominant finding (5 of 7 agents, ZERO actions in 2 hours) named the
mechanism: the goal reviews held goal='social' (change_goal=keep every
heartbeat) while Clef answered next_action=party_invite (p=0.45) — but every
agent was ALREADY in a party, so the social action path dispatched nothing,
forever. Two fixes, both in the landed design's style:
(1) the moot-options drop (decisions.py) now also drops party_invite when
in_party AND no nearby outsider — an inviter needs a candidate (the leg-16
precedent: party_join dropped for members);
(2) the starved-social bounce (brain.py): the brain counts actions emitted
between heartbeat reviews; a social/idle goal with zero emitted actions for
SOCIAL_IDLE_STREAK_LIMIT (3) consecutive reviews bounces to GRIND — the
economy resumes. Real activity resets the streak honestly (the widen-streak
pattern applied to the goal itself).

## 2026-10-28 morning — two launch traps caught before they ate leg 32

(a) RUNNER DURATION VS WINDOW: the runner was launched 3h04m before its
window with duration 8400s — it would have died at ~07:46, 24 minutes
BEFORE the 08:10 window opened, producing an empty receipt. The duration
must cover launch -> window close + receipt margin.
(b) SCHEDULE DAY INDEX: the schedule file said day index 3 (Thursday) but
the launch was on WEDNESDAY — PersonaClock (Python weekday(), Monday=0)
silently never opens the window and the runner idles at 0/0/None forever.
The symptom is unmistakable: agents 0/0/None well past the window's open.
Both caught by the log readback before the window; leg 32 relaunched 08:57
with day 2, window 09:00-10:40, duration 7200. ALSO: T3 schedule_task's
weekdays are SUNDAY=0 (Tue=2, Wed=3, Thu=4) — the OPPOSITE of the runner's
Monday=0; a readout scheduled with the runner's convention fires a day late.

## 2026-10-28 09:15 — leg 32 window LIVE; the guild-invite legacy limb crashes on a list

The corrected window opened on time and the agents are acting. Live error
(spotted in /tmp/population_leg32.log, 5 occurrences): `action GuildInvite
failed: 'list' object has no attribute 'get'` — agent_runtime.py:1301's
legacy limb does `client.party_members.get(player)` but party_members is a
LIST on this host, and semantically a guild invite (CZ_REQ_JOIN_GUILD 0x0168
= target_AID) needs the CANDIDATE's account id from the nearby actors, not a
party-member lookup. Per-action caught; the runner unaffected. NEXT FIX
(leg 33, TDD): the guild-invite limb resolves the candidate from
state.nearby players (name -> aid) and the native path's _invite_to_guild is
audited for the same assumption.

## 2026-10-28 midday — leg 32 receipt: the behavioral layer is FIXED; the bottleneck is now singular (kills)

Receipt population-receipt-32-1793173804.json (28,724 steps, 0 errors, all
7 online the whole window). THE BOUNCE VERDICT: WORKS. After leg 31's five
frozen agents, every agent emitted actions this window: goals went farm_item
(4 agents) / grind / social-with-actions — the moot drop and the
starved-social bounce changed behavior qualitatively. g00m01 held goal=grind
for 69/69 reviews on the field (412 MoveTos); g00m00/g01m00 drove real shop
limbs (NpcShopBuySelection — the buy list opened); FoundGuild fired twice.
THE CONVERT CHAIN IS NOW PRECISE: 1,343 Loots picked up NOTHING (no kills ->
no drops -> no floor items), 2 attacks total, no sells, no exp, zeny
unchanged (5/3/4/0). Everything downstream of the kill is built and waiting
(sell gate, shop limbs, loot, travel, warp). THE SLICE: the grind script
spams targetless Loot (1,343!) instead of attacking visible monsters — the
Loot action must be gated on observed floor items (the walkability-filter
precedent), and the approach->attack chain then gets its chance. The
melee-landing discipline (18.8% at leg 28) is the open question behind it.

## 2026-10-28 afternoon — the loot gate: the scripts no longer mint Loot on their own inventory

Leg 32's convert chain pinpointed the waste: the grind/farm scripts minted
`Loot()` whenever `state.inventory` was non-empty — a stand-in for floor
items a script cannot SEE (BotState has no floor field; the observed drops
live in tracker.view.floor_items). g00m01 minted 1,343 Loot actions that the
floor-item-aware performer silently no-oped, and each one PREEMPTED the roam
leg — the agent stood ticking Loot instead of walking to find mobs. Loot
priority already lives in the RUNTIME (`_loot_first` injects the pickup when
drops are actually observed, window-24's contract). The scripts' branches
are removed: an empty view now falls through to the roam/approach/attack
chain, and the runtime keeps owning real pickups. Reconciled:
test_no_monsters_tail (roam, not Loot), the two commitment-release tests
(the release is the intent; the action is the roam). The GuildInvite legacy
limb crash (party_members.get on a list) is the other queued fix.

## 2026-10-28 afternoon — leg 33 receipt: mobility healthy, the attack layer is the starving limb

Receipt population-receipt-33-1793182164.json (window 13:00-15:00, 57,459
steps, 0 errors, all 7 online throughout). The behavioural stack HOLDS: goals
distributed grind 309 / farm_item 236 / social 70, mobility HEALTHY (2,206
MoveTos, positions advancing on the field), the loot gate worked as designed
(zero targetless Loot spam). But the convert chain still ends at zero: only
6 Attacks (g00m01, the field agent) from 516 approaches, no kills, no drops,
zeny unchanged. THE STARVING LIMB IS THE ATTACK: 516 approaches -> 6 swings.
Next slice: instrument the attack gate (the melee-range check vs the tracked
mob position after arrival; the stop-and-swing standing gate; the
nearby_monsters visibility at the arrival cell) so the receipt names WHY
approaches do not become swings. Also live this window: the GuildInvite
legacy-limb crash x10 (party_members.get on a list) - the TDD fix lands
today (name->aid from the nearby actors).

## 2026-10-28 evening — the GuildInvite crash fixed in BOTH limbs (the live shape was a list)

Leg 33's 10 live crashes traced to TWO sites with the same bug: `party_members.get(player)`
on a client whose party_members is a LIST of {name, aid} dicts (the existing
test had pinned the dict fake, so it never matched production). Both the
native `_invite_to_guild` (playing_runtime) and the legacy limb
(agent_runtime) now resolve the candidate from either shape and fail closed
on an unknown candidate (0x0168 = target_AID). RED->GREEN:
test_guild_invite_limb_accepts_the_live_party_members_shape. The attack-layer
starvation (6 attacks from 516 approaches) is the next instrumentation slice.

Gate 6,592 + 65 subtests green: `guild_candidate_aid` extracted to
src/robots/app/party_roster.py (both invite limbs share it; xenon back under B).

## 2026-10-28 evening — the attack-gate telemetry: a suppressed swing names its reason

Leg 33's 6-attacks-from-516-approaches had no instrument on the LAST hop:
`_attack`'s early-return gates (alive / pending-walk / target-visibility /
resting / cooldown) dropped swings silently. Mirroring the w58 move-gate
contract, `_note_attack_gate` records the drop reason on the client
(`_attack_gate_reasons`, bounded deque) and the population runner samples it
into the receipt as `attack_gates: {pending_walk: 12, ...}`. Two stop-and-
swing pins added (a pending walk records pending_walk; an invisible target
records target_not_visible). Leg 34's receipt will NAME the swing drop, and
the fix follows from the named reason.

## 2026-10-28 evening — leg 34 receipt: the attack gate is EXONERATED, the starve is UPSTREAM of it

Receipt population-receipt-34-1793202892.json (window 18:00-20:00 CEST, 57,484
steps, 0 errors, all 7 personas online for the whole window and a clean
scheduled logout at 20:00). The leg's purpose was the attack-gate telemetry
(fea2b2db): the receipt names WHY an authored Attack sends nothing. THE
INSTRUMENT ANSWERS, AND IT EXONERATES THE GATE: the attack-gates counter
recorded ONE event in the entire leg (pending_walk=1, on g00m01). Every other
gate (dead / target_not_visible / resting / cooldown) is ZERO on every
persona. So the swings were not suppressed by the melee/standing/visibility
gates — they were never AUTHORED.

The traces show where they died. In the window the agents authored 691
MoveTos and exactly 1 Attack (script_step rows: 692, of which 691 MoveTo and
1 Attack; action_executed: 3,482 MoveTo and 3 Attack, all three from
g00m01/RinceNyan on the same gid 110090709 from (189,366)). 43 decide-requests
saw a mob that was NOT the plan's species, and the widen escape hatch that
should have covered that case never opened.

THE ROOT CAUSE, from the pinned source: the widen streak is written but
never read. brain.py:490 constructs `FarmScript(plan)` with NO
`initial_starved`, so every plan re-author restarts `_starved` at 0, and the
threshold TARGET_WIDEN_STEPS=20 (scripts.py:63) can never be reached - the
streak resets every ~49s (g00m01) / ~55s (s00) median plan cadence while the
plan lifetime carries only a median 5-7 script steps. The persistence half
exists but is orphaned: brain.py:717-718 writes `self._widen_streaks` and
nothing ever reads it back (`initial_starved` has no caller outside
scripts.py itself; the only other reference is a test fixture). Consequence:
the agents only ever attack the plan's EXACT species, and a visible-but-
different mob (43 samples) is ignored forever.

The second, independent limiter: MELEE_RANGE=1 (scripts.py:44) against a
median plan-species distance of 9 cells (g00m01) and 14 cells (s00, which
never once got within 1 cell in 56 samples). The approach is a MoveTo toward
the target's neighbouring cell, re-targeted every evaluation, so the agents
walk for the whole window without closing. Even the 3 swings that landed did
not kill: the fixture chars carry NO WEAPON (weapon=0 on all 7, and the
inventory has no blade), so a Novice's bare-hand damage cannot clear a 60-HP
Poring. RinceNyan took 9 DamageTaken from that same gid while its HP fell
86 -> 7 (it rested and recovered to 43; it never died).

Economy: ZERO kills, ZERO sells, ZERO zeny. The DB is byte-identical to the
pre-window baseline for all 7 chars (exp unchanged, zeny unchanged: NyxSong
5z, RinceNyan 3z, PipinWalker 4z, the rest 0z; every char still at level 10
base/10 job). The picklog is empty. The 2 items on RinceNyan (713 Empty
Bottle, 1002 Iron Ore) PREDATE this window - no pickup/loot/sell action was
executed by any persona in the window, and the char server autosaved
`Saved Inventory (0)` for every char throughout.

SOCIAL: the guild layer is healthy and the GuildInvite fix holds -
`GuildInvite failed` count is ZERO (10 GuildInvite actions, 0 failures,
after a95e00f6); 2 guilds found (NyxSongGuard, PipinWalkerGuard) and
persisted in the DB (char 300000 guild_id 2, char 300003 guild_id 3);
4 InviteToParty, 12 PartyChat; parties 2/3/4 intact across the window.

THE NEXT SLICE is therefore NOT a gate fix: (1) wire the widen streak -
pass `initial_starved` from `self._widen_streaks` when the re-authored plan
has the SAME target set and map (the key already computed at brain.py:716),
so a plan-species re-author cannot reset the streak; (2) give the fixture a
weapon (the 50z knife the economy is supposed to buy) or the melee leg has no
damage even when the chase closes; (3) then re-measure the approach
convergence - with MELEE_RANGE=1 and a median 9-cell distance, the approach
needs its own convergence rule.

Also worth recording: the login server's socket-level `connect_check` DDoS
throttle rejected the 7th login of the window (6 logins inside 3s from one
IP). The pinned rule is in rathena/src/common/socket.cpp:1089-1091
(ddos_interval=3s, ddos_count=10, ddos_autoreset=10min) and a rejected
connection does NOT refresh the flag's tick, so the block self-expires: the
solo (pop_0003_s00) rejoined unprompted ~15 min later with no intervention.
The fix is the roster's login stagger, not a runner change.

## 2026-10-28 night — the widen-streak read half is wired: the re-author inherits the recorded streak

Leg 34's verdict (3776019f) named the orphan: brain.py wrote `_widen_streaks`
per (targets, map) at every step and NOTHING read it back — `FarmScript(plan)`
constructed with the default `initial_starved=0`, so the median-49s re-author
reset the starvation count forever and TARGET_WIDEN_STEPS=20 could never
accumulate (691 MoveTos, 1 authored Attack). The construction now injects
`initial_starved` from the recorded streak for the same (targets, map) key; a
target change is a different key and resets honestly (the sibling test). The
old survival test passed VACUOUSLY (both scripts at 0 == 0); the new test
starves the first script through 5 real steps before the re-author and
demands the streak carry. The widen now converges: ~20 starved evaluations
open the target set to the observed species, the plan species meets the
roam, and the approach chain gets its chance. NEXT: the fixture weapon (the
7 chars carry weapon=0 — even a landed swing cannot kill a 60-HP Poring),
then re-measure the approach convergence at MELEE_RANGE=1.

The live e2e chars received their knives too (an INSERT for char_id >= 300000
against the existing world — 7 rows verified, equip=2): leg 35's swings carry
damage without waiting for the fixture regeneration.

## 2026-10-29 00:30 — LEG 35 VERDICT: the window was dead from minute one — a MISSING PACKET, not a mechanic

**The kill question: 0 attacks, 0 kills, 0 sells. The widen convergence and the
knife never got a chance to be tested.** The leg-35 traces hold, for the whole
window (21:30-23:00 UTC), only: 9 decide_request/response, 7 goal_review, 4
state_tick, 4 script_step, 7 action_executed = 4 MoveTo + 3 PartyChat. Not one
Attack. Not one Loot. The DB exp/zeny are byte-identical to the pre-leg
baselines (NyxSong 2/4, RinceNyan 9/17, zeny_wing 7/10, PipinWalker 7/2, the
rest 0; zeny 5/3/0/4/0/0/0). `GuildInvite failed` = 0.

**The cause: the framer did not know the wear-equip ack.** Leg 35 was the first
window with a Knife in every char's right hand (2b0f249e, `equip=2` =
EQP_HAND_R, all 7 rows verified). The runtime's equip progression then sends
CZ_REQ_WEAR_EQUIP (0x0998) and the pinned server answers with
ZC_ACK_WEAR_EQUIP_V5 **0x0999** (11B: <index>.W <wear location>.L <view id>.W
<result>.B, packets_struct.hpp:1269-1276; sent by clif_equipitemack,
clif.cpp:4302-4328). `spikes/003-clientless-limbs/packetdb.py` had no entry for
it, so `parse_stream` raised `ValueError('unknown packet 0x0999')`, the rx
thread died, the transport went unavailable, and `agent_runtime.py` took the
silent `NativeTelemetryUnavailable` early-return forever. Every agent froze
1-3 s after its own connect (six at 21:30:01-05, the throttled solo at
21:43:16 -> 21:43:18).

**The proof is an A/B on the production host**, not a reading:
`.work/engagement-diagnosis/leg35_host_probe.py` connects two fixture chars
against the e2e world. With the Knife: `rx_error: ValueError('unknown packet
0x0999')`, transport unavailable, ZERO continuing ticks. Without it: ticks
continue normally. The frame-set diff of the two raw login captures showed the
Knife run carrying exactly one extra frame (0x0A0D, the equipment list), and
replaying both sets through the production `NativeGameplayTracker` ingested
cleanly - so 0x0A0D was NOT the cause; the 0x0999 REPLY was. (0x0A9B, an
earlier hypothesis, is also absent from the table but is not causal.)

**The fix: THREE frames, all sized from the pinned headers, not transcribed.**
`PACKET_DB.update({0x0999: 11})`, `{0x01F2: 20}`, `{0x01EB: 10}`.

The gaps came out in a chain, each one revealed by the fix before it (the rx
thread lived long enough to reach the next):

1. **0x0999** ZC_ACK_WEAR_EQUIP_V5 (<index>.W <wear location>.L <view id>.W
   <result>.B = 11B, packets_struct.hpp:1269-1276; sent by clif_equipitemack,
   clif.cpp:4302-4328). The leg-35 killer: the Knife made the equip
   progression send CZ_REQ_WEAR_EQUIP (0x0998) and the reply killed the rx
   thread.
2. **0x01F2** ZC_UPDATE_CHARSTAT, the guild member login notice (<account
   id>.L <char id>.L <status>.L <gender>.W <hair style>.W <hair color>.W =
   20B, map/packets.hpp:876-885; compiled sizeof=20, and the live capture is
   exactly 20 bytes decoding to aid=2000101/cid=150101 - the other fixture
   char). The server sends it to a guild's other members when one logs in
   (map/guild.cpp:1439 -> clif_guild_memberlogin_notice), so it reaches any
   char that shares a guild - and two population chars do (guild 2 = NyxSong,
   guild 3 = PipinWalker; `guild_member` verified).
3. **0x01EB** ZC_NOTIFY_POSITION_TO_GUILDM (<account id>.L <x>.W <y>.W = 10B,
   map/packets.hpp:859-865; compiled sizeof=10), the guild member position
   notice the server sends when one of them moves (map/clif.cpp:3316-3335).

Fixing one at a time is slow, so the third was found with a SWEEP instead: a
tolerant framer that RECORDS every unknown frame instead of raising
(`.work/engagement-diagnosis/leg35_unknown_sweep.py`). With the first two
framed, the sweep reported exactly ONE remaining unknown - 0x01eb - and with
it tolerated both fixture clients ran clean (`rx_error: None`). That is the
whole guild/equip path, closed.

**Verified live after the fix:** the same A/B probe with the Knife now ticks
75 times with `rx_error: None`, `tracker_ready: true`, `standing: true`, and
the char MOVES (pos 169,132 -> 169,133). With all three frames framed, both
fixtures tick cleanly (71 and 72 ticks, `rx_error: None`, `wire_running:
true`, positions advancing). The ack is not merely framable, it is CONSUMED:
`native_gameplay.py:665` dispatches pid 0x0999 to `_equip_ack`, which calls
`decode_equip_ack` (native_equipment.py:71-77) and settles the worn state.

One honest detail the live probe surfaced: the knife is ALREADY equipped
server-side (the fixture inserted it with `equip=2` = EQP_HAND_R), so the
server's ack is a FAILURE (pc.cpp:12056-12063 rejects an already-worn item)
and the client's `worn` set stays EMPTY. The damage path is unaffected - the
server applies the knife's damage from ITS state, and the fixture knife is
worn there - but the client will keep re-sending the equip request until the
attempt cap (3). That is a bounded, harmless loop, not a stall.

**The digest discipline held.** All three additions are byte-exact evidence
blocks, so the SHA-pinned framing tests needed reconciling: the era chains
(906 -> 909 entries, `0x0999: 11`, `0x01F2: 20` and `0x01EB: 10` added to
the wear_ack set) and the accepted-hash tuples - the actual hashes, read
from the pytest failures or computed from the file, never written by hand.
The new test file `tests/test_native_wear_equip_ack_framing.py` pins all
three frames' sizes, their framing, their non-desync of the following frame,
and the evidence bytes (one shared digest for the three blocks).

**What leg 35 does NOT tell us:** nothing about the widen convergence, the
knife's damage, the approach chain, or the mob kill. All of it was downstream
of a dead transport. The next window (leg 36) is the first real test of
2b0f249e + 429e54a7.

**The login throttle recurred and is NOT the cause here.** The solo
(pop_0003_s00) was rejected by the login server's socket-level `connect_check`
throttle (leg 34's note above) and rejoined unprompted at 21:43:16 - 13
minutes later, no intervention, the self-expiry the pinned rule predicts. The
8 `connect failed (ConnectionError)` lines in the runner log are those
retries. The other six agents were already connected and still froze, and the
solo froze too, 2 s after its own successful connect - so the throttle is not
the cause.

**The throttle's real rule, read from the pinned source and confirmed live.**
`connect_check_` (rathena/src/common/socket.cpp:1112-1204) is CHAINED, not
windowed::

    if (hist->ddos)                                   return 0;   # flagged
    else if (DIFF_TICK(gettick(),hist->tick) < ddos_interval) {
        hist->tick = gettick();
        if (hist->count++ >= ddos_count) { hist->ddos = 1; ... }     # trip
    } else { hist->tick = gettick(); hist->count = 0; }              # RESET

`ddos_count=10`, `ddos_interval=3s`, `ddos_autoreset=10min`. The count is
only CLEARED when a connection arrives MORE than ddos_interval after the
previous one - so a chain of 1s-apart logins ACCUMULATES (7 agents plus the
solo's retry storm = >10) and trips it. The live login log shows the shape
exactly: six logins at 0.79-1.13s apart (22:30:00.24 -> 22:30:04.45 local),
then "connect_check: DDoS Attack detected from 10.89.3.6!" on the seventh.
The fix is therefore NOT "space them a second" but "space them MORE than
ddos_interval", so every login takes the reset branch and the chain count
never grows. `LoginStagger` (agent_runtime.py) does exactly that - 3.5s
between personas - and the host's connect path consults it. The roster opens
over ~24s instead of ~5s, which is free against a 90-minute window.

**Two observability gaps are closed too, because leg 35 burned three hours
on a failure NOTHING named.** The runner's receipt had no transport field and
its log printed only the online/decides summary, so the whole window's death
was invisible: no "unknown packet", no "Traceback", no receipt line. The
receipt now carries `rx_error` (the transport's own reason, as
"<Type>: <message>") and `dispatch_errors` (counted per packet id), and the
runner prints "TRANSPORT DOWN pid=...: <reason>" the first time each distinct
reason appears. A dead transport must be loud.

## 2026-10-29 04:30 — LEG 36 VERDICT: the widen CONVERGED and the knife killed — but only 1 of 7 agents ever left the town

**The kill question: YES, and for the first time in the population series, the
exp moved.** RinceNyan (pop_0003_g00m01) went 9/17 -> **17/20** base/job exp
(+8 base, +3 job) and ended on prt_fild08. The arithmetic names the kills
exactly: the pinned `mob_db.yml` gives Poring 2/1 and Lunatic 6/2, and
`Poring + Lunatic = 8 base / 3 job` — the ONLY two-mob combination in the
species set that sums to the observed delta. The trace agrees: 4 swings at
Lunatic 110095584 (01:36:27-35) and 4 at Poring 110095692 (01:37:34-41), then
one more Poring swing at 110095691 (02:10:06). Three mobs died.

**The widen convergence WORKS.** g00m01 authored **127 plans**, 105 of them
with the STABLE target set `(Lunatic, Pupa) on prt_fild08`. That stability is
the precondition the read half (429e54a7) needs — the streak is keyed on
`(frozenset(target_mobs), map_name)`, so a stable target set is exactly the
case where the recorded `_starved` is inherited instead of reset. The first
plan was authored at 01:08:27 and the first swing landed at 01:36:27: **28
minutes** for 20 starved evaluations, matching the ~49s re-author cadence
leg 34 measured. The widen did its job.

**The knife did its job.** The swing at 01:36:27 is on a level-10 Novice with
a Knife (1201, equip=2) against a 60-HP Lunatic: 4 swings per mob, mobs
dying, +8/+3 exp. Leg 34's third limiter (weapon=0 on all 7) is closed.

**The transport held.** 0 `TRANSPORT DOWN`, 0 `rx_error`, 0 `dispatch_errors`
on every one of the 7 agents — the three packet ids (0x0999, 0x01F2, 0x01EB,
64dc6c83) are registered and the leg-35 death does not recur. 0
`GuildInvite failed`. 43,114 steps, **0 step errors**. LoginStagger admitted
all 7 with no connect_check throttle. The window opened on time: the runner
printed `CLOCK: (3, 1.4)` (Thursday, 01:24 Madrid) and the schedule's day-3
02:00-04:00 window opened with all 7 online by t=2162s.

**But 6 of 7 agents never fought, and the reason is NOT the widen.** They
authored **zero** plans (0 each, except s00 with 7), never entered a farm
map, and racked up 21,000 MoveTos without a single swing. The receipt's
`attack_gates` is `None` for all six — they never reached the attack gate,
because they never authored an Attack. The gate is exonerated for the third
leg running.

**The mechanism, named exactly: the travel route is consulted only for
`Goal.GRIND`, and the agents' goals were `farm_item` or `social`.**
`brain._goal_script` (brain.py:1014-1019) hands the route to `GrindScript`
only `if goal == Goal.GRIND and state.map_name in TRAVEL_ROUTES`, and
`TRAVEL_ROUTES` (src/robots/knowledge/travel_routes.py) has exactly ONE
entry: prontera -> (156,22) -> prt_fild08. Meanwhile `_setup_farm_plan`
returns None for a town map (no observed mobs, and prontera/prt_in have NO
spawn declaration in the rathena fields files — only prt_fild08 and
pay_fild04 do), so those agents fell back to the bare `GrindScript()` with no
route and no plan, and simply patrolled their town all window.

The timeline proves it to the second. g00m02 (in prontera) issued 31 MoveTos
to the warp cell (156,22) between 01:00:08 and 01:01:13, then STOPPED — and
its `goal_review` flipped `grind -> farm_item` at 01:01:16, three seconds
later. The same flip killed the route: `farm_item` is not `Goal.GRIND`, so
`_goal_script` stopped handing over `TRAVEL_ROUTES`, and the agent roamed
prontera for the remaining 119 minutes. g01m02 walked to the warp 159 times
and then stopped at exactly its own flip (01:05:51). The Clef answers are
unmistakable: `change_goal` chose `farm` 137/128 times for the two prontera
agents and `keep`/`farm` for the rest; only g00m01 stayed on `grind` (48
`grind` answers) and only g00m01 reached the field.

**So the leg's verdict is: the widen converges, the knife kills, the transport
is healthy — and the remaining limiter is that the TRAVEL ROUTE IS BOUND TO
THE GOAL NAME.** A `farm_item` goal on a town map has neither a plan nor a
route, so it patrols forever. That is a one-line-class fix in
`_goal_script`/`_setup_farm_plan` (route on any farming goal, or route to the
map the plan names), not a mechanic hunt.

Also recorded: the decide counters in the receipt are EXACT this leg
(154/174/147/162/147/146/161 = the trace's own decide_response counts) — the
stale-ref under-count the brief warned about did not bite. The `picklog` is
still empty (0 rows) despite the verified kills, so the loot pickup is the
next unproven hop: the mobs died but no drop was picked up and zeny is
unchanged (no sells). The trace shows `Loot=0` for every agent.

## 2026-10-29 ~04:4x — leg 36 follow-up: the travel route unbound from the goal name (brain.py:1014)

Leg 36 closed with the first kills (9 attacks, 2 confirmed: RinceNyan 9/17 -> 17/20,
the mob_db arithmetic naming Poring 2/1 + Lunatic 6/2 uniquely) - but 6 of 7 agents
authored ZERO plans and burned ~21k MoveTos with no swing, their attack_gates None
for the third leg running (the gate is exonerated; they never reached it).

Mechanism, proven to the second: `_goal_script` handed TRAVEL_ROUTES to GrindScript
only `if goal == Goal.GRIND`, and `_setup_farm_plan` returns None on a town map
(prontera/prt_in have no spawn declaration in rathena/npc/pre-re/mobs/fields), so a
farm_item goal on a town map had NEITHER a plan NOR a route and patrolled forever.
g00m02's 31 warp-cell MoveTos stopped at 01:01:13; its goal_review flipped
grind -> farm_item at 01:01:16. g01m02 stopped at exactly its own flip (01:05:51).
Only g00m01 stayed on grind (48 grind answers) and only it reached the field.

Fix (one line): `_wants_farming(goal)` - ANY farming goal gets the seeded route when
the current map has one; the goal's NAME is irrelevant. RED test
`test_farm_item_on_a_routed_town_gets_the_travel_plan` reproduced the leg-36
patrol-forever shape; the on-field cases pin no route. Gate 6,637+65 / 95.50%.

Still open from leg 36: the picklog 0 rows + Loot=0 despite verified kills (the
drop->pickup hop unproven), zeny unchanged (no sells) - the economy closure. Next:
leg 37 in a window where all 7 can actually reach a field.

## 2026-10-29 ~06:2x — leg 37 follow-up: a farming goal on prt_in gets the exit route (travel_routes.py)

Leg 37 measured the leg-36 route fix and it WORKS: PoringMuffin14 - a farm_item
goal on prontera that patrolled its town forever in leg 36 - crossed to prt_fild08
within a minute of the window opening and authored 61 farm plans. The goal-name-free
handout (78167c2b) is confirmed live.

But three agents still patrolled forever, and the mechanism is NOT the goal name this
time - it is the LOGIN POSITION. A char logs in where it LOGGED OUT (the char table's
`last_map`, via pc.cpp's `pc_lastpoint_special`), not at its Kafra save point. The
popgen fixture sets `save_map=prontera` for six of the seven personas, but the merchant
trip of an earlier leg left NyxSong, PipinWalker and xXLunasongXx inside the prontera
INTERIOR, so every later leg opened them on `prt_in`. Verified from the DB and the
trace: NyxSong's `last_map=prt_in, last_x=166, last_y=137` and its first leg-36 action
was at prt_in (167,138) - its last position, not its save point.

`prt_in` has no spawn declaration (so `_setup_farm_plan` returns None - no plan) AND
no TRAVEL_ROUTES entry (so `_goal_script` hands over the plain GrindScript - no route).
The goal script then roamed the interior at random: 117 distinct random MoveTo targets
for one agent over the window, never the exit door, never the dealer cell. It is the
same patrol-forever SHAPE as leg 36, with a different cause - which is why the leg-36
fix could not have caught it.

The trap is sticky across legs: PipinWalker's history shows prontera + prt_fild08 on
10-27 11:00, a walk to the dealer cell (172,130) at 11:25, and prt_in for every window
since. The route table is the general mechanism for "a farming goal on a map whose
spawns are elsewhere", and prt_in is exactly such a map.

Fix: the pinned exit door `prt_in,168,124` (warp prt05-1 -> prontera,174,218 - the
same cell the merchant return leg already cites) joins the route table, and the route
continues through the prontera field warp to prt_fild08. The three legs of the route
were simulated against the live map cache: from all three stuck agents' positions
(166,137), (168,134) and (44,102) every hop cell is walkable and the pinned warp
arrivals chain prt_in -> prontera -> prt_fild08.

RED: `test_farming_goal_in_the_shop_interior_gets_the_exit_route` and its GRIND twin
both failed on the empty travel plan. GREEN: the prt_in route added. Full gate green:
6,639 passed, coverage 95.50%.

Note for the next leg: the worktree needs the git-ignored corpus DBs
(`run/knowledge/iro-db/iro-db.db`, `run/knowledge/iro-wiki/iro-wiki.db`) and
`rathena/config.log` present or six unrelated tests fail - a fresh worktree has
neither. They are not part of the fix.

## 2026-10-29 ~08:0x — leg 37 receipt: the route fix is live, 2 agents reached a field, and the loot hop is UNPROVEN

Window 04:30-06:30 UTC (05:30-07:30 Madrid), 43,109 steps, **0 step errors**, receipt
`run/plain_host_receipts/population-receipt-37-1793246792.json`. Clean: 7/7 online
at open, zero `TRANSPORT DOWN`, zero `GuildInvite failed`, zero `rx_error`, zero
`dispatch_errors`, no traceback. One transient keepalive failure
(`action Rest failed: native keepalive send failed`) which self-recovered - the
agent kept its session and no transport-down followed it.

**THE ROUTE VERDICT: 2 of 7 agents reached a field (one CROSSED the warp during
the window, the other already lived there), and the five that did not were trapped
for reasons the fix did not touch.**

| persona | map in window | plans | attacks | attacks' gates | outcome |
|---|---|---|---|---|---|
| g00m00 NyxSong | prt_in | 0 | 0 | - | PATROL FOREVER (the prt_in trap) |
| g00m01 RinceNyan | prt_fild08 | 140 | 32 | pending_walk only | field, KILLS (exp 17/20 -> 30/29) |
| g00m02 zeny_wing | prontera | 0 | 0 | - | stuck in a 1-cell walk loop |
| g01m00 PipinWalker | prt_in | 0 | 0 | - | PATROL FOREVER (the prt_in trap) |
| g01m01 xXLunasongXx | prt_in | 0 | 0 | - | PATROL FOREVER (the prt_in trap) |
| g01m02 PoringMuffin14 | prontera -> prt_fild08 | 151 | 3 | pending_walk only | field, CROSSED the warp |
| s00 YuffieFy81 | pay_fild04 | 2 | 0 | - | stuck in a 1-cell walk loop |

The leg-36 fix (78167c2b, the route on any farming goal) is CONFIRMED LIVE:
g01m02 - a `farm_item` goal on prontera that patrolled its town forever in leg 36 -
crossed to prt_fild08 inside the window and authored 151 farm plans. Its first
`state_tick` is prontera (153,35), its last is prt_fild08 (182,358), and its
MoveTo targets include the field warp cell (156,22) 21 times - the route cell from
the pinned warp bytes. g00m01 was already on prt_fild08 (it lives there: its
`last_map` is prt_fild08) and farmed 140 plans with 32 attacks.

**Kills: 1 agent killed (g00m01), +13 base / +9 job exp over the leg-36 baseline
(17/20 -> 30/29).** The odd totals are the fractional co-attack exp split, not a DB
anomaly. 32 attacks on Porings at ~12 dmg/hit, and the DB inventory confirms the
kill is real: g00m01's inventory now holds 713 Empty Bottle + 1002 Iron Ore, the
Poring drop species (mob_db.yml `Id: 1002`, Drops Jellopy 7000 / Knife_ 100 /
Empty_Bottle 1500). **`sells: 0`** - every zeny is unchanged from the baseline
(NyxSong 5, RinceNyan 3, zeny_wing 0, PipinWalker 4, xXLunasongXx 0,
PoringMuffin14 0, YuffieFy81 0). The economy closure did NOT happen.

**THE LOOT HOP IS UNPROVEN, AND IT IS A REGRESSION IN THE ACTION COUNT.** Zero
`Loot` actions in the window, against 8,338 across leg 35-36 for the same agent
(2026-10-26: 2,271, 10-27: 1,982, 10-28: 4,081, 10-29: **0**). The action-count
change is pinned to a commit: `2c99e7f0` (2026-10-28 11:07, "the grind/farm
scripts no longer mint Loot on their own inventory") removed the scripts'
`if state.inventory: return (Loot(),)` branch - correctly, `state.inventory` is
the agent's BAG, not the floor - leaving the runtime's `_loot_first` as the sole
owner of real pickups. So the zero is EXPECTED for the script layer and the
question moves to the runtime hop, which this leg does NOT settle: the picklog
on the e2e world is EMPTY (`SELECT COUNT(*) FROM picklog` -> 0) but that proves
nothing here, because `log_athena.conf` on e2e has `sql_logs: no` /
`enable_logs: 0` - the picklog was armed on the TEST world, not on e2e. The
0x009D / 0x0ADD / 0x00A1 / 0x0A37 packet ids ARE all registered in the client
table (packetdb.py:313/315/321), so the framer is not the blocker, and the
inventory readback shows the kill was real (713 Empty Bottle + 1002 Iron Ore -
the Poring drop species, mob_db.yml `Id: 1002`). So: the drop->floor->pickup hop
is UNPROVEN on this world, not disproven. Named next slice, with the picklog
ARMED ON E2E so the evidence is decisive.

**THE prt_in TRAP SURVIVED THE FIX, AND THE FIX IS INCOMPLETE.** Three agents
still patrolled prt_in for the whole window - 3510/3504/3514 MoveTo to 218/213/264
distinct random targets, zero plans, zero attacks. Two causes, both real:

(a) The running leg did not HAVE the prt_in route. The runner launched at
04:06:32 UTC (the receipt's own epoch, `population-receipt-37-1793246792`), the
window opened 04:30 UTC, and the prt_in route commit landed at 05:20:08 UTC
(`5c2b24dd`, 06:20:08 +0100) - 74 minutes after the launch and 50 minutes after
the window opened. Python binds the module at process start, so the leg ran
without it. (The leg-36 fix `78167c2b` at 03:58:16 UTC DID land before the
launch, which is why g01m02 crossed to the field.)

(b) Even WITH it, the route would not have released the third agent: **the route
names ONE door and prt_in is 26 disconnected building interiors** - `prt_in` is
not one room. The pinned warp bytes give 15 interiors their own door to prontera
(npc/warps/cities/prontera.txt:39-:69), each in its own component of the client
grid: BFS over the live grid finds 26 disconnected walkable components, and a
flood from each of the 15 door cells lands in a different one. The single door
(168,124) is in the prt05 interior, so it could only have walked out the agents
that woke up there - NyxSong (166,137) and PipinWalker (168,134) - and NOT
xXLunasongXx (44,102), whose interior's door is (53,105).
`shortest_path` from (44,102) to (168,124) returns NoRoute. All 34,892
historical prt_in positions sampled across the whole trace history are in
direct-door components, so reachability-aware door selection covers 100% of the
observed cases. The fix in flight: resolve the exit BY REACHABILITY from the
agent's real position (a flood over the agent's own component), with the
internal prt_in warp hops as the fallback for the four interiors that have no
door of their own.

**TWO NEW STUCK-LOOP SHAPES, both from the SAME root cause.** g00m02 (prontera)
and s00 (pay_fild04) each burned the entire window walking to ONE adjacent cell:
3,210 MoveTo to (159,194) and 3,224 to (204,166) - and BOTH target cells are
UNWALKABLE in the client grid (tile 1, not in the walkable set). The position
sequences show exactly what happened. g00m02 walked north cell by cell from
(159,170) to (159,184) to (159,193) in the first two minutes, and then STOPPED -
(159,193) is the last cell before the wall at (159,194), and it stood there for
the remaining 117 minutes, re-authoring the same impossible move. s00 never
moved at all: it stood at (204,165) for the whole window (ONE distinct position
across 118 state ticks), and that cell is ITSELF unwalkable in the client grid
(tile 1) - so the client's picture of the map and the server's disagree about
where the agent is, and its target (204,166) is a wall in the client's grid
too.

The root cause is that a MoveTo target's walkability is never checked before
the script authors it. `IdleTownScript` - the script for the `social` goal,
which both agents had (132 and 133 goal reviews) - emits
`MoveTo(x=state.x, y=state.y+1)`: an unconditional one-cell step NORTH. It
walked g00m02 up its column until the next cell was a wall, and then re-authored
that wall-ward move forever.

**CORRECTION (the fix shape this entry first named was wrong).** This entry
said the FarmScript/GrindScript roam leg "filters its candidates for
walkability (the w59 fix)" and that IdleTownScript was the twin path never
given the same filter. That is false: `grep -n walkable
src/robots/app/scripts.py` returns NOTHING. The script layer has no walkability
check anywhere. The only walkability filter in the whole stack lives in the
RUNTIME at `playing_runtime.py:2059` (`_field_target`, which filters its random
patrol candidates) and it is reached only through `_legacy_mechanical`, which
fires only when the script authored NO actions and the goal is GRIND/FARM_ITEM.
So "give IdleTownScript the filter its siblings have" was not implementable as
written - there was no sibling filter to copy.

**THE REAL MECHANISM, PROVEN.** `IdleTownScript.step`
(`src/robots/app/scripts.py:619`) emits `MoveTo(x=state.x, y=state.y+1)` with no
grid knowledge. The runtime's `_move` then calls `shortest_path`, which raises
NoRoute because the TARGET is unwalkable, and the leg-28 fallback sends the
walk DIRECTLY at the target (`no_route_direct`) up to
`NO_ROUTE_DIRECT_SENDS`=5 times, then stops with `no_route_exhausted`.
`_no_route_attempts` is reset ONLY by a successful path
(`playing_runtime.py:1699`) - so a permanently unreachable target burns the
budget and the agent then sends NOTHING for the rest of the window.

**AND THE SERVER AGREES WITH THE WALL - this is not a client-grid-only
disagreement.** A probe drove the real client for s00 (YuffieFy81) on the live
e2e world: it logged in at (204,165), the walk to (204,166) was sent DIRECTLY
(the server path-finds its own side), and the server REFUSED it - the agent did
not move after 120s. The client's grid is right about (204,165) and (204,166):
both are tile 1, and so is every cell in the 11x11 around them (a 41-cell
blocked run 185-225 on row 165). The agent is standing INSIDE a blocked cell,
and the script's only possible move is +1 north, into that same blocked band.
So every walk it can ever author is into the wall.

**THE FIX BELONGS IN THE RUNTIME, not the script.** The script has no grid and
cannot know; the runtime owns `self.cache` and already owns the walkability
notion (the `_field_target` filter). The shape: in the runtime's move path,
when the authored target is not walkable in the client grid, do not send it and
do not burn the no-route budget on it - pick a walkable NEIGHBOUR of the
agent's CURRENT cell (the same 8-neighbour no-corner-cutting rule as
`shortest_path`) and send that, or stand still and re-plan. The picker must
consider neighbours even when the CURRENT cell is itself blocked (s00's case),
because the agent must be able to walk OUT of a blocked cell; and the leg-28
direct-send must stay, because the server path-finds its own side and may
accept a walk the client grid refuses.

The DEALER TRIP has the same shape and will need the same treatment:
MERCHANT_ROUTE["prt_in"] = (172,130) and MERCHANT_ROUTE_RETURN["prt_in"] =
(168,124) are both in the PRT05 interior, so from the prt03 interior
`shortest_path` returns NoRoute for BOTH (verified on the live grid) - the
dealer cell and the exit door are both unreachable from there. The merchant
legs are a separate fix from the travel route, but they are the same defect:
a cell pinned to a map instead of to the region the agent stands in.

Next slice, in order: (1) the reachability-aware prt_in door resolution - three
agents are locked out of the field by one shared door (DONE, 9330defd); (2) the
RUNTIME-side walkability-aware move picker - two agents walked into a wall for
two hours; (3) the drop->pickup hop (the 0x009D floor ingest -> the 0x0362
pickup) with the picklog ARMED ON THE E2E WORLD (`sql_logs: yes` +
`enable_logs: 0xFFF`) so the next leg's pickup evidence is decisive.

## 2026-10-29 ~09:0x — the prt_in exit is resolved by REACHABILITY (each interior gets its own door)

Leg 37's prt_in trap had TWO causes, and the second one is the deeper one.
The first: the running leg did not even HAVE the prt_in route - the commit
landed at 05:20 UTC, 74 minutes after the 04:06:32 launch. The second: the
route names ONE door, and **prt_in is not one room**. It is 26 disconnected
building interiors, and the pinned warp bytes give 15 of them their own door
to prontera (npc/warps/cities/prontera.txt:39-:69). A BFS over the live client
grid finds 26 disconnected walkable components, and a flood from each of the
15 door cells lands in a different one. So the single door (168,124) - the
prt05 interior's - could only ever have released the agents that woke up in
THAT interior: NyxSong (166,137) and PipinWalker (168,134), but NOT
xXLunasongXx (44,102), whose own interior's door is (53,105).
`shortest_path` from (44,102) to (168,124) returns NoRoute - the door is not
merely far, it is in another component of the map.

The exit is a property of the INTERIOR the agent stands in, so it is now
resolved by REACHABILITY from the agent's own cell, live, on the client grid.
The door table stays knowledge (robots/knowledge/travel_routes.py: EXIT_CELLS,
the 15 pinned doors, plus INTERNAL_WARPS, the 12 interior hops for the four
interiors that have no door of their own); the reachability is navigation
(robots/adapters/native_navigation.py: `walkable_region` + `exit_in_region`,
the same 8-neighbour no-corner-cutting rule as `shortest_path`); and the
composition is the app layer (robots/app/travel_routing.py: the TravelRouter,
which memoizes the per-map region index so the live resolution is a set
lookup, not a flood per step).

The plan is no longer baked into the goal script: the brain hands the script
a RESOLVER (the `travel_resolver` protocol, `(map_name, x, y) -> legs`), and
the script resolves the leg from the agent's CURRENT cell every step - so an
agent that warps into another interior re-resolves on the next step instead
of walking to a door that is no longer reachable.

Two deliberate choices. (1) A map with SEVERAL exits resolves by reachability
(prt_in's 15 doors); a map with ONE exit (prontera's field warp) resolves
UNCONDITIONALLY - the client grid is a lossy picture of the server's and the
server path-finds its own side (the leg-28 direct-send path), so a
client-side "unreachable" there would veto a walk the server would happily
make. (2) When the grid does not carry the map at all, the seeded static
route is the fallback, so a world without the map keeps a route rather than
losing it.

Verified against the LIVE client grid, not a fixture: the three leg-37
trapped agents now resolve to their OWN doors - NyxSong (166,137) -> 168,124,
PipinWalker (168,134) -> 168,124, xXLunasongXx (44,102) -> **53,105** (the
door the old route could never have reached) - and all 15 doors resolve to
themselves from their own cells. prontera still resolves to the field warp
from every position tested, and the field itself resolves to None (it is the
destination, not a route). Every one of the 74 distinct historical prt_in
positions resolves (43 to the prt05 door, 31 to the prt03 door, 0
unresolved).

**AND THE WALK IS LIVE-PROVEN AGAINST THE SERVER.** A probe drove the real
client for xXLunasongXx (the agent that the old route could never have
released) against the live e2e world: it logged in on prt_in at (40,99), the
resolver named (53,105) for its cell, the client path was 10 cells, the agent
walked it and **the warp fired 13 seconds later** - it arrived on prontera at
(136,186), exactly the pinned arrival cell for that door
(npc/warps/cities/prontera.txt:61). The door the fix names is a door the
SERVER will let the agent walk into, not only a cell the client grid can
path to.

## 2026-10-29 ~10:4x — leg 38 slice (a): the unwalkable-target deadlock closed (IdleTownScript + the runtime re-roll)

Leg 37 defect 2: g00m02 (prontera) authored 3,210 MoveTos to (159,194) — unwalkable
in the client grid — and stood 117 minutes re-authoring it; s00 (pay_fild04) never
moved at all (its own cell (204,165) is unwalkable in the client grid; the client's
map picture and the server's disagree). Both agents ran the `social` goal's
IdleTownScript, which emitted MoveTo(x, y+1) unconditionally — one wall locked the
whole script lifetime onto a single impossible cell. The twin roam paths vary their
step among several directions; IdleTownScript never got the same treatment (the
corrected mechanism per 44af0c7e: the SCRIPT layer has no walkability filter — the
runtime owns the grid).

Two halves, both TDD:
- scripts.py: IdleTownScript cycles the four directions deterministically
  (N->E->S->W, clamped at 0). The runtime's walkability/route handling stays the
  single authority on whether a cell can actually be walked.
- native_navigation.py: nearest_walkable (pure, ring order, radius 2) + playing_runtime._move_reroll:
  when the bounded NoRoute direct sends cannot move the unit (the cell is a wall on
  BOTH sides), the exhausted target gets ONE walk to the nearest walkable neighbor
  (target_unwalkable_rerolled), tried once per (map, target) — a second failure
  names rerolled_target_dead and fails the patrol for the bounded replan; a sealed
  pocket (no walkable neighbor at all) names target_unwalkable and sends NOTHING
  (the honest stop; s00's case). The leg-28 warp cells are untouched: their first
  direct send succeeds before any exhaustion.

Note the deliberate placement: a HEAD gate on the client-grid walkability (walk to a
neighbor BEFORE routing) would have preempted leg 28's warp direct-sends ((170,378)
is unwalkable client-side and the server must still receive the walk). The re-roll
lives at the EXHAUSTED branch, after the server has refused the cell five times.

Merchant legs (the second half of defect 2) NOT yet fixed: MERCHANT_ROUTE/
MERCHANT_ROUTE_RETURN prt_in cells are pinned PRT05-interior cells, component-blind
from the prt03 interior — the same defect one layer over, needing the resolver wired
through _merchant_step (FarmScript holds no resolver yet). Next slice.

Gate 6,654+65 / 95.3x%.

## 2026-10-29 ~11:2x — leg 38 slice (a2): the merchant legs respect interior components

The second half of leg 37 defect 2: MERCHANT_ROUTE/MERCHANT_ROUTE_RETURN's prt_in
cells are pinned PRT05-interior cells, component-blind from the prt03 interior —
the dealer trip from a foreign interior walked into a wall exactly like the exit
route did before 02657775.

- travel_routing.TravelRouter.reachable(map, position, cell) -> bool | None: the
  cell's membership in the agent's own walkable region; None = no authority for
  the map (fail-open — the client grid is a lossy picture of the server's, so
  only an explicit False vetoes a leg).
- scripts.MerchantReachable protocol + _merchant_step(state, resolver, reachable):
  when the authority says the pinned dealer cell is in ANOTHER component, the
  outbound walk starts with the agent's OWN door (the resolver's first
  current-map leg); from prontera the route's own prontera leg (177,221) takes
  over, re-enters through the prt05 warp, and the dealer cell is same-component
  from there. No authority wired = the pinned leg unchanged (all pre-existing
  behavior pinned).
- Both goal scripts carry the authority: GrindScript gained merchant_reachable;
  FarmScript gained travel_resolver + merchant_reachable (it held neither); the
  brain wires both at both construction sites.

RED tests: the router's region verdicts (same region True / cross-component
False / unknown map None), the trapped outbound walking its own door (53,105),
the same-component dealer leg unchanged, and the no-authority fallback. Gate
6,659+65.

## 2026-10-29 ~13:5x — leg 38 mid-window: the fourth guild-path packet (0x014e) registered

Leg 38's loud transport reporting did its job: g01m00 (PipinWalker) died with
"unknown packet 0x014e" and the error tail DECODED — 4e01 d7000000 = 0x014e + the
menu-flag bitmap 0xd7. The persisted guilds (leg 33's creations survive the
volume) make the client ask for the guild menu interface on login; the pinned
server answers ZC_ACK_GUILD_MENUINTERFACE 0x014e (<menu flag>.L = 6B,
map/packets.hpp:842, clif.cpp:8755-8768). The same silent transport-loss class as
leg 35's three - the guild path keeps paying for its persistence.

Registered 0x014E: 6 in the packet table (source-cited block, byte-exact pins
reconciled across ALL seven digest/count tests: the close/cutin/wear-equip
chains, the emotion baseline, the dialogue-era set, the shop and skill-context
counts; each new digest read from its own pytest failure per the discipline).
The leg-38 run itself still carries the old table (its receipt row for g01m00
will show the transport loss) - the fix serves the legs after it.

Gate 6,662+65.

## 2026-10-29 ~15:4x — receipt: leg 38 — six of seven on the field, first e2e loot, s00's unwalkable spawn nailed

The Thursday window (day-3, 12:30-14:30 CET, all 7 personas) opened with every
agent ON TIME and held full cadence the whole leg: 1,397 decide requests /
1,397 responses (zero decide failures, heavengraph :8091), 18,768 actions, 775
plans authored, 50,227 runner steps / 0 step errors / 420 samples. Receipt
run/plain_host_receipts/population-receipt-38-1793272245.json.

FIELD VERDICT: 6 of 7 reached prt_fild08 (leg 37: 2 of 7) — the three prt_in
dwellers (NyxSong, PipinWalker, xXLunasongXx) walked their own interior doors
out per 02657775/453823b1 and the roster hunted the dense band (y 335-372).
COMBAT: 46 attacks across 6 agents (PoringMuffin14 15 + 8 rests; NyxSong 11;
RinceNyan 6); kills: 6 of 7 gained XP over the pre-read baselines, +30 base /
+12 job total. Attack gates nearly silent all leg (12 deferrals: 8
pending_walk + 4 resting — stop-and-swing healthy). KILLS LANDED but the
economy hop did not: sells 0 (zeny unchanged everywhere), though the
DROP->PICKUP hop is now CLOSED on the e2e world — RinceNyan holds Empty Bottle
+ Iron Ore picked up in the field (zeny unchanged rules out purchase). The
picklog stayed 0 rows despite the verified pickup — its write path is dead
again; the inventory table is the loot evidence.

SOCIALS at population scale for the first time: 2 guilds founded (NyxSong,
PipinWalker), 12 GuildInvites with 0 failures, 4 InviteToParty, 110 chats
sent / 203 heard, PartyChat on all six group agents.

s00 (YuffieFy81) was the single stand-still, now ROOT-CAUSED by cache probe:
pay_fild04 (204,165) is UNWALKABLE in the loaded map cache (db/map_cache.dat;
the merged pre-re set agrees; the server disagrees — it saved the char
standing there twice), nearest walkable (204,172), only 34/289 roam-box cells
walkable. Every MoveTo routed from an unwalkable origin: 3,300 authored / 0
executed / 0 mobs ever seen / 199 decides. The d692a66d deadlock fix did not
recur on the six field agents (ZERO stand-still among them). Named fix:
mark_walkable ground-correction (native_navigation.py:155) of a login cell the
server demonstrates, plus walkability-filtered roam targets for that 88%
unwalkable corner.

TRANSPORT: one loud loss all leg (PipinWalker, unknown 0x014e at the login
burst) — ConnectBackoff recovered inside 30s; the mid-leg hotfix e39bb69d
registered ZC_ACK_GUILD_MENUINTERFACE, so leg 39 expects zero. RECEIPT GAP:
_move_gate_reasons exist on the client but the plain-host samples carry only
attack_gates — ride them into the receipt next leg (this leg's move verdict
came from live position samples + the cache probe). LOGOFF-SAVE ARTIFACT: 3
chars saved AT SAVE POINTS on logoff (last==save), so DB last_map is not
field-presence truth — the traces are.

NEXT: (1) s00 login-cell ground correction + pay_fild04 roam-target filter,
(2) ride _move_gate_reasons in the receipt samples, (3) economy closure — the
sell trip, with RinceNyan's carried loot as the live test case, (4) leg 39
validates the 0x014e registration.

## 2026-10-29 ~16:1x — leg 38 follow-up: the own-cell ground correction + the move gates in the receipt

Leg 38's readout named s00's corner precisely: pay_fild04 (204,165) is UNWALKABLE
in the loaded client grid (nearest walkable 7 cells away; 34/289 roam-box cells
walkable) while the SERVER saved the char there twice — the tracked position
comes only from the received entry/0x0087 stream, so it is server truth and the
grid's picture of that corner is wrong. The d692a66d deadlock did not recur on
the six field agents; s00 authored 3,300 MoveTos / 0 executed / 0 mobs seen.

Two slices, both TDD:
- playing_runtime._move: when the tracked own cell is unwalkable per the grid,
  mark_walkable it (the server demonstrably placed us there) and note
  ground_corrected_own_cell. The leg-28 direct send then carries the walk (the
  server path-finds its own side) and the roam/reroll machinery engages from a
  walkable start instead of stopping.
- population_host_runner: the receipt samples now carry move_gates beside
  attack_gates (the w58/leg-38 reasons ride the receipt; no more invisible
  stand-stills).

Also closed from leg 38: the drop->pickup hop is CLOSED on the e2e world
(RinceNyan holds Empty Bottle + Iron Ore picked up in the field; the picklog's
SQL write path is dead AGAIN — inventory is the evidence). The 0x014e transport
down recovered by ConnectBackoff in <=30s; e39bb69d makes leg 39 expect zero.

Frontier: the economy closure — RinceNyan ended the leg carrying unsold loot;
the sell trip is the live test. Then WoE, sustained population, dashboard
control, benchmarks.

Gate 6,663+65.

## 2026-10-29 ~19:45 — receipt: leg 39 - kills on 5 of 7, transports zero, but s00's pocket held and the sell trip never fired

Thursday 17:00-19:00 window (launch 16:41, 43090 steps, 0 step errors, no
tracebacks). TRANSPORT DOWN = 0 — the e39bb69d 0x014e registration holds; GuildInvite
failed = 0. THE VERDICT by question:

- FIELD: 6 of 7 on the fields during the window (4 roaming prt_fild08 wide:
  NyxSong (84,349), RinceNyan (173,360) after walking out of prontera,
  zeny_wing (266,359), xXLunasongXx + PoringMuffin14 roaming the (150-230,330-370)
  band; s00 on pay_fild04; PipinWalker stayed in prontera (208,266), 0 attacks,
  26 socials). Leg 38 was also 6/7.
- s00 THE POCKET HELD: move_gates = {target_unwalkable: 8} — every roam target
  rejected; ground_corrected_own_cell NEVER fired. Root finding: the correction
  triggers on a server-DEMONSTRATED unwalkable own cell, but the server SILENTLY
  IGNORES walks sent from an unwalkable own cell — the demonstration cannot
  arrive, so 7b05e66a's trigger is unreachable by construction for a char that
  spawns parked in the bad cell. The state_ticks show it alive (86 decides→217,
  hp full, 1 adjacent monster, 1949 MoveTos in-window) and unmoved at (204,165).
- MOVE/ATTACK GATES (receipt, cumulative): attack_gates pending_walk
  14/2/5/0/5/0/0 + resting 1/3 (RinceNyan ground 43 Rests in-window — grinding
  at low HP, stop-and-swing discipline working); move_gates await_pending
  6-8 each, no_route_direct 2 (PipinWalker), no_position_or_dead 2 (zeny_wing),
  target_unwalkable 8 (s00). rx_error / dispatch_errors: clean on all 7.
- ATTACKS: 107 in-window (NyxSong 49, zeny_wing 34, xXLunasongXx 12,
  RinceNyan 8, PoringMuffin14 4, PipinWalker 0, s00 0). Two agents ground
  IN PLACE at mob clusters (NyxSong/zeny_wing stationary for ~1h while attacking).
- KILLS: 5 of 7 above their pre-window baselines — NyxSong +16/+10 base/job,
  RinceNyan +6/+2, zeny_wing +6/+6, xXLunasongXx +6/+3, PoringMuffin14 +9/+3
  (4 attacks → +9 base: the pooled-target discipline pays). PoringMuffin14
  killed with 4 swings; PipinWalker and s00 flat (0 attacks each, different
  reasons: town vs pocket).
- THE SELL VERDICT: NO TRIP. Zeny flat at baselines on all 7 (max 5z),
  shop_offer never opened, npc_stage None end-to-end; RinceNyan still carries
  Empty Bottle + Iron Ore + Knife. The w84-proven merchant chain did not
  engage — the agents never decided to go to town to sell.
- SOCIALS: 2 NEW GUILDS formed live — guild 2 NyxSongGuard (master NyxSong),
  guild 3 PipinWalkerGuard (master PipinWalker); parties regrouped: party 3
  NyxSong+zeny_wing, party 2 PipinWalker+xXLunasongXx+PoringMuffin14,
  RinceNyan solo in party 4. 69 social actions in-window.

Receipt: run/plain_host_receipts/population-receipt-39-1793288428.json.
NOTE: the receipt samples' wire_sent/moves are post-logoff zeros — in-window
activity truth is the traces (window-filtered census above).

NEXT: (1) s00's release needs a REACHABLE trigger — repeated target_unwalkable
+ zero position change while standing must mark the own cell walkable (or check
the entry-frame cell at login against the grid and correct there), since the
server will never demonstrate the cell; (2) the economy closure — the sell trip
needs a decide-level trigger (sellable loot + no planned kill target ⇒ go_town),
RinceNyan's carried loot remains the live test case; (3) PipinWalker's town
stickiness (0 attacks, 26 socials — the guidance/roam never pulled it to a
field).

## 2026-10-29 ~20:3x — leg 39 follow-up: the field loot is sellable stock + the sealed-pocket escalator

Leg 39's verdict (aa1703a9): 6 of 7 on the fields held, 107 attacks, 5 of 7 above
baseline XP (kills at population scale), TRANSPORT DOWN 0 (e39bb69d holds),
socials live (2 new guilds, 2 parties). Two defects named, both fixed TDD:

(1) THE SELL TRIP NEVER ENGAGED because the merchant want's stock set only knew
Jellopy 909 + Chrysalis 915 - RinceNyan carried Empty Bottle 713 + Iron Ore 1002
(the leg-38 pickups) and nothing decided to go to town. The stock set is now the
pinned mob_db drops of the field species (Pupa 1008: 915/938/1002; Drops 1113:
909/713; Lunatic 1063: 705/949; Poring 1009: 917; Fabre 1007: 914 - mob_db.yml +
item_db_etc.yml, pinned e985006171d2). Any of them in a Novice's known inventory
now drives the dealer trip (the w84-proven chain owns the exchange).

(2) s00's pocket HELD and the ground correction never fired: the correction's
predicate is the cell's walkability, but s00's cell is walkable-in-grid while
every NEIGHBOR is walled - shortest_path dies, the direct sends are
server-refused, and the radius-2 reroll finds nothing (target_unwalkable x8,
1,949 MoveTos, zero movement). The sealed verdict now ESCALATES once per own
position to radius 12 (nearest_walkable, ring order) and direct-sends the far
walkable cell (target_unwalkable_escalated) - the server path-finds its own side
(the leg-28 rule); a second sealed verdict at the same position is the honest
stop (escalated_target_dead). The roam box's 34 walkable cells are within 12.

Gate 6,665+65.

## 2026-10-29 ~23:4x — leg 40: the sell trip STILL never engaged at population scale; the escalator fired once and the pocket held

Leg 40 verdict (run/plain_host_receipts/population-receipt-40-1793302886.json,
window 21:00-23:00 Madrid, all 7 personas, day-3 schedule): 43,080 steps, 0
errors, TRANSPORT DOWN 0, "GuildInvite failed" 0, clean open (7/7 online with
decides flowing ~3 min after 21:00 - the healthiest opening to date) and clean
23:00 close (7/7 offline in the samples).

THE SELL VERDICT: DID NOT ENGAGE. shop_offer was never non-null on any of the
360 receipt samples, npc_stage never set, zero NpcDialogue/shop trace kinds
20:00-22:00 UTC, and zeny is unchanged for all 7 (5/3/0/4/0/0/0). RinceNyan
still holds Empty Bottle 713 + Iron Ore 1002 after 170 decides - the 4ffc515d
stock-set fix made the items SELLABLE but the goal layer never selected the
trip. zeny_wing even walked a full prontera corridor to (216,133) on social
premades without opening a deal. The config fix alone does not fire the trip:
NEXT, a decide-level trigger (sellable stock held + no planned kill target =>
go_town), TDD on RinceNyan's exact stock as the fixture.

s00 (YuffieFy81): the escalator FIRED exactly once (target_unwalkable_escalated)
and the radius-12 direct-send also failed (escalated_target_dead on 8 samples) -
the honest stop held per design and s00 never left (204,165): distinct sampled
positions = 1, 3,375 MoveTos, 0 attacks, 0 exp. ground_corrected_own_cell fired
once (the leg-39 correction works). The pay_fild04 pocket exceeds a radius-12
escape; cheapest next step is a fixture save-move (the fx0 precedent) or a
wall-follow/radius-sweep law.

The rest: field count 6 of 7 (every group member entered prt_fild08 during the
window; matches legs 38/39). Attacks 69 total: xXLunasongXx 28 (3 targets) and
PoringMuffin14 25 (3 targets) - the two campers; rovers authored ~3.3-3.5k
MoveTos each (await_pending 12,539 remains the approach-pacing frontier;
attack:pending_walk 1,965 = stop-and-swing discipline; rerolled_target_dead
2,451 + escalated_target_dead 2,538 = roam-target churn). KILLS: 6 of 7 above
baseline XP at the e2e world's 1x rates (+1..+5 each: NyxSong +2/+1, RinceNyan
+2/+1, zeny_wing +2/+2, PipinWalker +1/+1, xXLunasongXx +4/+5, PoringMuffin14
+4/+5; s00 zero) - the first leg where both attack leaders converted. NyxSong
looted a Jellopy 909 (inventory ground truth). Socials: guild rows UNCHANGED
from leg 39 (NyxSongGuard, PipinWalkerGuard stand; this leg's FoundGuild/
GuildInvite actions repeated without new guild rows and without failures);
6 of 7 in parties at readback (4 party rows; s00 solo); 133 chat_sent, 87 LLM
escalations.

## 2026-10-29 ~00:1x (Oct 30) — leg 40 follow-up: the sell arm survives the knife

Leg 40's verdict (baa0cb76): 6 of 7 on the fields held, 69 attacks, 6 of 7 above
baseline XP, TRANSPORT DOWN 0 — and THE SELL TRIP NEVER ENGAGED despite 4ffc515d
making the loot sellable. Mechanism: merchant_drive_cell RELEASED the whole drive
when a wanted weapon is held — and every agent has carried the fixture knife
(1201) since 2b0f249e. The stock-set fix never got a chance to fire.

Fix: the weapon release now gates only the BUY arm. The SELL arm (sellable stock
held, weapon or not) walks the trip; a weapon holder with no stock and no zeny
still releases to the field. Both arms need a KNOWN inventory + a pinned route
map (unchanged fail-closes). RED tests: the armed-and-stocked state gets the
drive cell; the armed-and-empty state releases. Gate 6,667+65.

s00's pocket: the radius-12 escalation fired once and the far send was
server-refused too (escalated_target_dead x8) — the pocket exceeds radius 12.
The pragmatic release is the fx0-precedent save-move (the SQL last-position
reset), applied before the next leg; the radius-sweep/wall-follow law stays a
named option if the pocket recurs elsewhere.

## 2026-10-30 ~00:4x — leg 39/40 follow-up: THE s00 ROOT CAUSE IS THE MISSING MAP CACHE ENTRY

Discovered while placing s00's save-move: the e2e runtime's client-side
map_cache.dat (.work/runtime/population-live/db/pre-re/map_cache.dat) carries
only alberta/izlude/morocc/prontera/prt_church/prt_fild05/prt_fild08/prt_in —
pay_fild04 IS ABSENT. The map-server loads it (s00 logs in and stays online
there), so the docker image's conf/build differs from the public source tree
whose mapcache the runtime copies. Consequence: every walkability check for
s00's moves had NO AUTHORITY — no grid, no route, no roam, no escalation; the
leg-38/39 client-grid analyses of s00's pocket were analyses of a MISSING map,
not of disagreeing geometry. The ground correction (7b05e66a) and the escalator
(4ffc515d) never had a grid to work with on pay_fild04.

THE NEXT SLICE (before any leg with s00): get pay_fild04 into the client-side
cache — either regenerate the runtime cache from the docker image's own
mapcache (it must carry the map: the server loads it) or add pay_fild04 to the
pinned build's maps_athena.conf and rebuild. Then re-run the pocket analysis
against REAL cells: the save-move to (206,175) stands either way.

Also landed this session: 8599e32f — the sell arm survives the wanted weapon
(the knife release gates only the BUY arm; sellable stock drives the trip).
Leg 40's sell verdict (baa0cb76) named it: the fixture knife in every inventory
kept the old single release from ever firing the drive.

### RETRACTION (same day, ~01:2x) — the "missing pay_fild04 cache entry" claim above is WRONG

The 5a0c7b53 entry names a false root cause. Verified: the RUNTIME cache the
runner actually loads is .work/runtime/population-live/db/map_cache.dat (the
3 MB primary; playing.py:148 loads it TOGETHER with the trimmed pre-re file),
and pay_fild04 IS in it — the leg-38 analysis (204,165 unwalkable, nearest
walkable (204,172)) already knew this. I probed only the trimmed pre-re file.
The true state: the map is loaded and analyzed correctly; (204,165) is a real
wall the server saved twice; the ground correction marks it walkable but the
server still refuses the escape walk (leg 40: escalated_target_dead x8 — the
server path-finds from a blocked cell and fails).

VERIFIED FIX in place: the save-move to (206,175) — walkable in the runtime
cache (checked (206,175)/(206,176)/(205,175) all True) — releases s00 to real
cells. No cache work is needed. The rathena/db/pre-re/map_cache.dat merge from
the false lead has been reverted (submodule content restored).

## Leg 41 — Friday 2026-10-30, 01:00-03:00 Madrid (00:00-02:00 UTC), day 4 — THE FIRST SELL ZENY

Head e9aa6457 at launch (00:26 Madrid, duration 10800s, receipt
`population-receipt-41-1793316328.json`: steps 43053, errors 0). Launch fix
first: the leg-41 schedule file at HEAD was a review document, not the runner
format (`{"persona_id": [[day, start, end]]}`) — the runner died on
`KeyError: 'pop_0003_g00m00'`; rewrote it to `[[4, 1.0, 3.0]]` x7 (the
convention of every prior leg) and relaunched.

VERDICT: **PASS — the economy-closure leg landed its goal.** All four
acceptance criteria hold:

1. SELL LIST REACHED: the receipt's `shop_offer` field never read non-null at
   a 30s sample instant, but the sell list reaching the client is proven by
   `npc_stage='unsupported_shop'` (the stage name for a RECEIVED 0xC4 market
   packet — native_npc_dialogue.py STAGES) on NyxSong x2 and RinceNyan x2
   samples, plus the executed chain. The offer field is a transient decoded
   view; npc_stage + the completed sell are the stronger evidence.
2. **FIRST SELL ZENY EVER: NyxSong 5 -> 8 (+3 = exactly Jellopy 909's 3z sell
   price)** — DB ground truth. Complete wire chain at 00:16 UTC:
   `TalkToNpc -> NpcShopSellOpen -> NpcShopSell` all at prt_in (173,130), the
   Weapon Dealer interior — the merchant trip (walk into the interior, deal,
   sell) worked END TO END. DB inventory: 909 gone; the fixture knife (1201)
   correctly kept (sell = Jellopy only).
3. s00 MOVED ON REAL GROUND: traces show 2 distinct positions on pay_fild04,
   (206,175) login cell -> (207,176), plus 3 `Attack` actions in the first 35s
   of the window. The receipt's 30s sampler caught only (207,176) (it moved
   before the first sample). The DB reads last=(204,165)==save — the known
   logoff-save fallback to the save point, NOT evidence of no movement;
   movement truth is the trace series.
4. TRANSPORT CLEAN: zero TRANSPORT DOWN, rx_error=0, dispatch_errors=0, all 7
   agents online 33/33 ticks, decides 155-277 each.

KILLS (DB exp deltas vs the 00:21 baseline): zeny_wing +2/+1, xXLunasongXx
+2/+1, PoringMuffin14 +8/+4 = 1 + 1 + 4 Porings (2/1 base/job each, mob_db)
= 6 kills. Socials: zero new rows — the FoundGuild/GuildInvite/InviteToParty
actions (NyxSong: FoundGuild 1 + GuildInvite 6; PipinWalker: FoundGuild 1 +
GuildInvite 6) were replays; guilds NyxSongGuard/PipinWalkerGuard and the
party set stand from leg 39 (cumulative-table rule held).

GATES: NyxSong/RinceNyan move_gates.await_pending ~2319 (sell trip walking,
no attack gates — never authored an Attack); farmers carried
attack_gates.pending_walk + no_route_direct (PoringMuffin14 x99 — the loudest
farmer, 142 distinct positions); s00 pending_walk 290 + resting 289 (attacked,
then idled at its spawn cell — it has no farm plan on pay_fild04's spawn
declaration yet).

THE NEXT SLICE — extend SELLABLE_ITEM_IDS to the carried loot species:
RinceNyan reached the dealer (TalkToNpc 00:14 UTC, received the C4 twice) and
NEVER sent NpcShopSellOpen — `_sell_open_action` returns None when
`shop_sellable_stock(...) <= 0`, and `SELLABLE_ITEM_IDS = (909, 915)`
(scripts.py:230) does not include the 713 Empty Bottle + 1002 Iron Ore it
carries. Re-derive the set from the pinned drop tables (prt_fild08/pay_fild04
`Drops:` -> item_db ids, per the economy-want rule) so every loot species can
fund a sell leg. SECONDARY: s00's release is NOT sticky across logouts — the
logoff save fell back to the save point (204,165), so leg 42 logs it back into
the sealed pocket unless the last_point is re-pinned pre-window or the logoff
write is fixed to keep the live position.

## 2026-10-30 03:5x — leg 41: THE FIRST SELL ZENY + the 713/1002 sellable-stock fix

Leg 41 (be486068, window 01:00-03:00) closed the first hop of the economy:
NyxSong walked the dealer trip and SOLD its Jellopy — zeny 5 -> 8 (+3) through
TalkToNpc -> NpcShopSellOpen -> NpcShopSell, the first sell zeny ever. s00
walked real pay_fild04 ground (save-move verified). All 7 online, zero
TRANSPORT DOWN.

The named remainder: RinceNyan held 713 Empty Bottle + 1002 Iron Ore AT the
dealer for 100+ decides and its sell never opened — SELLABLE_ITEM_IDS was
(909, 915) only, so shop_sellable_stock returned 0 and the sell leg was
skipped while the DRIVE (merchant_drive_cell's separate sellables set) fired
correctly. Fixed: SELLABLE_ITEM_IDS now carries the full prt_fild08 drop set
(705 Clover, 713 Empty Bottle, 909 Jellopy, 914 Fluff, 915 Chrysalis, 917
Talon, 938 Sticky Mucus, 949 Feather, 1002 Iron Ore). RED test
test_empty_bottle_and_iron_ore_are_sellable_stock. Gate 6,668+65.

Next leg: RinceNyan's sell opens and lands — then the 50z knife purchase
(zeny 3 + sell proceeds vs the 50z price), then equip.

## 2026-10-30 ~04:35 — the s00 pocket mechanism is the SAVEPOINT (204,165) + leg 42 armed

The leg-41 trace closes the s00 question: it logged in at the save-move
(206,175), stepped out (207,176), took ~43 damage in the first minute (86->43,
NOT a death), and held (207,176) in every state_tick all window — yet the
server logged it out at (204,165), the pocket cell, with NO 0x0087 walk in
between (the tracked position never moved after 00:00:30). Two facts now
pinned:

1. s00's SAVEPOINT in the char table IS (pay_fild04, 204, 165) — the pocket
   cell. Every death/respawn parks it inside the sealed run; the walk-out is
   refused server-side (leg 40). That is the multi-leg "sealed pocket"
   mechanism.
2. The leg-41 logout divergence (server (204,165) vs tracked (207,176), no
   0x0087 between) is an OPEN question: a server-initiated reposition the
   client never saw — the unregistered-packet class (leg 35). Sweep with
   .work/engagement-diagnosis/leg35_unknown_sweep.py on a diagnostic pass.

OPERATIONAL RESET applied: s00 save_map/save_x/save_y AND last_map/last_x/
last_y -> pay_fild04 (206,175) (verified walkable in the runtime cache). Any
future respawn now lands on real ground.

Leg 42 scheduled (run/reviews/population-live-schedule-leg42.json): Friday
05:00-07:00 Madrid. Primary acceptance: RinceNyan (713+1002, saved AT the
dealer) sells through the fixed SELLABLE_ITEM_IDS (3b8bdac5).


## 2026-10-30 ~06:20 — leg 42: THE FIX PROVEN — RinceNyan sells 713+1002 (+28z, first minute); s00 walks free ground; next: the post-sell stall + s00's dead attacks

Window 05:00-07:00 Madrid CET = 04:00-06:00 UTC (the schedule DOC's
"03:00-05:00 UTC" was a CEST leftover; the runner works Madrid-local so it
changed nothing). The schedule file was DOC-shaped AGAIN (2584 bytes of
brief) — rewritten in place to the runner mapping
`{persona: [[4, 5.0, 7.0]]}` and committed (bbf3403e) before launch, the
doc staying in git history. Launch 03:27:34 UTC (receipt
population-receipt-42-1793330854.json), duration 9600 s, DONE steps 38280,
errors 0, ZERO TRANSPORT DOWN, all 7 online throughout (decides 158-349).

PRIMARY ACCEPTANCE MET in the window's first minute: RinceNyan ran
TalkToNpc(110001762) -> NpcShopSellOpen -> NpcShopSell
sales=[[2,1],[3,1]] at 04:00:04-08 UTC at the dealer cell (prt_in 172,129);
DB zeny 3 -> 31 (+28 = bottle + iron ore) and 713/1002 are GONE from its
inventory. The SELLABLE_ITEM_IDS fix (3b8bdac5) is proven end-to-end. It
even browsed NpcShopBuySelection right after — but nobody reached 50 z
(max 31), so the buy-list condition correctly never armed
(shop_offer 0 across all 320 samples).

s00: the savepoint reset held — 37 distinct sampled positions on
pay_fild04 (spawn (206,175) -> (247,200)), its DB logout row last==save
(206,175) (the logoff-save fallback, walkable either way). The multi-leg
sealed pocket is DISARMED: no death parked it, because the savepoint no
longer points into the pocket.

Kills (DB exp, ground truth): 6/7 gained — NyxSong +12/+4 (exactly two
Lunatics), PipinWalker +10/+4 (2 Poring + 1 Lunatic), PoringMuffin14 +2/+1
(one Poring), zeny_wing +4/+5, xXLunasongXx +2/+4. YuffieFy81 (s00) ZERO
despite 349 decides and 554 actions of movement.

FINDING 1 — the post-sell stall: RinceNyan stood at the dealer for the
remaining ~115 min (ONE distinct position all window), its npc_stage
reading blocked x253 / opening x1 / unsupported_shop x1. After the sell
emptied its stock the sell arm kept engaging a dead shop dialog instead of
handing back to the field grind. The sell trip needs a POST-sell re-route
(the sell arm must not re-arm on empty stock).

FINDING 2 — s00's attacks never land on pay_fild04: attack_gates
pending_walk x214 / resting x213, zero exp. It walks (37 positions) but
nothing dies. Field density or the pending-walk gate on that map — next
diagnostic pass.

Also: the logoff-save fallback (last==save) hit 4/7 this leg (zeny_wing,
PipinWalker, xXLunasongXx, s00); NyxSong (prt_fild08 213,318) and
PoringMuffin14 (prt_fild08 176,351) kept true field positions.

Next leg: post-sell re-route for the economy arm (RinceNyan must leave the
dealer once stock is empty) + s00's attack landing on pay_fild04; the 50z
knife purchase stays queued behind them.

## 2026-10-30 ~07:3x — the EQUIP hop is DB-proven on all 7 agents

Post-leg-42 readback: every agent's knife (nameid 1201) carries equip=2
(EQP_HAND_R) in the inventory table — the wear-equip progression
(_equip_progression -> native_gameplay.equip, 0x0999 ack as authority) works
live on the whole population. The economy loop's proven hops: farm -> kills ->
drops -> loot-first -> SELL (2 of 2 legs: NyxSong +3, RinceNyan +28 through the
fixed SELLABLE_ITEM_IDS) -> EQUIP (all 7 worn). The last unproven economy hop:
the 50z BUY (C6 buy list + purchase).

s00's zero-kill is therefore NOT the weapon (it hits for 12): the attack->kill
conversion on pay_fild04 (Pupa 60 HP at 1x rates = 5 hits) is the remaining
combat question, plus the post-sell dealer stall the leg-42 receipt names.

Leg 43 acceptance shape: RinceNyan (31z) + one farm-and-sell cycle crosses 50z
-> NpcShopPurchaseOpen in the trace -> the economy is closed end to end.

## 2026-10-30 ~07:5x — leg 43 armed: the 50z BUY with the sanctioned fixture

Every agent holds a (worn) knife, so the BUY arm (no weapon + zeny >= 50) can
never fire naturally - the buy hop had no live path. Fixture applied (the
sanctioned class: Emperium for the guild probe, knife 2b0f249e): zeny_wing
(300002) zeny 0->60 + knife DELETEd. The BUY arm now fires for it: dealer trip
-> 0x00C4 dealtype type 0 -> 0x00C6 buy list -> purchase 50z -> the knife
returns (DB evidence: zeny 60->10 + nameid 1201 back in inventory).

Leg 43 scheduled (Friday 08:30-10:30 Madrid). Secondary: RinceNyan's second
sell after farming; carry-overs: the post-sell dealer stall, s00's attack->kill
conversion (weapon ruled out).

## 2026-10-30 ~09:55 — the leg-43 buy stall: a dialogue-await latch (named mid-window)

zeny_wing (the 60z/no-knife buy fixture): window open -> PartyChat ->
TalkToNpc(npc_id=110000883) from its save (150,143) -> 15 clicks over 2 min
while walking east to (158,135) -> NpcNext(110000883) at 07:32:08 -> then
SILENCE: 108 decides over 2h17m with ZERO actions. The buy never fired; zeny
stays 60, no knife.

Named shape: a DIALOGUE-AWAIT LATCH. The click/NpcNext sequence opened (or
believed it opened) a dialogue with npc 110000883 — which is NOT the Weapon
Dealer (that one lives at prt_in,172,130) — and the dialogue state sits
awaiting a menu/dealtype that never arrives. The leg-24 recovery only expires
the BEGIN deadline (_expire, deny_origin='timeout', 5s); an OPEN dialogue
awaiting a response has NO timeout, so neither the fail-closed barrier nor
_retry_blocked_dialogue ever engages. Two candidate root layers for the fix
slice: (1) the missing await timeout (open dialogue + expected response
absent for N s -> deny_origin='timeout' -> close/re-begin); (2) WHY the
merchant leg clicked an npc at (150,143) instead of walking the route cell
(177,221) first — the drive's engage path skipped the walk leg.

The steered shepherd readout (npc_stage + move_gates for g00m02) confirms
which. Fix slice: TDD the await timeout + re-check the drive's walk-then-click
ordering; leg 44 re-proves the buy.


## 2026-10-30 10:45 — leg 43 CLOSE: the buy never armed — two stacked gates (receipt 001b4738 + population-receipt-43-1793343336)

Window held: 7/7 online 239-240/320 samples each, 0 TRANSPORT DOWN, 38302
steps, 0 step_errors, decides 148-216 per agent. The BUY did NOT land:
DB zeny_wing zeny 60->60, no knife; receipt shop_offer 0 samples;
move_gates {} (ZERO MoveTos authored all window); npc_stage samples
opening x1 -> next x2 -> BLOCKED x247 (npc 110000883 YuPi#pront, the
novice guide 2.8 cells from the stall cell 158,135). Secondary not
landed: RinceNyan zeny 31->31 despite field kills (exp 40->44/33->38);
zero Loot actions authored, no sellable stock, no return trip. Zero zeny
movement in the whole population; only exp moved (NyxSong +8/+3 and
PipinWalker +8/+3 = one Poring+Lunatic pair each; xXLunasongXx,
PoringMuffin14, s00: zero kills; s00's move_gates read
escalated_target_dead 1916 around pay_fild04 (208,183) — the pocket in a
new cell).

GATE A (decisive, arithmetic): the runtime NEVER learned the zeny. Zero
in-window decide states carry non-null zeny for ANY agent; the 0xB0/B1
currency receipt arrives only when a zeny-paying transaction answers
(RinceNyan's 117 x "zeny":31 decide states are the leg-42 post-sell
session tail — native_shop_context._consume_currency), never at login.
So state.zeny is None all window, merchant_drive_cell's
`affordable = type(state.zeny) is int and zeny >= 50` is False, and with
the fixture-emptied inventory has_stock is False too: the drive returned
None all window. The 60z exists only in the DB. The clicks were NOT the
merchant engage: they were the novice-guidance lane talking the guide
NPC (needs_npc_preparation / NpcGuidanceScript; the drive cell
(177,221) was never computed, so there was no engage that "skipped the
walk" — candidate (2) of the 09:55 entry is disproven).

GATE B (would have blocked the buy even with zeny known): the retained
guide dialogue sits at stage "blocked" (pages/options empty — a dialog
frame the client could not drive). _dialogue_route diverts every
step_script before the goal script; for farming goals
_grind_dialogue_block_expired burns its budget on the first minute's
NpcNext loop, then _dialogue_clear_drive has NO reviewed send for
"blocked" (it handles next/close/unsupported_input/string_input/menu),
the stage never enters _dialogue_cleared_stages, and _npc_step returns
an EMPTY outcome forever — GrindScript (where _merchant_step lives)
never ran again: plans 0, actions frozen at (158,135). Candidate (1) of
the 09:55 entry is the right family; the precise mechanism is the
send-less stage in the divert loop, not a missing await timeout.

Next slice (one TDD slice, two RED tests): (a) login zeny receipt
reachability — frame-capture a login to decide whether the pinned server
sends ZC_ZENY and the framer/consumer drops it, or never sends it, then
fix that one hop so affordable is computable in a fresh session;
(b) a reviewed clear drive for stage "blocked" (NpcClose) or a bound on
the send-less divert, so a blocked frame cannot starve the goal script.
Leg 44 re-proves the buy; the fixture stays applied and reusable
(zeny_wing 60z, no knife — verified unchanged at close).

## 2026-10-30 ~12:1x — the leg-43 two-gate fix: SP_ZENY ingest + the blocked-dialogue close drive

Leg 43's stacked gates (668e5714), fixed in one TDD slice (3 RED -> GREEN):

(1) THE ZENY OBSERVATION. The pinned server broadcasts the balance via
clif_longpar_change = ZC_NOTIFY_PARAM2 0x00B1 parameter 20 (clif.cpp:3735,
case SP_ZENY; SP_ZENY = 20 in the pinned _sp enum, map.hpp:501). The tracker
had no handler: state.zeny was None all window (the shop-context balance is
only populated inside the shop loop) and the merchant drive's affordable gate
could never arm. Now: 0x00B0 param 20 AND 0x00B1 param 20 both ingest into
tracker view.zeny; build_native_state prefers the tracked balance with the
shop-context balance as fallback (zeny_receipt unchanged). The warp/continuity
tests reconciled: the tracked balance survives an ordinary warp and the shop
context's clearance; a WIRE SWAP still resets it (a fresh session knows
nothing until re-delivery).

(2) THE BLOCKED-STAGE STARVE. _dialogue_clear_drive had no reviewed drive for
stage 'blocked', so the fail-closed divert fed _npc_step's empty outcome
forever (zeny_wing: NpcNext at 07:32, then 2h17m of decide-only ticks). Now a
blocked dialogue gets ONE NpcClose drive per session (the cleared-stages set
bounds it): the close passes _npc_action's actuation gate (it only eats
Attack/Loot/MoveTo/TalkToNpc), terminates the deal server-side, and the
script resumes. The retry budget (3/epoch) still runs first - the close is
the escalation after it.

Gate 6,671+65. Leg 44 re-proves the buy: zeny_wing (60z fixture) should arm
the drive on the tracked balance, walk the dealer, open the C6 buy list,
purchase the knife (zeny 60->10, knife back in inventory).

## 2026-10-30 ~13:1x — the login zeny is NEVER sent on this pin; the fix shape is a runner-side seed

Leg 44's live trace settles it: zeny_wing's state_tick zeny is None even after
61f44ef6's 0x00B0/0x00B1 param-20 ingest. Pinned-source reading: the map-server
emits SP_ZENY only on a CHANGE (pc.cpp:5810/5844 pay/get, trade.cpp, mail.cpp —
all via 0x00B1 param 20, clif.cpp:3735); the login entry packets
(ZC_ACCEPT_ENTER 0x0073/0x02EB, clif.cpp:751-753) carry position only, and
clif_initialstatus has no zeny field. A real client knows its wallet from the
CHAR-server character list — a clientless agent never parses that channel.

THE GOOD NEWS from the same trace: the 61f44ef6 close-drive fix WORKS LIVE —
the same TalkToNpc latch that starved 2h17m in leg 43 now terminates in ~6s
(TalkToNpc -> NpcNext x2 -> NpcClose at +6s -> the script resumed and zeny_wing
is walking freely).

FIX SHAPE (next slice, TDD): the runner seeds each agent's balance from the
fixture DB (the shepherd reads the char table pre-launch anyway — the same
ground truth any player's screen shows; parity, not a shortcut).
--seed-zeny-file {persona: int} -> build_host -> the client's initial tracked
zeny (used only until the wire delivers its own change update). Then leg 45
proves the buy.

## 2026-10-30 ~14:2x — the runner-side zeny seed (TDD, 4 hops) — the wallet parity fix

The login zeny is never sent on this pin (the previous entry): a real client
reads its wallet from the char-server character list, which a clientless agent
never parses. Fix: the runner passes the fixture DB's true balance per persona
(the same number any player's screen shows — parity, not a shortcut).

Wiring (each hop one test): --seed-zeny-file {persona_id: balance} ->
load_seed_zeny (playing.py) -> AgentHost(seed_zeny_by_persona=...) ->
ScheduledAgent(seed_zeny=...) -> PlayingClient(seed_zeny=...) -> the balance
authority chain in _zeny_balance: tracked wire observation (0x00B1 param 20)
> shop-context receipt > the seed. A wire-delivered balance always overrides
the seed; a wire swap still resets to unknown.

Shepherd launch delta: write run/worlds/population-live/seed-zeny.json from the
pre-launch char-table readback and add --seed-zeny-file to the runner command.
Gate 6,674+65.

## 2026-10-30 ~14:50 — leg 44 window: the close-drive un-starve is LIVE-proven; the buy voided by the missing login zeny (as predicted); seed-zeny.json delivered; NEW defect class: death mid-window = permanent silent stall

Window 12:30-14:30 Madrid (11:30-13:30 UTC; the brief's "10:30-12:30 UTC" was
the CEST conversion trap again — the runner's CLOCK: line is Madrid-local and
the first tick landed at 11:30:08 UTC exactly). 7/7 online at open, decided
186-519x each, 0 TRANSPORT DOWN, DONE steps 38296 errors 0
(receipt population-receipt-44-1793358352.json, launch 11:05:52 UTC).

The steer's three readout points:

1. CLOSE DRIVE (61f44ef6 gate 2): zeny_wing opened the SAME guide npc
   (110000883) at window-open: TalkToNpc 11:30:08 -> NpcNext 11:30:10 ->
   NpcClose 11:30:14 — the latch held ~6s vs leg 43's 2h17m silent divert.
   The receipt's npc_stage is non-null in exactly ONE sample, and 210 MoveTos
   followed with zero frozen stretches: the script stayed un-starved all window.
2. TRACKED ZENY: stayed None ALL window for ALL agents (zero non-null zeny in
   any state_tick or decide-state) — confirming the seed's necessity. The buy
   never armed (shop_offer non-null in 0 samples, no NpcShopPurchaseOpen);
   zeny_wing's DB row ended zeny=60 with the knife still absent (the fixture
   held), so the acceptance "zeny 10 + knife back" was NOT met — expected,
   since the parser has no login frame to parse on this pin.
3. SEED DELIVERED: run/worlds/population-live/seed-zeny.json written at close
   from the char-table readback (all 7 personas; zeny_wing 60). Leg 45
   launches with --seed-zeny-file run/worlds/population-live/seed-zeny.json.

Economy/kills (DB exp deltas over the pre-window baseline): xXLunasongXx
+23/+14, NyxSong +12/+6, PoringMuffin14 +6/+3, PipinWalker +5/+3, RinceNyan
+4/+2, zeny_wing +1/+1, YuffieFy81 0. Zero zeny movement anywhere (no sell
trip engaged — RinceNyan, the only candidate, died 43 minutes in).

NEW DEFECT CLASS — death mid-window = permanent silent stall: RinceNyan was
swarmed at prt_fild08 (264,364) (hp 86->5 with DamageTaken 7 arriving at
11:47:37 = dead) and YuffieFy81 at pay_fild04 (244,193) (hp 86->9 at
12:00:4x). After the death both kept ticking decides on a FROZEN tracker
state — map/pos stuck at the death cell, hp frozen at 43 = exactly max/2 —
and authored ZERO script steps for the remaining ~2h/1.5h, while the SERVER
teleported the body to its SAVE CELL at hp 43 (DB: last_map/last_x/last_y ==
save_map/save_x/save_y for both, hp column 43). The receipt names the
client-side half: YuffieFy81's move_gates carry no_position_or_dead x840 —
the runtime gates the moves as dead but nothing resumes scripting (no
re-begin at the save cell). Open question: the vendored rathena's
pc_setrestartvalue heals a respawn to FULL (86), not 43 — the running
container either carries a respawn patch or is not this exact pin. Cost:
~2 agent-hours plus RinceNyan's secondary sell. Next slice candidate: a
death-recovery drive — on dead detection, re-begin at the save cell (the
gate exists; only the resume is missing).

## 2026-10-30 ~16:4x — the death-recovery fix: a map change clears the stale death latch

Leg 44's new defect class (89bccea5), fixed: after the own-vanish death
(0x0080), the save-cell respawn warps via pc_setpos -> clif_changemap
(0x0091; pinned rathena src/map/pc.cpp:7118; pc_respawn -> pc_setpos,
pc.cpp:9653) — and the tracker's 0x0091 branch re-seeded position/map but NOT
the death latch, so the agent dead-gated forever (no_position_or_dead x840)
while the server body stood alive at the save cell.

Fix: the 0x0091 handler clears a stale latch (alive False -> True) — a map
change IS the server pointing at a live body; there is no dead-body-warp
case (only pc_respown warps a dead one). The old [warp] contract
("life authority never from positive hp" pinning the latch as warp-proof) is
reconciled with the leg-44 falsification: positive hp ALONE still never
resurrects (the [authless] case), a received 0x0148 does (the resurrection
case), and now a post-death warp does too (the [warp] case — the pose
machinery re-engages: the stand request fires instead of the dead-gate's
silence). RED test
test_map_change_after_own_death_clears_the_death_latch. Gate 6,675+65.

## 2026-10-30 18:3x — leg 45 (Fri 16:00-18:00 Madrid): the zeny seed proven live; the buy stops at dialogue stage `unsupported_shop`

The seed slice CLOSED: zeny_wing's first state_tick reads zeny=60 with an
empty inventory, and all seven agents carried their exact seeded balances
all window (8/31/60/4/0/0/0 — the tracked > shop > seed chain live). Two
launch defects were fixed en route: the population runner's own argparse
never accepted --seed-zeny-file (0ef5df79 — 2743782a wired playing.py's
parser only), and the deeper gap the first live window then exposed: the
runner overrides the runtime's seed-aware client factory, so seed_zeny
never reached PlayingClient (b7a4890d — first launch live-proved it:
state_tick zeny null with the seed file loaded and parsed). The committed
receipt covers launch 3 (16:38-18:33); launches 1-2 were void for the
slice (no seed / short duration) and their trace segment reads zeny=null.

The trip machinery is PROVEN to the C6 hop: zeny_wing walked
prontera (177,221) -> the prt05 warp -> prt_in within ~3 minutes of login,
clicked the cited Weapon Dealer cell (172,130 +/-1, npc 110001762), and on
the fresh epoch re-talked 2 seconds after login, authoring
NpcShopBuySelection (opened_sequence 68) 2 seconds after the dialogue
arrived. The purchase never authored: the dealer's deal frame lands as
dialogue stage `unsupported_shop` — the C6 purchase list is never ingested
as a shoppable offer (receipt: shop_offer NONE across 230 samples; DB
zeny 60->60, no knife in inventory). The close-drive then cycled the stage
per its design (4x NpcClose -> "opening" re-received, one close per
received-dialogue session) and the per-epoch drive budget was spent: 109
decides standing at the dealer cell, goal_review farm_item every ~45s,
zero re-talks for the rest of the window.

Rest of the window: 5/7 farmed kills (base_exp +4..+8; s00 — leg 44's dead
agent — farmed pay_fild04 the whole window, the death stall did NOT recur
with the warp-clears-latch fix live in the tree mid-edit), sells 0 (no
other agent reached a dealer), RinceNyan weak (178 MoveTos vs peers'
~1550, static at (188,323) from 16:10 with climbing decides — the leg-44
carry candidate, owned by the main lane). Receipt
population-receipt-45-1793374702.json: 27,511 steps, 0 errors, rx_error
NONE, all 7 online through the window.

NAMED NEXT SLICE: make the shop stage shoppable — ingest the C6 purchase
list so the dealer's deal frame carries offer rows into the shop loop
(killing the `unsupported_shop` classification) and exempt shop stages
from the blocked-close drive. RED test: after NpcShopBuySelection with an
opened_sequence, a NpcShopPurchase must author within N decides when the
wanted id (1201) is on the received offer; DB acceptance stays
zeny 60->10 + nameid 1201 back in inventory.

## 2026-10-30 ~19:3x — leg 45: the seed proven; the buy's last hop named (the C6 offer never binds)

Leg 45 (46e1de70): the zeny seed PROVEN live — zeny_wing's first state_tick
read zeny=60 (all 7 seeded exactly; the shepherd also landed b7a4890d: the
population runners override build_host's client_factory, so the seed needed
forwarding through the factory). The leg-44 death stall did NOT recur (0b256526
validated live). 5/7 farmed kills, no transport down.

THE BUY's last hop named: the chain reached TalkToNpc -> NpcShopBuySelection
(the C4 dealtype answered with the buy arm, 15:38:32) — and the server's C6
buy-list frame NEVER BOUND THE OFFER: the deal frame lands as dialogue stage
'unsupported_shop' and state.shop_offer stays None, so _buy_purchase_actions
(`if offer is None: return None`) can't mint the purchase; the close-drive
cycled the dialogue and the per-epoch drive spent. The bind path exists
(native_shop_context._consume_offer keyed on pid 0xC6 + self._issued + the
send window) — the break is in the ISSUE->BIND handoff: either the authored
NpcShopBuySelection never registered as the context's _issued, or the C6 fell
outside the _sent_at/_deadline window.

NEXT SLICE: drive .work/engagement-diagnosis/shop_trace_probe.py (the w84-era
instrument) over the leg-45 trace window on zeny_wing — dump state.shop_offer
/ the context's _issued/_sent_at/_deadline per tick — to name which half of
the issue->bind handoff dropped. Then the one-line fix, leg 46, the buy lands,
and the economy is closed end to end.

## 2026-10-30 ~19:4x — the C6 offer-bind gap narrowed to two silent drop points

Static trace of the full issue->bind chain (all steps verified present):
NpcShopBuySelection mint (npc_shop_buy_selection, the C4 unsupported_shop
stage live) -> perform_native -> _select_shop_buy (binding stashed at mint) ->
_npc.request(action, now) [encodes C5 type 0 via _encode_shop] -> the send +
_shop_context.issued(action, after, now, deadline) -> the server's C6 ->
_consume_offer binds the offer.

Two silent drop points survive the audit:
(1) request() returns None BEFORE sending: the _name_request_clock denies when
now >= min(deadline, absolute_deadline) — the unsupported_shop stage's window
is 15s from the C4 receipt (the mint->dispatch gap must fit it); or
requests >= 32 denies a long-lived dialogue.
(2) the C6 arrives but decode_shop_offer RAISES (ValueError -> invalidate_offer,
silent): the decoder's row layout vs the pinned server's actual C6 bytes — the
w84-era note says the C6 rows are price/discount/type/nameid; a single
field-order mismatch poisons every attempt.

The leg-45 window's raw frames are not persisted, so neither point is
decidable offline. THE INSTRUMENT for the next leg: a debug tap (one-off, in
the emission/trace lane) logging request()'s return + decode_shop_offer's
exceptions around zeny_wing's buy attempts; leg 46 runs it inside the window
and the drop point falls out of the log. Then the one-line fix, leg 47, the
buy lands, and the economy is closed.

## 2026-10-30 ~20:4x — the shop-debug tap (fails-open warnings on both C6 drop points)

The two silent drops (e02d875b) now name themselves in the runner log:
(1) _select_shop_buy logs a warning when request() returns None (the stage,
the request counter, the deadline, now) — the clock/cap deny falls out;
(2) _consume_offer logs a warning on a C6 outside the issue window and on
decode_shop_offer's ValueError (with the first 64 bytes hex — the row layout
evidence). No behavior change; the gate 6,675+65. Leg 46 runs the tap inside
the window; the drop point falls out of /tmp/population_leg46.log.

## 2026-10-30 ~22:0x — the guard-level tap: every seen C6 names its guard state

Leg 46's mid-window evidence: NpcShopBuySelection minted (20:00:10), the C5
sent (no request-drop warning), the purchase still missing, and ZERO tap lines
— so `_consume_offer`'s EARLY GUARDS (pid/issued/after/consumed) are the
remaining suspects; the two drop-point taps never fired. Added the guard-level
tap: every seen 0xC6 frame logs seq/issued/after/consumed/rows before the
guards. Leg 47 (or 46's close) names the guard definitively. The dispatch chain
re-verified clean (NpcShopBuySelection -> _select_shop_buy -> _npc.request ->
issued()).

## 2026-10-30 ~21:55 — leg 46 readout: BOTH 2470dd93 taps silent with the purchase still missing — the reply frame is the 0xC4 deal marker, not a C6; the drop is the C4 handoff, upstream of both taps

Launch 19:32:24 UTC (20:32 CET; receipt epoch 1793388724); window 21:00-22:30
Madrid CET = 20:00-21:30 UTC — the brief's "19:00-20:30 UTC" was the CEST
mis-conversion; the runner's CLOCK is Madrid and the logins fired exactly at
20:00:00 UTC. The zeny seed proven live again (first state_tick zeny=60; the
seed file matched the fresh pre-launch char-table readback exactly). 7/7
online all window; steps 29911, step_errors 0; ZERO TRANSPORT DOWN.

THE ATTEMPT (the only one; the per-epoch drive spent after it): 20:00:08.184
TalkToNpc(110001762) -> 20:00:10.187 NpcShopBuySelection executed — the C5 WAS
sent (the request-drop tap stayed silent) -> 20:00:10.1866 world_event
NpcDialogueReceived npc=110001762 stage=unsupported_shop, 0.5 ms after the C5;
0xC4 is the ONLY pid the STAGES table maps to that stage
(native_npc_dialogue.py:25). shop_offer non-null in ZERO of 250 receipt
samples. NpcClose 20:00:26 + 20:01:07 (the close-drive cycling the latch);
zeny_wing held one cell (prt_in 172,129) all window; DB zeny 60->60, no knife.

THE LOCALIZATION: ZERO 'shop-debug:' lines in the whole leg log. Both C6 taps
sit BEHIND the bind gate `pid != 0xC6 ... return` (native_shop_context.py:107)
— the 0xC4 the server actually sends dies there BEFORE any tap can emit. No
0xC6 was ever consumed post-issued: an in-window registered 0xC6 would have
bound the offer or tripped the window/decode tap, and an unregistered frame id
would have killed the transport LOUDLY (zero TRANSPORT DOWN). The C4 half of
the handoff was never wired: decode_deal_type (native_shop.py:57) has ZERO
callers. VERDICT: the acceptance's letter (a tap line naming the drop, or the
purchase landing) was NOT met — and that silence IS the answer: the killer is
the third, upstream drop, the C5->C4->C6 handoff; the 2470dd93 tap is
structurally unreachable for the frame the server actually sends.

Reconciliation with 1afddfce (the guard-level C6 tap, landed 21:51 CET
mid-window): it keys `if pid == 0xC6` — on this evidence it logs ZERO lines on
a rerun. The instrument that names the drop definitively is a pid census of
EVERY frame arriving while a selection is issued (one bounded line), or skip
the instrument and wire decode_deal_type into the handoff — that is the fix.

The rest of the window: kills by exp delta, mob_db-exact — RinceNyan +6/+2 =
one Lunatic; PoringMuffin14 +6/+2 = one Lunatic; xXLunasongXx +4/+3 = one
Drops; NyxSong/PipinWalker/YuffieFy81/zeny_wing zero. No sells (zeny flat
8/31/60/4/0/0/0). Social actions fired (FoundGuild/GuildInvite on NyxSong and
PipinWalker). move_gates: await_pending 6680, escalated_target_dead 1393,
no_route_direct 90, target_unwalkable_escalated 3, no_position_or_dead 123;
attack_gates: resting 698, pending_walk 383, dead 156; npc_stage 'blocked'
x193 samples. NEXT SLICE: wire the 0xC4 deal marker through decode_deal_type
into the shop handoff so the offer bind can proceed; leg 47 lands the buy or
prints the 0xC4 bytes.

## 2026-10-30 ~23:5x — the C6-bind fix: the prompt_sequence term drops from the shop context's binding guard

Leg 46's silence + the guard tap's own RED output (C6 seen, issued=False,
after=41) localized the killer: the shop context's check() compared
dialog.sequence to action.prompt_sequence, and the dealer's repeat C4
dealtype marker (leg 46: 0.5ms before the C5, native_npc_dialogue._receive
re-bumps sequence on every 6-byte frame) invalidated the issued binding
before the C6 arrived -> _issued None -> the C6 dropped on the early guard.
The fix: drop the prompt_sequence term (a REAL new prompt still invalidates
via the stage term - menu/text/unsupported_* - and via opened/map/epoch).
Law B kept: the dialogue's own _encode_request still matches
prompt_sequence, so the STALE action cannot re-dispatch a second C5 (the
drift test passes untouched). New test pins Law A end to end: repeat C4 ->
check -> the C6 binds (offer non-None). The tap lines were the instrument:
the RED run's own "C6 seen (seq=43 issued=False after=41)" is the mechanism
reproduced. Gate 6,676+65. NEXT: leg 47 - the buy re-proof; expect the offer
to bind, the purchase admission to mint, the C8 to fire, zeny 60 -> 10 and
the knife (1201) back on zeny_wing.

## 2026-10-31 ~01:1x — the buy-mint starvation: the seeded wallet + the operator knife qualification

Leg 47's mid-window proof: the C6 BOUND (issued=True, the guard tap printed
"C6 seen (seq=70 issued=True after=69 rows=213)" — the b78f105b fix works
LIVE) but the purchase still never minted. Two starvation points, one class:
(1) _buy_mint_attempt read the shop context's wire-observed balance; the wire
delivers SP_ZENY on changes only, so a fresh login wallet is None there. The
mint now reads _zeny_balance's authority chain (tracked > receipt > seed).
(2) The purchase machine refuses to mint on unbound facts; nothing in the
live flow ever bound them. The first live qualification binds the operator's
knife template (item identity 1201/weight 400/ordinary/non-stackable from the
pinned item_db_equip.yml:2262-2265) to the CURRENT exchange; the price fields
qualify from the RECEIVED row (the dealer's actual price is the exchange's,
not the db's Buy column — _eligible re-checks them equal anyway), and the
admission's receipt falls back to the seeded balance (marked runner-seed).
The RED test drives the offered() harness minus the B1 zeny: the offer binds,
the seed reports 80, the mechanical layer mints NpcShopPurchase. Gate
6,677+65. STILL OPEN (production observation for the next leg): the slot
allowance and the max-weight receipt bind only from the operator proof /
B0-24+25 frames — whether the live login delivers the weight pair is
observable in the next receipt.

## 2026-10-31 02:2x — leg 47 receipt: the C6-bind fix is PROVEN live; the purchase admission starved exactly as 3c6cb3bf diagnosed (that fix landed mid-window, NOT under test); the sell arm closed end to end (+4z)

Window 00:45-01:45 CET (23:45-00:45 UTC), runner launched 00:23:40 CET on
02d10b35 (b78f105b binary), duration 6900s, DONE steps 27493 step_errors 0,
zero TRANSPORT DOWN, 7/7 online (decides 84-136/agent). Receipt:
run/plain_host_receipts/population-receipt-47-1793402622.json.

THE FIX UNDER TEST HELD AT ITS HOP. The guard tap printed once, verbatim:
`shop-debug: C6 seen (seq=70 issued=True after=69 consumed=False rows=213)`
— leg 46's RED tap (issued=False) did not reproduce; the dealer's repeat C4
no longer kills the issued binding. The binding is receipt-proven too:
sample i=43 (t=1291.3, 23:45:13.3 UTC) reads npc_stage='waiting' with
shop_offer='rows=19' — leg 46 never had a non-null shop_offer in any sample.
(NB: the tap's rows=213 is the frame's declared row count; the bound offer
carries rows=19 — a row-count mismatch worth one look when the list decode
is next touched.)

THE BUY STILL DID NOT LAND — and the failure signature is precisely the
starvation 3c6cb3bf fixed 88 minutes after this leg's launch (so the leg ran
without it): the offer sat bound ~13s (23:45:13 -> the expiry close
23:45:26), the purchase admission never minted (zero purchase actions in the
trace), the dialogue expired deny('timeout') -> 'blocked' (the structural
shop-chain end), the blocked-stage close fired 3x, and shop_offer reads None
from sample i=44 to the end. DB: zeny_wing zeny 60 -> 60, no 1201 in
inventory, zero exp — parked at the dealer cell (172,129) all window (1
distinct sampled position, 84 decides). ACCEPTANCE NOT MET on the buy; the
verbatim tap above plus the bound-sample is the OR-branch evidence, and the
drop is now NAMED one hop downstream: offer-bound -> purchase-admission
(wallet read + knife qualification), fixed by 3c6cb3bf for the next leg.

THE SELL ARM CLOSED END TO END in the same window: PoringMuffin14
TalkToNpc 00:10:58 -> NpcShopSellOpen 00:11:03 -> NpcShopSell 00:11:05
(sales=[[3,1]], 2s after the C5 — the admission CAN mint inside the waiting
window) -> DB zeny 0 -> 4, ended prt_in (173,130), one cell from the dealer.
Closes the sell hop with a real zeny move; the buy arm is the last open hop.

Other legs' business: kills by exp delta (NyxSong +5/+10, RinceNyan +2/+2,
PipinWalker +5/+3 with 406 Attacks + 4 Loots, xXLunasongXx +3/+3 with 11
Loots, PoringMuffin14 +6/+4; YuffieFy81 and zeny_wing zero). Socials
participated: FoundGuild x2 (NyxSong, PipinWalker), GuildInvite x6 each,
InviteToParty x2 each, party chat traffic. Observation for the next readout:
neither arm re-armed after its blocked expiry (one trip each all window) —
the drive re-arm condition is still an open question if a leg ever needs a
second trip inside one window. Fixture intact for the re-proof: zeny_wing
still holds 60z and no knife. NEXT: leg 48 — relaunch on 3c6cb3bf; expect
the admission to mint on the seeded wallet + the qualified knife: the C8
fires, zeny 60 -> 10, the 1201 back in inventory — THE ECONOMY CLOSES.

## Leg 48 (Sat 2026-10-31 03:30-04:30 Madrid = 02:30-03:30 UTC, launched 03:10:19, 6400s, receipt population-receipt-48-1793412635.json) - THE ECONOMY CLOSE attempt on 3c6cb3bf: NOT MET - the C6 bind regressed to 'blocked', the fix's trigger is unreachable one hop upstream

Pre-launch (cf3ac207): the pump's brief arrived DOC-SHAPED again and was rewritten to the bare mapping ({persona: [[5, 3.5, 4.5]]}, bbf3403e/02d10b35 precedent); seed-zeny refreshed from the fresh char-table readback and CAUGHT A DRIFT the stale file carried: PoringMuffin14 0 -> 4 (leg 47's sell arm) - the fixture chars verified intact (zeny_wing 60z, NO 1201 in inventory, worn equip=2 knives on the other six).

Window health: 7/7 online, steps 25503, step_errors 0, rx_error 0, dispatch_errors 0, zero TRANSPORT DOWN. Seed delivery PROVEN: state_tick zeny=60 for zeny_wing from the first login tick (3c6cb3bf's seed chain reaches the state).

THE BUY DID NOT LAND, one hop EARLIER than leg 47: the trip fired at window open (TalkToNpc 02:30:08 UTC -> NpcShopBuySelection 02:30:10 -> NpcClose 02:30:26 -> NpcClose 02:31:09) and the ONLY verbatim tap line is:

  shop-debug: C6 seen (seq=70 issued=True after=69 consumed=False rows=213)

NO further tap lines ('buy selection request returned None' / 'C6 outside the issue window' / 'C6 decode failed' never printed) - per the silence rule that IS the finding: the drop sits in a guard the taps do not reach. The receipt names it: shop_offer bound in ZERO samples this leg (leg 47's context held the bound offer rows=19 stage 'waiting' from its in-deal sample t=1291.3 to the end); leg 48's in-deal sample t=1201.3 (selection+10s, offer alive to +13s) already reads unbound, and zeny_wing's npc_stage is 'blocked' x174 samples from the FIRST sample - the deal never entered 'waiting'. With no bound offer, _buy_mint_attempt returns at `offer is None` - 3c6cb3bf's seeded-wallet mint + knife qualification are UNREACHABLE (its trigger never fired; the fix did not participate, and the code delta cannot have caused this - it touches nothing on the C6 arrival path). DB: zeny_wing 60 -> 60, no 1201, zero exp, parked at (172,129) all window (1 distinct sampled position, 84 decides, 6 actions).

The dealer stocks the knife (rathena/npc/merchants/shops.txt:255 Weapon Dealer#prt prt_in,172,130 - 19 items, 1201 fourth; the 213 in the tap is the frame's bogus self-declared row count, already bogus in leg 47 where 19 valid rows still bound). Leg 47 -> leg 48 delta with byte-identical tap lines and identical client code on this path: the deal state went 'waiting' (leg 47) vs 'blocked' (leg 48). NEXT slice (RED first): extend the shop-debug taps THROUGH _consume_offer's guards AND the deal-state classifier (log the classified stage + each bind-refusal clause with the frame's seq/length), and check the C5's shop-type byte leg 48 sent vs leg 47 (PipinWalker's sell deal this leg classified 'unsupported_shop' x2 before 'blocked' - the classifier's input, not the wire, is the new suspect). The seeded-currency epoch parity (currency.epoch == offer.epoch inside _resources_fit) stays a named second suspect for AFTER the bind is re-proven.

THE LATCH IS DEAL-AGNOSTIC AND ATE BOTH DEALERS: PipinWalker CLOSED A SELL (TalkToNpc 03:02:17 -> NpcShopSellOpen 03:02:22 -> NpcShopSell 03:02:24 sales=[[3,1]] -> DB zeny 4 -> 7, one Jellopy-priced item) and THEN latched: his last window action is the 03:03:33 NpcClose, 'blocked' x108, 27 min silent at the dealer cell. zeny_wing latched 119 min after her failed deal. The blocked-stage close-drive's one-close-per-session cannot release a RE-latched deal and the drive never re-arms - a post-deal latch release is now a named slice of its own (second sell proof stands: the sell arm works end to end from a mid-window trip, zeny DB-proven).

Kills by exp delta: NyxSong +2/+1, PipinWalker +2/+4, xXLunasongXx +4/+2, PoringMuffin14 +1/+1 (330-360 actions each); RinceNyan patrolled 1637 MoveTos with ZERO kills (exp 60 -> 60 - the only mover who never engaged); YuffieFy81 near-idle (9 actions, exp 0 - watch her next leg; 7 actions last leg too). Socials: GuildInvite x6 (NyxSong, PipinWalker), party chat traffic. Fixture intact for the re-proof: zeny_wing still 60z, no knife. NEXT: leg 49 - the bind re-proof on the extended taps (find WHY the deal classified 'blocked' instead of 'waiting'), THEN relaunch the economy close on 3c6cb3bf once the offer binds again.

## 2026-10-31 ~05:5x — the offer lifecycle tap: every invalidation names its reason, the bind announces itself

Leg 48 (ba3d8247) narrowed the drop to the offer lifecycle: the C6 arrived,
issued=True, but shop_offer never surfaced (0 samples) with npc_stage 'blocked'
x174 from the first sample. The lifecycle tap now names every step:
- "shop-debug: C6 BOUND (seq/rows/npc)" when an offer actually lands;
- "shop-debug: offer invalidated (<reason>) had_issued/had_offer" at every
  invalidate_offer call site, each with a literal reason (identity-changed,
  re-issued, not-ready/dialog-none/past-deadline, guard-failed with the exact
  failing term and values, c6-outside-window, c6-decode-failed,
  purchase-ca-result, selection-sent).
Leg 49 reads which line fires between the bind and the offer surfacing — the
two candidates (the dialogue-deadline invalidation vs the consume-order) fall
out of the log directly. No behavior change; gate 6,677+65.

## 2026-10-31 ~07:05 — leg 49: the lifecycle tap FIRED — hypothesis (a) confirmed; the bound-offer fix TDD'd and landed (bf93474a)

Pre-launch caught a window-killer: the pump's brief carried day index 6
(Sunday) but 2026-10-31 is a SATURDAY (weekday()=5; the runner's own
`CLOCK: (5, 6.05)` proved it) — a day-6 window never opens today and the agents
idle offline forever. The t=60s SCHED line showed all-False; the fresh runner
was killed, the file rewritten to `{persona: [[5, 6.5, 7.5]]}` and relaunched
06:05:26 Madrid (a995317a; seed-zeny refreshed from the fresh char-table
readback — fixture verified intact: zeny_wing 60z, NO 1201, worn knives on the
other six; PipinWalker 4->7).

THE VERDICT — the tap named the offer's fate in the logins' first seconds
(zeny_wing logs in at prt_in 172,129, the dealer is 172,130):

    shop-debug: C6 seen (seq=71 issued=True after=70 consumed=False rows=213)
    shop-debug: C6 BOUND (seq=71 rows=19 npc=110001762)
    shop-debug: offer invalidated (not-ready=True dialog-none=False past-deadline=True) had_issued=True had_offer=True

Hypothesis (a): the offer BOUND and the NEXT snapshot's `check()` killed it on
the dialogue-liveness terms — the ~5s dialogue deadline vs the decide-paced
tick gap. One lifecycle sequence all window; zeny_wing latched 'blocked' x168
(pos=1 all window, 79 decides, 8 actions), shop_offer in 0 samples — the
leg-48 shape, now with the kill point NAMED.

THE FIX (bf93474a, TDD'd this session, gate green 6678 passed / 95.34%): a
bound offer is RECEIVED DATA. `NativeShopContext.check`'s new bound branch
dies only on: the received exchange GONE (dialog None), lost
identity/self-readiness (`context_ok`), a NEW exchange round (the repeat-C4
sequence/opened_sequence/epoch/map/npc terms), or AGE at its own 300s working
TTL (`_SHOP_OFFER_TTL` — native_purchase's own guards at :168/:257 read the
same deadline, so the TTL is what makes the decide-paced mint reachable at
all); never on the clock/`_npc.failed`/cancel-uncertainty terms. MEASURED, not
inferred (per-term diagnostics over every pinned boundary): the post-C6
resting stage IS 'blocked' (the dialogue retry budget expires failed while the
deal lives) — the conjunction cannot discriminate latch from walk-away, so the
runtime passes the narrow `context_ok`; the motion/sit/map/vanish/round-move
pins still die. The purchase [timeout] pin reconciled to 'acquired': the ca is
the server's receipt — refusing to account a completed purchase invites the
retry double-spend, and the anti-retry asserts still hold via
purchase-ca-result invalidation. The synthetic RED test reproduced the live
tap VERBATIM before the fix.

Leg 50 is the proof leg (a fix committed mid-window is not in the running
leg): expect C6 BOUND to SURVIVE, the mint to fire from the seeded 60z, and
the economy close = DB zeny drop + 1201 in inventory.

Window health: 7/7 online, steps 26299, step_errors 0, 0 TRANSPORT DOWN.
DB: kills = NyxSong +4/+5, xXLunasongXx +10/+5; zero zeny moves anywhere; no
purchase (pre-fix leg); fixture intact for leg 50 (60z, no knife).

FINDING (recurrence): YuffieFy81 hit the death-mid-window signature AGAIN
despite 0b256526's landed latch-clear — `move:no_position_or_dead` x510
samples, decides climbing to 216, the respawn fingerprint last==save exact
(pay_fild04 206,175), exp 6/3 -> 6/3 (zero kills). The fix's trigger
reachability is the audit: did a 0x0091 actually arrive at THIS respawn? No
receipt counter names the latch-clear, so participation is unreadable — name
the counter when auditing. Secondary: RinceNyan zero kills a SECOND leg
running (exp flat, full-window patrol) and 5/7 agents farmed nothing — grind
engagement is thin; watch, do not fix in the economy lane.


## Leg 50 — the buy proof ran; the bound offer died to the recovery's OWN re-begin

Launch 08:37:50 Madrid from 106ebeb6+01326562 (the pump shipped the schedule
brief DOC-SHAPED again; rewritten in place to the bare
`{persona: [[5, 9.0, 10.0]]}` mapping and committed before launch, bbf3403e
precedent — the doc stays in git history). Seed-zeny refreshed from a fresh
char-table readback (byte-identical to the committed file: 8/31/60/7/0/4/0);
fixture re-verified pre-launch: zeny_wing zeny=60, inventory EMPTY, all six
others wearing 1201 equip=2. Window 09:00-10:00 Madrid = 08:00-09:00 UTC —
the brief's own "07:00-08:00 UTC" line carried the CEST assumption; the
runner's CLOCK line was the authority. Logins staggered clean, seed verified
delivered (every persona's first state_tick zeny == the seed file).

Receipt: steps 25110, step_errors 0, 210 samples, 7/7 online, decides
77-116/agent, 0 TRANSPORT DOWN. The BUY chain got exactly one at-bat:
TalkToNpc 08:00:08 -> NpcShopBuySelection 08:00:10 -> C6 seen (seq=71
issued=True after=70 consumed=False rows=213) -> C6 BOUND (seq=71 rows=19
npc=110001762). THE LEG-49 KILLER DID NOT FIRE — no
not-ready/past-deadline invalidation; bf93474a worked at its own layer.
Then, VERBATIM taps (/tmp/population_leg50.log):

    shop-debug: C6 seen (seq=71 issued=True after=70 consumed=False rows=213)
    shop-debug: C6 BOUND (seq=71 rows=19 npc=110001762)
    shop-debug: offer invalidated (bound-deal-lost moved-on=True) had_issued=True had_offer=True

shop_offer surfaced in 0/210 samples; the admission never ran; no C8, no
0xCA. DB ground truth: zeny_wing zeny 60 -> 60, inventory still 0 rows —
THE ECONOMY DID NOT CLOSE. Remaining drop, named by the trace timeline:
the NPC-dialogue recovery acted INSIDE the bound window — NpcClose x3
(08:00:26/08:00:44/08:01:12 UTC) plus three runtime re-begins
(NpcDialogueReceived stage='opening' 08:00:28/46/56, same npc, no
TalkToNpc action rows = runtime clicks). No dealer frame arrived after the
bind (world events: nothing between 08:00:10 'unsupported_shop' and
08:00:28 'opening'), and the C6 itself cannot move the machine's sequence
(a 213-byte frame either never matches or _deny()s — and _deny sets
stage='blocked' WITHOUT touching sequence; that deny IS the measured
post-C6 resting 'blocked'). So the moved-on trigger was the recovery's own
re-begin: begin() mints a fresh view (sequence AND opened_sequence reset),
and the next build's `_check_bound_offer` read it as a NEW exchange round.
The heartbeat decide (30-75 s) came at 08:00:52 — after the invalidation;
the mint never had shop_offer to read.

NEXT SLICE (economy lane): hold the dialogue recovery OFF while a bound
offer exists — gate the re-begin budget AND the blocked-stage close drive
on the shop context's bound offer (a bound offer IS live-deal evidence;
recovery must not re-click or close into it). RED test: bind an offer,
exhaust the dialogue budget, assert no re-begin and no NpcClose while
bound, and that the next decide mints from the intact offer. Secondary
watch: zeny_wing never re-armed after the trip (farm_item + empty-plan
GrindScript at the dealer cell, 0 MoveTos, 33 decides all next_action=None
— only chat) — a recovery hold-off makes the single at-bat survivable; the
re-arm cadence is the gap after that.

Window health: kills = RinceNyan +4/+2 (SWITCHED attack target — the
leg's kill), NyxSong +2/+1, xXLunasongXx +2/+1, 21 attacks total; zero
zeny moves anywhere (no sells; the sell arms correctly idle — nobody
holds sellables beyond the worn knives). YuffieFy81 did NOT recur the
death-stall this leg (2 attacks, 11 MoveTos, 1 Rest, 89 decides, no
death-latch fingerprint). Socials flowed (PartyChat 26, Say 35,
InviteToParty 4, GuildInvite 12 — cumulative tables, attribute by diff not
by count).

## 2026-10-31 ~11:3x — the recovery holds while a bound offer exists (the leg-50 verdict, TDD)

Leg 50's receipt (c17fbf00) named the last hop: the C6 BOUND survived the
leg-49 clock killer (bf93474a at its own layer) but the offer died to the
dialogue RECOVERY's own re-begin inside the bound window — the retry budget
re-arms the dialogue, the fresh begin replaces the view, and the shop context
reads a NEW exchange round (bound-deal-lost moved-on=True) before a decide
ever saw the offer. The guard: _retry_blocked_dialogue returns True (the
barrier owns the dispatch) WITHOUT the re-begin while _shop_context.offer is
not None — the deal is alive server-side even though the dialogue clock
expired; the re-begin waits until the offer dies on its own terms (the
exchange gone / identity loss / a real new click / the 300s TTL). The RED
test reproduces leg 50 verbatim (the fresh 'opening' view at
opened_sequence 12 vs the blocked 10 while the offer was bound); the retry
stubs gain a no-offer shop context so the cadence still runs unbound. Gate
6,679+65. Leg 51: the full chain to the C8 — the offer binds and SURVIVES,
the admission mints, the purchase fires, the economy closes.

## 2026-10-31 ~12:4x — the repeat-C4 tolerance + the newer-C6 re-bind (the leg-51 tap verdict)

Leg 51's tap (mid-window): C6 BOUND then "bound-deal-lost moved-on=True"
AGAIN — bf93474a's moved-on terms reintroduced the leg-46 misread: the raw
`dialog.sequence != offer.prompt_sequence` counts the vendor's repeat C4
re-marker as a NEW exchange round. Two changes, both dictated by the live
evidence:
(1) moved_on drops the raw sequence term; the deal lives in waiting / the C4
marker stage / blocked (the resting stage) and dies on a fresh click
(opened_sequence), identity loss, or a stage that leaves the deal set
(menu/text) — the drift law holds at the offer level.
(2) a NEWER in-window C6 RE-BINDS (the latest list wins — the server's own
refresh of the same deal); only a stale duplicate (seq <= the bound
receipt_sequence) is dropped. The detached-once law holds: the old offer
object is never mutated. The [new_c4]/detached contracts reconciled to the
same-prompt + latest-list laws. Gate 6,680+65. Leg 52 = the buy attempt on
the complete chain (bind survives clock + recovery + re-marker).

## Leg 51 — the economy-close attempt on the recovery-hold guard (c0f99258): NOT CLOSED, the remaining drop is the close drive

Window Saturday 2026-10-31 11:30-12:30 Madrid (10:30-11:30 UTC), day index 5;
launched 11:17:40 (receipt epoch 1793441833, duration 6600s) from 4c07c561 —
so the leg ran WITHOUT 75054047 (the re-marker fix landed after the launch
and is leg 52's code). 7/7 online the whole window, decides 72-172/agent,
26,309 steps, 0 errors, 0 TRANSPORT DOWN.

Pre-launch fixture work (4c07c561): the brief arrived doc-shaped AGAIN —
rewrote to the bare runner mapping (bbf3403e precedent); seed-zeny refreshed
from the char-table readback and zeny_wing's grant bumped 60->150z: the
received C6 knife row price is 73z (leg-49 decode; db Buy says 50) and
affordability compares the FULL received price, so 60z could never cover the
buy. Seed delivery VERIFIED: the first state_tick read zeny=150 at
10:30:08 UTC. zeny_wing logged back in at prt_in (172,129), one cell from
Weapon Dealer#prt (172,130).

VERDICT: THE ECONOMY DID NOT CLOSE. zeny_wing DB zeny 150->150, no 1201 in
inventory. The chain advanced one hop and named the remaining drop verbatim:

    shop-debug: C6 seen (seq=71 issued=True after=70 consumed=False rows=213)
    shop-debug: C6 BOUND (seq=71 rows=19 npc=110001762)
    shop-debug: offer invalidated (bound-deal-lost moved-on=True) had_issued=True had_offer=True

The trace (pop_0003_g00m02.jsonl, UTC): TalkToNpc 10:30:08.179 -> C4
10:30:10.181 -> NpcShopBuySelection (the C5) 10:30:10.182 -> C6 BOUND ->
**NpcClose 10:30:26.204 — 16s into the bound window** -> the offer
invalidated -> the FIRST re-begin 10:30:28.211 (AFTER the offer died) ->
two more close/re-begin cycles (10:31:05/07, 10:31:23/25). The bound offer
surfaced in the decide state for exactly 1 of 220 receipt samples (t=780.8,
rows=19, stage waiting) — the C6 handoff WORKED end to end. Every decide
after 10:30:26 read offer=None, so the decide-paced mint never saw a bound
offer; the admission/affordability hop (and the 150z grant) was never
reached. One buy at-bat per window, as leg 50 predicted; it never re-armed.

THE REMAINING DROP: c0f99258 gated only the RE-BEGIN arm of the dialogue
recovery (_retry_blocked_dialogue, playing_runtime.py:849). The
BLOCKED-STAGE CLOSE DRIVE is ungated and minted that NpcClose while the
offer was bound — the server deal terminated and the context read
deal-lost. The re-begin hold itself held at its own layer: no re-begin
until after the invalidation (leg 50's +2s re-begins are gone). No dealer
frame arrived between the bind and the close (the world-event stream is
empty there), so the close is the killer — not a repeat C4.

NEXT SLICE: extend the hold to the close drive — gate
_dialogue_clear_drive's blocked-stage NpcClose on
`self._shop_context.offer is not None` (the mirror of the re-begin hold).
RED test in the test_recovery_holds_bound_offer.py harness: bind an offer,
expire the dialogue into stage 'blocked' past the retry budget, assert NO
NpcClose while bound and that the next heartbeat decide mints the purchase
from the intact offer. NOTE for leg 52 (launched 13:07 from 48f50cf0 with
75054047 in): the close-drive hold is NOT in that tree either — expect the
same 16s kill at the 13:30 open unless it lands first. After the close
drive holds, the chain should finally close: mint -> C8 -> 0xCA -> DB zeny
drop by the received price (73z per leg 49; grant now 150z) + 1201 in
inventory.

Secondary: guild actions fired again (FoundGuild + 6 GuildInvite x2 — the
cumulative-tables rule: check the masters against leg 50 before claiming
new formation); a party formed (2 AcceptInvite; party chat flowed);
attacks 37/20/7/13/28/0/0 across the seven; no kill attribution this leg —
the pre-launch baseline SQL omitted base_exp/job_exp (baseline gap; next
shepherd re-adds the exp columns). Receipt:
run/plain_host_receipts/population-receipt-51-1793441833.json.

## 2026-10-31 ~13:5x — the moved-on term tap: WHICH bound-deal-lost term fired

Leg 52 mid-window: C6 BOUND then bound-deal-lost moved-on=True AGAIN with
75054047 live — so the firing term is NOT the sequence (dropped); it is
opened_sequence (a re-click/re-begin) or the stage leaving the deal set. The
tap now names the term values at every moved-on invalidation. Leg 53 reads it.

## 2026-10-31 15:00 — leg 52: the close-drive kill confirmed live (second window); THE ECONOMY DID NOT CLOSE

Receipt: run/plain_host_receipts/population-receipt-52-1793448485.json.
Launched 13:08 from 48f50cf0 on the SHIFTED window 13:30-14:30 Madrid (the
12:46 launch died at boot: BlockingIOError memory_journal.py:93 — the
still-running leg-51 runner held the memory-journal flocks; they release only
at its 13:07 exit). CLOCK (5, 13.13) matched the file's day 5; logins fired at
the 13:30 open; 7/7 online in every sample to the 14:30 close; 26262 steps,
0 errors, 0 TRANSPORT DOWN.

THE BUY: bound, then killed at the same hop ~16s in —
  shop-debug: C6 seen (seq=71 issued=True after=70 consumed=False rows=213)
  shop-debug: C6 BOUND (seq=71 rows=19 npc=110001762)
  shop-debug: offer invalidated (bound-deal-lost moved-on=True) had_issued=True had_offer=True
Trace: TalkToNpc 12:30:08.7Z -> NpcDialogueReceived (the C4) 12:30:10.7 ->
NpcShopBuySelection 12:30:10.7 -> BOUND -> NpcClose 12:30:26.732 with NO
decide between 12:30:08.7 and 12:30:28.7 (runtime-minted, not decided) -> a
fresh dialogue 12:30:28.7 (new opened_sequence) -> moved-on=True. The mint
never ran: zero mint/prepare/purchase taps, shop_offer in 0/220 samples (the
offer lived <=16s, sub-sample). zeny_wing then ground in place at the dealer
cell (prt_in 172,129) to the close — no re-arm (the leg-50 gap, still open;
80 decides, zero MoveTos, zero attack gates).

Leg-51's diagnosis CONFIRMED live: _dialogue_clear_drive's blocked-stage
NpcClose (brain.py:828) is the ungated second terminator — the post-C6
resting stage IS "blocked", the grind divert budget expires ~16s in, and the
close kills the bound deal. c0f99258 held only _retry_blocked_dialogue.

DB (acceptance arm 1 failed): zeny_wing 150->150, NO 1201 back (the six
others still wear theirs, equip=2). Seed verified live: the first state_tick
read zeny=150 (top-level field). Kills (exp delta): NyxSong +3/+2, RinceNyan
+9/+5, YuffieFy81 +2/+1, others 0; zeny moves: none.

NOTE: two pump commits landed mid/post-window: 077b214b (the moved-on term
tap, 13:51) and e593544d (the blocked-stage close drive holds while a shop
offer is bound — the exact next slice this entry names). Leg 52 ran with
NEITHER (launched 13:08; the moved-on line above carries no term values).
Leg 53 launches with both: the moved-on invalidation should not fire while
bound at all, the offer should survive to the decide-paced mint, and the
re-arm cadence is the named gap after that.

## 2026-10-31 ~15:1x — the blocked-stage close holds while a shop offer is bound (the leg-51 receipt verdict)

The leg-51 receipt (5349321a) named the killer precisely: the blocked-stage
CLOSE DRIVE — ungated by c0f99258 (which held only the re-begin arm) — minted
NpcClose at +16s INSIDE the bound window; the close terminates the deal
server-side and the shop context reads bound-deal-lost moved-on=True before
the decide-paced mint ever saw shop_offer. The guard (the mirror of the
re-begin hold): _dialogue_clear_drive's blocked-stage close returns None when
state.shop_offer is not None — the deal is alive server-side; the close waits
until the offer dies on its own terms. The RED test pins both arms (the hold
with a bound offer, the close without). The chain's guards are now COMPLETE:
the clock (bf93474a), the recovery re-begin (c0f99258), the repeat-C4
re-marker (75054047), and the close drive (this slice). Gate 6,681+65. Leg 53
= the buy attempt with every arm held.

## 2026-10-31 ~17:0x — the fifth guard: the merchant drive holds its click while an offer is bound (the leg-53 tap verdict)

Leg 53's term tap (the first leg to carry 077b214b) named the term exactly:
"moved-on terms (seq=70->72 opened=69->72 stage=opening ...)" — a FRESH
CLICK opened a new exchange round while the offer was bound. Not the
recovery, not the marker: the merchant drive's own TalkToNpc re-mint (the
dialogue's resting stage 'blocked' reads as no-deal to the script). The
guard (the script layer's first): _merchant_engage returns empty ACTIVE when
state.shop_offer is not None — the mechanical purchase path owns the
exchange and the decide-paced mint sees it on the same tick. The chain's
guards are now FIVE: the clock, the recovery re-begin, the repeat-C4
re-marker, the close drive, and the drive's re-click. Gate 6,682+65. Leg 54
= the buy attempt with every layer held.

## 2026-10-31 ~17:10 — receipt: leg 53 - THE ECONOMY DID NOT CLOSE; the killer is the blocked-stage CLOSE, and e593544d's hold never fired (it reads state.shop_offer, null at the moment)

7/7 online all window, 25,112 steps, 0 errors, 0 TRANSPORT DOWN; seed verified
live (first state_tick zeny=150, inventory_counts {} - fixture intact: 150z,
no 1201). The full chain ran in the session's first 90s: TalkToNpc 14:30:08 ->
C4 14:30:10 -> NpcShopBuySelection +2ms -> C6 frame 14:30:28 -> C6 BOUND
(seq=71 rows=19 npc=110001762) -> **NpcClose 14:30:47 (+19s inside the bound
window)** -> NpcDialogueReceived reopen 14:30:49 (begin() bumps opened AND
sequence) -> moved-on -> invalidated; two more close/reopen pairs (14:31:06/08,
then close 14:31:27) and the agent idled at the dealer cell for the remaining
hour (1 distinct position, 0 MoveTos, no re-arm - the leg-50 shape). DB
zeny_wing 150->150, no 1201. Verbatim taps (the first leg carrying 077b214b):

    shop-debug: C6 seen (seq=71 issued=True after=70 consumed=False rows=213)
    shop-debug: C6 BOUND (seq=71 rows=19 npc=110001762)
    shop-debug: moved-on terms (seq=70->72 opened=69->72 stage=opening epoch=True map=True npc=True)
    shop-debug: offer invalidated (bound-deal-lost moved-on=True) had_issued=True had_offer=True

THE REMAINING DROP: e593544d gates the close on `state.shop_offer is not
None` (brain.py:828), but the decide-state projection was null on every
state_tick through the bound window (14:30:08/14:31:10/14:32:10 all
shop_offer=null) - the hold's trigger is unreachable in exactly the state it
was written for, and brain.py holds no `_shop_context` to read the authority
(grep: zero hits). The bound offer lives ONLY in the shop context (the tap's
had_offer=True). The leg-51 prescription was to gate on the CONTEXT's bound
offer; the diff shipped the projection instead.

RETRACTION of the entry above (5c71a9e4's attribution): the leg-53 trace
action census names ONE TalkToNpc for the whole leg (the opening click) -
there is NO fresh click after the bind; the actions in the bound span are
NpcClose x3. "opened 69->72" is begin()'s post-close bump (the reopen 2s
after the close), not a new exchange round from a re-click. The
merchant-drive re-click hold aims at an arm that did not fire, and it too
keys on the unreliable `state.shop_offer` projection. NEXT SLICE: plumb the
shop context (or the bind state) into EventDrivenBrain and gate
_dialogue_clear_drive - and the new _merchant_engage hold - on the CONTEXT's
bound offer; RED test: bind in the context, leave state.shop_offer=None,
assert the close (and the empty-ACTIVE engage hold) fire nothing. With the
close truly held, c0f99258's re-begin arm finally gets its live at-bat.


## 2026-10-31 ~18:35 — receipt: leg 54 - THE ECONOMY DID NOT CLOSE (fourth window); leg 54 names the first domino: the TICK-PATH dialogue retry begins INSIDE the bound window

Launched 16:55 from 626f11db (5c71a9e4 in). Window 17:15-18:15 Madrid, day
index 5 (CLOCK (5, 16.92) at t=60, SCHED windows all (5, 17.25, 18.25)); the
pump's doc-shaped brief rewritten to the bare mapping and committed
(626f11db, bbf3403e precedent); seed refreshed from the 16:52 char readback
(unchanged bytes; fixture intact) and verified live (first state_tick
zeny=150 at 16:15:08 UTC). The whole buy chain ran in the first 40s of the
window - zeny_wing logged in ON the dealer cell (prt_in 172,129, leg 53's
logout point): TalkToNpc 16:15:08 -> C4 (unsupported_shop 16:15:10) ->
NpcShopBuySelection 16:15:10 -> C6 BOUND ~16:15:28. The offer then died to
moved-on ~13s later, BEFORE the close and before any decide-paced mint (the
next decide was 16:15:55): a begin() fired at ~16:15:28 INSIDE the bound
window - world event NpcDialogueReceived stage='opening' at 16:15:28.255,
and 'opening' is begin()'s stage (native_npc_dialogue.py:104) - its server
answer moved the cursor 70->72, and the next check read moved-on. By
elimination that begin is _retry_blocked_dialogue_on_tick
(playing_runtime.py:2078) - the tick-path twin of the leg-50-held
action-path retry (:862, which HAS the c0f99258 hold) - and it carries NO
bound-offer hold at all. The census rules out every other begin source: ONE
TalkToNpc total (16:15:08, before the bind - the fifth guard's re-click arm
never fired, confirming 4b1d4d05's leg-53 retraction on fresh evidence) and
no recovery NpcClose until later. The blocked-stage close still fired
NpcClose at +19s (16:15:47) with two more begins after it (16:15:49/58) -
e593544d's hold silent because it reads state.shop_offer, null on every
tick (shop_offer in 0/180 samples); the context knew the whole time
(had_issued=True had_offer=True). Verbatim taps:

    shop-debug: C6 seen (seq=71 issued=True after=70 consumed=False rows=213)
    shop-debug: C6 BOUND (seq=71 rows=19 npc=110001762)
    shop-debug: moved-on terms (seq=70->72 opened=69->72 stage=opening epoch=True map=True npc=True)
    shop-debug: offer invalidated (bound-deal-lost moved-on=True) had_issued=True had_offer=True

DB: zeny_wing 150->150, no 1201 (the economy did not close); the farmers
landed kills (base_exp NyxSong 99->105, RinceNyan 77->82, PoringMuffin14
52->56, xXLunasongXx 86->90); zeny_wing parked at the dealer cell all
window (83 decides, 0 further npc actions - the one-at-bat shape again).
7/7 online, 21506 steps, 0 step_errors, 0 TRANSPORT DOWN. Receipt
run/plain_host_receipts/population-receipt-54-1793462104.json. NEXT SLICE
(4b1d4d05's slice, EXTENDED by leg 54): plumb the shop context into
EventDrivenBrain and gate _dialogue_clear_drive, _merchant_engage AND
_retry_blocked_dialogue_on_tick on the CONTEXT's bound offer - leg 54 shows
a close-only gate cannot save the offer, because the tick-path retry's
first begin precedes the close by ~19s. RED test: bind in the context,
leave state.shop_offer=None, tick past the dialogue timeout, assert no
begin, no close, and no empty-ACTIVE engage while bound.


## 2026-10-31 ~20:20 — context-gate landed: the tick-path dialogue retry now holds while a bound offer exists; the state-surfacing gap verdict: the pass-through is honest, the offer died young (extends 4b1d4d05, named by b99e047f)

The leg-54 slice (feat/context-gate-offer, worktree wt-context-gate). Site (2)
first, because the receipt's own taps name it: `_retry_blocked_dialogue_on_tick`
(playing_runtime.py) carried NO bound-offer hold and re-began the dialogue
INSIDE the bound window - the c0f99258 hold now mirrored on the tick path
(same placement: after the deny-origin/budget gates, before the cadence wait;
the barrier owns the dispatch until the offer dies on its own terms). RED
test drove the tick path against a C6-bound client: the begin fired, the view
was replaced (opened 10->12, stage 'opening'), and the next build's moved-on
check killed the offer - the exact leg-54 kill chain offline.

Site (1) VERDICT - the three suspects are exonerated, with evidence: the
surfacing at build_native_state (playing_runtime.py:711,
`shop_offer=self._shop_context.offer`) is a LIVE attribute read; offline
probes prove the bound offer surfaces on EVERY build in all three live
post-bind shapes - the 'waiting' stage, the expired/blocked resting stage
(failed=True, deny_origin 'timeout' - the e2e-49 narrowed predicate holding
as built), and the repeat-C4 re-marker (the leg-46 no-raw-sequence law
holding). The brief's RED test (bind in the context, build, assert
state.shop_offer) PASSES on the pre-fix code - the state-surfacing gap was
NOT a stage condition, a wrong source field, or a stale copy: the offer was
ALREADY DEAD at every sampled build. The receipt's 0/180 is a sampling
artifact: `_consume_offer`'s issue-window guard
(`_sent_at <= at < min(_npc.deadline, absolute_deadline)`) forces the C6
bind inside ~[16:15:10.2, 16:15:15.2) - the receipt's "~16:15:28" bind
timestamp was the log-line estimate, not the bind - so the bound window was
~16s (bind ~16:15:12-15 -> moved-on death ~16:15:28.x), and the 30s receipt
samples (16:15:08.5, 16:15:38.5) straddled it. The death at bind+~13s
matches the receipt's "~+13s": the tick-path begin at 16:15:28.255 replaced
the view (opened 69->72, stage 'opening') and the next check read moved-on.
From that instant state.shop_offer was legitimately None - the close at
16:15:47 and the two later begins were all post-mortem. With the tick-path
hold landed the offer lives its 300s TTL, every build surfaces it, and the
state-gated arms (e593544d's close hold, 5c71a9e4's engage hold) finally
see it; a model-ordered NpcClose while bound is additionally swallowed by
the action-path retry gate perform_native already carries. No
context-layer duplication of the close/engage arms (per the slice brief).

Tests: tests/test_context_gate_bound_offer.py - the tick-path hold (RED ->
GREEN) plus its no-offer control (the re-begin still fires unheld), and
three surfacing pins (every-build, blocked-stage, re-marker). Scoped
neighbors green: test_npc_retry, test_recovery_holds_bound_offer,
test_native_shop_context, test_buy_mint_seeded_wallet, test_shop_sell_loop,
test_decide_starvation_blocked_dialogue, test_merchant_drive,
test_native_shop_selection, test_brain. Pre-lint (black/ruff/mypy/xenon)
green before the gate; full `task check` GATE GREEN: 6687 passed,
65 subtests passed, coverage 95.34% (all eight chain phases: black,
vulture, pylint-dup, xenon, bandit, ruff, mypy, pytest).


## 2026-10-31 ~23:05 — receipt: leg 55 - THE ECONOMY DID NOT CLOSE (fifth window); THE FIX UNDER TEST WORKED: the bound offer survived its FULL 300s TTL for the first time in the series - and starved: the mint's own precondition (`_shop_loop_action`'s `_npc.failed` term) is the sixth arm, consumer-side

Launched 21:24 from 10471d3b (a038bcbc in). Window 21:45-22:45 Madrid (day
index 5 == weekday() Saturday; CLOCK (5, 21.4) at t=0; SCHED windows all
(5, 21.75, 22.75)). The pump's doc-shaped brief rewritten to the bare
mapping and committed (10471d3b, bbf3403e precedent). Seed refreshed from
the 21:24 char readback (unchanged bytes; fixture intact: zeny_wing 150z,
no 1201) and verified live (first state_tick zeny=150 at 20:45:08 UTC).

THE CHAIN THE FIX TARGETED, LIVE: zeny_wing logged in ON the dealer cell
(prt_in 172,129): TalkToNpc 20:45:08 -> NpcShopBuySelection 20:45:10 ->
C6 BOUND ~20:45:10 (seq=71, rows=19, npc=110001762). Then NO moved-on, NO
re-begin, NO close inside the bound span - all five hold arms held
(bf93474a clock terms, c0f99258 action-path re-begin, e593544d close drive,
75054047 moved-on raw-sequence, a038bcbc tick-path retry). The closes fired
only at 20:50:11/29/47, AFTER the offer's own death. ONE TalkToNpc total
(the re-click arm never fired, again). The offer died to AGE at exactly its
300s TTL - the first offer in the series to reach its own terms. Verbatim
taps:

    shop-debug: C6 seen (seq=71 issued=True after=70 consumed=False rows=213)
    shop-debug: C6 BOUND (seq=71 rows=19 npc=110001762)
    shop-debug: offer invalidated (offer-ttl-expired) had_issued=True had_offer=True

THE REMAINING DROP, NAMED: the decide-paced mint never ran. Nine heartbeat
decides inside the bound span (20:45:52-20:49:55, all next_action=None,
zeny=150 visible on every tick, dealer adjacent under the agent) minted
NOTHING. The consumer-side gate `_shop_loop_action`
(src/robots/app/playing_runtime.py:1219) - `if state.alive is not True or
self._npc.failed or self._npc.cancel_uncertain: return None` - is the sixth
arm: the C6 is NOT in NPC_RECEIVE_IDS, so it never refreshes the dialogue
deadline; `_expire` fires ~15s after the bind into `_deny('timeout')`
(failed=True, stage 'blocked', the leg-49 measured resting shape); from the
first heartbeat decide onward the mint precondition returns None on every
call, and the intact offer starves to its TTL with all hold arms keeping
everything else away from it. The leg-49 healing (offer check immune to the
clock terms) fixed the OFFER's survival; the MINT's precondition still
reads the same clock terms and was never held. The mint path carries NO
taps - zero tap lines with the failure present is the finding that the
drop sits in a guard upstream of every tap.

DB: zeny_wing 150->150, no 1201 (the economy did not close). Kills landed:
6/7 field chars gained exp (base xXLunasongXx 90->112, NyxSong 105->118,
PoringMuffin14 56->68, PipinWalker 50->60, RinceNyan 82->87, YuffieFy81
8->10; 145 Attacks, 62 dmg_taken, 9854 MoveTos, one Loot). Socials replayed
with zero new rows (FoundGuild x2, GuildInvite x6 x2, InviteToParty x4 -
NyxSongGuard/PipinWalkerGuard and both parties predate this window, leg
53's rows). zeny_wing parked at the dealer cell all window (79 decides, the
one-at-bat shape again - re-arm cadence is the gap AFTER the mint works).
xXLunasongXx logged out on prontera (153,156) - next leg logs in there.
7/7 online all window, 21499 steps, 0 step_errors, 0 TRANSPORT DOWN.
Receipt run/plain_host_receipts/population-receipt-55-1793478281.json
(launch 2026-10-31 20:24:41 UTC).

NEXT SLICE (the consumer-side sixth arm): hold `_shop_loop_action`'s
`self._npc.failed or self._npc.cancel_uncertain` terms off the mint while
`self._shop_context.offer is not None` (gate on the CONTEXT, not the state
mirror - the visibility law). RED test: bind an offer in the context,
expire the dialogue into deny('timeout') (failed=True, stage 'blocked'),
fire a heartbeat decide, assert NpcShopPurchase mints from the intact
offer; plus the no-offer control (a failed dialogue with no offer must
still gate). Add mint-path taps while there (announce affordable-weapon
verdict, admission, qualification, purchase-action build) so any FURTHER
drop (affordability row match, knife qualification, admission) names itself
next leg instead of re-derivation.


## 2026-11-01 ~00:15 - the sixth arm landed: the mint precondition holds on the CONTEXT's bound offer (timeout denials only) + the mint-path skip tap

feat/mint-precondition-hold: `_shop_loop_action`'s `self._npc.failed` term no
longer gates the decide-paced mint while `self._shop_context.offer is not None`
AND the denial is the innocent clock expiry (`deny_origin == "timeout"`, the
legs 23-24 retryable origin). The poison denials (malformed / send-failure)
still block with an offer bound, and a failed dialogue with no bound offer
keeps the barrier complete - the hold lives on the CONTEXT's offer (the same
gate the leg-49 healing gave the offer's own survival), not on the state
mirror. `cancel_uncertain` is unchanged: it still blocks always.

Guard shape: `_mint_skip_term` names the failing precondition term
("alive" / "cancel_uncertain" / "npc_failed"); `_timeout_denial_with_live_offer`
is the one held-off shape; `_note_mint_skip` is the mint-path TAP
(tap-before-fix doctrine): one
`shop-debug: mint skipped by <term> (alive=... npc_failed=... deny_origin=...
cancel_uncertain=... offer_bound=...)` WARNING whenever the precondition skips
the shop loop while an offer is bound - the next leg can name any remaining
gate from the log instead of re-deriving. Bounded to the mint window (a bound
offer: without one no mint was pending), fails open, never behavior.

TDD RED->GREEN (tests/test_mint_precondition_bound_offer.py, the seeded-wallet
ready_shop harness + the REAL dialogue machine deny: the timeout class driven
by pulling the post-C5 deadline under the harness clock, the poison class by
the machine's backwards-clock guard):
1. timeout denial + bound offer -> NpcShopPurchase mints (RED first:
   `assert 0 == 1` with failed=True, deny_origin='timeout', shop_offer set -
   the exact leg-55 starvation, the offer alive and the mint starved),
2. poison denial + bound offer -> still blocked, and the tap names it
   ("mint skipped by npc_failed ... deny_origin=poison offer_bound=True"),
3. no bound offer + failed -> still blocked, tap silent (no mint pending).

Full gate green on the branch: 6690 passed + 65 subtests, coverage 95.36%
(`nix develop -c task check`, exit 0). NEXT SLICE (leg 56, the coordinator
dispatches): the live window - zeny_wing re-armed at the dealer with the hold
active; the mint-path tap line names the next gate if the economy still does
not close (candidates: the re-arm cadence, the admission/facts window after
the 300s TTL death).

## 2026-11-01 ~02:45 — receipt: leg 56 - THE ECONOMY DID NOT CLOSE (sixth window): the sixth arm WORKED (the precondition held, zero mint-skip taps) and the mint still never fired - the remaining gate is the 5-second capacity freshness on the login-stamped weight pair (`_capacity_fits`'s `_fresh(weight.observed_at, now)`)

Launch 01:05 CET (runner t=0 ~01:09 after nix activation), window
01:15-02:15 (day 6 ✓, `CLOCK: (6, 1.133)`, `SCHED: ... configured: True`),
duration 5700s, `DONE: steps 22712, errors 0`, receipt
`population-receipt-56-1793491738.json`. Seed verified delivered: the first
state_tick read `zeny=150` (the fresh char-table readback matched the
committed seed byte-for-byte; fixture intact: 150z, no 1201, knife worn on
the other six). Transport: zero `TRANSPORT DOWN`; 7/7 online from the open.

The one at-bat (all times UTC, traces + runner log agreed once t=0 was
anchored on the receipt epoch): 00:15:08 login -> the drive clicked the
dealer (`TalkToNpc`, npc=110001762 = `Weapon Dealer#prt`, prt_in 172,130 —
the agent logged in at its `last_map` cell 172,129, adjacent) -> 00:15:10
C4 `unsupported_shop` -> `NpcShopBuySelection` -> `shop-debug: C6 seen
(seq=70 issued=True after=69 consumed=False rows=213)` -> `shop-debug: C6
BOUND (seq=70 rows=19 npc=110001762)` — 19 rows = the dealer's exact
shop list (`npc/merchants/shops.txt:255`, includes the 1201 Knife at the
received 73z <= 150z budget, so `shop_affordable_weapon` and
`_qualify_knife_facts` (exactly one 1201 row) both pass). Then SEVEN
heartbeat decides inside the bound span (00:15:50, 00:15:51, 00:16:10,
00:17:23, 00:18:22, 00:19:13, 00:20:04), every `next_action=null`, and
ZERO `mint skipped by ...` lines — the sixth arm engaged exactly as built:
with `npc.failed=True` (the innocent post-C6 `_deny('timeout')`),
`deny_origin='timeout'`, and the CONTEXT's offer bound,
`_mint_skip_term` returned None on every consult and the tap (which fires
only on a SKIP) stayed silent. The offer died at its own terms:
`shop-debug: offer invalidated (offer-ttl-expired) had_issued=True
had_offer=True` at 00:20:10 (the full 300s TTL, no killer touched it —
the four holds plus the mint hold all did their jobs), the blocked-stage
close drive correctly released only after the death (three `NpcClose`
00:20:10-00:20:46), and the agent never re-armed (worldfeed: goal
`farm_item`, script `GrindScript`, `plan: ""` — the one-at-bat shape).

THE REMAINING GATE, named from code + the live timeline because the drop
sits DOWNSTREAM of the only mint tap (tap-before-fix debt: the sixth-arm
commit tapped the precondition only): `npc_shop_purchase` ->
`NativePurchase.mint` -> `_eligible` -> `_resources_fit` ->
`_capacity_fits` requires `_fresh(weight.observed_at, now) and
_fresh(maximum.observed_at, now)` = `0 <= now - at < 5.0`
(native_purchase.py), and `NativeCapacityContext._consume` stamps the
weight/max-weight `ReceivedCapacityValue` with the FRAME ARRIVAL time `at`
(native_capacity.py `_consume`, the 0x00B0 param-24/25 branch). The weight
pair arrives ONCE at login (00:15:08); the first post-bind decide is
00:15:50 (42s stale) and an agent standing idle at a dealer never receives
another weight frame — the 5s window is unsatisfiable BY CONSTRUCTION on
every decide, the leg-39 "trigger waits on evidence the broken state
prevents from existing" law, now in the economy mint. This is the leg-47
zeny-staleness defect class: the wallet-parity seed (2743782a) fixed it
for CURRENCY (the seed path in `_purchase_snapshot` stamps
`observed_at=now`, fresh), but nobody applied the parity fix to CAPACITY.
Acceptance: DB zeny_wing 150 -> 150, inventory still has no 1201 — RED;
no verbatim mint-skip line exists to quote (the log is silent exactly
where the drop sits).

Rest of the window (window-filtered action census): 70 attacks / 5812
MoveTos; kills by exp delta (RinceNyan 87->102 base +68->75 job,
PipinWalker 60->69/+7, xXLunasongXx 112->116); zero zeny moves anywhere
(no sell trips — nobody's loot triggered one); socials ran (2 FoundGuild,
12 GuildInvite, 4 InviteToParty, 15 PartyChat); attack_gates all
`pending_walk` (sums 2/10/8/1/1/2 + s00 resting:3), s00
`no_position_or_dead: 5` samples (one transient latch, kept acting — 184
actions), nothing else stalled.

NEXT SLICE (leg 57, the coordinator dispatches): (a) extend the mint-path
taps to cover the WHOLE `_buy_mint_attempt` guard chain — the affordable
verdict, each admission build (`None` vs built), the facts bind, and each
`_eligible` term with its values — so the next drop names itself instead
of being re-derived offline; (b) the capacity-parity arm (the seventh
arm): stamp the capacity receipt's observations fresh the way 2743782a
seeded zeny, or hold the `_fresh` capacity terms while the CONTEXT's
offer is bound (the same hold doctrine, consumer-side); RED-test at the
exact leg-56 shape (login-stamped weight pair + a 45s-old bound offer +
one heartbeat decide -> assert NpcShopPurchase mints).

## Leg 57 slice (feat/capacity-freshness-receipt): the seventh arm — the capacity
freshness hold landed; the economy's last named gate is open

The leg-56 receipt named the remaining gate precisely and this slice landed it.
WHERE THE GATE LIVED: `src/robots/adapters/native_purchase.py` —
`_capacity_fits`'s freshness term (`_fresh(weight.observed_at, now) and
_fresh(maximum.observed_at, now)`, the `_fresh` helper at the old line 67,
consumed at the old line 96): the 0xB0 param-24/25 pair is stamped with the
FRAME ARRIVAL time by `NativeCapacityContext._consume` (native_capacity.py),
which on this pin is LOGIN — the pair arrives once at login and a
decide-paced mint runs 15s+ later, so `0 <= now - at < 5.0` was
unsatisfiable by construction exactly as the receipt derived.

THE FIX (the receipt's option (b), the seventh arm, consumer-side hold):
while the shop CONTEXT carries a BOUND offer, the login-stamped pair stays
valid — a bound offer is RECEIVED DATA (the e2e-49 law) whose C6 row
re-proves the item's identity, and the server-side weight cannot have
changed without a wire update arriving (SP_WEIGHT rides on changes only,
pc.cpp:5810/5844). Real weight movers still gate through the untouched
`inventory_changed_sequence` term (0x0A37/0x00AF/0x07FA/0x0991/0x0A0D), and
the honest stale path is preserved: with NO bound offer the admission never
forms and the aged pair mints nothing (pinned). The `_fresh` window itself
is unchanged and now named `_FRESH_WINDOW = 5.0`.

THE TAP (tap-before-fix, the receipt's option (a) narrowed to this gate):
when the raw login-stamp freshness refuses on a mint-capable state,
`_capacity_fits` logs one shop-debug WARNING naming
`weight_age=..s max_age=..s window=5.0s held_by_bound_offer=..` — so the
next leg reads the hold's load-bearing role straight from the log.

TESTS (tests/test_buy_mint_seeded_wallet.py, the ready_shop harness, RED
verified before the fix — 2 failed / 2 passed on the pre-fix tree):
`test_aged_login_weight_pair_mints_while_offer_is_bound` (20s-old pair +
bound offer -> NpcShopPurchase mints; RED pre-fix at exactly the leg-56
shape: C6 BOUND, offer alive, zero actions),
`test_aged_login_weight_pair_without_bound_offer_still_refused` (same age,
no offer -> no mint; the guard that keeps the hold from being a global
relaxation), `test_freshness_refusal_tap_names_age_and_window` (the tap
line names both ages vs the window). Full gate GREEN before the commit (nix develop -c task check: 6693
passed + 65 subtests, 0 failed; black/mypy/ruff phases clean).


## Leg 57 window — the seventh arm's hold ENGAGED and the mint still starved: the remaining gate is a second, untapped term in the same consumption seam

Sunday 04:45-05:45 Madrid (03:45-04:45 UTC, day 6), launch 04:35:15 local
(receipt epoch 1793504122, duration 5700 s). 7/7 online the whole window,
steps 22706, 0 errors, 0 TRANSPORT DOWN, logins staggered clean.

THE VERDICT: the economy did not close (seventh window). zeny_wing
(300002) ended zeny 150 (delta 0), exp 28/27 (delta 0), no 1201 in
inventory - and the fixture is INTACT for the next arm (150z >= the
received price, knife still absent).

The tap delivered exactly what it was built to deliver, and it EXONERATES
the seventh arm's own term: the single at-bat ran TalkToNpc x1 ->
NpcShopBuySelection x1 -> `C6 seen (seq=70 issued=True after=69
consumed=False rows=213)` -> `C6 BOUND (seq=70 rows=19 npc=110001762)` ->
144 capacity-freshness taps, EVERY ONE reading `held_by_bound_offer=True`
(ages 6.9 s -> 301.6 s) -> `offer invalidated (offer-ttl-expired)
had_issued=True had_offer=True` -> NpcClose x3. NO NpcShopPurchase, no C8,
no 0xCA. Since the hold term is `fresh or context.offer is not None` and
the tap prints `context.offer is not None`, the freshness term PASSED on
all 144 mint attempts - the refusal is real but its CAUSE is a different
term of the same seam, still silent. Note the tap's wording is misleading
when held=True ("capacity freshness gate refused" logs whenever !fresh
even though the hold covers that term); the tuple in `_resources_fit`'s
`all(...)` is fully evaluated, so `_capacity_fits` runs and taps even when
an upstream currency/budget term is the actual killer. One at-bat again:
no re-arm after the closes (the known cadence gap), npc_stage resting in
{None, blocked}, `shop_offer` non-null in 10 receipt samples (the state
mirror DID surface the ~5 min bind this window).

THE NAMED NEXT SLICE (the eighth rung): term-level verdict taps across
the CONSUMPTION seam, each naming the FAILING TERM with both values per
the tap ladder's top-rung law - `_resources_fit`'s four terms (budget >=
stable_discount_price, currency.balance >= price,
`currency.epoch == context.offer.epoch and _fresh(currency.observed_at,
...)`, `_capacity_fits`) and `_capacity_fits`' remaining terms
(`capacity.epoch == context.offer.epoch`, account/character identity, the
integer/value checks, `weight.value + facts.loaded_weight <=
maximum.value`, and `inventory_changed_sequence is None or
weight.receipt_sequence >= capacity.inventory_changed_sequence`), plus a
final verdict line for the whole admission (minted vs denied-at-term).
Ranked suspects: the inventory-sequence term (any of the five
inventory-ish packet ids arriving after the login weight pair kills it
forever), the two epoch-match terms, and the budget term. Fix the tap
wording in the same slice so a held freshness reads as COVERED, not
"refused".

Field side: 49 attacks over four agents; kills landed in the DB
(NyxSong 118->124/73->77, RinceNyan 102->112/75->83, PipinWalker
69->73/40->42, PoringMuffin14 68->78/41->45); zeny delta 0 for all (no
sellable stock in any inventory - the sell arm had nothing to fire on).
Social arms exercised: FoundGuild x2, GuildInvite x12, InviteToParty x4,
PartyChat x25. zeny_wing zero attacks (dealer park all window) and s00
zero attacks (town patrol; its exp delta 0). Receipt:
`run/plain_host_receipts/population-receipt-57-1793504122.json`; log
`/tmp/population_leg57.log`.

feat/term-verdict-taps (this commit): term-level verdict taps across the
purchase seam - the seventh arm held 144/144 and the mint still starved, so
the failing term is now NAMED per attempt instead of guessed. Every seam
predicate is evaluated as a named `(label, verdict, values)` term
(`_Term` in native_purchase.py); `_facts_match`, `_resources_fit`,
`_capacity_fits` and `_stock_fits` route their EXISTING terms through the
builders unchanged in membership and order (the flattened conjunction is
boolean-identical to the nested `all(...)` sets - the whole purchase suite
passes untouched, 161 scoped tests), and `NativePurchase._eligible` is now
`all()` over the same composed terms. `mint()` logs ONE shop-debug WARNING
per consumed mint attempt while the shop CONTEXT carries a bound offer:

`shop-debug: mint verdict owner=True(...) offer=True(receipt=7) f_src=...
f_acct=True(7/7) f_char=True(8/8) f_epoch=True(1/1) f_npc=True(123/123)
f_map=True(prontera/prontera) f_item=True(1201/1201) f_client=True(1201/1201)
f_ordinary=True(True) f_nonstack=True(True) f_price=True(73) f_disc=True(61)
f_valid=True(until=150.0 now=100.0) deadline=True(now=100.0 deadline=200.0)
row=True((73,61,4) v (73,61,4) rows=1) budget=True(budget=61 price=61)
balance=True(balance=1000 price=61) currency=True(epoch 1/1 age=0.0s)
epoch=True(1/1) acct=True(7/7) char=True(8/8) cap_held=True(w_age=0.0s
max_age=0.0s window=5.0s) ints=True(weight=400 max=2000)
loaded_int=True(loaded=400) loaded_w=True(400+400<=2000) inv_seq=True(receipt=5
changed=None) slots_free=True(0/100) rows_int=True(0 rows)
no_knife_dup=True(knife rows=0) eligible=True(verdict)`

- format `label=<verdict>(<both values>)`, one `=False(...)` grep names the
  starving term; the aged-pair shape reads `cap_held=True(w_age=20.0s ...)
  eligible=True` (the hold covering the stale login stamp), a missing pair
  reads `capacity=False(weight=False max=True)`, unbound facts read
  `verdict=False(facts=False context=True)`.
- the capacity freshness refusal tap is now BOUND to once per offer identity
  (`_FRESHNESS_TAPPED` keyed on account/character/epoch/npc/map/opened/receipt
  - it fired 144 identical lines at ~2s cadence in leg 57); a genuinely newer
  C6 receipt re-arms it. Tests: tests/test_mint_verdict_tap.py (golden line,
  failing-term rendering, one-line-per-attempt + no-context bound, once-per-
  offer memo) and a memo-clearing autouse fixture in the seeded-wallet file;
  the tap is instrumentation only - no gate term, value or early return moved.

## 2026-11-01 ~09:50 — receipt: leg 58 - THE NAMED-TERM READOUT: the verdict taps (80c25b5f) fired and the failing term names itself in one grep — `row=False((50,50,5) v (50,50,4) rows=1)` with `stock=False(stock=True slots=None)` behind it; the economy did not close (eighth window)

Window 08:15-09:15 Madrid (07:15-08:15 UTC), Sunday day 6, runner up
08:05:23-09:40:23 (5700s), steps 22728, errors 0, zero TRANSPORT DOWN,
7/7 online, decides 78-140. Seed-zeny refreshed pre-launch from a fresh
char-table readback (zeny_wing 150z, no 1201 - the buy fixture armed).

zeny_wing ran the dealer trip in one at-bat: TalkToNpc ->
NpcShopBuySelection -> C6 BOUND at receipt=70, then the decide/tick-paced
mint consumed **146 attempts across the offer's FULL 300s TTL** (10
shop_offer non-null samples at the 30s cadence - the state surfacing and
the CONTEXT agreed; npc_stage rested at 'blocked' 170 samples, the leg-49
shape). Every prior arm verified engaged: no mint-skip taps (the sixth
arm's precondition held), and `cap_held=True(w_age=... max_age=301.8s
window=5.0s)` - the seventh arm held the login-stamped freshness pair the
whole way. The mint still returned False on every attempt, and the taps
named the terms:

    row=False((50,50,5) v (50,50,4) rows=1)
    stock=False(stock=True slots=None)
    eligible=False(verdict)

(one representative line of 146; all identical modulo timestamps -
owner/offer/f_src..f_valid/deadline/budget/balance/currency/epoch/acct/
char/ints/loaded_int/loaded_w/inv_seq all True; f_price=True(50),
f_disc=True(50) - this dealer's knife row is 50z/50z, not the golden
fixture's 73z/61z).

Reading the row term: the received exchange row (50,50,5) agrees with the
qualification (50,50,4) on price and discount but differs in the THIRD
field - 5 received vs 4 pinned. Identity is confirmed both sides
(f_item=True(1201/1201), f_client=True), so this is the row's volatile
third field carrying the RECEIVED wire value (5) where the qualification
pins the item-db value (4) - the exact class the price already moved for
(take the volatile fields from the RECEIVED row, bind only identity from
the pin). The golden test line passed because its fixture row carried the
pinned value on both sides (`row=True((73,61,4) v (73,61,4))`) - the live
dealer's row is where they diverge. SECOND gate behind it: the stock arm
reads `stock=False(stock=True slots=None)` - stock itself is True but the
slots term is None on this offer and the predicate vetoes; None must be
treated as unknown-not-zero (decode it or pass it), or the row fix alone
still leaves the mint starved.

DB ground truth (pre vs post, same baseline file): zeny_wing UNCHANGED
(exp 28/27, zeny 150, no 1201 in inventory) - no buy. Zero zeny moves
anywhere (no sells). Kill exp moved slightly: NyxSong +2 base, RinceNyan
+4/+2 (2 Porings), xXLunasongXx +2/+4, YuffieFy81 +2/+1; PipinWalker and
PoringMuffin14 patrolled prontera with zero exp. zeny_wing never re-armed
after the TTL (one at-bat per window again): parked at the dealer cell
(172,129), 79 decides, no further TalkToNpc.

NEXT SLICE: (1) the row match takes the received row's volatile fields
(price/discount/third-field) as the comparison source - identity stays
pinned; RED test: a received row whose third field differs from the pin
while identity matches must pass `_facts_match`. (2) the stock arm treats
slots=None as unknown (pass) or decodes it from the received frame; RED
test: stock=True with slots=None must not veto. Then the next leg closes
the economy or names the next term in one grep.

## 2026-11-01 ~10:25 — the two named terms landed (feat/received-row-law): the received-row law extends to the C6 row's volatile third field and slots=None is unknown-not-zero

Leg 58's readout named exactly two starving terms in 146 verdict lines; both
laws are now landed in `native_purchase.py` with the tests-first receipts:

- ROW LAW EXTENDED: the seam's row term compared
  `(price, discount, item_type)` against the template with the item-db
  weapon pin (4) hardcoded — the received C6 row carries the exchange's own
  third field (5 live). The template already takes price/discount FROM the
  received row (the seeded-wallet law: identity from the pin, price from the
  received row); the same law now covers the volatile third field. The row
  term compares the RECEIVED row against itself: identity by nameid (the
  filtered 1201 rows, exactly one), price/discount re-checked against the
  row-derived facts, and the type NEVER demanded equal to the db-pin. The
  qualify step (`_qualify_knife_facts`) is unchanged — the pin stays
  available there, the consumption seam just no longer re-checks it.
  `_row_values` renders the received row's own type as evidence
  (`row=True((73,61,5) v (73,61) rows=1)`).
- SLOTS UNKNOWN-NOT-ZERO: `_stock_checked` read `slots=None` through
  `_integer(slots, 1, 100)` as a veto; the allowance facts are ABSENCE of
  information, not zero free slots. The stock check now passes on
  stock=True alone (`_allowance_received`: None passes, a RECEIVED value
  must still be a real slot count — fail-closed on received-bad data,
  unknown on absent data). The one downstream slots consumer (`prepare`)
  guards on its own None: `_acquisition_bound` uses the absolute 100-slot
  pin cap (indices 2..101) while the allowance is unknown, slots+1 when the
  wire speaks. The denial-suite's old 'slots' case flipped to the new law
  (commented at the parametrize); the tap's golden verdict line reconciled.

RED receipts (exact leg-58 shapes, `tests/test_buy_mint_seeded_wallet.py`):
`row=False((73,61,5) v (73,61,4) rows=1)` and `stock=False(stock=True
slots=None)` reproduced before the fix; the absent-stock negative still
refuses. The golden-shape test (exchange type 5 + slots unknown + seeded
wallet) pins the FULL verdict line all-True with `eligible=True(verdict)` —
the line leg 59's brief can quote:

    shop-debug: mint verdict owner=True(len 7/7) offer=True(receipt=12)
    f_src=True(rathena-item-db-pin-2018) f_acct=True(999/999)
    f_char=True(77/77) f_epoch=True(1/1) f_npc=True(123/123)
    f_map=True(prontera/prontera) f_item=True(1201/1201)
    f_client=True(1201/1201) f_ordinary=True(True) f_nonstack=True(True)
    f_price=True(73) f_disc=True(61) f_valid=True(until=400.0 now=100.0)
    deadline=True(now=100.0 deadline=400.0) row=True((73,61,5) v (73,61)
    rows=1) budget=True(budget=80 price=61) balance=True(balance=80 price=61)
    currency=True(epoch 1/1 age=0.0s) epoch=True(1/1) acct=True(999/999)
    char=True(77/77) cap_held=True(w_age=0.0s max_age=0.0s window=5.0s)
    ints=True(weight=400 max=2000) loaded_int=True(loaded=400)
    loaded_w=True(400+400<=2000) inv_seq=True(receipt=13 changed=None)
    slots_free=True(1/None) rows_int=True(1 rows) no_knife_dup=True(knife
    rows=1) eligible=True(verdict)

(the log renders it as ONE line; the deciding terms are
`row=True((73,61,5) v (73,61) rows=1)` and `slots_free=True(1/None)`).

Gate: full `task check` green on the worktree — 6702 passed + 65 subtests,
coverage 95.36% (pre-lint: black/ruff/mypy/xenon clean; xenon took the new
checks as the named predicates `_allowance_received`/`_acquisition_bound`).
NEXT (leg 59): dispatch the window — the two named terms are gone; if the
economy still does not close, the next starving term names itself in one
grep of the same verdict tap.

## Leg 59 — Sun 2026-11-01 10:45-11:45 CET — THE ECONOMY CLOSED END TO END (the buy arm, every verdict term True)

HEAD at launch a8a9e0f5 (the fix-under-test b8edef4e merged below it).
Receipt `run/plain_host_receipts/population-receipt-59-1793525736.json`
(launch 10:35:36 CET, duration 5700s): steps 22707, step_errors 0, 0
TRANSPORT DOWN, 7/7 online through the window. Seed refreshed from the
pre-launch char-table readback (zeny_wing 150z, no 1201 — byte-identical
to the committed file); schedule verified committed as the bare mapping
`{persona: [[6, 10.75, 11.75]]}` x7.

The fixture agent `pop_0003_g00m02` (char 300002, zeny_wing) opened the
deal 12 seconds into the window (traces 09:45:08-09:45:12 UTC:
TalkToNpc -> NpcShopBuySelection -> **NpcShopPurchase** -> NpcClose),
and the server closed it: **the C8 went out, the 0xCA came back, zeny
150 -> 100 (-50, the received price) and 1201 amount=1 equip=0 appeared
in the inventory table. THE ECONOMY CLOSES END TO END.** The verbatim
verdict line (ONE line in the log, quoted wrapped):

    shop-debug: mint verdict owner=True(len 7/7) offer=True(receipt=70)
    f_src=True(rathena-item-db-pin-2018) f_acct=True(2200002/2200002)
    f_char=True(300002/300002) f_epoch=True(1/1)
    f_npc=True(110001762/110001762) f_map=True(prt_in/prt_in)
    f_item=True(1201/1201) f_client=True(1201/1201) f_ordinary=True(True)
    f_nonstack=True(True) f_price=True(50) f_disc=True(50)
    f_valid=True(until=1078636.72 now=1078336.72) deadline=True(...)
    row=True((50,50,5) v (50,50) rows=1) budget=True(budget=150 price=50)
    balance=True(balance=150 price=50) currency=True(epoch 1/1 age=0.0s)
    epoch=True(1/1) acct=True(2200002/2200002) char=True(300002/300002)
    cap_held=True(w_age=4.8s max_age=4.8s window=5.0s) ints=True(weight=0
    max=22700) loaded_int=True(loaded=400) loaded_w=True(0+400<=22700)
    inv_seq=True(receipt=36 changed=None) slots_free=True(0/None)
    rows_int=True(0 rows) no_knife_dup=True(knife rows=0)
    eligible=True(verdict)

The two laws under test fired exactly as landed: `row=True((50,50,5) v
(50,50) rows=1)` — the received-row law comparing the C6 row against
itself, identity-by-nameid only, never demanding template==row on the
volatile third field (live wire said 5; a db-pin 4 would have starved
all 146 leg-58 mints again) — and `slots_free=True(0/None)` — the
slots-unknown law passing on None. `cap_held=True` shows the
facts-seam freshness hold keying on the bound offer (w_age 4.8s inside
the 5s window at mint time). One mint verdict line in the whole log;
one purchase; the drive then re-armed ONE at-bat (second
NpcShopBuySelection, C6 BOUND seq=78) and stopped — honest, the agent
now OWNS a knife (`no_knife_dup` would read False; the drive's goal is
satisfied), not a re-arm defect.

Rest of the roster: six roamers at 90-108 distinct sampled cells,
decides 77-157, attacks 37 total; kills by DB exp delta = five killers
(NyxSong +8/+3 = Poring+Lunatic, PipinWalker +8/+3, xXLunasongXx
+18/+6, PoringMuffin14 +14/+6, YuffieFy81 +4/+3 — 52 base exp total);
zero sells (no zeny gain anywhere; the sell arm did not engage — no
agent carried derived sellable stock this window). g00m02's npc_stage
samples read blocked/opening (the known post-C6 resting shape, hold
proven); its shop_offer never appears in the 30s-cadence samples — the
context held it for ~16s, shorter than the cadence (the corollary:
zero-sample is not a surfacing gap). s00 pocket-escalated 8x
(`escalated_target_dead`) yet still farmed pay_fild04 (5 cells, +4 exp)
— the escalator honest-stopping, not frozen. RinceNyan roamed only 23
cells with 306 actions and 0 exp (6 attacks all pending_walk) — low
engagement, no gate anomaly; watch next leg, no defect class named.

NEXT (leg 60): the SELL arm close — loot -> dealer -> C7 sell list ->
sell -> a zeny GAIN in the DB (the remaining half of the loop; derive
the sellable set from the field's actual drops). Fixture policy: the
buy arm is proven; a re-run needs the fixture re-applied (DELETE the
1201 row, re-grant the 150z) or it will honestly refuse on
no_knife_dup.

## Leg 60 — Sun 2026-11-01 13:15-14:30 CET — THE SELL ARM DID NOT CLOSE (zero zeny movement; the loot seam named)

HEAD at launch 8ff5f3c0 (schedule fdd499b4 + seed refresh; code untouched
at the leg-59 binary a43f91e5).
Receipt `run/plain_host_receipts/population-receipt-60-1793534223.json`
(launch 12:58:23 CET, duration 6000s, the 75-minute window): steps 23906,
step_errors 0, 0 TRANSPORT DOWN, **7/7 online through the window** (149
consecutive all-seven samples t=1111.5->5559.6, i.e. ~13:17-14:31 CET;
0 online before login, 0 after the 14.5 close). Schedule verified
committed as the bare mapping `{persona: [[6, 13.25, 14.5]]}` x7; seed
refreshed from the pre-launch char-table readback and byte-matched to
the `char` table (zeny_wing 100z post-buy; NyxSong 8, RinceNyan 31,
PipinWalker 7, xXLunasongXx 0, PoringMuffin14 4, YuffieFy81 0).

DB READBACK, baseline vs end (post-close `char`+`inventory` probe):

    persona            zeny0  zeny1   d   inv0 inv1 dinv
    NyxSong                8      8   0      1    1    0
    RinceNyan             31     31   0      1    1    0
    zeny_wing            100    100   0      1    1    0
    PipinWalker            7      7   0      1    1    0
    xXLunasongXx           0      0   0      1    1    0
    PoringMuffin14         4      4   0      1    1    0
    YuffieFy81             0      0   0      1    1    0

**ANY_ZENY_GAIN: False.** No inventory delta anywhere (per-item diff
empty for all seven). The sell chain did NOT close on the sustained
repeat — this is the honest second branch of the acceptance: the
verbatim trace lines naming where the arm failed to engage.

THE SELL TRACE CHAIN, and the starving term:

1. The decider's choice set has NO sell option at all. Verbatim first
   window decide_response (pop_0003_g00m00 12:15:01 UTC):

       {"type": "choice", "choice": "grind", "probabilities":
       {"chat": 0.011592735377335638, "go_town": 0.016950380848342717,
       "grind": 0.8549057339855622, "idle": 0.017487722374160613,
       "loot": 0.05047873538978764, "quest": 0.010726922518529703,
       "rest": 0.02459496075765234, "travel": 0.013262808748629047}}

   go_town sat at 2-6% and was picked 0 times in 1133 window picks
   (grind 1113, loot 16, travel 4); `sell` is not even in the support.

2. When loot WAS chosen, it landed in the farm scripts with no pickup
   behind it. Verbatim pair (pop_0003_g01m02 13:18:17 UTC):

       decide_response: {"type": "choice", "choice": "loot",
        "probabilities": {..., "loot": 0.4209152586019135, ...}}
       script_step:     {"script": "GrindScript", "status": "ACTIVE",
                         "actions": ["MoveTo"], "nearest_monster_d": 11.2}

   Zero pickup-class actions executed all window (full action
   histogram: MoveTo, Attack, Rest, Say, PartyChat, GuildInvite,
   InviteToParty, FoundGuild — no Loot/Pickup/GetItem).

3. No drop ever surfaced to loot. Window world_event vocabulary:
   Heartbeat 622, MonsterSpotted 425, DamageTaken 63, ChatHeard 16 —
   zero ItemDrop/MonsterDied-class events. The field's drops never
   reach the agents' event stream, so the derived sellable set is
   EMPTY BY CONSTRUCTION: no loot -> no stock -> the merchant trip
   never armed -> the C7 never went out (0 shop-debug/mint/NpcShop
   lines in the whole runner log — the leg-59 sell tap never fired).

Roster activity: 345 attacks (g01m02 207, g01m01 75, g01m00 34,
g00m01 9, g00m02 9, g00m00 8, s00 3); s00 authored 98 plans yet held
pay_fild04 (198,178) all window — the escalator again honest-stopping
on its own cell, not frozen. Killer deltas not claimed this leg: the
pre-launch readback seeded zeny+inventory baselines but no exp
baseline (exp columns at close: 136/118/31/89/146/94/16).

NEXT (leg 61): the loot seam is the named starving term — surface the
field's drops to the agents (ItemDrop-class world events off the kill)
and give the loot choice a real pickup action; only then can the
derived sellable set be non-empty and the C7 sell arm engage. The buy
arm remains proven (leg 59) and the fixture policy stands: a re-run of
the buy needs the fixture re-applied (DELETE the 1201 row, re-grant
the zeny) or it will honestly refuse on no_knife_dup.

## 2026-11-01 (leg-61 slice) — THE LOOT SEAM REPAIRED: two broken hops found and fixed, taps in (feat/loot-seam)

The leg-60 receipt named the starving term; this slice traced the seam hop by
hop and found TWO breaks, not one:

1. THE PICKUP ENCODE WAS A DROP REQUEST (the deeper break).
   `native_gameplay.pickup()` sent `0x0362` — the 2010-era TakeItem row. At
   the pinned MAIN 20180704 the 20120418+ block RE-REGISTERS `0x0362` as
   `clif_parse_DropItem` (clif_packetdb.hpp:1561) and moves TakeItem to
   `0x07E4` (line 1560); the later registration wins in the compiled
   packetdb. Every loot pickup this codebase ever "sent" was a DropItem
   request (index.W/amount.W carved from the floor-item AID dword) that the
   server rejects silently — the same shape as the party-invite silent drop.
   Fixed: `pickup()` now packs `0x07E4` (6B, AID at offset 2, clif.cpp:12006
   `clif_parse_TakeItem`). The two byte pins that asserted `620341010000`
   (tests/test_native_gameplay.py, tests/test_playing_runtime.py) are
   reconciled to `e40741010000` with the registration cited.

2. THE WORLD-EVENT PRODUCER NEVER SURFACED DROPS.
   `PlayingClient.drain_native_events` minted MonsterSpotted/damage/dialogue/
   invite but NOTHING off `tracker.view.floor_items` — `ItemSeen` existed in
   the domain and was minted nowhere; zero ItemDrop-class events all window
   (the receipt's term 3). Fixed: `_floor_item_events` (new helper) mints one
   `ItemDrop` (nameid/x/y/amount/map/floor_item_id) per newly present floor
   item, once per presence (a set-diff cursor mirroring `_seen_actors`; aid
   reuse after a 0x00A1 disappear re-mints honestly). Registered in the
   `event_summary` table (raw dict lookup — unregistered classes crash the
   brain) and in trace_log's `_PAYLOAD_HANDLERS`.

3. THE DECIDER'S LOOT CHOICE GOT A REAL ACTION BEHIND IT.
   `next_action=loot` (16 picks in leg 60) was consumed NOWHERE — `_review_goal`
   reads only `change_goal`; the answer existed only in the schema. Fixed:
   `EventDrivenBrain._loot_choice_action` authors `Loot()` on an explicit loot
   answer (fail-closed: nothing on grind/travel/rest; an authored Attack is
   never interrupted; no stacked Loot), and the runtime's `perform_native`
   dispatches it against the tracked floor item (walks to it when far —
   `test_distant_loot_walks_using_public_geometry` already pinned that half).

TAPS (the leg-61 log greps): `loot-debug: floor item surfaced (nameid=%s
cell=(%s,%s) amount=%s fid=%s)` at the mint, `loot-debug: pickup dispatched
(fid=%s nameid=%s cell=(%s,%s))` at the wire send — shop-debug-style
logger.warning lines, one per surfaced drop / one per dispatched pickup.

Offline evidence: tests/test_loot_seam.py (5 contracts — encode pin, mint
once-per-presence + aid-reuse re-mint, both taps, loot-choice authoring +
the non-loot fail-closed guard); RED was captured per hop before the fix
(ImportError ItemDrop / `620341010000` != `e40741010000` / zero actions on a
loot answer). spikes/ untouched; no runner leg dispatched (the coordinator
merges and dispatches leg 61).

NEXT (leg 61 window): the wire proof — one window should show surfaced
lines off real kills, dispatched pickups, 0x0A37 acks, inventory deltas,
and then the sell arm's own seam (the derived sellable set -> merchant
trip -> C7) engaging on real stock.

## Leg 61 — Sun 2026-11-01 16:45-18:00 CET (day 6) — the loot->sell readout with the seam repaired (43b5cc2e)

Launch 16:27:47 CET (receipt `population-receipt-61-1793546826.json`), 7/7
online the whole window, `DONE: steps 23901, errors 0`, zero TRANSPORT DOWN.
Schedule was the bare mapping committed at a04979c9 (verified
`[[6, 16.75, 18.0]]` x7); seed-zeny refreshed from a fresh char-table readback
and committed pre-launch (acebeecb).

THE FIX'S HOPS, LIVE VERDICT:

- Hop 1 (ingest->event) LIVE: 39 `loot-debug: floor item surfaced` taps off
  real kills, e.g. `loot-debug: floor item surfaced (nameid=915
  cell=(267,330) amount=1 fid=288)` (16:53). Repeats per fid are the
  once-per-presence set resetting when an item leaves/re-enters the view.
- Hop 2 (event->brain) wired and working on the prior: ItemDrop rides
  `_drain_events`->`handle_event`; the loot probability rose through the
  window (mean ~0.02-0.03 early -> 0.13-0.29 late; loot was top-2 in 167/518
  decides).
- Hop 3 (choice->CZ_ITEM_PICKUP) NEVER EXERCISED: zero `pickup dispatched`
  taps, zero Loot actions in 4,471 executed actions (4,267 MoveTo, 114
  Attack, 0 Loot), zero loot choices in 518 decides. THE MECHANISM, FROM THE
  TRACES: `choice == argmax(probabilities)` in 518/518 decides, and loot
  never outranked grind (loot max 0.2865 vs grind >= 0.42). The pickup
  wiring is code-complete; its TRIGGER (a won loot choice) is starved by the
  argmax rule. That is the remaining dead hop — the decider's draw, not the
  seam's wiring.

DB ground truth (same readback before 16:26 / after 18:02): kills = exp
deltas on five agents (PipinWalker +10/+10, RinceNyan +9/+9, xXLunasongXx
+10/+4, zeny_wing +5/+4, YuffieFy81 +2/+1); zeny +0 on all seven; inventory
GAINED=[] on all seven (only the worn 1201 knife). No pickup -> no sellable
stock -> no merchant trip -> no C7 -> no zeny gain, exactly through the
named seam.

Secondary: PipinWalker sealed at prt_fild08 (270,329) ~65 min after his
kills (decides 180, position flat, `await_pending` gates); PoringMuffin14
(merchant-economy) parked at (87,305) the whole window again (165 decides,
26 actions, 2 script_steps); NyxSong zero kills. No new guild/party rows.

NEXT (leg 62): give the loot choice a win it cannot lose — either a
floor-item-contingent override (a tracked floor item within pickup range
makes loot outrank grind in the decide answer) or author Loot directly in
the farm script off `tracker.view.floor_items` (the runtime `_loot`
already walks-then-picks within 2 cells and taps the send). Then re-test
the sell arm on real stock: derived sellables -> merchant trip -> C7 ->
zeny GAIN.

## 2026-11-01 (leg-62 slice) — THE MECHANICAL LOOT PATH: a floor item dispatches the pickup without a decide (feat/mechanical-loot)

Leg 61 named the dead hop: the pickup wiring was code-complete but its
TRIGGER (a won loot choice) starved under the argmax rule (0 loot choices /
518 decides while 39 ItemDrop events surfaced). The fix is a loot win the
argmax cannot lose: the runtime's mechanical layer (the seam that owns the
buy mint, `playing_runtime.py`) now owns the pickup outright.

WHAT LANDED (`_loot_mechanical`, called from `mechanical_actions` between
the npc layer and the legacy path):

- In pickup range (Chebyshev<=1 of the drop's cell, the server's radius):
  mints `Loot()`; the dispatch goes through the shared `_loot`, which now
  memoizes the send per floor item (one CZ_ITEM_PICKUP attempt while the
  item is on the floor view — the decider's loot choice lands on the same
  memo, so neither path can spam). New tap:
  `loot-debug: mechanical pickup dispatched (fid=... nameid=... cell=(x,y))`.
- Out of range: mints `MoveTo` toward the drop's cell, one move per item —
  walkability-aware (the drop's own cell when the grid walks it, else
  `nearest_walkable` radius 4; no walkable alt names `loot_target_unwalkable`,
  no map cache names `loot_no_map_cache`). New tap:
  `loot-debug: move toward floor item (fid=... nameid=... cell=(x,y) target=(x,y))`.
- The leg-61 guard carries over: an authored Attack (an in-melee exchange)
  is never interrupted, and an authored Loot stands the mechanical step
  down — the decider's 43b5cc2e choice remains the alternative trigger and
  keeps working where a plan owns the stream (the mechanical layer is
  bypassed there).
- The memo clears when the item leaves the floor view (presence-keyed; a
  reused aid is a real new drop).
- `_loot`'s send gate tightened from hypot<=2 to the server's Chebyshev<=1
  radius (the looser gate burned the one attempt on silent out-of-range
  rejects); its out-of-range walk leg and send tap unchanged. The old
  `_loot_first` injection folded into `_loot_mechanical` — one loot owner
  in the mechanical layer instead of two.

TESTS: `tests/test_loot_priority.py` rewritten to the mechanical contract
(7 tests: in-range one-send, the two-step move-then-pickup, the melee
guard, the spam memo, the presence clear, the walkability reroute, the
taps) — all RED before the implementation (the out-of-range tick authored
`Loot()` instead of the move; no memo; no taps). Full gate green:
`nix develop -c task --dir . check` — 6711 passed, 65 subtests passed,
coverage 95.33%.

NEXT (leg 62 live window): the receipt should show, per surfaced drop,
either a `move toward floor item` then a `mechanical pickup dispatched`
pair, or a direct dispatch when the kill lands adjacent; the sell arm then
re-tests on real stock (derived sellables -> merchant trip -> C7 -> zeny).

## Leg 62 (Sun 2026-11-01 20:15-21:30 Madrid = 19:15-20:30 UTC) — the pickup readout with the mechanical loot path (79a66511)

Runner: duration 6000s from 20:05:21, receipt `population-receipt-62-1793559921.json`. 7/7 online
149/200 samples, ZERO TRANSPORT DOWN, 23,894 steps, no step/rx/dispatch errors. Decides 110-387,
10,516 executed actions in-window, real displacement on six agents (s00: 16 distinct cells, the
known pay_fild04 pocket). attack_gates census {pending_walk 2123, resting 836, target_not_visible 85};
move_gates {await_pending 9207, no_route_direct 832, not_standing 2}.

THE FIX UNDER TEST (the mechanical loot path) — first two rungs LIVE, the dispatch rung dead:
- Hop 1 PROVEN: 21 `loot-debug: floor item surfaced` taps (~6 unique fids 311-317; species 909/938/705/713),
  all off real kills (6/7 agents gained exp: +1..+10 base, e.g. xXLunasongXx 156->166/90->94).
- Hop 2a PROVEN: 5 `loot-debug: move toward floor item` mints, verbatim:
  `loot-debug: move toward floor item (fid=313 nameid=909 cell=(181,370) target=(181,370))`
  (also fid=314 nameid=938 (182,369), fid=315 nameid=705 (172,363)).
- Hop 2b DEAD: ZERO `loot-debug: mechanical pickup dispatched` lines, ZERO inventory gains
  (DB inventory unchanged: 7x worn knife 1201 equip=2), ZERO zeny movement (all seven +0).
  THE FULL LOOP DID NOT CLOSE. Mechanism: the drops live ~60s server-side; the kill burst ran
  20:17-20:34 and the walk mints went out 20:26-20:41 — by adjacency the item was already gone
  from the tracked view (PoringMuffin14 STOOD at (180,370), adjacent to fid 313's (181,370),
  with no pickup tap and no view row left), the grind's Attack-authored steps leave few quiet
  steps inside the TTL, and the per-item move memo gives each drop exactly ONE walk attempt
  (a script MoveTo pre-empting the loot walk burns it).

THE CRASH (pre-existing, NOT introduced by 4bbb108a — leg 61's log carries 22 identical failures):
every ItemDrop/ItemSeen/Arrived delivery raised `TypeError: TraceLog.log() got multiple values for
keyword argument 'x'` in `_trace_event` (agent context x/y vs the event payload's x/y) — the tick
died BEFORE `brain.handle_event`, 18 lost ticks this leg, and the traces contain ZERO ItemDrop rows
while the producer taps fired. CONSEQUENCE: leg 61's "the decider's argmax starved the pickup"
verdict was incomplete — the decider never saw ONE ItemDrop; the event trigger was structurally
dead, not out-argmaxed. FIXED at fe963891 (mid-window commit; cannot affect this leg — modules
bind at launch): `_trace_event` merges the payload with colliding keys suffixed `_event`, RED test
delivers ItemDrop/Arrived/ItemSeen through `deliver_event`, gate green (6712 passed).

NEXT (leg 63, with fe963891 in): the pickup must win the race against the ~60s floor lifetime —
evaluate minting the walk AT the surfaced tap (not the first quiet step), re-minting instead of the
one-shot memo (a pre-empted walk currently burns the drop), and the immediate dispatch when the
killer stands adjacent at death time (drops land ON the kill cell). Then the sell arm re-tests on
real stock (derived sellables -> merchant trip -> C7 -> zeny). Also verify leg 63's traces now carry
ItemDrop world_event rows (the repaired delivery) — a zero there means the fix did not participate.

## Leg 63 slice (pre-window, branch `feat/loot-pace-safety`) — the loot pace + the safety gate (Otto's directive)

Two fixes to the mechanical loot path, both named by leg 62's receipt:

THE LOOT PACE — a floor-item MoveTo now re-authors ONCE per item on a bounded
faster clock (`LOOT_WALK_REAUTH_S = 1.0` in playing_runtime, inside the
pending-walk lifecycle's own 1s no-progress release, never spam): leg 62's
one-shot move memo gave each drop exactly ONE walk attempt and a pre-empting
script MoveTo or an `await_pending` gate (9207 in the receipt) burned it
before any cell was sent. The re-auth clock anchors at the FIRST mint
(`_loot_walk_reauth_due` / `_loot_walk_mark_mint`, presence-keyed memos in
`_refresh_loot_memo`); the re-authored mint carries `reauth=1` in the
`loot-debug: move toward floor item` tap so the window log proves the pace
live. The per-item pickup memo (4bbb108a) still governs the pickup attempt —
one CZ_ITEM_PICKUP per item, unchanged.

THE THREAT GATE (Otto: LOOT ONLY WHEN SAFE) — `ACTIVE_THREAT_RANGE =
MELEE_RANGE + 2` (Chebyshev, the brain's `_attackable_in_melee_range`
precedent): `_nearest_active_threat` reads the state's nearby attackables and
when one stands within range the WHOLE loot path defers — no walk mint, no
Loot authored, and the send seam (`_loot`) refuses the decider's authored
Loot too, WITHOUT consuming the pickup memo (the item stays lootable once
the threat leaves). The in-flight-Attack guard (43b5cc2e) carries untouched.
Tap: `loot-debug: pickup deferred (threat) (fid=... nearest=...)`, once per
item while the threat stands (`_loot_defer_tapped`, presence-keyed — no
per-tick spam). When threatened the item may despawn: safety over loot.

Tests: tests/test_loot_priority.py grows 7 (RED first): the re-author
clock (paced on the client's injected monotonic — the constant asserted,
never sleeps), the safe-pickup control, the threat defer + tap + bounded
re-tap, the boundary (Chebyshev 3 defers, 4 fires), the in-flight-Attack
carry, and the threat-walks-away recovery (a 0x09FD move entry moves the
mob's tracked destination out of range; the pickup then fires). Scoped:
loot_priority+loot_seam+playing_runtime+shop_sell_loop 152 passed; full
gate `nix develop -c task --dir . check` green before commit.

NEXT (leg 63 window): the receipt should show, per surfaced drop, either the
direct `mechanical pickup dispatched` (killer adjacent at death time), or the
move tap then the dispatch, with `reauth=1` naming any second mint; the
`pickup deferred (threat)` lines should pair with the grind's combat windows
and vanish when the mob leaves. Zero `deferred (threat)` lines in a leg with
real mob contact means the gate did not participate.

## Leg 63 — Sun 2026-11-01 23:15 → Mon 00:30 CET (midnight-crossing, both fragments) — EVERY PICKUP KILLS ITS OWN SESSION: the pace+gate taps proved (surfaced→dispatched ×4), and the served 0x07E4 packetdb row is named as the remaining dead hop

Window ran clean: launched 23:05:21 (6000s), window-1 opened t=631 (23:15:32), the day-6→day-0
rollover passed with continuous 1s flags (t=3275.9 → 3306.0, no midnight stall), window-2 closed
t=5079 (00:30:19) with all flags dropping on schedule, runner DONE steps 23905 / errors 0, receipt
`population-receipt-63-1793570735.json`. Server-side the window is exactly one login cycle (7 logins
~23:15, no 00:00 relogin, clean logoffs at 00:30 for the survivors).

THE FIX UNDER TEST (5a0fb61b) at its taps: 12 loot-debug lines — 8 `floor item surfaced`
(909/512/938/705, fids 319–323) and 4 `pickup dispatched` (fid=319/321/322/323), every drop surfaced
with the killer already inside the pickup radius so the dispatches all went through the shared `_loot`
seam. The new-code taps stayed silent *correctly*: 0 `mechanical pickup dispatched` / 0 `move toward
floor item` (the mechanical limb never needed to mint — nobody was out of range) and 0 `pickup
deferred (threat)` (no mob ever closed within `ACTIVE_THREAT_RANGE`, so the gate never participated —
the leg-63 slice's NEXT note called this: silence with no contact is expected, not failure).

THE DEAD HOP, server-side verbatim (docker logs e2e map-server):
`[Warning]: clif_parse: Received packet 0x07e4 with expected packet length 319, but only 6 bytes remaining, disconnecting session #9.` —
and the same for 321/#12, 322/#8, 323/#11 — followed by `Character 'RinceNyan'/'xXLunasongXx'/'NyxSong'/'PipinWalker' logged off.`:
EXACTLY the four agents that dispatched pickups, and the "expected packet length" values ARE the fids.
The served binary (rathena-playable:20180704-e985006171d2) parses 0x07E4 as VARIABLE-LENGTH — it reads
the declared length at offset 2, which is the fid — while the builder (`native_gameplay.py:141`,
`struct.pack("<HI", 0x07E4, fid)`) pins the fixed-6 TakeItem row (clif_packetdb.hpp:1560). The bot's 6
bytes are correct FOR a TakeItem,6 server; the served packetdb row is the 20090818
`ItemListWindowSelected,-1` row instead. Both rows exist at identical lines in the repo tree and the
callback-qualified snapshot, and `packetdb_addpacket` overwrites in source order (the 20120418 block
SHOULD win) — so the served image's build/init diverges from the tree. Bisect next leg: (a) the image
builds from a divergent/stale source pin, (b) its init order differs, (c)
docker/rathena.Dockerfile's PACKETVER sed targets src/common/mmo.hpp which has no such define (the
operative one lives in src/config/packets.hpp; the recovery recipes compile with
`-DPACKETVER=20180704 -DPRERE`) — a silent no-op sed on the container path.

Economy truth at close: picklog EMPTY, zenylog 0, inventory 8 rows (7 starter Knives 1201 + fixture
714) — zero loot rows anywhere, zeny byte-identical to seed (8/31/100/7/0/4/0, no gain on any char),
sell arm never armed. FULL LOOP STILL OPEN, one hop from proven: the pickup send never reaches
`clif_parse_TakeItem`.

Resilience finding for the runner: only the FIRST server EOF printed `TRANSPORT DOWN` (g00m01 t~650);
the other three EOFs surfaced only as `action X failed: native playing transport unavailable` with
frozen counters (decides 6/17/10/85 for exactly the four dead agents; receipt `rx_error` carries EOF
for those four and nothing else) while SCHED kept reporting them online at frozen positions all
window. An EOF'd wire should be flagged offline (or relogged), not reported online.

NEXT (leg 64): make the served 0x07E4 row TakeItem,6 (rebuild/re-pin the rathena image; verify with a
6-byte pickup probe — expect NO disconnect and a picklog P row), and harden the runner's EOF handling.
Then inventory gains → sell arm → C7 → zeny is the same chain leg 62/63 already mapped.

## 2026-11-02 (leg-64 slice, branch `feat/pickup-frame-varlen`) — THE PICKUP SPEAKS THE SERVED DIALECT: the 0x07E4 builder + framer table align with the served packetdb's var-len declaration (the leg-63 session killer)

Leg 63 proved every pickup disconnected its own session: the served binary
(rathena-playable:20180704-e985006171d2) parses CZ_ITEM_PICKUP 0x07E4 as
VARIABLE-LENGTH — it reads the declared length at offset 2, which was the
floor-item AID in the builder's fixed 6-byte TakeItem frame ("expected packet
length 319, but only 6 bytes remaining"). This slice takes the CLIENT-side
half of the fix (the brief's choice; the image-row bisect/rebuild of the
receipt's NEXT note stays open for the coordinator):

- THE SERVED ROW: `parseable_packet(0x07e4,-1,clif_parse_ItemListWindowSelected,2,4,8,12)`
  (clif_packetdb.hpp:1268, the 20090818 block) — not the tree's
  `parseable_packet(0x07E4,6,clif_parse_TakeItem,2)` (line 1560). The served
  length gate (clif.cpp:25757-25776) reads the length word at offset 2,
  requires `4 <= declared <= 32768` and RFIFOREST >= declared, then consumes
  exactly `declared` bytes.
- THE FRAME: `native_gameplay.pickup()` now emits type.W + len.W(total=8) +
  AID.L — 8 bytes, e.g. `e407080041010000` for fid 321 — the 0xC6/0xC7
  var-len precedent (pdb.pack prepends 4 + len(payload)). The declared length
  matches the frame, so the served parser consumes it cleanly; the
  ItemListWindowSelected handler then no-ops for a bot with no menuskill
  (clif_menuskill_clear + return), so the SESSION SURVIVES. Honest boundary:
  the pickup still does not reach clif_parse_TakeItem until the served row is
  TakeItem,6 — no picklog P row is claimed by this slice.
- THE FRAMER TABLE: spikes/003-clientless-limbs/packetdb.py gains the
  append-only block `PACKET_DB.update({0x07E4: -1})` +
  `_NATIVE_REGISTRATION_SHADOWS.update({0x07E4: (6, -1)})` (the tree-derived
  table says TakeItem,6 by later-wins; the served binary obeys the -1 row —
  the same separate-authorities shadow as 0x2C4/0x0168, recorded so
  packetdb.self_test stays true). The table count stays 910 (a value
  override, not an addition).
- TESTS: new tests/test_pickup_frame_varlen.py pins the builder's golden
  bytes + length field, the framer's -1 registration, the served-parser
  desync harness (golden byte test + fragment reassembly at every split),
  the historical leg-63 fixed-frame disconnect signature, and the shadow/
  self-test contract. Reconciled to the new contract: the pickup byte pins
  in test_native_gameplay.py / test_playing_runtime.py / test_loot_priority.py
  (PICKUP fixture) / test_loot_seam.py, the era chains + stripped-digest
  chains in test_native_emotion_framing.py / test_native_npc_close_framing.py /
  test_native_npc_cutin_framing.py / test_native_wear_equip_ack_framing.py,
  and the dialogue-era baseline comparison
  in test_native_npc_dialogue.py (0x07E4 excluded from `old`, compared as the
  served -1 row). New packetdb.py digests were read from the pytest failures
  and appended with comments, never hand-computed.

## Leg 64 (Mon 2026-11-02 03:15-04:30 CET, day 0) — THE PICKUP SURVIVAL READOUT: the served-dialect 0x07E4 holds every session; the served image's 0x07E4 row is the remaining dead hop

Fix under test c9f00fa4 (ded48f5a): CZ_ITEM_PICKUP rebuilt as the SERVED packet_db declares it — var-len `type.W + len.W(8) + AID.L` against the pinned image's 20090818 row `parseable_packet(0x07e4,-1,clif_parse_ItemListWindowSelected,2,4,8,12)` (clif_packetdb.hpp:1268; the 0xC6/0xC7 precedent), not the tree's later `parseable_packet(0x07E4,6,clif_parse_TakeItem,2)` row (line 1560, not what the binary obeys).

**VERDICT: THE SESSIONS SURVIVE — 4/4 dispatched pickups, 4/4 sessions alive after the send.** The leg-63 killer (the fixed 6-byte TakeItem frame made the served parser read the AID word as a length word -> "expected packet length 319, but only 6 bytes remaining, disconnecting session #N") did not fire once. 0 TRANSPORT DOWN, 0 Traceback, 0 step/rx/dispatch errors across 23,498 steps; 7/7 online=1 through the whole window; clean logoff at the 04:30 close (t=5112, on the dot).

**The full loop did NOT close — and that is the shim's designed outcome, not a regression.** Zero inventory gains, zeny unchanged on all 7 (8/31/100/7/0/4/0), no C7. The served dialect parses our frame with the ItemListWindowSelected handler, which no-ops for a bot with no menuskill (clif_menuskill_clear + return): the send is consumed harmlessly and never reaches clif_parse_TakeItem, so the item stays on the floor and the pickup never lands. **THE REMAINING DEAD HOP: the SERVED IMAGE'S 0x07E4 row itself** — the leg-64 bisect note the pickup() docstring carries. Next slice: rebuild the image's packet_db row (0x07E4 -> clif_parse_TakeItem, 6) or otherwise reach TakeItem at the served offsets, then re-run this window unchanged client-side — inventory gains become reachable with the wire shape already proven safe.

Verbatim taps (four surfaced -> four dispatched; /tmp/population_leg64.log):
- `loot-debug: floor item surfaced (nameid=909 cell=(225,173) amount=1 fid=324)` -> `loot-debug: pickup dispatched (fid=324 nameid=909 cell=(225,173))` (Jellopy, YuffieFy81, pay_fild04)
- `loot-debug: floor item surfaced (nameid=713 cell=(232,372) amount=1 fid=325)` -> `loot-debug: pickup dispatched (fid=325 nameid=713 cell=(232,372))` (Empty Bottle, NyxSong)
- `loot-debug: floor item surfaced (nameid=705 cell=(204,342) amount=1 fid=326)` -> `loot-debug: pickup dispatched (fid=326 nameid=705 cell=(204,342))` (Clover, xXLunasongXx)
- `loot-debug: floor item surfaced (nameid=949 cell=(205,341) amount=1 fid=327)` -> `loot-debug: pickup dispatched (fid=327 nameid=949 cell=(205,341))` (Feather, xXLunasongXx)

In-range proof from the traces: the Loot rows executed ADJACENT to the drops — NyxSong at (231,373) vs (232,372) = Chebyshev 1 at 02:55:16 UTC, xXLunasongXx at (203,343) vs (204,342)/(205,341) = Chebyshev 1/2 at 03:04:26/27 UTC — and every action stream ran on for minutes after the send (the `_loot` send seam: the dispatched tap sits immediately before `wire._send(pickup(fid))`).

Death-stall recurrences (the standing open defect, fresh data): RinceNyan (g00m01) action stream dead since 02:28:30 UTC, tracker frozen at (235,344) through 140 decides; YuffieFy81 (s00) dead since 02:27:51 UTC, frozen at (233,176) through 135 decides; both DB rows fell back to EXACT save cells at readback (prontera 150,143 / pay_fild04 206,175 — the respawn fingerprint). The 0x0091 latch-clear did not release either. Both deaths land ~02:27-02:28 UTC, ~12 min into the window, on different maps.

Receipt `run/plain_host_receipts/population-receipt-64-1793585142.json` (launch 03:05:42 CET, duration 5900s): 11,732 executed actions (MoveTo 11569, Say 55, PartyChat 41, Attack 41, Loot 6 rows / 4 sends, GuildInvite 12, FoundGuild 2, InviteToParty 4, Rest 2), 794 decide_responses (95-140 per agent), move_gates await_pending 9554 / no_route_direct 203 / no_position_or_dead 151 / rerolled 3 / escalated 2, attack_gates pending_walk 662 / resting 152. DB exp deltas: NyxSong +4/+2, RinceNyan +4/+5 (frozen at death), xXLunasongXx +2/+1, YuffieFy81 +2/+1 (frozen at death). Schedule `run/reviews/population-live-schedule-leg64.json` held the bare mapping; seed-zeny refreshed pre-launch (15adb284, values unchanged).
\n
## Leg 65 fix (Mon 2026-11-02, offline slice, branch feat/real-takeitem-id) — THE REAL TAKEITEM ID: the compiled 20180704 table ends at 0x0362,6,clif_parse_TakeItem,2; 0x07E4 stays the window selection

Leg 64's "next slice" question answered FROM THE DB, no image rebuild needed: the served image ALREADY registers TakeItem — at 0x0362. `packetdb_readdb` (clif.cpp:25845-25847) memsets the table then includes `clif_packetdb.hpp` and `clif_shuffle.hpp` IN ORDER, and `packetdb_addpacket` (clif.cpp:25808-25834) is a plain last-write-wins assignment, so the compiled 20180704-PRERE profile (rathena/config.log:749 `-DPACKETVER=20180704 -DPRERE`) ends at `clif_shuffle.hpp`'s `#elif PACKETVER > 20180307` block (20180704 has no exact-date block; "Clients after 2018-03-07bRagexeRE do not have shuffled packets anymore"), whose final rows read verbatim:

    parseable_packet(0x0362,6,clif_parse_TakeItem,2);
    parseable_packet(0x07E4,-1,clif_parse_ItemListWindowSelected,2,4,8,12);

Confirmed by preprocessing both headers with the exact compiled flags: the last active rows are `packetdb_addpacket(0x0362,6,clif_parse_TakeItem,2,0)` and `packetdb_addpacket(0x07E4,-1,clif_parse_ItemListWindowSelected,2,4,8,12,0)`. The leg-61 "0x0362 = DropItem (plain-table 20120418 block)" reading and the leg-64 var-len 0x07E4 send were both plain-table/shallow readings overridden by the shuffle's final block: the leg-64 sends were window selections BY ID — parsed by ItemListWindowSelected, no-op for a bot with no menuskill, zero inventory — exactly the receipt's "remaining dead hop".

Landed (TDD RED-GREEN, worktree /tmp/wt-takeitem-id): (1) `pickup()` (src/robots/adapters/native_gameplay.py) emits the REAL id with the SERVED fixed-row shape — `struct.pack("<HI", 0x0362, aid)`, 6 bytes, NO len.W (fixed-size C->S rows carry no length word); (2) the packetdb registers `{0x0362: 6}` explicitly (append-only, source-cited leg-65 block; the numeric section already carried 6 — the value is unchanged, the registration is now named); (3) 0x07E4 stays registered -1 as the window-selection row leg 64 proved parses safely (shadow (6,-1) and self_test untouched); (4) new `tests/test_pickup_frame_takeitem_0362.py` pins the golden bytes `620341010000` (AID 321), the framer fixed-pack identity, the uint32 boundaries, the fixed-row desync-free framing at every fragment boundary, and the runtime dispatch (`perform_native(Loot())` -> `wire.sent == [0x0362 frame]`).

Reconciled pins (old contract named, not deleted): test_pickup_frame_varlen.py is now the 0x07E4 history file (the served -1 row framing, the leg-63 disconnect signature `e40741010000`, and the dead-hop regression guard `pickup(321) != e407080041010000`); byte pins flipped to `620341010000` in test_loot_seam.py / test_loot_priority.py (PICKUP) / test_native_gameplay.py / test_playing_runtime.py; the packetdb stripped-digest chains gained the leg-65 era digests read FROM the pytest failures (`62cf3228`+`07a4acde` in test_native_npc_close_framing.py, `656f1bcc` in test_native_wear_equip_ack_framing.py, `910c70e7` in its three-guild chain, `23282dc1` in test_native_npc_cutin_framing.py) — never hand-computed.

Full gate green after two digest-chain reconcile rounds (the first gate run surfaced the four unreconciled chains): 6758 passed, 65 subtests passed, coverage 95.35% >= 85%, exit 0. Next: the coordinator merges and dispatches leg 65's window — the dispatch seam and lootDebug taps are unchanged, so the readout reads the same taps with the pickup expected to LAND (inventory gains become reachable with the id now pointing at TakeItem).

## Leg 65 window (Mon 2026-11-02 06:45-08:00 Madrid / 05:45-07:00 UTC) — THE REAL-ID PICKUP READOUT: 0x0362 fixed-6 DISPATCHED, INVENTORY GAINS IN THE DB, THE FULL LOOP CLOSED (zeny)

**VERDICT: THE FIX WORKS END TO END — pickups DISPATCHED on the real TakeItem id (71131a84), sessions SURVIVED, INVENTORY GAINS in the DB, and THE FULL LOOP (pickup -> dealer sell -> zeny GAIN) closed on three chars.** Launched 06:35:04 CET (receipt epoch 1793597704), duration 6000s; the 06:45 window opened on the dot (CLOCK: (0, 6.58) pre-open with SCHED all-False, logins fired at 6.75); 7/7 online=1 by 06:50; clean logoff at the 08:00 close (t=5112 region, online=0 on every sample after); runner DONE at t=6000: steps 23,881, errors 0. ZERO `TRANSPORT DOWN`, zero Traceback/tick-failed, zero `no_position_or_dead` move-gates (the leg-64 death-stall pair did NOT recur — DamageTaken x49 across the roster but exp kept climbing and positions kept moving all window).

The four dispatched pickups (verbatim taps, /tmp/population_leg65.log — 19 `floor item surfaced`, 4 `pickup dispatched`, 0 `pickup deferred (threat)`):

- `loot-debug: floor item surfaced (nameid=909 cell=(185,341) amount=1 fid=335)` -> `loot-debug: pickup dispatched (fid=335 nameid=909 cell=(185,341))` (Jellopy)
- `loot-debug: floor item surfaced (nameid=938 cell=(186,339) amount=1 fid=336)` -> `loot-debug: pickup dispatched (fid=336 nameid=938 cell=(186,339))` (Sticky Mucus)
- `loot-debug: floor item surfaced (nameid=909 cell=(173,353) amount=1 fid=338)` -> `loot-debug: pickup dispatched (fid=338 nameid=909 cell=(173,353))` (Jellopy)
- `loot-debug: floor item surfaced (nameid=909 cell=(256,332) amount=1 fid=340)` -> `loot-debug: pickup dispatched (fid=340 nameid=909 cell=(256,332))` (Jellopy)

Every send SURVIVED (zero desync — the leg-63 killer stayed dead) and this time the pickups LANDED: baseline inventory was knife-only (7x 1201 equip=2, read back fresh pre-launch); the mid-window DB probe showed NyxSong +1x Jellopy (909, equip=0) and PoringMuffin14 +1x 909 — the direct inventory-gain acceptance — and the final readback keeps NyxSong's 909 held while PoringMuffin14's is gone (sold).

THE FULL LOOP: 21 ItemDrop world events off the kill bursts; Loot x64 authored roster-wide; the three g01 agents each ran TalkToNpc(1) -> NpcShopSellOpen(1) -> NpcShopSell(1) at the prt_in dealer (their samples parked at prt_in 172-173,128-130 with npc_stage non-null on 124-139 of 200 samples) and zeny MOVED in the DB: PipinWalker 7->42 (+35), xXLunasongXx 0->3 (+3), PoringMuffin14 4->7 (+3). The knife-only baseline makes the attribution clean: every zeny gain traces to THIS leg's picked-up drops sold at the dealer. Exp deltas on five chars: PoringMuffin14 +11/+5, NyxSong +6/+3, xXLunasongXx +8/+3, YuffieFy81 +2/+1, PipinWalker +1/+1.

Remaining gaps (next-slice material, none acceptance-failing): (1) YuffieFy81 (s00, pay_fild04) authored/executed 50 Loot steps with ZERO dispatch taps — her loot never closed to Chebyshev<=1 inside the ~60s drop TTL (walk-toward mints burn the window on a patrol that keeps re-targeting); (2) NyxSong walked to the dealer cell HOLDING the unsold Jellopy and ended with npc_stage null on every sample — the sell arm never clicked for it (vs the three g01 sell trips): a loot-holding agent already at the dealer needs the sell arm to re-arm; (3) zeny_wing parked at prt_fild08 (188,346) all window (35 MoveTos, 5 Attacks, 0 exp) — engagement efficiency, not the loop.

Receipt `run/plain_host_receipts/population-receipt-65-1793597704.json` (200 samples, step_errors 0): decides 114/153/162/112/124/123/250, move_gates await_pending ~1430 each / no_route_direct 9-140 / target_unwalkable_rerolled 1 / target_unwalkable_escalated 1, attack_gates pending_walk 174-670 / resting 176-420. Schedule `run/reviews/population-live-schedule-leg65.json` (8872300c) held the bare mapping day 0, 6.75-8.0; seed-zeny re-derived from a fresh pre-launch char readback (8/31/100/7/0/4/0 — unchanged from the committed file, nothing to commit).

## Leg 66 window (Mon 2026-11-02 09:15-10:30 Madrid / 08:15-09:30 UTC) — THE SUSTAIN WINDOW: THE CLOSED LOOP REPEATED AUTONOMOUSLY, TWICE

**VERDICT: REPEAT CONFIRMED — leg 65's loop re-ran with zero intervention, and this time a SECOND agent completed the FULL loop on loot it picked up in the same window (kill -> drop surfaced -> pickup dispatched -> carry to dealer -> sell -> zeny gain).** Launched 09:06:32 CET (receipt epoch 1793606810), duration 6300s; the 09:15 window opened on the dot (CLOCK: (0, 9.1) pre-open with SCHED all-False, logins fired at 9.25); 7/7 online (MAX simultaneous online = 7); clean logoff at the 10:30 close; runner DONE at t=6300: steps 25,056, errors 0. ZERO `TRANSPORT DOWN`, zero Traceback. Seed verified delivered: every persona's first state_tick read zeny 8/31/100/42/3/7/0 — exactly the refreshed seed (7a9647e6).

Acceptance, all DB-backed against the 08:56 pre-launch readback: **10 `pickup dispatched` taps (7 unique fids)** and inventory GAINS (YuffieFy81 +6 carried items: 511x2, 905x3, 906x1; xXLunasongXx picked up a 909 and sold it); **zeny gains NyxSong 8->11, xXLunasongXx 3->6**; kill exp on four chars (RinceNyan +4/+2, PipinWalker +6/+2, xXLunasongXx +4/+3, YuffieFy81 +4/+3).

**Leg-65 defect (1) — NyxSong's sell re-arm: DID NOT RECUR; the stock was seen, the dealer offer arrived, the drive held — sale landed 40 seconds after login.** Verbatim trace rows (`pop_0003_g00m00.jsonl`, UTC):

- `{"t": "2026-11-02T08:15:01.476077+00:00", "zeny": 8, "inventory_counts": {"909": 1, "1201": 1}}` (state_tick: logged in HOLDING the 909 Chrysalis from leg 65)
- `08:15:03.481618 TalkToNpc` -> `08:15:08.173276 NpcShopSellOpen` (the C7 sell list answered) -> `08:15:10.175028 NpcShopSell` (the C9 sell request, x=(173,129) the prt_in dealer cell)
- `{"t": "2026-11-02T08:16:02.971954+00:00", "zeny": 11, "inventory_counts": {}}` — the Chrysalis gone, +3 zeny; the DB readback keeps 1201 equip=2 (worn knife) only.

**Leg-65 defect (2) — s00's loot range: DID NOT RECUR; drops surfaced, the walk-toward fired, and the pickups CONVERGED into inventory.** Verbatim taps (/tmp/population_leg66.log): `loot-debug: floor item surfaced (nameid=511 cell=(265,189) amount=1 fid=345)` -> `loot-debug: pickup dispatched (fid=345 nameid=511 cell=(265,189))`; `loot-debug: move toward floor item (fid=346 nameid=905 cell=(266,188) target=(266,188) reauth=0)` -> `loot-debug: mechanical pickup dispatched (fid=347 nameid=906 cell=(264,189))` -> `loot-debug: pickup dispatched (fid=347 ...)`. YuffieFy81's state_tick inventory series grew `{"1201": 1}` (08:15) -> `{"511": 1, "905": 1, "906": 1, "1201": 1}` (08:23) -> `{"511": 2, "905": 3, "906": 1, "1201": 1}` (08:47 onward) — six items banked plus +4/+3 exp from the same kills. Three `pickup deferred (threat) (fid=... nearest=1..3)` lines show the loot-safety gate deferring exactly as designed.

**The repeat, second instance:** xXLunasongXx authored the whole chain on THIS leg's own loot: `08:54:55 TalkToNpc` -> `08:55:01 NpcShopSellOpen` -> `08:55:03 NpcShopSell` at the dealer (172,129), zeny 3->6, the 909 it had picked up mid-window gone from inventory.

Observations for the next slice (none acceptance-failing; NO FIX SLICES ran this leg — pure observation window): (1) YuffieFy81 farms and loots but NEVER sells — it ended on pay_fild04 with 6 carried items, 0 zeny, 188 decides: the sell trip never engaged for the solo field agent (every sell so far started from a prt_in login); (2) prt_fild08 909 drops fid 350/351/352 at (143,364)/(134,367)/(134,368) surfaced but never dispatched — the g00 field agents' loot arms did not converge on them (the per-item one-attempt memo is the suspect); (3) NyxSong parked at the dealer interior the whole window after its sale (102 decides, no return to the field).

Receipt `run/plain_host_receipts/population-receipt-66-1793606810.json` (210 samples, step_errors 0): decides 102/158/151/132/134/149/188; npc_stage non-null only on the two dealer visitors (NyxSong 'unsupported_shop'/'blocked', xXLunasongXx 'opening'/'unsupported_shop'/'blocked' — the deal lifecycle); `shop_offer` never sampled non-null (offer lifetime < the 30s sample cadence — the zeny moves are the sell verdict, per the field-lifetime vs sample-cadence law). Schedule `run/reviews/population-live-schedule-leg66.json` (16bc22f3) verified disk==HEAD pre-launch: bare persona mapping, day 0, 9.25-10.5.

## Leg 67 window (Mon 2026-11-02 11:45-13:00 Madrid / 10:45-12:00 UTC) — THE FIELD-TO-TOWN ARC: THREE FIELD-SIDE SELL TRIPS LANDED (11->14, 31->41, 42->45); THE EQUIP HOP WAS ALREADY CLOSED; s00'S TRIP IS TRIPLE-GATED OFF

**VERDICT: THE LOOP REPEATED AGAIN WITH THE FIELD-TO-TOWN ARC AS THE NEW SHAPE — three agents each picked up loot ON prt_fild08, walked the field->town->interior route, and sold at the Weapon Dealer; s00's field-side trip is structurally gated off (stock set + zeny floor + route table all lack pay_fild04); the "zeny_wing equip hop" premise was stale (knife already worn equip=2 pre-launch).** Launched 11:35:49 CET (receipt epoch 1793615749), duration 6000s; the 11:45 window opened on the dot (CLOCK: (0, 11.58) pre-open with SCHED all-False, logins fired 11:45:02-11:45:23 staggered); 7/7 online (MAX simultaneous = 7); clean logoff at the 13:00 close; DONE at t=6000: steps 23,884, errors 0. ZERO TRANSPORT DOWN, zero Traceback. Seed verified delivered 7/7: every persona's first state_tick read zeny 11/31/100/42/6/7/0 — exactly the refreshed seed (d3916505).

**Acceptance, all DB-backed against the 11:25 pre-launch readback:** >0 new pickups (4 dispatched fids; RinceNyan gained 909+512, PipinWalker and NyxSong each a 909 — all five items sold same-window) AND >0 new zeny gains (NyxSong 11->14, RinceNyan 31->41, PipinWalker 42->45); kill exp +1..+2 base on the three sellers; no TRANSPORT DOWN; 7/7 online.

**THE FIELD-TO-TOWN ARC x3 (verbatim trace rows, UTC):** PipinWalker `10:48:53/54 ItemDrop 909+713 (193,354)` -> `TalkToNpc 11:04:48` -> `NpcShopSellOpen 11:04:53` -> `NpcShopSell 11:04:55` at (172,129), zeny 42->45. RinceNyan `11:06:50/52 ItemDrop 909+512 (128,347)` -> `TalkToNpc 11:24:08` -> `NpcShopSellOpen 11:24:13` -> `NpcShopSell 11:24:15` at (173,130), zeny 31->41 (+10, both items). NyxSong `11:11:14/15 ItemDrop 909+512 (161,356)` -> `TalkToNpc 11:26:56` -> `NpcShopSellOpen 11:27:01` -> `NpcShopSell 11:27:03` at (173,129), zeny 11->14.

**Target (2) zeny_wing's equip hop: ALREADY CLOSED BEFORE LAUNCH.** The fresh pre-launch char row reads `300002 zeny_wing 10 10 38 34 100 prontera 150 143` with inventory `zeny_wing 300002 1201 1 2` — equip=2 (worn) — and never regressed (post-window row identical). The brief's "knife in bag equip=0 since leg 59" premise was stale: leg 65's pre-launch readback already recorded "7x 1201 equip=2". Nothing waited on an equip arm this window. Side observation: zeny_wing parked at its save cell (150,142) all window — 110 decides, 46 actions in the first 27 min, move_gates `no_position_or_dead: 356`, exp/zeny flat — a town-side engagement gap, not an equip one.

**Target (1) s00's field-side sell trip: HELD — triple-gated OFF (verbatim, tree + traces).** (1) Stock set: `src/robots/app/scripts.py:230` `SELLABLE_ITEM_IDS = (705, 713, 909, 914, 915, 917, 938, 949, 1002)` — the comment at :355 pins it to "the prt_fild08 field species"; s00's bag is 511 Green Herb x2 + 905 Stem x3 + 906 Pointed Scale x1 (pay_fild04 species, iro-db) -> `has_stock = any(str(item) in sellables for item in state.inventory)` (:375) is False all window (state_tick inventory_counts frozen at `{"511": 2, "905": 3, "906": 1, "1201": 1}`). (2) `MERCHANT_ZENY_MIN = 50` (:290) vs zeny 0 -> `affordable` False; `if not (affordable or has_stock): return None` — the drive never armed: zero TalkToNpc, zero npc_stage samples, zero no_route gates for s00 (it never tried to route anywhere). (3) `MERCHANT_ROUTE` keys = {prt_fild08, prontera, prt_in} (:297) — "Unknown maps are absent: the drive never engages there (fail-closed)" — `MERCHANT_ROUTE.get("pay_fild04")` is None even with stock; `TRAVEL_ROUTES` (:75) likewise has no pay_fild04 entry, so no pay_fild04->dealer route exists at all. This window s00 also killed nothing (exp frozen 28/16; 6 Attacks, 0 connects; parked (209,177) from 11:47 UTC) — but the hold is structural: its 6 leg-66 bag items are invisible to the sell arm regardless.

**Target (3) un-dispatched prt_fild08 drops: NOT a surface latch — the DISPATCH chain's silent exits ate the pair-mates.** 6 unique fids surfaced (358-363; fid 363 surfaced TWICE — once per agent view: NyxSong's and xXLunasongXx's — the once-per-presence memo working as built); 4 dispatched (358/360/361/362). The two un-dispatched are pair-mates of dispatched drops (each kill dropped TWO items ~1.2s apart): fid 359 (713 (195,352), PipinWalker's 10:48 kill) and fid 363 (512 (163,356), the 11:11 kill). `_loot_mechanical` (playing_runtime.py) returns/continues UNTAPPED at :2083 (`if any(isinstance(action, (Attack, Loot)) for action in actions): return None`), :2100 (`if item.floor_item_id in self._loot_pickup_tried: continue`), and `_loot_walk_mint` :2117 (the `_loot_move_minted` memo) — zero 'move toward', zero 'pickup deferred (threat)', zero 'mechanical pickup dispatched' taps name which exit ate 359/363. The far-agent half: xXLunasongXx surfaced the SAME 362/363 from (158,367) ~10 cells away (trace rows carry x_event/y_event per fe963891) and authored Loot x11 — each enters the :2083 skip and goes out RAW out-of-range (the server refuses silently, no reply frame — the RANGE LAW), zero taps: 11 dead attempts while the drops lived. Contrast proof the machinery works unopposed: RinceNyan's pair BOTH dispatched ~1.5s apart (11:06:50/52) before any drive armed; in kills 1 and 3 the FIRST pickup flipped has_stock=True and the sell drive consumed the window before the pair-mate's attempt.

**Observations (none acceptance-failing):** all three sellers ended parked AT the dealer cells (last_map prt_in 172-173,128-130) — the after-sale return leg (MERCHANT_ROUTE_RETURN exists, :314) did not run for them, leg-66 observation (3) recurring x3; PoringMuffin14 field presence with 700 resting gates, 0 exp; zeny_wing's no_position_or_dead 356 (above).

Receipt `run/plain_host_receipts/population-receipt-67-1793615749.json` (200 samples, steps 23,884, step_errors 0, MAX online 7): decides 106/118/110/110/125/142/128 (s00's receipt count 128 == its trace decide_response count, cross-checked); npc_stage non-null only on the three dealer visitors (opening/unsupported_shop/blocked — the deal lifecycle); move_gates await_pending ~908-1442, no_route_direct 8-179, no_position_or_dead 356 (zeny_wing only), target_unwalkable_rerolled 1 (xXLunasongXx); attack_gates pending_walk 59-597, resting 270-700. Schedule `run/reviews/population-live-schedule-leg67.json` (2303c16b) verified disk==HEAD pre-launch: bare persona mapping, day 0, 11.75-13.0; seed-zeny refreshed from the fresh pre-launch char readback and committed (d3916505). NO FIX SLICES ran — pure observation window.

**Next slice (named):** (a) the s00 stock/route set — re-derive pay_fild04's sellables from its pinned mob_db drops into BOTH sets (the drive's `sellables` AND `SELLABLE_ITEM_IDS`) and add the pay_fild04->prontera legs to MERCHANT_ROUTE/TRAVEL_ROUTES from the pinned warp files; (b) the loot pair-mate taps — tap EVERY silent exit of `_loot_mechanical`/`_loot_walk_mint` and route the decider's Loot through the shared mechanical dispatcher instead of raw sends; (c) the after-sale return leg — all three sellers parked at the dealer at close.

## Slice: s00's sell-trip gate + the loot dispatch taps (branch feat/s00-route-and-dispatch-exits, no runner leg)

**THE leg-67 NAMED FIXES (a)+(b) LANDED OFFLINE.** Worktree /tmp/wt-s00-route off 9e538f6c; TDD: 8 RED in tests/test_s00_sell_trip_route.py + 7 RED in tests/test_loot_priority.py before any fix, GREEN after; full gate `nix develop -c task --dir . check` green (6774 passed + 65 subtests, 7:18); packetdb/spikes untouched.

**(a) The s00 triple gate — route + stock.** `MERCHANT_ROUTE` gains `"pay_fild04": (17, 165)` (the payf002 warp, npc/pre-re/warps/fields/payon_fild.txt:30) and `"moc_fild01": (239, 382)` (mocf006, fields/morroc_fild.txt:24 — lands ON prt_fild08, joining the leg-67-proven field->prontera->prt_in dealer arc). pay_fild04's OTHER pinned exit (payon_fild.txt:31 -> moc_fild02) leads into the desert chain, not the dealer map set — ONE exit cited, so the resolver resolves it unconditionally. Travel network carries the same chain: `TRAVEL_ROUTES["pay_fild04"]` (5 legs to the dealer cell), `EXIT_CELLS["pay_fild04"]`, `ONWARD["pay_fild04"]` (travel_routing.py); brain._goal_script now hands a pay_fild04 farming goal the GrindScript WITH the resolver/merchant wiring (RED before: bare GrindScript, no merchant step — the drive could never arm from the field). Stock sets: BOTH `SELLABLE_ITEM_IDS` and the drive's `sellables` carry the derived pay_fild04 drops (spawn file payon.txt:63-70 -> served mob_db.yml Drops, image verified identical to the repo tree -> pre-re item dbs): herbs 509/510/511, Apple 512, Grape 514, Candy 529, juices 531/619/620, scrolls 694/695/700, Old_Blue_Box 603, Branch_Of_Dead_Tree 604, Leaf_Of_Yggdrasil 610, Emperium 714, jewels 720/722, dyestuffs/wings/cloth, looted dagger/rod 1207/1602, garments, Poring_Hat 5035, 8 cards, Blade_Lost_In_Darkness 7023. **EXCLUDED: Knife_ 1202** — a NOVICE_WANTED_WEAPONS member the setup phase WEARS; a worn weapon stays in received inventory, so inside the set it would read has_stock=True on every equipped Novice and false-arm the sell arm forever (the leg-40 release pin test_wanted_weapon_in_inventory_releases caught this in the first GREEN run and is unchanged). **The zeny-floor decision (receipt gate 2): NO behavior change** — `merchant_drive_cell`'s `if not (affordable or has_stock): return None` already admits the sell arm on stock at zeny 0 (the trip EARNS the zeny); `MERCHANT_ZENY_MIN = 50` exists ONLY as the BUY arm's travel-cost guard. The floor docstring now states the split; test_sell_arm_admits_on_stock_regardless_of_zeny + test_zeny_floor_still_governs_the_buy_arm pin it so the floor can never grow back into the sell arm.

**(b) The silent dispatch exits — every early return of the loot dispatch now has a NAME (tap-before-fix; zero behavior change).** The leg-67 pair-mate exits that ran untapped log WARNING lines, all once-per-item-per-presence (the `_refresh_loot_memo` intersection; a reused aid re-taps — a real new drop): `loot-debug: pickup deferred (authored-action) (fid=… kinds=…)` (the authored Attack/Loot stand-down, :2083 — kinds names the owner, the decider's out-of-range Loot reads kinds=Loot); `loot-debug: loot unavailable (tracker-missing|agent-not-alive)` (the tracker/alive gate on BOTH paths, once per reason, re-armed by a healthy tick); `loot-debug: walk suppressed (reauth pending) (fid=…)` (the `_loot_walk_mint` move-memo hold, :2117); `loot-debug: pickup suppressed (already tried) (fid=…)` (the once-per-presence pickup memo's continue, :2100 AND the send seam's twin — one shared memo, one line per item per presence whichever path hits). The send seam (`_loot`) also now fires the EXISTING `loot-debug: pickup deferred (threat)` tap — its twin threat return was silent while the mechanical path tapped (the fifth-arm law: a tap set watching one path goes quiet exactly when the break moves to the twin). Next leg reads these directly: a surfaced line + a suppressed line names which gate ate the drop. Receipt item (b)'s second half — routing the decider's Loot through the shared mechanical dispatcher instead of raw sends — stays OPEN deliberately: taps first, fix after the log names the eater. Receipt item (c) (the after-sale return leg) untouched — not this slice's scope.

## Leg 68 (Mon 2026-11-02 14:45-16:00 CET) — THE S00 SELL-TRIP READOUT with the pay_fild04 route legs (df421bbf)

Receipt `run/plain_host_receipts/population-receipt-68-1793625923.json`; seed refreshed pre-launch from a fresh char-table readback (2dbaeee9: NyxSong 14z, RinceNyan 41z, zeny_wing 100z, PipinWalker 45z, xXLunasongXx 6z, PoringMuffin14 7z, YuffieFy81 0z). 7/7 online, 0 TRANSPORT DOWN, steps 25030, errors 0, rx_error/dispatch_errors all zero, 210 samples.

**THE LOOP REPEATS — acceptance met on the town group.** >0 new pickups AND >0 new zeny gains vs baseline, all DB-verified: RinceNyan 41->83 (+42; sold 512x1 + 938x1 — both gone from inventory), PipinWalker 45->48 (+3; sold 909x1), PoringMuffin14 7->12 (+5; sold 705x1). 5 `loot-debug: pickup dispatched` taps (fid 364-367, nameids 705/512/909/938); NyxSong +4/+5 exp and xXLunasongXx +4/+2 exp = kills feeding the loop. PoringMuffin14 ran the FULL autonomous arc on same-window loot: prt_fild08 pickup -> prontera -> prt_in -> TalkToNpc 14:20:05 -> NpcShopSellOpen 14:20:10 -> NpcShopSell 14:20:12 -> zeny 7->12. One timing note for future legs: its client tick read zeny=12 at 14:20:59 while the DB still read 7 at ~14:24 — the DB credit landed by the 14:39 read; treat the DB as the authority and expect the credit visibility to lag the client tick, not the reverse.

**THE LEG-68 QUESTION ANSWERS NO: s00 (YuffieFy81) never sold — zeny 0 unchanged, stock intact (511x2/905x3/906x1).** The gates, verbatim from the receipt/log:
- It never reached a trip: `move_gates` sum `{'await_pending': 605, 'no_route_direct': 10, 'target_unwalkable_rerolled': 1, 'rerolled_target_dead': 3, 'target_unwalkable_escalated': 2, 'escalated_target_dead': 731}` — it walked itself into a pocket at pay_fild04 (226,317) by 14:31 UTC and stood there 88 minutes to the close; the sealed-pocket escalator fired (2 `target_unwalkable_escalated`) and EVERY far target was server-refused (731 `escalated_target_dead`). The route legs (payf002/mocf006) exist in knowledge but s00 never walked them — the pocket ate the leg.
- It never fought: `attack_gates` None (never authored an Attack), exp 28/16 unchanged, zero kills, and ZERO `loot-debug: floor item surfaced` taps with a pay_fild04 cell (all 16 surfaced taps are the town group's prt_fild08 drops). `MonsterSpotted` x35 world events with all-`None` `next_action` across its 183 decides — nothing ever minted an Attack.
- The sell arm never engaged: `npc_stage` None and `shop_offer` None in ALL 210 samples; ZERO merchant-drive/sell-arm evaluation lines in the whole runner log — **the sell arm's admission is an UNTAPPED silent gate**. All three leg-67 named gates are now clear (stock set derived, floor buy-arm-only, route legs landed), yet the arm still never fired: the leg-39 trigger-reachability law applies — audit whether the drive's sell arm is ever EVALUATED for a field-side agent before re-reading its gate logic.

**The dispatch taps worked; every exit that fired was NAMED** — `loot-debug: loot unavailable (agent-not-alive)` x1, `loot-debug: pickup suppressed (already tried) (fid=367)` x1, zero silent exits in the tapped dispatch head. ONE untapped path found: s00 executed 23 bare `Loot` actions (script layer, no fid payload, no floor view, no tap) — Loot authoring OUTSIDE the tapped dispatch head; zero pickups landed from them.

**NEXT SLICES (named, in order):** (1) TAP the sell-arm admission — a named-term verdict line per evaluation (tap-before-fix; its silence this leg is why s00's non-engagement is inferred from absence). (2) s00's pay_fild04 (226,317) pocket — offline probe the merged-cache walkability around that cell vs the server's refusals; the escalator's radius-12 candidates were all server-dead, which reads as a broad dead band, not a single wall. (3) Name the script-layer Loot author (23 executed Loots, no taps) and wire it into the tapped dispatcher. (4) Why a mob-rich field never minted an Attack for s00 (MonsterSpotted x35, next_action all None, attack_gates None) — without kills the field-side loop has no fresh loot, though the carried stock alone should have fired the trip.
\n
## Slice: the sell-arm admission taps + the (226,317) pocket diagnosis (branch feat/sell-arm-admission-tap, no runner leg)

**LEG-68 NEXT-SLICE (1)+(2) LANDED OFFLINE: the admission's refusals name themselves, and the pocket is DIAGNOSED — pinned by the leg-39 deadlock latch, NOT reroll exhaustion; the client grid around the pocket is OPEN, the server is the refusing side.** Worktree /tmp/wt-sell-arm-tap off 45271d0d; TDD: 14 RED in tests/test_merchant_admission_taps.py + 4 RED in tests/test_walk_release_taps.py before any tap, GREEN after; pre-lint clean (black/ruff/mypy/xenon B).

**(1) The sell-arm admission taps (tap-before-fix; zero behavior change).** `merchant_admission_refusal(state)` (scripts.py) decomposes `merchant_drive_cell`'s silent `return None` gates into named terms — `not_novice`, `inventory_unknown`, `no_stock_below_zeny_floor` (the combined gate; its detail names which sub-fact failed: `has_stock=`/`affordable=`), `weapon_release`, `map_not_on_merchant_route` — and `_merchant_step` taps `merchant_route_unresolved` when the drive admitted but the resolver names no usable leg on this map (the blind engage used to fall through untapped; behavior exact — the same MoveTo still goes out). Tap channel: `logger.warning("merchant-drive: sell arm %s (%s)")` in the runner log (the loot-debug law), change-only per bot via `_MERCHANT_DRIVE_TAPPED`: the FIRST evaluation of a presence ALWAYS logs (this is the leg-68 instrument gap — zero lines could not tell "evaluated and refused" from "never evaluated"; now any evaluation logs at least once), then only term changes. A whole window of steady-state refusals logs bounded lines. The admit line names `dest=` so the armed trip is provable too. s00's live shape pinned: 511x2 carried at zeny 0 on pay_fild04 ADMITS (`(17,165)`) — the stock term is presence-based and 511 is in both sets; note 905/906 are NOT in the sets (their invisibility is moot for admission since 511 carries), and the next leg's log will name whether the drive is ever REACHED for s00.

**(2) The (226,317) pocket: walkable cell, dead band to the south, server-refused walks, latch-pinned.** Offline probe of the merged cache (`rathena/db/map_cache.dat` + `db/pre-re/`, the exact runtime load): pay_fild04 (226,317) IS walkable and NOT unwalkable-adjacent like the leg-37 (204,165) cell — radius-2 census 15/25 walkable, radius-12 357/625; client routes EXIST from it (shortest_path to the payf002 engage cell (17,165) len=295; to (250,340) len=41). The dead band is REAL but LOCAL: two of the six GrindScript roam offsets — (0,8)->(226,325) and (5,5)->(231,322) — land unwalkable with NO radius-2 alternative (nearest_walkable None); the other four roam targets are walkable with radius-2 alts. So the leg-68 gate sums decode as: the ~1/3 dead-band share of the roam re-authors drove the escalate path, and after `target_unwalkable_escalated` x2 (whose escape walks the tracked position NEVER advanced — the server refused them) the leg-39 per-position latch `(pay_fild04,(226,317)) in _deadlock_cells` short-circuits EVERY later dead-band target straight to `escalated_target_dead` (x731 = the 2-of-6 share at the roam cadence over 88min) without re-deriving radius-12 for that target. **PINNED, not rerolled: the reroll did not exhaust and `rerolled_target_dead` (x3) is NOT the loop.** The half the existing `_move_reroll` correctly handles is the dead-band targets; the half it CANNOT release is the walkable-target subset — their walks are sent (no NoRoute), the server refuses them, and the refusal went SILENT through `_await_pending`'s 1s no-progress release (w57). That silent release is now tapped: `walk_released_no_progress(origin)` with the walk class — `step`/`direct`/`rerolled`/`escalated` — tagged at each send site (`_pending_origin`, class-attribute default so `__init__` gains no statements; the deque note rides the existing receipt lift unchanged). Next leg reads the counts BY ORIGIN: a `(step)`-dominated storm with client-side routes open = the server cannot path FROM the saved cell (the 204,165 class, server-side) and the fix direction is the reposition/teleport seam, not more client rerolls; a `(direct)`/`(escalated)`-only storm would instead name the escape walks as the eaten class.

Full gate `nix develop -c task --dir . check` green before commit (7xxx passed + 65 subtests; see the commit for the exact counts). packetdb/spikes untouched — no packet-table growth. Next slices (named): (a) read s00's first `merchant-drive:` line off the next window log — if the line is absent while script steps advance, the drive is never REACHED for s00's goal path and the next tap goes on the script-selection seam; (b) the pocket: decide the server-side reposition seam off the `walk_released_no_progress` origin split; (c) the script-layer bare Loot author (leg-68 item 3) and the attack-mint question (item 4) remain open.

## Leg 69 — the named-admission readout (Mon 2026-11-02 17:45-19:00 Madrid, day 0; taps 92ba3081; launched 17:31 CET, receipt epoch 1793637073)

The leg-68 taps answered the leg-69 question. The sell-arm admission tap fired for FIVE agents and named every other arm's refusal. s00 verbatim: `merchant-drive: sell arm admitted (map=pay_fild04 dest=(17, 165) zeny=0 stock=2)` — the arm RAN and ADMITTED (stock=2 satisfies the combined gate over the zeny floor; the pay_fild04 route leg resolves dest (17,165)). The town arms named themselves: 4x `no_stock_below_zeny_floor` (NyxSong 14z, PipinWalker 48z, xXLunasongXx 6z, PoringMuffin14 12z at first eval), 2x `weapon_release` (RinceNyan 83z, zeny_wing 100z — the BUY-side hold naming itself), and 3x `inventory_unknown` at prt_in carrying WIRE zeny (41 / 87 / 17 — zeny reaches the wire only on a transaction, so these lines are sell receipts).

THE LOOP REPEATED (observation acceptance >0 pickups AND >0 zeny gains: MET). 3 DB-verified sells — NyxSong 14->17, RinceNyan 83->87, xXLunasongXx 6->41 (+35 for the fid=368 nameid=938 pickup) — each behind a full trip in the window traces (TalkToNpc 1 -> NpcShopSellOpen 1 -> NpcShopSell 1). 4x `loot-debug: pickup dispatched` (938, 909, 705) and PoringMuffin14 holds a NEW 705 at close. Kills on five agents (DB exp +1..+6; zeny_wing and s00 zero). steps 25042, errors 0, TRANSPORT DOWN 0, 7/7 online 17:45:44 -> 19:00 close. `POPULATION-RUNNER[69] DONE: steps 25042, errors 0, receipt run/plain_host_receipts/population-receipt-69-1793637073.json`.

s00 VERDICT: pocket RELEASED, trip ADMITTED, sell NEVER HAPPENED — and the gate is the WALK, not admission and not the dealer: zero TalkToNpc and npc_stage empty all window. s00 left the sealed cell (226,317 -> live 213,325; DB logout 213,325 != save 206,175, a live logout save) and patrolled a ~20x10 band for the window: 2120 MoveTos with receipt gates `escalated_target_dead x944`, `walk_released_no_progress(step) x204`, `no_route_direct x54`, `walk_released_no_progress(direct) x53`, `target_unwalkable_escalated x2`, `walk_released_no_progress(escalated) x1`. The escalation FIRED LIVE for the first time (x2, one escalated release) yet the band still ate 944 honest-stop verdicts — the leg-68 open item (bind the escalation per position; the honest stop loops) now has its first live numbers. s00 also never attacks or loots (attack_gates empty, 0 Loot executed; `loot-debug: pickup deferred (threat) (fid=371 nearest=1)` — threat deferral with zero combat engagement behind it).

Next slices (named; observation law — re-check before fixing). (a) s00's band: the escalator fires but cannot path OUT — decide the server-side reposition/teleport seam (leg-68 item b) off the origin split, now with live counts. (b) The sell MINT at the dealer: an agent arrives ADMITTED with stock and never mints TalkToNpc (PoringMuffin14 stood at the dealer cells 26 min unsold, npc_stage empty — the arrival-without-sell-mint shape, one leg after its leg-68 sell fired). (c) Zero-combat grind: s00 2120 and zeny_wing 2173 MoveTos with ZERO Attack authored (zeny_wing exp frozen at 38) — the leg-68 attack-mint question now has two live instances.

## Slice: the server-reposition seam (branch feat/server-reposition-seam, no runner leg)

**LEG-69 NEXT-SLICE (a) LANDED OFFLINE: the latched escalated-dead verdict now RELEASES a bounded server-reposition direct send instead of dead-ending silently — the pocketed agent can WALK OUT.** Worktree /tmp/wt-server-reposition cut from f626bcac; TDD: 4 RED in tests/test_server_reposition_seam.py before any seam code (every test failing on the missing `ESCALATED_DEAD_DIRECT_BOUND` — feature absent, not a typo), GREEN after; the leg-39 pinned test reconciled at its own site (the latch pin KEPT — the same position still never re-escalates — its tail extended to pin the handoff: after the dead-verdict bound the nearest client-side walkable cell goes out as a direct send).

**What fires when (the seam as landed, `playing_runtime._escalated_dead_release`):** the leg-39 latch (`_deadlock_cells`, once-per-position radius-12 escalation) is unchanged; when a verdict lands on the latch, the verdict hands to the seam instead of the old silent stop. Per position: `ESCALATED_DEAD_DIRECT_BOUND = 3` consecutive `escalated_target_dead` verdicts stay silent (the honest stop holds for the bound), then the runtime picks `nearest_walkable` around the OWN cell (radius 12, own cell excluded — the escalation's search is target-anchored, the seam's is agent-anchored: walk OUT, not toward the dead target) and sends the walk DIRECTLY at it — leg-28 `no_route_direct` semantics, the server path-finds its own side (the proven mechanism: it walked s00 226,317 -> 213,325 on exactly such sends). Paced on the same pending lifecycle, pending origin `repositioned` (the leg-68 release tap names it free: `walk_released_no_progress(repositioned)`), gate note `server_reposition_direct` so the receipt reads which cells needed it. `ESCALATED_DEAD_REPOSITIONS = 3` caps the sends per position; beyond the cap the verdict is an honest `escalated_target_dead` stop again (no spin on a truly sealed pocket — pinned: an own-anchored search that finds nothing also stops honestly). A server-confirmed position advance re-arms BOTH budgets at the fresh position (the walk-out loop: each confirmed step forward re-latches normally and re-earns its bound + cap). Class-attribute shadow idiom (`_escalated_dead_count` / `_escalated_dead_pos` / `_reposition_sends`) — no `__init__` statements.

Leg-69 decode: the x944 `escalated_target_dead` at (213,325) become at most 3 silent verdicts + a paced reposition send, repeating as the server moves the char — bounded per position, unbounded only through real progress. Pre-lint clean (black/ruff/mypy 357 files/xenon B); scoped suites green (tests/test_playing_runtime.py + test_walk_release_taps.py + test_server_reposition_seam.py, 117 passed); packetdb/spikes untouched — no packet-table growth. Full gate `nix develop -c task --dir . check` green before commit (see the commit for exact counts).

Remaining (named, unchanged order): (b) the dealer sell-MINT — an agent arrives ADMITTED with stock and never mints TalkToNpc (the seam restores the mobility that gate needs; the mint gate itself is untouched); (c) the zero-combat grind (s00/zeny_wing author zero Attacks — the spawn-knowledge seed may need the pay_fild04 dense cluster).

## Leg 70 — the server-reposition readout (Mon 2026-11-02 20:15-21:30 Madrid, day 0; fix under test b76f7d19; launched 20:06:04 CET, receipt epoch 1793646383; seed 896d27fb)

`POPULATION-RUNNER[70] DONE: steps 25072, errors 0, receipt run/plain_host_receipts/population-receipt-70-1793646383.json`. steps 25072, step_errors 0, TRANSPORT DOWN 0 the whole leg, 7/7 online 20:15:07 -> 21:30 close (all seven logged in at their baseline cells; s00 at the released 213,325). One transient `agent pop_0003_g00m01: action MoveTo failed: native keepalive send failed; transport release required` — RinceNyan recovered on the next samples (decides climbing to 109), no transport death.

**THE SEAM VERDICT: `server_reposition_direct` x0 AND `escalated_target_dead` x0 in s00's move_gates census — the seam (b76f7d19) NEVER FIRED because its trigger NEVER FORMED.** Leg 69's latch storm (x944 `escalated_target_dead`) did not recur: the per-launch `_deadlock_cells` started empty, and this window no position ever latched — the server accepted s00's walks everywhere it roamed. The pocket question is CLOSED: the leg-69 release held, (213,325) is not sealed, the agent roams the y=315-325 band freely (213,325 -> 188,315 -> 217,325 across the window). The fix under test was VACUOUS this window — the failure class it targets did not occur (intermittent-defect rule: leg 69's x944 was a per-window cadence artifact of the FarmScript dead-band roam targets, not a permanent pocket). A landed fix's named counter read ZERO in its first leg: per the trigger-reachability law the audit target is WHEN the escalated-dead latch can ever form again (it needs the radius-2-reroll-dead verdict chain — i.e. the FarmScript dead-band targets — not the far-route/no-route-direct path that dominated this window).

**THE LEG-70 QUESTION ANSWERS NO: s00 (YuffieFy81) never sold — zeny 0 unchanged, exp 28/16 unchanged, stock intact (511x2/905x3/906x1), zero TalkToNpc, npc_stage/shop_offer empty all window.** But the trip RAN this time, and the failure moved past admission: `merchant-drive: sell arm admitted (map=pay_fild04 dest=(17, 165) zeny=0 stock=2)` (the leg-69 verbatim line, again at ~20:15:2x), then 57 far `MoveTo(17,165)` rows 20:15:22->20:17:54 with the position advancing on server-accepted steps (213,325 -> 188,315, ~1 cell per 2.3s send — the 2s re-send of the same far target restarts the server walk each time), then **the drive's far authoring STOPPED at (188,315) and never resumed** — zero further merchant-drive lines for s00 through close, while the TOWN arms kept re-arming (admitted x3 across the log). The IdleTownScript jitter (goal flipped grind->social at 20:16:58) took over: 271 consecutive 1-cell patrol moves drifted s00 back east to the pocket corner by close. s00 census verbatim: `await_pending 567, no_route_direct 191, walk_released_no_progress(direct) 185, walk_released_no_progress(step) 585, server_reposition_direct 0, escalated_target_dead 0`.

**THE LOOP REPEATS — acceptance MET (observation window, no fix slices).** 3 DB-verified sells, full chains in the traces at the prt_in dealer npc 110001762: zeny_wing 100->103 (TalkToNpc 19:32:04 -> NpcShopSellOpen -> NpcShopSell sales [[3,1]]), PoringMuffin14 12->17, xXLunasongXx 41->47 (20:21:56 TalkToNpc -> NpcShopSell sales [[3,1],[4,1]] — a sell trip that completed AFTER the mid-window census). Pickup: RinceNyan holds a NEW 935x1 in the DB; `loot-debug: floor item surfaced` + `pickup dispatched` taps fired from the window's first minutes (nameids 909/938); kills on four agents (NyxSong +3 base, zeny_wing +2, xXLunasongXx +4/+3, RinceNyan +1).

**NEXT SLICES (named, in order):** (a) The sell drive's ONE-AT-BAT ON AN INCOMPLETE TRIP: admitted once, walked 25 cells, then the arm went permanently silent (zero evaluations after 20:17:54 — the admission-tap law says a gate BEFORE the verdict line, but here no line at all means the arm stopped being REACHED; the trip-in-progress case has no re-arm). Re-arm cadence must cover an armed-but-unfinished trip, and the route walk should pace per-segment (intermediate waypoints) instead of re-sending one far MoveTo against the pending lifecycle (185 `walk_released_no_progress(direct)`). (b) The goal-script interleave: IdleTownScript's 1-cell patrol (700+ jitter moves, 271 consecutive after the flip) authors alongside an armed trip walk and both fight for the wire — a trip in progress should hold the goal script's moves, or the goal flip away from a selling state should release the trip cleanly. (c) Unchanged from leg 69: the dealer sell-MINT for arrived agents and the zero-combat grind (s00 authored zero Attacks again; its exp stayed frozen).

## Slice: the sell-drive re-arm + the goal-script interleave (branch feat/sell-drive-rearm, no runner leg)

**LEG-70 NEXT-SLICE (a)+(b) LANDED OFFLINE: an admitted, incomplete sell trip now re-arms EVERY tick under any goal script, so the leg-70 mid-route stop can never recur; farming interleaves unchanged.** Worktree /tmp/wt-sell-rearm off 8477d851; TDD: 3 RED in tests/test_sell_drive_rearm.py (the flip orphaning reproduced offline: post-flip step authored IdleTownScript jitter MoveTo(213,326) instead of the trip's MoveTo(17,165)) before any fix, GREEN after; 2 companion tests pinned green pre-fix (the off-route terminal refusal stays fail-closed; the farm engage resumes on the sold-out drive). Full gate `nix develop -c task --dir . check` green (6802 passed + 65 subtests, coverage 95.38%, 8:41).

**The defect, proven from the leg-70 traces:** the drive lives INSIDE `FarmScript`/`GrindScript.step` only. s00's trip ADMITTED (the verbatim line) and walked 213,325->188,315 on accepted sends (57 far MoveTo rows 20:15:22->20:17:54 local); the heartbeat goal review flipped grind->social at 19:16:58 UTC, `_goal_script` replaced the drive-bearing script with IdleTownScript, and the drive was never REACHED again — 425 IdleTownScript jitter steps to close, zero merchant-drive evaluations after 19:17:54 local, no TalkToNpc, no sell, zeny 0. The trace also shows the interleaved GrindScript steps 19:17:17-19:17:49 (a MonsterSpotted re-arm) — the last drive authoring before the flip's replacement took hold at the 19:17:57 review.

**The re-arm as landed (`EventDrivenBrain._sell_drive_rearm` + the gate in `_step_goal_script`):** the want-driven dealer trip is evaluated at the BRAIN level every tick, ahead of whichever goal script is active, with the SAME resolver/reachable wiring the farm scripts receive. It has NO state of its own: an admitted, INCOMPLETE trip (sellable stock still held) keeps authoring its route walk under any goal script until (a) the trip COMPLETES — the stock sells, `has_stock` clears, the admission turns off (`no_stock_below_zeny_floor`), the goal script resumes — or (b) the admission names a refusal, terminal for the trip when the fact is structural (`not_novice`, `map_not_on_merchant_route`) and self-releasing when transient (`inventory_unknown`, the weapon hold) — either way None hands the tick back to the goal script. No latch, no trip record: the want IS the state, recomputed per tick (the window-29 design, extended past the goal flip). `_merchant_step` keeps owning the engage, the talk latch, the bound-offer hold and the return leg, so a social-goal agent at the dealer completes the SAME exchange chain, and the leg-66/67 "sellers parked at the dealer" shape now walks the return leg under any goal. `script_for`/IdleTownScript are untouched; the farm scripts' internal `_merchant_step` calls stay (standalone use + defense in depth) — for farm/grind goals the outcome is byte-identical, the brain gate just evaluates first.

**The interleave:** with the gate ahead of the script step, a trip in progress HOLDS the goal script's moves (leg-70 item (b): IdleTownScript's 271 consecutive jitter moves can no longer fight the trip walk for the wire), and a sold-out drive never starves farming — the refusal returns None and the farm/grind engage/roam applies exactly as before (pinned both ways). Telemetry stays honest: the sampled script_step row names the re-arm author `MerchantDrive` (`_trace_script_step` gained the `script_name` override), so a trip walk can never read as the idle script's jitter again (the leg-70 readout used exactly that row). The widen-streak sync moved into `_sync_widen_streak` unchanged (xenon statement budget on `_step_goal_script`).

Remaining (named, unchanged order): the per-segment route pacing (185 `walk_released_no_progress(direct)` — the far MoveTo re-send is unchanged drive behavior, now merely uninterrupted), the dealer sell-MINT for arrived agents (leg-69 item b), and the zero-combat grind (s00/zeny_wing author zero Attacks).

## Leg 71 (2026-11-03 00:48 CET close) — the sell-drive re-arm (c9fbea6d) live verdict: RE-ARM PROVEN, s00 completion fails on ROUTE LENGTH

Window Mon 23:15-00:30 Madrid (day 0 + the post-midnight fragment), seed b6b39967
(NyxSong 17z, RinceNyan 87z, zeny_wing 103z, PipinWalker 48z, xXLunasongXx 47z,
PoringMuffin14 17z, YuffieFy81 0z on pay_fild04 217,325 holding 511x2/905x3/906x1).
SCHEDULE FIX AT LAUNCH (017f5f3f): the committed single fragment `[0, 23.25, 24.5]`
NEVER WRAPS — `Schedule.is_online` takes the `start <= end` simple branch, so the
window would have closed silently at local midnight and cut the readout span in
half. The correct runner-format encoding is BOTH day fragments in one persona list:
`[[0, 23.25, 24.0], [1, 0.0, 0.5]]`. Proven live: all seven stayed online=1 through
the 00:00 day flip; the flip caused no stall.

THE FIX UNDER TEST IS PROVEN: the admitted incomplete trip re-arms EVERY TICK under
any goal script, for the WHOLE window. s00's MerchantDrive authored 327 script_step
rows, first `22:15:22 ACTIVE ['MoveTo']`, last `23:29:55 ACTIVE ['MoveTo']` (5s
before close), zero authoring gaps — the leg-70 mid-route stop shape did not recur.
xXLunasongXx ran the same shape (MerchantDrive n=222, 22:51:10→23:29:55). Four
agents ran MerchantDrive this window (leg 70: effectively one arm, one admission).

The loop REPEATED vs baseline: 3 DB-verified sells (NyxSong 17→22, PipinWalker
48→51, PoringMuffin14 17→20), exp gains on 4 agents (kills), one new pickup
(xXLunasongXx +512x1 equip=0), steps 24599, step_errors 0, TRANSPORT DOWN 0, 7/7
online all window. PipinWalker's drive COMPLETED (the fix's completion half):
MerchantDrive's last row IS the talk — `23:07:43 ACTIVE ['TalkToNpc']` →
NpcShopSellOpen 23:07:48 → NpcShopSell 23:07:50 → NpcClose x4 — a full
admit→walk→talk→sell trip under the re-arm.

ACCEPTANCE: YuffieFy81 zeny = 0 (FAILS on completion, NOT on re-arm). The trip
walked pay_fild04 217,325→(32,175) in 41 min on accepted sends, took the WEST edge
warp into moc_fild01 (22:57), toured it SW, warped into prt_fild08 NORTH edge
(23:15, at (233,29)), and was walking south along x=233 at ~12 cells/min toward the
town warp (170,378) when the close cut it at (233,203) — ~180 cells short. THE TRIP
IS NOW TOO LONG, NOT UNAUTHORED: from a deep pay_fild04 spawn the pinned route is a
3-field odyssey a 75-min window cannot cover. Frontier (a): pin the CORRECT
pay_fild04→town exit (the (17,165) west edge leads to moc_fild01, not town) or route
the odyssey knowingly with the walk budget for it, and pace far route legs faster
than ~1 cell per re-send.

Frontier (b) — the arrival→talk gate, named by a counter-example inside the same
window: xXLunasongXx crossed prt_fild08→prontera→prt_in and from ~23:05 UTC parked
at (173-174,128-130) — Chebyshev 2 from the dealer cell (172,129, held all window by
the stationary zeny_wing) — authoring MoveTo every tick and NEVER TalkToNpc (npc
rows: []). PipinWalker sold FROM (173,129), Chebyshev 1; PoringMuffin14 from
(173,130), also adjacent. The talk fires at dealer-adjacency and (174,128)/(173,128)
never qualified. Measure the talk's true acceptance radius once against the live
dealer (the loot range law) and gate the arrival test with it, or re-roll the
parking cell among the dealer-adjacent set when the dest cell is occupied.

Also named (minor): s00 authored 13 Loot actions with zero DB inventory gain — the
pickups fired but nothing landed; read the pickup-dispatch taps before touching loot
code. Receipt: run/plain_host_receipts/population-receipt-71-1793657128.json.
Next slice: the route-coverage/talk-radius pair above; observation cadence complete,
fix slices unblocked.

## Slice: the dealer approach cell (branch feat/dealer-approach-cell, no runner leg)

**LEG-71 FRONTIER (b) LANDED OFFLINE: the sell drive's walk-to-dealer now closes the last
cells — the approach cell (the dealer's neighbouring cell nearest the agent, the proven
`_approach_cell` intercept from the attack scripts) — and TalkToNpc still fires ONLY at
dealer-adjacency (Chebyshev <= 1), so the range-2 silent park can never recur.** Worktree
/tmp/wt-talk-radius off ad3f3850; TDD: 4 RED in tests/test_dealer_approach_cell.py before any
fix — the parked-at-2 leg-71 shape reproduced exactly (agent (174,128), dealer received at
the cited (172,130), drive authored MoveTo(172,130), the shop's own held cell) — then GREEN,
plus two companion pins (the adjacency-gated talk PipinWalker proved live; the field warp
legs keep the warp cell, since a neighbouring cell never fires a warp). Full gate
`nix develop -c task --dir . check` green before commit.

**The defect, from the receipt's verbatim lines:** xXLunasongXx crossed prt_fild08 ->
prontera -> prt_in and from ~23:05 UTC parked at (173-174,128-130) — Chebyshev 2 from the
dealer cell — authoring MoveTo every tick and NEVER TalkToNpc (npc rows: []), while
PipinWalker sold FROM (173,129) and PoringMuffin14 from (173,130), both adjacent. The
drive's walk-to-dealer targeted the DEALER'S OWN cell; that cell is held by the shop npc,
so the server stopped the walk 2 cells out, `_dealer_talk`'s agent-range gate then refused
every talk, and the drive re-authored the same doomed MoveTo forever — silent at range 2.

**The fix as landed (`_merchant_engage` + `_dealer_talk` in src/robots/app/scripts.py):**
on the prt_in interior leg the outbound walk targets `_approach_cell(dest, state)` — the
deterministic nearest neighbour of the cited dealer cell — which is enterable, so the walk
COMPLETES and lands the agent inside the talk ring (every leg-71 park cell converges in one
approach: (174,128)->(173,129), Chebyshev 1). The tap-before-fix: when a dealer npc IS
received at the cited cell but the talk cannot fire, `_tap_dealer_range` emits
`merchant-drive: sell arm dealer_talk_out_of_range (agent=(..) dealer=(..) chebyshev=N)` —
its own DETAIL-keyed memo (the shared per-term memo would flip-flop with the per-tick
`admitted` line and log every tick), so a steady park logs ONE bounded line and a real
change of position re-names itself; if the defect still fires, the log names the distance.
One incidental correction the drive legitimately needs: `_approach_cell`'s sentinel
initial best (`(99, 99, ...)`) silently returned `(tx+1, ty)` unexamined for targets more
than 99 cells away — unreachable for melee approaches (mobs in view are <= ~14 cells) but
wrong for the drive's far approach; the init is now a real first-candidate seed with a
drift-guard return. Old-contract pins reconciled, not deleted: the three
`MoveTo(172,130)`-cell asserts in test_merchant_drive.py, the two dealer-leg cells in
test_merchant_route_reachability.py — each now pins its approach cell with a comment
naming the new behavior; the pinned route table itself is unchanged (prt_in still cites
the dealer cell (172,130) — the approach cell is derived from it per tick).

**SECONDARY (frontier a, NOT fixed here — coordinator decision after the next leg):**
s00's completion still fails on ROUTE LENGTH: from a deep pay_fild04 spawn the pinned
route is a 3-field odyssey (pay_fild04 -> moc_fild01 -> prt_fild08 -> prontera -> prt_in)
a 75-min window cannot cover — the trip needs route coverage (the correct pay_fild04 ->
town exit; the (17,165) west edge leads into moc_fild01, not town), or a knowingly-routed
odyssey with the walk budget for it (paced faster than ~1 cell per re-send), or a
persisted in-progress trip that survives the window close. Named in the leg-71 receipt;
untouched on this branch.

## 2026-11-08 leg 72 — runner killed 06:37:45; the talk-radius fix SOLD live anyway

Launch 06:06 (schedule `[6, 6.5, 7.75]` = 06:30–07:45 Madrid; weekday 6 verified). The
runner was SILENTLY KILLED at 06:37:45 (t=1892 s, 7m45s into the window): log frozen
mid-sample, NO traceback, NO receipt, no OOM in the kernel log, e2e world healthy
throughout. Killer unnamed — not a Python exception; a signal from outside the process.

TWO defects named by the incident:

1. THE SHEPHERD PATTERN BROKE: the T3 shepherd child COMPLETED ITS TURN at ~06:06,
   right after posting the launch update — its planned 07:00 timer and the whole
   readout never ran; the runner outlived it as an orphan until the 06:37:45 kill.
   LESSON: a shepherd must STAY ALIVE polling to completion inside its turn (sleep
   loops in tool calls), never schedule a timer and exit; and the runner itself must
   launch DETACHED (systemd-run --user) so no agent process tree can carry it down.

2. THE 06:37:45 SILENT KILL is a new, unnamed killer class (nothing in dmesg/journal,
   mid-window, log frozen). Leg 73 launches under systemd-run --user — if it dies the
   same way, the unit journal names the signal.

PARTIAL EVIDENCE (the window's 7m45s, all DB-grounded): xXLunasongXx zeny 47→54 (+7)
at prt_in (173,129) — Chebyshev 1 off the dealer cell (172,130). The dealer
approach-cell fix (50e8a283, merged e9f507c7) walked the APPROACH CELL, talked, and
SOLD — the exact leg-71 failure shape (parked Chebyshev 2, MoveTo every tick, npc rows
[]) is GONE live. 4 bounded dealer_talk_out_of_range details early (transient approach
ticks, detail-keyed memo, no spam), 1 pickup dispatched (fid=382 nameid=909), 0
TRANSPORT DOWN at the cut. A separate transport death at window open
(NativeTelemetryUnavailableError: native keepalive send failed, ~06:31) recovered via
relogin — distinct from the runner kill; watch it in leg 73.

VERDICT: leg 72 INVALID for the full readout (no receipt), but the talk-radius
mechanism is LIVE-PROVEN by the DB zeny delta. Leg 73 re-runs for the complete
verdict + sustain + the s00 odyssey. Positions moved: NyxSong prontera (158,223);
PipinWalker prontera (157,222); PoringMuffin14 prontera (153,156); RinceNyan
prt_fild08 (213,351); s00 pay_fild08 (231,308) still walking, 0z; xXLunasongXx
prt_in (173,129) at 54z.

## 2026-11-08 leg 73 — full window survived detached; zeny flat; THE DEALER CONGESTION DEADLOCK named

Launch 08:51 under `systemd-run --user --unit=leg73-runner` (detached per the leg-72
lesson); the shepherd stayed alive polling to completion inside its turn. The full
6000 s survived: clean DONE 10:31, steps 23898, errors 0, receipt
run/plain_host_receipts/population-receipt-73-1794124259.json; the unit journal
carries the whole lifecycle (a future killer NAMES itself — leg 72's gap closed).
Window [6, 9.0, 10.25]: all 7 online 09:00–10:15, clean open and close, decides
99–153/agent (857 total), full cadence, 0 TRANSPORT DOWN all leg.

VERDICTS:

(a) TALK-RADIUS SUSTAIN: NOT PROVEN. xXLunasongXx never returned to the dealer —
   goal locked on farm_item (94 goal_reviews), stood prt_fild08 (179,370) resting
   (10 Rest actions, attack gates resting:5); 0 TalkToNpc / NpcShopSellOpen /
   NpcShopSell events ALL leg; zeny 54 unchanged. Leg 72's 7-minute +7z mechanism
   proof stands; the full-window farm→return→sell arc did not re-fire.

(b) ECONOMY SUSTAIN: NOT CLOSED — zeny 22/87/103/51/54/20/0 = exactly the seed
   baseline, 0 delta all seven (DB ground truth). The loot leg DID close live:
   59 attacks, 12 Loots dispatched, 3 pickups DB-verified (NyxSong +909 Jellopy,
   PipinWalker +512 Carrot, PoringMuffin14 +705 Clover).

(c) s00 ODEYSSEY: the WALK closed — YuffieFy81 pay_fild08 (231,308) crossed maps to
   prt_in (169,127), standing by the dealer at close (DB last_map prt_in) — but 0z
   stands: parked Chebyshev 3, never talked, inventory unchanged
   (511x2 / 905x3 / 906x1 + knife).

(d) SIGNATURES: the leg-72 transport-death-at-open did NOT recur (0 TRANSPORT DOWN
   all leg); the leg-72 silent kill did NOT recur (full 6000 s detached, journal
   clean).

NEW DEFECT — THE DEALER CONGESTION DEADLOCK: five agents (NyxSong, RinceNyan,
PipinWalker, PoringMuffin14, s00) entered prt_in and parked Chebyshev 2–4 off the
dealer (172,130) for the window's last ~60 min on cells (169,127–129 / 170,128 /
171,128); each tapped dealer_talk_out_of_range at the door (168,128) and at its
best cell — 10 detail-keyed taps total (168,128 x5 / 170,128 / 169,127 / 169,128 /
171,128 / 169,129); move gate rerolled_target_dead: 8 on each; NO agent ever
reached Chebyshev ≤1; receipt npc_stage/shop_offer null for ALL agents all leg.
The leg-72 proof ran alone; five agents on one dealer block each other's approach
cells. Single-agent mechanism proven; the multi-agent sell arm needs approach-cell
allocation or sell-arm queueing. ALSO: xXLunasongXx's sell arm never re-entered
(goal stayed farm_item) — re-entering the sell arm after a sell, when restocked
loot exists, is the unwired leg of the sustain arc.

BONUS: first social actions live in traces — FoundGuild x2, GuildInvite x12,
InviteToParty x4; chat 101 chat_sent + 60 Say + 41 PartyChat.

Code base: 24283f9d (no code change this leg). Commit: receipt + this entry.

## 2026-11-08 leg 74 prep — dealer approach allocation from local perception

Leg-73 evidence: `run/plain_host_receipts/population-receipt-73-1794124259.json`,
`.work/runtime/population-live/traces/` (08:00–09:15 UTC), and
`/tmp/population_leg73.log:709–802`. The log contains exactly 10 detail-keyed
`dealer_talk_out_of_range` taps: five at the door (168,128), then one each at
(170,128), (169,127), (169,128), (171,128), (169,129). Five sellers parked
Chebyshev 2–4 from (172,130), `rerolled_target_dead: 8` per agent, zero shop
offers and zero zeny delta. Leg 72's solo sale from (173,129) remains the
single-agent proof; this change has no new live-run evidence.

`scripts.py` now filters the dealer's eight neighbouring cells using only
located OTHER `player` actors in the handed-in `state.nearby` (bots use the
player kind), plus received body cells in `state.occupied_cells`. It keeps the
original deterministic ordering: Chebyshev distance, squared Euclidean distance,
then `x * 1000 + y`. Positionless players and non-player rows in `nearby` do
not reserve cells. A free candidate is skipped only when
the existing injected reachability authority explicitly returns False; absent
or unknown authority keeps the original choice. No grid is read in scripts.
The original geometric ordering remains the melee intercept, without dealer
occupancy filtering; field/town warp targets and adjacent dealer talk are unchanged.

When no eligible neighbour remains, the sell arm stays ACTIVE with no actions.
It re-evaluates the received occupancy every tick and resumes walking as soon
as a cell becomes available. A separate per-bot diagnostic memo bounds
`sell arm hold dealer_occupied (free=…/8 occupied=…/8 reachable=0/8 …)` independently
of the admission/range tap memos, so steady admission cannot make it log every
tick. This memo records diagnostics only; allocation never reads another
agent's state or writes a shared reservation. Shared queues/reservations,
walkability logic in scripts, and changes to runtime movement/reroll were rejected.

TDD: nine new cases; RED was 7 failed / 64 passed before implementation, GREEN
was 71 passed across dealer approach, merchant drive, merchant route reachability,
and approach intercept. Coverage includes the next-free tie-break from east and
west, one remaining slot independent of actor ordering, a bounded 20-tick hold,
vacancy → walk → adjacent talk, positionless/non-player exclusions, crowded
adjacent talk, and explicit reachability veto/unknown-authority release.

While tracing perception, found that native `PlayingClient._nearby` projects
NPCs and attackable monsters only, not player actors. The coordinator explicitly
answered the implementation question with option 2: add a separate occupied-cell
perception signal while preserving the type-0 classification contract. The
additive `BotState.occupied_cells` tuple is now built by
`PlayingClient._occupied_cells` and passed through `build_native_state` to the
script picker. It contains at most the nearest 64 unique type-0 body cells,
ordered by Chebyshev distance, squared Euclidean distance, then coordinates.
Self AID and its negated/disguised alias are excluded. PC-sprite mobs/NPCs may
also occupy these cells: this is conservative body perception, never an identity
claim. `_nearby` and `test_unproven_actor_is_not_player_or_monster` stay unchanged.
No packetdb edits, new packet ids, or SHA-pin changes were needed; existing
registered actor frames and tracker movement/vanish/map-reset handling supply
the signal. Runtime movement/reroll is unchanged.

Native wiring TDD: RED was 9 failed / 4 classification cases passed before the
new field/projection. Native tests cover type filtering, unchanged identity refusal, self/alias
exclusion, nearest-64 truncation with duplicate body cells, native frames → full
dealer hold → received move/vanish → freed-cell MoveTo, and map-change expiry.
No required native seam remains unwired. Simultaneously approaching agents do
not reserve future cells, and bodies beyond the nearest-64 cap are omitted;
allocation re-evaluates the next received view. A live leg is still needed to
establish that this closes the leg-73 congestion shape.

Gate setup needed the rAthena submodule initialized at the pinned e985006171d2
revision and its ignored `config.log` symlink. The supplied canonical iRO Wiki
database path was a self-referential symlink, so the gate uses the existing
database at `/home/otto/dev/wt-mobpos/run/knowledge/iro-wiki/iro-wiki.db` locally.
That environment-only symlink override is excluded from this commit.

Final GREEN: `nix develop -c task --dir . check` exited 0 before commit:
**6827 passed, 65 subtests passed, 4 warnings; coverage 95.39%** (85% required),
including all formatting/static gates and the unchanged classification tests.
Gate transcript: `/tmp/dealer-congestion-check-final.log`. No runners or probes
launched, no heavengraph access, no `spikes/` edits, no merge to main.

## 2026-11-08 leg 74 — the allocation fix moved exactly ONE agent to the dealer; the hold path never fired

Launch 11:50 under `systemd-run --user --unit=leg74-runner` (detached; the shepherd
stayed alive polling to completion inside its turn). Clean DONE 13:29 (t=6000, unit
Result=success): steps 22596, step_errors 0, **0 TRANSPORT DOWN** all leg. Receipt
run/plain_host_receipts/population-receipt-74-1794134973.json. Pre-launch gate green:
fresh readback matched seed exactly (zeny 22/87/103/51/54/20/0), staged positions
confirmed, all offline; seed-zeny.json unchanged (no drift fix needed). Window
[6, 12.0, 13.25]: all 7 online 12:00–13:15, clean open and close.

VERDICTS:

(a) DEALER CONGESTION FIX: NOT PROVEN. Exactly ONE sell closed — RinceNyan walked
   170,128 → 172,129 (adjacent) and sold at window open (traces: TalkToNpc 11:00:16Z
   → NpcShopSellOpen 11:00:21Z → NpcShopSell 11:00:23Z; zeny 87→97, DB-verified,
   909 Jellopy gone from inventory). But RinceNyan's approach exercised the OLD
   unobstructed path, not the fix: it was the first mover and met no contention.
   The other four stock holders (NyxSong 171,128 / PipinWalker 170,128 /
   PoringMuffin14 171,128 / zeny_wing 169,128) plus s00 (169,127) parked
   Chebyshev 2–3 for the WHOLE window; `sell arm admitted` fired for all six,
   9 dealer_talk_out_of_range taps (verbatim:
   `merchant-drive: sell arm dealer_talk_out_of_range (agent=(171,128) dealer=(172,130) chebyshev=2)`
   and the same shape for chebyshev 2/3/4 at (169,127)/(170,128)/(168,128)/(169,128)),
   and the `sell arm hold dealer_occupied` tap NEVER fired (0 — the block never
   formed because no second agent ever converged), so the hold→release path the
   fix added was never exercised live. rerolled_target_dead is NOT ~0: the receipt
   move_gates show **8 per parked agent** on all five (note: this gate counter is
   receipt-only — the log greps 0, the mid-window instrument was looking in the
   wrong place).

(b) s00 (YuffieFy81): FAILED — 0z stands. Parked (169,127) all window, 659 decides,
   rerolled_target_dead 8, stock (511x2 / 905x3 / 906x1) still in bag (DB). The
   odyssey-to-sale arc did not close.

(c) xXLunasongXx: NOT TRIGGERED — farmed prt_fild08 (195,329) all window (156
   decides, 90 goal_reviews, 80 plan_authored), acquired no sellable stock, never
   returned; zeny 54. weapon_release had already freed it pre-window (zeny 54 ≥
   floor 50, affordable, stock 0) but the weapon purchase did not happen either.

(d) NEW SIGNATURES:
   1. The approach allocation still loses to dead targets: rerolled_target_dead 8x
      per parked agent despite the 4dcebb2c allocation. The allocator picks
      next-free cells from agent OCCUPANCY only; the 2026-10-20 precedent (roam
      targets dying in shortest_path on unwalkable cells) suggests shop-interior
      counter tiles around the dealer are agent-free but UNWALKABLE, and the
      reroll fires each time the approach re-targets one. RinceNyan only succeeded
      from a cell (172,129) it reached by the plain goal walk.
   2. RinceNyan npc_stage latched 'blocked' AFTER its successful sale
      (`sell arm inventory_unknown (map=prt_in zeny=97 ...)`) — the sell-side
      release and the dialogue barrier disagree post-sale.
   3. PlayingBackendError x27 (`real inference request failed (details redacted)`,
      ~1/min from ~12:44 onward, growing to window close); 0 step_errors, the
      runner survived all 27 (heavengraph :8091 health stayed ok), but the decide
      failures degrade the back half of any window.
   4. Sell-arm vs goal-layer tension: admitted stock holders spent the window on
      the decide layer's social choices instead of completing the approach —
      NyxSong founded guild 'NyxSongGuard' (guild_id 2, master NyxSong) with
      GuildInvite x6 + InviteToParty x2, PipinWalker founded 'PipinWalkerGuard'
      (guild_id 3) with GuildInvite x6 + InviteToParty x2; BOTH foundings persisted
      in the DB (char.guild_id set), though no invitee joined a guild.

BONUS — SOCIALS LIVE AND PERSISTING: FoundGuild x2 (DB-persisted guilds 2 and 3),
GuildInvite x12, InviteToParty x4, PartyChat x43, Say x914, chat_sent x957 across
the seven agents; parties 2/3/4 held (char.party_id set: 2 = PipinWalker +
xXLunasongXx + PoringMuffin14, 3 = NyxSong + zeny_wing, 4 = RinceNyan).

Economy ground truth at close: zeny 22/97/103/51/54/20/0 (one +10 delta total;
RinceNyan sold 1 Jellopy batch); zeny_wing holds 705 Clover x1 unsold (its
`sell arm admitted (map=prt_fild08 dest=(170, 378) zeny=103 stock=1)` fired on the
field pickup and it walked home but never converged); knives (1201) are fixture
grants, not purchases.

Code base: 049d8862 (no code change this leg). Commit: receipt + this entry.

## 2026-11-08 leg 75 prep — runtime walkability veto and completed-sale dialogue release

Implementation branch `fix/dealer-convergence-leg75`, based on main `439250fa`.
Evidence: leg-74 receipt
`run/plain_host_receipts/population-receipt-74-1794134973.json`, population traces
under `.work/runtime/population-live/traces/` (11:00–12:15 UTC), and the leg-74
entry above. RinceNyan's DB-verified +10z sale was the unobstructed first mover;
it did not prove contested convergence. Five other stock holders stayed 2–3
cells from `(172,130)`, with receipt-only `rerolled_target_dead=8` each. s00 at
`(169,127)` retained 511x2 / 905x3 / 906x1 and made no sale.

Fix 1: the script's existing `MerchantReachable` veto was available but the
production host supplied only `travel_resolver`, leaving the veto unwired.
`ScheduledAgent._start_brain` now binds the current `PlayingClient` authority
before scripts are constructed. `PlayingClient.merchant_reachable` rejects
individual unwalkable cells using its own `self.cache`, then checks the agent's
route region. The script stays grid-free and still permits unknown geometry.
An occupied walkable neighbour plus seven free counter tiles now produces a
hold for s00, with `free=7/8`, `reachable=0/8`, and `walkable_free=0/8` in the
`dealer_occupied` tap; freeing the walkable cell releases the hold. The veto is
before MoveTo authoring, consistent with the 2026-10-20 blocked-cell precedent.
The melee intercept remains unchanged.

Fix 2: a sent C9 now retains the current dialogue round and received-stream
cursor. A validated successful CB (0x00CB, result 0) after that send completes
the C7/C9 exchange and releases the dialogue view, failed flag, and deny origin,
including an intervening innocent timeout. Sending C9 alone or receiving a
failed CB does not release it. Unsolicited success, replies from older rounds,
newer UI prompts, poison denials, and cancellation uncertainty retain the
fail-closed barrier. Existing timeout-origin retry cadence is unchanged. A new
click/C4/C7 round can mint and send the next sale without replaying the old C7.

TDD RED: **6 failed, 29 passed** before implementation (blocked-cell authority,
production session wiring for both goal scripts, and successful-sale latch).
Focused dealer/route/recovery GREEN: **60 passed**; further completion/barrier
regressions were added for normal success, cancellation, unsolicited success,
and a newer prompt in the same round. Final full gate recorded below.

Defect 3 remains report-only: leg 74 observed a heavengraph decide-latency burst,
`PlayingBackendError` x27 from about 12:44 (~1/min), while the runner survived
and :8091 health stayed OK. No backend code or service changes were made.

Gate environment: initialized the pinned rAthena e985006171d2 submodule and used
the supplied config.log symlink. The canonical wiki DB symlink is still
self-referential; the worktree gate uses the existing
`/home/otto/dev/wt-mobpos/run/knowledge/iro-wiki/iro-wiki.db` fallback already
documented above. This local symlink override is excluded from the commit.
No runners/probes launched, no heavengraph access, no `spikes/` changes, and no
merge. Live leg-75 contention/sales remain to be demonstrated by the coordinator.

Final GREEN before commit: `nix develop -c task --dir . check` exited 0;
**6840 passed, 65 subtests passed, 4 warnings; coverage 95.40%** (85% required).
All formatting and static gates passed. Transcript:
`/tmp/dealer-leg75-check.log`; RED: `/tmp/dealer-leg75-red.log`.

## 2026-11-08 leg 75 — the walkability-veto era sold three live; the last three agents' walks never land; s00 talked at window close

Launch followed the shepherd brief: pre-launch readback matched the seed exactly
(22/97/103/51/54/20/0; stock holders NyxSong 909x1, zeny_wing 705x1, s00
511x2/905x3/906x1, RinceNyan at the dealer row (172,129)), no stale runner, both
heavengraph backends healthy. Runner detached under `leg75-runner`
(systemd-run --user), 6000 s, window [6, 15.0, 16.25], four staggered playing
groups; **23,916 steps, 0 step_errors, all 7 agents online, 0 TRANSPORT DOWN,
0 PlayingBackendError**. Receipt:
`run/plain_host_receipts/population-receipt-75-1794145508.json`.

SALES (three, within 40 s of window open, TalkToNpc -> NpcShopSell -> zeny, all
DB-verified): NyxSong 22 -> 25 (talk 14:00:07 UTC), PoringMuffin14 20 -> 25
(14:00:21), PipinWalker 51 -> 58 (14:00:31). Each emptied its stock on the first
sale and closed its dialogue with clean NpcClose actions; `rerolled_target_dead`
was **0 for all seven agents** — the walkability veto never had to kill a dealer
target, and the hold path (`hold dealer_occupied ... walkable_free=N/8`) never
fired because the block never saturated.

THE REMAINING GAP is a new signature, named "ghost walks": zeny_wing,
xXLunasongXx, and s00 never converged. Each tapped the dealer from chebyshev=2
(**1307 `dealer_talk_out_of_range` events**) while re-authoring MoveTo to the
same south-row cells ((173,131) / (172,131)) every ~2 s — 553+ authored walks
each — without ever arriving. The target cells pass the walkability veto (rtd=0
proves the target check, not the route), so the suspect is NoRoute around the
shop counter between the y=128 row and the y=131 row, or the 2 s re-author
cadence cancelling in-flight walks; receipt move_gates show only tiny
`await_pending` / `walk_released_no_progress(step)` counts (1-4 per agent).
Path-level route validation (not just target-cell walkability) is the next fix.

LATCH: not exercised — every seller emptied its stock on sale one, so no agent
had a second sale opportunity in-window; no blocked re-begin loop appeared and
the sellers' post-sale NpcClose chains ran clean, so nothing contradicts the
release. s00's odyssey-to-sale arc is still open: it walked to (172,129)
(chebyshev=1) by window end and TalkToNpc fired at 16:15:04 Madrid — 26 s before
window close — but the sale did not complete (zeny stayed 0, stock intact in the
DB readback). Decision cadence was healthy (91-148 decides per agent; no
decide-latency bursts).

## 2026-11-08 leg 76 prep — veto path-blocked dealer cells and give approach walks time

Implementation on `t3/fix-merchant-ghost-walk`, based on `main` at `ee112388`.
Leg 75's 1,307 out-of-range taps / repeated south-row targets motivate two
guards; this is unit/gate evidence, not a claim of live arrival or sales.

`PlayingClient.merchant_reachable` now runs the same `shortest_path` primitive
as `_move`, after the cell walkability check. **NoRoute returns False**: a known
path-blocked neighbour must not be authored just because its cell is walkable.
No cache / unknown map still returns None (the existing fail-open contract).
Both successful and rejected paths are memoized per `(map, position, cell)` and
cleared at the next `build_native_state` tick. This replaces the merchant's
region-only verdict; other travel routing and movement recovery are unchanged.

The grid-free script approach memoizes the last authored `(map, cell)` per bot,
including across goal-script recreation. The first evaluation authors; four
evaluations hold ACTIVE without a MoveTo; the fifth elapsed evaluation
re-affirms the same target (authors at 1, 6, 11, ...). Changed targets and other
bots author immediately. Dealer contact, bound offers, route/return transitions,
loss of the merchant drive, a fully vetoed/occupied approach, and the existing
session/test reset clear patience so a fresh approach can start immediately.
This is bounded author patience; scripts do not infer wire progress or arrival.

When every free neighbour is rejected by the authority, s00 holds ACTIVE with
no MoveTo and the existing deduplicated `hold dealer_occupied` detail:
`free=8/8 ... reachable=0/8 walkable_free=0/8`. Here `walkable_free` counts free
neighbours admitted by the combined cell/path authority, not raw grid cells.
Rejected alternatives: fail-open on known NoRoute (would repeat the ghost
target), removing the retry bound (could strand a lost action), and consulting
the grid from scripts. Live leg-76 arrival/sale proof remains for the coordinator.

TDD RED before implementation: **6 failed, 19 passed**; fake walkable geometry
with NoRoute exposed the path veto and s00 hold, positive/negative caching
exposed the missing path calls, and repeated-author tests exposed the cadence.
Focused dealer/route/recovery/rearm GREEN: **101 passed**. Existing actor-order
allocation tests now reset the author memo between independent scenarios;
merchant-drive tests isolate their session memo between tests.

Gate environment: initialized the pinned rAthena submodule and supplied
config.log / iro-db links. The supplied canonical iro-wiki link is still
self-referential; used the existing `wt-mobpos` wiki DB fallback documented in
the previous implementation entry, only for local verification. No database
content was changed. No runners/probes or heavengraph access, no `spikes/`
changes, and no merge.

The additional `task audit` failed on **17 existing vulnerabilities in four
packages** (black, certifi, filelock, opentelemetry-api). `uv.lock`,
`pyproject.toml`, and `Taskfile.yml` are identical to the base; dependency upgrades
were left outside this movement fix. This audit is separate from the full
`task check` gate documented in README.md. Its generated requirements file was
removed after the failed audit.

Final GREEN before commit: `nix --option auto-optimise-store false develop -c
task --dir . check` exited 0; **6847 passed, 65 subtests passed, 4 warnings;
coverage 95.41%** (85% required). All formatting and static gates passed.
Restored the worktree's original iro-wiki symlink after verification; local
gate inputs are excluded from the commit.
Transcripts: `/tmp/ghost-walk-red.log`, `/tmp/ghost-walk-focused.log`,
`/tmp/ghost-walk-check.log`, `/tmp/ghost-walk-audit.log`.

## 2026-11-08 leg 76 — the odyssey-to-sale frontier closed: s00 logged in at the dealer and sold in 26 seconds; the veto-approach sells 4/4 at true adjacency, but the sell-arm taps from a full ring

Window Sunday [6, 18.0, 19.5] = 18:00-19:30 Madrid (90 min). Runner detached under
`systemd-run --user --unit=leg76-runner` 17:47:31-19:48, duration 7200s:
**28,681 steps, step_errors 0, TRANSPORT DOWN 0, PlayingBackendError 0,
walkable_free holds 0.** Receipt
`run/plain_host_receipts/population-receipt-76-1794156469.json`.
Pre-launch DB readback matched the seed exactly (zeny 25/97/103/58/54/25/0;
s00=YuffieFy81 300006 parked dealer-adjacent prt_in 172,129 with 511x2/905x3/906x1
at 0z; zeny_wing 705x1; xXLunasongXx 909x1) — no seed fix needed. All 7 agents
online 178-179/240 samples, decides 104-159 each at heartbeat cadence, clean
logoff at 19:30. heavengraph :8091/:8092 untouched.

**(b) FRONTIER (a) CLOSED — odyssey-to-sale.** s00's first window arc:
18:00:22 TalkToNpc (22 s after window open; leg-75 missed close by 26 s) →
18:00:24 NpcShopSellOpen → 18:00:26 NpcShopSell → 18:00:28 NpcShopBuySelection.
DB ground truth: char 300006 zeny **0 → 113**, staged 511/905/906 all gone from
its inventory. Four sells total, all at true adjacency: zeny_wing 18:00:16
(+5z, 103→108, 705 gone), xXLunasongXx 18:00:24 (+3z, 54→57, 909 gone), s00
18:00:26 (+113z), RinceNyan 18:36:55 (+3z, 97→100, field loot carried back).

**(a) ghost-walk fix verdict: path authority PROVEN, tap-count bar failed.**
4/4 sells executed at real adjacency with zero server-side misfires;
`rerolled_target_dead` 0; s00 authored 0 MoveTo and 0 plan re-authors during its
90-minute dealer hold — the 5-tick walk-author patience holds. But
`dealer_talk_out_of_range` reached **422** (first 3 in the opening minute, burst
from 18:36 as fielders returned; sources cluster on the y=128 row at chebyshev
2-4). These are PRE-SEND vetoes (fail-closed, never wire-sent) — not ghost
walks — but the sell-arm's retry cadence from a blocked cell is unbounded, so
the "tens, not hundreds" bar is not met.

**(c) repeat-sell latch NOT proven:** all four sellers sold exactly once
in-window; no farm→return→sell-twice cycle occurred. The 0x00CB release proof
stays open for a future leg.

**(d) new signatures.** (1) Knife-buy stock-block: 147 shop-debug mint
verdicts, ALL fail-closed on `stock=False` — the dealer's offer (receipt=89)
carries no knife slots, so the zeny→knife purchase hop is structurally blocked
until dealer stock is staged seed-zeny-style. All six chars already hold fixture
knives (2b0f249e), so equipment is satisfied; s00's 113z sits unspent. (2)
Dealer-congestion residue: post-sale agents hold the adjacency ring while
retrying the stock-blocked buy (`npc_stage='blocked'` at close for
g00m01/g00m02/g01m01); arrivals park one row short and tap every ~10 s.
PoringMuffin14 looted a fresh 909 (Jellopy) and queued ~60 min without
converging. Named follow-up: approach-cell allocation/queueing (leg-73 item) +
buy-attempt backoff/give-up.

Socials continued: FoundGuild x2 (one per group leader), GuildInvite x12,
InviteToParty x4, 36 chat emissions across the roster. Leg-76 ran on main as it
stood at 8655e5ff; coordinator commit b461e135 (dashboard compose) landed
mid-leg without touching leg files.

## 2026-11-08 leg 77 prep — bounded buy stock refusals, sell-queue patience, and the corrected knife diagnosis

Base `b7f29351`; evidence is leg 76,
`run/plain_host_receipts/population-receipt-76-1794156469.json` (four sales,
s00 0→113z in 26 seconds), plus its existing offline transcript
`/tmp/population_leg76.log`. No new runner, probe, or live-world access.

The runtime now gives up after **three consecutive stock-blocked buy
evaluations per (map, dealer, item 1201) in a session/window epoch**.
`MerchantBuyBackoff` keeps the counter owner-local; only an offer bound to the
current epoch, NPC, map, and dialogue-open cursor can contribute. A fresh offer
containing Knife clears the missing-offer refusal; a known indexed inventory
also clears the separate inventory-unknown refusal. A new session resets both.
Changed offers that still omit Knife do not pretend the stock block resolved.

The third evaluation emits one truthful `buy give-up no stock in offer` tap,
including `offer_item_ids` truncated to eight IDs. The leg-76 inventory-unknown
shape instead says `buy give-up inventory stock unknown`, never claiming the
dealer lacks Knife. The runtime sends the pinned `CZ_CLOSE_DIALOG` **0x0146**
(`<HI>`, matching `native_npc_dialogue.py`'s close encoder and
`rathena/src/map/clif.cpp:13406`), then clears the received dialogue marker,
invalidates the offer, and completes the local shop controller. A failed send
retains the fail-closed barrier. Later stockless dialogues in the same window
close without another give-up tap. Poison/cancellation/dead-state gates still
own their exchanges; no purchase admission term is relaxed.

The detached `merchant_buy_suspended` verdict prevents the script's BUY-only
trip from immediately re-arming. Fresh sellable inventory still admits the
SELL arm. Existing return legs can move a suspended buyer away even if the
inventory snapshot is unknown or a fixture weapon is already present. Scripts
do not parse offers, count market refusals, or query grids.

A vetoed approach keeps its grid-free patience memo across goal-script
recreation: unchanged perception rechecks on the **fifth elapsed evaluation**
(evaluations 1, 6, 11, ...), holding ACTIVE with no walk or talk in between.
This includes the runtime authority's all-free-cells-unreachable verdict,
preserving `reachable=0/8 walkable_free=0/8`. A changed perceived vacancy,
position, destination, session, or injected authority rechecks immediately.
Contact, a bound offer, route/return transitions, and session reset release
the queue wait. Existing
hold/range tap deduplication and the pre-send adjacency veto remain intact.

**Knife diagnosis: runtime inventory-admission block; neither a C6 item-list
parse bug nor world-side missing dealer stock.** The requested binary verdict
would misstate the available evidence:

- Pinned rAthena `e985006171d2eb320ee512a653f4c83aea3d81b6`,
  `npc/merchants/shops.txt:255`: `Weapon Dealer#prt` at `prt_in,172,130`
  lists **`1201:-1`** among 19 items. This is an ordinary `shop`, not a
  finite-stock market requiring a stock seed.
- `rathena/src/map/clif.cpp:2235` specifies C6's complete 11-byte
  `<price.L discount.L type.B nameid.W>` rows; `clif_buylist` emits every shop
  item. `src/robots/adapters/native_shop.py:122` uses
  `struct.iter_unpack("<IIBH", raw[4:])` over all rows (64-row engineering cap,
  not a prefix slice). `native_shop_context.py:270` copies every decoded item ID
  into `ReceivedShopOffer`; `playing_runtime.py::_buy_mint_attempt` checks these
  rows. Only the diagnostic list in the new tap is truncated.
- C7 is the sellable **inventory-index** list, not dealer item IDs:
  `rathena/src/map/clif.cpp:2265` and
  `src/robots/adapters/native_gameplay.py:742` (`<HII>` rows). It must not be
  interpreted as an offer missing Knife.
- The saved leg-76 transcript line 41 binds **19 C6 rows** at receipt 89
  (213 bytes = 4 + 19×11); line 43 proves
  `f_item=True(1201/1201)` and `row=True((50,50,5) v (50,50) rows=1)`.
  All **147** mint verdicts instead say
  **`stock=False(stock=False slots=None)`**. That `stock` is
  `PurchaseAdmission.stock`, sourced from `tracker.indexed_inventory` in
  `playing_runtime.py::_purchase_snapshot`, not the offer's rows.
- `native_purchase.py:318` refuses unknown player inventory;
  `native_gameplay.py:412` returns None when it is unknown, and
  `native_gameplay.py:671` deliberately invalidates it on 0x00AF/0x07FA
  sell/delete receipts. Reconstructing current inventory after deletions is a
  separate adapter-accounting task; this slice bounds the resulting hold
  without fabricating current stock or reopening purchase authority.

**Coordinator staging change: none.** Do not add a duplicate `1201:-1` or seed
shop stock: Knife is already declared and was received. Rejected: the leg-76
diary's inference that `stock=False` meant missing dealer stock, a false
`WORLD-SIDE MISSING STOCK`/`RUNTIME PARSE BUG` label, inventing bag contents,
fail-open buys/walks, and changing live NPC scripts, SQL, Docker, or `spikes/`.

TDD RED: **9 failed, 5 passed** before implementation
(`/tmp/buy-queue-red.log`). Expanded new-suite GREEN: **16 passed**; final focused
merchant/dealer/route/recovery suite GREEN: **235 passed**.
The first full gate exposed the authority-replacement compatibility case:
**1 failed, 6862 passed + 65 subtests, coverage 95.45%**
(`/tmp/buy-queue-check-first.log`). Including the injected authority in the
wait's context preserves the existing immediate recheck when an authority is
replaced, without weakening patience for a steady authority. No existing test
assertions were changed.
Gate inputs: initialized only the worktree's pinned rAthena checkout and used
the requested config.log / iro-db links. The canonical iro-wiki link points to
itself, so verification uses the existing
`/home/otto/dev/wt-mobpos/run/knowledge/iro-wiki/iro-wiki.db` fallback, as in the
prior implementation entry; the original worktree link is restored afterward.
No corpus contents, live world, heavengraph, runners, probes, or `spikes/` edits.
Final full gate GREEN before commit: `nix --option auto-optimise-store false
develop -c task --dir . check` exited **0**; **6863 passed, 65 subtests passed,
4 warnings, coverage 95.45%** (85% required), in 268.43 seconds. Formatting,
ruff, strict mypy (363 files), vulture, xenon, duplicate-code, and bandit all
passed. Transcript: `/tmp/buy-queue-check.log`. The original iro-wiki symlink
was restored after verification; gate inputs are excluded from the commit.
Committed/pushed on `t3/buy-arm-sell-queue-patience`; no merge.

## 2026-11-08 leg 77 — three sells landed (909 gone, PoringMuffin14 25→28z) but the buy give-up never armed: the post-sale blocked-dialogue freeze held the dealer ring instead

Launch 20:50:12 Madrid under `systemd-run --unit=leg77-runner`, window
`[6, 21.0, 22.5]`, backends heavengraph :8091/:8092 (read-only health probes
only). Pre-launch seed verified against a fresh DB readback: 25/100/108/58/57/
25/113 exact, no seed fix needed. Runner exit 22:50: **28,685 steps,
0 step_errors, 0 TRANSPORT DOWN, 0 PlayingBackendError**; decides 120-191 per
agent at full cadence; positions seeded for all seven; no stale-gate noise.
Receipt: `run/plain_host_receipts/population-receipt-77-1794167425.json`.

**Sells (trace timestamps, DB-verified zeny):** NyxSong 21:00:10 (+35z → 60),
PoringMuffin14 21:00:44 (+3z → 28), s00/YuffieFy81 21:56:50 (+3z → 116).
PoringMuffin14's 909 is GONE from `inventory` (only the 1201 knife remains) —
the queued-seller target converged 44 seconds after window open. Honest caveat:
it logged in already dealer-adjacent (position persisted from leg 76), so this
was not a queue traversal. Each seller sold EXACTLY once — no repeat-sell
latch anywhere in-window.

**(a) BUY GIVE-UP: NOT EXERCISED — 0 `merchant-drive: buy give-up` lines.**
The precondition never armed: `_give_up_stock_blocked_buy` needs a received
offer (`_current_buy_offer()`), and every frozen agent's final sample shows
`shop_offer=None` with `npc_stage="blocked"` — the fail-closed dialogue
barrier sits BEFORE the C6 offer, so the 3-refusal counter never starts.
What did NOT reproduce is leg 76's residue shape: the buy-retry ring storm
(422 pre-send vetoes, ~60 min of hold-the-ring retries) is gone — the sellers
each sent 1 TalkToNpc + 3 NpcClose and sold in seconds.

**THE NEW DOMINANT DEFECT — post-sale blocked-dialogue freeze.** The three
sellers stopped authoring actions 21-56 minutes into the window and stood at
their dealer cells until close: NyxSong last action 21:31:19 Madrid (after
`FoundGuild 'NyxSongGuard'` + 6 GuildInvites @ 21:01:51 — the guild frontier
fired live), PoringMuffin14 last 21:22:13, s00's last action IS its sell
21:56:50. Decides kept flowing at full cadence; `npc_stage=blocked`
(Weapon Dealer 110001762); 1-3 move gates total per agent. Ring cells
therefore stayed occupied ~90 min and the queue starved behind them.

**QUEUE PATIENCE (bounded taps):** RinceNyan queued the whole window at
Chebyshev 2 — 110 `dealer_talk_out_of_range` taps, ~16 s cadence, one agent
(vs 422 in leg 76). Bounded, never converged: no ring cell freed. It farmed
instead (12 Attacks, 2 Loots, carries Clover 705x1 as `stock=1` sell-arm
admission at 22:06) — the farm-while-queued fallback works.

**Soft signature:** zeny_wing went action-silent for the last 52 min standing
in prontera (191 decides, `npc_stage=None`) — the decide→dispatch dead-link
shape, weaker evidence than the three hard freezes.

**(c) REPEAT-SELL LATCH: PASS** — 3 sells, 3 agents, one each; no 0x00CB
release stress appeared.

NEXT: the freeze, not the buy, is the frontier. The give-up's arming
condition must include the BLOCKED-dialogue path (barrier pre-offer), and a
post-sale agent must return to its farm_item goal instead of camping the
ring — the 90-minute dealer occupation is what starved the one genuinely
queued seller. Traces (UTC window): `.work/runtime/population-live/traces/`.

## 2026-11-09 leg 78 — the post-sale freeze is dead: zero blocked npc stages all window, both sellers left the ring, RinceNyan traversed the queue and sold 8 seconds after open; new signature — MerchantDrive travel dest (170,378) is unwalkable and pinned the field-side seller

Launch 06:51:39 Madrid Monday under `systemd-run --user
--unit=leg78-runner`, window `[0, 6.85, 8.35]` = 06:51-08:21 same day (no
midnight crossing), main 1a2d94a7 (post-sale-freeze fix 55efa277 merged).
Backends heavengraph :8091/:8092, health-verified pre-launch, read-only
probes only. Pre-launch seed verified against a fresh DB readback:
60/100/108/58/57/28/116 exact (YuffieFy81=s00 116), no seed fix; RinceNyan
held Clover 705x1 as the queue-traversal target. Runner exit 08:51: **28,681
steps, 0 step_errors, 0 TRANSPORT DOWN, 0 rx/dispatch errors**; decides
309-609 per agent; online 178-179/240 samples for every agent. One transient:
40 PlayingBackendError from heavengraph :8091 in a ~07:08-08:0x Madrid
cluster — all caught by the narrow handler, sessions kept, decides recovered
(backend `/health` ok throughout; no starvation; max action gap stayed
104-196s). Receipt:
`run/plain_host_receipts/population-receipt-78-1794203505.json`.

**(a) POST-SALE FREEZE: FIXED — the leg-77 shape did not recur.** npc_stage
is EMPTY for all seven agents across all 240 receipt samples: zero `blocked`
stages, zero shop_offer=None holds, max blocked+shopNone streak 0. No agent
froze (decides>0 with actions>0 everywhere; no >10 min action gap). Both
sellers LEFT the ring after their sales: RinceNyan was farming prt_fild08
(166,365) 11 minutes post-sale and finished offline at (191,365) on the
field; zeny_wing was walking out of prt_in at close, offline at (162,119),
10+ cells west of the dealer.

**(b) QUEUE TRAVERSAL: PASS — RinceNyan sold through the still-congested
ring 8 seconds after window open.** Chain 06:51:51 TalkToNpc → 06:51:56
NpcShopSellOpen → 06:51:58 NpcShopSell (Madrid; sales [[3,...]]), zeny
100→105 DB-verified, and its inventory was EMPTY at the 07:11 DB check —
the Clover it carried since leg 77 is gone. Leg 77 shape disproved: the
same agent waited the whole window at Chebyshev 2 then; this time the
queue released it. Second traversal: zeny_wing farmed a jellopy (909x1),
traveled prontera→prt_in, sold 08:11:40 Madrid (Talk 08:11:33 → Open
08:11:38 → Sell 08:11:40), +3z → 111 DB-verified, 909 gone. Repeat-sell
latch still clean: one sale per stock item, no double-sell.

**(c) DEATH RECOVERY: NOT EXERCISED** — zero deaths (hp_min 43 zeny_wing,
48 PipinWalker, never 0); the respawn path never armed.

**Farm/combat/socials healthy:** 326 attacks (PipinWalker 316, hp_min 48,
6239 resting gates — real grind with rest discipline), exp grew for all
seven (PipinWalker 168/95 base/job, RinceNyan 172/131); 93-219 chat
actions per agent; RinceNyan farmed a NEW Clover 705x1 after its sale
(present in the final DB readback — the 705-gone evidence is the 07:11
mid-window check, not the final one).

**(d) NEW SIGNATURE — MerchantDrive field-side travel dest unwalkable.**
The sell arm's travel leg for field sellers targets (170,378), a known
UNWALKABLE prt_fild08 cell (the walkability veto covers roam/candidate
cells but not this dest): xXLunasongXx (admitted stock=2 at window open,
dest=(170,378)) re-sent MoveTo(170,378) **1,144 times over the whole
window** from (176,374), never departed the field, never attacked, and
finished with Clover 705x2 unsold. zeny_wing hit the same dest 43x
(07:48-07:54 Madrid) but escaped once its wanderings left the field and
the drive re-targeted on prontera. s00's receipt gates show the machinery
CAN reroll/escalate unwalkable targets (`target_unwalkable_rerolled` /
`_escalated`) — the MerchantDrive travel dest simply does not go through
that veto. NEXT: apply the same walkability veto (reroll to nearest
walkable) to the MerchantDrive travel dest; leg 79 then reads xXLunasongXx's
sell plus the first repeat-sell of freshly farmed stock (RinceNyan already
carries one). Traces (UTC window 05:51-07:21):
`.work/runtime/population-live/traces/pop_0003_*.jsonl` (append-only across
legs — timestamp-filter, never cumulative greps).

## 2026-11-08 leg 78 prep — recover the post-sale dialogue freeze and release the dealer ring

Implementation only, based on main `a99c5846`; branch
`fix/leg78-post-sale-dialogue`. Leg-77 evidence:
`run/plain_host_receipts/population-receipt-77-1794167425.json`,
`.work/runtime/population-live/traces/pop_0003_*.jsonl`, and
`/tmp/population_leg77.log`. No runner/probe, live-world, Docker, heavengraph,
or `spikes/` edits. No merge.

**Evidence correction and limits.** The rows matching the receipt's three
sales and final positions are **20:00–21:30 UTC**, not the supplied
19:00–20:30 UTC window. The trace records authored actions and received UI
stages, not raw outgoing packets. The exchanges below are reconstructed
from those rows and the pinned dispatch/FSM; an `action_executed NpcClose`
is NOT evidence that 0146 was sent. Receipt `wire_sent=0` is also not such
evidence: its sampler counts a test-double-style `wire.sent` list, which
the live wire does not expose.

| Seller | Last NPC exchange and final stage | Why recovery did not recover |
| --- | --- | --- |
| NyxSong / g00m00, prt_in (173,129) | Sold at 20:00:10.074755: C5 type 1 / C7 / C9 / successful CB. Post-sale retries reconstruct 0090 clicks at about 20:00:27, 20:00:43, and 20:01:02.216912. The last C4 was observed at 20:01:04.218318 (UI sequence 152, `unsupported_shop`); deadline expiry made it `blocked`. The later authored close at 20:01:20.253022 was swallowed by the spent-budget retry guard; no 0146. | All three attempts spent after the sale. Farm/grind's bounded dialogue drive subsequently yielded MoveTo actions, but the native barrier filtered them. Chat/guild actions explain the later 20:31:19 last action; movement was already held. |
| PoringMuffin14 / g01m02, prt_in (172,129) | Initial 0090 at 20:00:20.997035 expired unanswered; the first retry was observed `opening` at 20:00:39.670202. C4 arrived 20:00:42.462866, then C5 type 1 / C7 / C9 at 20:00:44.464571 / successful CB. Two post-sale retries used the authored closes at 20:00:58.477380 and 20:01:16.524493. Last C4: 20:01:18.540720, sequence 134, `unsupported_shop` -> timeout `blocked`. The 20:01:34.660054 close was swallowed, not sent. | One retry spent before the sale, two after. Inventory became unknown after deletion, so admission refused, but the UI and return barriers still held. Last chat action at 20:22:13 did not move it. |
| YuffieFy81 / s00, prt_in (173,130) | C4 at 20:56:48.068221; C5 type 1 / C7 / C9 at 20:56:50.073557 / successful CB. No further authored actions. Host-pump retries produced opening/C4 pairs at 20:57:20/23, 20:57:41/43, and 20:58:01/04. Last C4: 20:58:04.959420, sequence 3309, `unsupported_shop` -> timeout `blocked`. | All three post-sale retries ran on the tick seam. The retained social goal uses strict dialogue routing and never authors farm/grind's bounded close. Budget exhaustion therefore held forever without even a close intent. |

All three have the **timeout-origin / exhausted one-session budget** shape,
not a demonstrated malformed poison and not a missing tick seam. No buy C5
or C6 is recorded for these final rounds, so received-offer buy give-up
cannot arm. Three distinct retry schedules and brain routes produced the
same native hold.

**The CB release existed but missed the live map spelling.** The trace sale
intents carry `map_name='prt_in.gat'`; their dialogue carries `prt_in`.
`_consume_sell_result` compared those literals, rejected the otherwise valid
CB, and retained the old UI until it timed out. "No double sell" alone did
not prove that release ran. The offline replay with a real MapCache, raw
`.gat` map receipt, inventory deletion, and CB reproduces the miss; the
same map-normalization authority used elsewhere now qualifies the
comparison. Owner/epoch/NPC/round/prompt/poison/cancel guards remain.

**zeny_wing is a fourth shape, with a diary correction.** Its final trace
and receipt position is **prt_fild08 (186,322)**, not prontera. The last
authored action is MoveTo(186,326) at 20:38:41.975048 after repeated Lunatic
damage (last logged DamageTaken at 20:38:41.173367). Thereafter 191 decides
continue, no NPC UI exists, the pose is None, and goal-script traces stop.
The runtime path that clears an already-established pose to None here is
received SELF vanish/death (0080, reason 1); `_received_death` then returns
an empty outcome before script telemetry. The displayed HP 43 is stale
presentation, not life authority. The retained JSONL does not include the
raw death frame/time, so this is a source-supported reconstruction rather
than a packet capture. `respawn()` already encoded B2 type 0, but no runtime
caller existed: the dead body had no recovery request. This is not a
merchant-drive ownership hold.

**Implementation and fail-closed boundaries.**

- `playing_runtime.py::_consume_sell_result` compares the verified map
  identity and records a released merchant visit only after successful CB.
- `_dispatch_timeout_close` admits a close for an already-denied timeout
  before the retry interceptor. It does not change fresh-expiry dispatch
  timing or the absolute 120-second/page/request budgets. The raw 0146 send
  must succeed before local release; a failed send keeps permanent poison.
- `_retry_timeout_dialogue` is shared by dispatch and tick: three attempts
  per **300-second** epoch, minimum **5 seconds** apart, no catch-up burst.
  An admitted trader can get fresh attempts in later epochs. Live offers,
  cancel uncertainty, and non-timeout denials still prevent re-begin.
- The host pump closes a refused, received, adjacent Weapon Dealer at the
  existing prt_in dealer cell even without authored actions. It reuses
  `_dealer_talk` and `merchant_admission_refusal`; unrelated/absent NPCs,
  admitted business, planner holds, dead/sitting bodies, and pending walks
  do not gain a close. `merchant_returning` records the actual released
  visit, enabling `merchant_return_cell` through unknown inventory or a
  fixture weapon without inventing inventory or suspending a buy. Fresh
  admission still wins, and reaching the field clears the visit marker.
- `_recover_dead_self` sends the existing B2 type 0 only for received dead
  SELF, at most once per **30 seconds**, retaining pose/life barriers until
  received warp/resurrection and SELF standing. Poison/cancel holds survive.
  `agent_runtime.py::_drain_events` applies the host's existing
  `mechanical_fallback_allowed` ownership law, preserving typed planner
  boundary passivity for both new autonomous recovery paths.
- `native_npc_dialogue.py::_expire` cannot overwrite a prior denial with
  timeout. `_send_npc` explicitly records `send_failure` while retaining the
  failed request's existing stage and exact exception. Poison therefore
  cannot age into a retryable timeout.

**Verification.** Initial TDD RED before implementation: **13 failed, 4
passed**, `/tmp/leg78-red.log`. Expanded 29-case suite replayed against an
isolated copy of baseline source: **21 failed, 8 passed**,
`/tmp/leg78-final-suite-red.log`; current new suite GREEN: **29 passed**.
It covers raw/canonical sale completion, expired sale completion, honest
close and send failure, all goal routes, paced horizon renewal, deep-time
poison, queue vacancy through C4/C5/C7/C9/CB convergence, self-death recovery,
and ownership/identity/offer/cancel/pose/walk guards. No existing test
assertions were edited, including malformed-cancel. Focused existing plus
new dealer/recovery/latch/backoff/planner tests: **692 passed**,
`/tmp/leg78-focused-final.log`.

The first full gate caught compatibility regressions (16 failed, 6864 passed
plus 65 subtests): observing before the ordinary retry seam advanced fresh
expiry in the same dispatch, forcing failed requests to `blocked` rewrote
retained request stages, and autonomous respawn violated a typed planner's
passive death boundary. Those were fixed without altering existing test
expectations. An intermediate gate was stopped after the final deadline
compatibility correction; the final gate runs on the completed source.

Gate inputs: only this worktree's pinned rAthena checkout and requested
config/knowledge symlinks. The canonical iro-wiki symlink points to itself;
tests use the existing wt-mobpos iro-wiki fallback as in leg-77 prep, then
restore the requested original link. No corpus contents were edited.
The README's full gate is `nix develop -c task check`; the separately run
`task audit` is outside that gate and reports 17 existing findings in four
unchanged locked packages (black, certifi, filelock, opentelemetry-api),
`/tmp/leg78-audit.log`. Dependency manifests/lockfile remain unchanged.

Rejected: disabling the NPC barrier, reclassifying poison as timeout,
clearing a live offer to make progress, optimistic stock/life/pose,
instant/unbounded re-click loops, a new buy-stock policy before any C6,
rewriting typed planner ownership, treating an authored close as a wire
receipt, world/NPC/SQL/Docker changes, runner/probe validation, and unrelated
dependency upgrades. Unit/gate evidence does not claim a new live sale or
leg-78 population convergence.

Final full gate **GREEN before commit**: `nix --option auto-optimise-store
false develop -c task --dir . check` exited **0**; **6892 passed, 65 subtests
passed, 4 warnings, coverage 95.48%** (85% required), in **256.35 seconds**.
Black, ruff, strict mypy (364 files), vulture, xenon, duplicate-code, and
bandit all passed. Transcript: `/tmp/leg78-check-final.log`. The completed
queue-sale assertions also passed in the final 29-case focused run
(`/tmp/leg78-core-final.log`). The requested iro-wiki link was restored after
verification, and no gate inputs are included in the commit.

## 2026-11-09 leg 79 prep — validate MerchantDrive travel destinations before authoring

Leg-78 evidence: `run/plain_host_receipts/population-receipt-78-1794203505.json`
and the leg-78 diary above report xXLunasongXx admitted with Clover x2 at
window open, then 1,144 authored MoveTo(170,378) actions from prt_fild08
(176,374), with no sale or field departure. The counter approach already
used the runtime path authority; the travel destination bypassed it.

`PlayingClient.merchant_travel_target` now validates each outbound and
return travel cell with `merchant_reachable`, hence the SAME
`shortest_path` no-corner-cutting contract as dealer approaches. A known
unwalkable or path-blocked destination searches `nearest_walkable`'s
radius-2 neighborhood in deterministic order, skipping candidates without
a path from the received position. The runtime memoizes success AND failure
once per (map, original destination), separately per client. Ordinary
native-state ticks and successful movement do not clear that memo. A
memoized replacement is revalidated from the current received position;
failure holds without authoring a MoveTo and logs one destination-naming
tap per key, e.g. `travel dest unwalkable (170,378)`. Walkable but unreachable
destinations are named `unreachable`. Absent geometry retains the existing
no-authority behavior. The script layer only consumes the injected target
or hold; it imports no grid/navigation implementation.

The authority is wired at session start through brain-level MerchantDrive
re-arm, FarmScript, and plan-less GrindScript, including field maps without
a seeded farming travel route. NPC preparation and dealer approach/queue
ownership remain intact. Field/town path failure no longer sends an
outbound seller along the farming resolver's homeward leg. The existing
foreign-interior own-door resolution is retained, and its authored exit is
validated too. Field travel still clears previous dealer approach/queue
memos. Startup no longer paints all route cells walkable: a citation is
not permission to overwrite the client-grid veto.

**Full route audit**, raw common + pre-re client grids from pinned rAthena
`e985006171d2eb320ee512a653f4c83aea3d81b6`, before any ground correction:

| Direction | Map | Original cell | Raw walkable | Final cell | Raw walkable |
| --- | --- | --- | --- | --- | --- |
| outbound | pay_fild04 | (17,165) | yes | (17,165) | yes |
| outbound | moc_fild01 | (239,382) | yes | (239,382) | yes |
| outbound | prt_fild08 | (170,378) | **no** | **(169,377)** | **yes** |
| outbound | prontera | (177,221) | yes | (177,221) | yes |
| outbound | prt_in | (172,130) | yes | (172,130) | yes |
| return | prt_in | (168,124) | yes | (168,124) | yes |
| return | prontera | (156,22) | yes | (156,22) | yes |

No other unwalkable merchant waypoint was found. Corrected the field cell
in MERCHANT_ROUTE and the duplicated TRAVEL_ROUTES/ONWARD knowledge. The
replacement lies inside prtf004's inclusive trigger rectangle
(167..173,376..380), pinned by
`npc/pre-re/warps/fields/prontera_fild.txt:65`; both the field arrival
(170,375) and leg-78 received origin (176,374) have raw-grid paths to it.
The audit regression checks every table entry against the unmodified
public grids; the warp-trigger regression also pins the corrected cell's
reachability and the knowledge-table copy.

**TDD and verification.** Initial RED before implementation: 18 failed,
6 passed (`/tmp/leg79-red.log`). The dealer-memo cleanup regression then
failed before its correction (`/tmp/leg79-latches-red.log`). The final new
suite has 25 cases, including nearest reachable selection, disconnected
nearest candidate, walkable-but-path-blocked destination, memo persistence
through received 0x0087 movement and native-state cache resets, one-time
honest hold, every travel waypoint, absent geometry, client isolation,
foreign interiors, and session-to-brain/script wiring under grind,
farm_item, and social goals. Focused new + existing merchant/dealer/
approach/route/re-arm/admission tests: **136 passed**
(`/tmp/leg79-focused.log`). Existing coordinate expectations were updated
only to the corrected route DATA, retaining their behavior assertions.

Gate inputs use this worktree's pinned local rAthena checkout and requested
config/knowledge links. As in leg-78 prep, the canonical iro-wiki link points
to itself, so verification temporarily uses the existing wt-mobpos corpus
fallback; the requested canonical link is restored afterward. No corpus
contents or gate inputs are committed. The first full gate was deliberately
interrupted for the dealer-memo compatibility regression; the final full
gate runs on the completed source.

Rejected: per-tick neighbor re-rolls; blind re-sends at the dead center;
redirecting field sellers home on path failure; painting route walls
walkable; putting geometry in scripts; changing general movement budgets,
dealer ownership, or admission policy. No runners/probes, live-world,
Docker, or heavengraph access; no spikes/ formatting. This is unit/public-
grid evidence, not a new live sale or leg-79 population claim. The branch
is committed and pushed for review only; no merge or deployment.

Final full gate **GREEN before commit**: `nix --option auto-optimise-store
false develop -c task --dir . check` exited **0**; **6917 passed, 65 subtests
passed, 4 warnings, coverage 95.49%** (85% required), in **263.78 seconds**.
Black, ruff, strict mypy (365 files), vulture, xenon, duplicate-code, and
bandit all passed. Transcript: `/tmp/leg79-check-final.log`. The requested
iro-wiki link was restored after verification. No gate input changes are
included in the commit.

## 2026-11-09 leg 79 — the dead waypoint is gone (0 spams of (170,378)), repeat-sells are now sustained (RinceNyan and s00 sold in consecutive windows), but the field-seller traversal still stalls: 2,191 MoveTo((169,377)) authored from (176,374), zero movement — the travel leg lacks author patience / its perform phase is unnamed

Launch 10:10:32 Madrid Monday under `systemd-run --user --unit=leg79-runner`,
window `[0, 10.25, 11.5]` = 10:15-11:30, main d0559aa3 (travel-dest
walkability merge b3f4bee4). Pre-launch seed verified exact
(60/105/111/58/57/28/116). Runner exit clean ~12:10: **28,685 steps, 0
step_errors, 0 TRANSPORT DOWN, 0 PlayingBackendError** (the leg-78 decide
burst did not recur). Receipt:
`run/plain_host_receipts/population-receipt-79-1794215351.json`.

**(a) TRAVEL-DEST FIX: the data correction holds.** Zero re-sends of the old
unwalkable (170,378) all window; the travel leg now authors the corrected
(169,377) (reachable per the path authority). The leg-78 signature is dead.

**(b) FIELD-SELLER TRAVERSAL: NOT COMPLETED — and the evidence is exact.**
xXLunasongXx (stock 705x2) authored **2,191 MoveTo to (169,377)** on
prt_fild08 across the whole window (~10s cadence, no author patience on the
travel leg) from a frozen (176,374) — seven cells away, walkable and
reachable per the authority — and never moved: no walks landed server-side
or each re-author cancelled the in-flight one (the ghost-walk cancel shape
reborn on a path the 5-tick reaffirm memo does not cover; the receipt's
per-agent gate fields are null so the perform-phase gate is unnamed).
Diagnosis target: travel-leg author patience + perform-phase instrumentation
for the merchant travel MoveTo.

**(c) REPEAT-SELL: SUSTAINED.** RinceNyan sold in consecutive windows
(105->110, its 705 gone) and s00 in consecutive windows (116->120). The
0x00CB release + fresh-farm-and-return cycle now repeats across legs.

**(d) No new signatures**: 0 freezes, 0 blocked stages, 0 deaths; chat and
guild chains continued. Final zeny 60/110/111/58/57/28/120.

Evidence: traces `.work/runtime/population-live/traces/pop_0003_g01m01.jsonl`
(UTC 09:15-10:30: 2,191 MoveTo((169,377)) action_executed rows), DB readback
in-container. The shepherd's turn ended mid-readout; the coordinator parsed
the receipt + traces and wrote this entry.

## 2026-11-09 leg 80 prep — merchant travel author patience and named MoveTo perform outcomes

Implementation only, based on main `7715926c`; branch
`t3/merchant-travel-patience`. Evidence receipt:
`run/plain_host_receipts/population-receipt-79-1794215351.json`, with the
append-only `.work/runtime/population-live/traces/pop_0003_*.jsonl`
filtered to **2026-11-09 09:15–10:30 UTC**. No runner/probe, live-world,
Docker, or heavengraph access; no `spikes/` formatting. Review branch only,
no merge or deployment.

**Differential evidence and corrections.** Line numbers below refer to the
original trace files under `/home/otto/dev/ro-bots`, not copied fixtures.

| Seller / trace | Actual leg-79 travel sequence | Transition / sale evidence |
| --- | --- | --- |
| xXLunasongXx / `pop_0003_g01m01.jsonl` | Lines **173424** (09:15:15.080412) through **176597** (10:30:00.693950): **2,191** authored MoveTo(169,377), all from prt_fild08 **(176,374)**. Line **173425** is the next identical author at 09:15:17.082710. Median interval **2.0068015s**, minimum 2.002298s, maximum 4.862252s. | No map transition or changed received coordinate in this window. No sale. |
| RinceNyan / `pop_0003_g00m01.jsonl` | Lines **160824** (09:15:06.472264), **160825**, **160827**: MoveTo(169,377) from **(191,365)**, then (190,365), then (189,365). **43** travel authors, median interval **2.0071225s**; line **160884** (09:16:32.308016) is from **(171,375)**. | **160885** (09:16:34.502789): prontera (156,26). **161433** (09:30:41.419843): prt_in (168,128). **161454** (09:31:31.032904): NpcShopSell at (172,129). |
| s00 / `pop_0003_s00.jsonl` | Lines **231161** (09:21:12.546709), **231163**: MoveTo(169,377) from **(194,356)**, then **(193,356)**. **48** authors in the completed outbound burst; **231230** (09:22:50.920123) is from **(171,375)**. Ordinary intervals are about 2s. Two later MoveTo(169,377) authors after the return bring the window total to 50. | **231232** (09:22:53.106409): prontera (156,26). **231778** (09:36:58.553018): prt_in (168,128). **231798** (09:37:48.255148): NpcShopSell at (172,129). |

The completed sellers used the SAME corrected destination and essentially
the SAME author cadence. They received advancing positions; xXLunasongXx
did not. The historical entry's “~10s” cadence is not what these rows show:
**~2s** is the old author cadence, **~10s** is the new five-evaluation
cadence at this tick rate. The supplied (180,350)/(174,355) coordinates are
useful differential test origins, but are not the starts of these actual
leg-79 sell bursts. RinceNyan's leg-78 sale began at the dealer after its
prior queue wait (see the leg-78 entry); its completed leg-79 trip above
is the direct same-destination comparison.

**Offline geometry.** The unmodified common + pre-re map caches from
pinned public rAthena `e985006171d2eb320ee512a653f4c83aea3d81b6`
(`/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source/db/`) give an
8-step no-corner-cutting path:
`(176,374) -> (175,374) -> (174,374) -> (173,374) -> (172,374) ->
(171,374) -> (171,375) -> (170,376) -> (169,377)`.
Both endpoints and all path cells are client-walkable. Runtime
`merchant_reachable` agrees. The supplied comparison origins have paths
of **27** and **22** steps respectively; the actual leg-79 burst origins
(191,365)/(194,356) have **23**/**26** steps. A shorter origin-distance
claim cannot explain the freeze.

**Perform diagnosis: occupied one-cell-west rejection.** The supplied
“move_gates are null” premise describes startup samples, not active ones.
The receipt's `samples[13]` (t=390.5s), lines **2184–2207**, reports
xXLunasongXx online, **standing=true**, position (176,374), npc_stage=null,
and **walk_released_no_progress(step): 8**. ALL **227** active samples
have the same standing and eight release notes. `wire_sent=0`/`moves=0`
are list-counter artifacts of this live wire, not absence-of-send proof.
The release notes establish `_move` reached its step-send/pending path
and repeatedly released it. This was neither a standing block nor a
pending slot that never released.

The raw-grid path's FIRST dispatch is **(175,374)**, exactly one cell west
of the frozen origin. Pinned `npc/quests/seals/brisingamen_seal.txt:25`
places **Bard#brising** on that cell; `npc/scripts_athena.conf:218` loads
that NPC. Trace **173418**, 09:15:14.391326, independently receives
`Bard#brising(npc, d=1)`, actor **110005545**, immediately before the first
corrected travel author. The decisive pinned server rule is
`src/map/clif.cpp:11401–11405`, `clif_parse_WalkToXY`: with
`official_cell_stack_limit > 0`, a move exactly **one cell west** is
silently rejected if `map_count_oncell(..., BL_CHAR|BL_NPC, 1)` is nonzero.
The pinned default is **1** (`conf/battle/misc.conf:103`,
`src/map/battle.cpp:8478`). A GAT-walkable NPC cell therefore does not make
this particular one-cell-west command dispatchable. `_move` ignored the
received occupancy and repeatedly chose that same refused first step.
The stall clock correctly released it; static `merchant_reachable` kept
correctly approving the FAR destination, so neither memo could break the
loop. RinceNyan/s00 approached from other cells and did not enter this
exact occupied-west send trap. Author patience alone would only slow it.

`action_executed` still precedes `_perform`, so an individual author row
alone remains insufficient proof of a wire send. There are **zero Arrived
world_event rows for all three sellers** in leg 79: this runtime does not
translate its 0x0087 stream into Arrived events, and raw packets were not
recorded in those JSONL files. Thus the traces cannot independently count
raw walk-end frames. The receipt's repeated no-progress releases and
unchanged position, together with the pinned silent-rejection branch,
explain why no progressing walk landed. The old “each re-author cancels an
in-flight walk” hypothesis is unnecessary for this failure.

**Changes.** Runtime dispatch now detects the exact occupied-west command
from this bot's RECEIVED `nearby` actor coordinates or `occupied_cells`.
When the path's first step hits it, the runtime recomputes the path with
that cell as a received blocker and dispatches its safe first step, naming
**occupied_west_rerouted**. A missing alternative is an explicit
**occupied_west_no_route** refusal: it never falls through to blind direct
sends at the blocked command. Received vanish/movement immediately releases
the detour. No grid tile is rewritten or occupancy inferred from another
bot or a private world. The general move seam enforces the server rule,
including merchant travel; scripts remain grid-free.

The travel leg now shares the grid-free five-evaluation walk
author helper with dealer approaches, using separate per-bot memos. It
authors immediately on a changed map, native epoch, or validated target;
otherwise it holds four evaluations and reaffirms on the fifth. Script
recreation and goal flips retain patience. A vetoed target, departure from
the drive, dealer engagement, and explicit contact reset clear the travel
memo so a fresh trip does not inherit a stale hold. Runtime geometry
validation remains in the injected target authority.

`PlayingClient` now records the actual per-MoveTo result. Every native move
branch returns an explicit result, including direct/reroll/escalation
sends and exhausted refusals. `ScheduledAgent` writes a **move_performed**
sibling AFTER each authored MoveTo, with its params and cached map/x/y:
`outcome=dispatched` with `wire_target` and origin (`step`, `direct`,
`rerolled`, `escalated`, `repositioned`); `standing-blocked` with
`reason=not_standing`; `pending` with `reason=await_pending`; or `refused`
with the actual gate. NPC interception resets any prior dispatch result;
perform exceptions explicitly name `perform_error`. Legacy clients are
honestly `unavailable`, rather than guessed dispatched. Telemetry never
re-observes native state.

The stall clock retains **pending_outcome=pending-cancelled**,
`pending_reason=no_progress(<origin>)`, and the old pending target until
the next MoveTo perform. This also covers a release during event draining
while the patient author holds. Map/epoch changes clear that evidence.
The existing stall algorithm is preserved: a lost walk releases and the
next patient reaffirm dispatches again; a real moving walk with no final
walk-end can likewise progress after its stall-clock release. The
standing barrier remains fail-closed until received SELF standing.

**TDD and verification.** Initial RED: **16 failed** before implementation
(`/tmp/leg80-red.log`). A second RED for the diagnosed occupied-west seam
was **3 failed, 18 passed** (`/tmp/leg80-occupancy-red.log`). The completed
new suite has **21** cases covering
all outbound/return travel legs, context changes, three sellers on raw
public geometry with the received Bard at (175,374), a dropped first walk
then received progress, fail-closed blocked alternatives, NPC vanish,
release during event draining, named standing/pending/dispatch/refusal/stall
telemetry, NPC interception, send failure, and no observing trace read.
Updated compatibility assertions preserve drive ownership and enforce the
new bounded author cadence across goal/script changes. Focused merchant,
dealer, route, travel, re-arm, runtime, trace and post-sale tests: **340
passed** (`/tmp/leg80-focused.log`). Ruff and strict mypy (366 files) passed. The first full gate exposed four
post-sale fixture-isolation failures (new per-bot travel memos persisted
between parametrized cases); its tests now explicitly reset contacts, as
the other merchant fixtures do. No production behavior was changed for
that isolation correction.

The supplied worktree started at an unrelated initial commit; its clean
task branch was moved to the requested local main commit `7715926c` before
implementation. Its rAthena submodule is pinned to the requested revision,
with the requested config/knowledge links. The canonical iro-wiki link
still points to itself, as recorded in leg-79 prep; gate verification uses
the existing wt-mobpos corpus fallback, then restores the requested link.
No corpus, submodule, or gate-input changes are included in the commit.

Rejected: treating startup-null receipt gates as active-window evidence;
inventing a retrospective perform cause from intent-only traces; treating
absence of Arrived rows as absence of raw walk frames;
assuming the successful sellers were closer or authored more patiently;
putting grids in scripts; weakening received standing; changing global
movement timeouts or retry budgets; runners/probes, live-world edits,
Docker, heavengraph, and `spikes/` formatting. These are offline synthetic
contracts plus existing trace evidence, not a new live traversal claim.

**Final full gate GREEN before commit.** The README's documented full gate,
`nix --option auto-optimise-store false develop -c task --dir . check`,
passed on the completed source: **6938 passed, 65 subtests passed, 4
warnings**, **95.49% coverage** (85% required), **253.17 seconds**. Black,
ruff, strict mypy (366 files), vulture, xenon, duplicate-code and bandit
passed. Transcript: `/tmp/leg80-gate-final.log`. It ran as the first half of
`task --dir . check && task --dir . audit`; reaching audit establishes the
check task's successful exit.

The EXTRA dependency audit is **not green**: pip-audit reported **17
findings in 4 packages** already pinned by main's unchanged `uv.lock`:
black 26.10.0 (fix 26.10.1), certifi 2026.7.22 (fix 2026.10.18), filelock
4.0.11 (fix 4.2.1), and opentelemetry-api 1.45.0 (fix 1.45.1). Its failure
made the combined command exit 201 after the full check passed. Rejected
expanding this merchant runtime slice into a dependency upgrade; no audit
ignores or gate weakening were added. The audit temporary export was
removed. The requested canonical iro-wiki symlink was restored before
commit. The source, tests and log entry are committed and pushed for
review only; no merge or deployment.

## 2026-11-09 leg 80 — the occupied-cell fix is proven live (65 sparse named refusals, zero frozen-author spam; s00 ran the complete field→warp→prt_in→dealer→sell chain: TalkToNpc 14:10:59 at chebyshev 1, NpcShopSell 14:11:06, 120→125z DB-verified; two popgen guilds formed) but xXLunasongXx's third traversal died on a NEW blocker: four MerchantDrive agents staging-congested the prontera south-gate tiles for the whole window

Runner: systemd unit `leg80-runner`, launched 14:10:47 Madrid Monday, 7200 s,
DONE at 16:11 with **28,265 steps, 0 errors, 0 TRANSPORT DOWN, 0
PlayingBackendError, 0 tracebacks**. Receipt
`run/plain_host_receipts/population-receipt-80-1794229859.json` (its
`passed` field is None — the runner sets no leg verdict; the verdict below
is the shepherd's). Window [0, 14.5, 16.0] opened on schedule, all seven
agents logged in with the staggered pairs, all logged off cleanly at 16:00.

**(a) OCCUPIED-CELL REROUTE: PASS.** xXLunasongXx left the leg-79 frozen cell
(176,374) within 30 s of window open ((175,373)→(172,373)→warp) — the
2,191-same-cell re-author shape is gone. Refusal telemetry is named and
sparse: **65 refused across ~11.4k authored moves population-wide**
(`occupied_west_no_route` = the explicit no-safe-alternative refusal,
`no_position_or_dead`, `perform_error`), vs 8,123 dispatched / 5,527
pending. The `occupied_*_rerouted` reroute outcome never fired — the field
path this leg never needed it; every named occupation refusal was
prontera-side (see (d)1).

**(b) FIELD-SELLER TRAVERSAL: xXLunasongXx FAILED, the chain itself PROVEN.**
xXLunasongXx crossed the leg-79 Bard-blocked leg into prontera by 13:38 UTC,
then never left the south-gate staging cluster: no prt_in row, no shop
action, **705x2 + 909x1 still held, zeny 57** — third attempt stopped by the
staging congestion, not by the Bard. The full trip shape was proven by s00
instead: Loot (Clover) 13:31:39 on prt_fild08 (175,364) → warp → prontera
walk north → prt_in 14:10:16 → walked the y=128 row east to (172,129),
**chebyshev 1 from Weapon Dealer (172,130)** → TalkToNpc 14:10:59 →
NpcShopSellOpen 14:11:04 → **NpcShopSell 14:11:06** → walked out by 14:12:10.
Zeny 120→125 and the sellable gone from inventory, both DB-verified. This is
the first complete field→warp→dealer→sell run of the population era, and the
merged talk-radius fix converged on true adjacency first try.

**(c) SUSTAINED REPEAT: s00 only.** One sell this window (s00 +5z). s00 has
now sold in a third consecutive selling window (per the leg-79 seed note);
RinceNyan did not repeat (110z unchanged); nobody else sold.

**(d) NEW SIGNATURES.** (1) **Prontera south-gate staging congestion**: four
MerchantDrive agents (NyxSong, PipinWalker, xXLunasongXx, PoringMuffin14)
churned the (154-157, 24-28) tile cluster for 50-90 min, mutually occupying
the first steps toward the dealer target (177,221) — the leg-73
dealer-congestion shape, now at the staging tiles; the named
`occupied_west_no_route` refusals are its telemetry. Only s00, which hit the
prontera side before the cluster formed, routed cleanly north. Next fix
shape: staging-tile approach-cell allocation/queueing. (2) **Warp ping-pong**
(NyxSong): dozens of prontera↔prt_fild08 crossings without dealer progress —
same congestion family. (3) **First popgen guild formations live**: NyxSong
founded `NyxSongGuard` (guild_id 2) and PipinWalker founded
`PipinWalkerGuard` (guild_id 3); FoundGuild + GuildInvite actions executed
in-window, both persisted in the DB; invitees did not join within the
window. (4) Farming stayed healthy: RinceNyan 67 / zeny_wing 33 / NyxSong 18
Attacks from the field agents that escaped or stayed east.

Seeds verified pre-launch: all seven zeny matched `seed-zeny.json` exactly
(60/110/111/58/57/28/120); no seed fix was needed. Heavygraph backends
:8091/:8092 health-checked before launch and untouched after; the DB secret
expanded only inside the mariadb container.

Rejected: crediting xXLunasongXx's crossing as a traversal pass (the sell
gate is zeny/inventory, not map changes); attributing the staging stall to
the occupied-cell fix (the fix produced the honest refusal telemetry that
NAMED the stall); reading s00's +5z as a Clover-at-4z mismatch (sell price
includes the overcharge column; the DB delta is the ground truth); touching
the dealer-ring code (nothing in this leg's evidence points at the ring —
every blocked agent was pre-dealer).

## 2026-11-09 leg 81 prep — staging approach allocation, bounded dealer-entry bypass and named warp crossings

**Evidence and scope.** Based on main `3f5f430f` and the leg-80 receipt
`run/plain_host_receipts/population-receipt-80-1794229859.json` (see the
leg-80 entry above). The live field→warp→prt_in→dealer→sell chain is already
proven by s00; this change addresses the new south-gate congestion and
NyxSong bounce without claiming another live traversal. Implementation branch:
`leg81-staging-approach`. No merge, runner/probe launch, live-world edit,
Docker action, heavengraph access, or `spikes/` formatting.

**Allocation.** `MerchantStaging` reuses the existing dealer `_approach_cell`
and `_free_approach_cells` helpers at the runtime travel-target seam for
prontera `(177,221)`. It selects a free neighbour from this agent's received
player/body cells, with a walkable, no-corner-cutting path on public geometry.
The path also avoids received local blockers near the south gate, rather
than validating only the distant endpoint. The runtime dispatch checks the
same constraints again against its fresh received state; a newly sealed
path names `staging_occupied` and sends nothing, with no blind fallback.
Path memoization changes with position and occupancy. Vacancy releases a
hold immediately; map, native epoch and session changes clear the hold.
Allocation reads no other bot's memo and creates no shared reservations.
Scripts retain their existing grid-free five-evaluation travel author
patience, including across goal changes and script recreation.

**Honest bounded hold.** A full or unreachable neighbour block returns an
ACTIVE empty outcome and taps `hold staging_occupied` once per hold episode.
After **900 monotonic seconds**, the agent may enter the dealer route through
another independently reachable cell of the existing `prt05` trigger,
naming `staging_hold_expired_direct_dealer` once. This is source-backed:
`npc/warps/cities/prontera.txt:25` defines `(177,221)` as the actual entrance
warp with inclusive radii `(2,2)` delivering to `prt_in (168,128)`. Its outer
trigger cells can be free even while the eight immediate neighbours are
occupied. There is no valid same-map MoveTo directly to the dealer's
`prt_in (172,130)` coordinates from prontera. A sealed local cage still
holds after expiry: time alone never authorizes an unreachable bypass.

**Ping-pong diagnosis, not a cooldown hypothesis.** Read-only analysis of
`.work/runtime/population-live/traces/pop_0003_g00m00.jsonl` from leg 80,
13:30–15:00 UTC, found **385 trace map transitions**: 193 field→town and
192 town→field, with no prt_in visit. These are observed trace transitions,
not a retrospective count of raw wire warp packets. The goal reviews were
96 farm_item→farm_item, one grind→grind and one grind→farm_item; repeated
goal flips do not explain the bounce. There were 465 sampled MerchantDrive
rows. At 13:35:50 UTC the admitted drive authored `(177,221)` from
`(157,27)`; at 13:35:52 its empty patience tick was followed by a local
`(156,26)` walk; at 13:35:56 `(154,24)` dispatched from `(155,25)`, followed
by a received field row at 13:35:58 and town again at 13:36:00. The public
`prt001` return trigger is x=153..159, y=20..24.

The runtime's legacy mechanical fallback was treating the drive's empty
patience/queue outcome as permission to walk home. A separate RED contract
reproduced exactly that loss of ownership: without the guard, the empty
merchant tick produced a field-return MoveTo. The runtime now preserves the
admitted town drive through those empty ticks, and outbound staging paths
avoid the public field-return trigger. Congestion and this competing return
walk explain the observed bounce; changing a global cooldown is unwarranted.
A passive **merchant_warp_crossings** receipt field counts only received
prontera↔prt_fild08 edges on each agent's client/window, ignores repeated
observations and unrelated map edges, and resets at connect. Four crossings
name **merchant_warp_ping_pong** once so any residual recurrence is visible.
No extra observe or send is performed for telemetry. The runner change is
only the additive passive sample field; the runner was not launched.

**TDD.** Initial RED: **13 failed, 2 passed**, `/tmp/leg81-red.log`.
The strengthened mechanical-ownership RED is **1 failed**,
`/tmp/leg81-mechanical-red.log`. Contracts cover distinct free choices for
two agents, walkability, received player/body occupancy, saturation tap
cadence, immediate vacancy release, five-evaluation author patience, expiry
and independent dealer-entry reachability, sealed-block refusal, map/epoch
and new-window reset, the public south-gate geometry, dispatch-time
saturation, mechanical ownership/release, crossing counts, and the passive
receipt field. Static checks include strict mypy on 368 files and xenon;
no thresholds or exclusions were weakened.

**Gate inputs.** The supplied worktree began at an unrelated initial commit;
the clean task branch was based on the requested local main before edits.
The rAthena checkout is the pinned `e985006171d2`, and the requested
knowledge/config links were installed. The canonical iro-wiki link still
points to itself (the existing leg-80 prep fact), so verification temporarily
uses `/home/otto/dev/wt-mobpos/run/knowledge/iro-wiki/iro-wiki.db` and restores
the requested canonical link afterward. No gate input or submodule change
is included in the commit.

Rejected: treating `(177,221)` as a mandatory separate destination; inventing
a cross-map coordinate shortcut; hidden cross-agent reservations; blind
sends after a staging veto; interpreting every empty merchant tick as idle;
a hardcoded warp cooldown; attributing the bounce to repeated goal flips;
claiming a new live sell; and unrelated dependency/live-world changes.

**Full gate GREEN before commit.** The documented non-mutating gate,
`nix --option auto-optimise-store false develop -c task --dir . check`,
exited **0** on the completed source: **6,955 passed, 65 subtests passed,
4 warnings, 95.52% coverage** (85% required), **270.00 seconds**. All **17**
new staging/crossing contracts passed, together with all existing dealer,
merchant, staging/travel/approach, runtime and post-sale contracts. Black,
ruff, strict mypy (368 files), vulture, xenon, duplicate-code and bandit all
passed. Transcript: `/tmp/leg81-gate-first.log`. The earlier focused run was
152 passed before the two final window/completion tests were added. The
canonical iro-wiki symlink was restored before commit. Source, tests,
passive receipt field and this log entry are committed and pushed on the
implementation branch for review only; no PR, merge or deployment.

## 2026-11-09 leg 81 — the staging allocation is proven live: five sellers traversed and xXLunasongXx's traversal finally closed (57→70z DB-verified); merchant warp crossings fell from 385 (one agent, leg 80) to 9 (all agents)

**Launch and health.** `systemd-run --user --unit=leg81-runner`, main
`d9cf3a25`, 16:38–18:28 Madrid, duration 6600 s. **26,167 steps, 0 step
errors, 0 TRANSPORT DOWN, 0 PlayingBackendError**; all seven agents online
~149–150 of 220 samples (the full 17:00–18:15 window). Pre-launch readback
matched the seed exactly (60/110/111/58/57/28/125; xXLunasongXx 57 at
prontera (156,26) holding 705x2 + 909x1 + 1201), so no seed fix was needed.

**Sell timeline (UTC).** 16:35:26 PipinWalker sales=[[3,1]] at (172,129)
(+3z); 16:35:38 **xXLunasongXx sales=[[3,2],[4,1]] at (172,129)** (+13z);
16:36:00 PoringMuffin14 sales=[[3,1]] at (173,129) (+7z); 16:36:38 NyxSong
sales=[[3,1]] at (172,129) (+4z); 16:47:45 zeny_wing sales=[[3,1]] at
(172,129) (+4z) — after release-on-vacate re-allocated it from an
out-of-range cell to chebyshev 1. Four sellers completed inside 74 seconds
of each other on distinct ring cells; the fifth sold once its predecessor
vacated. DB deltas: NyxSong 60→64, zeny_wing 111→115, PipinWalker 58→61,
**xXLunasongXx 57→70 (705 gone from inventory)**, PoringMuffin14 28→35;
RinceNyan 110→110 (grounded all window) and s00 125→125 (idle in town)
unchanged.

**Verdicts.** (a) STAGING **PASS** — no 50–90 min mutual occupation: four
sellers held distinct cells and sold within 74 s; holds honest (22 sparse
named `dealer_talk_out_of_range` refusals across 5 cells, ~5 each, no
frozen-author spam). (b) TRAVERSAL **PASS** — xXLunasongXx: logged in at
the staging block, MerchantDrive walk toward (176,220) by 17:15, dealer
ring, TalkToNpc 16:35:31Z at chebyshev 1, NpcShopSellOpen 16:35:36Z,
NpcShopSell 16:35:38Z, zeny 57→70 DB-verified, then returned to the field
and ground for the rest of the window (GrindScript ACTIVE, 145 moves +
3 attacks, 3–4 mobs nearby). (c) PING-PONG **PASS** —
`merchant_warp_crossings` 1/2/3/1/1/1/0 = **9 total** (leg 80: 385
transitions for NyxSong alone). (d) New signatures: the allocation can
hand out ring cells at chebyshev 2–4 from the dealer (the talk radius
rejects those with named refusals; release-on-vacate resolved it live for
zeny_wing — a chebyshev ≤1 pre-filter is the cheap hardening if it
recurs); receipt-sample `pos` froze for two field agents (g00m00 at
(159,346), g01m01 at (173,368)) while their traces show continued
moves/attacks/loots to window close — a host-sampling artifact to watch.

Receipt: `run/plain_host_receipts/population-receipt-81-1794238714.json`.
Traces: `.work/runtime/population-live/traces/` (leg window UTC 16:00+).

## 2026-11-09 leg 82 prep — prefer dealer talk-range cells and reconcile received inventory deletions

Base `56303e42`; implementation branch `fix/leg82-economy-slices`. Evidence:
`run/plain_host_receipts/population-receipt-81-1794238714.json` and
`run/plain_host_receipts/population-receipt-80-1794229859.json`, their existing
`.work/runtime/population-live/traces/` files, and the saved
`/tmp/population_leg80.log`, `/tmp/population_leg81.log` transcripts. No
runner/probe launch, live-world/Docker edit, heavengraph access, packetdb
edit, `spikes/` formatting, PR or merge.

**Dealer allocation.** `MerchantStaging.dealer_target` is wired through the
runtime travel-target seam into `_merchant_approach`. It checks the eight
Chebyshev-1 neighbours first, using received local occupancy and a walkable,
no-corner-cutting path. Only when none is available does it select a
reachable free cell at radius 2–4, naming `dealer_outer_fallback`, the cell,
its Chebyshev distance, and `preferred_chebyshev<=1=unavailable`. The outer
cell is a queue position, never permission to talk out of range. A new
inner vacancy is preferred immediately; unchanged selections retain the
existing five-evaluation author patience. A sealed block holds with the
same named preference. No cross-agent reservation or other bot's memo is
read. Prontera staging and its bounded entry hold retain their contracts.

**Evidence correction for signature d1.** The existing script helper already
constructs only the eight immediate dealer neighbours. In zeny_wing's leg-81
trace, lines 140068–140093 (16:46:53–16:47:36 UTC) repeatedly author
`MoveTo(172,129)`, which is Chebyshev 1; wire targets progress through
`(169,128)`, `(170,128)`, `(171,128)`, `(172,128)`, then `(172,129)`.
The range-2–4 taps describe intermediate *agent positions*, not proof that
the allocator handed out outer destinations. The new runtime contract makes
the requested preference and named saturation fallback explicit without
claiming that the saved trace proves a bad final target.

**Knife-guard verdict: missing delete accounting, not missing login ingest
or lazy construction.** `NativeGameplayTracker.indexed_inventory` directly
projects its complete received baseline. Both inventory-list packet IDs
(0x0991, 0x0A0D) were already ingested; 0x00AF and 0x07FA were already in
`spikes/003-clientless-limbs/packetdb.py`. The old `_other` handler discarded
the inventory-known latch on *every* delete, including successful sales,
and disarmed the initial inventory/WEIGHT barrier. Subsequent WEIGHT or map
packets could not restore it. No additional packet registration is needed.

Concrete traces: s00/YuffieFy81 sells index 3 at
**2026-11-09 14:11:06.941388 UTC**, leg 80, trace line 234835. The prior
14:11:01 state contains 705×1 and 1201×1; the 14:11:25 decision (line
234843) reports `inventory=unknown`, inventory change sequence **1166**,
then WEIGHT sequence **1167** with value 400. zeny_wing sells index 3 at
**16:47:45.157581 UTC**, leg 81, line 140100. Its prior 16:46:53 state
contains 915×1 and 1201×1; the 16:48:25 decision (line 140115) reports
unknown inventory, change sequence **1151**, then WEIGHT **1152**, value
400. The respective saved runtime logs name `inventory_unknown` at 125z
and 115z. These are received baseline → sale → unknown transitions.

**C6 evidence limit.** Neither leg-80/81 saved transcript has a C6 bind, and
neither receipt samples a bound offer for these two agents. They cannot
supply the requested moment of a valid C6 simultaneously with unknown
inventory. The existing leg-76 transcript does: `/tmp/population_leg76.log`
lines 40–43 show C6 receipt **89**, **19 rows**, a valid **1201** row at
50z, and `stock=False(stock=False slots=None)`. It belongs to s00/account
2200006, with change sequence **83** preceding WEIGHT **84**. This supports
the same accounting diagnosis; it is not relabelled as leg-80/81 evidence.
Both recent agents already held a Knife, so their unspent balance does not
prove an unmet buy goal. The duplicate-weapon travel guard remains intact.

**Fix and fail-closed boundary.** `_inventory_delete` decodes the registered
00AF index/count and 07FA reason/index/count layouts (pinned
`rathena/src/map/clif.cpp:2894–2930`). Against a complete real received
baseline, it subtracts the exact quantity, removes exhausted indices and
stale worn entries, and preserves the indexed view before the shop context
reads it. Unknown baseline, absent index, zero quantity or overdraw still
invalidate inventory; WEIGHT alone cannot repair it. Deletes before the
LoadEnd barrier retain the previous conservative refusal. Acquisition
history never substitutes for current stock, and no item is fabricated.

TDD RED: **7 failed, 11 passed** (`/tmp/leg82-red.log`). Focused GREEN:
**206 passed** (`/tmp/leg82-focused.log`), including all existing staging,
dealer approach, gameplay, repair, purchase and buy-backoff contracts. New
contracts cover distinct perceived free inner cells, walkability, named
outer saturation and immediate vacancy release, a sealed hold, partial/full
received deletions for both packet IDs, replay safety, invalid-delta refusal,
a real inventory plus Knife offer authorizing the normal purchase send,
unknown-stock refusal, and retaining a received Knife after selling loot
and changing maps. The existing three-evaluation give-up remains bounded.

Gate inputs are the requested knowledge/config symlinks and a private
checkout of pinned rAthena `e985006171d2`. As documented in leg-81 prep,
the canonical iro-wiki symlink loops to itself; verification temporarily
uses `/home/otto/dev/wt-mobpos/run/knowledge/iro-wiki/iro-wiki.db` and restores
the requested canonical link afterward. No input or submodule changes are
part of this commit. Rejected: inventing a C6 event in recent traces,
calling transient wire waypoints allocated dealer cells, seeding dealer
stock, treating unknown inventory as empty, relaxing guard/backoff rules,
and unrelated world/protocol changes.

The first full gate exposed **8 failures** (6,967 passed + 65 subtests,
268.11 s; `/tmp/leg82-full-gate.log`). Two session-wiring contracts pass an
explicit script state without populating the runtime's cached state. The
script now always selects a valid free inner cell with its existing
reachability authority first; only saturation invokes the runtime's outer
allocator. This preserves the existing script/authority contract and never
uses stale runtime state to bypass a hold. Five post-sale contracts exposed
a second interaction: a now-known empty bag restarted novice guidance
before the validated sale/timeout return. `needs_npc_preparation` now honours
`merchant_returning`, preserving the existing received return ownership.
The existing post-sale, poisoned-dialogue and novice-guidance tests all
remain intact. The capacity-freshness test's old assertion that an exact
received deletion makes inventory unknown was updated to require the now
known empty view; its receipt/freshness assertions are unchanged.

**Full documented gate GREEN before commit.** On the completed source,
`nix --option auto-optimise-store false develop -c task --dir . check`
(the first command of the final `check && audit` invocation) succeeded:
**6,975 passed, 65 subtests passed, 4 warnings, 95.52% coverage** (85%
required), **262.60 s**. Black, ruff, strict mypy (**369 files**), vulture,
xenon, duplicate-code and bandit passed. Final focused suite: **361 passed**
(`/tmp/leg82-focused-final.log`). Transcript:
`/tmp/leg82-full-gate-final.log`. Canonical knowledge links are restored
before commit. No thresholds, exclusions, packetdb bytes or SHA pins changed.

**Additional audit is not green.** After the successful documented check,
`task audit` reports **17 known vulnerabilities in four unchanged packages**:
black 26.10.0 (CVE-2026-114134), certifi 2026.7.22
(PYSEC-2026-4320, reported twice), filelock 4.0.11 (13 CVEs), and
opentelemetry-api 1.45.0 (CVE-2026-114603). The combined shell command
therefore exits 201 at audit. `pyproject.toml`, `uv.lock` and `Taskfile.yml`
are byte-identical to base/main `56303e42`; these findings are inherited,
not introduced here. Unrelated dependency upgrades and audit suppressions
are rejected from these two economy slices. This entry does not claim
`task quality` or the additional dependency audit passed.

## 2026-11-09 leg 82 — four sells live, all talks from the chebyshev-1 cell (172,129); post-sell inventory reconciliation proven; the buy arm never admits because every seed persona holds the fixture knife (the leg-40 weapon_release hold) — the spend side needs a weaponless affordable Novice in the roster to fire

**Launch and health.** `systemd-run --user --unit=leg82-runner`, main
`719b9fe6`, 19:18–21:18 Madrid, duration 7200 s. **28,641 steps, 0 step
errors, 0 TRANSPORT DOWN, 0 PlayingBackendError**; all seven agents online
179–180 of 240 samples (the full 19:30–21:00 window; online at open,
offline at close). Three early keepalive-send transients on zeny_wing
(g00m02) recovered via the connect backoff. Pre-launch readback matched
the seed exactly (64/110/115/61/70/35/125), so no seed fix. Launch-line
correction recorded for future briefs: `--runtime-root` is the DB root
(`.work/runtime/population-live`, the parent of `db/`) and `--memory-root`
the journal directory (`.work/runtime/population-live/memory`) — both are
required by the runner's argparse; a one-flag line fails startup.

**Sell timeline (UTC; all four sales `[[3,1]]` at prt_in npc 110001762
from the chebyshev-1 cell (172,129)).** 19:05:30 xXLunasongXx (+3z
70→73); 19:09:04 NyxSong (+3z 64→67); 19:14:13 RinceNyan (looted stock,
+3z 110→113); 19:43:17 PoringMuffin14 (looted stock, +5z 35→40 — a
non-Jellopy sellable, most plausibly 713 Empty Bottle at 5z; the item id
was not snapshotted pre-sale). DB deltas are the ground truth:
64/110/115/61/70/35/125 → 67/113/115/61/73/40/125. Post-sale
re-admissions: NyxSong looted a 713 (zeny=67 stock=1 at 20:45) and
xXLunasongXx a second 909 (zeny=73 stock=1 at 20:50); the window closed
before either sold. Merchant warp crossings per agent 2–3 (14 total = 7
round trips: 4 sell trips, 2 re-admission trips, zeny_wing's early field
trip).

**Verdicts.** (a) RING **PASS** — every dealer selection landed on a
chebyshev≤1 approach cell: zero `dealer_outer_fallback`, zero
`staging_occupied`, zero bypass taps; all four TalkToNpc calls fired from
(172,129); the 20 `dealer_talk_out_of_range` taps are exactly four named
approaches (168→172 along y=128, chebyshev 4→3→2→2→2) each converging to
the talk cell; no 2–4 cell parking (saturation never occurred — four
sellers sequenced through the single adjacent cell). (b) SPEND **NOT MET —
NOT ARMED, BY THE LEG-40 HOLD**: the buy arm (C5→C6→knife) admits only a
weaponless affordable Novice (`_want_refusal` returns `weapon_release`
when `not has_stock and any wanted weapon in inventory`;
`NOVICE_WANTED_WEAPONS = (1201, 1202, 1204)`, scripts.py:237); all seven
seed personas hold the fixture knife 1201, so every affordable agent was
`weapon_release`d (zeny_wing 115z included — its goal stayed `farm_item`
through 64 heartbeat reviews). No `NpcShopBuySelection` was minted by any
agent. To exercise the spend live the seed roster needs a weaponless
affordable Novice (fixture SQL without 1201, zeny ≥ 50). (c) SELL
**PASS** — all residual named stock sold (both 909 holders) plus two
looted stocks; the drive handled sell→return→re-admit across trips.
(d) SIGNATURES — the inventory delete-receipt reconciliation (0x00AF/0x07FA
against the received baseline, `native_gameplay._inventory_delete`) is
proven live: all four sells left `inv_known=True` (post-sale
`weapon_release` taps carry `inv_known=True`; the leg-76
sell→unknown-inventory→purchase-refused chain is broken), and the
fail-closed purchase guard never triggered (no inconsistent receipt).
Socials live: two new guilds founded (guild table rows 2 `NyxSongGuard`
master NyxSong and 3 `PipinWalkerGuard` master PipinWalker; `FxGuard`
row 1 pre-existing), party invites/chat active. New signature: all four
sells chose the prt_in interior dealer (npc 110001762) rather than a
street approach.

**Evidence.** Receipt
`run/plain_host_receipts/population-receipt-82-1794248282.json`; traces
`.work/runtime/population-live/traces/pop_0003_*.jsonl` (UTC; `NpcShopSell`
rows at 19:05/19:09/19:14/19:43); runner transcript
`/tmp/population_leg82.log`; DB readback via the e2e mariadb container
(`/tmp/leg82_final.sql`). No gate run for this window commit (no code
change); the standing gate figure 6,975+65/95.52% is from the
economy-slices merge `34980fd4`.

## 2026-11-09 leg 83 — the spend test failed at a NEW gate one layer ABOVE the weapon guard: the knife strip emptied zeny_wing's inventory and `needs_npc_preparation` (scripts.py:1279) held it in novice guidance all window — 218 TalkToNpc to the spawn-cell warp npc 110010229 (which can never deliver `instructions_received`), 0 MoveTo, 0 buy actions; sells continued (xXLunasongXx 73→76z, NyxSong 67→70z, both chebyshev-1 at the prt_in dealer, then correctly weapon_release-held)

**Pre-window state (21:42-21:46).** Baseline verified against the seed
before launch: char 300000-300006 zeny 67/113/115/61/73/40/125 — exact
match, no seed fix needed. THE STRIP: `DELETE FROM inventory WHERE
char_id=300002 AND nameid=1201` (zeny_wing's fixture knife, equip=2);
verified the inventory EMPTY and zeny 115. Clean logless launch under
`systemd-run --user --unit=leg83-runner` at 21:45:46 (duration 7200s),
window Mon [22.0, 23.25] = 22:00-23:15 Madrid.

**THE MECHANISM (why the spend never armed).** The strip achieved its
direct purpose — zeny_wing holds no wanted weapon, so the leg-40
`weapon_release` guard is out of its picture (no merchant line for it
names that term) — but an empty inventory is ALSO the first clause of
`needs_npc_preparation` (scripts.py:1279: Novice + `inventory_known` +
`not state.inventory` + no instruction received + not returning). In
`brain._step_goal_script` (brain.py:753-756) that gate returns
`NpcGuidanceScript().step(state)` BEFORE `_sell_drive_rearm` (:758) is
ever consulted, and `self._plan is None` in prontera (no spawns declared,
no mobs observed — `_setup_farm_plan` authors nothing in a city). So the
merchant drive's admission — which WOULD have admitted zeny_wing (Novice,
`inv_known=True`, stock=0, no wanted weapon, zeny 115 ≥ floor 50,
prontera on MERCHANT_ROUTE dest (177,221)) — was never even evaluated:
no merchant-drive line for zeny_wing exists anywhere in the runner
transcript. The loop then cannot self-clear: `NpcGuidanceScript.step`
(scripts.py:1267) talks to `npcs[0]` — the NEAREST npc-kind actor, which
at its spawn cell (156,25) is the warp `prtf004` (npc 110010229) at
(156,26), Chebyshev 1 — and a warp never delivers
`npc_instructions_received`, so `needs_npc_preparation` stays true
forever. The NPC-close discipline closes each dialog (NpcClose x217) and
the gate re-fires TalkToNpc x218, first action 21:00:08 UTC, last action
22:14:52 UTC — the loop ran the entire 75-minute window. Receipt
corroboration: npc_stage `opening` x45 and `blocked` x156 of 240 samples,
71 decides, pos frozen at (156,25), 0 MoveTo.

**VERDICTS.** (a) SPEND **FAIL** — zero hops past the guard fired:
weapon_release GONE (the strip worked), but the drive admission never ran
(held by `needs_npc_preparation` via brain.py:753), NpcShopBuySelection 0,
MerchantDrive 0 (MoveTo 0 all window), dealer talk 0, C5 type 0 / C6 buy
list / 0xCA purchase 0; DB truth: zeny 115→115, inventory stays empty, no
1201 purchased. The full economy loop remains open at exactly this gate.
(b) SELL **PASS** — two chebyshev-1 sells at the prt_in interior dealer:
xXLunasongXx NpcShopSellOpen 21:23:43 → NpcShopSell 21:23:45 UTC (73→76z),
NyxSong 21:25:22 → 21:25:24 (67→70z); both approaches converged live
(out_of_range taps chebyshev 4→3→2→1 across (168,128)→(172,128)), and
both sellers were then weapon_release-held in prt_in — the leg-40 guard
working as designed on agents that still hold the fixture knife.
PipinWalker (61z), RinceNyan (113z), PoringMuffin14 (40z, below floor),
s00/YuffieFy81 (125z) unchanged. (c) RUN HEALTH **PASS** — 28,678 steps,
0 step_errors, 0 TRANSPORT DOWN, 7/7 online through the window (150/150
window samples each), clean staggered logoff at 23:15, runner exit clean
at 7200s with the receipt written. Socials stayed live (NyxSong
FoundGuild x1, GuildInvite x6, InviteToParty x2). (d) NEW SIGNATURE —
the strip-guidance collision: `needs_npc_preparation`'s `not
state.inventory` clause makes the weaponless-affordable state (the buy
arm's exact precondition) indistinguishable from the un-prepared novice
state, and in a town the gate is unresolvable because the nearest
npc-kind actor is a warp that can never instruct. Leg-84 slice (TDD):
exempt merchant-drive-admitted agents from the preparation gate — either
consult `merchant_admission_refusal(state) is None` inside
`needs_npc_preparation`, or move `_sell_drive_rearm` ABOVE the
preparation return in brain.py:753 — and make NpcGuidanceScript never
target warp-kind npcs (they can never deliver instructions). Note the
same gate shape exists in `script_for` (scripts.py:1291) and
`playing_runtime._npc_mechanical` (:2806) — fix all three consistently or
name why not.

**Evidence.** Receipt
`run/plain_host_receipts/population-receipt-83-1794257145.json`; traces
`.work/runtime/population-live/traces/pop_0003_*.jsonl` (UTC; zeny_wing
window rows 1048 with TalkToNpc x218 / NpcClose x217 / MoveTo x0 and
dialogue npc 110010229 x225; seller NpcShopSell rows 21:23:45 and
21:25:24); runner transcript `/tmp/population_leg83.log` (8 distinct
merchant-drive lines, none for zeny_wing); DB readback char 300000-300006
zeny/positions/inventory via the e2e mariadb container. No gate run for
this window commit (no code change); the standing gate figure is
unchanged from the leg-83 seed commit `91af0c6a`.


## 2026-11-10 leg 84 — admitted stripped buyers outrank novice preparation; guidance excludes received warp sprites

Implementation-only slice from main `8cc7e821`. Leg 83 evidence:
`run/plain_host_receipts/population-receipt-83-1794257145.json` (28,678
steps, zero step errors). Its saved analysis records zeny_wing at 115z,
empty known inventory and prontera (156,25): the preparation gate intercepted
the affordable buyer before merchant admission, then repeatedly talked to
warp prtf004/110010229 instead of taking the dealer route. This slice runs
no population runner, probe, live world or Docker operation and claims no
new live purchase evidence.

The shared `needs_npc_preparation` predicate now evaluates
`merchant_admission_refusal(state)` before allowing preparation to divert
the tick. All three consumers share that precedence: the brain's
`_step_goal_script`, the `script_for` factory and `PlayingClient._npc_mechanical`.
An admitted buyer passes through to the brain's existing merchant re-arm,
under every goal, including its empty patience ticks. A refusal retains
novice guidance and emits the existing bounded, change-only named admission
tap. The original native/Novice/known-empty/no-instruction/not-returning
conditions remain intact, as do recovery and active dialogue barriers.
The goal script remains the chosen goal's script, so completing a trade
releases the retained social behavior correctly.

`ActorRef.npc_sprite` carries the already-received actor presentation from
the runtime's owner-local metadata, with no hidden NPC lookup. Pinned
rAthena `npc.hpp` identifies `JT_WARPNPC=45` and
`JT_HIDDEN_WARP_NPC=139`; both are excluded by the shared
`is_guidance_npc` candidate predicate in guidance and the exploration gate.
Object presentation 12 remains an ordinary monster-sprite NPC presentation,
not a warp classification. A warp-only/no-guide view returns FAILED with
the named debug reason `no_non_warp_guidance_npc`, emits no TalkToNpc,
and permits the existing bounded public-map exploration.

TDD RED: **23 failed, 2 passed** (`/tmp/leg84-red.log`). Focused GREEN:
**142 passed** (`/tmp/leg84-focused-final.log`). Contracts cover the 115z known-empty
prontera buyer under all five goals, factory/runtime preparation precedence,
zero-zeny and unknown-route novice guidance, named zeny/route/buy-suspension
refusals, both warp sprites with all three received entry layouts, a farther
valid guide, warp-only exploration, fresh sprite replacement, patient drive
ownership and returning to retained social behavior after buying. Existing
merchant admission and guidance/recovery contracts remain part of the focused
suite.

Rejected: an unconditional merchant re-arm before preparation (its return
arm could steal a refused novice's guidance), replacing every admitted
agent's retained goal script with GrindScript (the existing sell-completion
contracts catch that behavior change), using objecttype 12 as a warp marker,
weakening admission guards or claiming offline tests prove a live purchase.
No spikes formatting, thresholds, exclusions, packet bytes, dependency pins,
corpus contents or live-world files change.

Gate setup uses the requested config.log and knowledge symlinks and a private
checkout of the pinned rAthena `e985006171d2`. The canonical iro-wiki DB
symlink loops to itself, as documented in earlier implementation entries;
verification temporarily uses the existing
`/home/otto/dev/wt-mobpos/run/knowledge/iro-wiki/iro-wiki.db` corpus and restores
the exact requested canonical link before commit. No gate input or submodule
change is included in the commit.


**Full gate GREEN before commit.**
`nix develop -c task --dir . check` (with process-local
`NIX_CONFIG='auto-optimise-store = false'` to avoid the host's store
hard-link limit) exited 0: **7,005 passed, 65 subtests passed, 4 warnings,
95.52% coverage** (85% required), **257.98 s**. Black, ruff, strict mypy
(**370 files**), vulture, xenon, duplicate-code and bandit passed. Final
transcript: `/tmp/leg84-full-gate-final.log`. The preliminary gate transcript
`/tmp/leg84-full-gate.log` records an intentional interruption after 3,369
passing tests to strengthen the moving-entry regression fixture; the fresh
final gate above ran to completion on the final implementation and tests.

Final preparation sites: `src/robots/app/brain.py:753`,
`src/robots/app/scripts.py:1311` (`script_for`) and
`src/robots/app/playing_runtime.py:2806` (`_npc_mechanical`), all through
`src/robots/app/scripts.py:1284` (`needs_npc_preparation`). Warp candidate
selection is `src/robots/app/scripts.py:1266`; received sprite projection
is `src/robots/app/playing_runtime.py:3097`. Canonical knowledge links were
restored before commit. The implementation branch is pushed without merging.


## 2026-11-10 leg 84 window — the strip-guidance merge verified live through the dealtype; the buy open never minted (the C4→C5 hop is the remaining hold); the sell side closed again (PipinWalker 61→64z)

Shepherd run of the strip re-test on the e2e world, launch 00:08 Madrid,
systemd unit `leg84-runner`, window [1, 0.5, 2.0] with the leg-83 zeny
baseline 70/113/115/61/76/40/125 (read back identical pre-launch; zeny_wing
300002 still weaponless — no seed fix needed). Receipt:
`run/plain_host_receipts/population-receipt-84-1794265660.json` — 28,691
steps, 0 step errors, 0 TRANSPORT DOWN, 7/7 online at the staggered window
open, 1,207 decides total (223/213/113/138/200/222/98), routine move gates
only, no rx_error. `passed` is None (this receipt schema carries no
engagement-floor verdict); health is read from the counters above.

(a) SPEND: **FAILED — zeny_wing did not buy the knife** (final DB: no 1201
row, zeny 115 flat, parked prt_in 172,129). The holding hop is now exactly
named: the admitted buyer walked prontera (156,25)→the inn-door staging leg
(`MERCHANT_ROUTE["prontera"]` 177,221, validated target 176,220, ~35 min at
5.9 cells/min), warped prt_in 00:03:21 UTC, approached the dealer 110001762
to Chebyshev 1, and **TalkToNpc 00:04:04 → ZC_SELECT_DEALTYPE received
00:04:09 (stage `unsupported_shop`)** — the leg-83 guidance collision is
gone and every hop up to the dealtype fired. The hold: **the C5 buy-open
never minted** — `_shop_loop_mechanical` ran with no shop action already
present, no `merchant-drive: buy give-up` and no `shop-debug: mint skipped`
tap fired (that tap only logs with a bound offer, so the pre-offer silence
is a blind spot), so `_buy_open_action` → `npc_shop_buy_selection` →
`_shop_dialogue(now)` returned None every tick. `_shop_dialogue`'s conjunct
set (`_npc_self_ready` standing/stand-pending/rest, `_npc.failed`,
`cancel_uncertain`, requests<32, map identity) is the gate; the exact
failing conjunct needs a next-leg instrument (a per-conjunct buy-open tap
mirroring `_note_mint_skip` but firing before any offer exists). The
dialogue then closed (`NpcClose` 00:04:25, 16 s after the C4, no reviewed
`unsupported_shop` drive exists in `_dialogue_clear_drive`, and the
admission tap never flipped to a refusal, so neither the buy give-up nor
`_recover_idle_merchant` accounts for it — second open question), and the
one-talk-per-contact latch (`_DEALER_TALKED`, cleared only when the dealer
npc leaves view) kept the drive parked with empty actions for the rest of
the window (113 decides, 0 further actions).

(b) Guidance exclusion: **PASSED** — zero TalkToNpc-to-warp rows fleet-wide
this window (leg 83: 218 by zeny_wing alone); zeny_wing's only npc contact
was the dealer itself. The admission taps named the verdict for every
agent: `admitted` (zeny_wing, buy arm), `weapon_release` (NyxSong,
RinceNyan, xXLunasongXx, YuffieFy81 — each already holds the equipped
fixture knife), `no_stock_below_zeny_floor` (PoringMuffin14, 40z), and the
sell arm admitted PipinWalker (stock=1).

(c) SELL side: **CLOSED again** — PipinWalker ran the full mechanical sell
chain (TalkToNpc 00:16:52 → `NpcShopSellOpen` 00:16:57 → `NpcShopSell`
00:16:59) for +3 z (61→64), DB-verified. Notably its sell-open minted fine
while zeny_wing's buy-open did not 12 minutes earlier: `_sell_open_action`
gates on stage+stock only, `_buy_open_action` additionally passes
`_shop_dialogue` — the divergence confirms the gate sits in the buy path's
dialogue-readiness read, not in the shared stage machine.

(d) Fleet state: 6/7 chars hold the equipped 1201 (fixture knives;
zeny_wing is the sole stripped buyer — the roster is now exactly the one
weaponless affordable Novice the spend side needs); zeny flat elsewhere;
field legs ground and traveled normally (PoringMuffin14/NyxSong/RinceNyan
roamed prt_fild08; YuffieFy81 stayed idle-town at 282,214 under a refused
drive). New signature for the next leg: the post-C4 dealer park (empty
actions at Chebyshev 1 with stage `unsupported_shop`, no C5, no offer, no
give-up tap) — instrument `_shop_dialogue` per conjunct, then re-run the
spend test with the same roster.


## 2026-11-10 LEG-85 — buy-open uses received dealer adjacency; timeout close rearms a bounded contact

Implementation branch `leg-85-buy-open-dialogue`, based on main `eb348b35`.
Evidence: `run/plain_host_receipts/population-receipt-84-1794265660.json`:
zeny_wing reached the dealer, received C4 at 00:04:09, never minted C5,
closed at 00:04:25, then held the one-talk latch. PipinWalker's sell-open
minted in the same window. This change is offline implementation evidence;
no runner, probe, world, Docker or heavengraph operation was performed.

The exact reproducible failed conjunct is `_shop_dialogue` ->
`_npc_self_ready` -> `_npc_motion_ready()` ->
`tracker.view.arrival_confirmed`. A nonzero walk leaves that flag false
even when the received position is adjacent and the pending walk is gone.
In the synthetic post-walk, post-C4/pre-C6 replay, finite clocks, validated
native telemetry, the dialogue, selected character/session, life, standing,
stand/rest barriers, failed/cancel flags, request budget and map identity
all pass; only the extra arrival proof fails. Sell-open and the corrected
dealer click already use received adjacency. The proposed C6 circular
dependency is absent: `_shop_dialogue` reads neither offer rows nor an
inventory snapshot.

`src/robots/app/playing_runtime.py:1830` (`_shop_dialogue`) now names each
refusal; `:1855` (`_buy_open_refusal`) uses the current talk, received
dealer adjacency and real actuation/identity prerequisites, retaining the
outstanding-walk barrier without requiring the stale arrival flag.
`:1879` emits `shop-debug: buy-open held by <conjunct>` on every refusal,
including pre-offer failure/cancel refusals at the outer shop-loop gate.
The buy and sell open latches also exclude each other for the same prompt:
waiting for a minted sell-open cannot fall through to a buy-open next tick.
Owner-bound dispatch, current prompt checks, finite clocks, request limits,
and the real C6 purchase authority remain in place. Purchase admission and
offer-lifetime predicates are unchanged.

A successfully sent timeout close with no bound offer queues the admitted
contact for rearm. The next host recovery pump releases just that bot/NPC
latch through `scripts.release_merchant_talk` (`scripts.py:222`), allowing
the next script tick to talk again. `_rearm_closed_merchant`
(`playing_runtime.py:2963`) shares `_take_npc_retry` (`:1131`) with existing
timeout recovery: three attempts, at least five seconds apart, per
five-minute epoch. Exhaustion keeps the contact latched until the next
epoch; poison, cancellation uncertainty, active dialogues, bound offers,
and unready actuation cannot release it. Session reset discards the pending
rearm. The existing stockless-buy give-up path remains terminal for its
exchange and is not turned into a new click loop.

TDD RED: `/tmp/leg85-red.log` records **11 failures and 1 pass**: the buy
open, named taps and closed-contact rearm failed; the same sell-open replay
passed. `/tmp/leg85-outer-red.log` records two additional outer-gate tap
failures before their fix. Focused GREEN: **122 tests**, including the new
14 cases, existing buy-selection ownership/drift tests, sell-completion
tests, timeout recovery and bound-offer mint guards
(`/tmp/leg85-green-final.log`). The movement guard regression now supplies
an actual outstanding walk; the stale arrival flag alone is the defect
being removed. Repeated ticks mint/send one open only; the close/reopen
regression consumes exactly three tokens, remains quiet through repeated
ticks, then rearms once in the next epoch.

Rejected: fabricating a C6 or inventory snapshot, removing shared
`_npc_self_ready` guards globally, relaxing purchase admission, resetting
the entire fleet's contact registry, changing retry limits, or touching
spikes. No claim of a live purchase is made.

Gate preparation uses the requested canonical knowledge/config links and
a private checkout of pinned rAthena `e985006171d2`. As recorded in leg 84,
the canonical iro-wiki link loops to itself. Verification temporarily uses
the existing `/home/otto/dev/wt-mobpos/run/knowledge/iro-wiki/iro-wiki.db`
corpus; the exact requested link is restored before commit. No gate input,
dependency, threshold, exclusion, submodule or live-world edit is committed.

**Full gate GREEN before commit:** `nix develop -c task --dir . check`,
with process-local `NIX_CONFIG='auto-optimise-store = false'` for the host's
store hard-link limit, exited 0: **7,019 passed, 65 subtests passed,
4 warnings, 95.53% coverage**, **280.03 s**. Black, ruff, strict mypy
(**371 files**), vulture, xenon, duplicate-code and bandit passed. Final
transcript: `/tmp/leg85-full-gate-final.log`. The earlier
`/tmp/leg85-full-gate.log` stopped at static analysis; its typing,
statement-count and complexity findings were fixed before the complete
final run. Canonical knowledge links were restored before commit. The
implementation branch is pushed without merging.

## Leg 85 — the spend re-test landed: the full economy loop is live population-wide (2026-11-10)

Window Tue [1, 3.0, 4.25] = 03:00-04:15 Madrid, runner `leg85-runner` (systemd-run
--user, 7200 s) on main 147409e3 with the buy-open adjacency merge (235669a7).
Receipt: `run/plain_host_receipts/population-receipt-85-1794274225.json` —
**28,562 steps, 0 step_errors, 0 rx_error, 0 dispatch_errors, 0 TRANSPORT DOWN**;
all 7 agents online for the entire 149-sample window (03:00-04:15), decisions
84-142 per agent. Seed staged exactly (fresh readback pre-launch matched
70/113/115/64/76/40/125); zeny_wing logged out AT the dealer (prt_in 172,129).

**THE SPEND LANDED — zeny_wing's decisive arc, 12 seconds login-to-purchase**
(trace `pop_0003_g00m02.jsonl`, UTC): 02:00:08 `TalkToNpc 110001762`;
02:00:10 ZC_SELECT_DEALTYPE (stage `unsupported_shop`) → **`NpcShopBuySelection`
minted** (C5, epoch 1, prompt_sequence 69, opened_sequence 68) — the leg-84 gate
is gone; the buy-open rides received adjacency like the sell-open; 02:00:12
`NpcShopPurchase {item_id 1201, quantity 1, maximum_zeny 115}`; the 02:01:09
state_tick reads **zeny 65** — exactly the Knife's 50 z. DB ground truth: char
300002 zeny 115→65 mid-window, inventory row `1201, amount 1, equip=2`
(EQP_HAND_R per pinned rathena mmo.hpp:340) — bought AND equipped.

**Beyond the test subject: all six merchant-drive agents closed sell→buy→equip
this window.** Sell arms landed live at the dealer corner: PipinWalker 64→71 z
(02:18:28, prt_in 169,127), PoringMuffin14 40→43 z (02:17:40, prt_in 171,128),
more sales behind `weapon_release` taps (zeny 79/91/116/70 ≥ floor 50,
affordable=True). Final DB readback: every one of the six holds
`1201, 1, equip=2`; zeny NyxSong 70→91, RinceNyan 113→116, zeny_wing 115→70
(re-sold after the buy), PipinWalker 64→74, xXLunasongXx 76→79, PoringMuffin14
40→46 — every merchant agent net-positive: sold loot, bought the weapon, kept
the change. YuffieFy81 (s00) holds a knife that predates the window: seed zeny
125 unchanged, 0 merchant_warp_crossings, no merchant arm rows — no in-window
spend was possible (fixture knife INSERT 2b0f249e armed all 7 live chars on
Oct 28; the solo's row survives while the six merchants demonstrably lacked
weapons at window open — their buy arcs and zeny math prove absence).

**Named taps observed live (no silent gates anywhere in the arc):**
`dealer_talk_out_of_range` (chebyshev 2-4, agent/dealer cells named),
`buy-open held by stage` (stage=opening/waiting, offer_bound=False —
double-open prevention), `offer invalidated (purchase-ca-result)`
(had_issued=True, had_offer=True), `weapon_release` (sell→buy handoff),
`sell arm admitted` (map/dest/zeny/stock).

**Verdict: the full economy loop — farm → loot → sell → BUY → equip — is
closed and DB-verified for the whole merchant population.** Next leg: kills
WITH the weapons (attack authoring at 1-cell melee range, the leg-34 limiters
widen/approach), the loop then re-arms with weapon-accelerated farming; s00's
idle-with-knife behavior in prontera (84 decides, no merchant arm) is worth a
glance. No code change this leg; no gate run (receipt + log only).

## Leg 86 — ARMED KILLS LAND: three agents convert knife attacks to DB-verified kills (2026-11-10)

Window Tue [1, 8.5, 10.0] = 08:30-10:00 Madrid (90 min), runner `leg86-runner`
(systemd-run --user, 7800 s) on main 3900b297, seed staged exactly (fresh
readback pre-launch matched 91/116/70/74/79/46/125 — no drift, no SQL).
Receipt: `run/plain_host_receipts/population-receipt-86-1794294871.json` —
**31,082 steps, 0 step_errors, 0 TRANSPORT DOWN, 0 PlayingBackendError**; all
7 agents online the full window, decisions 99-157 each at full cadence.

**(a) ARMED KILLS: YES — the loop repeats armed.** Exp deltas vs the pre-launch
baseline decode EXACTLY against the pinned pre-re mob_db at 1x rates:
PipinWalker +2/+1 = one Poring (BaseExp 2/JobExp 1), RinceNyan +2/+1 = one
Poring, zeny_wing +2/+4 = one Drops (2/4) — three kills, one per agent,
species-verified (no Lunatic 28/15 or Pupa 66/108 deltas present). The full
chain is trace-verified for PipinWalker: 4 swings at gid 110183671
(07:50:18-25 UTC, (181,356) prt_fild08) → kill → ItemDrop 909 Jellopy
(07:50:27) + 512 Apple (07:50:29) → Loot attempts (07:50:29/31). 4 swings to
kill a 50-HP Poring with the knife is the expected armed math. Field drops
seen this window: 909 Jellopy, 512 Apple, 935 Clover (real drop tables;
no 713/1002 rolled). Looted inventory ground truth: NyxSong holds 935 Clover
x1, RinceNyan 909 Jellopy x1.

**The hop to name is ATTACK AUTHORING VOLUME: 30 attacks / 6 armed agents /
90 min** (leg 85 same-filter: 114; per-agent 1/5/20/4/0/0). Kill conversion
when attacks fire is high (~1 kill per 5-10 knife swings), but the agents
spend the window roaming — MoveTos 1,598-2,631 per agent (leg 85: 799-1,141)
— and rarely reach the adjacent-cell attack state. The leg-34 widen/approach
limiters remain the binding constraint, not the weapon.

**(b) SUSTAINED: YES — the second economy cycle in one day.** xXLunasongXx
79→82 z (sold its Jellopy 909; inventory clean after), PoringMuffin14 46→49 z
(looted fresh stock mid-window — `sell arm admitted` 08:50 with stock=1 —
then sold it). Two agents bank unsold stock for the next cycle (NyxSong 935,
RinceNyan 909).

**(c) run health: clean** (above). Every merchant tap named, no silent gates:
`weapon_release` (s00 08:30: zeny=125 stock=0 has_stock=False), `sell arm
admitted` (08:50), `dealer_talk_out_of_range` (09:27, chebyshev 2, agent
(170,128) vs dealer (172,130) — recovered; the sale landed).

**(d) new signatures:** (1) xXLunasongXx: 0 attacks / 40 Loot actions / 0
MonsterSpotted — it roamed 174→248 x looting drops from the other agents'
kills, almost all failed (inventory ended clean): opportunistic loot without
ever spotting a mob. (2) s00 YuffieFy81: ~2,450 MoveTos toward the field
travel target (156,22) while its position only jittered ±3 cells around
prontera (284,223) — the travel never progressed, same stuck shape as leg 85;
the solo never farmed (0 attacks, 0 exp, zeny 125 unchanged). (3) Pickup
failure: PipinWalker's own-kill drops at adjacent cells produced Loot
attempts but no inventory rows — loot success rate is the next refinement.

**Next leg: attack authoring at density** — the widen/approach stack against
a live field (kills/agent should scale from 1 to tens once attack authoring
fires at field density), then loot-success rate and the s00 travel block.
No code change this leg; no gate run (receipt + log only).

## LEG-87 implementation — consecutive farm starvation and approach contracts (2026-11-10)

Baseline: main `1bb04abf`, evidence
`run/plain_host_receipts/population-receipt-86-1794294871.json` (30 attacks
across six armed agents in 90 minutes; 1,598–2,631 MoveTos per agent).
This is an offline implementation slice; no new population window, runner,
probe, live-world or Docker operation was performed. No claim of increased
live attack volume follows from these tests.

**The proposed missing readback is already fixed at this baseline.**
`_run_review` already passes the persisted `(frozenset(target_mobs), map)`
streak to `FarmScript(initial_starved=...)`, and the leg-34 nonzero-injection
test already passes. Do not reapply that historical fix or diagnose the
leg-86 volume loss as proof that the readback is absent.

**The remaining reset bug reproduced RED, then passed GREEN.** The old
dictionary retained historical keys: target A → B → A (or map A → B → A)
resurrected A's old streak even though the evaluations were no longer
consecutive. Leaving farming, plan expiry and a new native session could
also resurrect it. `_inherit_widen_streak` now checks the immediately
previous plan before replacement; only the same target set and map inherit.
`_sync_widen_streak` keeps only the current key. Intermediate plans reset
even without a script step. Target ordering and new plan IDs do not reset;
seeing the preferred species does. A new session's own legitimate new
evaluations still accumulate.

`tests/test_farm_reauthor_cadence.py` adds 18 offline cases. Against the
unchanged baseline: **10 failed / 8 passed** (all failures are stale-streak
resurrection); after the fix: **18 passed**. Heartbeat re-authoring every
1, 5 or 19 steps reaches the widening threshold on evaluation 20. The
9- and 14-cell approach cases use the real native runtime's incremental
route sends, received walk acknowledgements and repeated heartbeat plans:
the script reaches an adjacent cell, an in-flight walk names `pending_walk`
and sends no swing, then a received stationary arrival releases the gate
and sends the expected attack. No goal-script walkability filters, modes,
targeting shortcuts or attack decision bypasses were added.

**Loot-success refinement deferred: acknowledgement/refusal attribution.**
The own-attack → received target death → received drop fixtures verify that
both mechanical and explicitly authored pickups name an active threat
(`pickup deferred (threat)`, floor item ID and nearest distance), and do not
consume the pickup memo. They do not prove live drop ownership. At pinned
rAthena `e985006171d2`, `clif_parse_TakeItem` (`src/map/clif.cpp:12006`)
accepts shuffled `0x0362`; `pc_takeitem` (`src/map/pc.cpp:6197`) checks
distance **2**, pickup permission and ownership/party priority, then awards
inventory. Standing ON the drop is therefore not a server requirement;
the current runtime's range 1 is already conservative. `0x009D` is floor
appearance, not inventory confirmation. `clif_additem`
(`src/map/clif.cpp:2838`) emits the pinned `0x0A37` pickup acknowledgement;
`NativeGameplayTracker._pickup` consumes successful results into inventory
and currently discards nonzero result codes. A follow-up slice should
attribute those received refusals/absent acknowledgements to attempted
pickups before changing range, retry or ownership policy. The leg-86
own-kill inventory gap remains unexplained by this offline slice.

**Pre-commit full gate GREEN:** `nix develop -c task --dir . check` —
Black and mypy checked 372 files; Ruff, vulture, xenon, duplicate-code and
Bandit passed. Pytest: **7,036 passed, 1 skipped, 65 subtests passed**, four
warnings, **95.54% total coverage** (85% minimum), 263.75 seconds. Only
`src/robots/app/brain.py`, the new regression module and this log changed;
`spikes/` and the rAthena gitlink are unchanged.

## Leg 87 (2026-11-10, window Tue 14:30-16:00 Madrid) — attack-volume validation: the widen-streak persistence fix is live

Receipt: `run/plain_host_receipts/population-receipt-87-1794316483.json` (31,060 steps,
0 errors, 0 TRANSPORT DOWN, 260 samples, decide cadence full: 96-177/agent, ~954 total,
heavengraph :8091/:8092 healthy the whole window; runner `leg87-runner`, launched
14:23 CET under `systemd-run --user`, exit 16:28 CET).

**(a) ATTACK VOLUME — PASS, 7.3x.** 220 attacks vs leg-86's 30 (per-agent avg 31.4 vs
4.3). Six of seven agents attacked (leg-86: 30 attacks concentrated in two agents).
Top attackers: PipinWalker 117, xXLunasongXx 48, RinceNyan 21. **Widen events: 17
target-set growth events** across all six field agents (e.g. `('Lunatic',)` →
`('Lunatic','Pupa')` after sustained starvation; g01m01 x6, g00m01 x5, g01m00 x4,
g00m00 x2) — the streak now survives heartbeat re-authors and widens at threshold,
with honest narrowing on species change. Stop-and-swing discipline: 100% of attacks
fired from a standing position (zero same-second move+attack rows), and 100% had
monsters in the decide context (Pupa/Lunatic/Poring/Drops).

**(b) LOOT — attempts up, conversion partial.** 33 Loot attempts (leg-86: ~52 with
only 4 kept rows). Post-window inventory ground truth: NyxSong holds Jellopy(909) x1,
RinceNyan holds Clover(705) x1; everything else in-window picked up was sold. Four
agents closed the sell chain (NpcShopSellOpen+Sell x4); fleet zeny +24 net (seed
91/116/70/74/82/49/125 → 103/119/76/74/82/52/125). No purchases: all seven already
hold the equipped knife (1201 equip=2, `char.weapon=1`) from leg 85, so zeny deltas
are pure sell income; the one buy-open attempt held at stage `opening`
(`offer_bound=False`) — buy path unexercised by necessity. The 0x0A37
attempt-vs-acknowledgement attribution remains the deferred refinement.

**(c) SUSTAINED — PASS: third economy cycle in one day** (leg 85 yesterday evening,
leg 86 this morning 08:14-10:24, leg 87 this afternoon). Kills: 6/7 agents gained
base exp (+29 fleet base, +15 job): NyxSong +8/+3, RinceNyan +5/+1, zeny_wing
+10/+7, PipinWalker +1/+1, xXLunasongXx +2/+1, PoringMuffin14 +3/+2. Species-per-kill
attribution stays blocked by the picklog silent-fail (0 rows again; known since the
w63-era, cosmetic repair queued) and party even-share exp splitting — per-kill
values at 7.5x from the pinned `mob_db.yml` (Poring 15/7, Pupa 15/30, Lunatic 45/15,
Drops 30/22) exceed every observed per-agent delta, consistent with shared credit;
exp deltas remain the server-side kill record.

**(d) New signature: the solo-in-city roam trap.** s00 (YuffieFy81) logged into
prontera, whose map has no spawn-species entries → no farm plan authored →
GrindScript roam targets (±8/±5) land on unwalkable city cells and the
nearest-walkable re-roll collapses each move to ±1 cell: 2,446 MoveTos, position
jitter only, 0 attacks, 0 exp, decides repeatedly choosing `party_join` with no
invite in existence. Fix direction (queued): when the current map has no spawn
knowledge and `next_action=grind`, author travel to a known field map at the
plan level. Operational notes: dealer-adjacency refusals named correctly by the
`dealer_talk_out_of_range` tap (chebyshev=2) with re-approach; `sell arm admitted`
and `weapon_release` taps fired; merchant congestion (leg-73 defect) did not recur
with the six field agents. NO gate (receipt + log only; no code change).

## LEG-88 implementation — leave a spawn-empty city for the nearest known field (2026-11-10)

Baseline: main `848be8d5`; signature (d) in
`run/plain_host_receipts/population-receipt-87-1794316483.json`: solo s00
(YuffieFy81) remained in Prontera for 2,446 MoveTos, with zero attacks or
experience. This slice is offline implementation and verification; it does
not claim a new live traversal or increased live attack volume.

The brain now authors the destination farm plan before travelling when both
local target knowledge and observed monsters are absent. The public spawn
index supplies candidate fields and target species; the structured local
warp declarations (the same source as `route_hint`) supply their routes.
Dijkstra ranks routes by summed Chebyshev walking distance plus one per
warp, an explicit knowledge-level cost estimate rather than a server path
length. The existing TravelRouter rejects doors in disconnected interiors;
unknown geometry retains its existing fail-open semantics. There is no
hard-coded destination: the nearest exit from east-central Prontera can
lead to prt_fild06, while the southern test position selects prt_fild08.

FarmScript follows the selected warp chain through the existing MoveTo
runtime seam, after the merchant drive's existing priority. It resolves the
next leg from each received position, keeps an underway destination stable
across heartbeat reviews, and starts farming immediately on reaching the
field without waiting for another decision or a first mob observation.
Travel preserves the destination species and widen streak without counting
travel steps as starvation evaluations. A city objective cannot overwrite
the selected field and restore city roaming. Known fields retain their
local ±8/±5 patrol steps; a missing field route holds instead of falling
back to city roaming. Script code performs no grid queries, and
playing_runtime's walkability veto and nearest-walkable re-roll are unchanged.
The planner shares immutable public knowledge and geometry caches only;
agent destinations remain in each brain's own plan, with no out-of-game
coordination or census.

TDD RED: four failures and one passing known-field regression before the
implementation. GREEN contracts cover both farming goals, nearest route
cost (including a cheaper multi-hop route), disconnected interiors,
unknown/missing routes, observed monsters, destination stability, unchanged
field roaming, immediate arrival farming, nonzero widen-streak carry,
actual host composition, and the pinned spawn/warp/map-cache declarations.
No runner/probe, live-world/Docker edit, heavengraph operation, or spikes/
formatting was performed. The rAthena gitlink remains at the pinned revision.

**Pre-commit full gate GREEN:** `nix develop -c task --dir . check` —
Black and mypy checked 374 files; Ruff, vulture, xenon, duplicate-code and
Bandit passed. Pytest: **7,050 passed, 1 skipped, 65 subtests passed**, four
warnings, **95.57% total coverage** (85% minimum), 255.03 seconds. All 14
LEG-88 regression cases pass. No unresolved gate or review rejection remains.

## Leg 88 (2026-11-10, window Tue 19:30-21:00 Madrid) — travel-from-knowledge-empty validated live: the s00 odyssey; the dealer sell-churn named

Receipt: `run/plain_host_receipts/population-receipt-88-1794334610.json` (31,096 steps,
0 errors, 0 TRANSPORT DOWN, 260 samples, decide cadence full: 94-245/agent, ~904 total,
heavengraph :8091/:8092 healthy the whole window; runner `leg88-runner`, launched 19:16
CET under `systemd-run --user`, exit 21:26 CET). Pre-launch: seed verified exactly vs a
fresh DB readback (103/119/76/74/82/52/125 — no drift, no fix), no runner resident,
backends healthy, real-shape decide probe 0.48s.

**(a) TRAVEL — PASS for the solo, partial for the fleet.** s00 (YuffieFy81) executed the
first full travel-from-knowledge-empty odyssey: farm_item plans targeting prt_fild06
(the route-nearest known field) authored from spawn-knowledge-empty prontera at
18:30:22; walked to the west exit; crossed prontera→prt_fild06 at 18:31:17 (27,193);
walked across prt_fild06 for ~25 minutes; crossed prt_fild06→pay_fild04 at 18:56:57
(206,175); farmed there immediately (131 attacks through 19:21, ≥1 kill: +2 base/+1
job); kept walking east to (253,194) at close. 1,448 MoveTos, all real travel — the
leg-87 ±1-cell jitter trap (2,446 no-op MoveTos) did not recur anywhere in the fleet.
NyxSong's knowledge side also worked (farm_item plans targeting prt_fild08 authored
continuously from 18:30:02, route walk 156,32→166,201), but at 19:02:11 the merchant
drive diverted it into prt_in before the crossing (it holds one sellable Jellopy) and
the dealer churn absorbed the rest of its window.

**(b) FARMING — attacks hold in volume, collapse in distribution.** 232 attacks total
(leg-87: 220): s00 131, PoringMuffin14 85, xXLunasongXx 9, PipinWalker 5, zeny_wing 2.
All volume landed 18:31-19:33; after that every field agent stopped attacking — the
driver is the loot leg: each field-side agent picked up exactly one sellable and the
merchant drive took over, walking it to town. Kills DB-verified in five agents
(fleet +14 base/+8 job): xXLunasongXx +5/+3, PoringMuffin14 +4/+2, PipinWalker +2/+1,
s00 +2/+1, zeny_wing +1/+1. NyxSong and RinceNyan never attacked.

**(c) ECONOMY — FAIL: zero sells, no fourth cycle.** All seven zeny ended exactly at
seed (103/119/76/74/82/52/125). Five agents stood at the Weapon Dealer for the tail of
the window; npc_stage repeatedly reached `unsupported_shop` (and cycled
`opening`/`blocked`), but `shop_offer` never became non-null for any agent — the C7
sell list never landed, so no sell chain step beyond the dialog stage executed. The
leg-84/85-proven chain did not fire under this window's conditions.

**(d) New signatures.** (1) DEALER SELL-CHURN: TalkToNpc→NpcClose epochs ~5 minutes
apart (the bounded retry-epoch re-arm), e.g. RinceNyan 32 talks / 32 closes from
18:37 to close, zeny flat throughout; the break sits between the C4 dealtype dialog
and the C7 offer. (2) DEALER CONGESTION RECURRED (leg-73 defect): five agents parked
around the dealer simultaneously and 359 named `dealer_talk_out_of_range` rejections
(chebyshev=2) accumulated; the approach-cell allocation/queueing gap is now the
binding constraint whenever several agents hold sellables. (3) MERCHANT-DRIVE
DIVERSION: the sell arm outranks the travel arc — an agent mid-crossing to a known
field abandons the crossing to attempt selling one item (NyxSong). Whether that
precedence is right is a design decision for the next slice.

Inventory ground truth (char DB): all seven hold the equipped knife (1201, equip=2);
unsold sellables: 909 x1 on NyxSong/zeny_wing/xXLunasongXx, 705 x1 on RinceNyan, 512
x1 on PipinWalker (a leg-85 leftover purchase). Final maps: five logged out in prt_in
(dealer churn), PoringMuffin14 on prt_fild08 (66,302), s00 on pay_fild04 (253,194).
Frontier: dealer approach-cell allocation/queueing, then the C4→C7 break diagnosis.
NO gate (receipt + log only; no code change).
