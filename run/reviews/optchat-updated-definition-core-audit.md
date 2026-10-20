# RO memory core / current UniiChat audit

**Verdict: not compliant.** Current official revision `3c190e06f34aba0c69f49042c526093269604935` (2026-10-08T01:58:24Z); complete text SHA-256 `12f300f760af82bc07bc5201051d1267824ded09c9def8186e4f8144368038d8`.

Finite matrix: 37 rows; ADAPTED=6, FAIL=20, PASS=6, UNKNOWN=5.

**Execution:** 9 actual-core negative contracts failed (0 errors); 139 legacy scoped tests passed. Independent scratch oracle matches rollback binary counter for all 20,001 ticks 0..20,000 using last-message rank; first-message rank matches 481. Four oracle tests passed after preserved RED. No production or live effects; eight frozen dependencies unchanged.

## Required outcome / root cause

RO is not implementing the mistaken first-based rank: it implements a different greedy `_minimal_cover` refit. Merely replacing a formula cannot fix prefix loss, coverage eviction, view persistence, byte measurement or full-chat/raw zoom. Four-to-five unpressured append rewrites prefix; 511 emoji notes emit 4193 bytes at cap4000; budget250 keeps only [6,7) of seven notes; time30→200 changes cached age. Five further negative contracts reproduce whitespace normalization, raw-leaf zoom absence, short-source model calls, nonliteral short-pair separator and truncation of a free 487-byte leaf.

## Finite matrix

