"""AgentHost: N scheduled agents on the live rAthena server + WorldFeed.

The integration slice between the society layer (ADR-005), the event-driven
brain (ADR-002), and the dashboard world (ADR-007/008/010):

- :class:`ScheduledAgent` binds one :class:`~robots.society.models.SocietyPersona`
  to one in-game character (account + char from the e2e seed manifest) with an
  :class:`~robots.app.brain.EventDrivenBrain` and a
  :class:`~robots.society.memory.Memory`. It owns its BotClient (spike 003 via
  the import shim below — the spike is a stdlib-only script, not a package) and
  the BotRunner-equivalent loop: poll the client's world model for events
  (chat heard, actors seen), pump the brain (``handle_event`` on real events,
  ``Heartbeat`` via the ADR-002 random timers), execute script steps as client
  actions (say/move/sit), and publish the runtime state into the
  :class:`~robots.app.world_state.WorldState` so the dashboard shows real data.
- :class:`AgentHost` orchestrates N agents: connect/disconnect lifecycle driven
  by each persona's group Schedule (a session is a memory, ADR-004: the
  disconnect path writes a ``session`` experience note first), decision and
  chat backend selection (CLEF_URL -> ClefLocal else ScriptedDecisionModel;
  LocalChatServer if a llama-server is reachable else StaticChatGenerator),
  the WorldFeed uvicorn server in a background thread, and the
  :class:`PersonaClock` SocietyClock adapter.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import random
import socket
import threading
import time
import urllib.parse
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast, final

import uvicorn

from robots.adapters.chat.chat_local import LocalChatServer
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.clef_local import ClefLocal
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.adapters.memory_summary_cache import JsonlSummaryNodeStore
from robots.adapters.native_vitals import (
    NativeTelemetryUnavailable,
    NativeVitals,
    require_native_vitals,
)
from robots.adapters.playing_backends import PlayingBackendError
from robots.adapters.worldfeed_server import create_app
from robots.app.brain import EventDrivenBrain, TickResult
from robots.app.host_commands import ChatRequest, HostChatCommands
from robots.app.host_memory_factory import validate_summary_cache
from robots.app.npc_planning_execution import NpcHostBinding
from robots.app.planning_brain import PlannedBrain
from robots.app.playing_runtime import PlayingClient
from robots.app.timers import TimerSet
from robots.app.trace_log import (
    STATE_TICK_INTERVAL_S,
    TracedChatGenerator,
    TracedDecisionModel,
    TraceLog,
    action_params,
    chat_channel,
    event_payload,
)
from robots.domain.actions import (
    AcceptGuildInvite,
    AcceptInvite,
    FoundGuild,
    GameAction,
    GuildInvite,
    InviteToParty,
    MoveTo,
    NpcRespond,
    PartyChat,
    Rest,
    Say,
    WhisperTo,
)
from robots.domain.events import ChatHeard, Heartbeat, TimerFired, WorldEvent
from robots.domain.model import ActorRef, BotState, ChatLine, Goal
from robots.popgen import GeneratedPopulation, load_population
from robots.society.memory import Memory, StubSummarizer
from robots.society.models import SocietyClock, SocietyPersona
from robots.society.objectives import BoundCoordinator, GroupCoordinator, seed_roster
from robots.society.relations import RelationshipLedger
from robots.society.society import SocietyRoster
from robots.society.wants import Personality, WantEvent, WantSatisfier, WantState

if TYPE_CHECKING:
    from robots.ports import ChatGenerator, DecisionModel, TickClock

if TYPE_CHECKING:  # the WorldFeed aggregate is landed, but stay tolerant
    from robots.app.world_state import WorldState
else:
    try:
        from robots.app.world_state import WorldState
    except ImportError:  # pragma: no cover - exercised only while it is in flight
        WorldState = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)

# ---- spike 003 import shim -------------------------------------------------
# BotClient lives in spikes/003-clientless-limbs/client.py (stdlib-only, import
# side effects: sys.path juggling). It is NOT a package; import it tolerantly.
_SPIKE_DIR = Path(__file__).resolve().parents[3] / "spikes" / "003-clientless-limbs"
try:
    import sys as _sys

    if _SPIKE_DIR.is_dir():
        _sys.path.insert(0, str(_SPIKE_DIR))
    from client import BotClient as _BotClient  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - spike missing is a deployment issue
    _BotClient = None

DEFAULT_TICK_SECONDS = 2.0
HEARTBEAT_MIN_S = 300.0
HEARTBEAT_MAX_S = 300.0
"""The user directive (2026-10-22): no agent stands idle longer than five
minutes — the heartbeat's upper bound equals its lower bound, so every agent
reviews its goal (and can socialize) at least once every five minutes."""
IDLE_REVIEW_S = 300.0
"""An agent whose last executed action is older than this gets a synthetic
idle-review decide immediately, without waiting for the heartbeat timer."""
DEFAULT_CHAT_URL = "http://127.0.0.1:8301/v1/chat/completions"
DEFAULT_WORLDFEED_PORT = 8400

# The scripted model: grind/farm + chatty + party-friendly. Answers must
# satisfy every question the brain asks (unknown keys are ignored). Mirrors
# scripts/e2e_runner.py so the stub behaves identically on the live server.
DEFAULT_STUB_ANSWERS: dict[str, Any] = {
    "next_action": {"choice": "travel", "confidence": 0.9},
    "target_choice": {"choice": "closest"},
    "should_reply": {"noul": True},
    "hp_critical": {"noul": False},
    "threat_near": {"noul": False},
    "accept_invite": {"noul": True},
    "use_premade": {"noul": True},
    "premade_pick": {"choice": "greet"},
    "chat_urgency": {"score": 2.0},
    "change_goal": {"choice": "farm"},
    "goal_review": {"score": 0.9},
    "farm_duration": {"score": 1.0},
    "farm_target": {"choice": "Poring"},
    "react_monster": {"choice": "ignore"},
    "react_damage": {"choice": "rest"},
}


def _join_producer(thread: threading.Thread, label: str, *, timeout: float | None = None) -> None:
    """Keep ownership until join confirms termination; optionally bound the attempt."""
    if thread is threading.current_thread():
        msg = f"cannot shut down {label} from its worker itself"
        raise RuntimeError(msg)
    if timeout is None:
        thread.join()
    else:
        thread.join(timeout)
    if thread.is_alive():
        msg = f"{label} worker is still alive after join"
        raise RuntimeError(msg)


def _raise_cleanup_errors(errors: list[BaseException]) -> None:
    """After cleanup, preserve control flow; aggregate only ordinary failures."""
    origin = next((error for error in errors if not isinstance(error, Exception)), None)
    if origin is not None:
        with suppress(BaseException):
            metadata = BaseException.__dict__["__dict__"].__get__(origin)
            prior = dict.get(metadata, "shutdown_cleanup_errors", ())
            secondary = tuple(error for error in errors if error is not origin)
            dict.__setitem__(metadata, "shutdown_cleanup_errors", prior + secondary)
        raise origin
    if len(errors) == 1:
        raise errors[0]
    if errors:
        msg = "shutdown failed after cleanup"
        raise BaseExceptionGroup(msg, errors)


def _close_failed_memory(origin: BaseException, close: Callable[[], None]) -> None:
    """Attempt owned storage cleanup without replacing construction's origin."""
    try:
        close()
    except BaseException:
        with suppress(BaseException):
            origin.add_note("host memory cleanup failed; storage release may be incomplete")


