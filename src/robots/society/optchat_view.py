"""Opt-in pure incremental summary view; no provider or persistence side effects."""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from typing import cast

MAX_SOURCES = 1_000_000
MAX_LEVEL = 20


class InvalidViewError(ValueError):
    """Malformed coordinates, policy, state or summary."""


class OverBudgetError(RuntimeError):
    """The complete view is still above its high watermark."""


@dataclass(frozen=True)
class ViewPolicy:
    """UTF-8 line payload thresholds; custom policies require explicit adoption."""

    namespace: str = "optchat-reference-v1"
    low_bytes: int = 64_000
    high_bytes: int = 128_000

    def __post_init__(self) -> None:
        _integer(self.low_bytes, 1, 128_000_000)
        _integer(self.high_bytes, self.low_bytes + 1, 128_000_000)
        if not isinstance(self.namespace, str) or not self.namespace or len(self.namespace) > 128:
            message = "Policy namespace must be a nonempty bounded string"
            raise InvalidViewError(message)


class NotReadyError(RuntimeError):
    """A required summary has not been built."""


def _integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        message = "Expected a bounded exact integer"
        raise InvalidViewError(message)
    return value


@dataclass(frozen=True, order=True)
class NodeCoordinate:
    """Immutable dyadic tree address (level, index)."""

    level: int
    index: int

    def __post_init__(self) -> None:
        _integer(self.level, 0, MAX_LEVEL)
        _integer(self.index, 0, (MAX_SOURCES >> self.level) - 1)


@dataclass(frozen=True)
class ViewState:
    """Ordered complete source coverage."""

    source_count: int = 0
    coordinates: tuple[NodeCoordinate, ...] = ()
    pending_batch: bool = False

    def __post_init__(self) -> None:
        _integer(self.source_count, 0, MAX_SOURCES)
        if type(self.pending_batch) is not bool or type(self.coordinates) is not tuple:
            message = "State requires tuple coordinates and a boolean pending flag"
            raise InvalidViewError(message)
        end = 0
        for node in self.coordinates:
            if not isinstance(node, NodeCoordinate) or node.index * (1 << node.level) != end:
                message = "Coordinates must cover the source in contiguous ordered intervals"
                raise InvalidViewError(message)
            end += 1 << node.level
        if end != self.source_count:
            message = "Coordinates must cover exactly [0, source_count)"
            raise InvalidViewError(message)