|Invariant|Status|Definition lines|RO evidence|Finding|
|---|---|---|---|---|
|raw_append_ack_lock|PASS|43-46|`src/robots/adapters/memory_journal.py:75-105`; `src/robots/adapters/memory_journal.py:137-156`; `src/robots/society/memory.py:169-174`|Raw journal has lifetime flock, private no-follow file opens, flush/fsync before local append; baseline receipts exercise storage failures.|
|verbatim_original|FAIL|9-10|`src/robots/society/memory.py:410-414`|Facade collapses all whitespace before persistence, so historical originals cannot be recovered from normalized notes.|
|chat_kinds_and_complete_transcript|ADAPTED|28-41|`src/robots/society/memory.py:28-44`; `src/robots/app/agent_runtime.py:623-701`|RO records typed observed experiences, not user/unii/tool/echo/work/note full chat; observed-note equivalence must remain explicitly adapted.|
|daily_log_permanent_ids|ADAPTED|27-33|`src/robots/adapters/memory_journal.py:75-80`; `src/robots/adapters/memory_journal.py:144-145`|One persona JSONL rather than daily chat streams; indices are list positions, not serialized permanent message ids.|
|exclude_model_thoughts|UNKNOWN|47-48|`src/robots/society/memory.py:28-44`; `src/robots/app/brain.py:422-425`|Typed journal has no reasoning field, but a complete model-output logging boundary is absent; cannot prove no thought text enters arbitrary notes.|
|tool_head_tail_and_long_text_split|UNKNOWN|49-51|`src/robots/society/memory.py:410-414`; `src/robots/adapters/memory_journal.py:137-145`|No full-chat admission/splitting adapter in these ports; neither 30000-character tool cap nor lossless long non-tool chunking is implemented here.|
|dyadic_binary_immutable_nodes|PASS|55-62|`src/robots/society/memory.py:220-248`; `src/robots/society/memory.py:250-257`|Builds fully covered leaves and exact sibling parents once using per-level counters; no raw-block hybrid or recomputation.|
|durable_summary_nodes|PASS|67-67|`src/robots/society/memory.py:143-150`; `src/robots/society/memory.py:250-257`; `src/robots/adapters/memory_summary_cache.py:258-299`|Optional summary store preserves built nodes with acknowledgement-before-publication; no claim that configuration always enables it.|
|short_source_zero_calls|FAIL|64-66|`src/robots/society/memory.py:230-245`|Every short leaf and pair invokes summarizer; counting probe made 3 calls for two short leaves.|
|short_pair_verbatim_newline|FAIL|64-66|`src/robots/society/memory.py:90-92`; `src/robots/adapters/memory_summary_cache.py:70-76`|Stub joins with tilde; cache rejects newline/control chars. Future short-pair policy requires a new storage encoding, not just a renderer change.|
|512_utf8_summary_policy|FAIL|56-69|`src/robots/society/memory.py:32-34`; `src/robots/society/memory.py:99-110`; `src/robots/adapters/memory_summary_cache.py:24-29`|Default limits are 120/200 Python characters and cache accepts up to 4096 bytes; core has no 512-byte policy. The 487-byte free leaf is truncated.|
|view_summaries_only_no_raw_last|PASS|85-87|`src/robots/society/memory.py:289-297`; `src/robots/society/memory.py:319-319`|Every rendered line reads a built node summary, including last leaf; docstring calling latest verbatim does not mean a raw-text special case.|
|whole_history_coverage_under_pressure|FAIL|73-74|`src/robots/society/memory.py:319-324`|View drops oldest covered nodes instead of coarsening; seven-note budget250 probe retains only [6,7). Raw journal is not deleted.|
|last_message_due_rank|FAIL|157-182|`src/robots/society/memory.py:260-276`; `src/robots/society/memory.py:319-324`|Production uses greedy refit, not due rank (neither first nor last formula). Independent oracle verifies required last-based rank for 20001 steps; do not misattribute old-first implementation to RO.|
|oldest_ties_and_built_parent_filter|FAIL|164-169|`src/robots/society/memory.py:260-276`; `src/robots/society/memory.py:315-319`|No incremental sibling selection seam; full summaries built synchronously before refit. Required tie/readiness behavior is separately verified in independent oracle, not production.|
|append_only_prefix_between_batches|FAIL|184-186|`src/robots/society/memory.py:260-276`; `src/robots/society/memory.py:319-319`|Four-to-five note append changes L1:0 prefix to L2:0 even at budget128000, well below pressure.|
|128000_64000_sawtooth|FAIL|186-191|`src/robots/society/memory.py:32-34`; `src/robots/society/memory.py:314-324`|Every read recomputes a minimal cover under character cap4000; no high/low state or batch boundary.|
|partial_batch_continues_without_drop|FAIL|192-193|`src/robots/society/memory.py:314-324`|No pending-batch flag, no parent-ready stall retention; budget enforcement evicts oldest coverage.|
|persistent_view_never_restart_refit|FAIL|195-197|`src/robots/society/memory.py:126-150`; `src/robots/society/memory.py:314-324`; `src/robots/society/memory.py:65-72`|Stores raw notes and tree nodes only; there is no view-state store or view checkpoint. Restart reconstructs cover on read, not saved coordinates.|
|actual_utf8_view_bytes|FAIL|23-23|`src/robots/society/memory.py:327-328`; `src/robots/society/memory.py:314-324`|511 emoji notes render 4193 UTF-8 bytes despite budget4000; len(str) is not bytes.|
|stable_no_dates_view|FAIL|85-87|`src/robots/society/memory.py:279-297`|Optional now renders relative age; wall clock30 to200 rewrites the same single-note view. Default now=None does not erase that unsafe API.|
|id_plus_n_addressing|ADAPTED|60-62|`src/robots/society/memory.py:297-297`; `src/robots/society/memory.py:347-372`|Llevel:index names are convertible losslessly, but literal id+n wire format and zoom(id,n) API are absent.|
|zoom_leaf_original|FAIL|445-447|`src/robots/society/memory.py:365-366`; `src/robots/society/memory.py:410-414`|Level-zero zoom returns unchanged summary, not whole original; truncation is irrecoverable through current zoom API.|
|date_id_tool|FAIL|448-448|`src/robots/society/memory.py:214-218`; `src/robots/society/memory.py:416-420`|Timestamp tail helper exists, but no public permanent-message date(id) tool.|
|ready_work_queues|FAIL|307-308|`src/robots/society/memory.py:225-248`; `src/robots/adapters/memory_summary_cache.py:112-120`; `src/robots/adapters/memory_summary_cache.py:267-279`|No ready queue; existing per-level counters avoid rescanning built nodes, so do not call core tree build O(N²). However repeated full raw-prefix hashing per node is O(N²) work in summary-cache binding.|
|eight_job_leaf_admission_and_parent_ready|FAIL|300-306|`src/robots/society/memory.py:225-248`|Synchronous build under RLock; no eight-job worker/admission policy. Parent dependencies are correctly satisfied by bottom-up order, but literal scheduling unavailable.|
|compaction_context_16k_32k_and_prefix_stop|FAIL|245-260|`src/robots/society/memory.py:75-80`; `src/robots/society/memory.py:103-110`|Summarizer port gets only A/B, no contextual view; neither compacted A/B view state nor missing-built-prefix stop can be supplied.|
|512_ruler_retries_shortest_next_message|FAIL|262-298|`src/robots/society/memory.py:103-110`; `src/robots/society/memory.py:230-245`|Qwen prompt has no 512-dash ruler, byte feedback, five-attempt conversation, shortest-line selection, or explicit per-message retry queue. Definition permits slight overshoot after retries:512 is a target for model output, not an unconditional rejection bound.|
|fixed_tools_and_system_shared_with_compactions|UNKNOWN|206-213|`src/robots/society/memory.py:75-80`; `src/robots/society/memory.py:103-110`; `src/robots/app/brain.py:422-425`|Core Summarizer/ChatGenerator do not expose tools/system/cache block identity; no provider call executed, therefore no prefix-cache compliance assertion.|
|fresh_turn_view_before_new_message|ADAPTED|427-439|`src/robots/app/brain.py:422-425`; `src/robots/app/agent_runtime.py:623-643`|RO event-driven decisions and chat escalation are not the literal endless-chat harness; adapting observed experience memory does not establish fresh full-chat continuity.|
|anthropic_four_line_marks_single_writer_ttl|UNKNOWN|223-237|`src/robots/society/memory.py:75-80`; `src/robots/app/brain.py:422-425`|Provider wire/runtime constraint: no Anthropic request serialization, shared-prefix in-flight coordination, TTL or usage-field verification audited or called.|
|subagent_chats_and_work_reports|UNKNOWN|450-454|`src/robots/society/memory.py:28-44`|Optional full-chat feature has no core typed experience analogue; no literal subagent log/zoom(Name) certification.|
|consumer_keeps_full_selected_view|FAIL|73-74|`src/robots/domain/decisions.py:77-78`|Decision payload silently slices memory_lines[:40]. Increasing core budget alone would still discard most rendered context at this consumer.|
|raw_source_identity_child_closure_binding|PASS|67-67|`src/robots/adapters/memory_summary_cache.py:185-219`; `src/robots/adapters/memory_summary_cache.py:225-256`|Cache rejects world/persona/policy mismatch, changed/truncated raw prefix, duplicates/noncontiguous levels or missing child closure; existing baseline exercises guards.|
|bounded_cache_not_forever_chat|ADAPTED|9-10|`src/robots/adapters/memory_summary_cache.py:24-29`; `src/robots/adapters/memory_summary_cache.py:213-219`|Explicit 8192-node and other resource ceilings are safe finite admission, not endless-chat capacity; exceeding them blocks persistence rather than allowing unbounded growth.|
|uncertain_write_poisoning|PASS|45-46|`src/robots/adapters/memory_journal.py:146-161`; `src/robots/adapters/memory_summary_cache.py:292-299`; `src/robots/society/memory.py:250-257`|Uncertain raw/cache writes poison future work; retains stronger existing safety contract while adapting policy.|
|compactor_model_policy|ADAPTED|310-310|`src/robots/society/memory.py:84-110`; `src/robots/app/agent_runtime.py:1001-1009`|Host still defaults deterministic StubSummarizer; optional Qwen is separate from named Haiku policy. No paid or native inference effects.|