@final
class PersonaClock:
    """SocietyClock adapter over local wall-clock time (Monday=0)."""

    def local_now(self) -> tuple[int, float]:
        """Return ``(weekday, hour_float)`` from the machine's local time."""
        local = datetime.now().astimezone()
        return local.weekday(), local.hour + local.minute / 60.0


@final
class WallClock:
    """TickClock over ``time.monotonic`` / ``time.sleep`` (the real loop)."""

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def monotonic(self) -> float:
        return time.monotonic()


@final
class ManifestEntry:
    """One row with a literal IPv4 endpoint; defaults retain legacy port 6900."""

    __slots__ = (
        "account",
        "char_name",
        "login_host",
        "login_port",
        "password",
        "persona_id",
        "pincode",
    )

    def __init__(
        self,
        persona_id: str,
        account: str,
        password: str,
        char_name: str,
        *,
        login_host: str = "127.0.0.1",
        login_port: int = 6900,
        pincode: str | None = None,
    ) -> None:
        _validate_login_endpoint(login_host, login_port)
        if pincode is not None:
            _validate_pincode(pincode)
        self.persona_id = persona_id
        self.account = account
        self.password = password
        self.char_name = char_name
        self.login_host = login_host
        self.login_port = login_port
        self.pincode = pincode


def _validate_login_endpoint(host: object, port: object) -> None:
    """Validate plain primitives without DNS lookup or string/number coercion."""
    if type(host) is not str:
        msg = "login_host must be an IPv4 literal"
        raise ValueError(msg)
    try:
        ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        msg = "login_host must be an IPv4 literal"
        raise ValueError(msg) from None
    if type(port) is not int or not 1 <= port <= 65535:
        msg = "login_port must be an integer from 1 to 65535"
        raise ValueError(msg)


def _validate_pincode(pincode: object) -> None:
    """Reject malformed explicit PINs without including their values in errors."""
    if (
        type(pincode) is not str
        or len(pincode) != 4
        or any(digit not in "0123456789" for digit in pincode)
    ):
        msg = "pincode must be exactly four ASCII digits"
        raise ValueError(msg)


def _manifest_login_endpoint(data: dict[str, Any]) -> tuple[str, int]:
    """Require either a complete declared endpoint or legacy defaults."""
    if ("login_host" in data) != ("login_port" in data):
        msg = "login_host and login_port must be declared together"
        raise ValueError(msg)
    login_host = data.get("login_host", "127.0.0.1")
    login_port = data.get("login_port", 6900)
    _validate_login_endpoint(login_host, login_port)
    return login_host, login_port


