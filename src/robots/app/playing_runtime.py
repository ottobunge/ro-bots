"""Strict received-wire bridge for the existing scheduled host.

No hidden population, persona progression, optimistic position or stub providers.
Initial life uses fresh authenticated map-session source authority; SELF death
overrides it until an explicit resurrection receipt. Warp alone never revives.
"""

import logging
import math
import random
import struct
import sys
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from robots.adapters.native_actor_presentation import actor_entry_npc_name
from robots.adapters.native_capacity import NativeCapacityContext
from robots.adapters.native_chat_text import public_chat_text
from robots.adapters.native_encounter_context import ReceivedSelfLevel
from robots.adapters.native_encounter_stream import SELECTION_BINDING, NativeEncounterStream
from robots.adapters.native_gameplay import (
    NativeGameplayTracker,
    NativeGameplayView,
    ObservedDamage,
    ObservedFloorItem,
    ObservedPosition,
    ObservedSkillUse,
    ObservedXP,
    attack,
    equip,
    npc_close,
    party_chat,
    pickup,
    respawn,
    sell,
    sell_open,
)
from robots.adapters.native_navigation import (
    MapCache,
    NoRoute,
    WalkMap,
    nearest_walkable,
    shortest_path,
    starter_route,
)
from robots.adapters.native_npc_dialogue import NativeNpcDialogue, observed_npc, received_npc_name
from robots.adapters.native_purchase import NativePurchase, PurchaseAdmission
from robots.adapters.native_self_metadata import server_self_slots
from robots.adapters.native_session_progression import (
    SessionProgression,
    require_native_session_progression,
)
from robots.adapters.native_shop_context import NativeShopContext
from robots.adapters.native_skills import NativeSkillContext
from robots.adapters.native_vitals import NativeTelemetryUnavailable, require_native_vitals
from robots.app.loot_attribution import LootAttribution
from robots.app.merchant_buy_backoff import MerchantBuyBackoff
from robots.app.merchant_staging import MerchantStaging, MerchantWarpCrossings, dealer_entry_cell
from robots.app.npc_planning_execution import LocalNpcDispatch, NpcHostBinding, NpcUiObservation
from robots.app.party_roster import guild_candidate_aid
from robots.app.planning_execution import RestObservation
from robots.app.scripts import (
    MELEE_RANGE,
    MERCHANT_ROUTE,
    MERCHANT_ROUTE_RETURN,
    NOVICE_STAT_TARGETS,
    _approach_cell,
    _dealer_talk,
    merchant_admission_refusal,
    needs_npc_preparation,
    novice_weapon_index,
    release_merchant_talk,
    shop_affordable_weapon,
    shop_sell_entries,
    shop_sellable_stock,
)
from robots.domain.actions import (
    AcceptGuildInvite,
    AcceptInvite,
    Attack,
    FoundGuild,
    GameAction,
    GuildInvite,
    InviteToParty,
    Loot,
    MoveTo,
    NpcClose,
    NpcNext,
    NpcRespond,
    NpcSelect,
    NpcShopBuySelection,
    NpcShopPurchase,
    NpcShopSell,
    NpcShopSellOpen,
    NpcSubmitName,
    PartyChat,
    Rest,
    Say,
    TalkToNpc,
)
from robots.domain.events import (
    DamageTaken,
    InviteReceived,
    ItemDrop,
    MonsterSpotted,
    NpcDialogueReceived,
    WorldEvent,
)
from robots.domain.farm import MobInfo
from robots.domain.model import ActorRef, BotState, ChatLine, Goal, PartyInvite, PartyObservation
from robots.domain.npc import NpcDialogue
from robots.domain.planning import (
    NpcIntent,
    NpcObservation,
    NpcOperation,
    PlanningIdentity,
    npc_intent_matches,
)
from robots.domain.self_metadata import ServerSelfSlots
from robots.domain.shop import (
    QualifiedShopItem,
    ReceivedShopOffer,
    ReceivedZeny,
    ShopPurchaseProgress,
)
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.domain.skills import ReceivedSkillContextReadOnly

# e985 socket.cpp235,396,1016-1022; conf/packet_athena.conf22: inbound
# inactivity closes client sessions after >60s. Leave two intervals of slack.
KEEPALIVE_INTERVAL_S = 20.0
OCCUPIED_CELL_LIMIT = 64
"""Nearest unique received type-0 body cells; presentation never proves identity."""


def _finite_npc_time(value: float) -> bool:
    """Reject unsafe integer conversion before controller clock arithmetic."""
    return (
        type(value) in (int, float)
        and -sys.float_info.max <= value <= sys.float_info.max
        and math.isfinite(value)
    )


def _valid_npc_response(identity: object, intent: object) -> bool:
    """Reject ordinary malformed payloads using the existing domain contracts."""
    if not isinstance(identity, PlanningIdentity) or not isinstance(intent, NpcIntent):
        return False
    try:
        PlanningIdentity.__post_init__(identity)
    except ValueError:
        return False
    return intent.valid()


class ObservedMobDatabase:
    """Public species mechanics; map membership comes only from this agent."""

    def __init__(self, catalog: Iterable[MobInfo] = ()) -> None:
        self.catalog = {mob.id: mob for mob in catalog}
        self._map = ""
        self._visible: tuple[MobInfo, ...] = ()

    @classmethod
    def load(cls, path: Path) -> ObservedMobDatabase:
        data = yaml.safe_load(path.read_text())
        return cls(
            MobInfo(
                row["Id"],
                row["Name"],
                row.get("Level", 1),
                bool(row.get("MvpExp", 0) or row.get("MvpDrops")),
            )
            for row in data["Body"]
        )

    def observe(self, map_name: str, species: Iterable[int]) -> None:
        self._map = map_name
        self._visible = tuple(
            sorted(
                (self.catalog[key] for key in set(species) if key in self.catalog),
                key=lambda mob: (mob.level, mob.id),
            )
        )

    def mobs_on_map(self, map_name: str) -> tuple[MobInfo, ...]:
        return self._visible if map_name == self._map else ()

    def by_name(self, name: str) -> MobInfo | None:
        return next((mob for mob in self.catalog.values() if mob.name == name), None)


@dataclass(frozen=True)
class _FieldPatrol:
    target: tuple[int, int]
    receipt_baseline: int
    context: tuple[str, int | None, Goal]
    deadline: float


_EQUIP_ATTEMPT_CAP = 3
_STAT_BATCH_CAP = 8  # CZ_STATUS_CHANGE spends per dispatch; paced on received acks
"""Bounded CZ 0x0998 sends per inventory index per epoch: several server paths
answer no ack at all (clif.cpp:12117-12130, pc.cpp:12056-12063), so absence of
an ack is not a verdict; after the cap the worn state stays unknown and no
further requests go out until a new session epoch."""


def _received_stats(stats: tuple[int, ...] | None) -> tuple[int, ...] | None:
    """The 0x00BD six-stat tuple as received; None stays None (never zeros)."""
    return tuple(stats) if stats else None


NPC_RETRY_BUDGET = 3
NPC_RETRY_CADENCE_S = 5.0
NPC_RETRY_EPOCH_S = 300.0
RESPAWN_RETRY_CADENCE_S = 30.0
NO_ROUTE_DIRECT_SENDS = 5
# The server's pickup radius: a CZ_ITEM_PICKUP lands when the bot stands
# within Chebyshev<=2 of the drop (pinned pc.cpp:6197).
# leg 69: the once-per-position escalation latch (leg 39) left s00 dead-
# verdicting x944 at pay_fild04 (213,325) while the server still accepted
# walks out of the pocket (it had walked the char 226,317 -> 213,325 on
# the leg-28 direct sends). After ESCALATED_DEAD_DIRECT_BOUND consecutive
# escalated_target_dead verdicts at the same position, the runtime
# releases a SERVER-REPOSITION direct send at the nearest client-side
# walkable cell around the own position (no_route_direct semantics: the
# server path-finds its own side). ESCALATED_DEAD_REPOSITIONS caps the
# repositions per position; a server-confirmed position advance re-arms
# both budgets.
ESCALATED_DEAD_DIRECT_BOUND = 3
ESCALATED_DEAD_REPOSITIONS = 3
_LOOT_PICKUP_RANGE = 2
# Bounded reroute search when a drop's own cell is unwalkable in the grid.
_LOOT_MOVE_RADIUS = 4
"""Direct walks sent at a grid-unreachable target before the patrol fails
(leg 28: the warp cell NoRoute silence — the server path-finds its own
side, so a direct send is the only way a clientless unit ever warps)."""
# Otto's directive (leg 63): the pickup fires only when no enemy is an
# active real threat - an attackable monster within this Chebyshev range
# of the bot's cell defers the loot walk/pickup (the item may despawn;
# safety over loot). The melee engagement distance +2 is the precedent
# (brain._attackable_in_melee_range gates on MELEE_RANGE).
ACTIVE_THREAT_RANGE = MELEE_RANGE + 2
# The loot-walk re-author clock (leg 62: the one-shot move memo burned a
# drop's only walk on a pre-empting script MoveTo / an await_pending gate,
# and the drop despawned at the server's ~60s floor TTL). A loot walk
# re-authors ONCE per item after this many seconds - a bounded faster
# pacing constant inside the pending-walk lifecycle's own 1s no-progress
# release, never unbounded spam; the per-item pickup memo still governs
# the pickup attempt.
LOOT_WALK_REAUTH_S = 1.0


def _pending_guild_invite(wire: Any) -> str | None:
    """The pending 0x16a guild name, if an invite is outstanding."""
    if getattr(wire, "guild_invite_gid", 0):
        return getattr(wire, "guild_invite_name", None) or None
    return None


def _recent_chat_lines(wire: Any, pos_at: float) -> tuple[ChatLine, ...]:
    """The public + party lines, newest last (the decide-state chat block).

    The party lines come from the 0x0109 ZC_PARTY_CHAT dispatch
    (spike client.party_chat); the public lines from the 0x008D path.
    """
    public = tuple(ChatLine("public", str(aid), text, pos_at) for aid, text in wire.chat[-5:])
    party: tuple[ChatLine, ...] = ()
    try:
        party_log = getattr(wire, "party_chat", ())
        party = tuple(ChatLine("party", name, msg, pos_at) for _aid, name, msg in party_log[-5:])
    except TypeError, AttributeError:
        party = ()  # stub wires expose Mock/custom attrs; logging never blocks play
    return public + party


logger = logging.getLogger(__name__)


