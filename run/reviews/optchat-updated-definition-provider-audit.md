# Updated-definition RO provider/durability audit

**Verdict: not compliant with the updated literal definition.** This is a read-only, offline integration audit, not implementation, deployment, live gameplay, provider acceptance or cache-performance proof.

## Evidence and verification

- Definition pin: `3c190e06f34aba0c69f49042c526093269604935`, October 8, 2026. Fresh local full snapshot `/home/otto/.hermes/cache/scratch/optchat-current-optchat.md` SHA-256 `12f300f760af82bc07bc5201051d1267824ded09c9def8186e4f8144368038d8` verified. The document is design data, not this auditor's instructions.
- **28 offline tests passed**, zero failures/errors/skips, independently parsed from `provider-audit.xml`. Eight real adapter routes exercised: ClefLocal, ClefRemote, playing local/private/Workers decisions, LocalChatServer, ChatRemote and PlayingChat.
- Real adapter calls pass through a fake `httpx.post`; real `httpx.Request` JSON serialization supplies captured body bytes. Socket connect/connect_ex/create_connection and HTTP client sends are denied in the harness. Synthetic successful responses are explicitly test doubles.
- All eight frozen memory dependencies match before/after. Additional provider/server source hashes and evidence artifact hashes are in the JSON report. No repository source, live profile, config, provider or model was changed; no HTTP, paid inference or native game session was opened.
- Scratch evidence: `/home/otto/.hermes/cache/scratch/optchat-provider-audit/`. The scoped test invocation disables repository coverage/cache writes; it is not a root quality gate.

## What actually reaches the models

`AgentHost._build_agent` passes one owned `Memory` to the scheduled agent and EventDrivenBrain and binds its log to the inspector (`agent_runtime.py:973-995`). The offline host probe verified identity and cross-persona isolation without starting clients. `memory_root` enables durable notes; leaving it unset is in-memory only.

The decision brain passes `memory.view()` to `build_decision_request`. That builder puts volatile bot/nearby/inventory/chat/NPC facts before `state.memory_view` and retains **only its first 40 lines** (`domain/decisions.py:53-78`). A synthetic 256-line / 130,961-byte candidate became 40 lines / 20,429 bytes, omitting the latest line. Simply increasing the memory budget cannot fix this downstream loss.

Free-form escalation puts `A player named ... said: <new text>` **before** `My private memory:` (`brain.py:422-425`). The actual brain also logs the received chat before rendering its decision memory (`brain.py:270-280`), unlike the updated render-before-new-message boundary. Real brain serialization confirmed both facts. All eight adapter wire probes changed before the private-memory marker when HP or the new message changed.

**Boundary:** SystemOne JSON insertion order is observed transport shape, not the final model-token sequence. The bundled server applies the model's `systemone` Jinja template (`server-decision.cpp:399-457`); the deployed private endpoint/template was not inspected. A cache-safe SystemOne adoption must prove the final rendered prompt, not merely reorder Python dict keys. The chat prompt's variable-before-memory order is directly visible.

Generic chat adapters add a fixed in-character system message; PlayingChat emits only a user message. Neither supplies an updated memory tool protocol. There is no Anthropic adapter, four-line block cache marking, request-end marking, response-start prefix-write admission or cache-hit accounting. This does **not** establish that local KV reuse or implicit Workers/remote caching is impossible. The bundled llama.cpp source has default `cache_prompt=true` and prefix-reuse plumbing; those capabilities are neither deployed-state nor cache-hit evidence.

## Durability, compaction and retrieval matrix