def load_manifest(path: str | Path) -> dict[str, ManifestEntry]:
    """Parse a seed manifest (e.g. ``run/test-world-manifest.json``).

    Returns persona_id -> ManifestEntry; rows without a persona_id or with
    duplicate ids are skipped (first one wins), malformed rows are tolerated.
    Optional root login_host/login_port must be a complete validated IPv4 pair.
    Optional row pincode must be four ASCII digits, even on skipped rows.
    No endpoint declaration means legacy 127.0.0.1:6900, not native-world selection.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        msg = f"manifest {path} must be a JSON object"
        raise ValueError(msg)
    login_host, login_port = _manifest_login_endpoint(data)
    entries: dict[str, ManifestEntry] = {}
    for raw in data.get("accounts", []):
        if not isinstance(raw, dict):
            continue
        if "pincode" in raw:
            _validate_pincode(raw["pincode"])
        persona_id = raw.get("persona_id")
        account = raw.get("account")
        char_name = raw.get("char_name")
        if not persona_id or not account or persona_id in entries:
            continue
        entries[str(persona_id)] = ManifestEntry(
            str(persona_id),
            str(account),
            str(raw.get("password", "")),
            str(char_name or account),
            login_host=login_host,
            login_port=login_port,
            pincode=raw.get("pincode"),
        )
    if not entries:
        msg = f"manifest {path} maps no personas to accounts"
        raise ValueError(msg)
    return entries


def _require_native_session(client: Any) -> None:
    """Observe exposed native session readiness without promising atomic health."""
    msg = "native vitals unavailable"
    missing = object()
    for name in ("running", "connected_map"):
        flag = getattr(client, name, missing)
        if flag is not missing and flag is not True:
            raise NativeTelemetryUnavailable(msg)
    if getattr(client, "sock", missing) is None:
        raise NativeTelemetryUnavailable(msg)
    reader: Any = getattr(client, "rx_thread", missing)
    if reader is not missing and (reader is None or not reader.is_alive()):
        raise NativeTelemetryUnavailable(msg)


def _public_chat_events(agent: Any, client: Any) -> tuple[WorldEvent, ...]:
    """New 0x008D public lines as ChatHeard (the cursor on the agent)."""
    chat_model = getattr(client, "chat", None) or []
    actors = getattr(client, "actors", None) or {}
    events: list[WorldEvent] = []
    while agent._chat_seen < len(chat_model):
        gid, text = chat_model[agent._chat_seen]
        agent._chat_seen += 1
        if gid == getattr(client, "aid", None) or gid == getattr(client, "gid", None):
            continue  # account-ID sender or legacy senderless self tag
        actor = actors.get(gid) if isinstance(actors, dict) else None
        sender = str(actor.get("name", gid)) if isinstance(actor, dict) else str(gid)
        events.append(
            ChatHeard(
                line=ChatLine(channel="public", sender=sender, text=str(text), at=time.time())
            )
        )
    return tuple(events)


def _party_chat_events(agent: Any, client: Any) -> tuple[WorldEvent, ...]:
    """New 0x0109 party lines as ChatHeard (the premade reply loop's ear).

    Module-level so unbound-drain test hosts (SimpleNamespace agents) work;
    the cursor lives on the agent (``_party_chat_seen``).
    """
    cursor = getattr(agent, "_party_chat_seen", 0)
    party_log = getattr(client, "party_chat", None)
    if not isinstance(party_log, (list, tuple, deque)):
        return ()
    events: list[WorldEvent] = []
    while cursor < len(party_log):
        aid, name, text = party_log[cursor]
        cursor += 1
        if aid in (getattr(client, "aid", None), getattr(client, "gid", None)):
            continue  # our own line echoed back
        events.append(
            ChatHeard(
                line=ChatLine(channel="party", sender=str(name), text=str(text), at=time.time())
            )
        )
    agent._party_chat_seen = cursor
    return tuple(events)


@final
class ScheduledAgent:
    """One persona + one character + one brain + one client + one loop."""

    def __init__(
        self,
        persona: SocietyPersona,
        entry: ManifestEntry,
        *,
        brain: EventDrivenBrain | PlannedBrain | None = None,
        memory: Memory | None = None,
        client: Any | None = None,
        client_factory: Any | None = None,
        tick_clock: TickClock | None = None,
        world_state: WorldState | None = None,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
        heartbeat_min_s: float = HEARTBEAT_MIN_S,
        heartbeat_max_s: float = HEARTBEAT_MAX_S,
        rng: random.Random | None = None,
        threaded: bool = True,
        telemetry_wait_s: float = 5.0,
        wants: WantState | None = None,
        trace: TraceLog | None = None,
    ) -> None:
        if type(telemetry_wait_s) not in (int, float) or not 0 <= telemetry_wait_s <= 5:
            msg = "telemetry_wait_s must be a plain number from 0 to 5"
            raise ValueError(msg)
        self._telemetry_wait_s = telemetry_wait_s
        # Full-trace JSONL logging (None = no tracing, zero behavior change).
        self._trace = trace
        self._last_state_tick: float | None = None
        self.persona = persona
        self.entry = entry
        self.brain = brain
        self.memory = memory or Memory(StubSummarizer())
        self.client = client
        self._client_factory = client_factory
        self._tick_clock: TickClock = tick_clock or WallClock()
        self.world_state = world_state
        self.tick_seconds = tick_seconds
        self._heartbeat_min_s = heartbeat_min_s
        self._heartbeat_max_s = heartbeat_max_s
        self.rng = rng or random.Random()
        self._threaded = threaded
        self.wants = wants
        self._wants_clock: float | None = None
        self._wants_last_map: str | None = None
        self._wants_was_alive = True
        self.goal: Goal = Goal.GRIND
        self.online = False
        self._client_cleanup_pending = False
        self._startup_cleanup_uncertain = False
        self._producer_start_pending = False
        self.stop_flag = False
        self.thread: threading.Thread | None = None
        self.timers: TimerSet | None = None
        self.heartbeat_seq = 0
        self.tick_count = 0
        self._session_ticks = 0
        self._chat_seen = 0
        self._party_chat_seen = 0

        self.commands: HostChatCommands | None = None
        self._planning_binding: NpcHostBinding | None = None

    # ------------------------------------------------------------ lifecycle
    def connect(self) -> bool:
        """Open the game session, seed the brain, start the loop thread."""
        if self._connect_blocked():
            return False
        if self.online:
            return True
        try:
            self._invalidate_planning_binding()
            if self.client is None:
                self.client = self._new_client()
            self._client_cleanup_pending = True
            self.client.connect()
            self.stop_flag = False
            self._session_ticks = 0
            self._chat_seen = 0
            self._party_chat_seen = 0
            self.timers = TimerSet(self._tick_clock, self.rng)
            self.timers.add_periodic("idle_review", self._heartbeat_min_s, self._heartbeat_max_s)
            if self.brain is not None:
                try:
                    result = self._start_brain()
                except PlayingBackendError as exc:
                    # The transport session is authenticated and telemetry-verified;
                    # a decision-backend outage must not discard it (window 32: this
                    # teardown caused infinite re-login churn). Keep the session and
                    # let the replan machinery retry once the backend returns.
                    logger.error(
                        "agent %s: decision backend unavailable at startup; "
                        "session kept for retry (%s)",
                        self.persona.persona_id,
                        type(exc).__name__,
                    )
                    result = TickResult((), {})
                self._apply_goal_notes(getattr(result, "notes", ()))
                self.execute_actions(result.actions)
            self.online = True
            self._publish()
            self.world_note("connected")
            if self._threaded:
                self.thread = threading.Thread(
                    target=self._run_loop, name=f"agent-{self.persona.persona_id}", daemon=True
                )
                self._producer_start_pending = True
                self.thread.start()
                self._producer_start_pending = False
        except BaseException as exc:
            self.stop_flag = True
            self._failed_startup_cleanup(exc)
            if not isinstance(exc, Exception) or self._producer_start_pending:
                raise
            logger.error(
                "agent %s: connect failed (%s)", self.persona.persona_id, type(exc).__name__
            )
            return False
        logger.info("agent %s online as %s", self.persona.persona_id, self.entry.char_name)
        return True

    def disconnect(self) -> None:
        """Gracefully end the session; the session is a memory (ADR-004)."""
        self.stop_flag = True
        if self.commands is not None:
            self.commands.cancel_pending(self.persona.persona_id)
        if not self._cleanup_due():
            return
        self.stop_flag = True
        thread = self.thread
        if thread is not None:
            timeout = 0 if self._producer_start_pending else None
            _join_producer(thread, f"agent {self.persona.persona_id}", timeout=timeout)
        self.thread = None
        self._producer_start_pending = False
        errors: list[BaseException] = []
        if self.online:
            self._client_cleanup_pending = True
            try:
                self.memory.remember(
                    "session",
                    f"session ended after {self._session_ticks} ticks as {self.entry.char_name}",
                    ts=time.time(),
                )
            except BaseException as exc:
                errors.append(exc)
            self.online = False
        self._close_planning(errors)
        closed = self._finish_client_cleanup(errors)
        cleanups: tuple[Callable[[], None], ...] = (self._publish,)
        if closed:
            cleanups += (lambda: self.world_note("disconnected"),)
            logger.info("agent %s offline", self.persona.persona_id)
        for cleanup in cleanups:
            try:
                cleanup()
            except BaseException as exc:
                errors.append(exc)
        _raise_cleanup_errors(errors)

    def _connect_blocked(self) -> bool:
        return (
            self._producer_start_pending
            or self._startup_cleanup_uncertain
            or not self._planning_reconnect_ready()
        )

    def _planning_reconnect_ready(self) -> bool:
        return not isinstance(self.brain, PlannedBrain) or self.brain.reconnect_ready

    def _cleanup_due(self) -> bool:
        return self._client_cleanup_due() or not self._planning_reconnect_ready()

    def _start_brain(self) -> TickResult:
        self._invalidate_planning_binding()
        self._wait_for_telemetry()
        brain = self.brain
        if brain is None:
            return TickResult((), {})
        if isinstance(brain, PlannedBrain):
            pose_reader = (
                self.client.planning_rest_observation
                if isinstance(self.client, PlayingClient)
                else None
            )
            npc_reader = (
                self.client.planning_npc_observation
                if isinstance(self.client, PlayingClient)
                else None
            )
            npc_ui_reader = (
                self.client.planning_npc_ui if isinstance(self.client, PlayingClient) else None
            )
            brain.bind_session(self._tick_clock.monotonic, pose_reader, npc_reader, npc_ui_reader)
            if isinstance(self.client, PlayingClient):
                self._planning_binding = NpcHostBinding(
                    self.client, self.client.wire, self.client.planning_session
                )
        return brain.start(self.build_state())

    def _invalidate_planning_binding(self) -> None:
        self._planning_binding = None
        if isinstance(self.brain, PlannedBrain):
            self.brain.invalidate_binding()

    def _ensure_planning_binding(self) -> bool:
        binding = self._planning_binding
        client = self.client
        if binding is None:
            return False
        if not isinstance(client, PlayingClient) or not binding.matches(
            client, client.wire, client.planning_session
        ):
            self._invalidate_planning_binding()
            return False
        return True

    def _planning_context_lost(self) -> None:
        if isinstance(self.brain, PlannedBrain):
            self.brain.sync_context(None)

    def _close_planning(self, errors: list[BaseException]) -> None:
        self._planning_binding = None
        if isinstance(self.brain, PlannedBrain):
            try:
                self.brain.close()
            except BaseException as exc:
                errors.append(exc)

    def _client_cleanup_due(self) -> bool:
        """Startup close uncertainty blocks retries, not ownership retention."""
        return not self._startup_cleanup_uncertain and (self.online or self._client_cleanup_pending)

    def _finish_client_cleanup(self, errors: list[BaseException]) -> bool:
        """Release independently of session state; retain uncertain cleanup for retry."""
        try:
            self._close_client(suppress_errors=False)
        except BaseException as exc:
            errors.append(exc)
            # An explicit released-state signal can confirm an after-release failure.
            # Unknown clients remain pending: offline is not evidence of release.
            self._client_cleanup_pending = getattr(self.client, "connected", None) is not False
            return False
        self._client_cleanup_pending = False
        return True

    def _failed_startup_cleanup(self, origin: BaseException) -> None:
        """Preserve startup origin; never retry an uncertain startup close."""
        errors: list[BaseException] = []
        self._reap_startup_producer(errors)
        if not self._producer_start_pending:
            self._close_planning(errors)
        self.online = False
        if self._client_cleanup_pending and not self._producer_start_pending:
            self._startup_cleanup_uncertain = not self._finish_client_cleanup(errors)
        try:
            self._publish()
        except BaseException as exc:
            errors.append(exc)
        for error in errors:
            with suppress(BaseException):
                origin.add_note(
                    f"startup cleanup failed ({type(error).__name__}); release unconfirmed"
                )
            logger.error(
                "agent %s: startup cleanup failed (%s)",
                self.persona.persona_id,
                type(error).__name__,
            )

    def _reap_startup_producer(self, errors: list[BaseException]) -> None:
        """A start interruption may precede ident publication; only join proves release."""
        thread = self.thread
        if thread is None:
            return
        try:
            _join_producer(thread, f"agent {self.persona.persona_id}", timeout=0)
        except BaseException as exc:
            errors.append(exc)
            return
        self.thread = None
        self._producer_start_pending = False

    def _new_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory(self.entry)
        if _BotClient is not None:
            wire = _BotClient(
                self.entry.account,
                self.entry.password,
                char_name=self.entry.char_name,
                verbose=False,
                login_ip=self.entry.login_host,
                login_port=self.entry.login_port,
                pincode=self.entry.pincode,
            )
            return PlayingClient(wire)
        msg = "no BotClient (spike 003 import failed) and no client_factory"
        raise RuntimeError(msg)

    def _close_client(self, *, suppress_errors: bool = True) -> None:
        if self.client is not None:
            try:
                self.client.close()
            except Exception as exc:
                if not suppress_errors:
                    raise
                logger.warning("agent %s: close failed: %s", self.persona.persona_id, exc)

    def world_note(self, what: str) -> None:
        """One 'session' line into the WorldFeed event feed (if wired)."""
        if self.world_state is not None:
            self.world_state.push_event(
                "session", f"{self.persona.persona_id} {what} as {self.entry.char_name}"
            )

    # ------------------------------------------------------------ tick loop
    def _run_loop(self) -> None:
        """The BotRunner-equivalent: tick until the schedule closes the window."""
        try:
            while not self.stop_flag:
                try:
                    self.tick()
                except Exception:
                    logger.exception("agent %s: tick failed", self.persona.persona_id)
                self._tick_clock.sleep(self.tick_seconds)
        except BaseException:
            # Refuse new work without pretending the client/journal were released.
            # Never take the host lifecycle lock: stop may hold it while joining us.
            self.stop_flag = True
            if self.commands is not None:
                try:
                    self.commands.cancel_pending(self.persona.persona_id)
                except BaseException as cleanup_error:
                    logger.error(
                        "agent %s: cancellation failed (%s)",
                        self.persona.persona_id,
                        type(cleanup_error).__name__,
                    )
            raise

    def tick(self) -> None:
        """One tick: world events -> brain, timers -> brain, script -> actions."""
        if self.commands is not None:
            for _ in range(64):
                request = self.commands.take(self.persona.persona_id)
                if request is None:
                    break
                self._dispatch_chat(request)
        if self.client is None or self.brain is None:
            return
        self._ensure_planning_binding()
        try:
            state = self.build_state()
        except NativeTelemetryUnavailable:
            self._planning_context_lost()
            return
        self.tick_count += 1
        self._session_ticks += 1
        self._trace_state_tick(state)
        for event in self._drain_events():
            self.deliver_event(state, event)
        timers = self.timers
        if timers is not None:
            for fired in timers.fire_due(self._tick_clock.monotonic()):
                self.deliver_event(state, self._as_heartbeat(fired))
        self._advance_script(state)
        self._publish(state)
        self._idle_watch(state)

    def _advance_script(self, state: BotState) -> None:
        brain = self.brain
        if brain is None:
            return
        context = getattr(brain, "sync_context", None)
        if context is not None:
            context(state)
        if isinstance(brain, PlannedBrain):
            outcome = brain.step_script(state)
            self.execute_actions(outcome.actions)
            if brain.stand_barrier is not None and isinstance(self.client, PlayingClient):
                self.client.planning_rest_ready(brain.stand_barrier)
            return
        if not getattr(brain, "is_recovering", False):
            outcome = brain.step_script(state)
            self.execute_actions(self._script_actions(state, outcome.actions))
            return
        ready = getattr(self.client, "recovery_ready", None)
        can_resume = True
        if ready is not None and brain.recovery_health_ready(state):
            can_resume = bool(ready(hp_ratio=brain.required_recovery_hp_ratio))
        outcome = brain.step_script(state, can_resume=can_resume)
        self.execute_actions(self._script_actions(state, outcome.actions))

    def _script_actions(
        self, state: BotState, actions: tuple[GameAction, ...]
    ) -> tuple[GameAction, ...]:
        if getattr(self.brain, "mechanical_fallback_allowed", True) is False:
            return actions
        if getattr(self.brain, "current_plan", None) is not None:
            # An authored plan owns the action stream; client-side mechanical
            # fallbacks (novice exploration) must not override its actions.
            return actions
        if getattr(self.brain, "is_recovering", False):
            return actions
        mechanical = getattr(self.client, "mechanical_actions", None)
        return (
            cast(tuple[GameAction, ...], mechanical(state, actions))
            if mechanical is not None
            else actions
        )

    def _dispatch_chat(self, request: ChatRequest) -> None:
        commands = self.commands
        if commands is None:
            return
        client = self.client
        if client is None:
            commands.finish(request, "failed", error_class="ClientUnavailable")
            return
        try:
            self.memory.remember(
                "session",
                f"operator {request.command_id} chat intent: {request.text}",
                ts=request.ts,
            )
        except BaseException as exc:
            commands.finish(request, "failed", audit_error_class=type(exc).__name__)
            if not isinstance(exc, Exception):
                raise
            return
        if not commands.begin_send(request):
            return
        try:
            client.say(request.text)
        except BaseException as exc:
            commands.finish(request, "uncertain", error_class=type(exc).__name__)
            if not isinstance(exc, Exception):
                raise
            return
        try:
            self.memory.remember(
                "chat",
                f"operator {request.command_id} dispatched (not confirmed): {request.text}",
                ts=time.time(),
            )
        except BaseException as exc:
            commands.finish(request, "dispatched", audit_error_class=type(exc).__name__)
            if not isinstance(exc, Exception):
                raise
            return
        commands.finish(request, "dispatched")

    def _idle_watch(self, state: BotState) -> None:
        """Synthesize an idle-review decide when no action has executed for
        IDLE_REVIEW_S. An agent that just stands there — no mobs, no plan
        progress, no script output — must re-plan (and may socialize) rather
        than wait out the heartbeat timer (the user directive: <= 5 minutes
        without doing something)."""
        now = self._tick_clock.monotonic()
        last = getattr(self, "_last_action_monotonic", None)
        if last is None:
            self._last_action_monotonic = now
            return
        if now - last < IDLE_REVIEW_S:
            return
        self._last_action_monotonic = now
        if self.brain is None or self.client is None:
            return
        logger.info(
            "agent %s: idle %.0fs; forcing goal review", self.persona.persona_id, now - last
        )
        self.deliver_event(
            state, self._as_heartbeat(TimerFired(name="idle_review", seq=0)), trigger="idle_review"
        )

    def deliver_event(
        self, state: BotState, event: WorldEvent, *, trigger: str | None = None
    ) -> None:
        """Hand one event to the brain and execute the resulting actions.

        ``trigger`` labels the review provenance in the trace (the idle watch
        passes "idle_review"; None lets the brain derive it from the event).
        """
        self._trace_event(state, event)
        self._observe_wants(state)
        if self.brain is None:
            return
        self._ensure_planning_binding()
        if isinstance(self.brain, EventDrivenBrain):
            result = self.brain.handle_event(state, event, trigger=trigger)
        else:
            result = self.brain.handle_event(state, event)
        self._apply_goal_notes(result.notes)
        self.execute_actions(result.actions)

    def _observe_wants(self, state: BotState) -> None:
        """Runtime-side want observation (design section 5 items 2-3).

        Time-based decay runs on the agent's own clock at each delivered
        event; state-only diffs (map change, death, low HP) satisfy here.
        The brain applies what arrives as WorldEvents (chat, invites, mob
        sightings) plus its party/level diffs.
        """
        wants = self.wants
        if wants is None:
            return
        now = self._tick_clock.monotonic()
        if self._wants_clock is None:
            self._wants_clock = now
        elif now > self._wants_clock:
            wants.decay((now - self._wants_clock) / 3600.0)
            self._wants_clock = now
        if state.map_name != self._wants_last_map:
            if self._wants_last_map is not None:
                WantSatisfier.apply(wants, WantEvent("map_change", name=state.map_name))
            self._wants_last_map = state.map_name
        alive = state.alive is not False
        if self._wants_was_alive and not alive:
            WantSatisfier.apply(wants, WantEvent("death"))
        self._wants_was_alive = alive
        if state.hp_ratio < 0.25:
            WantSatisfier.apply(wants, WantEvent("hp_low"))

    def _apply_goal_notes(self, notes: tuple[str, ...]) -> None:
        for note in notes:
            goal = self._goal_from_note(note)
            if goal is not None:
                self.goal = goal

    def execute_actions(self, actions: tuple[GameAction, ...]) -> None:
        """Push brain/script actions through the client's limbs."""
        if self.client is None:
            return
        if actions:
            self._last_action_monotonic = self._tick_clock.monotonic()
        for action in actions:
            self._trace_action(action)
            try:
                self._perform(action)
            except Exception as exc:
                logger.warning(
                    "agent %s: action %s failed: %s",
                    self.persona.persona_id,
                    type(action).__name__,
                    exc,
                )

    # ------------------------------------------------------------- tracing
    def _trace_context(self) -> dict[str, Any]:
        """The self-contained context block, from the CACHED built state.

        Reads ``last_built_state`` (the view the tick already built) — never a
        fresh observing read, which would starve the runtime's event windows.
        """
        state = getattr(self.client, "last_built_state", None)
        if state is None:
            return {"map": None, "x": None, "y": None}
        return {"map": state.map_name, "x": state.x, "y": state.y}

    def _trace_state_tick(self, state: BotState) -> None:
        """The bounded periodic snapshot (about one per interval of ticks)."""
        trace = self._trace
        if trace is None:
            return
        now = self._tick_clock.monotonic()
        last = self._last_state_tick
        if last is not None and now - last < STATE_TICK_INTERVAL_S:
            return
        self._last_state_tick = now
        trace.log(
            "state_tick",
            map=state.map_name,
            x=state.x,
            y=state.y,
            hp=state.hp,
            hp_max=state.max_hp,
            sp=state.sp,
            sp_max=state.max_sp,
            base_level=state.base_level,
            zeny=state.zeny,
            inventory_counts=dict(state.inventory),
            adjacent_monsters=len(state.nearby_monsters),
            online=self.online,
        )

    def _trace_event(self, state: BotState, event: WorldEvent) -> None:
        """Every delivered WorldEvent (plus the chat_heard alias), pre-brain."""
        trace = self._trace
        if trace is None:
            return
        context = {"map": state.map_name, "x": state.x, "y": state.y}
        trace.log(
            "world_event",
            **context,
            adjacent_monsters=len(state.nearby_monsters),
            **event_payload(event),
        )
        if isinstance(event, ChatHeard):
            trace.log(
                "chat_heard",
                **context,
                speaker=event.line.sender,
                message=event.line.text,
                channel=event.line.channel,
            )

    def _trace_action(self, action: GameAction) -> None:
        """Every executed action; Say/PartyChat/WhisperTo also alias chat_sent."""
        trace = self._trace
        if trace is None:
            return
        trace.log(
            "action_executed",
            **self._trace_context(),
            action=type(action).__name__,
            params=action_params(action),
        )
        if isinstance(action, (Say, PartyChat, WhisperTo)):
            trace.log(
                "chat_sent",
                **self._trace_context(),
                channel=chat_channel(action),
                message=action.text,
                action=type(action).__name__,
            )

    def _perform(self, action: GameAction) -> None:
        if self._perform_planned_npc(action):
            return
        client = self.client
        if client is None:
            return
        native = getattr(client, "perform_native", None)
        if native is not None:
            native(action)
            return
        self._perform_legacy(client, action)

    def _perform_guild_legacy(self, client: Any, action: GameAction) -> bool:
        """The guild limbs for the legacy host; True = handled."""
        match action:
            case AcceptGuildInvite():
                ggid = getattr(client, "guild_invite_gid", 0)
                if ggid:
                    client.guild_reply(ggid, True)
                return True
            case FoundGuild(name=name):
                client.guild_create(name)
                client.guild_created = True
                return True
            case GuildInvite(player=player):
                target = client.party_members.get(player)
                if target:
                    client.guild_invite(target, client.aid, client.gid)
                return True
            case _:
                return False

    def _perform_legacy(self, client: Any, action: GameAction) -> None:
        match action:
            case MoveTo(x=x, y=y):
                client.move(x, y)
            case Say(text=text):
                client.say(text)
                self.memory.remember("chat", f"said: {text}", ts=time.time())
            case PartyChat(text=text):
                # party chat limb is under repair (spike 003); speak publicly
                client.say(text)
                self.memory.remember("chat", f"party-said: {text}", ts=time.time())
            case Rest():
                client.sit()
            case AcceptInvite():
                pid = getattr(client, "party_invite_pid", 0)
                if pid:
                    client.party_reply(pid, True)
            case InviteToParty(player=player):
                client.party_invite(player)
            case AcceptGuildInvite() | FoundGuild() | GuildInvite():
                self._perform_guild_legacy(client, action)
            case _:
                logger.debug(
                    "agent %s: no limb for %s", self.persona.persona_id, type(action).__name__
                )

    def _perform_planned_npc(self, action: GameAction) -> bool:
        brain = self.brain
        if not isinstance(action, NpcRespond) or not isinstance(brain, PlannedBrain):
            return False
        if not self._ensure_planning_binding() or not brain.npc_action_current(action):
            brain.npc_dispatched(action, None)
            return True
        client = self.client
        if not isinstance(client, PlayingClient):
            brain.npc_dispatched(action, None)
            return True
        try:
            client.perform_native(action)
        finally:
            brain.npc_dispatched(action, client.local_npc_dispatch)
        return True

    # -------------------------------------------------- world model mapping
    def _wait_for_telemetry(self) -> None:
        """Bound only status readiness, separately from the native connect deadline."""
        deadline = self._tick_clock.monotonic() + self._telemetry_wait_s
        while True:
            try:
                self._native_vitals()
                if getattr(self.client, "build_native_state", None) is not None:
                    self.build_state()
                return
            except NativeTelemetryUnavailable:
                remaining = deadline - self._tick_clock.monotonic()
                if remaining <= 0:
                    raise
                self._tick_clock.sleep(min(0.05, remaining))

    def _native_vitals(self) -> NativeVitals:
        """Require current status and reject explicit transport/dispatch failure."""
        msg = "native vitals unavailable"
        client = self.client
        health = getattr(client, "is_healthy", None)
        if (
            getattr(client, "rx_error", None)
            or getattr(client, "dispatch_errors", None)
            or (health is not None and not health())
        ):
            raise NativeTelemetryUnavailable(msg)
        _require_native_session(client)
        parameters = getattr(self.client, "status_params", None)
        if not isinstance(parameters, Mapping):
            raise NativeTelemetryUnavailable(msg)
        return require_native_vitals(parameters)

    def build_state(self) -> BotState:
        """Snapshot a BotState from the client's world model.

        Maps what the clientless world model carries (position, map, actors,
        chat, party); job/level/inventory are not on the wire yet, so they are
        filled from the persona (level) or left neutral.
        """
        client = self.client
        if client is None:
            msg = f"agent {self.persona.persona_id} has no client"
            raise RuntimeError(msg)
        native = getattr(client, "build_native_state", None)
        if native is not None:
            return cast(BotState, native(self.goal))
        return self._legacy_state()

    def _legacy_state(self) -> BotState:
        """Compatibility for explicitly injected legacy simulation clients only."""
        client = self.client
        actors = getattr(client, "actors", None) or {}
        vitals = self._native_vitals()
        nearby = tuple(
            ActorRef(id=int(gid), name=str(info.get("name", gid)), kind="player", distance=1.0)
            for gid, info in list(actors.items())[:8]
        )
        chat_model = getattr(client, "chat", None) or []
        recent = tuple(
            ChatLine(channel="public", sender=str(gid), text=str(text), at=0.0)
            for gid, text in list(chat_model)[-5:]
        )
        return BotState(
            name=str(getattr(client, "char_name", None) or self.entry.char_name),
            job="Novice",
            base_level=self.persona.level_band[0],
            hp=vitals.hp,
            max_hp=vitals.max_hp,
            sp=vitals.sp,
            max_sp=vitals.max_sp,
            map_name=str(getattr(client, "map_name", None) or "prontera"),
            x=int(getattr(client, "x", 0) or 0),
            y=int(getattr(client, "y", 0) or 0),
            goal=self.goal,
            in_party=bool(getattr(client, "party_id", 0)),
            nearby=nearby,
            inventory={},
            pending_invites=(),
            recent_chat=recent,
        )

    def _drain_events(self) -> tuple[WorldEvent, ...]:
        """Map new client world-model entries into brain events."""
        client = self.client
        if client is None:
            return ()
        events: list[WorldEvent] = []
        native = getattr(client, "drain_native_events", None)
        if native is not None:
            events.extend(native())
        events.extend(_public_chat_events(self, client))
        events.extend(_party_chat_events(self, client))
        return tuple(events)

    def _as_heartbeat(self, event: WorldEvent) -> WorldEvent:
        """Timer fires are the ADR-002 random heartbeat (goal review clock)."""
        if isinstance(event, TimerFired) and event.name == "idle_review":
            self.heartbeat_seq += 1
            return Heartbeat(seq=self.heartbeat_seq)
        return event

    @staticmethod
    def _goal_from_note(note: str) -> Goal | None:
        """Parse a brain ``goal grind->social`` note (best effort)."""
        if not note.startswith("goal "):
            return None
        new = note.split("->", 1)[-1].split(" ", 1)[0]
        try:
            return Goal(new)
        except ValueError:
            return None

    # ---------------------------------------------------------- publishing
    def _publish(self, state: BotState | None = None) -> None:
        """Push the real runtime state into the WorldState (dashboard)."""
        ws = self.world_state
        if ws is None:
            return
        script = self.brain.current_script() if self.brain is not None else None
        plan = self.brain.current_plan if self.brain is not None else None
        ws.set_agent_state(
            self.persona.persona_id,
            current_goal=state.goal.value if state is not None else self.goal.value,
            current_script=type(script).__name__ if script is not None else "",
            current_plan=(
                f"farm {', '.join(plan.target_mobs)} on {plan.map_name}" if plan is not None else ""
            ),
            online=self.online,
        )


def meet_when_for(persona_id: str, population: GeneratedPopulation) -> str | None:
    """The rendezvous time hint for one agent: the group's window start (HH:MM).

    The group's window is its FIRST registered member's first window (the same
    rule ``build_roster`` applies to configured schedule files); solos derive
    from their own first window. Personas absent from the population derive
    nothing (``None``), which leaves the BoundCoordinator's rendezvous hint
    unset.
    """
    persona = next((p for p in population.personas if p.persona_id == persona_id), None)
    if persona is None:
        return None
    if persona.group_id is not None:
        members = [p for p in population.personas if p.group_id == persona.group_id]
        if members:
            persona = members[0]
    for window in persona.schedule:
        return _format_hhmm(window[1])
    return None


def _format_hhmm(hour: float) -> str:
    """A fractional schedule hour as HH:MM (the quarter-hour grid stays exact)."""
    whole = int(hour)
    minute = round((hour - whole) * 60)
    if minute >= 60:
        whole, minute = whole + 1, minute - 60
    return f"{whole % 24:02d}:{minute:02d}"


@final
class AgentHost:
    """Orchestrates N scheduled agents against the live server + WorldFeed."""

    def __init__(
        self,
        roster: SocietyRoster,
        manifest_path: str | Path,
        *,
        clef_url: str | None = None,
        decision_factory: Any | None = None,
        chat_generator: ChatGenerator | None = None,
        chat_url: str = DEFAULT_CHAT_URL,
        worldfeed_port: int = DEFAULT_WORLDFEED_PORT,
        run_worldfeed: bool = True,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
        heartbeat_min_s: float = HEARTBEAT_MIN_S,
        heartbeat_max_s: float = HEARTBEAT_MAX_S,
        clock: SocietyClock | None = None,
        rng: random.Random | None = None,
        client_factory: Any | None = None,
        mob_db_factory: Any | None = None,
        spawn_species_factory: Any | None = None,
        world_state: WorldState | None = None,
        memory_root: Path | None = None,
        summary_cache_world: str | None = None,
        summary_cache_policy: str | None = None,
        max_agents: int = 0,
        population: GeneratedPopulation | None = None,
        population_file: str | Path | None = None,
        meet_where: str | None = "prontera 156,22",
        meet_when: str | None = None,
        brain_factory: (
            Callable[[SocietyPersona, ManifestEntry, Memory], PlannedBrain] | None
        ) = None,
        trace_dir: str | Path | None = None,
    ) -> None:
        validate_summary_cache(memory_root, summary_cache_world, summary_cache_policy)
        self.roster = roster
        self.clock = clock or PersonaClock()
        self.rng = rng or random.Random()
        self.manifest = load_manifest(manifest_path)
        self.tick_seconds = tick_seconds
        self.client_factory = client_factory
        self._mob_db_factory = mob_db_factory
        self._spawn_species_factory = spawn_species_factory
        self._brain_factory = brain_factory
        self.memory_root = memory_root
        self.summary_cache_world = summary_cache_world
        self.summary_cache_policy = summary_cache_policy
        self.worldfeed_port = worldfeed_port
        self._run_worldfeed = run_worldfeed
        self._heartbeat_range = (heartbeat_min_s, heartbeat_max_s)
        self._stop = False
        self._lifecycle_lock = threading.RLock()
        self._worldfeed_server: Any | None = None
        self._worldfeed_thread: threading.Thread | None = None
        # The social coordination inputs: a GeneratedPopulation (or its
        # population.json) turns on the per-agent coordination wiring; without
        # one, brains keep coordination=None (today's behavior).
        self._population = (
            population
            if population is not None
            else (load_population(population_file) if population_file is not None else None)
        )
        self._meet_where = meet_where
        self._meet_when = meet_when
        self._ledgers: dict[str, RelationshipLedger] = {}
        # Full-trace JSONL logging: per-persona files under trace_dir; None
        # keeps today's behavior (no tracing, no files, no wrapping).
        self.trace_dir = Path(trace_dir) if trace_dir is not None else None
        self._traces: dict[str, TraceLog] = {}
        self._decision_factory = decision_factory or self._select_decision_factory(clef_url)
        self.chat = chat_generator or self._autodetect_chat(chat_url)
        self.world_state: WorldState | None = world_state or self._default_world_state(roster)
        self._warn_missing_personas(roster)
        self.agents: dict[str, ScheduledAgent] = {}
        self._populate_agents(max_agents)
        self.commands = HostChatCommands(self.agents)
        for agent in self.agents.values():
            agent.commands = self.commands

    def _populate_agents(self, max_agents: int) -> None:
        persona_ids = sorted(pid for pid in self.manifest if pid in self.roster.personas)
        if max_agents > 0:
            persona_ids = persona_ids[:max_agents]
        try:
            for persona_id in persona_ids:
                self.agents[persona_id] = self._build_agent(self.roster.personas[persona_id])
        except BaseException as origin:
            for agent in self.agents.values():
                _close_failed_memory(origin, agent.memory.close)
            raise

    def _select_decision_factory(self, clef_url: str | None) -> Any:
        """CLEF_URL -> ClefLocal factory; else the deterministic stub factory."""
        if clef_url:
            return self._make_clef_factory(clef_url)
        return self._make_stub_factory()

    def _default_world_state(self, roster: SocietyRoster) -> WorldState | None:
        """Construct the aggregate unless world_state.py is somehow missing."""
        if WorldState is not None:
            return WorldState(roster)
        return None  # pragma: no cover - world_state is landed; toleration only

    def _warn_missing_personas(self, roster: SocietyRoster) -> None:
        missing = [p for p in roster.personas if p not in self.manifest]
        if missing:
            logger.warning("manifest has no account for personas: %s", ", ".join(missing))

    @staticmethod
    def _make_clef_factory(url: str) -> Any:
        def factory() -> DecisionModel:
            return ClefLocal(url)

        return factory

    @staticmethod
    def _make_stub_factory() -> Any:
        def factory() -> DecisionModel:
            return ScriptedDecisionModel(answers=dict(DEFAULT_STUB_ANSWERS))

        return factory

    @staticmethod
    def _autodetect_chat(chat_url: str) -> ChatGenerator:
        """LocalChatServer if a llama-server listens on chat_url, else static."""
        parsed = urllib.parse.urlsplit(chat_url)
        try:
            with socket.create_connection(
                (parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=0.5
            ):
                pass
            logger.info("local llama-server reachable; using LocalChatServer")
            return LocalChatServer(chat_url)
        except OSError:
            logger.info("no local llama-server; using StaticChatGenerator")
            return StaticChatGenerator()

    def _build_agent(self, persona: SocietyPersona) -> ScheduledAgent:
        memory = self._new_memory(persona.persona_id)
        trace = self._open_trace(persona.persona_id)
        try:
            if self.world_state is not None:
                self.world_state.bind_memory(persona.persona_id, memory.log)
            wants = self._new_want_state(persona)
            social_view, coordination = self._new_coordination(persona.persona_id)
            # Trace wiring: the same TraceLog feeds the runtime taps, the
            # brain's review/plan lines and the transparent decide/LLM
            # proxies. A custom brain_factory owns its own model, so the
            # wrappers apply to the EventDrivenBrain path only.
            model: Any = self._decision_factory()
            chat: Any = self.chat
            if trace is not None:
                model = TracedDecisionModel(model, trace)
                chat = TracedChatGenerator(chat, trace)
            return ScheduledAgent(
                persona,
                self.manifest[persona.persona_id],
                brain=(
                    self._brain_factory(persona, self.manifest[persona.persona_id], memory)
                    if self._brain_factory is not None
                    else EventDrivenBrain(
                        model,
                        chat,
                        memory=memory,
                        mob_db=(
                            self._mob_db_factory(persona.persona_id)
                            if self._mob_db_factory
                            else None
                        ),
                        spawn_species=self._spawn_species_factory,
                        wants=wants,
                        social_view=social_view,
                        coordination=coordination,
                        trace=trace,
                    )
                ),
                memory=memory,
                client_factory=self.client_factory,
                world_state=self.world_state,
                tick_seconds=self.tick_seconds,
                heartbeat_min_s=self._heartbeat_range[0],
                heartbeat_max_s=self._heartbeat_range[1],
                rng=random.Random(self.rng.getrandbits(64)),
                wants=wants,
                trace=trace,
            )
        except BaseException as origin:
            _close_failed_memory(origin, memory.close)
            if trace is not None:
                _close_failed_memory(origin, trace.close)
            raise

    def _open_trace(self, persona_id: str) -> TraceLog | None:
        """The persona's TraceLog; an unusable dir disables tracing (fails open)."""
        if self.trace_dir is None:
            return None
        try:
            trace = TraceLog(self.trace_dir, persona_id)
        except OSError as exc:
            logger.warning("trace disabled for %s (%s)", persona_id, exc)
            return None
        self._traces[persona_id] = trace
        return trace

    @staticmethod
    def _new_want_state(persona: SocietyPersona) -> WantState | None:
        """One WantState per agent, from the persona's assigned personality.

        An unknown personality string keeps the agent want-less (log, no
        crash) — the want layer is motivational garnish, never a hard
        dependency of the session loop.
        """
        try:
            return WantState(Personality(persona.personality))
        except ValueError:
            logger.warning(
                "persona %s: unknown personality %r; wants disabled",
                persona.persona_id,
                persona.personality,
            )
            return None

    def _new_memory(self, persona_id: str) -> Memory:
        summarizer = StubSummarizer()
        raw = (
            JsonlExperienceStore(self.memory_root, persona_id)
            if self.memory_root is not None
            else None
        )
        if self.summary_cache_world is None:
            return Memory(summarizer, store=raw)
        try:
            cache = JsonlSummaryNodeStore(
                cast(Path, self.memory_root),
                self.summary_cache_world,
                persona_id,
                cast(str, self.summary_cache_policy),
            )
        except BaseException as origin:
            if raw is not None:
                _close_failed_memory(origin, raw.close)
            raise
        # Memory owns both stores from entry, including failed restore cleanup.
        return Memory(summarizer, store=raw, summary_store=cache)

    def _new_coordination(
        self, persona_id: str
    ) -> tuple[Callable[[], Sequence[str]] | None, BoundCoordinator | None]:
        """The per-agent social coordination wiring (None without a population).

        The ledger persists under ``memory_root/relations/`` (restore on
        construction = reconnect continuity), the roster is injected at
        creation (meta-knowledge only — no coordination message ever travels
        this channel), and the online provider reads ``self.agents`` LIVE: the
        agents reconnect, so a cached list would lie.
        """
        population = self._population
        if population is None:
            return None, None
        ledger = RelationshipLedger(persona_id, path=self._relations_path(persona_id))
        seed_roster(ledger, population)
        ledger.save()  # the injected roster is durable from the first start
        self._ledgers[persona_id] = ledger

        def online_members() -> tuple[str, ...]:
            return tuple(pid for pid, agent in self.agents.items() if agent.online)

        bound = BoundCoordinator(
            GroupCoordinator(ledger, persona_id),
            online=online_members,
            meet_where=self._meet_where,
            meet_when=(
                self._meet_when
                if self._meet_when is not None
                else meet_when_for(persona_id, population)
            ),
        )

        def social_view() -> tuple[str, ...]:
            return tuple(ledger.context_lines(persona_id, online_members=online_members()))

        return social_view, bound

    def _relations_path(self, persona_id: str) -> Path | None:
        """The persisted ledger file; an ephemeral host keeps memory only."""
        if self.memory_root is None:
            return None
        return self.memory_root / "relations" / f"{persona_id}.json"

    def _save_ledgers(self, errors: list[BaseException]) -> None:
        """Persist every relationship ledger (the reconnect-continuity carrier)."""
        for ledger in self._ledgers.values():
            try:
                ledger.save()
            except BaseException as exc:
                errors.append(exc)

    # ------------------------------------------------------------- schedule
    def _scheduled_on(self, persona_id: str, now: tuple[int, float]) -> bool:
        group = next((g for g in self.roster.groups if persona_id in g.member_ids), None)
        if group is None:
            return False
        return group.schedule.is_online(now)

    def step(self) -> None:
        """One scheduling pass: open/close sessions per each persona's schedule."""
        with self._lifecycle_lock:
            if self._stop:
                return
            now = self.clock.local_now()
            for persona_id, agent in self.agents.items():
                scheduled = self._scheduled_on(persona_id, now)
                if scheduled and not agent.online:
                    logger.info("schedule window open: connecting %s", persona_id)
                    agent.connect()
                elif not scheduled and agent.online:
                    logger.info("schedule window closed: disconnecting %s", persona_id)
                    agent.disconnect()

    def run(self, poll_seconds: float = 5.0) -> None:
        """Schedule forever (until :meth:`stop`); one last pass when stopped."""
        self.start_worldfeed()
        while True:
            self.step()
            if self._stop:
                break
            time.sleep(poll_seconds)

    def stop(self) -> None:
        """Join producers, release journals, then report any shutdown failures."""
        with self._lifecycle_lock:
            self._stop = True
            self.commands.stop()
            # Signal every producer before waiting on the first blocked worker.
            for agent in self.agents.values():
                agent.stop_flag = True
            errors: list[BaseException] = []
            for agent in self.agents.values():
                try:
                    agent.disconnect()
                except BaseException as exc:
                    errors.append(exc)
            try:
                self.shutdown_worldfeed()
            except BaseException as exc:
                errors.append(exc)
            self._save_ledgers(errors)
            self._close_memories(errors)
            self._close_traces(errors)
            _raise_cleanup_errors(errors)

    def _close_memories(self, errors: list[BaseException]) -> None:
        if any(agent._producer_start_pending for agent in self.agents.values()):
            # is_alive=False/ident=None cannot disprove a launched, unpublished worker.
            return
        producers = [agent.thread for agent in self.agents.values()]
        producers.append(self._worldfeed_thread)
        if any(thread is not None and thread.is_alive() for thread in producers):
            # A failed join is retryable. Retain ownership while a producer can write.
            return
        for agent in self.agents.values():
            try:
                agent.memory.close()
            except BaseException as exc:
                errors.append(exc)

    def _close_traces(self, errors: list[BaseException]) -> None:
        """Release the trace files after the agents stopped writing."""
        for trace in self._traces.values():
            try:
                trace.close()
            except BaseException as exc:
                errors.append(exc)

    # ------------------------------------------------------------ worldfeed
    def start_worldfeed(self) -> None:
        """Serve the WorldFeed API over the live WorldState (background thread)."""
        if self._worldfeed_server is not None or not self._run_worldfeed:
            return
        state: WorldState | None = self.world_state
        if state is None:  # pragma: no cover - world_state is landed; toleration only
            logger.warning("no WorldState available; WorldFeed disabled")
            return
        app = create_app(state, command_dispatcher=self.commands)
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=self.worldfeed_port, log_level="warning")
        )
        self._worldfeed_server = server
        self._worldfeed_thread = threading.Thread(target=server.run, name="worldfeed", daemon=True)
        self._worldfeed_thread.start()
        logger.info("worldfeed serving on http://127.0.0.1:%d", self.worldfeed_port)

    def shutdown_worldfeed(self) -> None:
        server = self._worldfeed_server
        if server is not None:
            server.should_exit = True
            thread = self._worldfeed_thread
            if thread is not None:
                _join_producer(thread, "WorldFeed")
            self._worldfeed_thread = None
            self._worldfeed_server = None