## Compatibility / migration handoff

### 1. Choose adapted policy before effects

- Confirm actual decision/chat model context budget, provider wire, hosted-vs-local compactor economics, concurrency and memory ceiling. Choose explicit adapted RO UTF-8 high/low thresholds; 4000 characters cannot be renamed 64000/128000 bytes.
- Declare observed-note adaptation versus complete UniiChat transcript; no new live journal, profile, migration, model, package, or server action without approval.

### 2. One finite core/cache-loss repair slice

- Introduce immutable coordinate ViewState + ViewStateStore port (coordinates, pending batch, exact policy/identity, raw count/digest and referenced-node closure); update view only on append/build events, never refit on reads/restart.
- Use inclusive-last due rank exact rational comparison, oldest ties, sibling-only merges with built parents; append a leaf otherwise, cross HIGH then coarsen to LOW; stalled pending batches retain full coverage and resume on next message.
- Measure rendered payload including separators/provenance in UTF-8; freeze age/date out of cached view; keep timestamps accessible through a separate date API.
- Add <=512-byte direct leaves and newline-joined short pairs without inference; new policy storage must preserve newline text, flatten only rendering. Add provider target-size ruler/retries later through an extended port rather than silent character slicing.
- Expose real leaf/raw zoom (adapted L names can retain legacy facade wrappers); keep raw append durable before visibility, fail-closed guards, immutable nodes and existing cleanup/poison behavior.
- Change decisions memory_lines[:40] only with reviewed consumer byte policy; otherwise core budget fix cannot preserve the full downstream view. Audit context_selector.fit_budget call sites separately: selected retrieval can be intentionally bounded, not whole-history continuity.