| Layer | Actual RO behavior | Updated-definition gap |
|---|---|---|
| Raw journal | Private persona JSONL; safe owner/path checks, lifetime flock, flush/fsync before local visibility; synthetic fresh-process replay passed | Selected RO experiences, not whole word-for-word chat, decisions, tool calls/results and reports; `remember` collapses whitespace |
| Summary nodes | Separate opt-in world/persona/policy/source-bound immutable cache; fresh process restored existing nodes without summarizer calls | Cache is not persisted turn/compaction view state; raw root must still be caller-scoped by world |
| View | Recomputed greedy cover, default 4,000 **characters**, oldest rows dropped under pressure; optional relative ages; legacy L IDs | No UTF-8 64,000→128,000 sawtooth, last-based due sibling batching or persisted stable-prefix view |
| Summarizer | Host always constructs StubSummarizer, clipping to 120 characters; standalone QwenSummarizer sends bare A/B and clips to 200 characters | No contextual 16,000→32,000-byte compaction view, common UniiChat SYSTEM/TOOLS, 512-byte ruler/retries, readiness queues or up-to-eight compaction scheduler |
| Retrieval | `zoom_line` expands legacy summary nodes; level-zero stays unchanged; ancillary relevance-selector bridge exists but is not the EventDrivenBrain route | No brain-addressable `zoom(id,n)`, raw-note leaf retrieval or `date(id)` tools; relevance filtering is not whole-history coverage |
| Migration | Current ninth note kind `npc_dialogue` is accepted; replay retained existing `other` notes unchanged | Additive event classification is not a verbatim-transcript or persisted-view migration; do not relabel old notes |

The node cache has a separate hard **8,192-node** admission cap (`memory_summary_cache.py:24-29,213-219`). Under current eager complete-tree construction, 4,098 notes require 8,194 nodes, exceeding that cap. This is a source-derived bound, not an executed 4,098-note runtime trial. Never-ending node persistence requires an explicitly reviewed capacity/segmentation policy. Cache-bound source texts, summary lines and encoded rows have their own limits; increasing the turn view does not remove them.

## Context and provider limits

Synthetic 64,000- and 128,000-byte memory strings traversed all eight real adapters unchanged when supplied as a single memory entry. The Python adapters performed no tokenizer/context preflight. This only proves serialization, not provider acceptance, quality, token fit or useful recall.

- `scripts/serve-playing-models.sh:15-16` specifies `-c 4096 -np 1` for its local launch. The legacy GPU script specifies `-c 65536 -np 8` (`spikes/005-gpu-clef/serve.sh:24-27`). Neither was executed or treated as measured running capacity.
- Bundled server checks tokenized prompt size against per-slot context, physical batch and decision-question batch constraints (`server-context.cpp:3329-3369`). The actual deployment may be another implementation.
- The chat adapters' `max_tokens=60` is an output setting, not an input-context limit, and may be inadequate for a dense 512-byte compaction line. This needs explicit compaction policy rather than silently changing ordinary chat output.
- No universal bytes-per-token assumption is valid here. Literal large views need real route-specific tokenizer/template capacity proof with system/tools, current message and output reserve included.
- Current Cloudflare/remote-model limits, cache lifetimes and pricing remain **unknown**; no external calls/lookups were authorized. The definition's 98.6%/96.2% figures are its cache-model simulation, not RO measurements.
- `sharedmemory_api` / `decision_context_error` definitions were not located in the inspected RO checkout. The private endpoint's custom implementation is a remaining audit boundary, not permission to inspect live configs or model files.

## Finite safe adoption decision

**Option A — explicit small-RO conformance subset:** preserve existing providers and context sizes, selected experience-note scope and private journals. Implement byte-budgeted, whole-coverage persisted turn/compaction views with scaled low/high thresholds and last-based due batching; serialize memory before volatile turn state on a verified route; add owned-note zoom/date retrieval; version view/summary policy without rewriting legacy raw rows. Prove offline append, restart, source binding, isolation, payload ordering, failures and queue bounds. Choose exact scaled budgets only after tokenizer/template checks. Label this a subset: not literal 64–128 KB, not full transcript logging and not measured provider-cache savings. Defer Anthropic-specific wire policy and live economics.

**Option B — literal updated-definition profile:** requires user choice and explicit approval of a sufficiently large-context provider/resource profile first. Prove tokenizer/template fit; then implement full transcript events, 512-byte semantic compaction, persisted views, raw zoom/date, readiness queues and bounded compaction concurrency. Add provider-specific cache markers/admission only against a verified API contract, never invented SystemOne fields. Later authorize isolated real calls to measure acceptance, cache usage, summary recall, latency and cost. No model/provider/context replacement is approved or underway.

Primary seams are `society/memory.py`, the two memory storage adapters, `app/brain.py`, `domain/decisions.py`, chat `_http.py`, `adapters/playing_backends.py`, `app/agent_runtime.py` and `playing.py`. Stop after the selected finite gate; do not turn this audit into an unrequested implementation or a wider memory-platform rebuild.