def _mapping(value: object, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        message = "Snapshot fields must match the schema exactly"
        raise InvalidViewError(message)
    return cast("dict[str, object]", value)


def _decode_state(data: dict[str, object]) -> ViewState:
    raw = data["coordinates"]
    if not isinstance(raw, list) or len(raw) > MAX_SOURCES:
        message = "Coordinates must be a bounded JSON array"
        raise InvalidViewError(message)
    nodes = []
    for pair in raw:
        if not isinstance(pair, list) or len(pair) != 2:
            message = "Coordinate requires exactly two integers"
            raise InvalidViewError(message)
        nodes.append(
            NodeCoordinate(_integer(pair[0], 0, MAX_LEVEL), _integer(pair[1], 0, MAX_SOURCES))
        )
    pending = data["pending_batch"]
    if type(pending) is not bool:
        message = "Pending batch must be a boolean"
        raise InvalidViewError(message)
    return ViewState(_integer(data["source_count"], 0, MAX_SOURCES), tuple(nodes), pending)


class IncrementalView:
    """Uses only caller-supplied built summaries, never raw messages."""

    def __init__(
        self, node_text: Callable[[NodeCoordinate], str | None], policy: ViewPolicy | None = None
    ) -> None:
        self.policy = policy if policy is not None else ViewPolicy()
        self._node_text = node_text
        self._state = ViewState()
        self._lines: dict[NodeCoordinate, bytes] = {}

    @property
    def state(self) -> ViewState:
        """The immutable current coordinates."""
        return self._state

    def append(self) -> None:
        """Admit exactly the next source leaf."""
        leaf = NodeCoordinate(0, self.state.source_count)
        self._line(leaf)
        self._state = ViewState(
            self.state.source_count + 1, (*self.state.coordinates, leaf), self.state.pending_batch
        )
        self.advance()

    def read(self) -> bytes:
        """Render stable UTF-8 line bytes without changing the view."""
        return b"".join(self._lines[node] for node in self.state.coordinates)

    def snapshot(self) -> dict[str, object]:
        """Pure JSON primitives, not a durable or world-bound storage receipt."""
        return {
            "version": 1,
            "policy": {
                "namespace": self.policy.namespace,
                "low_bytes": self.policy.low_bytes,
                "high_bytes": self.policy.high_bytes,
            },
            "source_count": self.state.source_count,
            "coordinates": [[node.level, node.index] for node in self.state.coordinates],
            "pending_batch": self.state.pending_batch,
        }

    @classmethod
    def restore(
        cls,
        snapshot: object,
        node_text: Callable[[NodeCoordinate], str | None],
        *,
        expected_policy: ViewPolicy | None = None,
    ) -> IncrementalView:
        """Load exact coordinates; reject corruption without any fallback/refit.

        The caller must bind the callback to the same immutable node closure across
        restarts. This primitive checkpoint does not establish source/world identity.
        """
        data = _mapping(
            snapshot, {"version", "policy", "source_count", "coordinates", "pending_batch"}
        )
        _integer(data["version"], 1, 1)
        raw_policy = _mapping(data["policy"], {"namespace", "low_bytes", "high_bytes"})
        namespace = raw_policy["namespace"]
        if not isinstance(namespace, str):
            message = "Invalid policy namespace"
            raise InvalidViewError(message)
        policy = ViewPolicy(
            namespace,
            _integer(raw_policy["low_bytes"], 1, 128_000_000),
            _integer(raw_policy["high_bytes"], 1, 128_000_000),
        )
        if expected_policy is not None and policy != expected_policy:
            message = "Snapshot policy does not match expected policy"
            raise InvalidViewError(message)
        state = _decode_state(data)
        view = cls(node_text, policy)
        try:
            for node in state.coordinates:
                view._line(node)
        except NotReadyError as error:
            message = "Snapshot references an unbuilt or missing node"
            raise InvalidViewError(message) from error
        view._state = state
        return view

    def read_ready(self) -> bytes:
        """Return complete bytes or explicitly refuse an over-high payload."""
        payload = self.read()
        if len(payload) > self.policy.high_bytes:
            message = "Complete view remains over high watermark"
            raise OverBudgetError(message)
        return payload

    def advance(self) -> None:
        """Explicit parent-readiness event; resume a high-to-low batch."""
        pending = self.state.pending_batch or len(self.read()) > self.policy.high_bytes
        nodes = list(self.state.coordinates)
        while pending and sum(len(self._lines[node]) for node in nodes) > self.policy.low_bytes:
            candidate = self._candidate(nodes)
            if candidate is None:
                break
            position, parent = candidate
            nodes[position : position + 2] = [parent]
        pending = pending and sum(len(self._lines[node]) for node in nodes) > self.policy.low_bytes
        self._state = ViewState(self.state.source_count, tuple(nodes), pending)
        self._lines = {node: self._lines[node] for node in nodes}

    def _candidate(self, nodes: list[NodeCoordinate]) -> tuple[int, NodeCoordinate] | None:
        candidates = []
        for position, (left, right) in enumerate(pairwise(nodes)):
            if left.level != right.level or left.index % 2 or right.index != left.index + 1:
                continue
            parent = NodeCoordinate(left.level + 1, left.index // 2)
            try:
                self._line(parent)
            except NotReadyError:
                continue
            size = 1 << left.level
            last = (left.index + 2) * size - 1
            rank = (self.state.source_count - last) << (MAX_LEVEL - left.level)
            candidates.append((rank, -position, parent))
        if not candidates:
            return None
        _, negative_position, parent = max(candidates)
        return -negative_position, parent

    def _line(self, node: NodeCoordinate) -> bytes:
        if node in self._lines:
            return self._lines[node]
        text: object = self._node_text(node)
        if text is None:
            message = "Required node is not built"
            raise NotReadyError(message)
        if not isinstance(text, str):
            message = "Summary must be text"
            raise InvalidViewError(message)
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError as error:
            message = "Summary must be valid UTF-8"
            raise InvalidViewError(message) from error
        if len(encoded) > 512:
            message = "Summary exceeds 512 UTF-8 bytes"
            raise InvalidViewError(message)
        size = 1 << node.level
        flat = text.replace("\n", " ").replace("\r", " ")
        line = f"{node.index * size}+{size}|{flat}\n".encode()
        self._lines[node] = line
        return line