### 3. Explicit compatible namespace and offline migration design

- Keep old append-only raw/summary files untouched and accepted ADRs immutable. New codec/policy namespace is required; old summaries, raw-normalized notes and absent view checkpoints cannot pretend to preserve the old literal prompt prefix.
- Existing typed notes can be imported as adapted note data with original stored text and timestamps, not invented lost whitespace/full-chat kinds. Prior already-normalized originals and never-logged messages cannot be reconstructed.
- If old policy lacks persisted view, require explicit one-time baseline reset/bootstrap migration approval; quantify cache invalidation, do not silently refit or claim resume equivalence.
- Reject malformed/missing new checkpoint, wrong persona/world/policy, wrong raw prefix or missing referenced nodes/children; source binding incremental hash/checkpoint design must remove quadratic repeated prefix work without weakening integrity.
- Maintain legacy Memory.remember/view/zoom_line signatures only as documented adapters; new ViewState, raw leaf/date retrieval and compactor-context/scheduling ports need exact compatibility tests. World root supplied explicitly; never infer unknown profile/model labels.

### 4. MVP acceptance cutoff

- Offline TDD on unchanged-safety fixtures: append prefix under no pressure, 511-emoji bytes, no dropped coverage, immutable node content, T10 and 20001-step rank oracle, oldest ties, delayed parent pending batches, corrupt/missing checkpoint rejection, exact restart view and raw-prefix/child closure validation.
- Run scoped and completed-snapshot whole quality gates only after writers stop; no automatic implementation from this audit.
- Separate later contextual compactor 16000/32000-byte view, bounded ready queues/admission, five-attempt 512-byte feedback, fresh literal full-chat logging, and provider-specific stable system/tools/cache wire metrics. Real Anthropic marks/usage and live effects remain unverified, not waived by pure oracle success.

## Evidence and reproduction

All exact source/test/artifact hashes, parsed JUnit cases and unchanged freeze are in `/home/otto/dev/ro-bots/run/reviews/optchat-updated-definition-core-audit.json`.
Scratch: `/home/otto/.hermes/cache/scratch/optchat-core-audit`. Actual RED: `actual-red.xml` / `actual-red.log`. Legacy: `baseline.xml`. Oracle: `oracle.py`, `test_oracle.py`, `oracle-result.json`, `oracle-red.log`, `oracle-green.log`.

```sh
cd /home/otto/.hermes/cache/scratch/optchat-core-audit
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_oracle -v
PYTHONDONTWRITEBYTECODE=1 python3 oracle.py
cd /home/otto/dev/ro-bots
env PYTHONDONTWRITEBYTECODE=1 TMPDIR=/home/otto/.hermes/cache/scratch/optchat-core-audit PYTHONPATH=/home/otto/dev/ro-bots/src nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c .venv/bin/python -m pytest -q -o addopts='' -p no:cacheprovider --basetemp=/home/otto/.hermes/cache/scratch/optchat-core-audit/pytest-red-rerun /home/otto/.hermes/cache/scratch/test_optchat_updated_contract.py /home/otto/.hermes/cache/scratch/optchat-core-audit/test_actual_extra.py --junitxml=/home/otto/.hermes/cache/scratch/optchat-core-audit/actual-red-rerun.xml
```

Expected production-contract exit:1 (9 genuine failing assertions, not errors). Oracle exit:0. No blanket literal UniiChat, provider cache-rate or native acceptance claim. Batch/restart migration behavior is specified, not implemented or verified by the rank-only oracle.

## Issues

- First stdlib urllib public API fetch failed TLS certificate validation; curl with normal certificate checks retrieved and verified authoritative current content. web.run also could not access GitHub URLs.
- Legacy tests intentionally encode old policy: ASCII character-budget checks, newest leaf preference, age suffix and leaf zoom no-op; 139 passes are legacy safety evidence, not current-definition compliance.