class PlayingClient:

    # the pending planner owns NPC recovery while a decide is in flight
    npc_recovery_hold = False
    mechanical_recovery_allowed = True
    _npc_retry_epoch_at: float | None = None
    _merchant_reopen: int | None = None
    _merchant_returning = False
    _respawn_retry_at = 0.0
    # consecutive NoRoute direct-walk sends (class default; instance shadow
    # on first use — a successful walk anywhere resets it to 0)
    _no_route_attempts = 0
    # per-(map, target) exhausted-target re-roll memory (leg 37 defect 2);
    # a successful walk anywhere clears it with the budget. Lazily created
    # (the _no_route_attempts shadow idiom; a mutable class default would
    # leak across clients).
    _rerolled_moves_memo: dict[tuple[str, tuple[int, int]], tuple[int, int]] | None = None
    # own positions whose sealed-pocket escalation already fired (leg 39)
    _deadlock_cells_memo: set[tuple[str, tuple[int, int]]] | None = None
    # leg 69 server-reposition budgets: consecutive escalated-dead verdicts,
    # the position they count at, and the reposition direct sends already
    # fired there (class defaults; instance shadow on first use - a
    # server-confirmed position advance re-arms all three)
    _escalated_dead_count = 0
    _escalated_dead_pos: tuple[int, int] | None = None
    _reposition_sends = 0

    @property
    def _deadlock_cells(self) -> set[tuple[str, tuple[int, int]]]:
        cells = self._deadlock_cells_memo
        if cells is None:
            cells = set()
            self._deadlock_cells_memo = cells
        return cells

    @property
    def _rerolled_moves(self) -> dict[tuple[str, tuple[int, int]], tuple[int, int]]:
        memo = self._rerolled_moves_memo
        if memo is None:
            memo = {}
            self._rerolled_moves_memo = memo
        return memo

    """Wrap native limbs while retaining AgentHost's client lifecycle contract."""

    _stat_unacked: int
    _stat_acks_seen: int
    _stat_failed: set[int]
    _loot_ack_cursor: int

    def __init__(
        self,
        wire: Any,
        mob_db: ObservedMobDatabase | None = None,
        *,
        cache: MapCache | None = None,
        public_skill_knowledge: PublicSkillKnowledge | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        keepalive_interval_s: float | None = None,
        seed_zeny: int | None = None,
    ) -> None:
        self.wire, self.cache = wire, cache
        self._init_merchant_navigation()
        self.public_skill_knowledge = public_skill_knowledge
        self._now = monotonic
        # the runner-side balance seed (e2e-43): the wire delivers SP_ZENY on
        # changes only, so the login wallet must be seeded (lowest precedence)
        self._zeny_seed = seed_zeny
        self._pending: tuple[tuple[int, int], int, float, int] | None = None
        self._retry_talk: int | None = None
        self._event_cursor = self._party_obs_cursor = 0
        self._seen_actors: set[int] = set()
        self._seen_floor: set[int] = set()
        self._invite = 0
        self._rng = random.Random(wire.char_name)
        self.mob_db = mob_db or ObservedMobDatabase()
        self._tracker: NativeGameplayTracker | None = None
        self._encounters: NativeEncounterStream | None = None
        self._skills: NativeSkillContext | None = None
        self._skill_wire = wire
        self._epoch: int | None = None
        self._epoch_character = wire.char_name
        self._species: dict[int, int] = {}
        self._npc_names: dict[int, str] = {}
        self._metadata_cursor = 0
        self._authenticated_baseline = False
        self._standing: bool | None = None
        self._last_built_state: BotState | None = None
        self._stand_pending: tuple[int, float, float, int] | None = None
        self._npc_retries, self._npc_retry_at = NPC_RETRY_BUDGET, 0.0
        self._patrol: _FieldPatrol | None = None
        self._keepalive_at: float | None = None
        self._keepalive_failed = False
        self._init_keepalive_pump(keepalive_interval_s)
        self._rest_at: float | None = None
        self._rest_seq: int | None = None
        self._equip_attempts: dict[int, int] = {}
        self._standing_seq = 0
        self._pose_seq = 0
        self._received_vitals: dict[int, int] = {}
        self._vitals_seq = 0
        self._closed = False
        self._init_npc_state()

        self._shop_context = NativeShopContext()
        self._purchase = NativePurchase()
        self._capacity = NativeCapacityContext()
        self._server_self_slots: ServerSelfSlots | None = None
        self._self_slots_owner: tuple[object, ...] | None = None
        self._self_slots_identity: tuple[object, ...] | None = None
        self._npc_dispatch: LocalNpcDispatch | None = None
        self._planning_session = object()
        self._shop_selection: (
            tuple[NpcShopBuySelection, NpcHostBinding, object, object, object] | None
        ) = None
        self._reset_shop_seam()

    @property
    def local_npc_dispatch(self) -> LocalNpcDispatch | None:
        return self._npc_dispatch

    def _reset_shop_seam(self) -> None:
        """Fresh shop-loop state; binding identity invalidates stale mints anyway."""
        self._buy_backoff = MerchantBuyBackoff()
        self._sell_open_issued: tuple[int, int] | None = None
        self._buy_open_issued: tuple[int, int] | None = None
        self._sell_sent: deque[int] = deque(maxlen=16)
        self._sell_open_mint: tuple[NpcShopSellOpen, tuple[object, ...]] | None = None
        self._sell_mint: tuple[NpcShopSell, tuple[object, ...]] | None = None
        self._sell_pending: tuple[NpcShopSell, NpcDialogue, int] | None = None

    def bind_server_self_slots(
        self,
        proof: object,
        *,
        source_id: str,
        observed_at_unix: float,
        login_ip: str,
        login_port: int,
    ) -> bool:
        """Publish offline operator metadata; never transmit or authorize purchases."""
        self._invalidate_self_slots()
        try:
            view = self._observe().view
        except NativeTelemetryUnavailable:
            return False
        if not self._self_slots_ready(view):
            return False
        self._server_self_slots = server_self_slots(
            proof,
            source_id=source_id,
            observed_at_unix=observed_at_unix,
            login_ip=login_ip,
            login_port=login_port,
            session_epoch=self.wire.native_epoch,
            owner=(self.wire.aid, self.wire.gid, self.wire.char_name),
            endpoint=(self.wire.login_ip, self.wire.login_port),
        )
        if self._server_self_slots is not None:
            self._self_slots_owner = self._received_owner()
            self._self_slots_identity = self._self_metadata_identity()
        return self._server_self_slots is not None

    def _invalidate_self_slots(self) -> None:
        self._purchase.check(None)
        self._server_self_slots = None
        self._self_slots_owner = None
        self._self_slots_identity = None

    def _server_slot_allowance(self) -> int | None:
        metadata = self._server_self_slots
        return metadata.inventory_slots if metadata is not None else None

    def _self_metadata_identity(self) -> tuple[object, ...]:
        wire = self.wire
        return (
            wire.native_epoch,
            wire.selection_epoch,
            wire.map_epoch,
            wire.aid,
            wire.gid,
            wire.char_name,
            wire.login_ip,
            wire.login_port,
        )

    def _self_slots_ready(self, view: NativeGameplayView) -> bool:
        try:
            self._progression(selection_only=True)
        except NativeTelemetryUnavailable:
            return False
        wire = self.wire
        return all(
            (
                self._authenticated_baseline,
                view.perception_ready,
                type(wire.aid) is int and 0 < wire.aid <= 0xFFFFFFFF,
                type(wire.char_name) is str and bool(wire.char_name),
                type(wire.login_ip) is str and bool(wire.login_ip),
                type(wire.login_port) is int and 0 < wire.login_port <= 65535,
            )
        )

    def _check_self_slots(self, view: NativeGameplayView) -> None:
        owner = self._self_slots_owner
        if owner is None:
            return
        if not all(
            (
                all(a is b for a, b in zip(owner, self._received_owner(), strict=True)),
                self._self_slots_identity == self._self_metadata_identity(),
                self._self_slots_ready(view),
            )
        ):
            self._invalidate_self_slots()

    @property
    def planning_session(self) -> object:
        return self._planning_session

    def connect(self, *args: Any, **kwargs: Any) -> Any:
        self._stop_keepalive_thread()
        self._merchant_staging.release()
        self._merchant_crossings = MerchantWarpCrossings()
        self._invalidate_self_slots()
        self._planning_session = object()
        self._capacity.invalidate()
        self._shop_context.invalidate()
        self._npc_dispatch = None
        self._invalidate_skills()
        self._encounters = None
        self._patrol = None
        self._keepalive_at = None
        self._reset_shop_seam()
        result = self.wire.connect(*args, **kwargs)
        self._closed = False
        self._epoch = None
        self._keepalive_failed = False
        return result

    def close(self, *args: Any, **kwargs: Any) -> Any:
        self._stop_keepalive_thread()
        self._invalidate_self_slots()
        self._planning_session = object()
        self._capacity.invalidate()
        self._shop_context.invalidate()
        self._invalidate_skills()
        self._encounters = None
        self._reset_shop_seam()
        self._closed = True
        self._rest_at = None
        self._rest_seq = None
        self._stand_pending = None
        self._pending = None
        self._epoch = None
        self._patrol = None
        self._keepalive_at = None
        result = self.wire.close(*args, **kwargs)
        self._keepalive_failed = False
        return result

    _pending_origin: str = "step"
    """Which walk class the current pending came from (the leg-68 release
    tap reads it); every send site re-tags it before arming a pending."""

    def __getattr__(self, name: str) -> Any:
        return getattr(self.wire, name)

    def _zeny_balance(self, view: Any) -> int | None:
        """The balance authority chain: tracked wire observation, then the
        shop loop's receipt, then the runner-side seed (e2e-43: the wire
        delivers SP_ZENY on changes only, so the login wallet is seeded)."""
        if view.zeny is not None:
            tracked: int = view.zeny
            return tracked
        if self._shop_context.balance is not None:
            receipt: int = self._shop_context.balance
            return receipt
        return self._zeny_seed

    def _init_npc_state(self) -> None:
        """The NPC-dialogue observer trio (extracted: the ctor's statement cap)."""
        self._npc = NativeNpcDialogue()
        self._npc_event_sequence = 0
        self._npc_explorations = 0

    def _init_keepalive_pump(self, keepalive_interval_s: float | None) -> None:
        """Validate the interval and build the shared pump state."""
        interval = KEEPALIVE_INTERVAL_S if keepalive_interval_s is None else keepalive_interval_s
        if not math.isfinite(interval) or interval <= 0:
            message = "invalid keepalive interval"
            raise ValueError(message)
        self._keepalive_interval_s = interval
        self._keepalive_lock = threading.Lock()
        self._keepalive_wake = threading.Event()
        self._keepalive_thread: threading.Thread | None = None

    def _health(self) -> None:
        if self._closed:
            self._invalidate_self_slots()
            message = "native playing session closed"
            raise NativeTelemetryUnavailable(message)
        if self._keepalive_failed:
            self._invalidate_self_slots()
            message = "native keepalive send failed; transport release required"
            raise NativeTelemetryUnavailable(message)
        wire = self.wire
        if (
            wire.running is not True
            or wire.connected_map is not True
            or wire.sock is None
            or wire.rx_thread is None
            or wire.rx_thread.is_alive() is not True
            or wire.rx_error
        ):
            self._invalidate_self_slots()
            message = "native playing transport unavailable"
            raise NativeTelemetryUnavailable(message)
        # dispatch_errors are per-frame parse failures, NOT transport failures:
        # the reader is alive and the rest of the stream is healthy. Gating on
        # them starved telemetry forever after one unparseable frame (fx0's
        # shop-interior maps carry one; w43-48 own_pos 0 with a live reader).
        # They stay visible in the client's packet counters for the receipts.

    def _observe(self, *, now: float | None = None) -> NativeGameplayTracker:
        try:
            self._health()
        except NativeTelemetryUnavailable:
            self._invalidate_self_slots()
            self._capacity.invalidate()
            self._invalidate_skills()
            self._npc.invalidate()
            self._shop_context.invalidate()
            self._encounters = None
            raise
        epoch, base, frames = self.wire.native_frame_snapshot()
        if epoch != self._epoch or self._skill_wire is not self.wire:
            self._reset_epoch(epoch, base)
        now = self._now() if now is None else now
        tracker = self._tracker
        if tracker is None or not self._observe_received_context(tracker, epoch, base, frames, now):
            self._invalidate_self_slots()
            self._capacity.invalidate()
            self._npc.invalidate()
            self._shop_context.invalidate()
            self._encounters = None
            self._invalidate_skills()
            message = "native playing frame continuity unavailable"
            raise NativeTelemetryUnavailable(message)
        if self._encounters is not None:
            self._encounters.consume(frames, tracker.view.damage)
        self._check_self_slots(tracker.view)
        return tracker

    def _observe_received_context(
        self,
        tracker: NativeGameplayTracker,
        epoch: int,
        base: int,
        frames: tuple[tuple[int, float, int, bytes], ...],
        now: float,
    ) -> bool:
        binding = self._received_owner()
        identity = (
            epoch,
            self.wire.char_name,
            self.wire.aid,
            self.wire.gid,
            getattr(self.wire, "selection_epoch", None),
            getattr(self.wire, "map_epoch", None),
        )
        if not self._capacity.observe(binding, identity, base, frames, now):
            return tracker._deny()
        if self._capacity.owner_replaced:
            # Preserve unrelated received continuity, but discard the old complete barrier.
            tracker._inventory_known = False
            tracker._inventory_initial = False
        self._shop_context.bind((*binding, self._npc), identity, frames[-1][0] if frames else base)
        return self._consume_received_snapshot(
            tracker, epoch, base, frames, now, inventory_replaced=self._capacity.owner_replaced
        )

    def _received_owner(self) -> tuple[object, ...]:
        """Shared selected-session references; SELF capacity is not NPC-scoped."""
        return (
            self,
            self.wire,
            self._planning_session,
            self.wire.sock,
            self.wire.rx_thread,
            getattr(self.wire, "selected_character_snapshot", None),
        )

    def _consume_received_snapshot(
        self,
        tracker: NativeGameplayTracker,
        epoch: int,
        base: int,
        frames: tuple[tuple[int, float, int, bytes], ...],
        now: float | None = None,
        *,
        inventory_replaced: bool = False,
    ) -> bool:
        """Validate each received context before that frame can release NPC uncertainty."""
        if not tracker.consume_snapshot(epoch, base, ()):
            return False
        now = self._now() if now is None else now
        self._npc.consume((), now)
        self._check_shop_context(tracker.view, now)
        for frame in frames:
            if frame[0] <= self._metadata_cursor:
                continue
            received = (frame,)
            if not tracker.consume_snapshot(epoch, base, received):
                return False
            if frame[2] == 0x0A37:
                self._observe_loot_acks(tracker.view)
            if inventory_replaced:
                # Retained auth must not rearm a pre-boundary inventory/WEIGHT barrier.
                tracker._inventory_known = False
                tracker._inventory_initial = False
            if self._skills is not None:
                self._skills.consume(frame)
            self._consume_metadata(received)
            self._validate_received_npc_context(tracker.view)
            self._npc.consume(received, now)
            self._check_shop_context(tracker.view, now)
            self._shop_context.consume(frame, epoch)
            self._consume_sell_result(frame)
            self._consume_purchase_frame(frame, tracker, now)
        return True

    def _consume_purchase_frame(
        self, frame: tuple[int, float, int, bytes], tracker: NativeGameplayTracker, now: float
    ) -> None:
        self._purchase.check(self._purchase_snapshot(now, tracker))
        self._purchase.consume(frame, tracker.indexed_inventory)
        progress = self._purchase.progress
        if progress is not None and progress.ca_result is not None:
            self._shop_context.invalidate_offer("purchase-ca-result")

    def _validate_received_npc_context(self, view: NativeGameplayView) -> None:
        if self._npc.view is None:
            return
        if view.position is None:
            self._npc.invalidate()
            return
        map_name = self._map_identity(view.map_name or self.wire.map_name)
        self._validate_npc_context(view, map_name, view.position)

    @property
    def last_built_state(self) -> BotState | None:
        """The most recent build_native_state result, WITHOUT re-observing.

        Instrumentation must read this, never call build_native_state: an
        observing read advances the metadata cursor and empties the runtime's
        event windows (the w65-67 double-consumer stall).
        """
        return self._last_built_state

    def build_native_state(self, goal: Goal) -> BotState:
        self._merchant_paths.clear()
        tracker = self._observe()
        wire, view = self.wire, tracker.view

        try:
            vitals = require_native_vitals(wire.status_params)
            progression = self._progression()
        except NativeTelemetryUnavailable:
            self._invalidate_skills()
            self._shop_context.invalidate()
            raise
        pos = view.position
        if not view.perception_ready or pos is None:
            self._shop_context.invalidate()
            message = "native playing position unavailable"
            raise NativeTelemetryUnavailable(message)
        map_name = self._map_identity(view.map_name or wire.map_name)
        nearby = self._nearby(view, pos, map_name)
        self._validate_npc_context(view, map_name, pos)
        offer = self._current_buy_offer()
        if offer is not None:
            self._buy_backoff.observe(offer, tracker.indexed_inventory is not None)
        invites = (PartyInvite(wire.party_invite_from, pos.at),) if wire.party_invite_pid else ()
        state = BotState(
            name=wire.char_name,
            job=progression.job,
            base_level=progression.base_level,
            hp=vitals.hp,
            max_hp=vitals.max_hp,
            sp=vitals.sp,
            max_sp=vitals.max_sp,
            map_name=map_name,
            x=pos.x,
            y=pos.y,
            goal=goal,
            in_party=self._in_party(),
            nearby=tuple(nearby),
            occupied_cells=self._occupied_cells(view, pos),
            inventory={str(key): count for key, count in (view.inventory_counts or ())},
            pending_invites=invites,
            pending_guild_invite=_pending_guild_invite(wire),
            recent_chat=_recent_chat_lines(wire, pos.at),
            npc_dialogue=self._npc.view,
            npc_instructions_received=self._npc.instructions_received,
            received_skills=self.received_skills,
            public_skill_knowledge=self.public_skill_knowledge,
            shop_offer=self._shop_context.offer,
            merchant_buy_suspended=self._buy_backoff.suspended,
            merchant_returning=self._merchant_departure(map_name),
            # The tracked SP_ZENY balance (0x00B1 param 20, pinned rathena
            # src/map/map.hpp:501) is the authority; the shop-context balance
            # is the fallback inside the shop loop and the runner-side seed
            # stands in for the login wallet the wire never delivers (leg 43:
            # state.zeny was None all window and the buy could never arm).
            zeny=self._zeny_balance(view),
            zeny_receipt=self._shop_context.currency,
            capacity_receipt=self._capacity.receipt,
            weight=self._capacity.weight_count,
            max_weight=self._capacity.max_weight_count,
            received_stats=_received_stats(view.stats),
            inventory_known=view.inventory_known,
            inventory_slots=self._server_slot_allowance(),
            server_self_slots=self._server_self_slots,
            alive_known=self._life(view) is not None,
            alive=self._life(view),
            native_epoch=wire.native_epoch,
            progression_source=progression.base_source,
            recent_encounters=self._encounters.records if self._encounters is not None else (),
        )
        self._last_built_state = state
        self._merchant_staging.observe(state)
        self._merchant_crossings.observe(map_name, state.name)
        self._drain_retry_talk(state)
        return state

    def _drain_retry_talk(self, state: BotState) -> None:
        """One deferred click: the walk-end tail dropped the first, so the
        scripts' talk-once latch must not hold on an unsent 0x0090."""
        if self._retry_talk is None or self._standing is not True:
            return
        npc_id, self._retry_talk = self._retry_talk, None
        self._talk_npc(state, npc_id)

    def _validate_npc_context(
        self, view: NativeGameplayView, map_name: str, pos: ObservedPosition
    ) -> None:
        dialog = self._npc.view
        if dialog is None:
            return
        actor = observed_npc(view, dialog.npc_id)
        if (
            (
                self._life(view) is not True
                or dialog.map_name != map_name
                or dialog.epoch != self._epoch
                or actor is None
            )
            or actor.walking
            or math.hypot(actor.position.x - pos.x, actor.position.y - pos.y) > 3
        ):
            self._npc.invalidate()

    def _map_identity(self, wire_name: str) -> str:
        """Derive a cache key, retaining the literal name in the received view.

        Pinned mapindex.cpp43-69/clif.cpp2159 append the .gat wire suffix.
        Only a derived identity present in this world's cache is usable.
        """
        if self.cache is None:
            return wire_name
        key = wire_name[:-4] if wire_name.endswith(".gat") else wire_name
        if key not in self.cache.maps:
            message = "received map has no public cache identity"
            raise NativeTelemetryUnavailable(message)
        return key

    def _merchant_departure(self, map_name: str) -> bool:
        """Retain the released visit through its return route, then forget it."""
        if map_name not in MERCHANT_ROUTE_RETURN:
            self._merchant_returning = False
        return self._merchant_returning

    def _init_merchant_navigation(self) -> None:
        self._merchant_staging = MerchantStaging()
        self._merchant_crossings = MerchantWarpCrossings()
        self.last_move_outcome: dict[str, object] = {}
        self._move_pending_release: dict[str, object] = {}
        self._merchant_paths: dict[tuple[str, tuple[int, int], tuple[int, int]], bool] = {}
        self._merchant_travel_rerolls: dict[tuple[str, tuple[int, int]], tuple[int, int] | None] = (
            {}
        )
        self._merchant_travel_holds: set[tuple[str, tuple[int, int]]] = set()

    @property
    def merchant_warp_crossings(self) -> int:
        return self._merchant_crossings.count

    def merchant_reachable(
        self, map_name: str, position: tuple[int, int], cell: tuple[int, int]
    ) -> bool | None:
        """Runtime authority for dealer approaches: a walkable cell WITH a path.

        Use the move primitive's no-corner-cutting path contract, memoized
        for this native-state tick. Known NoRoute vetoes authoring; absent
        geometry keeps the script's existing fail-open choice.
        """
        if self.cache is None:
            return None
        if map_name not in self.cache.maps:
            return None
        grid = self.cache.get(map_name)
        if not grid.walkable(cell):
            return False
        key = (map_name, position, cell)
        if key not in self._merchant_paths:
            try:
                shortest_path(grid, position, cell)
            except NoRoute:
                self._merchant_paths[key] = False
            else:
                self._merchant_paths[key] = True
        return self._merchant_paths[key]

    def merchant_travel_target(
        self, map_name: str, position: tuple[int, int], cell: tuple[int, int]
    ) -> tuple[int, int] | None:
        """Validate each authored merchant travel leg before movement (leg 79).

        Like _move_reroll, search the nearest walkable neighbors ONCE per
        (map, destination), but require the counter's shortest_path authority
        too. Memoize failure as well as success; native-state ticks and walks
        must not re-arm a dead destination. Missing geometry retains the
        script's existing choice. No grid cells are invented or corrected.
        """
        if (map_name, cell) in (
            ("prontera", MERCHANT_ROUTE["prontera"]),
            ("prt_in", MERCHANT_ROUTE["prt_in"]),
        ):
            return self._staging_travel_target(map_name, position, cell)
        self._merchant_staging.release()
        return self._validated_travel_target(map_name, position, cell)

    def _staging_travel_target(
        self, map_name: str, position: tuple[int, int], cell: tuple[int, int]
    ) -> tuple[int, int] | None:
        state = self.last_built_state
        if (
            state is not None
            and (state.map_name, state.x, state.y) == (map_name, *position)
            and self.cache is not None
            and map_name in self.cache.maps
        ):
            grid = self.cache.get(map_name)
            if map_name == "prt_in":
                return self._merchant_staging.dealer_target(
                    grid, state, own_id=self.wire.aid, bodies=self._dealer_bodies()
                )
            return self._merchant_staging.target(grid, state, self._now())
        if map_name == "prt_in":
            return (
                _approach_cell(*cell, state, reachable=self.merchant_reachable)
                if state is not None and (state.map_name, state.x, state.y) == (map_name, *position)
                else None
            )
        return self._validated_travel_target(map_name, position, cell)

    def _validated_travel_target(
        self, map_name: str, position: tuple[int, int], cell: tuple[int, int]
    ) -> tuple[int, int] | None:
        key = (map_name, cell)
        if key not in self._merchant_travel_rerolls:
            if self.merchant_reachable(map_name, position, cell) is not False:
                return cell
            self._merchant_travel_rerolls[key] = self._merchant_travel_neighbor(
                map_name, position, cell
            )
        target = self._merchant_travel_rerolls[key]
        if target is not None and self.merchant_reachable(map_name, position, target) is True:
            return target
        if key not in self._merchant_travel_holds:
            self._merchant_travel_holds.add(key)
            reason = (
                "unwalkable"
                if self.cache is not None and not self.cache.get(map_name).walkable(cell)
                else "unreachable"
            )
            logger.warning(
                "merchant-drive: hold travel dest %s (%s,%s) map=%s; no reachable neighbor",
                reason,
                *cell,
                map_name,
            )
        return None

    def _merchant_travel_neighbor(
        self, map_name: str, position: tuple[int, int], cell: tuple[int, int]
    ) -> tuple[int, int] | None:
        if self.cache is None:
            return None
        grid = self.cache.get(map_name)
        excluded = {position, cell}
        while (candidate := nearest_walkable(grid, cell, exclude=excluded)) is not None:
            if self.merchant_reachable(map_name, position, candidate) is True:
                return candidate
            excluded.add(candidate)
        return None

    def _dispatch_shop_action(self, action: GameAction) -> bool:
        """The shop actions; True = dispatched."""
        if isinstance(action, NpcShopPurchase):
            self._dispatch_purchase(action)
            return True
        if isinstance(action, NpcShopBuySelection):
            self._select_shop_buy(action)
            return True
        if isinstance(action, NpcShopSellOpen):
            self._send_sell_open(action)
            return True
        if isinstance(action, NpcShopSell):
            self._send_sell(action)
            return True
        if isinstance(action, NpcRespond):
            self._respond_npc(action)
            return True
        return False

    def perform_native(self, action: GameAction) -> None:
        if isinstance(action, MoveTo):
            # Reset BEFORE the dialogue intercepts: never reuse a prior dispatch.
            self.last_move_outcome = {"outcome": "refused", "reason": "npc_intercepted"}
        shop = self._dispatch_shop_action(action)
        if shop:
            return
        if self._dispatch_timeout_close(action):
            return
        if self._retry_blocked_dialogue():
            return
        state = self.build_native_state(Goal.GRIND)
        if self._npc_action(state, action):
            return
        self._equip_progression(state)
        self._stat_progression(state)
        match action:
            case Attack(target_id=target):
                self._attack(state, target)
            case Loot():
                self._loot(state)
            case MoveTo(x=x, y=y):
                # Close a server-open NPC deal BEFORE moving: walks sent while
                # a deal is open are ignored by the server (fx0's shop trap).
                # Movement-only scope: NPC-interaction actions keep their deals.
                self._close_open_npc_dialog(state)
                self._perform_move(state, (x, y))
            case _:
                self._social(state, action)

    def _close_open_npc_dialog(self, state: BotState) -> None:  # noqa: ARG002 (seam symmetry)
        """Close a server-open NPC deal before moving (fx0's shop trap).

        Walks sent while an NPC deal is open are ignored by the server
        (npc-interactive state): windows 43-49 logged a bot sending walk
        after walk from the prt_in shop interior with the dealer dialog
        open. The received 0x00b4/0x00b5/0x00b7 frames open the tracker's
        dialog marker; CZ_CLOSE_DIALOG 0x00b9 (clif_parse_NpcCloseClick,
        <HII npc id) closes it, mirrored to the tracker immediately (the
        send is the only close authority in this epoch).
        """
        tracker = self._tracker
        if tracker is None:
            return
        dialog = tracker.npc_dialog_open
        if dialog is None:
            return
        self.wire._send(npc_close(dialog.npc_id))
        tracker.clear_npc_dialog()

    def _dispatch_timeout_close(self, action: GameAction) -> bool:
        if not isinstance(action, NpcClose) or not self._npc.failed:
            return False
        return self._close_timeout_dialogue(self.build_native_state(Goal.GRIND), action)

    def _close_timeout_dialogue(self, state: BotState, action: GameAction) -> bool:
        """One honest close before retry interception; poison and live offers hold."""
        dialog = self._npc.view
        if not (
            isinstance(action, NpcClose)
            and dialog is not None
            and action.npc_id == dialog.npc_id
            and self._timeout_close_ready(state)
        ):
            return False
        self._send_npc(struct.pack("<HI", 0x146, dialog.npc_id))
        if self._tracker is not None:
            self._tracker.clear_npc_dialog()
        self._shop_context.invalidate_offer("timeout-close")
        self._npc.complete_shop()
        self._retry_talk = None
        self._shop_selection = None
        self._merchant_returning = merchant_admission_refusal(state) is not None
        if not self._merchant_returning:
            self._merchant_reopen = dialog.npc_id
        return True

    def _timeout_close_ready(self, state: BotState) -> bool:
        return all(
            (
                self._npc.failed,
                self._npc.deny_origin == "timeout",
                not self._npc.cancel_uncertain,
                self._shop_context.offer is None,
                state.alive is True,
                self._standing is True,
                self._pending is None,
            )
        )

    def _retry_blocked_dialogue(self) -> bool:
        """A denied dialogue owns dispatch; only timeout may start a fresh round."""
        if not self._npc.failed or self._npc.view is None:
            return False
        self._retry_timeout_dialogue(self._now())
        return True

    def _retry_timeout_dialogue(self, now: float) -> None:
        """Three paced attempts per five-minute epoch, shared by both paths.

        A bound offer survives its dialogue timeout. Poison/cancel uncertainty
        never spends or rearms a retry, regardless of elapsed time.
        """
        view = self._npc.view
        if (
            view is None
            or not self._npc.failed
            or self._npc.deny_origin != "timeout"
            or self._npc.cancel_uncertain
            or self._shop_context.offer is not None
        ):
            return
        if not self._take_npc_retry(now):
            return
        raw = self._npc.begin(
            view.npc_id,
            self.wire.native_epoch,
            view.map_name,
            self._metadata_cursor,
            now,
        )
        self._send_npc(raw)

    def _take_npc_retry(self, now: float) -> bool:
        """Share pacing and epoch limits across timeout retries and closed contacts."""
        if not _finite_npc_time(now):
            return False
        started = self._npc_retry_epoch_at
        if started is None:
            self._npc_retry_epoch_at = now
        elif now >= started + NPC_RETRY_EPOCH_S:
            self._npc_retry_epoch_at = now
            self._npc_retries = NPC_RETRY_BUDGET
        if self._npc_retries <= 0 or now < self._npc_retry_at:
            return False
        self._npc_retries -= 1
        self._npc_retry_at = now + NPC_RETRY_CADENCE_S
        return True

    def _note_attack_gate(self, reason: str) -> None:
        """Bounded gate-reason telemetry: WHY an authored Attack sent nothing.

        Leg 33: 516 approaches produced 6 swings and the receipt could not
        name the drop. Mirrors `_note_move_gate` (w58): the reasons ride the
        client for the runner sample to lift into the receipt.
        """
        reasons = getattr(self, "_attack_gate_reasons", None)
        if reasons is None:
            reasons = deque(maxlen=64)
            self._attack_gate_reasons = reasons
        reasons.append((self._now(), reason))

    def _attack(self, state: BotState, target: int) -> None:
        if state.alive is not True:
            self._note_attack_gate("dead")
            return
        if self._pending is not None:
            self._note_attack_gate("pending_walk")
            return
        if not any(actor.id == target for actor in state.nearby_monsters):
            self._note_attack_gate("target_not_visible")
            return
        if self._rest_seq is not None:
            self._note_attack_gate("resting")
            return
        if not self._attack_ready():
            self._note_attack_gate("cooldown")
            return
        self.wire._send(attack(target))

    def _equip_progression(self, state: BotState) -> None:
        """Wear an owned wanted weapon once per epoch (equip progression rule).

        The rule itself is scripts.novice_weapon_index (pure, tested). Sends
        ride this dispatch seam because the GameAction union in
        domain/actions.py is outside this slice's owned files. Bounded
        no-ack retries: several clif_parse_EquipItem/pc_equipitem paths
        return without any ack (dead: clif.cpp:12117-12121; npc-blocked:
        clif.cpp:12127-12130; already-worn item: pc.cpp:12056-12063), so an
        absent ack is not a server verdict — cap attempts per index per
        epoch and leave worn unknown afterwards (the received 0x0999 ack is
        the only success authority).
        """
        tracker = self._tracker
        if tracker is None or state.alive is False or self._npc.actuation_blocked:
            return
        index = novice_weapon_index(tracker.indexed_inventory, tracker.view.worn, job=state.job)
        if index is None or self._equip_attempts.get(index, 0) >= _EQUIP_ATTEMPT_CAP:
            return
        self._equip_attempts[index] = self._equip_attempts.get(index, 0) + 1
        self.wire._send(equip(index))

    def _stat_progression(self, state: BotState) -> None:
        """Spend unallocated status points per the novice stat plan.

        Reads the tracker's stat observation (status points, six stat values,
        the 0x00BC ack tail); sends at most one batch of CZ_STATUS_CHANGE
        (8 one-point spends) per dispatch, paced on received acks; never
        re-spends a stat whose spend ack failed this epoch.
        """
        tracker = self._tracker
        if tracker is None or state.alive is False or self._npc.actuation_blocked:
            return
        view = tracker.view
        if not self._stat_setup_ready(view):
            return
        self._absorb_stat_acks(view)
        if self._stat_unacked >= _STAT_BATCH_CAP:
            return
        self._dispatch_next_stat_leg(view)

    def _stat_setup_ready(self, view: Any) -> bool:
        points = view.status_points
        return points is not None and points > 0 and view.stats is not None

    def _absorb_stat_acks(self, view: Any) -> None:
        acks_seen = len(view.stat_acks)
        for ack in view.stat_acks[self._stat_acks_seen : acks_seen]:
            if not ack.ok:
                self._stat_failed.add(ack.stat_id)
        self._stat_unacked = max(0, self._stat_unacked - (acks_seen - self._stat_acks_seen))
        self._stat_acks_seen = acks_seen

    def _dispatch_next_stat_leg(self, view: Any) -> None:
        stats = view.stats
        remaining = view.status_points or 0
        for stat_id, target in NOVICE_STAT_TARGETS.items():
            index = stat_id - 13
            current = stats[index]
            if current >= target or stat_id in self._stat_failed:
                continue
            budget = min(_STAT_BATCH_CAP - self._stat_unacked, target - current)
            self._spend_status_batch(stat_id, current, budget, remaining)
            return  # one stat leg per dispatch, sidecar order

    def _spend_status_batch(self, stat_id: int, current: int, budget: int, points: int) -> None:
        """One sidecar leg: at most ``budget`` one-point spends while affordable."""
        for _ in range(budget):
            cost = 1 + (current + 9) // 10
            if points < cost:
                return
            self.wire._send(struct.pack("<HHB", 0x00BB, stat_id, 1))
            points -= cost
            self._stat_unacked += 1
            current += 1

    def _npc_action(self, state: BotState, action: GameAction) -> bool:
        if self._npc.actuation_blocked and isinstance(action, (Attack, Loot, MoveTo, TalkToNpc)):
            return True
        if isinstance(action, TalkToNpc):
            self._retry_talk = None  # the fresh scripted intent replaces the retry
            self._talk_npc(state, action.npc_id)
            return True
        if not isinstance(action, (NpcNext, NpcSelect, NpcClose, NpcSubmitName)):
            return False
        if state.alive is True and self._standing is True and self._npc_motion_ready():
            raw = self._npc.request(action, self._now(), self.wire.char_name)
            if raw is not None:
                self._send_npc(raw)
        return True

    def bind_shop_purchase_facts(self, facts: QualifiedShopItem) -> bool:
        """Explicit trusted injection only; no loader or live fact inference."""
        return self._purchase.bind(facts, self._purchase_admission(self._now()))

    def _qualify_knife_facts(self, context: PurchaseAdmission) -> QualifiedShopItem | None:
        """The operator's item-level facts for the pinned novice knife, bound to
        the CURRENT received exchange.

        The operator template supplies what the wire cannot carry reliably:
        the item identity (1201, the pinned rathena
        db/pre-re/item_db_equip.yml:2262-2265 Knife, ordinary non-stackable
        weapon, Weight 400). The price/discount qualify FROM THE RECEIVED
        exchange's own row — the C6 is the trusted bound offer, and
        native_purchase._eligible re-checks the facts against that same row,
        so a template price would have to equal it anyway (leg 47: the dealer's
        received price is the exchange's, not the db's Buy column). The session
        fields copy the CURRENT admission; a stale exchange denies at bind.
        """
        offer = context.offer
        now = context.now
        if offer is None or not _finite_npc_time(now):
            return None
        rows = tuple(r for r in offer.rows if r.item_id == 1201)
        if len(rows) != 1:
            return None
        return QualifiedShopItem(
            source_id="rathena-item-db-pin-20180704:1201",
            account_id=context.account_id,
            character_id=context.character_id,
            epoch=offer.epoch,
            npc_id=offer.npc_id,
            map_name=offer.map_name,
            actual_item_id=1201,
            client_item_id=1201,
            loaded_weight=400,
            ordinary_shop=True,
            nonstackable=True,
            stable_price=rows[0].price,
            stable_discount_price=rows[0].discount_price,
            valid_until=now + 300.0,
        )

    def npc_shop_purchase(self, *, maximum_zeny: int = 0) -> NpcShopPurchase | None:
        """Mint one finite owner intent; default budget grants no expenditure."""
        return self._purchase.mint(self._purchase_admission(self._now()), maximum_zeny)

    def shop_purchase_progress(self) -> ShopPurchaseProgress | None:
        context = self._purchase_admission(self._now())
        self._purchase.check(context)
        return self._purchase.progress

    def _purchase_owner(self) -> tuple[object, ...]:
        return (*self._received_owner(), self._npc)

    def _purchase_admission(self, now: float) -> PurchaseAdmission | None:
        if not _finite_npc_time(now) or now < 0:
            return None
        try:
            view = self._planning_npc_view(now)
        except NativeTelemetryUnavailable:
            return None
        if not self._npc_self_ready(view, self._epoch_character, self._epoch):
            return None
        return self._purchase_snapshot(now, self._tracker)

    def _purchase_snapshot(
        self, now: float, tracker: NativeGameplayTracker | None
    ) -> PurchaseAdmission | None:
        offer = self._shop_context.offer
        if offer is None or tracker is None or self._npc.requests >= 32:
            return None
        currency = self._shop_context.currency
        if currency is None:
            # the wallet-parity seed (2743782a) IS the operator's DB-backed
            # ground truth (the fixture char.zeny); the wire delivers SP_ZENY
            # on changes only, so a fresh login has no receipt to spend
            # against — arm the admission's receipt from the SAME authority
            # chain the state reports, marked as the runner seed, fresh now
            seeded = self._zeny_balance(tracker.view)
            if seeded is not None and type(self._epoch) is int:
                currency = ReceivedZeny(
                    seeded, self._epoch, 0, now, source_binding="runner-seed-char-zeny"
                )
        return PurchaseAdmission(
            self._purchase_owner(),
            offer,
            currency,
            self._capacity.receipt,
            tracker.indexed_inventory,
            self._server_slot_allowance(),
            self.wire.aid,
            self.wire.gid,
            now,
        )

    def _dispatch_purchase(self, action: NpcShopPurchase) -> None:
        raw = self._purchase.prepare(action, self._purchase_admission(self._now()))
        if raw is None:
            return
        _, base, frames = self.wire.native_frame_snapshot()
        after = frames[-1][0] if frames else base
        self._purchase.sending(after)
        self._npc.requests += 1
        self._send_npc(raw)
        self._purchase.issued(after)

    def npc_shop_buy_selection(self) -> NpcShopBuySelection | None:
        """Mint on the owner from current received C4; no planner capability or send."""
        dialog = self._shop_dialogue(self._now())
        if dialog is None:
            return None
        action = NpcShopBuySelection(
            dialog.npc_id, dialog.epoch, dialog.sequence, dialog.map_name, dialog.opened_sequence
        )
        self._shop_selection = (
            action,
            NpcHostBinding(self, self.wire, self._planning_session),
            self.wire.sock,
            self._npc,
            self.wire.rx_thread,
        )
        return action

    def _select_shop_buy(self, action: NpcShopBuySelection) -> None:
        binding, self._shop_selection = self._shop_selection, None
        if binding is None:
            return
        issued, owner, sock, controller, reader = binding
        if not all(
            (
                issued is action,
                owner.matches(self, self.wire, self._planning_session),
                sock is self.wire.sock,
                controller is self._npc,
                reader is self.wire.rx_thread,
            )
        ):
            return
        now = self._now()
        if self._shop_dialogue(now) is None:
            return
        raw = self._npc.request(action, now)
        if raw is None:
            # e2e-45 diagnostic tap: the C5 never sent - name the drop
            logger.warning(
                "shop-debug: buy selection request returned None"
                " (stage=%s requests=%d deadline=%s now=%.2f)",
                self._npc.view.stage if self._npc.view is not None else None,
                self._npc.requests,
                self._npc.deadline,
                now,
            )
        if raw is not None:
            self._shop_context.invalidate_offer("selection-sent")
            _, base, frames = self.wire.native_frame_snapshot()
            after = frames[-1][0] if frames else base
            self._send_npc(raw)
            self._shop_context.issued(
                action, after, now, min(self._npc.deadline, self._npc.absolute_deadline)
            )

    def _sell_binding(self) -> tuple[object, ...]:
        """Same owner-local references the other shop mints bind against."""
        return (
            self,
            self.wire,
            self._planning_session,
            self.wire.sock,
            self._npc,
            self.wire.rx_thread,
        )

    def _sell_owner_ok(self, binding: tuple[object, ...] | None) -> bool:
        if binding is None:
            return False
        return all(a is b for a, b in zip(binding, self._sell_binding(), strict=True))

    def _sell_actuation_ready(self, view: NativeGameplayView) -> bool:
        return all(
            (
                self._life(view) is True,
                self._standing is True,
                self._stand_pending is None,
                self._rest_seq is None,
            )
        )

    def _shop_loop_mechanical(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...] | None:
        """Deterministic received-shop continuation (window-28 loop rule).

        Priority: sell the received C7 rows while stock lasts; mint the
        owner-bound buy through the existing purchase path when the received
        offer has an affordable wanted weapon; otherwise point the received
        dealtype dialog at sell (sellable stock) or buy. Sellability and
        prices come from received frames only (clif.cpp:2265-2280,
        12333-12361). Without a shop context this returns None and the prior
        behavior applies unchanged.
        """
        tracker = self._tracker
        if tracker is None:
            return None
        action = self._shop_loop_action(state, actions, tracker)
        if action is None:
            return None
        if isinstance(action, NpcShopSell):
            self._sell_mint = (action, self._sell_binding())
        elif isinstance(action, NpcShopSellOpen):
            self._sell_open_mint = (action, self._sell_binding())
        return (action,)

    def _shop_loop_action(
        self, state: BotState, actions: tuple[GameAction, ...], tracker: NativeGameplayTracker
    ) -> GameAction | None:
        if any(
            isinstance(action, (NpcShopPurchase, NpcShopBuySelection, NpcShopSell, NpcShopSellOpen))
            for action in actions
        ):
            return None
        skip = self._mint_skip_term(state)
        if skip is not None:
            self._note_mint_skip(state, skip)
            return None
        sell_action = self._pending_sell(tracker)
        if sell_action is not None:
            return sell_action
        if self._give_up_stock_blocked_buy(tracker):
            return None
        purchase = self._buy_mint_attempt(tracker)
        if purchase is not None:
            return purchase[0]
        return self._sell_open_action(tracker) or self._buy_open_action()

    def _current_buy_offer(self) -> ReceivedShopOffer | None:
        offer = self._shop_context.offer
        if offer is None or not self._buy_backoff.current(offer, self._npc.view, self._epoch):
            return None
        return offer

    def _give_up_stock_blocked_buy(self, tracker: NativeGameplayTracker) -> bool:
        offer = self._current_buy_offer()
        if offer is None:
            return False
        refusal = self._buy_backoff.evaluate(offer, tracker.indexed_inventory is not None)
        if refusal is None:
            return False
        reason, first = refusal
        if first:
            logger.warning(
                "merchant-drive: buy give-up %s (map=%s dealer=%s item=1201 offer_item_ids=%s)",
                reason,
                offer.map_name,
                offer.npc_id,
                [row.item_id for row in offer.rows[:8]],
            )
        # The pinned close is CZ_CLOSE_DIALOG 0146, as in NativeNpcDialogue's
        # close request encoder. Send first: a failed close must keep the barrier.
        self._send_npc(struct.pack("<HI", 0x146, offer.npc_id))
        tracker.clear_npc_dialog()
        self._shop_context.invalidate_offer("buy-give-up")
        self._npc.complete_shop()
        self._retry_talk = None
        self._shop_selection = None
        return True

    def _mint_skip_term(self, state: BotState) -> str | None:
        """The mint precondition's failing term, named for the tap. Leg 55:
        the post-C6 _deny('timeout') set _npc.failed ~15s after every bind
        and gated the decide-paced mint for the offer's whole TTL. The
        dialogue denial is a NORMAL clock-expiry artifact while the deal
        lives server-side: the failed term is held off the mint while the
        shop CONTEXT still carries the received offer - but ONLY the innocent
        timeout origin (the deny_origin='timeout' retryable contract, legs
        23-24); the poison denials and any offer-less dialogue still block."""
        if state.alive is not True:
            return "alive"
        if self._npc.cancel_uncertain:
            return "cancel_uncertain"
        if self._npc.failed and not self._timeout_denial_with_live_offer():
            return "npc_failed"
        return None

    def _timeout_denial_with_live_offer(self) -> bool:
        """The one held-off shape: the failed dialogue's innocent timeout
        (deny_origin='timeout', the legs 23-24 retryable origin) does not
        gate the mint while the shop CONTEXT still holds the received offer.
        The poison denials (malformed, send-failure) and the offer-less
        dialogue keep the barrier complete."""
        return self._npc.deny_origin == "timeout" and self._shop_context.offer is not None

    def _note_mint_skip(self, state: BotState, term: str) -> None:
        """Mint-path tap (tap-before-fix doctrine): name the gate that skipped
        the shop loop's mint with every term's value, so the next leg can name
        any remaining gate. Bounded to the mint window (a bound offer -
        without one no mint was pending); fails open, never behavior."""
        if self._shop_context.offer is None:
            if self._npc.view is not None:
                self._note_buy_open_hold(term)
            return
        logger.warning(
            "shop-debug: mint skipped by %s (alive=%r npc_failed=%s"
            " deny_origin=%s cancel_uncertain=%s offer_bound=%s)",
            term,
            state.alive,
            self._npc.failed,
            self._npc.deny_origin,
            self._npc.cancel_uncertain,
            self._shop_context.offer is not None,
        )

    def _pending_sell(self, tracker: NativeGameplayTracker) -> NpcShopSell | None:
        lists = tracker.view.sell_lists
        if not lists:
            return None
        latest = lists[-1]
        # LAW 3: a C7 binds to its epoch. The sell list must postdate the
        # CURRENT dialogue's click (opened_sequence is the cursor the click
        # armed): a C7 received under a previous dialogue never authorises a
        # sell here — the recovery re-click opens a fresh epoch instead.
        dialog = self._npc.view
        if dialog is None or latest.seq <= dialog.opened_sequence:
            return None
        if not latest.rows or latest.seq in self._sell_sent:
            return None
        stock = tracker.indexed_inventory
        if stock is None or tracker.view.map_name is None or type(self._epoch) is not int:
            return None
        entries = shop_sell_entries(latest.rows, stock)
        if not entries:
            return None
        return NpcShopSell(None, self._epoch, tracker.view.map_name, latest.seq, entries)

    def _buy_mint_attempt(self, tracker: NativeGameplayTracker) -> tuple[GameAction, ...] | None:
        offer = self._shop_context.offer
        if offer is None:
            return None
        # the SAME balance authority chain the state reports: tracked wire >
        # shop receipt > the runner-side seed. Reading the shop context alone
        # starved the mint on a fresh login (the wire delivers SP_ZENY on
        # changes only — leg 47: the C6 bound, the purchase never minted).
        zeny = self._zeny_balance(tracker.view)
        rows = tuple((r.price, r.discount_price, r.item_type, r.item_id) for r in offer.rows)
        if shop_affordable_weapon(rows, zeny) is None:
            return None
        # the purchase machine's facts: the first live qualification binds the
        # operator's knife template to the CURRENT exchange (native_purchase
        # refuses to mint on unbound facts — the trusted-injection law)
        admission = self._purchase_admission(self._now())
        if admission is not None and not self._purchase.has_facts:
            facts = self._qualify_knife_facts(admission)
            if facts is not None:
                self.bind_shop_purchase_facts(facts)
        action = self.npc_shop_purchase(maximum_zeny=zeny if zeny is not None else 0)
        return None if action is None else (action,)

    def _sell_open_action(self, tracker: NativeGameplayTracker) -> NpcShopSellOpen | None:
        dialog = self._npc.view
        if dialog is None or dialog.stage != "unsupported_shop":
            return None
        if (dialog.opened_sequence, dialog.sequence) in (
            self._sell_open_issued,
            self._buy_open_issued,
        ):
            return None
        if shop_sellable_stock(tracker.view.inventory_counts) <= 0:
            return None
        # The epoch latches at the MINT, not after the send guard: a guard
        # failure (no adjacency, no arrival proof) must not re-mint the same
        # epoch's open every tick (leg 28: 32 opens). A fresh received C4 is
        # a fresh epoch and mints again.
        self._sell_open_issued = (dialog.opened_sequence, dialog.sequence)
        return NpcShopSellOpen(
            dialog.npc_id,
            dialog.epoch,
            dialog.sequence,
            dialog.map_name,
            dialog.opened_sequence,
        )

    def _buy_open_action(self) -> NpcShopBuySelection | None:
        dialog = self._npc.view
        if dialog is None:
            return None
        if dialog.stage != "unsupported_shop":
            self._note_buy_open_hold("stage")
            return None
        if (dialog.opened_sequence, dialog.sequence) in (
            self._buy_open_issued,
            self._sell_open_issued,
        ):
            self._note_buy_open_hold("open_issued")
            return None
        selection = self.npc_shop_buy_selection()
        if selection is not None:
            self._buy_open_issued = (dialog.opened_sequence, dialog.sequence)
        return selection

    def _dealer_adjacent(self, tracker: NativeGameplayTracker, npc_id: int) -> bool:
        """Tracked adjacency to the RECEIVED dealer — never the walk-arrival
        flag (it stays False after every real walk; gating the shop limb on
        it is what kept leg 28's 32 sell-opens from ever sending). Same
        contract e06dc511 gave the click path. Fail closed: no received
        dealer or out of range reads as not adjacent."""
        dealer = observed_npc(tracker.view, npc_id)
        if dealer is None or dealer.position is None or tracker.view.position is None:
            return False
        return (
            math.hypot(
                dealer.position.x - tracker.view.position.x,
                dealer.position.y - tracker.view.position.y,
            )
            <= 3
        )

    def _send_sell_open(self, action: NpcShopSellOpen) -> None:
        mint = self._sell_open_mint
        self._sell_open_mint = None
        if mint is None or mint[0] is not action or not self._sell_owner_ok(mint[1]):
            return
        tracker = self._tracker
        dialog = self._npc.view
        if tracker is None or dialog is None:
            return
        if not self._sell_open_request_ready(action, tracker, dialog):
            return
        if not self._dealer_adjacent(tracker, action.npc_id):
            return
        self._npc.requests += 1
        self._send_npc(sell_open(action.npc_id))

    def _sell_open_request_ready(
        self, action: NpcShopSellOpen, tracker: NativeGameplayTracker, dialog: NpcDialogue
    ) -> bool:
        """All local guards for one bounded 0xc5 type-1 against the received dialog."""
        fields_match = (
            dialog.npc_id == action.npc_id
            and dialog.epoch == action.epoch
            and dialog.sequence == action.prompt_sequence
            and dialog.map_name == action.map_name
            and dialog.opened_sequence == action.opened_sequence
        )
        return all(
            (
                self._npc.requests < 32,
                self._sell_actuation_ready(tracker.view),
                dialog.stage == "unsupported_shop",
                fields_match,
            )
        )

    def _send_sell(self, action: NpcShopSell) -> None:
        """Echo the received C7 indices back as one bounded CZ 0xc9 request.

        The server re-verifies stock, proximity and sellability (npc.cpp
        3040-3083) and always answers 0xcb; the received sell list, not the
        mint, stays the only send authority, and one request is sent per
        received receipt.
        """
        mint = self._sell_mint
        self._sell_mint = None
        if mint is None or mint[0] is not action or not self._sell_owner_ok(mint[1]):
            return
        tracker = self._tracker
        if tracker is None or self._sell_request_target(action, tracker) is not True:
            return
        self._npc.requests += 1
        self._sell_sent.append(action.sell_sequence)
        dialog = self._npc.view
        _, base, frames = self.wire.native_frame_snapshot()
        after = frames[-1][0] if frames else base
        self._send_npc(sell(action.sales))
        if dialog is not None:
            self._sell_pending = (action, dialog, after)

    def _consume_sell_result(self, frame: tuple[int, float, int, bytes]) -> None:
        """Only a successful, sent sale in the current round releases its UI.

        C7 is an offer and C9 is a request; neither proves completion. The
        validated CB result does, even if the dialogue clock expired while
        it was in flight. Poison/cancel barriers and newer rounds still hold.
        """
        pending = self._sell_pending
        seq, _, pid, raw = frame
        if pid != 0x00CB or pending is None or seq <= pending[2]:
            return
        self._sell_pending = None
        action, sent_dialog, _ = pending
        dialog = self._npc.view
        if dialog is None:
            return
        if all(
            (
                raw[2] == 0,
                dialog.epoch == action.epoch,
                dialog.map_name == self._map_identity(action.map_name),
                dialog.npc_id == sent_dialog.npc_id,
                dialog.opened_sequence == sent_dialog.opened_sequence,
                dialog.sequence == sent_dialog.sequence,
                not self._npc.cancel_uncertain,
                not self._npc.failed or self._npc.deny_origin == "timeout",
            )
        ):
            self._npc.complete_shop()
            self._merchant_returning = True

    def _sell_request_target(self, action: NpcShopSell, tracker: NativeGameplayTracker) -> bool:
        """All local guards for one bounded 0xc9 against the received receipt."""
        if (
            self._npc.requests >= 32
            or type(self._epoch) is not int
            or self._epoch != action.epoch
            or not self._sell_actuation_ready(tracker.view)
        ):
            return False
        lists = tracker.view.sell_lists
        stock = tracker.indexed_inventory
        if (
            not lists
            or lists[-1].seq != action.sell_sequence
            or stock is None
            or action.sell_sequence in self._sell_sent
        ):
            return False
        return shop_sell_entries(lists[-1].rows, stock) == action.sales

    def _check_shop_context(self, view: NativeGameplayView, now: float) -> None:
        ready = all(
            (
                _finite_npc_time(now),
                self._npc_self_ready(view, self._epoch_character, self._epoch),
                not self._npc.failed,
                not self._npc.cancel_uncertain,
                self._npc.view is not None
                and self._npc.view.map_name == self._planning_npc_map_identity(view),
            )
        )
        # e2e-49: the BOUND-offer lifetime uses a NARROWER predicate than the
        # in-flight `ready` conjunction: identity + self-readiness ONLY, with
        # the exchange-failure and cancel-uncertainty terms (and the clock)
        # excluded. Measured constituents (leg 49 diagnosis): the post-C6
        # resting stage is 'blocked' (the deal waits at a send-less dialogue
        # stage while the shop list is open), the dialogue retry budget then
        # expires -> _npc.failed, and the clock passes the dialogue deadline -
        # ALL while the deal is alive. Killing a bound offer for those terms
        # made the decide-paced mint unreachable (live tap: "C6 BOUND
        # (seq=71 rows=19)" then "offer invalidated (not-ready=True
        # dialog-none=False past-deadline=True)"; the identical signature
        # fires on the motion/sit boundaries via _npc_self_ready, so the
        # conjunction alone cannot discriminate). Self-activity and identity
        # still kill it: they are the real deal-enders.
        context_ok = all(
            (
                _finite_npc_time(now),
                self._npc_self_ready(view, self._epoch_character, self._epoch),
                self._npc.view is not None
                and self._npc.view.map_name == self._planning_npc_map_identity(view),
            )
        )
        self._shop_context.check(self._npc.view, ready, now, context_ok=context_ok)

    def _shop_dialogue(self, now: float) -> NpcDialogue | None:
        clocks = (
            ("now", now),
            ("deadline", self._npc.deadline),
            ("absolute_deadline", self._npc.absolute_deadline),
        )
        for term, value in clocks:
            if not _finite_npc_time(value):
                self._note_buy_open_hold(term)
                return None
        try:
            view = self._planning_npc_view(now)
        except NativeTelemetryUnavailable:
            self._note_buy_open_hold("native_telemetry")
            return None
        dialog = self._npc.view
        if dialog is None:
            self._note_buy_open_hold("dialogue")
            return None
        refusal = self._buy_open_refusal(view, dialog)
        if refusal is not None:
            self._note_buy_open_hold(refusal)
            return None
        return dialog

    def _buy_open_refusal(self, view: NativeGameplayView, dialog: NpcDialogue) -> str | None:
        # C4 precedes C5 and C6: opening needs the current talk and the same
        # received adjacency as sell-open, never an offer or walk-arrival proof.
        # Keep the purchase's stricter received-offer admission unchanged.
        terms = (
            ("character", self.wire.char_name == self._epoch_character),
            ("epoch", self.wire.native_epoch == self._epoch == dialog.epoch),
            ("alive", self._life(view) is True),
            ("standing", self._standing is True),
            ("stand_pending", self._stand_pending is None),
            ("rest", self._rest_seq is None),
            ("pending_walk", self._pending is None),
            ("npc_failed", not self._npc.failed),
            ("cancel_uncertain", not self._npc.cancel_uncertain),
            ("requests", self._npc.requests < 32),
            ("stage", dialog.stage == "unsupported_shop"),
            ("map_identity", dialog.map_name == self._planning_npc_map_identity(view)),
            (
                "dealer_adjacent",
                self._tracker is not None and self._dealer_adjacent(self._tracker, dialog.npc_id),
            ),
        )
        return next((name for name, ready in terms if not ready), None)

    def _note_buy_open_hold(self, term: str) -> None:
        dialog = self._npc.view
        logger.warning(
            "shop-debug: buy-open held by %s (stage=%s dealer=%s requests=%s offer_bound=%s)",
            term,
            dialog.stage if dialog is not None else None,
            dialog.npc_id if dialog is not None else None,
            self._npc.requests,
            self._shop_context.offer is not None,
        )

    def _respond_npc(self, action: NpcRespond) -> None:
        """One host-owner receipt check/request, not atomic server legality.

        Never reenter the unbound dispatcher: a refresh could apply the same
        received index to a different menu. Remote races/rejection remain unknown.
        """
        self._npc_dispatch = LocalNpcDispatch(action, "denied")
        if not _valid_npc_response(action.identity, action.intent):
            return
        observation = self.planning_npc_observation(action.identity)
        if observation is None or not npc_intent_matches(
            action.intent, observation, action.identity, observation.observed_at
        ):
            return
        intent = action.intent
        primitive: NpcNext | NpcSelect
        if intent.operation is NpcOperation.NEXT:
            primitive = NpcNext(observation.npc_id)
        elif intent.option_index is not None:
            primitive = NpcSelect(observation.npc_id, intent.option_index)
        else:
            return
        raw = self._npc.request(primitive, observation.observed_at)
        if raw is not None:
            self._npc_dispatch = LocalNpcDispatch(action, "failed")
            self._send_npc(raw)
            self._npc_dispatch = LocalNpcDispatch(action, "issued")

    def planning_npc_ui(self, identity: PlanningIdentity) -> NpcUiObservation | None:
        """Validated same-session received UI/lease, including expected waiting.

        This does not advertise readiness or manufacture an actionable receipt.
        """
        now = self._now()
        if not all(
            _finite_npc_time(v) for v in (now, self._npc.deadline, self._npc.absolute_deadline)
        ):
            return None
        try:
            view = self._planning_npc_view(now)
        except NativeTelemetryUnavailable:
            return None
        dialog = self._npc.view
        if dialog is None or not self._planning_npc_self_ready(view, identity):
            return None
        return NpcUiObservation(
            dialog,
            now,
            min(self._npc.deadline, self._npc.absolute_deadline),
            self._npc.failed or self._npc.cancel_uncertain,
        )

    def _npc_motion_ready(self) -> bool:
        tracker = self._tracker
        return tracker is not None and tracker.view.arrival_confirmed and self._pending is None

    def _npc_open_ready(self, state: BotState) -> bool:
        return state.alive is True and not self._npc.actuation_blocked and not self._npc.failed

    def _talk_npc(self, state: BotState, npc_id: int) -> None:
        tracker = self._tracker
        if tracker is None or not self._npc_open_ready(state):
            return
        actor = observed_npc(tracker.view, npc_id)
        # The scripts' adjacency gate (DEALER_TALK_RANGE / talk range) is the
        # sufficient in-range proof: tracker arrival_confirmed stays False
        # after every real walk (a moving walkok proves nothing about the
        # destination), so it must not gate the click (the w82 null-offer
        # trace: TalkToNpc dispatched but the 0x0090 never sent).
        if actor is None:
            return
        if actor.walking or not self._attack_ready() or self._rest_seq is not None:
            # The server-side click may land during the walk-end tail
            # (pc_cant_act2) — schedule one retry; the scripts' talk-once
            # latch must not be left holding on a click the server dropped.
            self._retry_talk = npc_id
            return
        self._retry_talk = None
        distance = math.hypot(actor.position.x - state.x, actor.position.y - state.y)
        if distance > 3:
            self._move(state, (actor.position.x, actor.position.y))
        else:
            self._retry_talk = None
            raw = self._npc.begin(
                npc_id, self.wire.native_epoch, state.map_name, self._metadata_cursor, self._now()
            )
            self._send_npc(raw)

    def _send_npc(self, raw: bytes) -> None:
        try:
            self.wire._send(raw)
        except BaseException:
            self._npc.failed = True
            self._npc.deny_origin = "send_failure"
            raise

    def _social_chat(self, state: BotState, action: GameAction) -> bool:
        """The chat limbs; True = handled."""
        match action:
            case PartyChat(text=text):
                if state.in_party:
                    self.wire._send(party_chat(text, speaker_name=self.wire.char_name))
                return True
            case Say(text=text):
                self.wire.say(public_chat_text(text, self.wire.char_name))
                return True
            case _:
                return False

    def _social(self, state: BotState, action: GameAction) -> None:
        if self._social_chat(state, action):
            return
        match action:
            case Rest():
                self._rest(state)
            case AcceptInvite():
                if self.wire.party_invite_pid:
                    self.wire.party_reply(self.wire.party_invite_pid, True)
            case InviteToParty(player=player):
                self._ensure_party_for_invite()
                self.wire.party_invite(player)
            case FoundGuild(name=name):
                self._found_guild(name)
            case GuildInvite(player=player):
                self._invite_to_guild(player)
            case AcceptGuildInvite():
                self._accept_guild_invite()
            case _:
                message = "unsupported native playing action"
                raise ValueError(message)

    def _ensure_party_for_invite(self) -> None:
        """Create the session party once before the first invite.

        rAthena's party_invite requires the INVITER to already lead a party
        (party.cpp:383-386: ``p == nullptr -> return false`` with no
        client-visible reply) and to be its leader (party.cpp:390-395). The
        name is unique per leader-hour so re-runs never hit the
        duplicate-party-name rejection; recreating into an existing party is
        refused by the server with the create-ack and is harmless.
        """
        if getattr(self.wire, "party_created", False):
            return
        bucket = int(time.time()) // 3600
        # ALPHANUMERIC ONLY: the pinned conf sets char_name_option: 1 with
        # char_name_letters = letters/digits/space — a hyphen makes the
        # char-server reject the create (mapif_parse_CreateParty's
        # char_name_letters filter -> result=1; leg 9's zero-party cause).
        self.wire.party_create(f"{self.wire.char_name}p{bucket}")
        self.wire.party_created = True

    def _found_guild(self, name: str) -> None:
        """The charter: one create per session (the re-creates bounce)."""
        if not getattr(self.wire, "guild_created", False):
            self.wire.guild_create(name)
            self.wire.guild_created = True

    def _invite_to_guild(self, player: str) -> None:
        """One invite per member per session; the AID resolves from the roster."""
        invited: set[str] = getattr(self.wire, "guild_invited", set())
        if player in invited:
            return
        members = getattr(self.wire, "party_members", None)
        target = guild_candidate_aid(members, player)
        if target:
            self.wire.guild_invite(target, self.wire.aid, self.wire.gid)
            invited.add(player)
            self.wire.guild_invited = invited

    def _accept_guild_invite(self) -> None:
        """Answer the pending 0x16a prompt with the accept flag."""
        if getattr(self.wire, "guild_invite_gid", 0):
            self.wire.guild_reply(self.wire.guild_invite_gid, True)

    def _loot(self, state: BotState) -> None:
        """The shared pickup dispatch (the mechanical path's Loot and the
        decider's loot choice both land here): the CZ_ITEM_PICKUP send is
        memoized per floor item - one attempt while the item is on the
        floor view - inside the server's pickup radius (Chebyshev<=2; the
        looser hypot gate burned attempts on silent out-of-range rejects)."""
        tracker = self._tracker
        if tracker is None or state.alive is not True:
            self._note_loot_unavailable(tracker)
            return
        floor_items = tracker.view.floor_items
        self._refresh_loot_memo(floor_items)
        threat = self._nearest_active_threat(state)
        if threat is not None:
            # Otto's directive at the send seam: a pickup under an active
            # threat is refused (fail-closed) and the attempt memo is NOT
            # consumed - the item stays lootable once the threat leaves.
            # Leg 67: the refusal is NAMED (the same per-item defer tap the
            # mechanical path carries - the twin gate must not be silent).
            self._note_loot_threat_defer(state, floor_items, threat)
            return
        items = self._loot_candidates(state, floor_items)
        if not items:
            self._loot_receipt.missing()
            return
        for item in items:
            if item.floor_item_id in self._loot_pickup_tried:
                self._note_loot_pickup_held(item.floor_item_id)
                continue
            if self._floor_item_distance(state, item) > _LOOT_PICKUP_RANGE:
                self._loot_receipt.defer(item, "out_of_range")
                self._loot_approach(state, item)
                return
            self._loot_attempt(state, item)
            return

    def _loot_attempt(self, state: BotState, item: ObservedFloorItem) -> None:
        if not self._loot_ready(item):
            return
        self.wire._send(pickup(item.floor_item_id))
        self._loot_pickup_tried.add(item.floor_item_id)
        self._loot_receipt.attempted(
            item,
            self._metadata_cursor,
            context={
                "map": state.map_name,
                "native_epoch": state.native_epoch,
                "x": state.x,
                "y": state.y,
            },
        )
        logger.warning(
            "loot-debug: pickup dispatched (fid=%s nameid=%s cell=(%s,%s))",
            item.floor_item_id,
            item.item_id,
            item.position.x,
            item.position.y,
        )

    def _loot_resume(self, state: BotState) -> None:
        """Continue unattempted intent on received ticks, including retained plans.

        Each approach step needs a fresh received position. Silence cannot
        create unlimited walks; arrival proof still owns the pickup barrier.
        """
        if self._tracker is None:
            return
        self._refresh_loot_memo(self._tracker.view.floor_items)
        if (
            state.alive is not True
            or self._rest_seq is not None
            or self._nearest_active_threat(state) is not None
        ):
            return
        items = self._loot_candidates(state, self._loot_receipt.deferred)
        if not items:
            return
        item = items[0]
        if self._floor_item_distance(state, item) > _LOOT_PICKUP_RANGE:
            self._loot_approach(state, item)
        else:
            self._loot_attempt(state, item)

    def _loot_approach(self, state: BotState, item: ObservedFloorItem) -> None:
        if self._rest_seq is not None or self._pending is not None or self._tracker is None:
            return
        pos = self._tracker.view.position
        if pos is None or pos.seq <= self._loot_approach_seq.get(item.floor_item_id, -1):
            return
        target = self._loot_move_target(state, item)
        if target is not None and self._move(state, target) in (
            "dispatched",
            "occupied_west_rerouted",
        ):
            self._loot_approach_seq[item.floor_item_id] = pos.seq

    def _loot_ready(self, item: ObservedFloorItem) -> bool:
        """Stop-and-swing barrier, plus received arrival and a single ack lane."""
        reason = "resting" if self._rest_seq is not None else None
        if reason is None and not self._require_standing():
            reason = "not_standing"
        if reason is None:
            reason = self._loot_motion_refusal(item)
        if reason is None and self._loot_receipt.pending is not None:
            reason = "awaiting_pickup_ack"
        if reason is not None:
            self._loot_receipt.defer(item, reason)
            return False
        return True

    def _loot_motion_refusal(self, item: ObservedFloorItem) -> str | None:
        view = self._tracker.view if self._tracker is not None else None
        self._loot_release_arrival(view)
        if self._pending is not None:
            return "pending_walk"
        if view is None or not view.arrival_confirmed:
            return self._loot_confirm_arrival(item, view)
        if view.position is None or view.position.seq <= self._loot_motion_seq:
            return "awaiting_walk_arrival"
        return None

    def _loot_release_arrival(self, view: NativeGameplayView | None) -> None:
        if view is None or view.position is None:
            return
        if (
            self._pending is not None
            and view.arrival_confirmed
            and view.position.seq > self._pending[1]
        ):
            self._await_pending(view, view.position)

    def _loot_confirm_arrival(
        self, item: ObservedFloorItem, view: NativeGameplayView | None
    ) -> str:
        """Normal walks have no terminal ack: request the received allocated cell.

        Pinned unit.cpp:187-192 answers an already-reached target with a
        zero-length walkok. Two requests per drop presence, paced by the
        existing pending-walk lifecycle; silence never authorizes pickup.
        """
        if view is None or view.position is None or self._standing is not True:
            return "walking"
        fid = item.floor_item_id
        attempts = self._loot_settle_attempts.get(fid, 0)
        if attempts >= 2:
            return "arrival_confirmation_exhausted"
        pos = view.position
        point = (pos.x, pos.y)
        self._send_walk(point, pos.seq)
        self._loot_settle_attempts[fid] = attempts + 1
        self._pending_origin = "loot_arrival_confirmation"
        self._pending = (point, pos.seq, self._now(), 0)
        return "walking"

    @property
    def loot_telemetry(self) -> tuple[dict[str, object], ...]:
        """Detached cached receipts; never advances wire observation."""
        self._ensure_loot_memos()
        return self._loot_receipt.rows

    def drain_loot_telemetry(self) -> tuple[dict[str, object], ...]:
        self._ensure_loot_memos()
        return self._loot_receipt.drain()

    def _observe_loot_acks(self, view: NativeGameplayView) -> None:
        self._ensure_loot_memos()
        # Expire item fallback before ingesting this ack, including floor ID
        # replacement earlier in the same received snapshot.
        self._refresh_loot_memo(view.floor_items)
        for ack in view.pickup_acks:
            if ack.seq > self._loot_ack_cursor:
                self._loot_receipt.consume(ack)
                self._loot_ack_cursor = ack.seq

    def _reset_loot_epoch(self, reason: str) -> None:
        self._ensure_loot_memos()
        self._loot_receipt.boundary(reason)
        self._refresh_loot_memo(())
        # Map changes retain the tracker's ack tail. Only a new session
        # replaces that tracker and may restart the received sequence.
        if reason == "session_changed":
            self._loot_ack_cursor = 0
        self._loot_motion_seq = -1

    def _rest(self, state: BotState) -> None:
        """pc_setsit stops walk/attack; cancel intent, never invent arrival."""
        if state.alive is not True:
            return
        if self._rest_seq is None:
            self._rest_seq = self._metadata_cursor
        now = self._now()
        if self._standing is False or (self._rest_at is not None and now - self._rest_at < 1):
            return
        self.wire.sit()
        self._rest_at = now
        self._rest_seq = self._metadata_cursor
        self._pending = None
        self._patrol = None

    def planning_npc_observation(self, identity: PlanningIdentity) -> NpcObservation | None:
        """Read on the host owner, without standing/movement recovery or sends.

        Agent/world/ruleset are host metadata, not independently provable from
        this wire. The exact selected name and epoch are checked locally. Ready
        describes known local gates only, never full native/server legality.
        """
        now = self._now()
        if not all(
            _finite_npc_time(value)
            for value in (now, self._npc.deadline, self._npc.absolute_deadline)
        ):
            return None
        try:
            view = self._planning_npc_view(now)
        except NativeTelemetryUnavailable:
            return None
        if not self._planning_npc_self_ready(view, identity):
            return None
        dialog = self._npc.view
        if dialog is None:
            return None
        if not all(
            (
                dialog.stage in ("next", "menu"),
                not self._npc.failed,
                not self._npc.cancel_uncertain,
                self._npc.requests < 32,
                dialog.map_name == self._planning_npc_map_identity(view),
            )
        ):
            return None
        observation = NpcObservation(
            identity,
            dialog.npc_id,
            dialog.epoch,
            dialog.map_name,
            dialog.opened_sequence,
            dialog.sequence,
            dialog.stage,
            tuple(index for index, _ in dialog.options),
            True,
            now,
            min(self._npc.deadline, self._npc.absolute_deadline),
        )
        return observation if observation.eligible(identity, now) else None

    def _planning_npc_map_identity(self, view: NativeGameplayView) -> str | None:
        """Reuse verified cache identity; never rewrite received map spelling."""
        if view.map_name is None:
            return None
        try:
            current = self._map_identity(view.map_name)
            return current if current == self._map_identity(self.wire.map_name) else None
        except NativeTelemetryUnavailable:
            return None

    def _planning_npc_view(self, now: float) -> NativeGameplayView:
        """The state-builder's validation path, without catalog/view publication."""
        view = self._observe(now=now).view
        try:
            require_native_vitals(self.wire.status_params)
            self._progression()
        except NativeTelemetryUnavailable:
            self._invalidate_skills()
            self._shop_context.invalidate()
            raise
        if not view.perception_ready or view.position is None:
            self._shop_context.invalidate()
            message = "native playing position unavailable"
            raise NativeTelemetryUnavailable(message)
        self._validate_received_npc_context(view)
        return view

    def _planning_npc_self_ready(
        self, view: NativeGameplayView, identity: PlanningIdentity
    ) -> bool:
        return self._npc_self_ready(view, identity.character, identity.session_epoch)

    def _npc_self_ready(self, view: NativeGameplayView, character: str, epoch: int | None) -> bool:
        return all(
            (
                self.wire.char_name == character,
                self._epoch_character == character,
                self.wire.native_epoch == epoch,
                self._life(view) is True,
                self._standing is True,
                self._stand_pending is None,
                self._rest_seq is None,
                self._npc_motion_ready(),
            )
        )

    def planning_rest_observation(self) -> RestObservation:
        """Read only on the host owner, after validated native state construction."""
        self._health()
        quartet = tuple(self._received_vitals.get(key) for key in (5, 6, 7, 8))
        vitals = None
        if all(type(value) is int for value in quartet):
            vitals = require_native_vitals(self._received_vitals)
        return RestObservation(
            self.wire.native_epoch,
            self._metadata_cursor,
            self._standing,
            self._pose_seq,
            (vitals.hp, vitals.max_hp, vitals.sp, vitals.max_sp) if vitals else None,
            self._vitals_seq,
            self._planning_arrival_ready(),
        )

    def _planning_arrival_ready(self) -> bool:
        tracker = self._tracker
        if tracker is None or not tracker.view.arrival_confirmed:
            return False
        pos = tracker.view.position
        if pos is None:
            return False
        if self._pending is None:
            return True
        point, seq, _, _ = self._pending
        return pos.seq > seq and (pos.x, pos.y) == point

    def planning_rest_ready(self, after_seq: int) -> bool:
        """Typed REST has its own HP/SP policy; retain pose and arrival barriers."""
        self.build_native_state(Goal.GRIND)
        return self._attack_ready(after_seq=after_seq)

    def recovery_ready(self, *, hp_ratio: float = 0.75) -> bool:
        """Recheck received health before requesting standing or releasing intent."""
        state = self.build_native_state(Goal.GRIND)
        if (
            state.alive is not True
            or state.hp_ratio < hp_ratio
            or not self._attack_ready(after_seq=self._rest_seq)
        ):
            return False
        self._rest_at = None
        self._rest_seq = None
        return True

    def _attack_ready(self, *, after_seq: int | None = None) -> bool:
        tracker = self._tracker
        if (
            tracker is None
            or tracker.view.position is None
            or not self._require_standing(after_seq=after_seq)
        ):
            return False
        return not self._await_pending(tracker.view, tracker.view.position)

    def _note_move_gate(self, reason: str) -> None:
        """Bounded gate-reason telemetry: WHY a scripted MoveTo sent nothing.

        w58: 2500 authored MoveTos per agent produced zero wire sends and the
        receipt could not name the gate. The last reasons ride the client for
        the emission capture to lift into the receipt.
        """
        reasons = getattr(self, "_move_gate_reasons", None)
        if reasons is None:
            reasons = deque(maxlen=8)
            self._move_gate_reasons = reasons
        reasons.append((self._now(), reason))

    def _move_gate(self, state: BotState, target: tuple[int, int]) -> str | None:
        """The blocked-MoveTo reason, or None when the move may proceed.

        ``target`` is part of the seam (the future per-target checks read it).
        """
        del target
        tracker = self._tracker
        if tracker is None:
            return "no_tracker"
        view = tracker.view
        if view.position is None or state.alive is False:
            return "no_position_or_dead"
        pos = view.position
        if not self._require_standing():
            return "not_standing"
        if self._await_pending(view, pos):
            return "await_pending"
        if self.cache is None:
            return "no_map_cache"
        return None

    def _perform_move(self, state: BotState, target: tuple[int, int]) -> None:
        """Name the actual limb result, without treating author intent as a send."""
        reason = self._move(state, target)
        outcome = {"not_standing": "standing-blocked", "await_pending": "pending"}.get(
            reason, "refused"
        )
        detail: dict[str, object] = {"outcome": outcome, "reason": reason}
        if reason in ("dispatched", "occupied_west_rerouted") and self._pending is not None:
            detail.update(
                outcome="dispatched",
                reason=self._pending_origin if reason == "dispatched" else reason,
                wire_target=self._pending[0],
            )
        self.last_move_outcome = detail | self._move_pending_release
        self._move_pending_release = {}

    def _move(self, state: BotState, target: tuple[int, int]) -> str:
        gate = self._move_gate(state, target)
        if gate is not None:
            self._note_move_gate(gate)
            return gate
        tracker = self._tracker
        cache = self.cache
        if tracker is None or cache is None or tracker.view.position is None:
            # The gate passed a moment ago; drift here is a bug upstream.
            self._note_move_gate("gate_state_drift")
            return "gate_state_drift"
        pos = tracker.view.position
        grid = cache.get(state.map_name)
        # leg 38: the tracked position comes ONLY from the received
        # entry/0x0087 stream - it is server truth even when the client
        # grid calls the cell a wall (s00 logged into pay_fild04 (204,165),
        # a cell the server saved twice). Ground-correct the own cell so
        # the roam/reroll machinery can engage; the leg-28 direct send then
        # carries the walk and the server path-finds its own side.
        if not grid.walkable((state.x, state.y)):
            cache.mark_walkable(state.map_name, (state.x, state.y))
            self._note_move_gate("ground_corrected_own_cell")
        # Allocation and dispatch must agree about received corridor blockers,
        # including the path home after a sale releases the counter.
        if dealer_entry_cell(state.map_name, target) or state.map_name == "prt_in":
            return self._move_staging(state, target, grid, pos)
        try:
            path = shortest_path(grid, (state.x, state.y), target)
            self._no_route_attempts = 0
        except NoRoute:
            return self._move_no_route(state, target, pos)
        return self._move_path(state, target, path, grid, pos)

    def _move_staging(
        self, state: BotState, target: tuple[int, int], grid: WalkMap, pos: ObservedPosition
    ) -> str:
        path = self._merchant_staging.path(grid, state, target)
        if path is None:
            self._note_move_gate("staging_occupied")
            return "staging_occupied"
        self._no_route_attempts = 0
        return self._move_path(state, target, path, grid, pos)

    def _move_path(
        self,
        state: BotState,
        target: tuple[int, int],
        path: tuple[tuple[int, int], ...],
        grid: WalkMap,
        pos: ObservedPosition,
    ) -> str:
        if len(path) > 1:
            return self._dispatch_path_step(state, target, path[1], grid, pos)
        self._note_move_gate("single_cell_path")
        return "single_cell_path"

    def _send_walk(self, point: tuple[int, int], after_seq: int) -> None:
        self.wire.move(*point)
        self._ensure_loot_memos()
        self._loot_motion_seq = after_seq

    def _move_no_route(
        self, state: BotState, target: tuple[int, int], pos: ObservedPosition
    ) -> str:
        if self._occupied_west(state, target):
            self._note_move_gate("occupied_west_no_route")
            return "occupied_west_no_route"
        # leg 28: the field warp cell (170,378) is unwalkable in the
        # client grid, so the route died here and NO walk was ever sent —
        # the server never moved the unit, the warp never fired, and the
        # script re-authored the same MoveTo 97 times. The server
        # path-finds its own side: send the walk DIRECTLY at the target
        # (the spike clients always worked this way), paced on the same
        # pending-walk lifecycle, capped on CONSECUTIVE no-route sends so
        # a cell unreachable on both sides cannot be retried forever (a
        # successful walk elsewhere resets the budget).
        self._no_route_attempts += 1
        if self._no_route_attempts > NO_ROUTE_DIRECT_SENDS:
            return self._move_reroll(state, target, pos)
        self._note_move_gate("no_route_direct")
        self._send_walk(target, pos.seq)
        self._pending_origin = "direct"
        self._pending = (target, pos.seq, self._now(), 0)
        return "dispatched"

    @staticmethod
    def _occupied_west(state: BotState, point: tuple[int, int]) -> bool:
        """Pinned clif.cpp rejects exactly one cell west onto a received body."""
        return point == (state.x - 1, state.y) and (
            point in state.occupied_cells
            or any((actor.x, actor.y) == point for actor in state.nearby)
        )

    def _dispatch_path_step(
        self,
        state: BotState,
        target: tuple[int, int],
        point: tuple[int, int],
        grid: WalkMap,
        pos: ObservedPosition,
    ) -> str:
        reason = "dispatched"
        if self._occupied_west(state, point):
            try:
                path = shortest_path(grid, (state.x, state.y), target, blocked_visible=(point,))
            except NoRoute:
                self._note_move_gate("occupied_west_no_route")
                return "occupied_west_no_route"
            point = path[1]
            reason = "occupied_west_rerouted"
            self._note_move_gate(reason)
        self._send_walk(point, pos.seq)
        self._pending_origin = "step"
        self._pending = (point, pos.seq, self._now(), 0)
        return reason

    def _move_reroll(
        self,
        state: BotState,
        target: tuple[int, int],
        pos: Any,
    ) -> str:
        """The exhausted target gets ONE walkable re-roll (leg 37 defect 2).

        The scripts author targets; the client grid is the walkability
        authority (the w59 split). When the bounded direct sends could not
        move the unit (the cell is a wall on BOTH sides), the runtime walks
        to the nearest walkable neighbor of the target instead of letting
        the script re-author the same impossible cell forever — g00m02
        burned 117 minutes that way. The re-roll is tried once per (map,
        target); a successful walk anywhere resets both budgets."""
        if self.cache is None:
            self._note_move_gate("no_map_cache")
            self._fail_patrol(target)
            return "no_map_cache"
        key = (state.map_name, target)
        if key in self._rerolled_moves:
            self._note_move_gate("rerolled_target_dead")
            self._fail_patrol(target)
            return "rerolled_target_dead"
        alt = nearest_walkable(
            self.cache.get(state.map_name),
            target,
            exclude=((state.x, state.y), target),
        )
        if alt is None:
            # leg 39: s00's pocket is sealed at radius 2 but the roam box
            # holds walkable cells ~7 cells away (34/289). Escalate ONCE per
            # own position to radius 12 and let the server path-find its own
            # side (the leg-28 rule); a second sealed verdict at the same
            # position hands the verdict to the leg-69 server-reposition
            # seam (_escalated_dead_release), not to a silent stop.
            if (state.map_name, (state.x, state.y)) in self._deadlock_cells:
                return self._escalated_dead_release(state, target, pos)
            alt = nearest_walkable(
                self.cache.get(state.map_name),
                target,
                radius=12,
                exclude=((state.x, state.y), target),
            )
            if alt is None:
                self._note_move_gate("target_unwalkable")
                self._fail_patrol(target)
                return "target_unwalkable"
            self._deadlock_cells.add((state.map_name, (state.x, state.y)))
            self._note_move_gate("target_unwalkable_escalated")
            self._send_walk(alt, pos.seq)
            self._pending_origin = "escalated"
            self._pending = (alt, pos.seq, self._now(), 0)
            return "dispatched"
        self._rerolled_moves[key] = alt
        self._note_move_gate("target_unwalkable_rerolled")
        self._send_walk(alt, pos.seq)
        self._pending_origin = "rerolled"
        self._pending = (alt, pos.seq, self._now(), 0)
        return "dispatched"

    def _escalated_dead_release(
        self,
        state: BotState,
        target: tuple[int, int],
        pos: Any,
    ) -> str:
        """The server-reposition seam (leg 69).

        The leg-39 latch stops the radius-12 escalation from re-firing at
        the same position - honest for the ESCALATION, but leg 69 turned
        the latched position into a silent dead-end: s00 sat at pay_fild04
        (213,325) burning x944 escalated_target_dead verdicts while the
        server still accepted walks out of the pocket. The doctrine is
        unchanged - the agent must be able to WALK OUT of a blocked pocket
        and the server path-finds its own side - so after
        ESCALATED_DEAD_DIRECT_BOUND consecutive dead verdicts at the same
        position, the runtime picks the nearest client-side walkable cell
        around the OWN position (nearest_walkable, radius 12) and sends
        the walk DIRECTLY at it (no_route_direct semantics; pending
        origin ``repositioned``, gate ``server_reposition_direct``).
        ESCALATED_DEAD_REPOSITIONS caps the sends per position; a
        server-confirmed position advance re-arms the budgets, and a
        truly sealed pocket (no walkable cell in range) stays an honest
        escalated_target_dead stop."""
        if self._escalated_dead_pos != (state.x, state.y):
            self._escalated_dead_pos = (state.x, state.y)
            self._escalated_dead_count = 0
            self._reposition_sends = 0
        self._escalated_dead_count += 1
        if (
            self._escalated_dead_count > ESCALATED_DEAD_DIRECT_BOUND
            and self._reposition_sends < ESCALATED_DEAD_REPOSITIONS
        ):
            cache = self.cache
            if cache is None:
                # the caller checked a moment ago; drift here is upstream
                self._note_move_gate("no_map_cache")
                self._fail_patrol(target)
                return "no_map_cache"
            alt = nearest_walkable(
                cache.get(state.map_name),
                (state.x, state.y),
                radius=12,
                exclude=((state.x, state.y),),
            )
            if alt is not None:
                self._reposition_sends += 1
                self._note_move_gate("server_reposition_direct")
                self._send_walk(alt, pos.seq)
                self._pending_origin = "repositioned"
                self._pending = (alt, pos.seq, self._now(), 0)
                return "dispatched"
        self._note_move_gate("escalated_target_dead")
        self._fail_patrol(target)
        return "escalated_target_dead"

    def mechanical_actions(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...]:
        self._sync_patrol_context(state)
        shop_actions = self._shop_loop_mechanical(state, actions)
        if shop_actions is not None:
            return shop_actions
        npc_actions = self._npc_mechanical(state, actions)
        if npc_actions is not None:
            return npc_actions
        # Empty MerchantDrive patience/queue ticks still own the outbound
        # town leg. The old field-return fallback walked them into prt001.
        if state.map_name == "prontera" and merchant_admission_refusal(state) is None:
            return actions
        loot_actions = self._loot_mechanical(state, actions)
        if loot_actions is not None:
            return loot_actions
        return self._legacy_mechanical(state, actions)

    def shop_actions(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...] | None:
        """Receipt-bound exchange execution also runs under an authored farm plan.

        This seam grants no exploration, loot or patrol fallback. The same
        owner mints, real offer rows and dispatch guards own every shop send.
        """
        return self._shop_loop_mechanical(state, actions)

    def _loot_mechanical(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...] | None:
        """The mechanical loot path: a floor item dispatches the pickup
        without a decide (leg 61: 39 ItemDrop events surfaced but 0 loot
        choices / 518 decides starved the pickups - the same mechanics-not-
        decisions seam that owns the buy mint). Within the server's pickup
        radius (Chebyshev<=2 of the item's cell) it mints the Loot dispatch;
        outside it mints the walk toward the drop's cell (walkability-aware,
        re-authored ONCE per item on the bounded LOOT_WALK_REAUTH_S clock -
        leg 62: the one-shot memo burned a drop's only walk on a
        pre-empting gate and the ~60s floor TTL ate the drop). One pickup
        attempt per item - the memo clears when the item leaves the floor
        view. Otto's directive: when an attackable monster stands within
        ACTIVE_THREAT_RANGE the whole loot path defers (the item may
        despawn; safety over loot). An authored Attack (an in-melee
        exchange, the leg-61 guard) and an authored Loot (the decider's
        alternative trigger already owning the tick through ``_loot``) are
        never interrupted."""
        if any(isinstance(action, (Attack, Loot)) for action in actions):
            self._note_loot_authored_defer(state, actions)
            return None
        tracker = self._tracker
        if tracker is None or state.alive is not True:
            self._note_loot_unavailable(tracker)
            return None
        floor_items = tracker.view.floor_items
        self._refresh_loot_memo(floor_items)
        threat = self._nearest_active_threat(state)
        if threat is not None:
            self._note_loot_threat_defer(state, floor_items, threat)
            return None
        for item in self._loot_candidates(state, floor_items):
            if item.floor_item_id in self._loot_pickup_tried:
                self._note_loot_pickup_held(item.floor_item_id)
                continue
            if self._floor_item_distance(state, item) > _LOOT_PICKUP_RANGE:
                move = self._loot_walk_mint(state, item)
                if move is not None:
                    return (move,)
                continue
            return self._loot_pickup_mint(item)
        return None

    def _loot_pickup_mint(self, item: ObservedFloorItem) -> tuple[GameAction, ...]:
        if not self._loot_ready(item):
            return ()
        logger.warning(
            "loot-debug: mechanical pickup dispatched (fid=%s nameid=%s cell=(%s,%s))",
            item.floor_item_id,
            item.item_id,
            item.position.x,
            item.position.y,
        )
        return (Loot(),)

    def _loot_walk_mint(self, state: BotState, item: Any) -> MoveTo | None:
        """The out-of-range limb: the walkability-aware MoveTo toward the
        drop, re-authored ONCE per item on the bounded LOOT_WALK_REAUTH_S
        clock (leg 62: the one-shot memo burned a drop's only walk on a
        pre-empting gate); None while this item's walk cannot mint."""
        if item.floor_item_id in self._loot_move_minted and not self._loot_walk_reauth_due(
            item.floor_item_id
        ):
            self._note_loot_walk_held(item.floor_item_id)
            return None
        target = self._loot_move_target(state, item)
        if target is None:
            return None
        reauth = self._loot_walk_mark_mint(item.floor_item_id)
        self._loot_move_minted.add(item.floor_item_id)
        self._loot_receipt.defer(item, "out_of_range")
        logger.warning(
            "loot-debug: move toward floor item (fid=%s nameid=%s"
            " cell=(%s,%s) target=(%s,%s) reauth=%d)",
            item.floor_item_id,
            item.item_id,
            item.position.x,
            item.position.y,
            target[0],
            target[1],
            1 if reauth else 0,
        )
        return MoveTo(*target)

    def _loot_candidates(self, state: BotState, floor_items: Iterable[Any]) -> tuple[Any, ...]:
        """Floor items nearest-first under the pickup metric (Chebyshev),
        the floor-item aid as the deterministic tie-break."""
        return tuple(
            sorted(
                floor_items,
                key=lambda item: (self._floor_item_distance(state, item), item.floor_item_id),
            )
        )

    @staticmethod
    def _floor_item_distance(state: BotState, item: Any) -> int:
        """Chebyshev distance to the drop - the pickup metric."""
        return int(max(abs(item.position.x - state.x), abs(item.position.y - state.y)))

    def _ensure_loot_memos(self) -> None:
        """The loot memo/tap sets, created once (the ``_attack_gate_reasons``
        lazy pattern; ``__init__`` sits at the statement cap)."""
        if getattr(self, "_loot_pickup_tried", None) is not None:
            return
        self._loot_receipt = LootAttribution()
        self._loot_ack_cursor = 0
        self._loot_motion_seq = -1
        self._loot_presence: dict[int, int] = {}
        self._loot_settle_attempts: dict[int, int] = {}
        self._loot_approach_seq: dict[int, int] = {}
        self._loot_pickup_tried: set[int] = set()
        self._loot_move_minted: set[int] = set()
        self._loot_move_reauth: set[int] = set()
        self._loot_move_minted_at: dict[int, float] = {}
        self._loot_defer_tapped: set[int] = set()
        self._loot_authored_tapped: set[int] = set()
        self._loot_walk_held_tapped: set[int] = set()
        self._loot_pickup_held_tapped: set[int] = set()
        self._loot_unavailable_reason: str | None = None

    def _refresh_loot_memo(self, floor_items: Iterable[Any]) -> None:
        """The mechanical loot memo (leg 61): one pickup attempt per floor
        item and one move mint per item, presence-keyed - an aid whose item
        left the floor view is free again (a reused aid is a real new
        drop). The sets are per-instance from the first refresh (the
        ``_attack_gate_reasons`` lazy pattern; ``__init__`` sits at the
        statement cap)."""
        self._ensure_loot_memos()
        presence = {item.floor_item_id: item.position.seq for item in floor_items}
        current = {fid for fid, seq in presence.items() if self._loot_presence.get(fid, seq) == seq}
        self._loot_presence = presence
        self._loot_receipt.refresh(current)
        self._loot_settle_attempts = {
            fid: attempts for fid, attempts in self._loot_settle_attempts.items() if fid in current
        }
        self._loot_approach_seq = {
            fid: seq for fid, seq in self._loot_approach_seq.items() if fid in current
        }
        self._loot_pickup_tried &= current
        self._loot_move_minted &= current
        self._loot_move_reauth &= current
        self._loot_defer_tapped &= current
        self._loot_authored_tapped &= current
        self._loot_walk_held_tapped &= current
        self._loot_pickup_held_tapped &= current
        # a healthy tick re-arms the unavailable tap: a LATER stall names
        # itself again (both dispatch paths pass through here)
        self._loot_unavailable_reason = None
        self._loot_move_minted_at = {
            key: value for key, value in self._loot_move_minted_at.items() if key in current
        }

    def _nearest_active_threat(self, state: BotState) -> int | None:
        """The Chebyshev distance of the nearest attackable monster within
        ACTIVE_THREAT_RANGE of the bot's cell, or None when the surroundings
        are safe (Otto's directive: the pickup fires only when no enemy is
        an active real threat). Unpositioned actors cannot be range-checked
        and are skipped - the native nearby view carries monster cells."""
        nearest: int | None = None
        for actor in state.nearby_monsters:
            if actor.x is None or actor.y is None:
                continue
            distance = max(abs(actor.x - state.x), abs(actor.y - state.y))
            if distance <= ACTIVE_THREAT_RANGE and (nearest is None or distance < nearest):
                nearest = distance
        return nearest

    def _note_loot_threat_defer(
        self, state: BotState, floor_items: Iterable[Any], threat: int
    ) -> None:
        """The threat gate's defer tap, once per item while the threat
        stands (presence-keyed like the loot memos - no per-tick spam),
        naming the nearest threat distance: leg 63's log proves the gate
        live."""
        for item in self._loot_candidates(state, floor_items):
            fid = item.floor_item_id
            if fid in self._loot_defer_tapped:
                continue
            self._loot_defer_tapped.add(fid)
            logger.warning(
                "loot-debug: pickup deferred (threat) (fid=%s nearest=%d)",
                fid,
                threat,
            )

    def _note_loot_authored_defer(self, state: BotState, actions: tuple[GameAction, ...]) -> None:
        """The authored-Action stand-down's tap, once per item while it
        stays on the floor view: leg 67's pair-mates died here untapped (an
        authored Attack exchange or the decider's own Loot owned the tick
        while the mate sat on the floor)."""
        tracker = self._tracker
        if tracker is None or tracker.view is None:
            return
        floor_items = tracker.view.floor_items
        self._refresh_loot_memo(floor_items)
        kinds = ",".join(
            sorted(
                type(action).__name__ for action in actions if isinstance(action, (Attack, Loot))
            )
        )
        for item in self._loot_candidates(state, floor_items):
            fid = item.floor_item_id
            if fid in self._loot_authored_tapped:
                continue
            self._loot_authored_tapped.add(fid)
            logger.warning(
                "loot-debug: pickup deferred (authored-action) (fid=%s kinds=%s)",
                fid,
                kinds,
            )

    def _note_loot_unavailable(self, tracker: Any) -> None:
        """The tracker/alive gate's tap, on BOTH dispatch paths: once per
        reason - a later stall after a healthy tick names itself again."""
        self._ensure_loot_memos()
        reason = "tracker-missing" if tracker is None else "agent-not-alive"
        if self._loot_unavailable_reason == reason:
            return
        self._loot_unavailable_reason = reason
        logger.warning("loot-debug: loot unavailable (%s)", reason)

    def _note_loot_walk_held(self, fid: int) -> None:
        """The move-memo hold inside ``_loot_walk_mint``, once per item
        while it stays on the floor view (leg 67: the pair-mate whose only
        walk a pre-empting gate burned was invisible)."""
        self._ensure_loot_memos()
        if fid in self._loot_walk_held_tapped:
            return
        self._loot_walk_held_tapped.add(fid)
        logger.warning("loot-debug: walk suppressed (reauth pending) (fid=%s)", fid)

    def _note_loot_pickup_held(self, fid: int) -> None:
        """The once-per-presence pickup memo's continue, shared by the
        mechanical loop and the send seam: one line per item per presence
        whichever path hit the gate."""
        self._ensure_loot_memos()
        if fid in self._loot_pickup_held_tapped:
            return
        self._loot_pickup_held_tapped.add(fid)
        logger.warning("loot-debug: pickup suppressed (already tried) (fid=%s)", fid)

    def _loot_walk_reauth_due(self, fid: int) -> bool:
        """True when the item's ONE bounded walk re-author is due: the walk
        mint is older than LOOT_WALK_REAUTH_S and the re-author is unused
        (leg 62: a pre-empting script MoveTo or an await_pending gate
        burned the drop's only walk)."""
        if fid in self._loot_move_reauth:
            return False
        minted_at = self._loot_move_minted_at.get(fid)
        return minted_at is not None and self._now() - minted_at >= LOOT_WALK_REAUTH_S

    def _loot_walk_mark_mint(self, fid: int) -> bool:
        """Record a loot-walk mint; True when this mint IS the item's
        bounded re-author (consuming it). The re-auth clock anchors at the
        FIRST mint."""
        if fid in self._loot_move_minted:
            self._loot_move_reauth.add(fid)
            return True
        self._loot_move_minted_at[fid] = self._now()
        return False

    def _loot_move_target(self, state: BotState, item: Any) -> tuple[int, int] | None:
        """The walk target for a drop out of pickup range: the item's own
        cell when the grid walks it, else the nearest walkable cell
        (bounded radius); never an unwalkable endpoint."""
        target = (item.position.x, item.position.y)
        if self.cache is None:
            self._note_move_gate("loot_no_map_cache")
            return None
        try:
            grid = self.cache.get(state.map_name)
        except NoRoute:
            # no grid authority for this map: aim at the drop's cell and
            # let _move's direct-send fallback cover the leg
            return target
        if grid.walkable(target):
            return target
        alt = nearest_walkable(
            grid,
            target,
            radius=_LOOT_MOVE_RADIUS,
            exclude=((state.x, state.y), target),
        )
        if alt is None:
            self._note_move_gate("loot_target_unwalkable")
            return None
        return alt

    def _legacy_mechanical(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...]:
        if state.goal not in (Goal.GRIND, Goal.FARM_ITEM) or self.cache is None:
            return actions
        if actions:
            return actions
        if state.nearby_monsters or state.alive is False:
            return actions
        try:
            field = self._field_target(state)
            route = starter_route(
                self.cache, state.map_name, (state.x, state.y), field_target=field
            )
        except NoRoute:
            self._fail_patrol()
            return actions
        point = route.next_waypoint
        return (MoveTo(*point),) if point is not None else ()

    def _npc_mechanical(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...] | None:
        if self._npc.actuation_blocked:
            return tuple(a for a in actions if not isinstance(a, (Attack, Loot, MoveTo, TalkToNpc)))
        if needs_npc_preparation(state):
            return (
                actions
                if any(a.is_guidance_npc for a in state.nearby)
                else self._explore_npcs(state, actions)
            )
        return None

    def _explore_npcs(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...]:
        if actions or self.cache is None or state.alive is not True or self._npc_explorations >= 16:
            return actions
        grid = self.cache.get(state.map_name)
        for _ in range(16):
            point = (state.x + self._rng.randint(-8, 8), state.y + self._rng.randint(-8, 8))
            try:
                path = shortest_path(grid, (state.x, state.y), point)
            except NoRoute:
                continue
            if len(path) > 1:
                self._npc_explorations += 1
                return (MoveTo(*point),)
        return ()

    def _floor_item_events(self, view: Any, state: BotState) -> tuple[ItemDrop, ...]:
        """The loot seam's surfacing hop: received drops become real world
        events, once per presence (leg 60 starved the sell arm with zero
        ItemDrop-class events). One tap line per surfaced item so the next
        leg's log proves the ingest -> event hop live."""
        events: list[ItemDrop] = []
        current: set[int] = set()
        for item in view.floor_items:
            current.add(item.floor_item_id)
            if item.floor_item_id in self._seen_floor:
                continue
            logger.warning(
                "loot-debug: floor item surfaced (nameid=%s cell=(%s,%s) amount=%s fid=%s)",
                item.item_id,
                item.position.x,
                item.position.y,
                item.amount,
                item.floor_item_id,
            )
            events.append(
                ItemDrop(
                    nameid=item.item_id,
                    x=item.position.x,
                    y=item.position.y,
                    amount=item.amount,
                    map_name=view.map_name or state.map_name,
                    floor_item_id=item.floor_item_id,
                )
            )
        self._seen_floor = current
        return tuple(events)

    def drain_native_events(self) -> tuple[WorldEvent, ...]:
        state = self.build_native_state(Goal.GRIND)
        self._pump_recovery(state)
        tracker = self._tracker
        if tracker is None:
            return ()
        pos = tracker.view.position
        if pos is not None:
            # Evaluate the pending walk on the received-frame path, not only
            # inside action dispatch: window 3 starved because a host that
            # stops dispatching never reached _await_pending, so the bounded
            # re-request (unit.cpp187-192 zero-cell walkok release evidence)
            # never fired and the single pending slot blocked every later
            # send. Same budget, pacing and exhaustion semantics as dispatch.
            self._await_pending(tracker.view, pos)
        self._loot_resume(state)
        events: list[WorldEvent] = []
        dialog = self._npc.view
        if dialog is not None and dialog.sequence > self._npc_event_sequence:
            events.append(NpcDialogueReceived(dialog))
            self._npc_event_sequence = dialog.sequence
        visible = {actor.id for actor in state.nearby_monsters}
        events.extend(
            MonsterSpotted(actor)
            for actor in state.nearby_monsters
            if actor.id not in self._seen_actors
        )
        self._seen_actors = visible
        events.extend(self._damage_events(tracker.view))
        events.extend(self._floor_item_events(tracker.view, state))
        self._event_cursor = self._metadata_cursor
        if self.wire.party_invite_pid and self.wire.party_invite_pid != self._invite:
            events.append(InviteReceived(state.pending_invites[0]))
        self._invite = self.wire.party_invite_pid
        return tuple(events)

    def _pump_recovery(self, state: BotState) -> None:
        if self.mechanical_recovery_allowed:
            self._recover_idle_merchant(state)
            self._rearm_closed_merchant(state)
            self._recover_dead_self(state)
        self._keepalive()

    def _rearm_closed_merchant(self, state: BotState) -> None:
        """A verified timeout close releases one contact per shared retry token."""
        npc_id = self._merchant_reopen
        if npc_id is None or self.npc_recovery_hold:
            return
        if merchant_admission_refusal(state) is not None:
            self._merchant_reopen = None
            return
        if not all(
            (
                self._npc.view is None,
                not self._npc.failed,
                not self._npc.cancel_uncertain,
                self._shop_context.offer is None,
                self._tracker is not None and self._sell_actuation_ready(self._tracker.view),
                self._pending is None,
            )
        ):
            return
        if self._take_npc_retry(self._now()):
            self._merchant_reopen = None
            release_merchant_talk(state.name, npc_id)

    def _recover_idle_merchant(self, state: BotState) -> None:
        """A refused dealer trip closes on the host pump, even under social goals."""
        if self.npc_recovery_hold or state.map_name != "prt_in":
            return
        dialog = self._npc.view
        if dialog is None or merchant_admission_refusal(state) is None:
            return
        talk = _dealer_talk(state, MERCHANT_ROUTE["prt_in"])
        if talk is not None and talk.npc_id == dialog.npc_id:
            self._close_timeout_dialogue(state, NpcClose(dialog.npc_id))

    def _recover_dead_self(self, state: BotState) -> None:
        """Only received self-death admits B2; its send never claims life or pose."""
        if state.alive is not False:
            self._respawn_retry_at = 0.0
            return
        if self._npc.actuation_blocked or self._npc.failed:
            return
        now = self._now()
        if now < self._respawn_retry_at:
            return
        # Pace before the fallible send, and preserve exact send-failure ownership.
        self._respawn_retry_at = now + RESPAWN_RETRY_CADENCE_S
        self._send_npc(respawn())

    def _retry_blocked_dialogue_on_tick(self, now: float) -> None:
        """The host keepalive can recover timeout even without authored actions."""
        if not self.npc_recovery_hold:
            self._retry_timeout_dialogue(now)

    def _keepalive(self) -> None:
        """Pump before host cognition; getters/state projection never send.

        Called only after strict received state readiness. Inference shares the
        host thread: this is pacing, not a guarantee against >60s blocked ticks.
        The wire owns the existing packet encoding and send-failure semantics.

        Window-14 reader stability: the map server closes a session it has
        received no data from for ``stall_time`` seconds (pinned rAthena
        src/common/socket.cpp:1016; deployed packet_athena.conf pins 60), and
        this pump rides the host tick, so a starved tick loop (build_state
        failures, a blocked inference review) can leave the socket silent past
        the kick and the reader dies with rx_error "EOF from map-server"
        (window 14, fixture_1: four keepalives in ~500s). An independent
        daemon pump thread (``_keepalive_loop``) therefore keeps its OWN
        wall-time schedule — never the injected host clock — and shares only
        the send critical-section and the poison flag below. The thread starts
        only after the first successful strict post-readiness pump, so the
        "only after strict received state readiness" contract is unchanged.
        Keepalive frames are 6 bytes: a single send syscall under a normally
        empty send buffer, so concurrent tick-thread sends cannot interleave
        mid-frame.
        """
        with self._keepalive_lock:
            now = self._now()
            previous = self._keepalive_at
            if not math.isfinite(now) or (previous is not None and now < previous):
                message = "native keepalive clock unavailable"
                raise NativeTelemetryUnavailable(message)
            if previous is None:
                self._keepalive_at = now
            elif now - previous >= self._keepalive_interval_s:
                # Poison before the fallible send; retain exact exception/ownership.
                self._keepalive_failed = True
                self.wire.keepalive()
                self._keepalive_failed = False
                self._keepalive_at = now
                self._retry_blocked_dialogue_on_tick(now)
            self._ensure_keepalive_thread()

    def _ensure_keepalive_thread(self) -> None:
        """Start the daemon pump once, after a successful readiness-gated send schedule."""
        if self._keepalive_thread is not None or self._closed:
            return
        # A fresh event per thread: the previous thread's event is never
        # recycled, so a stop can never leave a new thread armed on a stale
        # (or freshly reset) wait.
        self._keepalive_wake = threading.Event()
        thread = threading.Thread(
            target=self._keepalive_loop, name="playing-keepalive", daemon=True
        )
        self._keepalive_thread = thread
        thread.start()

    def _keepalive_loop(self) -> None:
        """Independent wall-time pump; survives starved ticks and blocked reviews.

        The schedule is deliberately ``time.monotonic`` (real wall time), not
        the injected host clock: the pump exists for exactly the failure shape
        where host cognition stops advancing. A send is at most one 6-byte
        syscall under the shared critical-section, so an extra pump cannot
        interleave a tick-path frame mid-write.
        """
        wake = self._keepalive_wake
        last = time.monotonic()
        while not wake.wait(timeout=self._keepalive_interval_s):
            if self._closed:
                self._release_keepalive_slot()
                return
            now = time.monotonic()
            if now - last < self._keepalive_interval_s:
                continue
            failed = False
            control_flow: BaseException | None = None
            with self._keepalive_lock:
                try:
                    # Same poison discipline as the tick pump: poison before
                    # the fallible send, clear only on success.
                    self._keepalive_failed = True
                    self.wire.keepalive()
                    self._keepalive_failed = False
                    last = now
                except Exception:
                    failed = True  # poison stays: health fails closed on next query
                except BaseException as origin:
                    failed = True
                    control_flow = origin
            if control_flow is not None:
                self._release_keepalive_slot()
                raise control_flow
            if failed:
                # Poison already recorded; stop the pump thread. No spin.
                self._release_keepalive_slot()
                return

    def _release_keepalive_slot(self) -> None:
        """Release this thread's slot under the lock; no automatic restart."""
        with self._keepalive_lock:
            if self._keepalive_thread is threading.current_thread():
                self._keepalive_thread = None

    def _stop_keepalive_thread(self) -> None:
        """Wake and join the daemon pump before the wire changes state."""
        # Keep the event object the loop captured: setting it wakes the wait
        # at once; replacing it here could re-arm a thread that had not yet
        # reached wait() and let it pump after close.
        self._keepalive_wake.set()
        thread = self._keepalive_thread
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(timeout=2.0)
        self._keepalive_thread = None

    def _in_party(self) -> bool:
        return bool(self.wire.party_id) or any(
            member.get("aid") == self.wire.aid for member in self.wire.party_members
        )

    def _life(self, view: NativeGameplayView) -> bool | None:
        if view.alive_known:
            return view.alive
        return True if self._authenticated_baseline else None

    def _dealer_bodies(self) -> tuple[tuple[int, tuple[int, int]], ...]:
        """Received identities preserve distinct allocation for overlapping bodies."""
        if self._tracker is None:
            return ()
        own_ids = (self.wire.aid, (-self.wire.aid) & 0xFFFFFFFF)
        return tuple(
            (actor.actor_id, (actor.position.x, actor.position.y))
            for actor in self._tracker.view.actors
            if actor.objecttype == 0 and actor.actor_id not in own_ids
        )

    def _occupied_cells(
        self, view: NativeGameplayView, pos: ObservedPosition
    ) -> tuple[tuple[int, int], ...]:
        """Perception only: type-0 bodies can be PCs, mobs or NPCs.

        Rebuilt from the tracker each tick, so received movement, vanish,
        map change and epoch reset release old cells without a shared queue.
        """
        own_ids = (self.wire.aid, (-self.wire.aid) & 0xFFFFFFFF)
        cells = {
            (actor.position.x, actor.position.y)
            for actor in view.actors
            if actor.objecttype == 0 and actor.actor_id not in own_ids
        }
        return tuple(
            sorted(
                cells,
                key=lambda cell: (
                    max(abs(cell[0] - pos.x), abs(cell[1] - pos.y)),
                    (cell[0] - pos.x) ** 2 + (cell[1] - pos.y) ** 2,
                    cell,
                ),
            )[:OCCUPIED_CELL_LIMIT]
        )

    def _nearby(
        self, view: NativeGameplayView, pos: ObservedPosition, map_name: str
    ) -> tuple[ActorRef, ...]:
        nearby = []
        species = []
        for actor in view.actors:
            cell = (actor.position.x, actor.position.y)
            if actor.objecttype in (6, 12):
                nearby.append(
                    ActorRef(
                        actor.actor_id,
                        self._npc_names.get(actor.actor_id, f"NPC#{actor.actor_id}"),
                        "npc",
                        math.hypot(actor.position.x - pos.x, actor.position.y - pos.y),
                        cell[0],
                        cell[1],
                        npc_sprite=self._species.get(actor.actor_id),
                    )
                )
            if actor.attackable:
                key = self._species.get(actor.actor_id, 0)
                species.append(key)
                info = self.mob_db.catalog.get(key)
                nearby.append(
                    ActorRef(
                        actor.actor_id,
                        info.name if info else f"monster#{key}",
                        "monster",
                        math.hypot(actor.position.x - pos.x, actor.position.y - pos.y),
                        cell[0],
                        cell[1],
                    )
                )
        self.mob_db.observe(map_name, species)
        return tuple(nearby)

    def _await_pending(self, view: NativeGameplayView, pos: ObservedPosition) -> bool:
        pending = self._pending
        if pending is not None:
            point, seq, sent, retries = pending
            if view.arrival_confirmed and pos.seq > seq and (pos.x, pos.y) == point:
                self._pending = None
            elif view.arrival_confirmed and pos.seq > seq:
                # The walk ENDED short of the point (its own walkok said so):
                # mobs wander, so the scripted point is already stale.
                # Release — the script's next step re-approaches from the
                # current geometry. Re-moving to the stale point cancelled
                # in-flight walks and crawled the approach to ~4
                # walks/minute (w57).
                self._pending = None
                return False
            elif pos.seq != seq:
                # The walk is progressing (the position frames advanced):
                # wait for its own arrival proof, refreshing the progress
                # clock on the monotonic.
                self._pending = (point, pos.seq, self._now(), retries)
                return True
            elif self._now() - sent >= 1.0:
                # No position progress for 1s with the point unproven: the
                # walk finished silently, was blocked, or the ack was lost.
                # Release for a fresh approach from the current position —
                # the re-send to the stale point did not converge (w57).
                # Leg 68: this release is where a server-refused walk goes
                # silent (the (226,317) pocket inferred its refusals from a
                # zero-note receipt) - the note names the release WITH the
                # walk class so the next receipt reads which walks died.
                self._note_move_gate(f"walk_released_no_progress({self._pending_origin})")
                # Retain until the next MoveTo perform: event draining can
                # release this walk while the patient author is holding.
                self._move_pending_release = {
                    "pending_outcome": "pending-cancelled",
                    "pending_reason": f"no_progress({self._pending_origin})",
                    "pending_target": point,
                }
                self._pending = None
                return False
            else:
                return True
        return False

    def _field_target(self, state: BotState) -> tuple[int, int] | None:
        self._sync_patrol_context(state)
        if self.cache is None or state.map_name != "prt_fild08":
            return None
        grid = self.cache.get(state.map_name)
        patrol = self._patrol
        if patrol is not None and not self._patrol_replan(patrol):
            return patrol.target
        self._patrol = None
        candidates = [
            (state.x + self._rng.randint(-8, 8), state.y + self._rng.randint(-8, 8))
            for _ in range(16)
        ]
        target = next((point for point in candidates if grid.walkable(point)), None)
        if target is not None:
            self._patrol = _FieldPatrol(
                target,
                self._metadata_cursor,
                (state.map_name, state.native_epoch, state.goal),
                self._now() + 120.0,  # bounded policy, not an inferred travel time
            )
        return target

    def _sync_patrol_context(self, state: BotState) -> None:
        patrol = self._patrol
        context = (state.map_name, state.native_epoch, state.goal)
        if self.cache is None or (patrol is not None and patrol.context != context):
            self._patrol = None

    def _fail_patrol(self, target: tuple[int, int] | None = None) -> None:
        patrol = self._patrol
        if (
            self._pending is None
            and patrol is not None
            and (target is None or target == patrol.target)
        ):
            self._patrol = None

    def _patrol_replan(self, patrol: _FieldPatrol) -> bool:
        pending = self._pending
        if pending is not None:
            tracker = self._tracker
            if tracker is None or tracker.view.position is None:
                return False
            view, pos = tracker.view, tracker.view.position
            point, seq, _, _ = pending
            if not view.arrival_confirmed or pos.seq <= seq or (pos.x, pos.y) != point:
                return False
        return self._patrol_arrived(patrol) or self._now() >= patrol.deadline

    def _patrol_arrived(self, patrol: _FieldPatrol) -> bool:
        tracker = self._tracker
        if tracker is None:
            return False
        view = tracker.view
        pos = view.position
        return bool(
            view.arrival_confirmed
            and pos is not None
            and pos.seq > patrol.receipt_baseline
            and (pos.x, pos.y) == patrol.target
        )

    def _require_standing(self, *, after_seq: int | None = None) -> bool:
        """Only received SELF pose, not HP or send intent, authorizes recovery."""
        if self._standing is True and (after_seq is None or self._standing_seq > after_seq):
            return True
        now = self._now()
        pending = self._stand_pending
        if pending is None:
            self._stand_pending = (self._metadata_cursor, now, now, 1)
            self.wire.stand()
        else:
            seq, started, last_sent, attempts = pending
            epoch = max(3.0, 3.0 * (2 ** min(attempts // 3, 3)))
            if attempts < 3 and now - last_sent >= 1.0 and now - started < epoch:
                self._stand_pending = (seq, started, now, attempts + 1)
                self.wire.stand()
            elif now - started >= epoch:
                # w65: a join-era sit pose can flip standing off; the old
                # recovery went permanently silent after the first 3s epoch,
                # dropping every action for the rest of the window. Re-arm a
                # longer epoch instead of giving up while the agent is alive.
                self._stand_pending = (self._metadata_cursor, now, now, 3)
                self.wire.stand()
        return False

    def _damage_events(self, view: NativeGameplayView) -> tuple[WorldEvent, ...]:
        events: list[WorldEvent] = []
        own = (self.wire.aid, (-self.wire.aid) & 0xFFFFFFFF)
        for damage in view.damage:
            if (
                damage.seq > self._event_cursor
                and damage.target_id in own
                and not damage.is_sp_damage
            ):
                amount = max(0, damage.damage) + max(0, damage.damage2)
                if amount:
                    events.append(DamageTaken(amount, damage.source_id))
        return tuple(events)

    def drain_party_observations(self) -> tuple[PartyObservation, ...]:
        """Party-scoped contribution rows new since the last drain, once each.

        The human-contribution ear: the damage rows name EVERY actor (the
        bot-dealt ones already exist; the human-dealt ones name the human as
        the source), the skill rows are the received heal/buff casts, and the
        exp rows are the party's shared exp flowing in. Reads only the cached
        tracker view — never a re-observing read (the w65-67 double-consumer
        stall); rows are attributed to humans by the society layer.
        """
        tracker = self._tracker
        if tracker is None:
            return ()
        view = tracker.view
        rows = [
            *self._party_damage_rows(view.damage),
            *self._party_skill_rows(view.skill_uses),
            *self._party_exp_rows(view.xp),
        ]
        self._party_obs_cursor = max(
            [self._party_obs_cursor]
            + [damage.seq for damage in view.damage]
            + [use.seq for use in view.skill_uses]
            + [xp.seq for xp in view.xp]
        )
        return tuple(rows)

    def _party_damage_rows(self, damage: tuple[ObservedDamage, ...]) -> list[PartyObservation]:
        cursor = self._party_obs_cursor
        return [
            PartyObservation(
                kind="damage",
                source_id=row.source_id,
                target_id=row.target_id,
                amount=max(0, row.damage) + max(0, row.damage2),
            )
            for row in damage
            if row.seq > cursor
        ]

    def _party_skill_rows(self, uses: tuple[ObservedSkillUse, ...]) -> list[PartyObservation]:
        cursor = self._party_obs_cursor
        return [
            PartyObservation(
                kind="skill",
                source_id=use.source_id,
                target_id=use.target_id,
                amount=0,
                skill_id=use.skill_id,
                failed=use.failed,
            )
            for use in uses
            if use.seq > cursor
        ]

    def _party_exp_rows(self, xp: tuple[ObservedXP, ...]) -> list[PartyObservation]:
        cursor = self._party_obs_cursor
        return [
            PartyObservation(
                kind="exp",
                source_id=0,
                target_id=0,
                amount=int(row.delta or 0),
                skill_id=row.parameter,
            )
            for row in xp
            if row.seq > cursor and (row.delta or 0) > 0
        ]

    def say(self, text: str) -> None:
        self.perform_native(Say(text))

    @property
    def received_skills(self) -> ReceivedSkillContextReadOnly:
        return self._skills.context if self._skills is not None else ReceivedSkillContextReadOnly()

    def _invalidate_skills(self) -> None:
        if self._skills is not None:
            self._skills.invalidate()

    def _reset_epoch(self, epoch: int, base: int) -> None:
        self._reset_loot_epoch("session_changed")
        self._invalidate_self_slots()
        self._skills = None
        self._skill_wire = self.wire
        if type(epoch) is int and 0 < epoch <= 0x7FFFFFFFFFFFFFFF:
            self._skills = NativeSkillContext(epoch, base)
        self._npc = NativeNpcDialogue()
        self._npc_retries, self._npc_retry_at = NPC_RETRY_BUDGET, 0.0
        self._npc_retry_epoch_at = None
        self._merchant_reopen = None
        self._merchant_returning = False
        self._respawn_retry_at = 0.0
        self._shop_context = NativeShopContext()
        self._reset_shop_seam()
        self._npc_event_sequence = 0
        self._npc_explorations = 0
        self._rest_at = None
        self._rest_seq = None
        self._standing_seq = base
        self._pose_seq = base
        self._received_vitals.clear()
        self._vitals_seq = 0
        self._keepalive_at = None
        self._keepalive_failed = False
        self._patrol = None
        self._tracker = NativeGameplayTracker(self.wire.aid)
        self._party_obs_cursor = base
        self._equip_attempts = {}
        self._stat_unacked: int = 0
        self._stat_acks_seen: int = 0
        self._stat_failed: set[int] = set()
        self._epoch = epoch
        self._epoch_character = self.wire.char_name
        self._species.clear()
        self._npc_names.clear()
        self._metadata_cursor = base
        self._authenticated_baseline = False
        self._move_pending_release = {}
        self._pending = None
        self._standing = None
        self._stand_pending = None
        self._event_cursor = base
        self._seen_actors.clear()
        self._invite = 0
        self._reset_encounters(epoch, base)

    def _reset_encounters(self, epoch: int, base: int) -> None:
        self._encounters = None
        if type(epoch) is not int or not 0 < epoch <= 0x7FFFFFFFFFFFFFFF:
            return  # Existing progression guard still denies the state.
        level = None
        try:
            selected = self._progression(selection_only=True)
        except NativeTelemetryUnavailable:
            pass  # No valid received selection: keep captured level unknown.
        else:
            level = ReceivedSelfLevel(epoch, 0, selected.base_level, "selection", SELECTION_BINDING)
        self._encounters = NativeEncounterStream(
            epoch=epoch, own_actor_id=self.wire.aid, base_seq=base, level=level
        )

    def _consume_metadata(self, frames: tuple[tuple[int, float, int, bytes], ...]) -> None:
        for seq, _, pid, raw in frames:
            if seq <= self._metadata_cursor:
                continue
            if pid == 0x00B0 and int.from_bytes(raw[2:4], "little") in (5, 6, 7, 8):
                self._received_vitals[int.from_bytes(raw[2:4], "little")] = int.from_bytes(
                    raw[4:8], "little", signed=True
                )
                self._vitals_seq = seq
            if pid == 0x0091:
                self._receive_map_metadata()
            elif pid == 0x0ADF:
                self._receive_npc_name(raw)
            elif pid == 0x02EB:
                # e985 clif.cpp10721-29 fresh zero allocation; pc_setnewpc,
                # pc_authok and pc_setpos do not set dead_sit before auth.
                # pc.hpp1150 defines dead_sit==1 as death, not display HP.
                self._authenticated_baseline = True
                self._standing = True
                self._stand_pending = None
            elif pid == 0x08C8:
                self._receive_pose(seq, raw)
            else:
                self._receive_actor_metadata(pid, raw)
            self._metadata_cursor = seq

    def _receive_map_metadata(self) -> None:
        """Invalidate received map-scoped NPC, patrol and motion metadata."""
        self._reset_loot_epoch("map_changed")
        self._npc.invalidate()
        self._npc_names.clear()
        self._move_pending_release = {}
        self._patrol = None
        self._species.clear()
        self._pending = None

    def _receive_actor_metadata(self, pid: int, raw: bytes) -> None:
        """Retain received species presentations and forget vanished actors."""
        if pid in (0x09FD, 0x09FE, 0x09FF):
            self._species[int.from_bytes(raw[5:9], "little")] = int.from_bytes(raw[23:25], "little")
            self._receive_actor_entry_name(raw)
        elif pid == 0x0080:
            self._receive_actor_vanish(raw)

    def _receive_actor_entry_name(self, raw: bytes) -> None:
        """Publish only after this exact frame has passed the received tracker."""
        name = actor_entry_npc_name(raw)
        actor_id = int.from_bytes(raw[5:9], "little")
        dialog = self._npc.view
        if (
            dialog is not None
            and dialog.npc_id == actor_id
            and (dialog.stage == "unsupported_shop" or self._shop_context.actor_id == actor_id)
        ):
            self._npc.invalidate()
        # A new received entry supersedes both entry and 0ADF names for this ID.
        self._npc_names.pop(actor_id, None)
        tracker = self._tracker
        if name is not None and tracker is not None and observed_npc(tracker.view, actor_id):
            self._npc_names[actor_id] = name

    def _receive_actor_vanish(self, raw: bytes) -> None:
        """Forget actor metadata; only received SELF death clears pose."""
        self._npc_names.pop(int.from_bytes(raw[2:6], "little"), None)
        self._species.pop(int.from_bytes(raw[2:6], "little"), None)
        if (
            int.from_bytes(raw[2:6], "little") in (self.wire.aid, (-self.wire.aid) & 0xFFFFFFFF)
            and raw[6] == 1
        ):
            self._standing = None
            self._stand_pending = None

    def _receive_npc_name(self, raw: bytes) -> None:
        received = received_npc_name(raw)
        tracker = self._tracker
        if received is not None and tracker is not None:
            actor_id, name = received
            if observed_npc(tracker.view, actor_id) is not None:
                self._npc_names[actor_id] = name

    def _receive_pose(self, seq: int, raw: bytes) -> None:
        """Validated ACT3: packed type@29, SELF srcID, target0.

        Pinned packets.hpp1412-26 and clif.cpp5329-58; negative source is
        the exact disguised SELF alias, never an arbitrary peer/NPC.
        """
        own = (self.wire.aid, (-self.wire.aid) & 0xFFFFFFFF)
        if (
            int.from_bytes(raw[2:6], "little") not in own
            or int.from_bytes(raw[6:10], "little") != 0
        ):
            return
        if raw[29] in (2, 3):
            self._pose_seq = seq
        if raw[29] == 2:
            # pc_setsit stops walking. Forget intent, not received coordinates.
            self._pending = None
            self._standing = False
        elif raw[29] == 3:
            pending = self._stand_pending
            if pending is None or seq > pending[0]:
                self._standing = True
                self._standing_seq = seq
                self._stand_pending = None

    def _progression(self, *, selection_only: bool = False) -> SessionProgression:
        wire = self.wire
        return require_native_session_progression(
            wire.selected_character_snapshot,
            {} if selection_only else wire.status_params,
            class_fresh=wire.class_fresh,
            selection_epoch=wire.selection_epoch,
            map_epoch=wire.map_epoch,
            native_epoch=wire.native_epoch,
            char_id=wire.gid,
        )
